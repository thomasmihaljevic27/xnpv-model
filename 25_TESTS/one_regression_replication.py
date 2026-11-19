"""
one_regression_replication.py - the findings document's one regression on the trades after 2022 (Thomas, 2026-11-19: "I
guess run the regression"; the replication he chose on 2026-11-18 as the guard against chance findings). Declared in
40_DOCS/Backtest_Protocol.md before it was built. Report only.

ROWS: one_regression.frame() (v2.2) builds every club side of every trade (t, all trades to 2026-03-13, facts filled by
facts_fill.py). Its own fit takes the two-team trades to 2022-03-28. Here the same selection code takes the two-team
trades dated AFTER 2022-03-28: sides sorted by (trade_id, club), the first club A and the second B, a trade left out when
either side's main player has an unknown characteristic (one_regression's rule).
DESIGN: one_regression's: the same terms under each rule (P5 less the duplicates and the below-average top-15 term, the
12 player characteristics, received a player), the first club's value on A minus B, no constant, HC1 standard errors, a
yes-or-no difference non-zero in fewer than five trades dropped. Four outcomes.
GUARD: the same selection and fit on the declared window reproduces one_regression.csv on every term, outcome, estimate
and p-value, both rules (so the only change is the dates).
READING (declared): a declared-window finding replicates in full when its trade-day grade and realized WAR after 2022 both
have the same sign with p < 0.05; on trade day only when only the trade-day grade does. These trades' realized values are
mostly the models' re-valuation at 2026-27, so the trade-day grade is the firm column.

OUTPUTS: OUTPUT_DIR/one_regression_replication_log.txt, one_regression_replication.csv
"""
import importlib.util
import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
SCRIPT_VERSION = "one_regression_replication.py v1.0 (2026-11-19)"
CONT = {"trailing_war", "rep_gap", "gp_share_last", "avg_war", "avg_gap", "avg_gs"}   # the continuous terms (as one_regression)
FINDINGS = {"main player rule": ["main_clause", "age28", "defence"], "any player rule": ["any_clause"]}   # the document's
LOG, OUT = [], []


def log(s=""):
    print(s)
    LOG.append(s)


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def pick(t, key, after):
    """one_regression.frame()'s selection, on one side of 2022-03-28 (after=False: the declared window)."""
    n = t.groupby("trade_id")["club"].transform("size")
    d = t["trade_date"] > "2022-03-28" if after else t["trade_date"] <= "2022-03-28"
    two = t[(n == 2) & d].sort_values(key)
    A = two.groupby("trade_id").nth(0).set_index("trade_id")
    B = two.groupby("trade_id").nth(1).set_index("trade_id")
    drop = A["unknown"].astype(bool) | B["unknown"].astype(bool)
    return A[~drop], B[~drop], int(drop.sum())


def main():
    log(SCRIPT_VERSION)
    OR = load("one_regression")
    OR.LOG = LOG
    log(f"  on {OR.SCRIPT_VERSION}")
    A0, B0, t, f, key, WO = OR.frame()
    ref = pd.read_csv(OUTPUT_DIR / "one_regression.csv")
    Ad, Bd, _ = pick(t, key, after=False)
    assert list(Ad.index) == list(A0.index), "declared-window rows"
    Aa, Ba, nd = pick(t, key, after=True)
    log(f"  after 2022-03-28: {len(Aa)} two-team trades in the fit ({nd} left out for an unknown characteristic); "
        f"{t.loc[t['trade_date'] > '2022-03-28', 'trade_date'].min()} to {t['trade_date'].max()}")
    log(f"  clubs that received a player: {int(Aa['recv'].sum() + Ba['recv'].sum())} of {2 * len(Aa)}")
    res = {}
    for rule in OR.P5:
        cols = [c for c in OR.P5[rule] if c not in OR.DUP[rule] and c != OR.BELOW[rule]] + OR.PC[rule] + ["recv"]
        fl = set(cols) - CONT
        fd, kd = OR.joint(Ad, Bd, cols, fl)
        r = ref[ref["rule"] == rule]
        for lab, y in OR.YS:                                               # GUARD: the declared window as recorded
            rr = r[r["outcome"] == lab].set_index("col")
            assert list(rr.index) == kd, (rule, "terms")
            assert np.allclose(fd[y].params[kd].values, rr["estimate"].values, atol=1e-9), (rule, y)
            assert np.allclose(fd[y].pvalues[kd].values, rr["p"].values, atol=1e-12), (rule, y)
        res[rule] = (fd, kd) + OR.joint(Aa, Ba, cols, fl)
    log("  check: the same code on the declared window reproduces one_regression.csv on every term, outcome, estimate and "
        "p-value, both rules (PASS)")

    log("\nTHE ONE REGRESSION, TRADES AFTER 2022-03-28 ($M a club, positive = the club gained; robust standard errors)")
    log("  beside: the declared window's trade-day | realized WAR. F = a finding (trade-day and realized WAR both p < 0.05,"
        " same sign); T = trade-day only; g, s as before")
    for rule in OR.P5:
        fd, kd, fa, ka = res[rule]
        log(f"\n  {rule}  ({int(fa['net_M'].nobs)} trades)")
        log(f"  {'term':<42}{'2017-22: trade-day | realized':>34}   {'after 2022: trade-day':>26}{'realized, WAR':>24}"
            f"{'Game Value':>20}{'seasons played':>20}  after 2022")
        for k in kd:
            dl = f"{fd['net_M'].params[k]:+.2f} p={fd['net_M'].pvalues[k]:.3f} | {fd['out_net_M'].params[k]:+.2f} p={fd['out_net_M'].pvalues[k]:.3f}"
            if k not in ka:
                log(f"  {OR.NAME[k]:<42}{dl:>34}   (dropped after 2022: fewer than five trades differ)")
                continue
            ps = [fa[y].pvalues[k] for _, y in OR.YS]
            bs = [fa[y].params[k] for _, y in OR.YS]
            same = lambda i: ps[i] < 0.05 and np.sign(bs[i]) == np.sign(bs[0])   # noqa: E731
            tag = ("F" + ("g" if same(2) else "") + ("s" if same(3) else "")) if (ps[0] < 0.05 and same(1)) else \
                  ("T" if ps[0] < 0.05 else "")
            cells = [f"{bs[0]:+.2f} ({fa['net_M'].bse[k]:.2f}) p={ps[0]:.3f}"] + [f"{bs[i]:+.2f} p={ps[i]:.3f}" for i in (1, 2, 3)]
            mark = "  <- finding 2017-22" if k in FINDINGS[rule] else ""
            log(f"  {OR.NAME[k]:<42}{dl:>34}   {cells[0]:>26}{cells[1]:>24}{cells[2]:>20}{cells[3]:>20}  {tag}{mark}")
            for (lab, y), b, p in zip(OR.YS, bs, ps):
                OUT.append({"rule": rule, "term": OR.NAME[k], "col": k, "outcome": lab, "n_trades": int(fa[y].nobs),
                            "estimate": b, "se": fa[y].bse[k], "p": p, "finding_2017_22": k in FINDINGS[rule]})

    log("\nTHE DOCUMENT'S FINDINGS, after 2022 (the declared reading)")
    for rule, ks in FINDINGS.items():
        fd, kd, fa, ka = res[rule]
        for k in ks:
            if k not in ka:
                log(f"  {rule}, {OR.NAME[k]}: dropped after 2022")
                continue
            td, rv = fa["net_M"], fa["out_net_M"]
            s0 = np.sign(fd["net_M"].params[k])
            t_ok = td.pvalues[k] < 0.05 and np.sign(td.params[k]) == s0
            r_ok = rv.pvalues[k] < 0.05 and np.sign(rv.params[k]) == np.sign(fd["out_net_M"].params[k])
            verdict = "replicates in full" if (t_ok and r_ok) else ("replicates on trade day only" if t_ok else
                      ("realized value only" if r_ok else "does not replicate"))
            log(f"  {rule}, {OR.NAME[k]}: trade-day {td.params[k]:+.2f} (p = {td.pvalues[k]:.3f}), realized "
                f"{rv.params[k]:+.2f} (p = {rv.pvalues[k]:.3f}): {verdict}")
    pd.DataFrame(OUT).to_csv(OUTPUT_DIR / "one_regression_replication.csv", index=False)
    (OUTPUT_DIR / "one_regression_replication_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
