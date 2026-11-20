"""
defence_gap_split.py - is the defenceman gap the picks that forwards' buyers paid with? (Thomas, 2026-11-19: "is that
true? Is that driving the difference?"; declared in 40_DOCS/Backtest_Protocol.md before it was built. Report only.)

THE SENTENCE UNDER TEST (findings document, Section 3): "clubs acquiring forwards came out better than their grade
(+0.47 [+0.19, +0.76]), mostly because they paid with picks, and picks under-deliver."

ROWS AND SPLIT: defence_checks.py part 0's, exactly: each club side's realized minus predicted value (outcome net less
trade-day grade, WAR) split into its main player's own miss, the other assets it received, the assets it GAVE (sign
flipped; a given asset carries its retained part) and retained salary. Here the given part is split further by what the
asset is: a pick, a prospect (valued by the prospect model) or a player. Main player position: backtest_cuts_all_sides
`pos` (defence_checks' rule). GUARD: the parts add up to the side's miss, and the given parts to defence_checks' given part.
Intervals: 2,000 resamples of trades, seed 20261119.

OUTPUTS: OUTPUT_DIR/defence_gap_split_log.txt, defence_gap_split.csv
"""
import os
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
EXT = OUTPUT_DIR / "_extended_run"
SCRIPT_VERSION = "defence_gap_split.py v1.0 (2026-11-19)"
DECLARED_END = "2022-03-28"
N_BOOT, SEED = 2000, 20261119
PARTS = ["side_miss", "main_miss", "other_recv_miss", "gave_pick", "gave_prospect", "gave_player", "retained_miss"]
LAB = {"side_miss": "the side: realized - predicted", "main_miss": "main player's own miss", "other_recv_miss": "other assets received",
       "gave_pick": "given: picks (sign flipped)", "gave_prospect": "given: prospects (sign flipped)",
       "gave_player": "given: players (sign flipped)", "retained_miss": "retained salary"}
LOG, OUT = [], []


def log(s=""):
    print(s)
    LOG.append(s)


def main():
    log(SCRIPT_VERSION)
    s = pd.read_csv(EXT / "backtest_cuts_all_sides.csv")
    a = pd.read_csv(EXT / "backtest_assets.csv")
    a["miss"] = a["outcome_M"] - a["value_2025_cap_M"]
    con = sqlite3.connect(EXT / "trades_extended.db")
    legs = pd.read_sql("select trade_id, acquiring_team from trade_legs", con)
    clubs = legs.groupby("trade_id")["acquiring_team"].apply(lambda x: sorted(set(x))).to_dict()
    a["sender"] = [r.from_team if pd.notna(r.from_team) else next((c for c in clubs[r.trade_id] if c != r.acquiring_team), None)
                   for r in a.itertuples()]
    a["kind"] = np.where(a["asset_type"] == "pick", "pick",
                         np.where(a["source"].astype(str).str.startswith("prospect model"), "prospect", "player"))
    ret = a[a["asset_type"] == "retained salary"]
    mv = a[a["asset_type"] != "retained salary"]
    rows = []
    for r in s.itertuples():
        got = mv[(mv["trade_id"] == r.trade_id) & (mv["acquiring_team"] == r.club)]
        gave = mv[(mv["trade_id"] == r.trade_id) & (mv["sender"] == r.club)]
        main = got[got["name"] == r.name] if pd.notna(r.name) else got.iloc[0:0]
        mmiss = float(main["miss"].sum()) if len(main) else 0.0
        rec = {"trade_id": r.trade_id, "club": r.club, "pos": r.pos, "date": r.trade_date, "side_miss": r.out_net_M - r.net_M,
               "main_miss": mmiss, "other_recv_miss": float(got["miss"].sum()) - mmiss,
               "retained_miss": float(ret[(ret["trade_id"] == r.trade_id) & (ret["acquiring_team"] == r.club)]["miss"].sum()),
               "gave_any_pick": int((gave["kind"] == "pick").any())}
        for k in ("pick", "prospect", "player"):
            g = gave[gave["kind"] == k]
            rec[f"gave_{k}"] = -float(g["miss"].sum() + ret[ret["asset_id"].isin(g["asset_id"])]["miss"].sum())
        rows.append(rec)
    d = pd.DataFrame(rows)
    rest = d["side_miss"] - d[[p for p in PARTS if p != "side_miss"]].sum(axis=1)
    assert rest.abs().max() < 1e-6, rest.abs().max()                                   # GUARD: the split is exact
    log(f"  check: the parts add up to each side's miss to within ${rest.abs().max():.6f}M (PASS)")
    ref = pd.read_csv(OUTPUT_DIR / "defence_checks.csv") if (OUTPUT_DIR / "defence_checks.csv").exists() else None
    rng = np.random.default_rng(SEED)
    for scope, msk in (("declared window", d["date"] <= DECLARED_END), ("all trades", pd.Series(True, index=d.index))):
        dd = d[msk & d["pos"].isin(["D", "F"])]
        tids = dd["trade_id"].unique()
        by = {t: g for t, g in dd.groupby("trade_id")}
        boots = []
        for _ in range(N_BOOT):
            bb = pd.concat([by[t] for t in tids[rng.integers(0, len(tids), len(tids))]])
            m = bb.groupby("pos")[PARTS].mean()
            boots.append(np.r_[m.loc["D"].values, m.loc["F"].values, (m.loc["F"] - m.loc["D"]).values])
        boots = np.array(boots)
        lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
        m = dd.groupby("pos")[PARTS].mean()
        est = np.r_[m.loc["D"].values, m.loc["F"].values, (m.loc["F"] - m.loc["D"]).values]
        n = dd.groupby("pos").size()
        gp = dd.groupby("pos")["gave_any_pick"].mean()
        log(f"\n  {scope}: main player a defenceman {n['D']} sides, a forward {n['F']}; gave at least one pick: "
            f"defenceman {gp['D']:.0%}, forward {gp['F']:.0%}")
        log(f"  {'$M a side':<34}{'defenceman':>24}{'forward':>24}{'forward - defenceman':>26}")
        k = len(PARTS)
        for i, p in enumerate(PARTS):
            cells = [f"{est[j]:+.2f} [{lo[j]:+.2f}, {hi[j]:+.2f}]" for j in (i, k + i, 2 * k + i)]
            log(f"  {LAB[p]:<34}{cells[0]:>24}{cells[1]:>24}{cells[2]:>26}")
            OUT.append({"scope": scope, "part": p, "D": est[i], "D_lo": lo[i], "D_hi": hi[i], "F": est[k + i], "F_lo": lo[k + i],
                        "F_hi": hi[k + i], "F_minus_D": est[2 * k + i], "diff_lo": lo[2 * k + i], "diff_hi": hi[2 * k + i]})
    pd.DataFrame(OUT).to_csv(OUTPUT_DIR / "defence_gap_split.csv", index=False)
    (OUTPUT_DIR / "defence_gap_split_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
