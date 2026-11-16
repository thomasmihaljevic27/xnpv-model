"""
groups_clustered.py - the back-test's group results with standard errors clustered by trade, and the outcome regressed on
the price by group (Thomas, 2026-11-15: "Yes, re-run them"; declared in 40_DOCS/Backtest_Protocol.md, "Standard errors
clustered by trade, and outcome on price by group", before it was built. Report only.)

WHY CLUSTER BY TRADE. Every trade sums to zero: in a two-team trade one club's net is the other's negative, so the two club
sides of a trade are not two independent observations. Ordinary standard errors would treat them as independent and come
out too small. Robust standard errors clustered by trade allow any dependence within a trade (the standard fix). The
earlier intervals resampled whole trades for the same reason; both are shown, so the reader sees they agree.

WHAT IT REPORTS (club sides of complete trades; $M at the 2025-26 cap; the model as decided, term left)
  1. each group's mean priced net and outcome net (WAR, Game Value), with its clustered standard error, 95% interval and
     p-value, beside the resampled interval (2,000 resamples of trades, seed 20261115)
  2. Thomas's regression on every club side:
        outcome net = a + b x priced net + c x G + d x (G x priced net)
     G is 1 for a side in the group. c: the group's outcome beyond what its price predicts (b x its priced net); a
     negative c means the group came out worse than even the price said. d: whether the models' verdict comes true
     more (d > 0) or less (d < 0) in the group. Clustered by trade.
  3. Holm's adjustment of each set of fourteen p-values (one outcome, one scope): a p-value is multiplied by the number
     of groups not yet passed, smallest first, which holds the chance of ANY false finding among the fourteen at 5%
  4. the joint regression (joint_regression.py's design: two-team trades, club A minus club B, no constant) with robust
     standard errors (rows are trades, so this is clustering by trade), and with the priced net added (Thomas's form)

THE GROUPS are joint_regression.py v1.2's thirteen characteristics, built here from the same files by the same rules
(GUARD: each group's side count equals the joint regression's trade count where it applies), plus the club that received
nothing recorded (the protocol's C5).

INPUTS: OUTPUT_DIR (the extended run)/backtest_cuts_all_sides.csv, backtest_cuts_more_gm_sides.csv,
        backtest_cuts_more_8_dumps.csv, backtest_sides.csv, backtest_sides_gv_adj.csv
OUTPUTS: OUTPUT_DIR/groups_clustered_log.txt, groups_clustered.csv
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv
from statsmodels.stats.multitest import multipletests

load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
SCRIPT_VERSION = "groups_clustered.py v1.0 (2026-11-15)"
N_BOOT, SEED = 2000, 20261115
DECLARED_END = "2022-03-28"
LOG, OUT = [], []
GROUPS = [("futures for players", "t_futures"), ("deadline buyer", "t_deadline_buyer"),
          ("other in-season buyer", "t_other_buyer"), ("rental", "t_rental"), ("retained salary", "t_retained"),
          ("main player 28 to 31", "t_age28"), ("main player 32 or over", "t_age32"), ("main player a defenceman", "t_def"),
          ("main player with a clause", "t_clause"), ("former top-15 pick below benchmark", "t_top15"),
          ("one asset for two or more", "t_single"), ("took a contract to clear cap", "t_dump"),
          ("sold under a new GM", "t_newgm"), ("received nothing recorded", "t_nothing")]
YS = [("priced", "net_M"), ("outcome, WAR", "out_net_M"), ("outcome, Game Value", "gv_net_M")]


def log(s=""):
    print(s)
    LOG.append(s)


def sides():
    """Every complete club side with its traits (joint_regression.py v1.2's rules) and its three nets."""
    s = pd.read_csv(OUTPUT_DIR / "backtest_cuts_all_sides.csv")
    key = ["trade_id", "club"]
    gm = pd.read_csv(OUTPUT_DIR / "backtest_cuts_more_gm_sides.csv")
    dumps = pd.read_csv(OUTPUT_DIR / "backtest_cuts_more_8_dumps.csv")
    s = s.merge(gm[key + ["new_gm_predecessor"]], on=key, how="left")
    s["new_gm_predecessor"] = s["new_gm_predecessor"].fillna(False).astype(bool)
    dump_trades, dumper = set(dumps["trade_id"]), set(zip(dumps["trade_id"], dumps["club"]))
    t = pd.DataFrame({"trade_id": s["trade_id"], "club": s["club"], "trade_date": s["trade_date"]})
    t["t_futures"] = s["g_futures"].astype(bool)
    t["t_deadline_buyer"] = s["g_buyer"].astype(bool) & (s["timing"] == "deadline window (14 days)")
    t["t_other_buyer"] = s["g_buyer"].astype(bool) & (s["timing"] == "rest of the regular season")
    t["t_rental"] = (s["cstatus"] == "final season, unrestricted at expiry") & s["during_regular_season"].astype(bool)
    t["t_retained"] = s["g_retained"].astype(bool)
    t["t_age28"] = s["age"].between(28, 32, inclusive="left")
    t["t_age32"] = s["age"] >= 32
    t["t_def"] = s["pos"] == "D"
    t["t_clause"] = s["g_clause"].astype(bool)
    t["t_top15"] = s["top15_below"].astype(bool)
    t["t_single"] = s["single_for_many"].astype(bool)
    t["t_dump"] = [(tr in dump_trades) and ((tr, c) not in dumper) for tr, c in zip(s["trade_id"], s["club"])]
    t["t_newgm"] = s["new_gm_predecessor"]
    t["t_nothing"] = s["g_nothing_back"].astype(bool)
    war = pd.read_csv(OUTPUT_DIR / "backtest_sides.csv")[key + ["net_M", "out_net_M"]]
    gv = pd.read_csv(OUTPUT_DIR / "backtest_sides_gv_adj.csv")[key + ["out_net_M"]].rename(columns={"out_net_M": "gv_net_M"})
    t = t.merge(war, on=key).merge(gv, on=key)
    assert len(t) == len(s)                                                       # GUARD: one row a side
    assert np.allclose(t.groupby("trade_id")["net_M"].sum(), 0, atol=1e-6)        # GUARD: every trade zero-sum
    return t


def clustered_mean(y, groups):
    """Mean of y with a standard error clustered on `groups` (an OLS of y on a constant)."""
    m = sm.OLS(y, np.ones((len(y), 1))).fit(cov_type="cluster", cov_kwds={"groups": groups})
    b, se = float(m.params[0]), float(m.bse[0])
    return b, se, b - 1.96 * se, b + 1.96 * se, float(m.pvalues[0])


def boot_mean(y, groups, rng):
    d = pd.DataFrame({"y": y, "g": groups})
    s_, c_ = d.groupby("g")["y"].sum().values, d.groupby("g")["y"].size().values
    i = rng.integers(0, len(s_), (N_BOOT, len(s_)))
    return np.percentile(s_[i].sum(1) / c_[i].sum(1), [2.5, 97.5])


def main():
    rng = np.random.default_rng(SEED)
    log(SCRIPT_VERSION)
    log(f"  reads {OUTPUT_DIR}")
    t = sides()
    scopes = [("DECLARED WINDOW (2017-07-01 to 2022-03-28), the primary scope", t["trade_date"] <= DECLARED_END),
              ("TRADES AFTER 2022-03-28 (the replication)", t["trade_date"] > DECLARED_END),
              ("ALL TRADES 2017-2026", pd.Series(True, index=t.index))]
    for scope, msk in scopes:
        d = t[msk]
        log(f"\n{'=' * 118}\n{scope}: {len(d)} club sides, {d['trade_id'].nunique()} trades")

        # ---- 1. group means: clustered standard errors beside the resampled interval -------------------------------------
        log("\n1. GROUP MEANS ($M per club side): mean [95% interval from clustered standard errors] p | the resampled interval")
        log(f"  {'group':<36}{'sides':>6}" + "".join(f"{lab:>44}" for lab, _ in YS))
        p_by = {y: [] for _, y in YS}
        for lab, g in GROUPS:
            x = d[d[g]]
            cells = []
            for ylab, y in YS:
                b, se, lo, hi, p = clustered_mean(x[y].to_numpy(float), x["trade_id"].to_numpy())
                blo, bhi = boot_mean(x[y].to_numpy(float), x["trade_id"].to_numpy(), rng)
                cells.append(f"{b:+.2f} [{lo:+.2f},{hi:+.2f}] p={p:.3f} | [{blo:+.2f},{bhi:+.2f}]")
                p_by[y].append(p)
                OUT.append({"scope": scope.split(" (")[0].split(",")[0], "part": "group mean", "group": lab, "outcome": ylab,
                            "n_sides": len(x), "n_trades": x["trade_id"].nunique(), "estimate": b, "se": se, "lo": lo, "hi": hi,
                            "p": p, "boot_lo": blo, "boot_hi": bhi})
            log(f"  {lab:<36}{len(x):>6}" + "".join(f"{c:>44}" for c in cells))
        log("  Holm-adjusted p-values (the chance of any false finding among the fourteen held at 5%):")
        for ylab, y in YS:
            adj = multipletests(p_by[y], method="holm")[1]
            passed = [GROUPS[i][0] for i in range(len(GROUPS)) if adj[i] < 0.05]
            log(f"    {ylab:<22} below 0.05 after adjustment: {len(passed)} of {len(GROUPS)}: {', '.join(passed) if passed else 'none'}")
            for i in range(len(GROUPS)):
                OUT.append({"scope": scope.split(" (")[0].split(",")[0], "part": "group mean, Holm", "group": GROUPS[i][0],
                            "outcome": ylab, "p": p_by[y][i], "p_holm": adj[i]})

        # ---- 2. outcome on price, by group ----------------------------------------------------------------------------------
        log("\n2. OUTCOME ON PRICE, BY GROUP: outcome net = a + b x priced net + c x group + d x group x priced net (clustered by trade)")
        base = sm.OLS(d["out_net_M"], sm.add_constant(d[["net_M"]])).fit(cov_type="cluster", cov_kwds={"groups": d["trade_id"]})
        log(f"  without groups (WAR): a {base.params['const']:+.3f}, b {base.params['net_M']:.3f} (se {base.bse['net_M']:.3f}): "
            f"the models' verdict comes true at {base.params['net_M']:.0%} on average")
        for ylab, y in YS[1:]:
            log(f"\n  outcome: {ylab}")
            log(f"  {'group':<36}{'sides':>6}{'c: beyond its price':>34}{'Holm p':>8}{'d: verdict differs':>30}{'b in the group (b + d)':>24}")
            cs, rows = [], []
            for lab, g in GROUPS:
                X = pd.DataFrame({"const": 1.0, "priced": d["net_M"], "G": d[g].astype(float), "GxP": d[g].astype(float) * d["net_M"]})
                m = sm.OLS(d[y], X).fit(cov_type="cluster", cov_kwds={"groups": d["trade_id"]})
                cs.append(float(m.pvalues["G"]))
                rows.append((lab, int(d[g].sum()), m))
            adj = multipletests(cs, method="holm")[1]
            for (lab, n, m), ph in zip(rows, adj):
                c, sc, d_, sd = m.params["G"], m.bse["G"], m.params["GxP"], m.bse["GxP"]
                log(f"  {lab:<36}{n:>6}{f'{c:+.2f} [{c - 1.96 * sc:+.2f},{c + 1.96 * sc:+.2f}] p={m.pvalues["G"]:.3f}':>34}{ph:>8.3f}"
                    f"{f'{d_:+.2f} [{d_ - 1.96 * sd:+.2f},{d_ + 1.96 * sd:+.2f}]':>30}{m.params['priced'] + d_:>24.2f}")
                OUT.append({"scope": scope.split(" (")[0].split(",")[0], "part": "outcome on price", "group": lab, "outcome": ylab,
                            "n_sides": n, "c": c, "c_se": sc, "c_p": m.pvalues["G"], "c_p_holm": ph, "d": d_, "d_se": sd,
                            "d_p": m.pvalues["GxP"], "b": m.params["priced"]})

        # ---- 4. the joint regression with robust errors, and with the price added -----------------------------------------------
        n = d.groupby("trade_id")["club"].transform("size")
        two = d[n == 2].sort_values(["trade_id", "club"])
        A = two.groupby("trade_id").nth(0).set_index("trade_id")
        B = two.groupby("trade_id").nth(1).set_index("trade_id")
        cols = [g for _, g in GROUPS[:-1]]                                              # the joint regression's thirteen
        X = pd.DataFrame({g: A[g].astype(int) - B[g].astype(int) for g in cols}, index=A.index)
        X = X.loc[:, (X != 0).sum() >= 5]
        nm = dict((g, l) for l, g in GROUPS)
        log(f"\n4. THE JOINT REGRESSION, {len(X)} two-team trades, robust standard errors (each row a trade); then with the priced net added")
        log(f"  {'characteristic':<36}" + "".join(f"{lab:>30}" for lab, _ in YS) + f"{'WAR, price held':>30}{'Game Value, price held':>30}")
        fits = {y: sm.OLS(A[y], X).fit(cov_type="HC1") for _, y in YS}
        Xp = X.assign(priced=A["net_M"])
        fitp = {y: sm.OLS(A[y], Xp).fit(cov_type="HC1") for _, y in YS[1:]}
        for g in X.columns:
            cells = []
            for _, y in YS:
                m = fits[y]
                cells.append(f"{m.params[g]:+.2f}{'*' if m.pvalues[g] < 0.05 else ' '} (se {m.bse[g]:.2f}) p={m.pvalues[g]:.3f}")
            for _, y in YS[1:]:
                m = fitp[y]
                cells.append(f"{m.params[g]:+.2f}{'*' if m.pvalues[g] < 0.05 else ' '} (se {m.bse[g]:.2f}) p={m.pvalues[g]:.3f}")
            log(f"  {nm[g]:<36}" + "".join(f"{c:>30}" for c in cells))
            for (ylab, y), m in list(zip(YS, [fits[y] for _, y in YS])) + [((f"{l}, price held", y), fitp[y]) for l, y in YS[1:]]:
                OUT.append({"scope": scope.split(" (")[0].split(",")[0], "part": "joint", "group": nm[g], "outcome": ylab,
                            "estimate": m.params[g], "se": m.bse[g], "p": m.pvalues[g]})
        log(f"  the priced net, with the characteristics held: WAR {fitp['out_net_M'].params['priced']:.3f} (se {fitp['out_net_M'].bse['priced']:.3f}); "
            f"Game Value {fitp['gv_net_M'].params['priced']:.3f} (se {fitp['gv_net_M'].bse['priced']:.3f})")
    pd.DataFrame(OUT).to_csv(OUTPUT_DIR / "groups_clustered.csv", index=False)
    (OUTPUT_DIR / "groups_clustered_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
