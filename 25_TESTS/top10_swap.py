"""
top10_swap.py v1.0 (2026-11-24) - report only; writes OUTPUT_DIR/top10_swap_log.txt and top10_swap.csv.

The protocol's "The former top-10 pick in place of the top-15" (declared 2026-11-24, before it was built). Karl at the
2026-11-23 meeting: "Did you try doing like more restrictive, like top 10?"; Thomas: "Do this first"; "Swap in top-10".
Exploratory: chosen after the top-15 term fell short of a finding.

Section 3's regression (one_regression.frame and joint, both rules, the 556 trades) with the former top-15 pick replaced
by the former top-10 pick; nothing else changes.
  main player rule  top15      = the main player's draft position <= 15 (who_overpaid.build, t["pick"]); here <= 10
  any player rule   any_top15  = any player received with draft position <= 15 (who_overpaid_any.player_facts, the pick
                                 from EXT/prospect_values.csv by asset); here <= 10
A club that received no player has every player characteristic 0 (frame's rule), here too.
GUARDS: (1) the flags rebuilt at 15 equal the document's on every row, both rules; (2) the document's fit reproduces
one_regression.csv. A finding: trade-day grade and realized value on WAR both p < 0.05, the same sign.
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
SCRIPT_VERSION = "top10_swap.py v1.0 (2026-11-24)"
LOG, OUT = [], []


def log(s=""):
    print(s)
    LOG.append(str(s))


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def flags(A, B, f, key, cut):
    """The two rules' flags at draft position <= cut, built as frame builds them, for the regression rows A and B."""
    pv = pd.read_csv(EXT / "prospect_values.csv", low_memory=False)[["asset_id", "pick"]].drop_duplicates("asset_id")
    ff = f[key + ["asset_id"]].merge(pv, on="asset_id", how="left", validate="many_to_one")
    assert len(ff) == len(f)
    anyf = (ff["pick"] <= cut).astype(int).groupby([ff["trade_id"], ff["club"]]).max()
    out = {}
    for lab, X in (("A", A), ("B", B)):
        idx = pd.MultiIndex.from_arrays([X.index, X["club"]])
        recv = X["recv"] == 1
        main = np.where(recv, (X["pick"] <= cut).astype(float), 0.0)
        anyv = np.where(recv, anyf.reindex(idx).fillna(0).values.astype(float), 0.0)
        out[lab] = (main, anyv)
    return out


def main():
    log(SCRIPT_VERSION)
    OR = load("one_regression")
    OR.LOG = LOG
    A, B, t, f, key, WO = OR.frame()
    ref = pd.read_csv(OUTPUT_DIR / "one_regression.csv")

    # GUARD 1: the flags rebuilt at 15 are the document's
    at15 = flags(A, B, f, key, 15)
    for lab, X in (("A", A), ("B", B)):
        m15, a15 = at15[lab]
        dm, da = int((m15 != X["top15"].values).sum()), int((a15 != X["any_top15"].values).sum())
        assert dm == 0 and da == 0, (lab, dm, da)
    log(f"  guard 1: the top-15 flags rebuilt from the draft positions equal the document's on all {len(A)} trades, both "
        f"clubs, both rules (PASS)")
    at10 = flags(A, B, f, key, 10)
    A10, B10 = A.copy(), B.copy()
    A10["top15"], A10["any_top15"] = at10["A"]
    B10["top15"], B10["any_top15"] = at10["B"]
    for rule, c in (("main player rule", "top15"), ("any player rule", "any_top15")):
        d15 = (A[c] - B[c] != 0).sum()
        d10 = (A10[c] - B10[c] != 0).sum()
        log(f"  {rule}: trades where the clubs differ, top-15 {int(d15)}, top-10 {int(d10)}; clubs with the trait, top-15 "
            f"{int(A[c].sum() + B[c].sum())}, top-10 {int(A10[c].sum() + B10[c].sum())}")

    YS = OR.YS
    for rule in OR.P5:
        cols = [c for c in OR.P5[rule] if c not in OR.DUP[rule] and c != OR.BELOW[rule]] + OR.PC[rule] + ["recv"]
        fl = set(cols) - {"trailing_war", "rep_gap", "gp_share_last", "avg_war", "avg_gap", "avg_gs"}
        doc, keep = OR.joint(A, B, cols, fl)
        new, keep10 = OR.joint(A10, B10, cols, fl)
        assert keep == keep10, (keep, keep10)
        # GUARD 2: the document's fit reproduces one_regression.csv
        for kk in keep:
            for ylab, y in YS:
                r0 = ref[(ref["rule"] == rule) & (ref["col"] == kk) & (ref["outcome"] == ylab)]
                assert len(r0) == 1 and np.isclose(r0["estimate"].iloc[0], doc[y].params[kk]) and \
                    np.isclose(r0["p"].iloc[0], doc[y].pvalues[kk]), (rule, kk, ylab)
        log(f"\n  guard 2: the document's fit reproduces one_regression.csv, {rule} (PASS)")
        top = "top15" if rule == "main player rule" else "any_top15"
        log(f"\n  {rule.upper()} ($M a club; estimate (standard error) p)")
        log(f"  {'term':<44}" + "".join(f"{y:>32}" for y, _ in YS) + "   finding")
        for fits, name in ((doc, "document"), (new, "top-10 swap")):
            for kk in keep:
                cells, ps, bs = [], [], []
                for ylab, y in YS:
                    m = fits[y]
                    cells.append(f"{m.params[kk]:+.2f} ({m.bse[kk]:.2f}) p={m.pvalues[kk]:.3f}")
                    ps.append(m.pvalues[kk]); bs.append(m.params[kk])
                    OUT.append({"rule": rule, "version": name, "term": OR.NAME[kk], "col": kk, "outcome": ylab,
                                "estimate": m.params[kk], "se": m.bse[kk], "p": m.pvalues[kk], "n_trades": int(m.nobs)})
                fnd = "F" if (ps[0] < 0.05 and ps[1] < 0.05 and np.sign(bs[1]) == np.sign(bs[0])) else ""
                if name == "top-10 swap" or kk == top:
                    label = ("former top-10 pick" if (kk == top and name == "top-10 swap") else OR.NAME[kk])
                    log(f"  {name[:9] + ': ' + label:<44}" + "".join(f"{x:>32}" for x in cells) + f"   {fnd}")
        # every other term's finding status, document against the swap
        moved = []
        for kk in keep:
            st = []
            for fits in (doc, new):
                g, o = fits["net_M"], fits["out_net_M"]
                st.append(g.pvalues[kk] < 0.05 and o.pvalues[kk] < 0.05 and np.sign(g.params[kk]) == np.sign(o.params[kk]))
            if st[0] != st[1]:
                moved.append(f"{OR.NAME[kk]} ({'finding' if st[0] else 'not'} -> {'finding' if st[1] else 'not'})")
        log(f"  terms whose finding status changes with the swap: {moved if moved else 'none'}")
    pd.DataFrame(OUT).to_csv(OUTPUT_DIR / "top10_swap.csv", index=False)
    (OUTPUT_DIR / "top10_swap_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    log(f"\nwrote top10_swap.csv and top10_swap_log.txt in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
