"""goalie_season_table.py -- the goaltender panel, on the skater's conventions.

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 5, the goalie branch. Nothing
adopted.

WHY A SECOND TABLE AND NOT A SECOND COPY
    Everything downstream of the season table -- the information set, the
    harness, the scoring -- is written against a schema, not against skaters.
    So a goalie table with the same columns plugs into all of it unchanged,
    and this module's whole job is to produce that schema from a different
    source without re-deciding any rule the skater table already settled.

    The rules it REUSES rather than restates: name normalisation and the
    career key, D20 schedule proration, the games share against the schedule
    the season actually had, the per-82 rate built from the raw total so the
    two schedule adjustments cancel, experience from the table itself with
    its left-censoring flag, and the birthdate join. All imported.

WHAT IS GENUINELY DIFFERENT, AND IS NOT A STYLE CHOICE
    ONE NUMBER, NOT SIX. The goalie source carries a single WAR with no
    component split, so the component-wise forecast has nothing to work on
    here. The candidates in the bake-off are all total-WAR rules.

    GAMES ARE A ROLE, NOT ONLY AVAILABILITY. A skater who plays 40 of 82 was
    hurt. A goaltender who plays 40 of 82 may be a healthy starter in a
    tandem, or a backup, or a starter who missed a month -- the source cannot
    tell them apart, and a team carries two goaltenders where it carries
    twelve forwards. So `gp_share` is computed the same way for continuity
    and is NOT availability for a goalie. Anything that reads it as
    availability, including the participation model, has to say so first.
    The median starter's share and the median goalie's share are printed on
    every run so that difference stays visible.

    THE ELIGIBILITY THRESHOLD IS THE SKATER'S AND THAT IS A CHOICE. `MIN_GP`
    is 10 games, chosen for skaters. Ten games is a third of a backup's
    season, so it admits goaltenders on much thinner evidence than it admits
    skaters. The table keeps the shared threshold so the two panels stay
    comparable, prints how many goalie-seasons sit between 10 and 20 games,
    and leaves the decision to the consumer.

WHAT THIS IS NOT
    Not a forecast, not a price, not adopted. It is the panel the goalie
    bake-off is scored on.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
from player_season_table import _attach_age, career_key, norm_name

SCRIPT_VERSION = "1.0"

# The position tag goalie rows carry, so a mixed table can be split again and
# a consumer that forgets to filter fails visibly rather than averaging a
# goaltender into a forward norm.
POS = "G"


def build(birthdate_csv: Path | None = None, verbose: bool = True,
          allow_thin_ages: bool = False) -> pd.DataFrame:
    """The goalie season table, in the skater table's schema.

    Order of operations follows the skater build for the same reasons: sum a
    traded goaltender's team-halves into one season row BEFORE anything is
    divided by games, then rate, then D20, then the share.
    """
    src = C.assert_read_only_source(C.F_WAR_GOALIES)
    g = pd.read_csv(src)
    n_raw = len(g)

    g["syr"] = g["Season"].str.split("-").str[0].astype(int) + 2000
    g["pkey"] = g["Goalie"].map(norm_name) + "|" + POS
    g["career_key"] = g["Goalie"].map(career_key)

    # TEAM-HALVES FIRST. A goaltender traded mid-season appears twice, and
    # summing after dividing by games would average two rates weighted by
    # nothing. Minutes and games add; WAR adds because it is a season total.
    a = (g.groupby(["career_key", "pkey", "syr"], as_index=False)
          .agg(WAR=("WAR", "sum"), GP=("GP", "sum"), TOI=("TOI", "sum"),
               SA=("SA", "sum"), GSAx=("GSAx", "sum"),
               teams=("Team", lambda s: "/".join(sorted(set(s))))))
    n_halves = n_raw - len(a)
    a["pos"] = POS

    # THE RATE FROM THE RAW TOTAL, before D20, so the proration in the total
    # and the schedule in the share cancel exactly -- the skater table's
    # reason, and it holds here for the same arithmetic.
    a["WAR_82"] = a["WAR"] / a["GP"] * C.FULL_SEASON
    a["WAR"] = a["WAR"] * a["syr"].map(C.PRORATION).fillna(1.0)

    sched = a["syr"].map(C.SEASON_LEN).fillna(float(C.FULL_SEASON))
    a["gp_share"] = (a["GP"] / sched).clip(upper=1.0)
    a["toi_pg"] = a["TOI"] / a["GP"]
    # Shots faced per game: the one exposure measure a goaltender has that a
    # skater does not, carried because workload is the obvious candidate for
    # weighting his evidence and it should not need a second source later.
    a["sa_pg"] = a["SA"] / a["GP"]

    a = a.sort_values(["career_key", "syr"]).reset_index(drop=True)
    first = a.groupby("career_key")["syr"].transform("min")
    a["exp_seasons"] = a["syr"] - first
    a["exp_censored"] = first <= C.FIRST_SOURCE_SEASON

    a["age"], a["age_exact"] = np.nan, np.nan
    a["has_age"] = False
    if birthdate_csv is not None:
        a = _attach_age(a, Path(birthdate_csv))
        cov = float(a["has_age"].mean())
        if cov < C.MIN_AGE_COVERAGE and not allow_thin_ages:
            raise AssertionError(
                f"goalie age coverage is {cov:.1%}, below the "
                f"{C.MIN_AGE_COVERAGE:.0%} this table proceeds on. Pass "
                "allow_thin_ages=True to proceed and starve any age term.")

    a = a.sort_values(["career_key", "syr", "pkey"]).reset_index(drop=True)

    if verbose:
        thin = int(((a["GP"] >= C.MIN_GP) & (a["GP"] < 20)).sum())
        qual = a[a["GP"] >= C.MIN_GP]
        C.log(f"  source rows              {n_raw}")
        C.log(f"  team-halves summed       {n_halves} rows away")
        C.log(f"  season rows              {len(a)}")
        C.log(f"  goaltenders              {a['career_key'].nunique()}")
        C.log(f"  seasons covered          {a['syr'].min()}-{a['syr'].max()}")
        C.log(f"  per season               {len(a) / a['syr'].nunique():.0f} "
              f"goalie-seasons, against ~700 skater-seasons")
        C.log(f"  age coverage             {a['has_age'].mean():.1%}")
        C.log(f"  at or above MIN_GP={C.MIN_GP}      {len(qual)} rows, of which "
              f"{thin} sit between {C.MIN_GP} and 20 games")
        C.log(f"  games share, median      {qual['gp_share'].median():.2f} "
              f"overall, {qual[qual['GP'] >= 40]['gp_share'].median():.2f} "
              f"among 40-game goaltenders")
        C.log("  A goaltender's games share is NOT availability: a team")
        C.log("  carries two of them, so a low share can be a backup role, a")
        C.log("  tandem, or an injury and the source cannot tell them apart.")
    return a


def self_test() -> None:
    """The arithmetic that has to hold, on the real panel."""
    a = build(verbose=False)
    # The rate is the raw total per 82 games, so a full season's rate equals
    # its total in an unprorated year.
    full = a[(a["GP"] == 82) & (~a["syr"].isin(C.PRORATION))]
    if len(full):
        assert np.allclose(full["WAR_82"], full["WAR"], atol=1e-9)
    # D20 scaled the shortened seasons and nothing else.
    for yr, factor in C.PRORATION.items():
        assert abs(factor - C.FULL_SEASON / C.SEASON_LEN[yr]) < 1e-12
    # One row per goaltender-season, after the halves are summed.
    assert not a.duplicated(["career_key", "syr"]).any()
    # Every row carries the schema the harness reads.
    need = {"pkey", "career_key", "syr", "pos", "WAR", "WAR_82", "GP",
            "gp_share", "exp_seasons", "exp_censored", "age", "has_age"}
    assert need <= set(a.columns), need - set(a.columns)
    C.log(f"  self-test passes on {len(a)} goalie-seasons")


def main() -> None:
    C.banner("goalie_season_table.py", SCRIPT_VERSION)
    from player_season_table import birthdate_source
    path, how = birthdate_source()
    C.log(f"  birthdates: {how}")
    C.log("")
    build(birthdate_csv=path, allow_thin_ages=True)
    C.log("")
    self_test()
    C.write_log("goalie_season_table_run_log.txt")


if __name__ == "__main__":
    main()
