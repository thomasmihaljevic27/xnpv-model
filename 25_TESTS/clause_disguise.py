"""
clause_disguise.py - is the clause finding another finding in disguise? (Thomas, 2026-11-19: "What are the chances that
the clause finding is a different finding in disguise? ... clause players are players who are of a higher reputation in
the league, they may carry higher cap hits, they may be more likely to become cap dumps"; "Maybe a clause is indicitive of
a reputation, so teams overpay for reputation and that appears in the form of a trade clause". Declared in
40_DOCS/Backtest_Protocol.md before it was built. Report only.)

ROWS AND DESIGN: one_regression.frame() (v2.1): the 556 two-team trades of the declared window, both rules, each trade once,
the first club's value on the two clubs' differences, no constant, robust standard errors.
EACH PLAYER RECEIVED, the added measures:
  cap hit        $M, prospect_values' (who_overpaid's cap_M)
  cost           the present value of the cap hit over the seasons left, $M at the 2025-26 cap: who_overpaid.build's formula
                 (cap hit x 2025-26 cap / page cap x (share of the trade season left + sum over later seasons of 1/1.03^k));
                 seasons left by who_overpaid's rule (the spine at the page), on the 2017 page with no spine row
                 page_2017_values' contract_last_season. GUARD: the main player's equals who_overpaid's cost where it had one.
  career WAR     the sum of his WAR over every season before the page (backtest.seasons_for, goalies on the goalie table)
  best season    his highest single-season WAR before the page; no season: 0 for both
  Main player rule: the main player's. Any player rule: cap hit and cost, the total over the players received; career WAR and
  best season, cap-weighted averages (as the other measures).
REPORTS: 1 the profile of clubs whose main player has a clause against those whose main player has none; 2 the regression
with the cap hit, the cost, both; 4 with career WAR, best season, both, both and the cap hit; 3 without the trades where a
club took a contract to clear cap. In each fit the clause, age 28 to 31 and added coefficients. GUARD: the fit with nothing
added reproduces one_regression.csv.

OUTPUTS: OUTPUT_DIR/clause_disguise_log.txt, clause_disguise.csv
"""
import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
EXT = OUTPUT_DIR / "_extended_run"
ROOT = Path(__file__).resolve().parent.parent
SCRIPT_VERSION = "clause_disguise.py v1.1 (2026-11-19)"   # v1.1: on one_regression v2.2 (the goalie indicator); no code change
LOG, OUT = [], []


def log(s=""):
    print(s)
    LOG.append(s)


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def player_measures(f, WO):
    """Cap hit, cost, career WAR and best season for each player received (f's rows)."""
    sys.path.insert(0, str(ROOT / "20_CODE"))
    import backtest as BT
    a = pd.read_csv(EXT / "backtest_assets.csv").drop_duplicates("asset_id").set_index("asset_id")
    pv = pd.read_csv(EXT / "prospect_values.csv", low_memory=False).drop_duplicates("asset_id").set_index("asset_id")["nhl_id"]
    tpv = pd.read_csv(EXT / "traded_player_values.csv").drop_duplicates("asset_id").set_index("asset_id")["nhl_id"]
    p17 = pd.read_csv(EXT / "page_2017_values.csv").drop_duplicates("asset_id").set_index("asset_id")
    p = f[["trade_id", "club", "asset_id", "cap_hit"]].copy()
    page = p["asset_id"].map(a["valuation_page"]).astype(int)
    date = pd.to_datetime(p["asset_id"].map(a["trade_date"]))
    share = p["asset_id"].map(a["season_share"]).fillna(1.0)
    gk = p["asset_id"].map(a["pos"]) == "G"
    name = p["asset_id"].map(a["name"])
    spell = p["asset_id"].map(a["war_spelling"]).fillna(p["asset_id"].map(p17["war_name"])).fillna(name)
    nid = p["asset_id"].map(pv).fillna(p["asset_id"].map(tpv)).fillna(p["asset_id"].map(p17["nhl_id"]))
    # seasons left: who_overpaid.build's rule (the contract running at the page, signed on or before the trade date)
    ss = pd.read_csv(OUTPUT_DIR / "contract_season_spine.csv", low_memory=False,
                     usecols=["nhl_id", "season_start", "pp_signed_end", "pp_signing_date"])
    ss["signed"] = pd.to_datetime(ss["pp_signing_date"])
    by = {k: g for k, g in ss.groupby(["nhl_id", "season_start"])}
    left = []
    for i, pg, d, aid in zip(nid, page, date, p["asset_id"]):
        g = by.get((i, pg)) if pd.notna(i) else None
        if g is None:
            cls = p17["contract_last_season"].get(aid) if pg == 2017 else None
            left.append(max(int(cls) - 2017 + 1, 1) if cls is not None and pd.notna(cls) else np.nan)
            continue
        g = g[g["signed"] <= d] if (g["signed"] <= d).any() else g
        left.append(max(int(g.sort_values("signed").iloc[0]["pp_signed_end"]) - pg + 1, 1))
    p["left"] = left
    p["cap_M"] = p["cap_hit"].fillna(0) / 1e6
    p["cost"] = [np.nan if pd.isna(l) or pd.isna(c) else
                 c * WO.CAP_NOW / WO.CAP[int(pg)] * (s + sum(1 / 1.03 ** k for k in range(1, int(l)))) / 1e6
                 for l, c, pg, s in zip(p["left"], p["cap_hit"], page, share)]
    car, best = [], []
    for sp, g_, nm, pg in zip(spell, gk, name, page):
        s = BT.seasons_for(sp, bool(g_), nm)
        s = s[s.index < pg] if len(s) else s
        car.append(float(s["WAR"].sum()) if len(s) else 0.0)
        best.append(float(s["WAR"].max()) if len(s) else 0.0)
    p["career_war"], p["best_war"] = car, best
    return p


def main():
    log(SCRIPT_VERSION)
    OR = load("one_regression")
    OR.LOG = LOG
    A, B, t, f, key, WO = OR.frame()
    p = player_measures(f, WO)
    # main player = highest cap hit received (who_overpaid's rule); GUARD: the same asset as who_overpaid's
    main = p.sort_values("cap_hit", ascending=False, kind="stable").drop_duplicates(key).set_index(key)
    ti = t.set_index(key)
    rec = ti["recv"] == 1
    assert (main["asset_id"].reindex(ti.index[rec]).values == ti.loc[rec, "asset_id"].values).all(), "main asset"
    tc = ti["cost"].where(rec)
    mc = main["cost"].reindex(ti.index)
    both = tc.notna() & mc.notna()
    assert np.allclose(tc[both], mc[both]), "cost"
    log(f"  check: the main player's cost equals who_overpaid's on all {int(both.sum())} sides that had one (PASS); "
        f"cost added for {int((rec & tc.isna() & mc.notna()).sum())} more, unknown for {int((rec & mc.isna()).sum())}")
    w = p.assign(wc=p["cap_hit"].fillna(0))
    agg = w.groupby(key).agg(cap=("cap_M", "sum"), cost=("cost", lambda x: x.sum(min_count=1)), wsum=("wc", "sum"))
    for c in ("career_war", "best_war"):
        num = (w["wc"] * w[c]).groupby([w["trade_id"], w["club"]]).sum()
        mean = w.groupby(key)[c].mean()
        agg[c] = np.where(agg["wsum"] > 0, num / agg["wsum"].where(agg["wsum"] > 0, 1), mean)
    extra = {"main player rule": {"cap": main["cap_M"], "cost": main["cost"], "career": main["career_war"], "best": main["best_war"]},
             "any player rule": {"cap": agg["cap"], "cost": agg["cost"], "career": agg["career_war"], "best": agg["best_war"]}}
    for rule, d in extra.items():
        tag = "m_" if rule.startswith("main") else "a_"
        for k, s in d.items():
            for X in (A, B):
                X[tag + k] = [s.get((tid, c), np.nan) for tid, c in zip(X.index, X["club"])]
                X[tag + k] = np.where(X["recv"] == 1, X[tag + k], 0.0)
    # trades where a club received a player whose cost is unknown are left out of the cost fits only
    cost_ok = ~(((A["recv"] == 1) & pd.isna(A["m_cost"])) | ((B["recv"] == 1) & pd.isna(B["m_cost"])))

    # ---- 1 profile ----
    sides = pd.concat([A.reset_index(), B.reset_index()])
    sides = sides[sides["recv"] == 1]
    log(f"\n1. PROFILE, main player rule: {len(sides)} clubs that received a player, 2017-22")
    prof = [("cap hit, $M", "m_cap"), ("cost over the seasons left, $M", "m_cost"), ("age", "age"), ("seasons left", "left"),
            ("recent WAR (50/30/20)", "trailing_war"), ("record above the forecast", "rep_gap"), ("career WAR", "m_career"),
            ("best season WAR", "m_best"), ("signed as an unrestricted free agent", "ufa"), ("former top-15 pick", "top15"),
            ("took the contract to clear cap", "t_dump"), ("higher in the standings, deadline", "t_deadline_buyer")]
    cl = sides["main_clause"] == 1
    log(f"  {'':<40}{'clause':>12}{'no clause':>12}   (clubs {int(cl.sum())} and {int((~cl).sum())})")
    for lab, c in prof:
        v = pd.to_numeric(sides[c], errors="coerce")
        log(f"  {lab:<40}{v[cl].mean():>12.2f}{v[~cl].mean():>12.2f}")
        OUT.append({"part": "profile", "term": lab, "clause": v[cl].mean(), "no_clause": v[~cl].mean()})

    # ---- 2, 3, 4 the fits ----
    fits = [("as in the document", [], None), ("+ cap hit", ["cap"], None), ("+ cost", ["cost"], "cost"),
            ("+ cap hit and cost", ["cap", "cost"], "cost"), ("+ career WAR", ["career"], None), ("+ best season", ["best"], None),
            ("+ career WAR and best season", ["career", "best"], None), ("+ career, best season and cap hit", ["career", "best", "cap"], None),
            ("without the cap-dump trades", [], "nodump")]
    ref = pd.read_csv(OUTPUT_DIR / "one_regression.csv")
    for rule in OR.P5:
        tag = "m_" if rule.startswith("main") else "a_"
        base = [c for c in OR.P5[rule] if c not in OR.DUP[rule] and c != OR.BELOW[rule]] + OR.PC[rule] + ["recv"]
        cont = {"trailing_war", "rep_gap", "gp_share_last", "avg_war", "avg_gap", "avg_gs"}
        clause_c = OR.PC[rule][3]
        age_c = OR.PC[rule][0]
        log(f"\n2-4. {rule}: coefficient (robust se) p, trade-day grade | realized WAR")
        for lab, add, rows in fits:
            if rows == "cost":
                Ar, Br = A[cost_ok], B[cost_ok]
            elif rows == "nodump":
                nd = (A["t_dump"] == 0) & (B["t_dump"] == 0)
                Ar, Br = A[nd], B[nd]
            else:
                Ar, Br = A, B
            cols = base + [tag + k for k in add]
            fl = set(cols) - cont - {tag + k for k in add}
            fs, keep = OR.joint(Ar, Br, cols, fl)
            if lab == "as in the document":                                   # GUARD: one_regression's figures
                r = ref[(ref["rule"] == rule) & (ref["col"] == clause_c)].set_index("outcome")["estimate"]
                assert abs(fs["net_M"].params[clause_c] - r["trade-day grade"]) < 1e-9, "base fit"
            terms = [("clause", clause_c), ("aged 28 to 31", age_c)] + [(k, tag + k) for k in add]
            parts = []
            for nm, c in terms:
                if c not in keep:
                    continue
                cells = []
                for y in ("net_M", "out_net_M"):
                    m = fs[y]
                    cells.append(f"{m.params[c]:+.2f} ({m.bse[c]:.2f}) p={m.pvalues[c]:.3f}")
                    OUT.append({"part": lab, "rule": rule, "term": nm, "outcome": y, "n_trades": int(m.nobs),
                                "estimate": m.params[c], "se": m.bse[c], "p": m.pvalues[c]})
                parts.append(f"{nm}: {cells[0]} | {cells[1]}")
            log(f"  {lab:<36} ({int(fs['net_M'].nobs)} trades)")
            for s_ in parts:
                log(f"      {s_}")
    log("  check: the fit with nothing added reproduces one_regression.csv's clause coefficient, both rules (PASS)")
    pd.DataFrame(OUT).to_csv(OUTPUT_DIR / "clause_disguise.csv", index=False)
    (OUTPUT_DIR / "clause_disguise_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
