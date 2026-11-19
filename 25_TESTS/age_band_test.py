"""
age_band_test.py - aged 28 or over in place of the two age bands (28 to 31; 32 or over) in the who-is-overpaid regression
(Thomas, 2026-11-18: "Replace 28-31 and 32+ with just 28+, I'm mostly just curious if the way you define the age bands
affects anything"; declared in 40_DOCS/Backtest_Protocol.md before it was built. Report only, a sensitivity.)

ROWS: traits_test.frame(), who_overpaid_any.py v1.4's 431 declared-window club sides with both rules' characteristics
(its guard 1: the two-band fits reproduce who_overpaid_any's coefficients).
THE TERM: main player rule, the main player is 28 or over at the trade date (his age28 or age32 flag; GUARD: equals his
age >= 28 on every side); any player rule, any player received is (any_age28 or any_age32). It replaces the two bands;
every other term, row and standard error (clustered by trade) is unchanged.
REPORTED: for each rule and outcome (trade-day grade, realized value on WAR, Game Value, the seasons played; $M a club,
positive = the club gained) the 28-and-over coefficient beside the two bands', and the clause and defenceman coefficients
in both fits. The joint regression's version is groups_any.py v1.3 part 6.

OUTPUTS: OUTPUT_DIR/age_band_test_log.txt, age_band_test.csv
"""
import importlib.util
import os
from pathlib import Path

import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
SCRIPT_VERSION = "age_band_test.py v1.0 (2026-11-18)"
YS = [("trade-day grade", "net_M"), ("realized value, WAR", "out_net_M"), ("realized value, Game Value", "gv_net_M"),
      ("realized value, seasons played", "real_net_M")]
LOG, OUT = [], []


def log(s=""):
    print(s)
    LOG.append(s)


def fit(d, y, xs):
    return sm.OLS(d[y], sm.add_constant(d[xs])).fit(cov_type="cluster", cov_kwds={"groups": d["trade_id"]})


def main():
    log(SCRIPT_VERSION)
    spec = importlib.util.spec_from_file_location("traits_test", Path(__file__).resolve().parent / "traits_test.py")
    TT = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(TT)
    TT.LOG = LOG                                                   # its guard lines go into this log
    WO, CC, d, f, key, flags, cc, cc_m, cc_a = TT.frame()
    d["m_age28p"] = ((d["age28"] == 1) | (d["age32"] == 1)).astype(int)
    assert (d["m_age28p"] == (d["age"] >= 28).astype(int)).all()                      # GUARD: the main player's age >= 28
    d["a_age28p"] = ((d["any_age28"] == 1) | (d["any_age32"] == 1)).astype(int)
    log(f"  check: the main player's 28-and-over flag equals his age >= 28 on all {len(d)} sides (PASS)")
    log(f"  clubs aged 28 or over: main player {int(d['m_age28p'].sum())}, any player {int(d['a_age28p'].sum())} "
        f"(two bands, main player: 28 to 31 {int(d['age28'].sum())}, 32 or over {int(d['age32'].sum())})")
    log("\n$M a club, positive = the club gained; clustered by trade; two bands -> 28 and over")
    log(f"  {'':<34}" + "".join(f"{y:>34}" for y, _ in YS))
    for rule, base, b28, b32, b28p in (("main player rule", cc_m, "age28", "age32", "m_age28p"),
                                       ("any player rule", cc_a, "any_age28", "any_age32", "a_age28p")):
        one = [b28p if c == b28 else c for c in base if c != b32]
        f2 = {y: fit(d, y, base) for _, y in YS}
        f1 = {y: fit(d, y, one) for _, y in YS}
        log(f"  {rule}")
        rows = [("aged 28 to 31 (two bands)", f2, b28), ("aged 32 or over (two bands)", f2, b32), ("aged 28 or over (one term)", f1, b28p)]
        for k in ("clause", "defence"):
            kk = base[cc.index(k)]
            rows += [(f"{k}, two bands", f2, kk), (f"{k}, one term", f1, kk)]
        for lab, fs, k in rows:
            cells = []
            for ylab, y in YS:
                m = fs[y]
                cells.append(f"{m.params[k]:+.2f} ({m.bse[k]:.2f}) p={m.pvalues[k]:.3f}")
                OUT.append({"rule": rule, "term": lab, "outcome": ylab, "n": int(m.nobs), "estimate": m.params[k],
                            "se": m.bse[k], "p": m.pvalues[k]})
            log(f"    {lab:<32}" + "".join(f"{x:>34}" for x in cells))
    pd.DataFrame(OUT).to_csv(OUTPUT_DIR / "age_band_test.csv", index=False)
    (OUTPUT_DIR / "age_band_test_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
