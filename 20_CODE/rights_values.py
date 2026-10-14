"""
rights_values.py -- the rights to a pending free agent, traded after the regular season and valued on the next page.

ASKED (Thomas, 2026-10-14): "Value restricted free agents' rights as their control years from the next page (the
terminal-value logic, from that page's forecast); unrestricted rights are worth zero. Show me the figures before
adopting." ADOPTED (Thomas, 2026-10-14: "Adopt the rights values: wire rights_values.py into the traded-player values
so the 19 assets carry them."): after it values them, this script writes each value back into
traded_player_values.csv (npv_total and its versions; status "rights: RFA control years" or "rights: UFA, zero"),
so it runs after traded_player_values.py and every reader of that file sees the rights valued.

WHO: traded_player_values.csv rows "rights only (his contract at the page was signed after the trade)" or "no contract
at the page": a trade after the regular season (trade_page.py: valued on the next page, P) of a player whose contract
ended with the season just played (P - 1).

THE EXPIRED CONTRACT: PuckPedia's spine contract of his whose last season is P - 1 (signed on or before the trade);
for P = 2018 (contracts ending 2017-18, before PuckPedia's coverage), his CapWages contract ending 2017-18, built into
the engine's own spine as page_2017_values.py builds them (cap hit, base salary, expiry, CBA Group 3 UFA year, the
"RFA (Arb)" flag).

THE VALUE
  * expiry UFA (or "UFA no QO"): zero, the club controls nothing (Thomas).
  * expiry RFA, skater: rfa_terminal_value.TerminalValuer.terminal_value(player, P, July 1 of P,
    expired_contract_id=...) (v2.6): the control seasons P .. UFA year - 1 on page P's forecast, the qualifying offer
    (on his last salary) or once eligible the arbitration price, D13 walk-away, D14(c) qualify-or-walk gates, the
    chain starting at 1.0; then the engine's own discount, 3% a season from the page (the first at k = 0).
    The term-free and qualifying-offer-chain versions beside it, as for every contract.
  * expiry RFA, goaltender: the goalie branch's terminal block (contract_npv._npv_goalie, as of 2026-10-14) restated
    here with the same rules: flat projection pw on page P, the pooled control weight, D13, arbitration from
    PuckPedia's flag or the CBA count; the chain starting at 1.0 and the first control season at k = 0.
  The trade date comes before July 1 of P; the page's information (seasons through P - 1) was complete at the trade.

OUTPUTS: OUTPUT_DIR/rights_values.csv, rights_values_log.txt.
Run from the repo root:  python 20_CODE/rights_values.py   (after traded_player_values.py)
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "rights_values.py v1.1 (2026-10-14)"
load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_npv as CN                                         # noqa: E402
import contracts_2017 as K                                        # noqa: E402
import prospect_values as PV                                      # noqa: E402
from player_season_table import norm_name                         # noqa: E402
from skater_forward_projection import page_date, cap_path, league_min_path   # noqa: E402
from rfa_terminal_value import qualifying_offer, arb_eligible     # noqa: E402
OUTPUT_DIR, SOURCE_DIR = Path(os.environ["OUTPUT_DIR"]), Path(os.environ["SOURCE_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def goalie_rights(eng, pid, t0, crows, as_of):
    """The goalie branch's terminal block (contract_npv._npv_goalie), the chain at 1.0, first control season k = 0."""
    from contract_npv import ALPHA_G, BETA_G, G, ARB_NEED, signing_year
    nname = crows.iloc[0]["nname"]
    pw, src = eng.g_proj.shrunk_projection(nname, t0)
    if pd.isna(pw):
        return None, "goalie: no history"
    end, ufa_year = int(crows["season_start"].max()), crows.iloc[0]["ufa_year"]
    if pd.isna(ufa_year):
        return None, "goalie: no UFA year"
    final = crows[crows["season_start"] == end].iloc[0]
    sal = float(final["cs_nhl_salary"]) if pd.notna(final["cs_nhl_salary"]) else float(final["pp_aav"])
    cap_hit = float(final["cost"])
    s20 = int(crows["season_start"].min()) >= 2020
    bd = crows.iloc[0]["bd"]
    observed, first = eng.g_proj.history(nname, t0)
    sy = signing_year(crows.iloc[0].get("nhl_id"))
    need = None if pd.isna(bd) else ARB_NEED(int(np.floor((pd.Timestamp(sy if sy is not None else first, 9, 15)
                                                           - bd).days / 365.25)))
    obs_gp = {z: v[0] for z, v in observed.items()}
    flag = eng.tv.arb_flag.get(int(crows.iloc[0]["contract_id"]))
    S_tv, tv = 1.0, 0.0
    for j, season in enumerate(range(end + 1, int(ufa_year)), 1):
        k = (end - t0) + j
        ceil = cap_path(t0, k)
        lm = league_min_path(season)
        val = max((ALPHA_G + BETA_G * pw) * ceil, lm)
        elig = arb_eligible(season, t0, need, obs_gp) if flag is None else (flag == 1 or j >= 2)
        tw = eng.g_proj.arbitration_war(nname, t0, season, pw) if elig else None
        qo = qualifying_offer(sal, cap_hit, season, s20)
        cost = max(qo, max((ALPHA_G + BETA_G * tw) * ceil, lm)) if tw is not None else qo
        if val - cost < 0:
            break                                       # D13
        S_tv *= eng.g_control_weight
        tv += S_tv * (val - cost) * (1 + G) ** (-k)
        sal, cap_hit = cost, cost
    return tv, "ok"


def main():
    log(SCRIPT_VERSION)
    tp = pd.read_csv(OUTPUT_DIR / "traded_player_values.csv")
    a = tp[tp["status"].astype(str).str.startswith(("rights only", "no contract at the page"))].copy()
    log(f"  rights assets: {len(a)}")
    eng = CN.NPVEngine()
    sp = eng.sp
    tables = {False: PV.season_table(SOURCE_DIR / "WAR.csv", "Player"),
              True: PV.season_table(SOURCE_DIR / "Goalies_WAR.csv", "Goalie")}
    next_cid = -1000
    rows = []
    for r in a.itertuples():
        P, date, pid = int(r.valuation_page), pd.Timestamp(r.trade_date), int(r.player_id)
        rec = {"asset_id": r.asset_id, "trade_date": r.trade_date, "player_name": r.player_name, "page": P}
        gk = (eng.gp_spine["player_id"] == pid).any() and not (sp.spine["player_id"] == pid).any()
        spine = eng.gp_spine if gk else sp.spine
        mine = spine[spine["player_id"] == pid]
        last = mine.groupby("contract_id")["season_start"].max()
        cands = [int(c) for c, l in last.items() if l == P - 1
                 and pd.notna(sp.signed.get(int(c))) and sp.signed[int(c)] <= date]
        source = "PuckPedia"
        if not cands:                                   # contracts ending 2017-18: CapWages, built as page_2017 does
            f = K.find_page(r.player_name)
            cons = K.parse_contracts(K.page_lines(open(f, encoding="utf-8", errors="ignore").read())) if f else []
            cw = [c for c in cons if c["seasons"] and max(c["seasons"]) == P - 1 and pd.notna(c.get("signing_date"))
                  and c["signing_date"] <= date]
            if not cw:
                rec["status"] = "no expired contract found (PuckPedia or CapWages)"
                rows.append(rec)
                continue
            c = max(cw, key=lambda x: x["signing_date"])
            raw = str(c.get("expiry_status"))
            expiry = "RFA" if raw.startswith(("RFA", "10.2")) else ("UFA no QO" if "No QO" in raw else "UFA")
            base = mine.iloc[0] if len(mine) else None
            nn = base["nname"] if (base is not None and "nname" in base and pd.notna(base.get("nname"))) else norm_name(r.player_name)
            pg = "G" if gk else (base["posgrp"] if base is not None else "F")
            bd = base["bd"] if base is not None else pd.NaT
            t = tables[gk]
            s = t.loc[nn] if nn in t.index.get_level_values(0) else pd.DataFrame({"GP": [], "WAR": []})
            ufa = PV.window_end(bd, gk, s) if pd.notna(bd) else np.nan
            cid, next_cid = next_cid, next_cid - 1
            sp.signed[cid] = c["signing_date"]
            if expiry == "RFA":
                eng.tv.arb_flag[cid] = 1 if "Arb" in raw else 0
            new = pd.DataFrame([{**(base.to_dict() if base is not None else {}),
                                 "contract_id": cid, "player_id": pid, "season_start": y, "cost": c["seasons"][y],
                                 "cs_cap_hit": c["seasons"][y], "pp_cap_hit": c["seasons"][y], "pp_aav": c["seasons"][y],
                                 "cs_nhl_salary": c.get("base", {}).get(y), "pp_expiry": expiry,
                                 "ufa_year": ufa if expiry == "RFA" else np.nan, "cs_entry_level": "Entry" in c["type"],
                                 "pp_ctype": "capwages", "nk": (base.get("nk") if base is not None and pd.notna(base.get("nk")) else nn + "|" + pg),
                                 "nname": nn} for y in sorted(c["seasons"])])
            if gk:
                eng.gp_spine = pd.concat([eng.gp_spine, new], ignore_index=True)
            else:
                sp.spine = pd.concat([sp.spine, new], ignore_index=True)
            cands, source = [cid], "CapWages"
        cid = cands[0]
        spine = eng.gp_spine if gk else sp.spine
        crows = spine[spine["contract_id"] == cid].sort_values("season_start")
        expiry = crows.iloc[0]["pp_expiry"]
        rec.update({"position": "G" if gk else crows.iloc[0].get("posgrp"), "expired_contract": cid, "source": source,
                    "expiry": expiry, "last_cap_hit": float(crows.iloc[-1]["cost"]), "ufa_year": crows.iloc[0]["ufa_year"]})
        if expiry != "RFA":
            rec.update({"status": "UFA rights: zero", "value_M": 0.0})
            rows.append(rec)
            continue
        as_of = page_date(P)
        if gk:
            v, st = goalie_rights(eng, pid, P, crows, as_of)
            rec.update({"status": st, "value_M": None if v is None else v / 1e6})
        else:
            d, sm = eng.tv.terminal_value(pid, P, as_of, expired_contract_id=cid)
            if sm.get("status") != "ok":
                rec.update({"status": sm.get("status")})
                if sm.get("status") in ("ufa_expiry", "rfa_no_control_years_DATA_FLAG"):
                    rec["value_M"] = 0.0
            else:
                disc = lambda j: (1 + CN.G) ** (-(j - 1))                   # noqa: E731  k = j - 1 from page P
                rec.update({"status": "ok", "n_control": sm["n_control"],
                            "value_M": float(sum(x.surplus_adjusted * disc(x.j) for x in d.itertuples())) / 1e6,
                            "value_qo_M": float(sum(x.surplus_adjusted_qo * disc(x.j) for x in d.itertuples())) / 1e6,
                            "value_term_free_M": float(sum(x.surplus_adjusted_term_free * disc(x.j)
                                                           for x in d.itertuples())) / 1e6})
        rows.append(rec)
    v = pd.DataFrame(rows).merge(tp[["asset_id"]], on="asset_id")
    log("\n" + v["status"].value_counts().to_string())
    log(f"  total ${v['value_M'].fillna(0).sum():,.2f}M")
    for x in v.sort_values("value_M", ascending=False, na_position="last").itertuples():
        val = "" if pd.isna(x.value_M) else f"${x.value_M:6.2f}M"
        log(f"    {x.trade_date}  {x.player_name:<22} page {x.page} {str(x.position):<2} {str(x.expiry):<10} "
            f"UFA year {x.ufa_year if pd.notna(x.ufa_year) else '-'}  {val:>9}  {x.status} ({x.source})")
    v.to_csv(OUTPUT_DIR / "rights_values.csv", index=False)
    # ADOPTED: write the values back into traded_player_values.csv (Thomas, 2026-10-14)
    tpv = pd.read_csv(OUTPUT_DIR / "traded_player_values.csv")
    got = v.dropna(subset=["value_M"]).set_index("asset_id")
    hit = tpv["asset_id"].isin(got.index)
    for i in tpv.index[hit]:
        x = got.loc[tpv.at[i, "asset_id"]]
        ufa = str(x["status"]).startswith("UFA rights")
        tpv.at[i, "status"] = "rights: UFA, zero" if ufa else "rights: RFA control years"
        tpv.at[i, "npv_total"] = x["value_M"] * 1e6
        tpv.at[i, "npv_contract"] = 0.0
        tpv.at[i, "npv_terminal"] = x["value_M"] * 1e6
        for col, src in (("npv_total_qo", "value_qo_M"), ("npv_total_term_free", "value_term_free_M")):
            q = x.get(src)
            tpv.at[i, col] = (q if pd.notna(q) else x["value_M"]) * 1e6
    tpv.to_csv(OUTPUT_DIR / "traded_player_values.csv", index=False)
    log(f"  written back into traded_player_values.csv: {int(hit.sum())} assets "
        f"(${got['value_M'].sum():,.2f}M); left without a value: {int((~v['asset_id'].isin(got.index)).sum())}")
    (OUTPUT_DIR / "rights_values_log.txt").write_text("\n".join(LOG), encoding="utf-8")
    log(f"\nwrote rights_values.csv and its log in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
