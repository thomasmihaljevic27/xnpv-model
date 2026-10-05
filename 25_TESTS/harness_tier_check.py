"""harness_tier_check.py -- does forecast_harness v1.4's tier label do what it says?

WHY (Thomas, 2026-10-05: "switch the harness label"). forecast_harness.subjects_at labelled each
player's tier ("star" = 3+) on the 60/40 two-season WAR total; v1.4 labels it on the forecast's own
trailing total, the plain 50/30/20 WAR total over the three seasons before the page (10+ game
seasons, rescaled; skater_forecast._anchors' tw_WAR). Two claims to hold it to. CHECK ONLY.

WHAT IT ASSERTS, on each development page 2015-2021:
  1. THE SUBJECT LIST IS UNCHANGED. The players v1.4 keeps are exactly the players the v1.3 rule
     (60/40 of the last two seasons, falling back to the last, then the one before, then the third)
     kept. skater_forecast's tail decay reads this list, so an unchanged list means no forecast moves.
  2. THE LABEL IS THE FORECAST'S TRAILING TOTAL. trailing_war equals skater_forecast._anchors' tw_WAR
     for each subject (tolerance 1e-12), and the tier is that total cut at 0, 1, 2 and 3 wins.
  It also prints how many player-pages change tier.

HOW TO RUN (repo root, laptop; under a minute):
    python 25_TESTS/harness_tier_check.py
Writes 30_OUTPUT/harness_tier_check_log.txt. A failed assertion stops the run.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
import numpy as np
import pandas as pd

import forecast_config as C
import forecast_harness as H
import information_set as ISET
import player_season_table as PST
import skater_forecast as SF

SCRIPT_VERSION = "1.0"
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def old_trailing(iset, keys):
    """forecast_harness v1.3's tier total, line for line: 60/40 of the two most recent qualifying
    seasons, else the most recent, else the one before, else the third."""
    recent = iset.seasons[iset.seasons["syr"] > iset.latest_season - H.ACTIVE_WINDOW]
    played = recent[recent["GP"] >= C.MIN_GP]
    t1, t2, t3 = iset.latest_season, iset.latest_season - 1, iset.latest_season - 2
    w = [played[played["syr"] == t].set_index("career_key")["WAR"].reindex(keys) for t in (t1, t2, t3)]
    return (w[0] * 0.6 + w[1] * 0.4).fillna(w[0]).fillna(w[1]).fillna(w[2])


def main():
    log(f"harness_tier_check.py v{SCRIPT_VERSION}; forecast_harness v{H.SCRIPT_VERSION}, skater_forecast v{SF.SCRIPT_VERSION}")
    assert H.SCRIPT_VERSION == "1.4", "this check is for forecast_harness v1.4"
    bd, how = PST.birthdate_source()
    table = PST.build(birthdate_csv=bd, verbose=False)
    moved = []
    for t0 in C.DEV_PAGES:
        iset = ISET.build(table, ISET.decision_date_for_page(t0), t0=t0)
        assert iset.latest_season == t0 - 1, f"page {t0}: latest readable season {iset.latest_season}, not {t0 - 1}"
        subs = H.subjects_at(iset).set_index("career_key")
        # 1. the subject list: everyone with a qualifying season in the window, as v1.3 kept
        recent = iset.seasons[iset.seasons["syr"] > iset.latest_season - H.ACTIVE_WINDOW]
        cand = sorted(recent.loc[recent["GP"] >= C.MIN_GP, "career_key"].unique())
        old = old_trailing(iset, cand)
        old_keep = set(old.index[old.notna()])
        assert set(subs.index) == old_keep, (f"page {t0}: subject list changed "
                                             f"({len(set(subs.index) ^ old_keep)} players differ)")
        # 2. the label is tw_WAR
        an = SF._anchors(iset.seasons[iset.seasons["GP"] >= C.MIN_GP], SF.XNPV1.N_SEASONS)
        an = an[an["t0"] == t0].drop_duplicates("career_key").set_index("career_key")
        tw = an["tw_WAR"].reindex(subs.index)
        assert tw.notna().all(), f"page {t0}: a subject has no forecast trailing total"
        gap = float((subs["trailing_war"] - tw).abs().max())
        assert gap < 1e-12, f"page {t0}: label differs from tw_WAR by {gap:.1e}"
        want = pd.cut(tw, bins=H.TIER_EDGES, labels=H.TIER_NAMES, right=False).astype(str)
        assert (subs["tier"].astype(str) == want).all(), f"page {t0}: tier is not the total cut at 0-3"
        old_tier = pd.cut(old.reindex(subs.index), bins=H.TIER_EDGES, labels=H.TIER_NAMES, right=False).astype(str)
        moved.append(pd.DataFrame({"old": old_tier.to_numpy(), "new": subs["tier"].astype(str).to_numpy()}))
        log(f"  page {t0}: {len(subs):,} subjects, list unchanged; label = tw_WAR (largest gap {gap:.1e}); "
            f"tier changed for {int((old_tier.to_numpy() != subs['tier'].astype(str).to_numpy()).sum()):,}")
    m = pd.concat(moved, ignore_index=True)
    log("\nplayer-pages by tier, 2015-2021 (rows: v1.3's 60/40 label, columns: v1.4's 50/30/20 label):")
    log(pd.crosstab(m["old"], m["new"]).reindex(index=H.TIER_NAMES, columns=H.TIER_NAMES).fillna(0).astype(int).to_string())
    log("\nALL CHECKS PASS: the subject list is unchanged and the tier label is the forecast's 50/30/20 total.")
    p = Path(os.environ["OUTPUT_DIR"]) / "harness_tier_check_log.txt"
    p.write_text("\n".join(LOG) + "\n", encoding="utf-8")
    log(f"written: {p}")


if __name__ == "__main__":
    main()
