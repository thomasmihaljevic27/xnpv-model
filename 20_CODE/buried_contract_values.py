"""
buried_contract_values.py -- traded veterans on NHL contracts that neither the player model nor the prospect model
can value: worth nothing on the ice, costing the cap hit a club cannot bury.

DECIDED (Thomas, 2026-10-14): "Cost above burial", confirmed after the conflict with D16(i) was put to him (D16(i):
the player model counts a buried or injured player's cap hit in full). A recorded departure from D16(i) for these
contracts only: players with no recent NHL season, whom the player model cannot forecast.

WHO (from prospect_values.csv's identities and contract_npv_panel.csv's coverage)
  A traded player asset (trades.db, from the player model's first page, 2018-19) that
  * neither model values: not a valued prospect, and no contract_npv_panel row for his NHL id at the trade season's
    page (the panel's player_id is PuckPedia's own id, translated to the NHL id); and
  * has an NHL contract (PuckPedia, standard or entry level) running on the trade date.
  These are veterans past club control with no NHL season of 10+ games in the three before (skaters) or no NHL game
  in the six before (goalies): the player model has no forecast for them (contract_npv: unpriced_no_anchor /
  unpriced_no_history), and the prospect model gives them zero.

WHAT HE IS WORTH
  value = - sum over the contract's seasons from the trade season to its last season of
          max(0, cap hit carried by the acquiring club - burial allowance that season) / that season's ceiling
          x the 2025-26 ceiling   (cap shares stated at the 2025-26 cap: 3% growth and 3% discounting cancel, D11)
  * burial allowance = the league minimum + $375,000. Source: PuckPedia's "Buried Threshold" (cap relief from an
    AHL assignment is the lesser of the cap hit and the minimum + $375K), also cited by CanucksArmy as CBA Article
    50.5; NOT yet read from the CBA text (flagged).
  * cap hit carried = PuckPedia's cap hit of the contract running on the trade date, less trades.db's retained
    amount when the trading club retained part of it.
  * the trade season counts in full, as for prospects.
  * no on-ice value: no forecast exists, and these players are in the minors or on long-term injury.

INPUTS: OUTPUT_DIR/prospect_values.csv, contract_npv_panel.csv; SOURCE_DIR/trades.db; the PuckPedia contract export
(contract_source.py); skater_forward_projection's ceilings and minimums.
OUTPUTS: OUTPUT_DIR/buried_contract_values.csv, buried_contract_values_log.txt.
Run from the repo root:  python 20_CODE/buried_contract_values.py   (after prospect_values.py)
"""

import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "buried_contract_values.py v1.0 (2026-10-14)"
load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_source as CS                        # noqa: E402
import skater_forward_projection as SFP             # noqa: E402  ceilings and league minimums
SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])
BURY_ABOVE_MIN = 375_000                            # PuckPedia "Buried Threshold" = minimum + $375K (CBA text unread)
CAP_NOW = SFP.CAP_CEILING[2025]
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def main():
    log(SCRIPT_VERSION)
    v = pd.read_csv(OUTPUT_DIR / "prospect_values.csv")
    panel = pd.read_csv(OUTPUT_DIR / "contract_npv_panel.csv", low_memory=False, usecols=["player_id", "valuation_season"])
    pc, _ = CS.load_contracts()
    pp2nhl = {int(a): int(b) for a, b in zip(pc["player_id"], pc["nhl_id"]) if pd.notna(a) and pd.notna(b)}
    assert set(panel["player_id"].astype(int)) <= set(pp2nhl)                     # GUARD: every panel id translates
    priced = {(pp2nhl[int(p)], int(s)) for p, s in zip(panel["player_id"], panel["valuation_season"])}
    first_page = int(panel["valuation_season"].min())
    pc = pc.dropna(subset=["nhl_id", "signing_date", "contract_end", "cap_hit"]).copy()
    pc["signed"] = pd.to_datetime(pc["signing_date"], format="%m/%d/%Y")
    pc["last"] = pc["contract_end"].astype(str).str[:4].astype(int)
    pc["ends"] = pc["last"].map(lambda y: pd.Timestamp(y + 1, 6, 30))
    by_id = dict(tuple(pc.groupby(pc["nhl_id"].astype(int))))
    ret = pd.read_sql("select asset_id, retained_aav from trade_assets", sqlite3.connect(SOURCE_DIR / "trades.db"))
    RET = dict(zip(ret["asset_id"], ret["retained_aav"].fillna(0)))
    link = pd.read_csv(OUTPUT_DIR / "draft_pick_linkage.csv")
    LID = {(int(a), int(b)): int(c) for a, b, c in zip(link["draftYear"], link["overallPickNumber"], link["playerId"])
           if pd.notna(c)}

    rows = []
    for _, r in v.iterrows():
        st = str(r["status"])
        if st.startswith(("prospect, valued", "undrafted prospect, valued")) or int(r["trade_season"]) < first_page:
            continue
        nid = next((int(r[c]) for c in ("nhl_id", "nhl_id_undrafted") if c in r and pd.notna(r[c])), None)
        if nid is None and pd.notna(r.get("draftYear")) and pd.notna(r.get("pick")):
            nid = LID.get((int(r["draftYear"]), int(r["pick"])))
        y, date = int(r["trade_season"]), pd.Timestamp(r["trade_date"])
        if nid is None or (nid, y) in priced or nid not in by_id:
            continue
        run = by_id[nid][(by_id[nid]["signed"] <= date) & (by_id[nid]["ends"] >= date)]
        if run.empty:
            continue
        c = run.sort_values("signed").iloc[-1]
        carried = float(c["cap_hit"]) - float(RET.get(r["asset_id"], 0) or 0)
        cost, seasons = 0.0, []
        for s in range(y, int(c["last"]) + 1):
            allowance = SFP.league_min_path(s) + BURY_ABOVE_MIN
            share = max(0.0, carried - allowance) / SFP.CAP_CEILING[s]
            cost += share
            seasons.append(f"{s}: ${carried / 1e6:.3f}M - ${allowance / 1e6:.3f}M")
        rows.append({"asset_id": r["asset_id"], "trade_date": r["trade_date"], "trade_season": y,
                     "player_name": r["player_name"], "acquiring_team": r["acquiring_team"], "nhl_id": nid,
                     "contract_cap_hit": float(c["cap_hit"]), "retained": float(RET.get(r["asset_id"], 0) or 0),
                     "last_season": int(c["last"]), "seasons_left": int(c["last"]) - y + 1,
                     "value_M": -cost * CAP_NOW / 1e6 + 0.0, "full_cap_hit_value_M": -sum(
                         carried / SFP.CAP_CEILING[s] for s in range(y, int(c["last"]) + 1)) * CAP_NOW / 1e6,
                     "seasons": "; ".join(seasons), "prospect_status": st})
    d = pd.DataFrame(rows)
    log(f"\nTRADED VETERANS ON NHL CONTRACTS NEITHER MODEL VALUES (from the {first_page}-{str(first_page + 1)[2:]} page): "
        f"{len(d)} assets, {d['player_name'].nunique()} players")
    log(f"  value (cost above the burial allowance, at the 2025-26 cap): ${d['value_M'].sum():,.2f}M; "
        f"beside it, the full cap hit (D16(i)'s rule): ${d['full_cap_hit_value_M'].sum():,.2f}M")
    for r in d.sort_values("value_M").itertuples():
        log(f"  {r.trade_date}  {r.player_name:<22} cap hit ${r.contract_cap_hit / 1e6:5.3f}M"
            f"{f' (retained ${r.retained / 1e6:.3f}M)' if r.retained else ''} to {r.last_season}-{str(r.last_season + 1)[2:]}: "
            f"${r.value_M:6.2f}M (full cap hit ${r.full_cap_hit_value_M:6.2f}M); to {r.acquiring_team}")
    d.to_csv(OUTPUT_DIR / "buried_contract_values.csv", index=False)
    (OUTPUT_DIR / "buried_contract_values_log.txt").write_text("\n".join(LOG), encoding="utf-8")
    log(f"\nwrote buried_contract_values.csv and its log in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
