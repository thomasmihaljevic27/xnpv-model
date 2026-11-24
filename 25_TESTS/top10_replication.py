"""
top10_replication.py v1.0 (2026-11-24) - report only; writes OUTPUT_DIR/top10_replication_log.txt and top10_replication.csv.

The protocol's "The former top-10 pick on the trades after 2022" (declared 2026-11-24, before it was built; Thomas: "Yes,
replicate it"). The top-10 swap (top10_swap.py) on the trades it was not chosen on.

ROWS AND FIT: one_regression_replication.pick (the two-team trades after 2022-03-28; a trade left out when a main player has
an unknown characteristic) and one_regression.joint, both rules, with the former top-15 pick replaced by the former top-10
pick: main player rule, the main player's draft position <= 10; any player rule, any player received at <= 10 (the pick from
EXT/prospect_values.csv by asset, as who_overpaid_any.player_facts). A club with no player received has 0 (frame's rule).
GUARDS: (1) the flags rebuilt at 15 equal one_regression.frame's on every club side of every trade; (2) the same code on the
declared window reproduces top10_swap.csv.
READING (declared): replicates in full when the trade-day grade and realized WAR after 2022 both have the declared window's
sign with p < 0.05; on trade day only when only the trade-day grade does.
"""
import importlib.util
import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
HERE = Path(__file__).resolve().parent
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
EXT = OUTPUT_DIR / "_extended_run"
SCRIPT_VERSION = "top10_replication.py v1.0 (2026-11-24)"
LOG, OUT = [], []


def log(s=""):
    print(s)
    LOG.append(str(s))


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def with_cut(t, f, key, cut):
    """Every club side's two flags at draft position <= cut (frame's construction)."""
    pv = pd.read_csv(EXT / "prospect_values.csv", low_memory=False)[["asset_id", "pick"]].drop_duplicates("asset_id")
    ff = f[key + ["asset_id"]].merge(pv, on="asset_id", how="left", validate="many_to_one")
    assert len(ff) == len(f)
    anyf = (ff["pick"] <= cut).astype(int).groupby([ff["trade_id"], ff["club"]]).max()
    recv = t["recv"] == 1
    main = np.where(recv, (t["pick"] <= cut).astype(float), 0.0)
    anyv = np.where(recv, anyf.reindex(pd.MultiIndex.from_frame(t[key])).fillna(0).values.astype(float), 0.0)
    return main, anyv


def main():
    log(SCRIPT_VERSION)
    OR, RP = load("one_regression"), load("one_regression_replication")
    OR.LOG = LOG
    A0, B0, t, f, key, WO = OR.frame()
    m15, a15 = with_cut(t, f, key, 15)
    dm, da = int((m15 != t["top15"].values).sum()), int((a15 != t["any_top15"].values).sum())
    log(f"  guard 1: the top-15 flags rebuilt from draft positions differ from frame's on {dm} and {da} of {len(t)} club "
        f"sides (main, any player rule)")
    assert dm == 0 and da == 0
    log("  (PASS)")
    t10 = t.copy()
    t10["top15"], t10["any_top15"] = with_cut(t, f, key, 10)
    Ad, Bd, _ = RP.pick(t10, key, after=False)
    assert list(Ad.index) == list(A0.index), "declared-window rows"
    Aa, Ba, nd = RP.pick(t10, key, after=True)
    log(f"  after 2022-03-28: {len(Aa)} two-team trades ({nd} left out for an unknown characteristic)")
    for rule, c in (("main player rule", "top15"), ("any player rule", "any_top15")):
        log(f"  {rule}: clubs with a former top-10 pick after 2022 {int(Aa[c].sum() + Ba[c].sum())}; trades where the clubs "
            f"differ {int((Aa[c] - Ba[c] != 0).sum())}")
    ref = pd.read_csv(OUTPUT_DIR / "top10_swap.csv")
    ref = ref[ref["version"] == "top-10 swap"]
    YS = OR.YS
    for rule in OR.P5:
        cols = [c for c in OR.P5[rule] if c not in OR.DUP[rule] and c != OR.BELOW[rule]] + OR.PC[rule] + ["recv"]
        fl = set(cols) - RP.CONT
        fd, kd = OR.joint(Ad, Bd, cols, fl)
        for lab, y in YS:                                                  # GUARD 2: the declared window as top10_swap
            rr = ref[(ref["rule"] == rule) & (ref["outcome"] == lab)].set_index("col")
            assert list(rr.index) == kd, (rule, "terms")
            assert np.allclose(fd[y].params[kd].values, rr["estimate"].values, atol=1e-9), (rule, y)
            assert np.allclose(fd[y].pvalues[kd].values, rr["p"].values, atol=1e-12), (rule, y)
        fa, ka = OR.joint(Aa, Ba, cols, fl)
        log(f"\n  guard 2: the declared window reproduces top10_swap.csv, {rule} (PASS)")
        top = "top15" if rule == "main player rule" else "any_top15"
        log(f"\n  {rule.upper()} ({int(fa['net_M'].nobs)} trades after 2022; $M a club, estimate (standard error) p)")
        log(f"  {'term':<36}{'2017-22: trade-day | realized':>36}" + "".join(f"{y:>32}" for y, _ in YS) + "   verdict")
        for k in [top] + [x for x in RP.FINDINGS[rule]]:
            name = "former top-10 pick" if k == top else OR.NAME[k]
            dl = (f"{fd['net_M'].params[k]:+.2f} p={fd['net_M'].pvalues[k]:.3f} | "
                  f"{fd['out_net_M'].params[k]:+.2f} p={fd['out_net_M'].pvalues[k]:.3f}")
            if k not in ka:
                log(f"  {name:<36}{dl:>36}   (dropped after 2022: fewer than five trades differ)")
                continue
            cells = [f"{fa[y].params[k]:+.2f} ({fa[y].bse[k]:.2f}) p={fa[y].pvalues[k]:.3f}" for _, y in YS]
            t_ok = fa["net_M"].pvalues[k] < 0.05 and np.sign(fa["net_M"].params[k]) == np.sign(fd["net_M"].params[k])
            r_ok = fa["out_net_M"].pvalues[k] < 0.05 and np.sign(fa["out_net_M"].params[k]) == np.sign(fd["out_net_M"].params[k])
            verdict = "replicates in full" if (t_ok and r_ok) else ("replicates on trade day only" if t_ok else
                      ("realized value only" if r_ok else "does not replicate"))
            log(f"  {name:<36}{dl:>36}" + "".join(f"{x:>32}" for x in cells) + f"   {verdict}")
            for (lab, y) in YS:
                OUT.append({"rule": rule, "term": name, "col": k, "outcome": lab, "n_trades": int(fa[y].nobs),
                            "estimate": fa[y].params[k], "se": fa[y].bse[k], "p": fa[y].pvalues[k], "verdict": verdict})
    pd.DataFrame(OUT).to_csv(OUTPUT_DIR / "top10_replication.csv", index=False)
    (OUTPUT_DIR / "top10_replication_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    log(f"\nwrote top10_replication.csv and top10_replication_log.txt in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
