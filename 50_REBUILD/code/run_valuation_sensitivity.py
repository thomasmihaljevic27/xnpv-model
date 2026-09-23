"""run_valuation_sensitivity.py -- does the valuation hold when the forecast changes?

EXPERIMENTAL (50_REBUILD). Development start years only; the reserved market
cohorts are refused by the guard, not avoided by habit.

WHY THIS RUN EXISTS
    The forecast has measured errors that concentrate on stars and on young
    players at long horizons, and three rounds of diagnostics could not
    separate their causes. That leaves one question worth asking, and it is not
    another diagnostic: DOES ANY OF IT CHANGE THE ANSWER?

    The thesis does not claim to forecast a player. It claims that certain
    categories of asset are systematically mispriced. So the test is whether
    the valuation of A FIXED SET OF CONTRACTS holds when the forecast under it
    is replaced.

THE GROUPING IS DECLARED ONCE AND APPLIED TO EVERY COLUMN, AND THE FIRST
VERSION OF THIS FILE GOT THAT WRONG
    Each column used to define its tiers from its OWN forecast. That answers a
    real question -- what does each model say about the players it calls stars
    -- but it is not a robustness test, because the columns then describe
    different populations. The top tiers held 51, 68, 18, 19 and 18 contracts,
    and the report printed one n row and read the spread across them as the
    same contracts changing sign.

    They do not. Held to one declared membership, every column's top tier is
    negative and the reported reversal disappears. The own-tier table is still
    printed below, second, labelled as the descriptive question it answers and
    with its own n on every cell.

    The declared rule: tiers are cut on the ADOPTED CANDIDATE's forecast
    production per season, fixed before any column is priced, and joined to
    every other column by contract id. Any rule would do as long as it is one
    rule; this one is named so a reader can object to it.

EACH FORECAST GETS ITS OWN PRICE LINE
    The currency is fitted on the forecast, so a world with a different
    forecast has a different price of a forecast win, and refitting makes each
    column a complete alternative pipeline. It also lets the market slope
    absorb part of the forecast change, so the participation test below is run
    both ways -- currency refitted and currency held at the baseline's.

WHAT THE PRODUCTION COLUMN IS, EXACTLY
    Production's own projection and exit-survival calculation, imported through
    `production_adapter.ProductionChain`, and then priced through THIS TREE's
    currency. It is not the output of the production contract-NPV chain, and
    agreement with it is not parity with the production spine. The adapter also
    inherits production's full-panel aging fit, so it carries a parameter
    look-ahead this runner's rolling price fits do not remove.

WHAT THIS IS NOT
    Not a back-test. Nothing is scored against a realised outcome and no trade
    is priced. Agreement among model valuations is a robustness check; it is
    not evidence about performance, and neither is evidence of systematic trade
    mispricing, which is the claim that still needs testing.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
from contract_price_model import contract_sample, attach_forecasts
from production_currency import ProductionCurrency
from player_season_table import build as build_table, birthdate_source
from run_phase4_decisions import prep
from ability_forecast import A0Production, A1AgingParticipationImputedNC
from production_adapter import ProductionChain
# THE ADOPTED MODEL COMES FROM THE ONE SWITCH, not a class named here. This file
# used to import `A1HingeExposure` by name and call it "the adopted candidate";
# when the skater leader changed on 2026-09-23 the simulation moved and this
# column did not, and the integration guard refused the two artifacts (point
# surplus apart by up to $1.06M on 948 contracts). Check 44 pins it.
from run_npv_simulation import LEADER, PRIOR_LEADER

SCRIPT_VERSION = "2.1"

KEY = "contract_id"     # not (player, start year): two contracts share that pair


class _EveryonePlays(A1AgingParticipationImputedNC):
    """The baseline with the probability of playing pinned to one.

    THIS IS THE PARTICIPATION TEST, and the first version of this file used a
    different class for it -- the calibrated total with aging but no
    participation -- which ALSO swapped the imputed survivorship aging for the
    uncorrected curve. Two things changed and the result was read as one.

    Everything here is the baseline's: the same anchor, the same fitted decay,
    the same imputed aging. Only the participation probability is replaced.
    Setting it to one is not a calibrated repair and nobody would ship it; it
    is the cleanest available way to ask what the participation half is worth
    to a valuation.
    """
    name = "baseline, participation pinned to one"

    def _p_play(self, a, subs, h):
        return np.ones(len(subs), dtype=float)


FORECASTS = [
    ("production's forecast, priced here", ProductionChain),
    ("trailing blend, carried flat", A0Production),
    ("calibrated total + aging + participation", A1AgingParticipationImputedNC),
    ("the same, participation pinned to one", _EveryonePlays),
    ("the previous leader, no contract data", PRIOR_LEADER),
    ("the adopted candidate", LEADER),
]
BASELINE = "calibrated total + aging + participation"
ADOPTED = "the adopted candidate"
PREVIOUS = "the previous leader, no contract data"
# THE GROUPING IS REBUILT ON THE ADOPTED MODEL, declared 2026-09-23. The rule
# has always been "tiers are cut on the adopted candidate's forecast"; the
# adopted candidate changed, so the membership changes with it. The previous
# membership (cut on the previous leader) is printed beside it as a
# sensitivity, with the number of contracts that change group, so the two are
# never read as the same category comparison.
GROUPING = ADOPTED

TIER_EDGES = [-np.inf, 0, 0.5, 1.0, 2.0, np.inf]
TIER_NAMES = ["below 0", "0 to 0.5", "0.5 to 1", "1 to 2", "2+"]


def price(d: pd.DataFrame, mode: str = "in",
          lines: dict | None = None) -> tuple[pd.DataFrame, dict, set]:
    """Every contract priced on a line fitted only to deals signed before it.

    `lines` reuses another forecast's fitted currencies instead of fitting new
    ones, which is how the "currency held fixed" column is produced. Returns
    the priced frame, the fitted lines, and the contract ids lost because their
    quarter had too few earlier signings to fit a line at all.
    """
    out, fitted, lost = [], {}, set()
    for cut, te in d.groupby("cut"):
        cur = lines[cut] if lines is not None and cut in lines else \
            ProductionCurrency(mode).fit(d, before_date=cut)
        if cur.coef_ is None:
            lost |= set(te[KEY])
            continue
        fitted[cut] = cur
        te = te.copy()
        te["value"] = cur.value(te)
        te["cost"] = ProductionCurrency("in").cost(te)
        te["surplus"] = te["value"] - te["cost"]
        out.append(te)
    return (pd.concat(out, ignore_index=True) if out else pd.DataFrame()), fitted, lost


def _tier_table(results: dict, tiers: pd.Series, label: str) -> pd.DataFrame:
    C.log(f"  {'forecast':<44}" + "".join(f"{t:>11}" for t in TIER_NAMES))
    g = {}
    for name, r in results.items():
        t = r[KEY].map(tiers)
        means = r.groupby(t, observed=False)["surplus"].mean() / 1e6
        g[name] = means
        C.log(f"  {name:<44}" + "".join(
            f"{means.get(x, np.nan):>11.2f}" for x in TIER_NAMES))
    n = tiers.value_counts().reindex(TIER_NAMES).fillna(0)
    C.log(f"  {('n per group (' + label + ')'):<44}" + "".join(
        f"{int(v):>11}" for v in n))
    return pd.DataFrame(g).T[TIER_NAMES]


def main() -> None:
    C.banner("run_valuation_sensitivity.py", SCRIPT_VERSION)
    path, how = birthdate_source()
    table = build_table(birthdate_csv=path, verbose=False)
    C.log(f"  birthdates: {how}")
    C.log("")

    sample = contract_sample()
    dev_years = [int(y) for y in sorted(sample["start_yr"].dropna().unique())
                 if int(y) not in C.CONFIRMATORY_START_YEARS]
    cohorts = C.check_market_cohorts(dev_years, "run_valuation_sensitivity")
    elig = sample[sample["start_yr"].isin(cohorts)
                  & (sample["signed"] >= pd.Timestamp("2015-07-01"))]
    C.log(f"  {len(elig)} contracts eligible on development start years "
          f"{min(cohorts)}-{max(cohorts)}")
    C.log("")

    results, attached_n, lost_fit = {}, {}, {}
    for label, cls in FORECASTS:
        t0 = time.time()
        d = prep(attach_forecasts(sample, cls, table, verbose=False))
        d = d[d[KEY].isin(elig[KEY])].copy()
        attached_n[label] = d[KEY].nunique()
        d["cut"] = d["signed"].dt.to_period("Q").dt.start_time
        r, lines, lost = price(d, "in")
        lost_fit[label] = lost
        r_free, _, _ = price(d, "free")
        r["surplus_free"] = r_free.set_index(KEY)["surplus"].reindex(r[KEY]).to_numpy()
        if label == BASELINE:
            self_lines, self_d = lines, d
        results[label] = r
        C.log(f"  {label:<44}{r[KEY].nunique():>6} priced  ({time.time() - t0:.0f}s)")
    C.log("")

    # ---- where the sample goes -------------------------------------------
    C.log("WHERE THE SAMPLE GOES, and the first version of this file blamed the")
    C.log("wrong stage. It attributed the losses to the forecast not reaching")
    C.log("far enough for a long deal, and proposed extending its reach. The")
    C.log("attachment path already extrapolates past its fitted horizons. The")
    C.log("binding constraint is downstream: a contract can only be priced if")
    C.log("its signing quarter has enough EARLIER signings to fit a price line,")
    C.log("and the early quarters do not.")
    C.log("")
    base = results[GROUPING]
    C.log(f"    {'eligible on development cohorts':<48}{len(elig):>6}")
    C.log(f"    {'lost at forecast attachment':<48}"
          f"{len(elig) - attached_n[GROUPING]:>6}")
    C.log(f"    {'lost because the price line could not be fitted':<48}"
          f"{len(lost_fit[GROUPING]):>6}")
    C.log(f"    {'priced':<48}{base[KEY].nunique():>6}")
    C.log("")
    C.log("  The independent audit splits the attachment loss further: no")
    C.log("  matching eligible forecast subject, and a term reaching back before")
    C.log("  the forecast starts. Of the excluded six-year deals it finds 34 of")
    C.log("  35 lost at the price-fit threshold, and 18 of 20 eight-year deals.")
    C.log("  Extending the forecast's reach would not restore them.")
    C.log("")

    # ---- every column on the same contracts -------------------------------
    keys = None
    for r in results.values():
        keys = set(r[KEY]) if keys is None else (keys & set(r[KEY]))
    for label in results:
        r = results[label]
        results[label] = (r[r[KEY].isin(keys)].drop_duplicates(KEY)
                          .sort_values(KEY).reset_index(drop=True))
    C.log(f"  {len(keys)} contracts priced by all {len(results)}; every table below is on")
    C.log("  exactly those.")
    C.log("")

    # ---- the declared grouping, which is the robustness test --------------
    fixed = results[GROUPING].set_index(KEY)["war_per_season"]
    tiers = pd.Series(pd.cut(fixed, TIER_EDGES, labels=TIER_NAMES).astype(str),
                      index=fixed.index)
    C.log("SURPLUS BY A DECLARED FIXED GROUP, $M over the whole deal, term-in.")
    C.log(f"Groups are cut once on {GROUPING}'s forecast and")
    C.log("applied to every column, so each cell is the SAME contracts valued a")
    C.log("different way. This is the robustness test.")
    C.log("")
    C.log("The LEVEL is not comparable across columns -- each line is fitted to")
    C.log("observed contracts, so the average prices near zero by construction.")
    C.log("The SIGN and the ORDER are, and the thesis rests on those.")
    C.log("")
    g_fixed = _tier_table(results, tiers, "fixed")
    C.log("")
    signs = np.sign(g_fixed)
    for t in TIER_NAMES:
        same = signs[t].nunique() == 1
        vals = g_fixed[t].to_numpy()
        C.log(f"    {t:<10}{f'same sign in all {len(g_fixed)}' if same else 'SIGN FLIPS':<24}"
              f"range {np.nanmin(vals):>+7.2f} to {np.nanmax(vals):>+7.2f} $M")
    orders = {k: tuple(g_fixed.loc[k].sort_values().index) for k in g_fixed.index}
    agree = len(set(orders.values())) == 1
    C.log("")
    C.log(f"    ordering of the five groups: "
          f"{f'identical in all {len(g_fixed)} columns' if agree else 'DIFFERS between columns'}")
    C.log(f"    worst to best: {' < '.join(orders[GROUPING])}")
    C.log("")

    # ---- the previous membership, as a declared sensitivity ---------------
    prev = results[PREVIOUS].set_index(KEY)["war_per_season"]
    tiers_prev = pd.Series(pd.cut(prev, TIER_EDGES, labels=TIER_NAMES).astype(str),
                           index=prev.index)
    moved = int((tiers_prev.reindex(tiers.index) != tiers).sum())
    C.log("THE SAME TABLE ON THE PREVIOUS MEMBERSHIP, groups cut on the previous")
    C.log("leader's forecast. A sensitivity for the change of adopted model, not")
    C.log(f"the same category comparison: {moved} of {len(tiers)} contracts sit in a")
    C.log("different group under the two memberships.")
    C.log("")
    C.log("  moved from (rows, previous) to (columns, adopted):")
    xt = pd.crosstab(tiers_prev.reindex(tiers.index), tiers).reindex(
        index=TIER_NAMES, columns=TIER_NAMES).fillna(0).astype(int)
    C.log(f"  {'':<12}" + "".join(f"{t:>11}" for t in TIER_NAMES))
    for t in TIER_NAMES:
        C.log(f"  {t:<12}" + "".join(f"{int(v):>11}" for v in xt.loc[t]))
    C.log("")
    g_prev = _tier_table(results, tiers_prev, "previous")
    C.log("")
    for t in TIER_NAMES:
        same = np.sign(g_prev[t]).nunique() == 1
        vals = g_prev[t].to_numpy()
        C.log(f"    {t:<10}{f'same sign in all {len(g_prev)}' if same else 'SIGN FLIPS':<24}"
              f"range {np.nanmin(vals):>+7.2f} to {np.nanmax(vals):>+7.2f} $M")
    C.log("")

    # ---- the descriptive own-tier view, second and labelled ---------------
    C.log("AND THE SAME THING WITH EACH COLUMN USING ITS OWN TIERS. This answers")
    C.log("a different and legitimate question -- what does each model say about")
    C.log("the players IT calls stars -- and it is not a robustness test,")
    C.log("because the columns describe different populations. The n row shows")
    C.log("how different.")
    C.log("")
    C.log(f"  {'forecast':<44}" + "".join(f"{t:>11}" for t in TIER_NAMES)
          + f"{'top-tier n':>12}")
    for label, r in results.items():
        own = pd.cut(r["war_per_season"], TIER_EDGES, labels=TIER_NAMES)
        means = r.groupby(own, observed=False)["surplus"].mean() / 1e6
        C.log(f"  {label:<44}" + "".join(f"{means.get(t, np.nan):>11.2f}"
                                         for t in TIER_NAMES)
              + f"{int((own == '2+').sum()):>12}")
    C.log("")
    C.log("  The top tier holds a different number of contracts in every column,")
    C.log("  so the spread across this row is partly a change of population.")
    C.log("")

    # ---- participation, both ways -----------------------------------------
    C.log("WHAT THE PARTICIPATION HALF IS WORTH, on the fixed groups. The")
    C.log("baseline against itself with the probability of playing pinned to")
    C.log("one, everything else -- including the imputed survivorship aging --")
    C.log("held. Run twice: refitting the currency, which lets the market slope")
    C.log("absorb part of the change, and holding the baseline's currency, which")
    C.log("does not.")
    C.log("")
    alt = prep(attach_forecasts(sample, _EveryonePlays, table, verbose=False))
    alt = alt[alt[KEY].isin(keys)].copy()
    alt["cut"] = alt["signed"].dt.to_period("Q").dt.start_time
    alt_held, _, _ = price(alt, "in", lines=self_lines)
    alt_held = alt_held[alt_held[KEY].isin(keys)].drop_duplicates(KEY)
    cols = {"baseline": results[BASELINE],
            "pinned, currency refitted": results["the same, participation pinned to one"],
            "pinned, currency held": alt_held}
    C.log(f"  {'group':<12}" + "".join(f"{k:>28}" for k in cols))
    for t in TIER_NAMES:
        line = f"  {t:<12}"
        for r in cols.values():
            m = r[KEY].map(tiers) == t
            line += f"{r.loc[m, 'surplus'].mean()/1e6:>28.3f}"
        C.log(line)
    C.log("")
    C.log("  Signs and ordering survive both. That is evidence for this sample")
    C.log("  and these alternatives. It does not show that a calibrated repair")
    C.log("  would leave individual contracts, a path simulation, or a realised")
    C.log("  trade result unchanged, and pinning everyone to play is not a")
    C.log("  calibrated repair.")
    C.log("")

    # ---- term framing, on the fixed groups --------------------------------
    C.log("THE TERM FRAMING, on the same fixed top group. The currency pricing a")
    C.log("run of one-year deals instead of the term the player was given.")
    C.log("")
    C.log(f"  {'forecast':<44}{'term-in':>10}{'term-free':>12}{'difference':>13}")
    for label, r in results.items():
        top = r[r[KEY].map(tiers) == "2+"]
        C.log(f"  {label:<44}{top['surplus'].mean()/1e6:>10.2f}"
              f"{top['surplus_free'].mean()/1e6:>12.2f}"
              f"{(top['surplus'] - top['surplus_free']).mean()/1e6:>13.2f}")
    C.log("")
    C.log("  Large, and it reproduces. It is a contrast between two declared")
    C.log("  framings on one group, not a general measure of model uncertainty,")
    C.log("  and it does not settle which framing is right.")
    C.log("")

    # ---- contract by contract ---------------------------------------------
    C.log("AND CONTRACT BY CONTRACT, against production's forecast priced here.")
    C.log("")
    live = results["production's forecast, priced here"].set_index(KEY)["surplus"]
    C.log(f"  {'forecast':<44}{'correlation':>13}{'same sign':>11}{'mean |gap| $M':>15}")
    for label, r in results.items():
        if label.startswith("production"):
            continue
        s = r.set_index(KEY)["surplus"].reindex(live.index)
        ok = s.notna() & live.notna()
        C.log(f"  {label:<44}{s[ok].corr(live[ok]):>13.3f}"
              f"{100*(np.sign(s[ok]) == np.sign(live[ok])).mean():>10.0f}%"
              f"{(s[ok]-live[ok]).abs().mean()/1e6:>15.2f}")
    C.log("")

    # The class behind every column is written with it, so a consumer can
    # check that the adopted column is the model the simulation ran on, by
    # name, before it compares a single number.
    cls_of = {lab: cls.__name__ for lab, cls in FORECASTS}
    out = pd.concat([r.assign(forecast=lab, model_class=cls_of[lab],
                              fixed_group=r[KEY].map(tiers),
                              previous_group=r[KEY].map(tiers_prev))
                     for lab, r in results.items()], ignore_index=True)
    out.to_csv(C.out_path("valuation_sensitivity.csv"), index=False)
    C.log(f"  wrote {C.out_path('valuation_sensitivity.csv').name}")
    C.write_log("valuation_sensitivity_run_log.txt")


if __name__ == "__main__":
    main()
