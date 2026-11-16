"""
joint_regression.py - which of the back-test's findings survive each other? (Thomas, 2026-11-15: "Yes, run it";
declared in 40_DOCS/Backtest_Protocol.md, "Which findings survive each other", before it was built. Report only.)

WHY. The exploratory cuts are largely the same trades seen from different sides: a deadline buyer often takes a rental
from a club that retains salary and gets picks back. Counted one at a time they look like many findings. Here they are
put in one regression, so each characteristic is credited only with what it adds once the others are held.

THE DESIGN (two-team complete trades; one row a trade)
  outcome    club A's net (A is the first club in alphabetical order; the other club's net is its negative): the forecast
             net (what the models priced), the outcome net on Bacon's WAR, the outcome net on Game Value. $M at the
             2025-26 cap, the model as decided (each contract season on the term left).
  traits     each enters as club A's indicator minus club B's: +1 if A has it and B does not, -1 the reverse, 0 if both or
             neither. No constant (a trade where neither club has any trait is expected to be even). A coefficient is
             therefore what having the trait, rather than the other club having it, adds to a club's net, the others held.
             Swapping which club is A flips the outcome and every trait, so nothing depends on the alphabet.
  traits used, each as its cut defines it (backtest_cuts.py v1.4 and backtest_cuts_more.py v1.3 write them per side):
    futures for players     received only picks and prospects, the other club only players (the protocol's C1)
    deadline buyer          higher in the standings, in the 14 days to the deadline
    other in-season buyer   higher in the standings, rest of the regular season
    rental                  main player in his final season, unrestricted at expiry, traded in-season
    retained salary         retained part of a player's cap hit
    main player 28 to 31; main player 32 or over   (against 27 and under or not known)
    main player a defenceman
    main player with a clause   no-trade or no-move clause in the trade season
    former top-15 pick below the benchmark   received one (cut 5b)
    one asset for two or more   received a single asset, the other club two or more
    took a contract to clear cap   received a $2.5M+ player with a pick or prospect, gave no $1M+ player (cut 8(i))
    sold under a new GM     sent its highest-paid player in a new general manager's first year, on a contract signed
                            before him (the GM cut)
  intervals  2,000 resamples of trades, seed 20261115; p two-sided against zero
  beside     each trait's coefficient alone (a regression on that trait only), so it shows which shrink

INPUTS: OUTPUT_DIR (the extended run)/backtest_cuts_all_sides.csv, backtest_cuts_more_gm_sides.csv,
        backtest_cuts_more_8_dumps.csv, backtest_sides_gv_adj.csv
OUTPUTS: OUTPUT_DIR/joint_regression_log.txt, joint_regression.csv
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
PLAYED = os.environ.get("XNPV_OUTCOME_PART", "all") == "played"
TAG = "_played" if PLAYED else ""
SCRIPT_VERSION = "joint_regression.py v1.2 (2026-11-15)"   # v1.2: XNPV_OUTCOME_PART=played; WAR outcome read from backtest_sides.csv; v1.1: three typical deals read from the joint fit
N_BOOT, SEED = 2000, 20261115
DECLARED_END = "2022-03-28"
LOG, OUT = [], []
TRAITS = [("futures for players", "t_futures"), ("deadline buyer", "t_deadline_buyer"),
          ("other in-season buyer", "t_other_buyer"), ("rental", "t_rental"), ("retained salary", "t_retained"),
          ("main player 28 to 31", "t_age28"), ("main player 32 or over", "t_age32"), ("main player a defenceman", "t_def"),
          ("main player with a clause", "t_clause"), ("former top-15 pick below benchmark", "t_top15"),
          ("one asset for two or more", "t_single"), ("took a contract to clear cap", "t_dump"),
          ("sold under a new GM", "t_newgm")]


def log(s=""):
    print(s)
    LOG.append(s)


def main():
    rng = np.random.default_rng(SEED)
    log(SCRIPT_VERSION)
    log(f"  reads {OUTPUT_DIR}")
    s = pd.read_csv(OUTPUT_DIR / "backtest_cuts_all_sides.csv")
    log(f"  club sides (complete trades): {len(s)}; trades {s['trade_id'].nunique()}")
    gm = pd.read_csv(OUTPUT_DIR / "backtest_cuts_more_gm_sides.csv")
    dumps = pd.read_csv(OUTPUT_DIR / "backtest_cuts_more_8_dumps.csv")
    key = ["trade_id", "club"]
    s = s.merge(gm[key + ["new_gm_predecessor"]], on=key, how="left")
    s["new_gm_predecessor"] = s["new_gm_predecessor"].fillna(False).astype(bool)
    # the club that TOOK the dumped contract: the other club in the dump's trade
    dump_trades = set(dumps["trade_id"])
    dumper = set(zip(dumps["trade_id"], dumps["club"]))
    s["took_dump"] = [(t in dump_trades) and ((t, c) not in dumper) for t, c in zip(s["trade_id"], s["club"])]
    # the traits as 0/1 per side (each cut's definition; see the docstring)
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
    t["t_dump"] = s["took_dump"]
    t["t_newgm"] = s["new_gm_predecessor"]
    part = "real_net_M" if PLAYED else "out_net_M"            # v1.2: the seasons played only, with XNPV_OUTCOME_PART=played
    gv = pd.read_csv(OUTPUT_DIR / "backtest_sides_gv_adj.csv")[key + [part]].rename(columns={part: "gv_net_M"})
    war = pd.read_csv(OUTPUT_DIR / "backtest_sides.csv")[key + [part]].rename(columns={part: "out_net_M"})
    t = t.merge(s[key + ["net_M"]], on=key).merge(war, on=key).merge(gv, on=key)
    log(f"  outcome: {'the seasons played through 2025-26 only (the 2026-27 re-valuation left out)' if PLAYED else 'realised through 2025-26 plus the rest re-valued at 2026-27'}")
    assert len(t) == len(s)                                                          # GUARD: one row a side
    # one row a two-team trade: A minus B
    n = t.groupby("trade_id")["club"].transform("size")
    two = t[n == 2].sort_values(["trade_id", "club"])
    A, B = two.groupby("trade_id").nth(0).set_index("trade_id"), two.groupby("trade_id").nth(1).set_index("trade_id")
    assert (A.index == B.index).all()
    assert np.allclose(A["net_M"] + B["net_M"], 0, atol=1e-6)                       # GUARD: zero-sum
    cols = [c for _, c in TRAITS]
    X = pd.DataFrame({c: A[c].astype(int) - B[c].astype(int) for c in cols}, index=A.index)
    Y = A[["net_M", "out_net_M", "gv_net_M"]]
    dates = A["trade_date"]
    log(f"  two-team trades: {len(X)} (left out: {t.loc[n != 2, 'trade_id'].nunique()} trades of three or more clubs)")
    log("  trades where the trait differs between the two clubs (all / declared window):")
    for lab, c in TRAITS:
        log(f"    {lab:<38}{int((X[c] != 0).sum()):>6} / {int((X.loc[dates <= DECLARED_END, c] != 0).sum()):>4}")
    cor = X.corr()
    pairs = [(cor.index[i], cor.columns[j], cor.iat[i, j]) for i in range(len(cols)) for j in range(i + 1, len(cols))]
    pairs = sorted(pairs, key=lambda x: -abs(x[2]))[:6]
    nm = dict((c, l) for l, c in TRAITS)
    log("  the most closely linked traits (correlation across trades): " + "; ".join(f"{nm[a]} with {nm[b]} {r:+.2f}" for a, b, r in pairs))

    def fit(Xm, y):
        b, *_ = np.linalg.lstsq(Xm, y, rcond=None)
        return b

    for scope, m in (("ALL TRADES 2017-2026", np.ones(len(X), bool)), ("DECLARED WINDOW (to 2022-03-28)", (dates <= DECLARED_END).values)):
        Xs, Ys = X[m].to_numpy(float), Y[m]
        keep = [j for j in range(len(cols)) if (Xs[:, j] != 0).sum() >= 5]           # a trait seen in fewer than 5 trades is left out
        Xs = Xs[:, keep]
        names = [cols[j] for j in keep]
        log(f"\n{scope}: {int(m.sum())} trades; $M per club side; together (alone in brackets); * = 95% interval excludes zero")
        log(f"  {'characteristic':<38}{'trades':>7}{'priced':>26}{'outcome, WAR':>26}{'outcome, Game Value':>26}")
        res = {}
        for y_ in ("net_M", "out_net_M", "gv_net_M"):
            y = Ys[y_].to_numpy(float)
            b = fit(Xs, y)
            boots = np.array([fit(Xs[i], y[i]) for i in (rng.integers(0, len(y), len(y)) for _ in range(N_BOOT))])
            lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
            p = np.minimum(1.0, 2 * np.minimum((boots <= 0).mean(0), (boots >= 0).mean(0)))
            alone = []
            for j in range(len(names)):
                x1 = Xs[:, [j]]
                alone.append(fit(x1, y)[0])
            res[y_] = (b, lo, hi, p, alone)
        res["_boots"] = {}
        for y_ in ("net_M", "out_net_M", "gv_net_M"):
            y = Ys[y_].to_numpy(float)
            r2 = np.random.default_rng(SEED + 1)
            res["_boots"][y_] = np.array([fit(Xs[i], y[i]) for i in (r2.integers(0, len(y), len(y)) for _ in range(N_BOOT))])
        for j, c in enumerate(names):
            cells = []
            for y_ in ("net_M", "out_net_M", "gv_net_M"):
                b, lo, hi, p, alone = res[y_]
                star = "*" if (lo[j] > 0 or hi[j] < 0) else " "
                cells.append(f"{b[j]:+.2f}{star} ({alone[j]:+.2f}) p={p[j]:.3f}")
                OUT.append({"scope": scope, "trait": nm[c], "outcome": y_, "trades_differing": int((Xs[:, j] != 0).sum()),
                            "together": b[j], "lo": lo[j], "hi": hi[j], "p": p[j], "alone": alone[j]})
            log(f"  {nm[c]:<38}{int((Xs[:, j] != 0).sum()):>7}" + "".join(f"{x:>26}" for x in cells))
        # typical trades: the traits are linked (a rental buyer's partner is usually the club taking futures), so single
        # coefficients are read together. The buying club's predicted net for three typical deals, with intervals.
        log("  TYPICAL DEALS, the buying club's predicted net (its traits minus the selling club's):")
        prof = [("deadline rental for picks and prospects", {"t_rental": 1, "t_deadline_buyer": 1, "t_futures": -1}),
                ("the same, the rental aged 28 to 31", {"t_rental": 1, "t_deadline_buyer": 1, "t_futures": -1, "t_age28": 1}),
                ("a clause veteran aged 28 to 31 for picks and prospects", {"t_clause": 1, "t_age28": 1, "t_futures": -1})]
        for lab, w in prof:
            v = np.zeros(len(names))
            for c, x in w.items():
                if c in names:
                    v[names.index(c)] = x
            cells = []
            for y_ in ("net_M", "out_net_M", "gv_net_M"):
                e = float(res[y_][0] @ v)
                bb = res["_boots"][y_] @ v
                lo_, hi_ = np.percentile(bb, [2.5, 97.5])
                cells.append(f"{e:+.2f} [{lo_:+.2f},{hi_:+.2f}]")
                OUT.append({"scope": scope, "trait": "deal: " + lab, "outcome": y_, "together": e, "lo": lo_, "hi": hi_})
            log(f"    {lab:<56}" + "".join(f"{x:>22}" for x in cells))
    pd.DataFrame(OUT).to_csv(OUTPUT_DIR / f"joint_regression{TAG}.csv", index=False)
    (OUTPUT_DIR / f"joint_regression{TAG}_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
