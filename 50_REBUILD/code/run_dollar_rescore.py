"""run_dollar_rescore.py -- contract dollars re-scored after the 28 September fixes.

EXPERIMENTAL (50_REBUILD). Development start years only. Scoring only: nothing
is adopted and no production file is edited. RUNS ON THE LAPTOP: it needs the
contract export, which is not in the cloud container.

WHY
    The dollar comparison on record (Model_Scorecard.md, 2026-09-24) scored the
    current model BEFORE its two 28 September revisions (aging curve and skater
    exit hazard fitted on seasons before each valuation date; older careers in
    the age table). `production_adapter.ProductionChain` v1.3 now carries both,
    so the same scoring, run again, prices the current model as it now runs.
    It also adds the "obvious fixes" model (`obvious_fixes.ObviousFixes`): the
    current model's comparable-player aging with every listed fix applied.

THE FORECASTS, DECLARED BEFORE THE RUN
    current        the live chain (ProductionChain v1.3); point valuation only
    obvious_fixes  fitted start, rebuilt games share and chance of playing,
                   comparables aging added, departures imputed; point only
    fixes_games    (v1.1) obvious_fixes with the games-share forecast reading the
                   player's level (Star_Bias_Test.md, change G); point only
    adopted        the rebuilt leader (visible contract status); simulated too
    previous       the rebuilt leader without contract data; simulated too
    The scoring is run_model_scorecard's section 2 unchanged: every valuation
    and the realised production priced on ONE line (the adopted model's,
    primary; the current model's, sensitivity), realised target asserted
    identical, squared error primary, shares as counts of 2,000 player
    resamples. Then the same on the contracts the current model answers itself.

WHAT DOLLARS HERE DO AND DO NOT CONTAIN
    The score is the contract's term production priced on one line. Control
    years after expiry (the restricted-free-agent rights) are not part of it
    for any forecast, so the rights fix cannot show here; neither can the
    choice of price line, since one line prices every forecast.

GUARDS
    * the adapter is v1.3 or later and production's projector fits its curve
      per page (`curve_for`), so "current" is the revised chain;
    * the age table production reads is logged by its real path;
    * everything run_model_scorecard and dollar_scoring already assert
      (identity fields per contract, identical realised targets).

HOW TO RUN (Windows PowerShell, from the repo root, .env in place):
    python 50_REBUILD\\code\\run_dollar_rescore.py
Output: 50_REBUILD/output/dollar_rescore_run_log.txt (the log to send back)
and dollar_rescore.csv. NOT YET RUN: written in the cloud container, where it
imports and runs up to the contract export and stops there.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import run_npv_simulation as RNS
import run_skater_dollar_scoring as SDS
import production_adapter as PA
import obvious_fixes as OF
import star_candidates as SC
from contract_price_model import contract_sample
from player_season_table import build as build_table, birthdate_source
from run_model_scorecard import production_unanswerable
from dollar_scoring import realised_path, score_on_line, report_scores

SCRIPT_VERSION = "1.1"
KEY = "contract_id"
MODELS = (("current", PA.ProductionChain, False),
          ("obvious_fixes", OF.ObviousFixes, False),
          ("fixes_games", SC.candidate(gp=True), False),
          ("adopted", RNS.LEADER, True),
          ("previous", RNS.PRIOR_LEADER, True))
# The recorded figures this run replaces, for the reader of the log only
# (Model_Scorecard.md, adopted line, production's answerable contracts, point).
RECORDED_2026_09_24 = {"current": (3.648, 1.854, -0.153), "adopted": (3.614, 1.761, -0.581),
                       "previous": (3.630, 1.762, -0.628)}
TERMS = (("1-2 years", 1, 2), ("3-5 years", 3, 5), ("6-8 years", 6, 8))


def check_current_is_revised() -> None:
    v = tuple(int(x) for x in PA.SCRIPT_VERSION.split("."))
    assert v >= (1, 3), f"production_adapter v{PA.SCRIPT_VERSION}: the revised chain needs v1.3+"
    SFP = PA._production()[0]
    assert hasattr(SFP.SkaterProjector, "curve_for"), \
        "skater_forward_projection has no curve_for: this is the pre-revision projector"
    C.log(f"  current model: production_adapter v{PA.SCRIPT_VERSION}, "
          f"skater_forward_projection v{getattr(SFP, 'SCRIPT_VERSION', '?')}")
    C.log(f"  production age table read: {Path(SFP.F_WAR_AGE).resolve()}")


def by_term(d: pd.DataFrame, rows: pd.DataFrame, labels) -> None:
    """Point-valuation error by contract length: long deals carry the stars."""
    ln = rows["length"].reindex(d[KEY]).to_numpy()
    C.log(f"    by term (point valuation; RMSE / MAE / bias, $M):")
    for name, lo, hi in TERMS:
        m = (ln >= lo) & (ln <= hi)
        cells = []
        for lab in labels:
            e = (d.loc[m, f"point_{lab}"] - d.loc[m, "realised"]) / 1e6
            cells.append(f"{lab} {np.sqrt((e ** 2).mean()):.2f}/{e.abs().mean():.2f}/{e.mean():+.2f}")
        C.log(f"      {name:<10} n={int(m.sum()):>4}  " + "   ".join(cells))


def main() -> None:
    C.banner("run_dollar_rescore.py", SCRIPT_VERSION)
    check_current_is_revised()
    path, how = birthdate_source()
    C.log(f"  birthdates: {how}")
    table = build_table(birthdate_csv=path, verbose=False)
    sample = contract_sample()                       # needs the contract export
    dev = [int(y) for y in sorted(sample["start_yr"].dropna().unique())
           if int(y) not in C.CONFIRMATORY_START_YEARS]
    cohorts = C.check_market_cohorts(dev, "run_dollar_rescore")
    C.log("")

    priced, results, draws = {}, {}, {}
    for label, cls, sim in MODELS:
        pt, lines, ok, keep = SDS.price_and_simulate(label, cls, sample, table, cohorts,
                                                     simulate=sim)
        priced[label] = (pt, lines)
        results[label] = ok if ok is not None else pt[[KEY, "end_yr"]]
        draws.update({label: keep} if sim else {})
    common = sorted(set.intersection(*[
        set(r.loc[r["end_yr"] <= C.LAST_SOURCE_SEASON, KEY]) for r in results.values()]))
    rows_of = {lab: priced[lab][0].set_index(KEY) for lab in priced}
    labels = tuple(l for l, _, _ in MODELS)
    real = realised_path(table)
    fallback = production_unanswerable(sample, common)
    C.log("CONTRACT DOLLARS IN ONE CURRENCY. Ended terms priced by all five; $M.")
    C.log(f"  {len(common)} contracts; {len(fallback)} have no current-model anchor at signing.")
    C.log("")
    out = None
    for line_label in ("adopted", "current"):
        d = score_on_line(common, rows_of, priced[line_label][1], draws, labels, real)
        d["production_answerable"] = ~d[KEY].isin(fallback)
        tag = "PRIMARY" if line_label == "adopted" else "sensitivity"
        for sub_label, dd in (("all contracts", d),
                              ("the current model's answerable contracts",
                               d[d["production_answerable"]].copy())):
            C.log(f"  on the {line_label} model's line ({tag}), {sub_label}: {len(dd)} "
                  f"contracts, {dd['pkey'].nunique()} players")
            report_scores(dd, labels, exact=True)
            # the headline question: the fixed current model against the rebuilt one
            report_scores(dd, ("adopted", "obvious_fixes", "fixes_games"), exact=True)
            by_term(dd, rows_of["adopted"], labels)
            C.log("")
        if line_label == "adopted":
            out = d
    C.log("  recorded 2026-09-24, adopted line, answerable contracts, point (RMSE, MAE, bias):")
    for lab, (r, m, b) in RECORDED_2026_09_24.items():
        C.log(f"    {lab:<10}{r:>8.3f}{m:>8.3f}{b:>+9.3f}")
    out.drop(columns=[c for c in out.columns if c.startswith("draws_")]).to_csv(
        C.out_path("dollar_rescore.csv"), index=False)
    C.write_log("dollar_rescore_run_log.txt")


if __name__ == "__main__":
    main()
