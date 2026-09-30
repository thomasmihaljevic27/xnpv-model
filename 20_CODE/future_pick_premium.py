"""
future_pick_premium.py -- what pick-for-pick trades imply about how clubs
discount a pick in a later draft.

SCRIPT_VERSION = 2.0  (2026-09-28)

RECREATED 2026-09-28. The July 2026 version could not be found anywhere (see
slot_curve.py). This one is rebuilt from the findings recorded in
DECISIONS.md / 01_Draft_Model_Sequence.md, and it must reproduce the recorded
sample before any estimate is printed (the guard below).

THE QUESTION
------------
A pick in next year's draft is worth less on the trade date than the same
slot this year: the player arrives a year later, and the club is less sure
where the pick will land. If clubs trade picks at the curve's values, then in
a trade of picks across drafts, sum(value x d^k) should match on both sides,
where k is how many drafts after the next one the pick belongs to, and d is
the discount factor per draft. One unknown, d. This script solves for it.

THE SAMPLE (reproduction guard, all five must match the 2026-07-28 record)
--------------------------------------------------------------------------
  119  trades made only of picks, at least two pick rows (7 single-row
       "trades", a pick sent for nothing recorded, are excluded)
   56  of those involve picks from more than one draft (only these say anything
       about d)
   39  of the 56 are one-for-one
   35  of the 39 are same-round swaps (almost no information)
   17  bundle trades (cross-draft, three or more picks): the estimation sample

WHAT THE RECORD SAYS, AND WHAT IS NOT KNOWN ABOUT HOW IT WAS COMPUTED
----------------------------------------------------------------------
Recorded (2026-07-28): pooled d = 0.486 under the round-mean convention and
0.510 under team-own-slot, on the PRE-rebuild curve; about 0.503 once the
steeper rebuilt curve was approximated; per-trade values 0.015 to 0.689;
Spearman 0.735 between sweetener size and the slot gap it buys. The fitting
criterion behind "pooled" is not recorded. Here it is least squares on the
cap-share gap between the two sides. Treat the pooled figures as comparable
in size, not as a reproduction; the sample counts are the reproduction.

CONVENTIONS (each is a choice that can move d)
----------------------------------------------
- k: the next draft on or after the trade date is k=0; a pick one draft
  later is k=1, and so on.
- A pick's number counts as KNOWN only from three days before its draft (by
  then the playoffs are over and the order is set). Inside that window the
  export's overall_position is the real slot and is not look-ahead. Outside it,
  overall_position is never read (it is back-filled with a number nobody knew
  on the day), and the slot comes from a convention:
    round_mean: average curve value of that round;
    own_slot:   the original team's position in the last draft held
                (decided 2026-09-28; see slot_curve.own_slot_overall).
- Conditional picks are taken as conveyed at their stated round (decided
  2026-09-28: assume conditions are met). The export's condition flags are
  as of the export date and are not read.
- Values are Rule A cap shares from the current banded curve. The break-test
  curve replaces it through slot_curve.py.

Outputs: OUTPUT_DIR/future_pick_premium_diagnostics.csv (one row per
cross-draft trade and convention), future_pick_premium_run_log.txt
Run: python 20_CODE/future_pick_premium.py
"""

import os
import sys

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from scipy.optimize import brentq, minimize_scalar
from scipy.stats import spearmanr

load_dotenv()
sys.path.insert(0, os.environ.get("CODE_DIR", os.path.dirname(__file__)))
import slot_curve as sc  # noqa: E402

SCRIPT_VERSION = "2.0"
OUTPUT_DIR = os.environ["OUTPUT_DIR"]
TRADES_XLSX = os.environ["PUCKPEDIA_TRADES_XLSX"]
OUT_CSV = os.path.join(OUTPUT_DIR, "future_pick_premium_diagnostics.csv")
OUT_LOG = os.path.join(OUTPUT_DIR, "future_pick_premium_run_log.txt")
KNOWN_WINDOW_DAYS = 3
RECORDED = {"all_pick": 119, "cross": 56, "one_for_one": 39, "same_round": 35, "bundles": 17}

_lines = []


def log(m=""):
    print(m)
    _lines.append(str(m))


def load_pick_trades() -> pd.DataFrame:
    t = pd.read_excel(TRADES_XLSX, sheet_name="trade_export")
    t["trade_date"] = pd.to_datetime(t["trade_date"])
    all_pick = t.groupby("trade_id")["draft_pick_id"].apply(lambda s: s.notna().all())
    pk = t[t["trade_id"].isin(all_pick[all_pick].index)].copy()
    size = pk.groupby("trade_id").size()
    pk = pk[pk["trade_id"].isin(size[size >= 2].index)]
    return pk


def next_draft_year(d: pd.Timestamp) -> int:
    y = d.year
    dd = sc.draft_date(y)
    if dd is None or d <= dd:
        return y
    return y + 1


def price_rows(pk: pd.DataFrame, convention: str) -> pd.DataFrame:
    out = pk.copy()
    ks, vals, how = [], [], []
    for _, r in out.iterrows():
        y, rnd, d = int(r.draft_year), int(r.draft_round), r.trade_date
        ks.append(y - next_draft_year(d))
        dd = sc.draft_date(y)
        known = dd is not None and d >= dd - pd.Timedelta(days=KNOWN_WINDOW_DAYS) \
            and pd.notna(r.overall_position)
        if known:
            vals.append(sc.slot_value(int(r.overall_position)))
            how.append("known slot")
        elif convention == "round_mean":
            vals.append(sc.round_mean_value(y, rnd))
            how.append("round mean")
        else:
            o, h = sc.own_slot_overall(r.draft_pick_team, y, rnd, d)
            vals.append(sc.slot_value(o))
            how.append(h)
    out["k"], out["value"], out["slot_source"] = ks, vals, how
    return out


def gap_fn(tr: pd.DataFrame):
    """f(d) = value side A gives minus value side B gives, at discount d."""
    teams = sorted(tr["from_team"].unique())
    a = tr[tr["from_team"] == teams[0]]
    b = tr[tr["from_team"] != teams[0]]
    return lambda dd: float((a.value * dd ** a.k).sum() - (b.value * dd ** b.k).sum())


def implied_d(f):
    lo, hi = 1e-6, 1.0
    flo, fhi = f(lo), f(hi)
    if np.sign(flo) == np.sign(fhi):
        return np.nan                       # no discount in (0, 1] balances it
    return brentq(f, lo, hi)


def main():
    log(f"future_pick_premium.py SCRIPT_VERSION {SCRIPT_VERSION} "
        f"(slot_curve {sc.SCRIPT_VERSION})")
    pk = load_pick_trades()
    ny = pk.groupby("trade_id")["draft_year"].nunique()
    n = pk.groupby("trade_id").size()
    cross = ny[ny > 1].index
    one = [i for i in cross if n[i] == 2]
    same = [i for i in one if pk.loc[pk.trade_id == i, "draft_round"].nunique() == 1]
    bundles = [i for i in cross if n[i] > 2]
    got = {"all_pick": pk.trade_id.nunique(), "cross": len(cross),
           "one_for_one": len(one), "same_round": len(same), "bundles": len(bundles)}
    log("[guard] sample vs 2026-07-28 record: " + ", ".join(
        f"{k} {got[k]}/{RECORDED[k]}" for k in RECORDED))
    if got != RECORDED:
        sys.exit("[guard] FAILED: the sample does not reproduce the record; no estimate printed.")

    diag = []
    for conv in ("round_mean", "own_slot"):
        priced = price_rows(pk[pk.trade_id.isin(cross)], conv)
        log(f"\n[{conv}] slot sources: " + ", ".join(
            f"{k} {v}" for k, v in priced.slot_source.str.split(" in ").str[0]
            .value_counts().items()))
        fs = {i: gap_fn(priced[priced.trade_id == i]) for i in bundles}
        pooled = minimize_scalar(lambda dd: sum(f(dd) ** 2 for f in fs.values()),
                                 bounds=(1e-6, 1.0), method="bounded").x
        per = {i: implied_d(f) for i, f in fs.items()}
        vals = pd.Series(per).dropna()
        log(f"[{conv}] pooled d (least squares, 17 bundles) = {pooled:.3f}; "
            f"per-trade d solvable in (0,1] for {len(vals)} of 17, range "
            f"{vals.min():.3f} to {vals.max():.3f}")
        sw, gp = [], []
        for i in bundles:
            tr = priced[priced.trade_id == i]
            fut = tr[tr.k > 0].groupby("from_team").value.sum()
            cur = tr[tr.k == 0].groupby("from_team").value.sum()
            sweet = float(fut.max()) if len(fut) else 0.0
            giver = fut.idxmax() if len(fut) else None
            gap = float(cur.drop(giver, errors="ignore").sum()
                        - cur.get(giver, 0.0)) if giver else np.nan
            sw.append(sweet)
            gp.append(gap)
            diag.append({"convention": conv, "trade_id": i,
                         "trade_date": tr.trade_date.iloc[0].date(),
                         "n_picks": len(tr), "implied_d": per[i],
                         "sweetener_share": sweet, "slot_gap_share": gap,
                         "pooled_d": pooled})
        rho = spearmanr(sw, gp, nan_policy="omit").correlation
        log(f"[{conv}] Spearman(sweetener, slot gap) = {rho:.3f} (recorded 0.735)")
    log("\nRecorded 2026-07-28 (pre-rebuild curve): 0.486 round-mean, 0.510 own-slot; "
        "about 0.503 on the approximated rebuilt curve. Not a reproduction target "
        "(fitting criterion unrecorded; own-slot rule revised 2026-09-28).")
    pd.DataFrame(diag).to_csv(OUT_CSV, index=False)
    with open(OUT_LOG, "w", encoding="utf-8") as fh:
        fh.write("\n".join(_lines) + "\n")
    log(f"[done] wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
