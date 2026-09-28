"""npv_spine_compare.py -- contract-by-contract: what a re-run moved in contract_npv_spine.csv.

Read-only. Compares two copies of the NPV spine (before and after a re-run)
and writes a plain-text summary; it never edits either file and writes only
its own log.

Written 2026-09-28 for the D3 revision (the aging curve fitted per valuation
page) together with the corrected age table (Elite Prospects ages restored;
ten sibling birthdates fixed). The two changes ran together, so this shows
their combined effect contract by contract; it cannot split them.

USAGE (from the repo root)
    python 20_CODE/npv_spine_compare.py OLD.csv NEW.csv [LOG.txt]
LOG defaults to npv_spine_compare_log.txt beside NEW.csv.

WHAT IT CHECKS FIRST
    * the same contracts are priced in both (key: contract_id + valuation
      season); any contract in only one file is listed, never dropped;
    * identity fields (player, position, valuation season, seasons) agree
      for every matched contract.
MONEY PRECISION: dollars are rounded to $1 before "moved" / "unchanged" is
decided, so a $1e-10 float difference is not counted as a move.
"""
from pathlib import Path
import sys

import pandas as pd

SCRIPT_VERSION = "1.0"
KEY = ["contract_id", "valuation_season"]
IDENT = ["player_id", "full_name", "position", "n_seasons"]
MONEY = ["npv_contract", "npv_terminal", "npv_total"]
# the ten players whose birthdates were corrected on 2026-09-28 (age_join.py Pass 5)
SIBLING_FIXED = ["Rick Nash", "Marcel Hossa", "Jared Staal", "Taylor Pyatt", "Brett Sutter",
                 "Brody Sutter", "Mark Cullen", "Patrick Holland", "Chris Brown", "Jeff Schultz"]


def main(old_path, new_path, log_path):
    lines = []
    def log(s=""):
        print(s); lines.append(s)
    log(f"npv_spine_compare.py v{SCRIPT_VERSION}")
    log(f"  old: {old_path}")
    log(f"  new: {new_path}")
    old, new = pd.read_csv(old_path), pd.read_csv(new_path)
    for d, nm in ((old, "old"), (new, "new")):
        assert not d.duplicated(KEY).any(), f"{nm} spine has duplicate contract keys"
    j = old.merge(new, on=KEY, how="outer", suffixes=("_old", "_new"), indicator=True)
    only_old, only_new = j[j._merge == "left_only"], j[j._merge == "right_only"]
    m = j[j._merge == "both"].copy()
    log(f"\ncontracts: old {len(old):,}  new {len(new):,}  in both {len(m):,}  "
        f"only old {len(only_old)}  only new {len(only_new)}")
    for lab, d, suf in (("only in OLD", only_old, "_old"), ("only in NEW", only_new, "_new")):
        for _, r in d.iterrows():
            log(f"  {lab}: {r['full_name' + suf]} {int(r['valuation_season'])} "
                f"(contract {r['contract_id']}) NPV ${r['npv_total' + suf] / 1e6:+.2f}M")
    def differs(c):
        a, b = m[c + "_old"], m[c + "_new"]
        if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
            return bool((a.astype(float) != b.astype(float)).any())   # the outer join makes ints float
        return bool((a.astype(str) != b.astype(str)).any())
    bad = [c for c in IDENT if differs(c)]
    assert not bad, f"identity fields differ between the two spines: {bad}"
    log("  identity fields (player, position, seasons) agree on every matched contract")

    for c in MONEY:
        m[c + "_d"] = m[c + "_new"].round(0) - m[c + "_old"].round(0)
    d = m["npv_total_d"]
    moved = d != 0
    log(f"\nNPV (contract + terminal), rounded to $1:")
    log(f"  moved: {int(moved.sum()):,} of {len(m):,}   up {int((d > 0).sum()):,}   "
        f"down {int((d < 0).sum()):,}   unchanged {int((~moved).sum()):,}")
    log(f"  total change ${d.sum() / 1e6:+,.1f}M   mean ${d.mean() / 1e6:+.3f}M   "
        f"median ${d.median() / 1e6:+.3f}M")
    if moved.any():
        q = d[moved].abs().quantile([.5, .9]).to_list()
        log(f"  among moved: median |change| ${q[0] / 1e6:.3f}M, 90th percentile ${q[1] / 1e6:.3f}M, "
            f"largest ${d.abs().max() / 1e6:.2f}M")
    log(f"  of which contract part ${m['npv_contract_d'].sum() / 1e6:+,.1f}M, "
        f"terminal (RFA control years) ${m['npv_terminal_d'].sum() / 1e6:+,.1f}M")
    for lab, s in (("old", "_old"), ("new", "_new")):
        x = m["npv_total" + s] / 1e6
        log(f"  distribution {lab}: p10 {x.quantile(.1):+.2f}  median {x.median():+.2f}  "
            f"p90 {x.quantile(.9):+.2f}  ($M)")

    def table(by, title):
        log(f"\n{title}:")
        g = m.groupby(by)
        t = pd.DataFrame({"n": g.size(), "moved": g["npv_total_d"].apply(lambda x: int((x != 0).sum())),
                          "total_$M": g["npv_total_d"].sum() / 1e6,
                          "mean_$M": g["npv_total_d"].mean() / 1e6})
        for k, r in t.iterrows():
            log(f"  {str(k):<24} n {int(r.n):>5}  moved {int(r.moved):>5}  "
                f"total {r['total_$M']:+9.1f}  mean {r['mean_$M']:+7.3f}")
    table("position_old", "by position")
    table("path_old", "by projection path (old run's label)")
    m["path_change"] = m["path_old"].astype(str) + " -> " + m["path_new"].astype(str)
    ch = m[m["path_old"].astype(str) != m["path_new"].astype(str)]
    log(f"\nprojection path changed on {len(ch)} contracts")
    for k, n in ch["path_change"].value_counts().items():
        log(f"  {k:<45} {n}")
    table("valuation_season", "by valuation season")
    m["tier"] = pd.cut(m["npv_total_old"] / 1e6, [-1e9, -20, -5, 0, 5, 1e9],
                       labels=["below -20", "-20 to -5", "-5 to 0", "0 to 5", "above 5"])
    table("tier", "by old NPV ($M)")

    show = ["full_name_old", "valuation_season", "n_seasons_old", "path_old", "path_new",
            "npv_total_old", "npv_total_new", "npv_total_d"]
    for lab, sub in (("largest increases", m[m["npv_total_d"] > 0].nlargest(15, "npv_total_d")),
                     ("largest decreases", m[m["npv_total_d"] < 0].nsmallest(15, "npv_total_d"))):
        log(f"\n{lab}:")
        for _, r in sub[show].iterrows():
            log(f"  {r.full_name_old:<24} {int(r.valuation_season)} {int(r.n_seasons_old)}yr  "
                f"{r.path_old}->{r.path_new}  ${r.npv_total_old / 1e6:+7.2f}M -> "
                f"${r.npv_total_new / 1e6:+7.2f}M  ({r.npv_total_d / 1e6:+.2f}M)")
    sib = m[m["full_name_old"].isin(SIBLING_FIXED)]
    log(f"\nthe ten players with corrected birthdates: {len(sib)} priced contracts")
    for _, r in sib[show].iterrows():
        log(f"  {r.full_name_old:<24} {int(r.valuation_season)} {int(r.n_seasons_old)}yr  "
            f"${r.npv_total_old / 1e6:+7.2f}M -> ${r.npv_total_new / 1e6:+7.2f}M  ({r.npv_total_d / 1e6:+.2f}M)")
    Path(log_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote {log_path}")


if __name__ == "__main__":
    # A Windows console on a legacy code page cannot print every accented name
    # (e.g. Slafkovsky's y-acute); print a stand-in rather than crash. The log file is UTF-8.
    sys.stdout.reconfigure(errors="replace")
    if len(sys.argv) < 3:
        raise SystemExit("usage: python 20_CODE/npv_spine_compare.py OLD.csv NEW.csv [LOG.txt]")
    old_p, new_p = Path(sys.argv[1]), Path(sys.argv[2])
    log_p = Path(sys.argv[3]) if len(sys.argv) > 3 else new_p.with_name("npv_spine_compare_log.txt")
    main(old_p, new_p, log_p)
