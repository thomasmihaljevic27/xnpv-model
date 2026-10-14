"""
page_2017_values.py -- the player model's 2017 page for the players traded in 2017-18 that no model valued.

DECIDED (Thomas, 2026-10-14): "Build a 2017 page"; "Continue the 2017-18 page here". The player model's pages start
in 2018-19 because PuckPedia's contract export holds contracts running in 2018-19 or later; 135 traded player
assets of 2017-18 were valued by neither model (25_TESTS/uncovered_assets_audit.py).

THE CONTRACTS: CapWages, for every asset (contracts_2017.py's parser). Where PuckPedia's spine also carries a 2017
row for the player (48 assets), the two were compared: they agree on the cap hit and the last season for 39 of 45;
in all six that differ, trades.db's own cap hit sides with CapWages (Spooner $2,825,000, Henrique $4,000,000,
Cammalleri $1,000,000, Turris $3,500,000, Phaneuf $7,000,000 with $1,750,000 retained), and its last seasons fit
the players' later contracts (Phaneuf to 2020-21, Turris's Ottawa deal ending 2017-18). So one source for the page:
the running contract and every extension signed on or before the trade date come from the player's CapWages page,
and the PuckPedia rows that overlap them are set aside for this page only.

THE VALUATION: contract_npv.NPVEngine, unchanged, at valuation season 2017 with as_of = the trade date (inside the
page's window, July 1 2017 to June 30 2018): page 2017's forecast (seasons 2016-17 and earlier), the locked price
line, the 2017-18 ceiling with D11's 3% path, the D10 floor, the terminal value at expiry. What the CapWages
contract supplies, per season: cap hit (the contract's stated cap hit), base salary (starts the qualifying-offer
chain), expiry status (UFA / RFA), entry level or not; the signing date (for the extension chain). Built here:
  * name key: the WAR spelling (contract_source.war_full_name for a crosswalked NHL id), cleaned, + F/D;
  * birthdate: PuckPedia's, else the age table's (WAR_with_age.csv) for the name key;
  * UFA year for an RFA contract: CBA Group 3 as pick_curve and prospect_values compute it (27 as of June 30, or
    seven Accrued Seasons from his NHL games), the start year of his first free season;
  * arbitration eligibility: no PuckPedia flag, so the CBA 12.1(a) count (rfa_terminal_value's rule without a flag);
  * player id: PuckPedia's when he has one, else a synthetic negative id (the engine keys on it only).
  FALLBACK: where CapWages shows no contract (an unsigned player's page lists none), PuckPedia's own spine contract at
  2017, priced on the unchanged engine. NO FORECAST (no recent NHL season): the buried rule of
  buried_contract_values.py (Thomas, "Cost above burial"): the cap hit above the league minimum + $375K, no value.
  REPRODUCTION (25_TESTS/page_2017_reproduction_check.py): where both sources hold the same contract (38 assets),
  the CapWages-built contract prices as PuckPedia's own does, npv_total within $0.01M for 38 of 38.
  The engine instance is this script's own; nothing the live chain writes is changed.

OUTPUTS: OUTPUT_DIR/page_2017_values.csv (one row per asset: the contract used, npv_total and its parts, status),
page_2017_values_log.txt.
Run from the repo root:  python 20_CODE/page_2017_values.py   (after contracts_2017.py and prospect_values.py)
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "page_2017_values.py v1.0 (2026-10-14)"
load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_source as CS                         # noqa: E402
import contracts_2017 as K                           # noqa: E402
import contract_npv as CN                            # noqa: E402
import prospect_values as PV                         # noqa: E402  window_end, season_table, norm
import skater_forward_projection as SFP              # noqa: E402  ceilings and minimums (the buried rule)
from buried_contract_values import BURY_ABOVE_MIN    # noqa: E402  minimum + $375K
from player_season_table import norm_name            # noqa: E402
OUTPUT_DIR, SOURCE_DIR = Path(os.environ["OUTPUT_DIR"]), Path(os.environ["SOURCE_DIR"])
PAGE = 2017
POSGRP = {"Center": "F", "Left Wing": "F", "Right Wing": "F", "Defense": "D", "Goaltender": "G"}
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def main():
    log(SCRIPT_VERSION)
    a = pd.read_csv(OUTPUT_DIR / "uncovered_assets_audit.csv")
    # every asset on the 2017 page (trade_page.py) the prospect model does not value (the player model's pages start
    # in 2018-19); not covered_by == "neither": the audit counts this script's own earlier output as coverage
    a = a[(a["covered_by"] != "prospect model") & (a["valuation_page"] == PAGE)].copy()
    k17 = pd.read_csv(OUTPUT_DIR / "contracts_2017.csv").set_index("asset_id")
    log(f"  assets: {len(a)} ({a['player_name'].nunique()} players), traded {PAGE}-{str(PAGE + 1)[2:]}, no model valued")

    pc, _ = CS.load_contracts()
    PPID = {int(b): int(x) for x, b in zip(pc["player_id"], pc["nhl_id"]) if pd.notna(x) and pd.notna(b)}
    INFO = {int(b): (p, bd) for b, p, bd in zip(pc["nhl_id"], pc["position"], pc["birthdate"]) if pd.notna(b)}
    wa = pd.read_csv(OUTPUT_DIR / "WAR_with_age.csv", usecols=["Player", "Position", "birthdate"]).dropna()
    BD_AGE = {norm_name(p) + "|" + str(q): bd for p, q, bd in zip(wa["Player"], wa["Position"], wa["birthdate"])}
    POS_WAR = {norm_name(p): str(q) for p, q in zip(wa["Player"], wa["Position"])}
    gw = pd.read_csv(SOURCE_DIR / "Goalies_WAR.csv", usecols=["Goalie"])
    GOALIE_NAMES = set(gw["Goalie"].map(norm_name))
    tables = {False: PV.season_table(SOURCE_DIR / "WAR.csv", "Player"),
              True: PV.season_table(SOURCE_DIR / "Goalies_WAR.csv", "Goalie")}

    eng = CN.NPVEngine()
    sp = eng.sp
    next_cid, next_pid = -1, -1
    rows = []
    for r in a.itertuples():
        rec = {"asset_id": r.asset_id, "trade_date": r.trade_date, "player_name": r.player_name,
               "acquiring_team": r.acquiring_team, "nhl_id": r.nhl_id}
        if r.asset_id not in k17.index or k17.loc[r.asset_id, "status"] != "contract found":
            why = k17.loc[r.asset_id, "status"] if r.asset_id in k17.index else "not read"
            # FALLBACK: CapWages shows no contract (an unsigned player's page lists none: Alex Galchenyuk), so the
            # unchanged engine prices PuckPedia's own contract when its spine has a 2017 row for him
            pid0 = PPID.get(int(r.nhl_id)) if pd.notna(r.nhl_id) else None
            has17 = pid0 is not None and (((sp.spine["player_id"] == pid0) & (sp.spine["season_start"] == PAGE)).any()
                                          or ((eng.gp_spine["player_id"] == pid0)
                                              & (eng.gp_spine["season_start"] == PAGE)).any())
            if has17:
                d, sm = eng.npv(pid0, PAGE, pd.Timestamp(r.trade_date))
                rec.update({"player_id": pid0, "contract": "PuckPedia (no CapWages contract)",
                            "status": sm.get("status")})
                for kk in ("npv_total", "npv_contract", "npv_terminal", "npv_total_qo", "npv_total_term_free"):
                    if kk in sm:
                        rec[kk] = sm[kk]
            else:
                rec["status"] = f"no contract found (CapWages: {why}; PuckPedia: none at 2017)"
            rows.append(rec)
            continue
        date = pd.Timestamp(r.trade_date)
        cons = K.parse_contracts(K.page_lines(open(k17.loc[r.asset_id, "page"], encoding="utf-8",
                                                    errors="ignore").read()))
        run = [c for c in cons if PAGE in c["seasons"] and pd.notna(c.get("signing_date")) and c["signing_date"] <= date]
        c0 = max(run, key=lambda x: x["signing_date"])
        chain = [c0]
        while True:                                     # extensions signed by the trade date, contiguous
            nxt = [c for c in cons if pd.notna(c.get("signing_date")) and c["signing_date"] <= date
                   and c["seasons"] and min(c["seasons"]) == max(chain[-1]["seasons"]) + 1]
            if not nxt:
                break
            chain.append(min(nxt, key=lambda x: x["signing_date"]))
        nid = int(r.nhl_id) if pd.notna(r.nhl_id) else None
        pos_pp, bd_pp = INFO.get(nid, (None, None)) if nid else (None, None)
        base_name = pd.Series([r.player_name])
        wname = (CS.war_full_name(pd.DataFrame({"nhl_id": [nid]}), base_name).iloc[0] if nid else r.player_name)
        nn = norm_name(wname)
        if pos_pp:
            pg = POSGRP.get(pos_pp)
        elif nn in POS_WAR:
            pg = "D" if POS_WAR[nn].startswith("D") else "F"
        elif nn in GOALIE_NAMES:
            pg = "G"
        else:
            pg = None
        if pg is None:
            rec["status"] = "position unknown (no PuckPedia record, no WAR row under the name)"
            rows.append(rec)
            continue
        gk = pg == "G"
        bd = pd.to_datetime(bd_pp, format="%m/%d/%Y", errors="coerce") if bd_pp else pd.NaT
        if pd.isna(bd):
            bd = pd.to_datetime(BD_AGE.get(nn + "|" + ("G" if gk else pg)), errors="coerce")
        pid = PPID.get(nid) if nid else None
        if pid is None:
            pid, next_pid = next_pid, next_pid - 1
        # the player's NHL seasons (for the CBA Group 3 window and accrued seasons)
        t = tables[gk]
        s = t.loc[nn] if nn in t.index.get_level_values(0) else pd.DataFrame({"GP": [], "WAR": []})
        ufa = PV.window_end(bd, gk, s) if pd.notna(bd) else np.nan
        new = []
        for c in chain:
            cid, next_cid = next_cid, next_cid - 1
            sp.signed[cid] = c["signing_date"]
            # CapWages's expiry labels, in the spine's terms: "RFA (Arb)" is an RFA with arbitration rights (PuckPedia's
            # arbitration_eligible = 1, read by the terminal value), "RFA" one without (0); "10.2(c)" is an RFA under
            # CBA 10.2(c) (no arbitration, no offer sheets); "UFA (No QO)" is the spine's "UFA no QO"; "UFA (Group 6)"
            # and "UFA" are UFA
            raw = str(c.get("expiry_status"))
            c["expiry_status"] = ("RFA" if raw.startswith("RFA") or raw.startswith("10.2")
                                  else "UFA no QO" if "No QO" in raw else "UFA")
            if c["expiry_status"] == "RFA":
                eng.tv.arb_flag[cid] = 1 if "Arb" in raw else 0
            c["expiry_raw"] = raw
            last = max(c["seasons"])
            for y in sorted(c["seasons"]):
                new.append({"contract_id": cid, "player_id": pid, "nhl_id": nid, "season_start": y,
                            "position": "Goaltender" if gk else ("Defense" if pg == "D" else "Center"),
                            "posgrp": pg, "full_name": wname, "nk": nn + "|" + pg, "nname": nn,
                            "cost": c["seasons"][y], "cs_cap_hit": c["seasons"][y], "pp_cap_hit": c["seasons"][y],
                            "pp_aav": c["seasons"][y], "cs_nhl_salary": c.get("base", {}).get(y),
                            "bd": bd, "birthdate": bd, "pp_expiry": c.get("expiry_status"),
                            "ufa_year": ufa if c.get("expiry_status") == "RFA" else np.nan,
                            "cs_entry_level": "Entry" in c["type"], "pp_ctype": "capwages", "season": f"{y}-{str(y + 1)[2:]}",
                            "first_name": "", "last_name": ""})
        nd = pd.DataFrame(new)
        seasons_used = set(nd["season_start"])
        if gk:                                          # set aside overlapping PuckPedia rows, add CapWages ones
            eng.gp_spine = pd.concat([eng.gp_spine[~((eng.gp_spine["player_id"] == pid)
                                                     & eng.gp_spine["season_start"].isin(seasons_used))], nd],
                                     ignore_index=True)
            sp.spine = sp.spine[sp.spine["player_id"] != pid]
        else:
            sp.spine = pd.concat([sp.spine[~((sp.spine["player_id"] == pid) & sp.spine["season_start"].isin(seasons_used))],
                                  nd], ignore_index=True)
            eng.gp_spine = eng.gp_spine[eng.gp_spine["player_id"] != pid]
        d, sm = eng.npv(pid, PAGE, date)
        rec.update({"player_id": pid, "position": pg, "war_name": wname, "contract": c0["type"],
                    "signed": c0["signing_date"].date(), "cap_hit_2017": c0["seasons"][PAGE],
                    "contract_last_season": max(c0["seasons"]), "expiry": c0.get("expiry_raw"),
                    "extensions": len(chain) - 1, "chain_last_season": max(chain[-1]["seasons"]),
                    "ufa_year": ufa, "status": sm.get("status")})
        for kk in ("npv_total", "npv_contract", "npv_terminal", "npv_total_qo", "npv_total_term_free"):
            if kk in sm:
                rec[kk] = sm[kk]
        if sm.get("status") in ("unpriced_no_anchor", "unpriced_no_history"):
            # no forecast (no recent NHL season): buried_contract_values.py's rule (Thomas, "Cost above burial"),
            # the cap hit above the burial allowance (league minimum + $375K) over the contracts held, no value
            cost = sum(max(0.0, nd.loc[i, "cost"] - (SFP.league_min_path(int(nd.loc[i, "season_start"]))
                                                     + BURY_ABOVE_MIN)) / SFP.CAP_CEILING[int(nd.loc[i, "season_start"])]
                       for i in nd.index)
            rec.update({"status": "buried veteran (cost above burial)", "npv_total": -cost * SFP.CAP_CEILING[2025] + 0.0,
                        "npv_contract": -cost * SFP.CAP_CEILING[2025] + 0.0, "npv_terminal": 0.0})
        rows.append(rec)
    v = pd.DataFrame(rows)
    log("\n" + v["status"].value_counts().to_string())
    ok = v[v["status"].isin(["ok", "buried veteran (cost above burial)"])]
    log(f"\n  priced: {len(ok)} assets; npv_total ${ok['npv_total'].sum() / 1e6:,.1f}M "
        f"(contract ${ok['npv_contract'].sum() / 1e6:,.1f}M, terminal ${ok['npv_terminal'].sum() / 1e6:,.1f}M)")
    for r in ok.sort_values("npv_total").itertuples():
        what = (f"{r.position} ${r.cap_hit_2017 / 1e6:5.3f}M to {int(r.chain_last_season)}-"
                f"{str(int(r.chain_last_season) + 1)[2:]} ({r.expiry})" if pd.notna(r.chain_last_season) else r.contract)
        log(f"    {r.trade_date}  {r.player_name:<24} {what}: ${r.npv_total / 1e6:7.2f}M"
            + ("  [buried]" if str(r.status).startswith("buried") else ""))
    for r in v[~v["status"].isin(["ok", "buried veteran (cost above burial)"])].itertuples():
        log(f"  {r.status}: {r.trade_date} {r.player_name}")
    v.to_csv(OUTPUT_DIR / "page_2017_values.csv", index=False)
    (OUTPUT_DIR / "page_2017_values_log.txt").write_text("\n".join(LOG), encoding="utf-8")
    log(f"\nwrote page_2017_values.csv and its log in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
