"""
who_overpaid_checks.py - two checks on who_overpaid.py (Thomas, 2026-11-17: "Yes, run both"; declared in
40_DOCS/Backtest_Protocol.md before it was built. Report only.)

1  IMMATURE OUTCOMES. Picks and prospects traded after 2022 have mostly not reached the NHL, so their "outcome" is largely
   the models valuing them again. The "who" regression (who_overpaid.py part C) is re-run on the trades after 2022-03-28
   alone, and with each club's result counted on the seasons played through 2025-26 only. The trade-day grade (the
   overpay) needs no maturity; only the loss moves.
2  MODEL ERROR OR THE MARKET. Trade prices followed about a quarter of the differences in contract value the models
   measure (part B). Error in the models' values pulls such a slope toward zero by itself. Two answers:
   a  the price paid regressed on the main player's performance value AS DELIVERED (his asset's outcome plus the same
      cost), and on the seasons played only
   b  two-stage least squares: the price on the model's performance value, that value predicted from the delivered value
      first. Error in the model's value is then removed, provided it is unrelated to the luck in what was delivered.
      Standard errors by 2,000 resamples of trades (seed 20261117).

INPUTS: who_overpaid.build() (the extended run), backtest_sides.csv, backtest_sides_gv_adj.csv, backtest_assets.csv
OUTPUTS: OUTPUT_DIR/who_overpaid_checks_log.txt, who_overpaid_checks.csv
"""
import importlib.util
import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
EXT = OUTPUT_DIR / "_extended_run"
SCRIPT_VERSION = "who_overpaid_checks.py v1.1 (2026-11-17)"   # v1.1: the two-stage fit also instrumented by the seasons played only
DECLARED_END = "2022-03-28"
N_BOOT, SEED = 2000, 20261117
LOG, OUT = [], []


def log(s=""):
    print(s)
    LOG.append(s)


def main():
    log(SCRIPT_VERSION)
    spec = importlib.util.spec_from_file_location("who_overpaid", Path(__file__).resolve().parent / "who_overpaid.py")
    WO = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(WO)
    GC, t = WO.build()
    key = ["trade_id", "club"]
    real = pd.read_csv(EXT / "backtest_sides.csv")[key + ["real_net_M"]]
    realg = pd.read_csv(EXT / "backtest_sides_gv_adj.csv")[key + ["real_net_M"]].rename(columns={"real_net_M": "real_gv_M"})
    t = t.merge(real, on=key, how="left").merge(realg, on=key, how="left")
    a = pd.read_csv(EXT / "backtest_assets.csv")[["asset_id", "realised_M"]].drop_duplicates("asset_id")
    t = t.merge(a.rename(columns={"realised_M": "V_real"}), on="asset_id", how="left")

    # ---- 1 ---------------------------------------------------------------------------------------------------------------
    chars = [("aged 28 to 31", "age28"), ("aged 32 or over", "age32"), ("defenceman", "defence"), ("a clause", "clause"),
             ("signed as a free agent", "ufa"), ("two seasons left", "left2"), ("three or more seasons left", "left3"),
             ("production (trailing WAR total)", "trailing_war"), ("record above the forecast (WAR)", "rep_gap"),
             ("games share, most recent season", "gp_share_last"), ("former top-15 pick", "top15")]
    cc = [c for _, c in chars]
    d = t[t["name"].notna()].dropna(subset=cc + ["age"]).copy()
    d["overpay"] = -d["net_M"]
    d["loss"], d["loss_gv"] = -d["out_net_M"], -d["gv_net_M"]
    d["loss_played"], d["loss_gv_played"] = -d["real_net_M"], -d["real_gv_M"]
    # GUARD: all trades, together, gives who_overpaid.py's recorded coefficients back (former top-15 pick +1.53 / +1.52)
    m = sm.OLS(d["overpay"], sm.add_constant(d[cc])).fit(cov_type="cluster", cov_kwds={"groups": d["trade_id"]})
    m2 = sm.OLS(d["loss"], sm.add_constant(d[cc])).fit(cov_type="cluster", cov_kwds={"groups": d["trade_id"]})
    assert abs(m.params["top15"] - 1.53) < 0.005 and abs(m2.params["top15"] - 1.52) < 0.005, (m.params["top15"], m2.params["top15"])
    log("  check: the all-trades fit gives who_overpaid.py's figures back (former top-15 pick +1.53 / +1.52) (PASS)")
    log("\n1. WHO IS OVERPAID: the same regression, all characteristics together ($M a side; * = statistically significant at 5%)")
    specs = [("after 2022-03-28 alone", d["trade_date"] > DECLARED_END, ["overpay", "loss", "loss_gv"]),
             ("all trades, seasons played only", pd.Series(True, index=d.index), ["overpay", "loss_played", "loss_gv_played"]),
             ("declared window, seasons played only", d["trade_date"] <= DECLARED_END, ["overpay", "loss_played", "loss_gv_played"])]
    for scope, msk, ys in specs:
        dd = d[msk]
        fits = {y: sm.OLS(dd[y], sm.add_constant(dd[cc])).fit(cov_type="cluster", cov_kwds={"groups": dd["trade_id"]}) for y in ys}
        log(f"\n  {scope} ({len(dd)} sides, {dd['trade_id'].nunique()} trades)")
        log(f"  {'characteristic':<34}" + "".join(f"{y:>26}" for y in ys))
        for lab, c in chars:
            cells = [f"{fits[y].params[c]:+.2f}{'*' if fits[y].pvalues[c] < 0.05 else ' '} (p={fits[y].pvalues[c]:.3f})" for y in ys]
            log(f"  {lab:<34}" + "".join(f"{x:>26}" for x in cells))
            for y in ys:
                OUT.append({"check": "1", "scope": scope, "term": lab, "outcome": y, "coef": fits[y].params[c],
                            "se": fits[y].bse[c], "p": fits[y].pvalues[c], "n": len(dd)})

    # ---- 2 ---------------------------------------------------------------------------------------------------------------
    b = t[t["perf"].notna() & t["price"].notna() & t["V_out"].notna()].copy()
    b["perf_del"] = b["V_out"] + b["cost"]
    b["perf_real"] = b["V_real"] + b["cost"]
    log(f"\n2. MODEL ERROR OR THE MARKET: the price paid for the main player ({len(b)} club sides)")
    log(f"  correlation of the model's performance value with the delivered one: {np.corrcoef(b['perf'], b['perf_del'])[0, 1]:.3f}; "
        f"with the seasons played only: {np.corrcoef(b['perf'], b['perf_real'])[0, 1]:.3f}")
    log(f"  {'scope':<18}{'price paid on':<46}{'performance value':>26}{'cost':>26}")
    rng = np.random.default_rng(SEED)
    for scope, msk in (("all trades", pd.Series(True, index=b.index)), ("declared window", b["trade_date"] <= DECLARED_END)):
        bb = b[msk].reset_index(drop=True)
        for lab, x in (("the model's performance value (part B)", "perf"), ("the performance value as delivered", "perf_del"),
                       ("the same, seasons played only", "perf_real")):
            m = sm.OLS(bb["price"], sm.add_constant(bb[[x, "cost"]])).fit(cov_type="cluster", cov_kwds={"groups": bb["trade_id"]})
            log(f"  {scope:<18}{lab:<46}{f'{m.params[x]:+.2f} ({m.bse[x]:.2f}) p={m.pvalues[x]:.3f}':>26}"
                f"{f'{m.params["cost"]:+.2f} ({m.bse["cost"]:.2f})':>26}")
            OUT.append({"check": "2", "scope": scope, "model": lab, "perf": m.params[x], "perf_se": m.bse[x], "perf_p": m.pvalues[x],
                        "cost": m.params["cost"], "cost_se": m.bse["cost"], "n": len(bb)})

        def tsls(df, inst="perf_del"):
            first = sm.OLS(df["perf"], sm.add_constant(df[[inst, "cost"]])).fit()
            df = df.assign(perf_hat=first.fittedvalues)
            second = sm.OLS(df["price"], sm.add_constant(df[["perf_hat", "cost"]])).fit()
            return float(second.params["perf_hat"]), float(second.params["cost"]), float(first.params[inst]), float(first.tvalues[inst])
        ids = bb["trade_id"].unique()
        by = {i: g for i, g in bb.groupby("trade_id")}
        # v1.1: also instrumented by the seasons played only, so the instrument shares no re-valuation at 2026-27 with the model
        for inst, lab in (("perf_del", "two-stage, instrument: delivered"), ("perf_real", "two-stage, instrument: seasons played")):
            e = tsls(bb, inst)
            boots = np.array([tsls(pd.concat([by[i] for i in ids[rng.integers(0, len(ids), len(ids))]]), inst)[:2] for _ in range(N_BOOT)])
            lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
            log(f"  {scope:<18}{lab:<46}{f'{e[0]:+.2f} [{lo[0]:+.2f}, {hi[0]:+.2f}]':>26}"
                f"{f'{e[1]:+.2f} [{lo[1]:+.2f}, {hi[1]:+.2f}]':>26}   (first stage: {e[2]:+.2f} per $1, t = {e[3]:.1f})")
            OUT.append({"check": "2", "scope": scope, "model": lab, "perf": e[0], "perf_lo": lo[0], "perf_hi": hi[0],
                        "cost": e[1], "cost_lo": lo[1], "cost_hi": hi[1], "first_stage": e[2], "first_t": e[3], "n": len(bb)})
    log("  (a price that follows each part in full: +1.00 on performance value, -1.00 on cost)")
    pd.DataFrame(OUT).to_csv(OUTPUT_DIR / "who_overpaid_checks.csv", index=False)
    (OUTPUT_DIR / "who_overpaid_checks_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
