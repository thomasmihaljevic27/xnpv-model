"""
clause_checks.py - why do clubs overpay for players with a no-trade or no-move clause? (Thomas, 2026-11-17: "Yes, run
them"; declared in 40_DOCS/Backtest_Protocol.md before it was built. Report only.)

THE FINDING. With the age bands and the other groups held, the club acquiring a main player with a clause is priced
$1.62M a side below the models' value and comes out $1.48M behind (joint regression, all trades). Three explanations:
  1  a marker of a free-agent contract: the joint regression with two more club differences, the main player's contract
     signed as an unrestricted free agent and his cap hit ($M)
  2  reputation: for main players at $3M+, his 50/30/20 trailing WAR total less the forecast's expected first-season WAR;
     clause against no clause, and the priced net on that gap
  3  the season: the clause group's means, off-season against in-season, clustered by trade

BAKED-IN ASSUMPTIONS
  - main player: the player-model asset a club received with the highest ledger cap hit (backtest_cuts.py's rule); his
    NHL id and cap hit from prospect_values.csv's inventory
  - signing status: the contract running at the trade's page and signed on or before the trade date (the season spine,
    as backtest_cuts.py), PuckPedia's signing_status; "UFA", "UFA no QO" and Group 6 count as signed as a free agent;
    a contract the spine does not hold (the 2017 page) counts 0 and is counted
  - the forecast: 30_OUTPUT/xnpv1_forecasts.csv at the trade's page, h = 0, the career key from his WAR name
    (player_season_table.career_key); the trailing total is backtest_assets.trailing_war (the harness's 50/30/20)
  - standard errors: clustered by trade for club sides; robust (each row a trade) for the joint regression

INPUTS: OUTPUT_DIR/_extended_run/ (sides, assets, groups as groups_clustered.sides()), prospect_values.csv,
        contract_season_spine.csv, WAR_with_age.csv, xnpv1_forecasts.csv; the PuckPedia contract export
OUTPUTS: OUTPUT_DIR/clause_checks_log.txt, clause_checks.csv
"""
import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
load_dotenv()
import contract_source as CS                         # noqa: E402
import player_season_table as PST                    # noqa: E402

OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
EXT = OUTPUT_DIR / "_extended_run"
SCRIPT_VERSION = "clause_checks.py v1.3 (2026-11-19)"   # v1.3: the guard reads joint_regression.csv instead of a pinned -1.62; v1.2: each added term alone   # v1.1: the main players after 2022 found (the extended inventory)
DECLARED_END = "2022-03-28"
LOG, OUT = [], []


def log(s=""):
    print(s)
    LOG.append(s)


def load_sides():
    spec = importlib.util.spec_from_file_location("groups_clustered", Path(__file__).resolve().parent / "groups_clustered.py")
    GC = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(GC)
    GC.OUTPUT_DIR = EXT
    return GC, GC.sides()


def main_players():
    """Each club side's main player: NHL id, cap hit, signed as a free agent, trailing total, expected first-season WAR."""
    a = pd.read_csv(EXT / "backtest_assets.csv")
    pv = pd.read_csv(EXT / "prospect_values.csv", low_memory=False)[["asset_id", "nhl_id", "cap_hit"]].drop_duplicates("asset_id")
    # v1.1: the extended run's inventory above (v1.0 read the declared window's, so no main player after 2022 was found)
    pl = a[(a["asset_type"] == "player") & a["source"].str.startswith(("player model", "buried"))].merge(pv, on="asset_id", how="left")
    m = pl.sort_values("cap_hit", ascending=False, kind="stable").drop_duplicates(["trade_id", "acquiring_team"]).copy()
    m["date"] = pd.to_datetime(m["trade_date"])
    # signing status of the contract running at the page
    ss = pd.read_csv(OUTPUT_DIR / "contract_season_spine.csv", low_memory=False, usecols=["nhl_id", "season_start", "contract_id", "pp_signing_date"])
    ss["signed"] = pd.to_datetime(ss["pp_signing_date"])
    by = {k: g for k, g in ss.groupby(["nhl_id", "season_start"])}
    c, _ = CS.load_contracts()
    st = c.drop_duplicates("contract_id").set_index("contract_id")["signing_status"]
    ufa, known = [], []
    for r in m.itertuples():
        g = by.get((r.nhl_id, int(r.valuation_page))) if pd.notna(r.nhl_id) else None
        if g is None:
            ufa.append(0); known.append(False); continue
        g = g[g["signed"] <= r.date] if (g["signed"] <= r.date).any() else g
        s_ = str(st.get(int(g.sort_values("signed").iloc[0]["contract_id"]), ""))
        ufa.append(int(s_.startswith("UFA"))); known.append(s_ not in ("", "nan"))
    m["ufa_signed"], m["status_known"] = ufa, known
    # expected first-season WAR from the forecast at the page
    w = pd.read_csv(OUTPUT_DIR / "WAR_with_age.csv", usecols=["Player", "nhl_id"]).dropna().drop_duplicates("nhl_id")
    ck = w.set_index("nhl_id")["Player"].map(PST.career_key)
    fc = pd.read_csv(OUTPUT_DIR / "xnpv1_forecasts.csv", usecols=["career_key", "page", "h", "p_play", "war_if_plays"])
    fc = fc[fc["h"] == 0].set_index(["career_key", "page"])
    exp = []
    for r in m.itertuples():
        k = (ck.get(r.nhl_id), int(r.valuation_page)) if pd.notna(r.nhl_id) else None
        exp.append(float(fc.at[k, "p_play"] * fc.at[k, "war_if_plays"]) if k is not None and k in fc.index else np.nan)
    m["expected_war"] = exp
    m["rep_gap"] = m["trailing_war"] - m["expected_war"]
    return m.rename(columns={"acquiring_team": "club"})[["trade_id", "club", "name", "nhl_id", "cap_hit", "ufa_signed",
                                                           "status_known", "trailing_war", "expected_war", "rep_gap"]]


def main():
    log(SCRIPT_VERSION)
    log(f"  reads {EXT}")
    GC, t = load_sides()
    mp = main_players()
    t = t.merge(mp, on=["trade_id", "club"], how="left")
    t["ufa_signed"] = t["ufa_signed"].fillna(0).astype(int)
    t["cap_M"] = t["cap_hit"].fillna(0) / 1e6
    has = t["name"].notna()
    log(f"  club sides {len(t)}; with a main player {int(has.sum())}; signing status known {int(t['status_known'].fillna(False).astype(bool).sum())}; "
        f"signed as a free agent {int(t['ufa_signed'].sum())}; with a clause {int(t['t_clause'].sum())}, of them signed as a free agent "
        f"{int((t['t_clause'] & (t['ufa_signed'] == 1)).sum())}")

    # ---- 1. the joint regression with the free-agent signing and the cap hit -----------------------------------------------
    cols = [g for _, g in GC.GROUPS[:-1]]
    n = t.groupby("trade_id")["club"].transform("size")
    two = t[n == 2].sort_values(["trade_id", "club"])
    A = two.groupby("trade_id").nth(0).set_index("trade_id")
    B = two.groupby("trade_id").nth(1).set_index("trade_id")
    X = pd.DataFrame({g: A[g].astype(int) - B[g].astype(int) for g in cols}, index=A.index)
    X["ufa_signed"] = A["ufa_signed"] - B["ufa_signed"]
    X["cap_M"] = A["cap_M"] - B["cap_M"]
    dates = A["trade_date"]
    log("\n1. A MARKER OF A FREE-AGENT CONTRACT: the joint regression, the clause coefficient before and after adding the main "
        "player's free-agent signing and cap hit ($M a side; robust standard errors, each row a trade)")
    log(f"  {'scope':<18}{'outcome':<22}{'clause, before':>24}{'clause, after':>24}{'signed as free agent':>26}{'cap hit, per $1M':>24}")
    for scope, msk in (("all trades", np.ones(len(X), bool)), ("declared window", (dates <= DECLARED_END).values)):
        for ylab, y in (("priced", "net_M"), ("outcome, WAR", "out_net_M"), ("outcome, Game Value", "gv_net_M")):
            Xb = X.loc[msk, cols]
            Xb = Xb.loc[:, (Xb != 0).sum() >= 5]
            m0 = sm.OLS(A.loc[msk, y], Xb).fit(cov_type="HC1")
            m1 = sm.OLS(A.loc[msk, y], pd.concat([Xb, X.loc[msk, ["ufa_signed", "cap_M"]]], axis=1)).fit(cov_type="HC1")
            f = lambda m, k: f"{m.params[k]:+.2f} ({m.bse[k]:.2f}) p={m.pvalues[k]:.3f}"   # noqa: E731
            log(f"  {scope:<18}{ylab:<22}{f(m0, 't_clause'):>24}{f(m1, 't_clause'):>24}{f(m1, 'ufa_signed'):>26}{f(m1, 'cap_M'):>24}")
            # each added term alone (CLAUDE.md: score each part of a multi-part change alone)
            for one in ("ufa_signed", "cap_M"):
                m2 = sm.OLS(A.loc[msk, y], pd.concat([Xb, X.loc[msk, [one]]], axis=1)).fit(cov_type="HC1")
                log(f"  {'':<18}{'  with ' + ('the free-agent signing' if one == 'ufa_signed' else 'the cap hit') + ' alone':<46}{f(m2, 't_clause'):>24}{f(m2, one):>26}")
                OUT.append({"check": "1", "scope": scope, "outcome": ylab, "term": "t_clause", "model": f"with {one} alone",
                            "coef": m2.params["t_clause"], "se": m2.bse["t_clause"], "p": m2.pvalues["t_clause"],
                            "added": m2.params[one], "added_p": m2.pvalues[one]})
            for k in ("t_clause", "ufa_signed", "cap_M"):
                OUT.append({"check": "1", "scope": scope, "outcome": ylab, "term": k, "model": "with signing and cap hit",
                            "coef": m1.params[k], "se": m1.bse[k], "p": m1.pvalues[k]})
            OUT.append({"check": "1", "scope": scope, "outcome": ylab, "term": "t_clause", "model": "before",
                        "coef": m0.params["t_clause"], "se": m0.bse["t_clause"], "p": m0.pvalues["t_clause"]})
    # GUARD: the "before" fit is joint_regression.py's (all trades, priced: +-1.62 on the clause)
    ref = [o for o in OUT if o["scope"] == "all trades" and o["outcome"] == "priced" and o["model"] == "before"][0]["coef"]
    # v1.3 (2026-11-19): joint_regression.csv's figure as written (it moved with the clause fill and the sellers for just
    # picks and prospects, protocol 2026-11-19); was a pinned -1.62
    jr = pd.read_csv(EXT / "joint_regression.csv")
    want = float(jr[(jr["scope"] == "ALL TRADES 2017-2026") & (jr["trait"] == "main player with a clause") & (jr["outcome"] == "net_M")]["together"].iloc[0])
    assert abs(ref - want) < 1e-6, (ref, want)
    log(f"  check: the 'before' fit gives the joint regression's clause coefficient back (all trades, priced {want:+.2f}) (PASS)")

    # ---- 2. reputation ------------------------------------------------------------------------------------------------------
    big = t[has & (t["cap_hit"] >= 3e6) & t["rep_gap"].notna()].copy()
    log(f"\n2. REPUTATION: main players at $3M+ with a trailing total and a forecast ({len(big)} club sides)")
    log("  trailing 50/30/20 WAR total less the forecast's expected first-season WAR (the record above the forecast), mean "
        "[95% interval], clustered by trade:")
    for scope, msk in (("all trades", pd.Series(True, index=big.index)), ("declared window", big["trade_date"] <= DECLARED_END)):
        cells = []
        for lab, g in (("clause", big[msk & big["t_clause"]]), ("no clause", big[msk & ~big["t_clause"]])):
            m = sm.OLS(g["rep_gap"], np.ones(len(g))).fit(cov_type="cluster", cov_kwds={"groups": g["trade_id"]})
            cells.append(f"{lab} {m.params.iloc[0]:+.3f} [{m.conf_int().iloc[0, 0]:+.3f}, {m.conf_int().iloc[0, 1]:+.3f}] (n={len(g)})")
            OUT.append({"check": "2", "scope": scope, "term": f"gap, {lab}", "coef": m.params.iloc[0], "se": m.bse.iloc[0], "n": len(g)})
        d = big[msk]
        X2 = sm.add_constant(pd.DataFrame({"gap": d["rep_gap"], "clause": d["t_clause"].astype(float)}))
        m = sm.OLS(d["rep_gap"], sm.add_constant(d["t_clause"].astype(float))).fit(cov_type="cluster", cov_kwds={"groups": d["trade_id"]})
        log(f"  {scope:<18}{'; '.join(cells)}; difference {m.params.iloc[1]:+.3f} (p={m.pvalues.iloc[1]:.3f})")
        for lab, Xm in (("priced net on the gap", sm.add_constant(d[["rep_gap"]])), ("the same, the clause held", X2)):
            mm = sm.OLS(d["net_M"], Xm).fit(cov_type="cluster", cov_kwds={"groups": d["trade_id"]})
            extra = f"; clause {mm.params['clause']:+.2f} (p={mm.pvalues['clause']:.3f})" if "clause" in Xm else ""
            log(f"    {lab:<28} gap {mm.params['rep_gap' if 'rep_gap' in Xm else 'gap']:+.2f} $M per WAR "
                f"(p={mm.pvalues['rep_gap' if 'rep_gap' in Xm else 'gap']:.3f}){extra}")
            OUT.append({"check": "2", "scope": scope, "term": lab, "coef": mm.params["rep_gap" if "rep_gap" in Xm else "gap"],
                        "p": mm.pvalues["rep_gap" if "rep_gap" in Xm else "gap"],
                        "clause": mm.params.get("clause", np.nan), "clause_p": mm.pvalues.get("clause", np.nan)})

    # ---- 3. the season -------------------------------------------------------------------------------------------------------
    log("\n3. THE SEASON: the clause group's means by timing ($M a side, standard errors clustered by trade)")
    log(f"  {'scope':<18}{'timing':<14}{'sides':>6}{'priced':>24}{'outcome, WAR':>24}{'outcome, Game Value':>24}")
    for scope, msk in (("all trades", pd.Series(True, index=t.index)), ("declared window", t["trade_date"] <= DECLARED_END)):
        for lab, tm in (("off-season", ~t["during_regular_season"] if "during_regular_season" in t else None),):
            pass
        side_s = pd.read_csv(EXT / "backtest_cuts_all_sides.csv")[["trade_id", "club", "during_regular_season"]]
        tt = t.merge(side_s, on=["trade_id", "club"])
        for lab, tm in (("off-season", ~tt["during_regular_season"].astype(bool)), ("in-season", tt["during_regular_season"].astype(bool))):
            g = tt[(tt["trade_date"] <= DECLARED_END if scope == "declared window" else True) & tt["t_clause"] & tm]
            cells = []
            for y in ("net_M", "out_net_M", "gv_net_M"):
                m = sm.OLS(g[y], np.ones(len(g))).fit(cov_type="cluster", cov_kwds={"groups": g["trade_id"]})
                cells.append(f"{m.params.iloc[0]:+.2f} ({m.bse.iloc[0]:.2f}) p={m.pvalues.iloc[0]:.3f}")
                OUT.append({"check": "3", "scope": scope, "term": lab, "outcome": y, "coef": m.params.iloc[0], "se": m.bse.iloc[0],
                            "p": m.pvalues.iloc[0], "n": len(g)})
            log(f"  {scope:<18}{lab:<14}{len(g):>6}" + "".join(f"{c:>24}" for c in cells))
    pd.DataFrame(OUT).to_csv(OUTPUT_DIR / "clause_checks.csv", index=False)
    (OUTPUT_DIR / "clause_checks_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
