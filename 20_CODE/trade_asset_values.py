"""
trade_asset_values.py -- every traded asset in one table: one value each, the file it came from, both caps.

WHY (the bug sweep, 2026-10-18, finding 4; Thomas: "move on to finding 4 (joining the files)"). The three models write
their values to five files, which the back-test has to put together:
  prospect_values.csv          prospects                          $M at the 2025-26 cap
  traded_player_values.csv     players and rights, 2018-19 on      $ at the cap of the trade's page
  page_2017_values.csv         players traded on the 2017 page     $ at the 2017-18 cap (page_2017_values v1.2)
  buried_contract_values.csv   veterans neither model forecasts    $M at the 2025-26 cap
  traded_pick_values.csv       draft picks                         $M at the 2025-26 cap
Read side by side they invite three mistakes: adding values stated at different caps, counting an asset twice (17
assets appear in two files), and missing an asset no file values. This script reads them once, gives each traded asset
exactly one value under a fixed order, states it at both caps, and lists what is left unvalued.

WHICH FILE VALUES A PLAYER ASSET (the first that applies; each rule follows a recorded decision)
  1. the prospect model, when it values him (status "prospect, valued..." or "undrafted prospect, valued...");
  2. the player model at his trade's page: traded_player_values "ok", or "rights: ..." (rights_values.py's values);
  3. the player model's 2017 page: page_2017_values "ok", or its buried-veteran rows;
  4. buried_contract_values (veterans on NHL contracts with no forecast: the cost above burial, Thomas 2026-10-14);
  5. the prospect model's zeros: past club control, no NHL contract, or signing rights to an expired contract.
  Rule 5 comes after 2-4 because "past club control" only says nothing is left to control: a veteran with no recent
  NHL season (David Clarkson, 2019) is a "prospect past club control" to the prospect model and still costs his cap
  hit above burial. GUARDS: an asset valued under rule 1 has no value under 2-4; rules 2, 3 and 4 never overlap; every
  player and pick asset in trades.db from 2017-07-01 appears once.

THE TWO CAPS (not a decision: how the back-test adds the sides is Thomas's, still open). value_page_cap_M states every
value at the cap of the trade's page; value_2025_cap_M at the 2025-26 cap. Both are the same cap shares times a
different ceiling (3% cap growth and 3% discounting cancel, D11), so the conversion is the ratio of the two ceilings.

ALSO CARRIED, FOR THE BACK-TEST'S OPEN QUESTIONS (no value changes): retained_aav (trades.db; the player model charges
the acquirer the full cap hit, the buried rule subtracts it) and during_regular_season (an in-season trade's value
counts the whole season).

INPUTS: the five files above (OUTPUT_DIR), SOURCE_DIR/trades.db, SOURCE_DIR/games.csv.
OUTPUTS: OUTPUT_DIR/trade_asset_values.csv (one row per traded asset), trade_asset_values_log.txt.
Run from the repo root, after the trade chain (page_2017_values.py last):  python 20_CODE/trade_asset_values.py
"""

import os
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "trade_asset_values.py v1.0 (2026-10-18)"
load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import skater_forward_projection as SFP             # noqa: E402  the ceilings
SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])
TRADES_FROM = "2017-07-01"
CAP_NOW = SFP.CAP_CEILING[2025]
PROSPECT_VALUED = ("prospect, valued", "undrafted prospect, valued")
PROSPECT_ZERO = ("prospect, club control over", "undrafted prospect, club control over",
                 "undrafted, no NHL contract", "undrafted, signing rights only")
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def main():
    log(SCRIPT_VERSION)
    files = {k: OUTPUT_DIR / f for k, f in (("prospects", "prospect_values.csv"), ("players", "traded_player_values.csv"),
                                            ("page2017", "page_2017_values.csv"), ("buried", "buried_contract_values.csv"),
                                            ("picks", "traded_pick_values.csv"))}
    for k, p in files.items():
        first = (p.with_name(p.stem + "_log.txt")).read_text(encoding="utf-8").splitlines()[0]
        log(f"  input {k}: {p.name} (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M}; {first})")
    pv, tp = pd.read_csv(files["prospects"]), pd.read_csv(files["players"])
    p17, bu, pk = pd.read_csv(files["page2017"]), pd.read_csv(files["buried"]), pd.read_csv(files["picks"])

    con = sqlite3.connect(SOURCE_DIR / "trades.db")
    a = pd.read_sql("select a.asset_id, a.trade_id, t.trade_date, a.asset_type, a.player_name, a.pick_year, a.pick_round, "
                    "a.pick_original_team, a.from_team, l.acquiring_team, a.retained_aav from trade_assets a "
                    "join trades t using(trade_id) join trade_legs l using(leg_id) where t.trade_date >= ?",
                    con, params=(TRADES_FROM,))
    import trade_page as TP
    a["valuation_page"] = a["trade_date"].map(TP.page)
    g = pd.read_csv(SOURCE_DIR / "games.csv", usecols=["season", "game_type", "game_date"])
    g = g[g["game_type"] == 2].assign(syr=lambda x: x["season"].astype(str).str[:4].astype(int),
                                      d=lambda x: pd.to_datetime(x["game_date"]))
    first_game = g.groupby("syr")["d"].min().to_dict()
    d = pd.to_datetime(a["trade_date"])
    a["during_regular_season"] = [(p in first_game) and first_game[p] <= x <= TP.regular_season_end().get(p, x)
                                  for p, x in zip(a["valuation_page"], d)]

    # ---- the value of each asset, from the first file that values it ----------------------------------------------
    P = pv.set_index("asset_id")
    T = tp.set_index("asset_id")
    S = p17.set_index("asset_id")
    B = bu.set_index("asset_id")
    K = pk.set_index("asset_id")
    rows = []
    for r in a.itertuples():
        rec = {"asset_id": r.asset_id, "trade_id": r.trade_id, "trade_date": r.trade_date, "asset_type": r.asset_type,
               "name": r.player_name if r.asset_type == "player" else f"{int(r.pick_year)} round {int(r.pick_round)} "
                                                                       f"({r.pick_original_team})",
               "from_team": r.from_team, "acquiring_team": r.acquiring_team, "valuation_page": int(r.valuation_page),
               "during_regular_season": bool(r.during_regular_season),
               "retained_aav": float(r.retained_aav) if pd.notna(r.retained_aav) else 0.0}
        page_cap = SFP.CAP_CEILING[int(r.valuation_page)]
        if r.asset_type == "pick":
            x = K.loc[r.asset_id]
            rec.update(source="pick curve (traded_pick_values)", status=x["method"],
                       value_2025_cap_M=x["value_M"], basis="2025-26 cap")
            rows.append(rec)
            continue
        ps = str(P.at[r.asset_id, "status"]) if r.asset_id in P.index else "not in prospect_values"
        ts = str(T.at[r.asset_id, "status"]) if r.asset_id in T.index else None
        ss = str(S.at[r.asset_id, "status"]) if r.asset_id in S.index else None
        has_t = ts is not None and (ts == "ok" or ts.startswith("rights:"))
        has_s = ss is not None and (ss == "ok" or ss.startswith("buried veteran"))
        has_b = r.asset_id in B.index
        valued_p = ps.startswith(PROSPECT_VALUED)
        assert not (valued_p and (has_t or has_s or has_b)), (r.asset_id, r.player_name)      # GUARD: rule 1 is alone
        assert has_t + has_s + has_b <= 1, (r.asset_id, r.player_name, ts, ss, has_b)       # GUARD: 2-4 never overlap
        rec["prospect_status"] = ps
        if valued_p:
            rec.update(source="prospect model", status=ps, value_2025_cap_M=P.at[r.asset_id, "value_M"],
                       basis="2025-26 cap")
        elif has_t:
            rec.update(source="player model" if ts == "ok" else "player model, rights", status=ts,
                       value_page_cap_M=T.at[r.asset_id, "npv_total"] / 1e6, basis="page cap")
        elif has_s:
            rec.update(source="player model, 2017 page" if ss == "ok" else "buried contract, 2017 page", status=ss,
                       value_page_cap_M=S.at[r.asset_id, "npv_total"] / 1e6, basis="page cap")
        elif has_b:
            rec.update(source="buried contract", status="cost above burial",
                       value_2025_cap_M=B.at[r.asset_id, "value_M"], basis="2025-26 cap")
        elif ps.startswith(PROSPECT_ZERO):
            rec.update(source="prospect model (zero)", status=ps, value_2025_cap_M=0.0, basis="2025-26 cap")
        else:
            why = ts if ts is not None else (ss if ss is not None else ps)
            rec.update(source="not valued", status=why, basis=None)
        # the overlap the order resolved: the prospect model's zero beside a player-side value (rule 5 under 2-4)
        rec["also_in"] = ("prospect model (zero)" if ps.startswith(PROSPECT_ZERO)
                          and rec["source"] not in ("prospect model (zero)", "not valued") else None)
        rows.append(rec)
    v = pd.DataFrame(rows)
    # both caps: the same cap shares at the trade page's ceiling and at the 2025-26 ceiling
    cap = v["valuation_page"].map(SFP.CAP_CEILING)
    v["value_page_cap_M"] = v["value_page_cap_M"].where(v["basis"] != "2025-26 cap", v["value_2025_cap_M"] * cap / CAP_NOW)
    v["value_2025_cap_M"] = v["value_2025_cap_M"].where(v["basis"] != "page cap", v["value_page_cap_M"] * CAP_NOW / cap)

    # ---- guards on the whole table ------------------------------------------------------------------------------------
    assert v["asset_id"].is_unique
    n_pl, n_pk = int((a["asset_type"] == "player").sum()), int((a["asset_type"] == "pick").sum())
    assert len(v) == len(a) and set(K.index) == set(v.loc[v["asset_type"] == "pick", "asset_id"])
    assert set(P.index) == set(v.loc[v["asset_type"] == "player", "asset_id"]), "prospect_values does not list every player"
    ok = v["source"] != "not valued"
    assert v.loc[ok, "value_2025_cap_M"].notna().all() and v.loc[ok, "value_page_cap_M"].notna().all()

    # ---- report -----------------------------------------------------------------------------------------------------------
    log(f"\nTRADED ASSETS FROM {TRADES_FROM}: {len(v):,} ({n_pl} players, {n_pk} picks; trades.db ends "
        f"{pd.read_sql('select max(trade_date) m from trades', con)['m'][0]})")
    s = v.groupby("source").agg(assets=("asset_id", "size"), page_cap_M=("value_page_cap_M", "sum"),
                                cap_2025_M=("value_2025_cap_M", "sum"))
    log(s.round(2).to_string())
    log(f"  all valued assets: {int(ok.sum()):,}; at the page caps ${v['value_page_cap_M'].sum():,.2f}M, "
        f"at the 2025-26 cap ${v['value_2025_cap_M'].sum():,.2f}M")
    two = v[v["also_in"].notna()]
    log(f"\n  in two files, resolved by the order above ({len(two)}; the other file's value is listed):")
    for r in two.itertuples():
        log(f"    {r.trade_date} {r.name:<24} {r.source}: {r.value_2025_cap_M:+.2f} at 2025-26 (also: {r.also_in})")
    nv = v[~ok]
    log(f"\n  NOT VALUED ({len(nv)}):")
    for r in nv.itertuples():
        log(f"    {r.trade_date} {r.name:<24} page {r.valuation_page}: {r.status}")
    rt = v[(v["retained_aav"] > 0) & v["source"].str.startswith("player model")]
    log(f"\n  for the back-test: {int((v['retained_aav'] > 0).sum())} assets with retained salary (valued by the player "
        f"model at the full cap hit: {len(rt)}); {int(v['during_regular_season'].sum())} assets traded during the "
        f"regular season (their value counts the whole season)")
    v.to_csv(OUTPUT_DIR / "trade_asset_values.csv", index=False)
    (OUTPUT_DIR / "trade_asset_values_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    log(f"\nwrote trade_asset_values.csv and its log in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
