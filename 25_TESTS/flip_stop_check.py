"""
flip_stop_check.py v1.0 (2026-11-24) - report only; writes OUTPUT_DIR/flip_stop_check_log.txt and flip_stop_check.csv.

The protocol's "Realized value stopped when the club trades the asset on" (declared 2026-11-24, before it was built;
Thomas: "Yes, test it", "His value at the flip", "Players and picks"). From Karl's question at the 2026-11-23 meeting.

READS: OUTPUT_DIR/_extended_run/backtest_assets_flipstop.csv and backtest_sides_flipstop.csv (backtest.py v1.9 run with
XNPV_STOP_AT_FLIP=1 on the extended ledger), beside the extended run's own backtest_assets.csv.
GUARDS: (1) every asset's held part + revalued + the part after the flip equals the full run's outcome to $1e-9M, and an
asset not flipped has the full run's outcome exactly; the trade-day values are identical; (2) trade_sides.club_sides on the
stop run's outcomes reproduces its sides (so the bound below is built the same way); (3) the document's regression
(one_regression.frame and joint, both rules) refitted here reproduces one_regression.csv; (4) the trade-day grade is the
same on every regression row.
VERSIONS of realized value (WAR) and seasons played: the document's; stopped at the flip with the exit value; stopped with
nothing after the flip (the bound). Every regressor is the document's. A finding: trade-day grade and realized value both
p < 0.05, the same sign.
"""
import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "20_CODE"))
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
EXT = OUTPUT_DIR / "_extended_run"
SCRIPT_VERSION = "flip_stop_check.py v1.0 (2026-11-24)"
LOG, OUT = [], []


def log(s=""):
    print(s)
    LOG.append(str(s))


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    log(SCRIPT_VERSION)
    full = pd.read_csv(EXT / "backtest_assets.csv")
    stop = pd.read_csv(EXT / "backtest_assets_flipstop.csv")
    for p in ("backtest_assets.csv", "backtest_assets_flipstop.csv", "backtest_sides_flipstop.csv"):
        log(f"  input {EXT / p}: modified {pd.Timestamp((EXT / p).stat().st_mtime, unit='s'):%Y-%m-%d %H:%M} UTC")

    # ---- GUARD 1: the cut adds up to the full run ----
    k = ["asset_id", "asset_type"]
    assert not full.duplicated(k).any() and not stop.duplicated(k).any()
    m = full[k + ["outcome_M", "value_2025_cap_M"]].merge(
        stop[k + ["realised_M", "revalued_M", "after_M", "exit_M", "outcome_M", "flip_trade", "value_2025_cap_M"]],
        on=k, suffixes=("_full", ""), validate="one_to_one")
    assert len(m) == len(full) == len(stop)
    assert np.allclose(m["value_2025_cap_M_full"], m["value_2025_cap_M"], equal_nan=True, atol=0)
    rec = m["realised_M"] + m["revalued_M"] + m["after_M"]
    both = m["outcome_M_full"].notna()
    gap = (rec[both] - m.loc[both, "outcome_M_full"]).abs()
    fl = m["flip_trade"].notna()
    same = (m.loc[both & ~fl, "outcome_M"] - m.loc[both & ~fl, "outcome_M_full"]).abs()
    log(f"  guard 1: held + revalued + after the flip against the full run's outcome, largest gap ${gap.max():.2e}M over "
        f"{int(both.sum())} assets; assets not flipped, largest gap ${same.max():.2e}M; NaN outcomes alike: "
        f"{bool((m['outcome_M_full'].isna() == m['outcome_M'].isna()).all())}")
    assert gap.max() < 1e-9 and same.max() < 1e-9 and (m["outcome_M_full"].isna() == m["outcome_M"].isna()).all()
    log("  (PASS)")

    # ---- GUARD 2: club sides, and the bound ----
    os.environ["XNPV_TRADES_DB"] = str(OUTPUT_DIR / "trades_extended.db")     # the extended ledger's clubs
    import trade_sides as TSD
    clubs, cond = TSD.trade_clubs()
    del os.environ["XNPV_TRADES_DB"]
    key = ["trade_id", "club"]
    ss = pd.read_csv(EXT / "backtest_sides_flipstop.csv")
    mine = TSD.club_sides(stop.assign(o=stop["outcome_M"]), "o", clubs, cond)[key + ["net_M"]]
    chk = ss[key + ["out_net_M"]].merge(mine, on=key, validate="one_to_one")
    assert len(chk) == len(ss) and np.allclose(chk["out_net_M"], chk["net_M"], atol=1e-9)
    bound = TSD.club_sides(stop.assign(o=stop["outcome_M"] - stop["exit_M"]), "o", clubs, cond)[key + ["net_M"]]
    bound = bound.rename(columns={"net_M": "bound_net_M"})
    log(f"  guard 2: club_sides on the stop run's outcomes reproduces its {len(ss)} sides (PASS)")

    # ---- the document's regression, then the stop versions ----
    OR = load("one_regression")
    OR.LOG = LOG                                                              # its checks print into this log
    A, B, t, f, _, WO = OR.frame()
    ref = pd.read_csv(OUTPUT_DIR / "one_regression.csv")
    new = ss[key + ["net_M", "out_net_M", "real_net_M"]].rename(
        columns={"net_M": "grade_stop", "out_net_M": "out_stop", "real_net_M": "real_stop"}).merge(bound, on=key)
    versions = {}
    for lab, ycol, rcol in (("document", "out_net_M", "real_net_M"), ("stop, exit value", "out_stop", "real_stop"),
                            ("stop, nothing after (bound)", "bound_net_M", "real_stop")):
        Ai, Bi = A.copy(), B.copy()
        for X in (Ai, Bi):
            j = X.reset_index()[["trade_id", "club"]].merge(new, on=key, how="left", validate="one_to_one")
            assert j[["grade_stop", "out_stop"]].notna().all().all(), "a regression side is missing from the stop run"
            # GUARD 4: the trade-day grade is the same on every row
            assert np.allclose(X["net_M"].values, j["grade_stop"].values, atol=1e-9)
            if lab != "document":
                X["out_net_M"], X["real_net_M"] = j[ycol].values, j[rcol].values
        versions[lab] = (Ai, Bi)
    log(f"  guard 4: the trade-day grade identical on all {len(A)} trades (PASS)")

    flips = stop[stop["flip_trade"].notna() & stop["trade_id"].isin(A.index)]
    log(f"\n  in the {len(A)} regression trades: {len(flips)} assets held to a second trade "
        f"({int((flips['asset_type'] == 'player').sum())} players and prospects, {int((flips['asset_type'] == 'pick').sum())} "
        f"picks), in {flips['trade_id'].nunique()} trades; left out after the flip ${flips['after_M'].sum():,.1f}M, exit "
        f"values ${flips['exit_M'].sum():,.1f}M")

    YS = [("trade-day grade", "net_M"), ("realized value, WAR", "out_net_M"), ("seasons played", "real_net_M")]
    for rule in OR.P5:
        cols = [c for c in OR.P5[rule] if c not in OR.DUP[rule] and c != OR.BELOW[rule]] + OR.PC[rule] + ["recv"]
        flg = set(cols) - {"trailing_war", "rep_gap", "gp_share_last", "avg_war", "avg_gap", "avg_gs"}
        fits = {lab: OR.joint(Ai, Bi, cols, flg) for lab, (Ai, Bi) in versions.items()}
        # GUARD 3: the document's fit reproduces one_regression.csv
        fs, keep = fits["document"]
        for kk in keep:
            for ylab, y in (("trade-day grade", "net_M"), ("realized value, WAR", "out_net_M")):
                r0 = ref[(ref["rule"] == rule) & (ref["col"] == kk) & (ref["outcome"] == ylab)]
                assert len(r0) == 1 and np.isclose(r0["estimate"].iloc[0], fs[y].params[kk]) and \
                    np.isclose(r0["p"].iloc[0], fs[y].pvalues[kk]), (rule, kk, ylab)
        log(f"\n  guard 3: the document's fit reproduces one_regression.csv, {rule} (PASS)")
        log(f"\n  {rule.upper()} ($M a club; estimate, p)")
        log(f"  {'term':<44}{'trade-day grade':>20}" + "".join(f"{lab:>30}" for lab in fits) + "   finding (doc | exit | bound)")
        for kk in keep:
            g = fits["document"][0]["net_M"]
            cells, tags = [], []
            for lab, (fsx, _) in fits.items():
                mo = fsx["out_net_M"]
                cells.append(f"{mo.params[kk]:+.2f} p={mo.pvalues[kk]:.3f}")
                tags.append("F" if (g.pvalues[kk] < 0.05 and mo.pvalues[kk] < 0.05
                                    and np.sign(mo.params[kk]) == np.sign(g.params[kk])) else "-")
                for ylab, y in YS:
                    OUT.append({"rule": rule, "term": OR.NAME[kk], "col": kk, "version": lab, "outcome": ylab,
                                "estimate": fsx[y].params[kk], "se": fsx[y].bse[kk], "p": fsx[y].pvalues[kk]})
            log(f"  {OR.NAME[kk]:<44}{g.params[kk]:>+11.2f} p={g.pvalues[kk]:.3f}" + "".join(f"{c:>30}" for c in cells)
                + f"   {' | '.join(tags)}")
    pd.DataFrame(OUT).to_csv(OUTPUT_DIR / "flip_stop_check.csv", index=False)
    (OUTPUT_DIR / "flip_stop_check_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    log(f"\nwrote flip_stop_check.csv and flip_stop_check_log.txt in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
