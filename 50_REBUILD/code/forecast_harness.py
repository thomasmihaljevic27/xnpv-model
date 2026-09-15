"""forecast_harness.py -- the scoreboard every candidate model is judged on.

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 0, item 5.

WHY THIS COMES FIRST
    Improvements measured on a leaky harness are artifacts. Both reviews of
    the player model put the harness ahead of any modelling, so it is built
    and its own acceptance test is run before a single candidate is fitted.

WHAT A MODEL IS, HERE
    A function from an InformationSet to a distribution over the next few
    seasons. Concretely, an object with:

        name                a short string
        fit(table, before)  fit on seasons whose OUTCOME is strictly before
                            `before`. Called once per page, so every fit is
                            rolling and no coefficient is ever estimated on
                            data the prediction has not yet lived through.
        predict(iset, hs)   one row per (career_key, horizon) with
                              rate_82     expected WAR per 82 games, GIVEN
                                          the player plays
                              gp_share    expected share of the schedule,
                                          GIVEN he plays
                              p_play      probability he plays at all
                            and optionally lo / hi, an 80% interval on the
                            season total.

    THE INTEGRATION RULE, asserted below and written once so no model can
    apply it twice: the expected season total is

        E[WAR] = p_play * rate_82 * gp_share

    The rate forecast is conditional on playing. Participation multiplies it
    exactly once. The production chain's separate exit-hazard haircut on an
    already-unconditional projection is the double count this removes.

WHAT IT SCORES, ALWAYS BY HORIZON AND SUBGROUP
    mean error and MAE in the per-82 rate (among players who played)
    mean error and MAE in the season total (zeros for players who did not)
    MAE in games played
    Brier score on participation -- the mean squared distance between the
      predicted probability of playing and what happened, 0 is perfect
    interval coverage -- how often the stated 80% range held the outcome

    Subgroups: horizon, level tier, position, experience band, and age band
    where ages exist. Aggregate improvement that hides a subgroup failure is
    the failure mode this project has already hit twice.

THE HOLDOUT SEAL
    Decision D: 2015-2021 are development pages, 2022-2025 are confirmatory
    and are touched once, at the end of Phase 5. The split is enforced here,
    in code. score() refuses a sealed page unless the caller passes
    unseal=True with a written reason, which is logged. Discipline that
    depends on remembering is discipline that fails.

NOT SCORED ON NPV
    Whether total NPV rises or falls is recorded elsewhere and is never a
    selection criterion. There is no dollar column in this file.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import information_set as ISET

SCRIPT_VERSION = "1.2"

DEFAULT_HORIZONS = (0, 1, 2, 3, 4, 5)   # h=0 is the valuation season itself

# Level tiers, on the trailing WAR the model itself starts from. These are the
# tiers the tilt was measured in (+24% at 3+), so the harness reproduces the
# known defect in the units it was found in.
TIER_EDGES = [-np.inf, 0.0, 1.0, 2.0, 3.0, np.inf]
TIER_NAMES = ["below 0", "0 to 1", "1 to 2", "2 to 3", "3+"]

EXP_EDGES = [-0.5, 2.5, 6.5, 10.5, np.inf]
EXP_NAMES = ["0-2", "3-6", "7-10", "11+"]

AGE_EDGES = [-np.inf, 22.5, 26.5, 30.5, 33.5, np.inf]
AGE_NAMES = ["<=22", "23-26", "27-30", "31-33", "34+"]

# A player is a SUBJECT at t0 if he played in the NHL in any of the last
# ACTIVE_WINDOW complete seasons. Wider than the anchor's own filter on
# purpose: a model must be scored on the players it would actually be asked
# about, including one coming off a lost season, not only on the players
# it finds easy.
ACTIVE_WINDOW = 3


def _bands(s, edges, names):
    return pd.cut(s, bins=edges, labels=names, right=False)


def subjects_at(iset: ISET.InformationSet) -> pd.DataFrame:
    """Who the model is asked about on this page, and the trailing facts the
    harness needs to classify them. Eligibility uses only the information
    set, so it is identical for every model -- a candidate cannot win by
    quietly declining the hard players."""
    recent = iset.seasons[iset.seasons["syr"] > iset.latest_season - ACTIVE_WINDOW]
    played = recent[recent["GP"] >= C.MIN_GP]

    last = (played.sort_values("syr").groupby("career_key")
            .agg(pkey=("pkey", "last"), pos=("pos", "last"),
                 last_syr=("syr", "last"), exp_seasons=("exp_seasons", "last"),
                 exp_censored=("exp_censored", "last"),
                 age=("age", "last"), has_age=("has_age", "last")))

    # Trailing level for the tier split: the locked 60/40 blend of the two
    # most recent qualifying seasons. Used ONLY to classify rows for
    # reporting; no model is obliged to use it as its own anchor.
    t1, t2, t3 = iset.latest_season, iset.latest_season - 1, iset.latest_season - 2
    w1 = played[played["syr"] == t1].set_index("career_key")["WAR"]
    w2 = played[played["syr"] == t2].set_index("career_key")["WAR"]
    w3 = played[played["syr"] == t3].set_index("career_key")["WAR"]
    both = w1.reindex(last.index) * 0.6 + w2.reindex(last.index) * 0.4
    # THE THIRD FALLBACK ADMITS THE RETURNERS. The window above says three
    # seasons and this line used to stop at two, so a player whose only
    # qualifying season was the oldest one in the window was dropped for having
    # no trailing level. That is not a neutral thinning of the sample: it
    # removes the players who missed a season and came back, which is precisely
    # the population the eligibility window was widened to admit and precisely
    # the population a survivorship-aware forecast has to be scored on.
    last["trailing_war"] = (both.fillna(w1.reindex(last.index))
                                .fillna(w2.reindex(last.index))
                                .fillna(w3.reindex(last.index)))
    last = last[last["trailing_war"].notna()]

    # HOW STALE the level behind each row is, carried so a report can say so
    # rather than presenting a two-year-old number as current.
    last["history_tier"] = np.where(
        w1.reindex(last.index).notna(), "current",
        np.where(w2.reindex(last.index).notna(), "one season stale",
                 "two seasons stale"))

    last["tier"] = _bands(last["trailing_war"], TIER_EDGES, TIER_NAMES)
    last["exp_band"] = _bands(last["exp_seasons"], EXP_EDGES, EXP_NAMES)
    # AGE AT THE VALUATION SEASON, not in the last season he happened to play.
    # The bands are reported as the population being forecast, so a returning
    # 22-year-old whose last season was at 20 was being counted in the "20 and
    # under" group and the group was not defined at the forecast date. The
    # models themselves were always aged correctly; this is the reporting side
    # of the same quantity.
    last["age_last_seen"] = last["age"]
    last["age"] = last["age"] + (iset.t0 - last["last_syr"])
    last["age_band"] = _bands(last["age"], AGE_EDGES, AGE_NAMES)
    return last.reset_index()


def outcomes(table: pd.DataFrame, t0: int, horizons=DEFAULT_HORIZONS) -> pd.DataFrame:
    """What actually happened, one row per (career_key, horizon).

    A player absent from the source in season t0+h did not play in the NHL
    that season: he is a ZERO in the season total and a False in `played`,
    not a missing row. Dropping him is the survivorship bias the participation
    model exists to price, and the reason the production chain's aging curve
    understates old-age decline.

    A horizon beyond the last season in the source is NOT observable and is
    left out entirely. An unplayed future is not a zero.
    """
    rows = []
    for h in horizons:
        s = t0 + h
        if s > C.LAST_SOURCE_SEASON:
            continue
        act = table[table["syr"] == s].set_index("career_key")
        rows.append(pd.DataFrame({
            "h": h, "season": s,
            "act_war": act["WAR"], "act_gp": act["GP"],
            "act_rate_82": act["WAR_82"], "act_gp_share": act["gp_share"],
        }).reset_index())
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _score_rows(pred: pd.DataFrame) -> pd.DataFrame:
    """Per-row errors. Everything the summary aggregates is computed once
    here so the two can never drift apart."""
    d = pred.copy()
    # The integration rule, applied in exactly one place in this codebase.
    d["pred_war"] = d["p_play"] * d["rate_82"] * d["gp_share"]

    # GAMES, on the schedule the outcome season actually had. The model
    # forecasts a SHARE of the schedule, and the scored outcome is a count of
    # games, so the conversion has to use that season's own length. Using a
    # flat 82 charged a player who was available for all 56 games of 2020-21 a
    # 26-game error for a season he did not miss.
    #
    # This reads the outcome season's length, which nobody knew at the
    # forecast date. That is legitimate here and only here: it converts the
    # units of a realized outcome for scoring, exactly as the realized WAR
    # total does. No model input touches it.
    sched = d["season"].map(C.SEASON_LEN).fillna(float(C.FULL_SEASON))
    d["pred_gp"] = d["p_play"] * d["gp_share"] * sched

    d["act_war"] = d["act_war"].fillna(0.0)          # absent = zero, not missing
    d["act_gp"] = d["act_gp"].fillna(0.0)
    # PLAYED means the participation event happened, which is the event the
    # participation model predicts. Scoring a Brier score against a ten-game
    # threshold while the model forecasts a one-game event scores the model
    # against a question it was not asked.
    d["played"] = d["act_gp"] >= C.PARTICIPATION_GP

    d["e_war"] = d["pred_war"] - d["act_war"]
    d["e_gp"] = d["pred_gp"] - d["act_gp"]
    # The RATE error is only defined for a season that happened. Scoring a
    # rate against a player who did not play would mix two different errors.
    d["e_rate"] = np.where(d["played"], d["rate_82"] - d["act_rate_82"], np.nan)
    d["brier"] = (d["p_play"] - d["played"].astype(float)) ** 2
    if {"lo", "hi"}.issubset(d.columns):
        d["covered"] = ((d["act_war"] >= d["lo"]) & (d["act_war"] <= d["hi"])).astype(float)
        d.loc[d["lo"].isna(), "covered"] = np.nan
    else:
        d["covered"] = np.nan
    return d


def _summarise(d: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    g = d.groupby(by, observed=True)
    out = pd.DataFrame({
        "n": g.size(),
        "bias_war": g["e_war"].mean(),
        "mae_war": g["e_war"].apply(lambda x: x.abs().mean()),
        "rmse_war": g["e_war"].apply(lambda x: float(np.sqrt((x ** 2).mean()))),
        "bias_rate": g["e_rate"].mean(),
        "mae_rate": g["e_rate"].apply(lambda x: x.abs().mean()),
        "mae_gp": g["e_gp"].apply(lambda x: x.abs().mean()),
        "brier": g["brier"].mean(),
        "play_rate": g["played"].mean(),
        "coverage": g["covered"].mean(),
    })
    return out.reset_index()


class Harness:
    """Holds the table and runs models over pages. One instance per session;
    `run()` is pure with respect to it, so two models scored on the same
    harness saw byte-identical inputs."""

    def __init__(self, table: pd.DataFrame, lag_days: int = ISET.AVAILABILITY_LAG_DAYS):
        self.table = table
        self.lag_days = lag_days

    def _check_pages(self, pages, unseal: bool, reason: str) -> tuple[int, ...]:
        pages = tuple(pages)
        sealed = [p for p in pages if p in C.CONFIRMATORY_PAGES]
        if sealed and not unseal:
            raise C.ConfirmatorySealBroken(
                f"pages {sealed} are confirmatory (decision D) and are scored "
                "ONCE, at the end of Phase 5. Development work uses "
                f"{C.DEV_PAGES[0]}-{C.DEV_PAGES[-1]}. To spend the "
                "confirmatory run, pass unseal=True with a reason -- it will "
                "be logged, and it is not repeatable.")
        if sealed:
            # A REASON IS REQUIRED, not merely invited. The seal previously
            # accepted unseal=True with an empty string and logged "(no reason
            # given)", which spends the one confirmatory run and leaves no
            # record of what it was spent on.
            if not reason.strip():
                raise C.ConfirmatorySealBroken(
                    f"pages {sealed} are confirmatory and unseal=True was "
                    "passed with no reason. The run is not repeatable, so what "
                    "it was spent on has to be written down before it is spent.")
            C.log(f"  *** CONFIRMATORY SEAL BROKEN for pages {sealed}: {reason}")
            C.log("  *** This is the one confirmatory run. Record it in DECISIONS.md.")
        C.record_inspection("forecast_harness", "forecast page", pages, reason)
        return pages

    def run(self, model, pages=C.DEV_PAGES, horizons=DEFAULT_HORIZONS,
            unseal: bool = False, reason: str = "") -> pd.DataFrame:
        """Roll the model across pages and return one scored row per
        (page, player, horizon)."""
        pages = self._check_pages(pages, unseal, reason)
        out = []
        for t0 in pages:
            d = ISET.decision_date_for_page(t0)
            iset = ISET.build(self.table, d, t0=t0, lag_days=self.lag_days)

            # ROLLING FIT. `before=t0` is the contract: the model may fit on
            # any pair whose OUTCOME season is strictly before t0. A three-
            # season outcome starting before t0 still ENDS after it, so the
            # model's own fit code must respect the outcome window, not just
            # the input window -- that is asserted in the model base class.
            model.fit(iset.seasons, before=t0)

            subs = subjects_at(iset)
            if subs.empty:
                continue
            pred = model.predict(iset, subs, horizons)

            need = {"career_key", "h", "rate_82", "gp_share", "p_play"}
            missing = need - set(pred.columns)
            assert not missing, f"{model.name} predict() is missing {missing}"

            # THE COMPLETE GRID, not just well-formed columns. Everything
            # below this point validated the CONTENTS of whatever frame came
            # back and never checked that the frame answered the question. A
            # model that returned one player for a page of 866 passed each
            # assertion, and the join two blocks down is a left join on the
            # prediction, so the missing players simply vanished and the model
            # was scored on the sample it chose. That is the same failure the
            # missing-value assertion below already guards against, one level
            # up: declining a player by omitting his row rather than by
            # returning a blank one.
            want = pd.MultiIndex.from_product(
                [sorted(subs["career_key"]), sorted(int(h) for h in horizons)],
                names=["career_key", "h"])
            got = pd.MultiIndex.from_arrays(
                [pred["career_key"], pred["h"].astype(int)], names=["career_key", "h"])
            dupes = int(got.duplicated().sum())
            assert not dupes, (
                f"{model.name} returned {dupes} duplicate (player, horizon) rows "
                f"on page {t0}. Each requested cell must be answered once.")
            absent = want.difference(got)
            extra = got.difference(want)
            assert absent.empty and extra.empty, (
                f"{model.name} did not answer the question asked on page {t0}. "
                f"Requested {len(want)} (player, horizon) cells, returned "
                f"{len(got)}, of which {len(absent)} requested cells are missing "
                f"and {len(extra)} were never asked for. Every model is scored "
                "on the same grid; a model that omits the players it finds hard "
                "is scored on an easier sample than its rivals.")
            assert pred["p_play"].between(0, 1).all(), f"{model.name} returned a p_play outside [0,1]"
            assert pred["gp_share"].between(0, 1).all(), f"{model.name} returned a gp_share outside [0,1]"
            # NO MODEL MAY DECLINE TO PREDICT. A missing forecast is dropped by
            # every mean taken downstream, so a model that returns NaN for the
            # players it finds hard is scored on an easier sample than its
            # rivals and wins by forfeit. This fired for real: the first aging
            # walk returned NaN for the 0.6% of rows with no birthdate, and its
            # error was computed on 210 fewer rows than everyone else's.
            for col in ("rate_82", "gp_share", "p_play"):
                bad = int(pred[col].isna().sum())
                assert not bad, (
                    f"{model.name} returned {bad} missing {col} values on page "
                    f"{t0}. Every model is scored on the same rows; a model "
                    "that cannot predict a player must fall back to something, "
                    "not decline.")

            act = outcomes(self.table, t0, horizons)
            m = (pred.merge(subs, on="career_key", how="left", suffixes=("", "_s"))
                     .merge(act, on=["career_key", "h"], how="left"))
            m = m[m["season"].notna() | (m["h"] + t0 <= C.LAST_SOURCE_SEASON)]
            m["season"] = (t0 + m["h"]).astype(int)
            m = m[m["season"] <= C.LAST_SOURCE_SEASON]
            m["page"], m["model"] = t0, model.name
            out.append(m)

        rows = pd.concat(out, ignore_index=True)
        return _score_rows(rows)

    @staticmethod
    def summary(scored: pd.DataFrame, by: str | list[str] = "h") -> pd.DataFrame:
        by = [by] if isinstance(by, str) else list(by)
        return _summarise(scored, ["model"] + by)

    @staticmethod
    def compare(a: pd.DataFrame, b: pd.DataFrame, metric: str = "e_war",
                n_boot: int = 2000, seed: int = 20260914) -> pd.DataFrame:
        """Paired comparison of two models on the SAME rows, by horizon, with
        a bootstrap interval CLUSTERED BY PLAYER.

        Clustering matters: one player contributes six overlapping horizons
        and up to seven pages, so his seasons are not independent draws.
        Resampling careers rather than rows is what stops the interval from
        being far too narrow -- the mistake that makes a 1% gain look decisive.
        """
        key = ["career_key", "page", "h"]
        j = a.merge(b, on=key, suffixes=("_a", "_b"))
        rng = np.random.default_rng(seed)
        rows = []
        for h, g in j.groupby("h"):
            ea, eb = g[metric + "_a"].abs(), g[metric + "_b"].abs()
            d = (eb - ea).to_numpy()                     # negative: b is better
            careers = g["career_key"].to_numpy()
            uniq, idx = np.unique(careers, return_inverse=True)
            by_career = [np.flatnonzero(idx == i) for i in range(len(uniq))]
            draws = np.empty(n_boot)
            for k in range(n_boot):
                pick = rng.integers(0, len(uniq), len(uniq))
                take = np.concatenate([by_career[i] for i in pick])
                draws[k] = d[take].mean()
            lo, hi = np.percentile(draws, [2.5, 97.5])
            rows.append(dict(h=h, n=len(g), n_careers=len(uniq),
                             mae_a=ea.mean(), mae_b=eb.mean(),
                             diff=d.mean(), pct=100 * d.mean() / ea.mean(),
                             ci_lo=lo, ci_hi=hi,
                             decisive=bool(lo < 0 and hi < 0)))
        return pd.DataFrame(rows)
