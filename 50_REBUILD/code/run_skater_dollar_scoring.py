"""run_skater_dollar_scoring.py -- Phase 5 acceptance: the skater contract
valuations, point and simulated, scored against what the players delivered.

EXPERIMENTAL (50_REBUILD). Development start years only (the reserved cohorts
are refused by the guard). Scoring only: nothing is fitted on realised seasons
and nothing is adopted.

WHAT THE PLAN ASKS FOR
    Phase 5's acceptance: the harness's dollar scoring on development pages, the
    zero-uncertainty identity (the simulation mean equals the point valuation
    when the spread is removed; `run_npv_simulation.py` report 2 and checks
    24-25), and full-chain movement against the production spine contract by
    contract (`run_production_reconciliation.py`). This runner is the first:
    the simulated contract values scored in dollars, for the adopted skater
    leader and, matched, for the previous one.

THE COMPARISON, DECLARED BEFORE THE RUN
    forecasts   adopted  = run_npv_simulation.LEADER (visible contract status)
                previous = run_npv_simulation.PRIOR_LEADER (no contract data)
    what        each development contract's own TERM (control years are the
                control-year runner's), valued two ways on each forecast: the
                point valuation (price of the expected season) and the mean
                of 2,000 drawn career paths priced one by one
    currency    ONE line prices every valuation and the realised path: the
                adopted leader's (PRIMARY); the previous leader's is the
                sensitivity. The realised target is asserted identical across
                forecasts, contract by contract (`dollar_scoring`)
    scores      squared error primary; absolute error and bias beside it;
                player-resampled shares as exact counts of 2,000; calibration
                of the simulated distribution (randomized PIT, and interval
                coverage against the model's own draws)
    rows        ended terms simulated under both forecasts

    The same draws are used for both lines (seeded per contract in
    `price_span`), so a line change reprices, it does not redraw.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import run_npv_simulation as RNS
import run_control_years as RCY
from contract_price_model import contract_sample
from player_season_table import build as build_table, birthdate_source
from dollar_scoring import (realised_path, term_extra, score_on_line, report_scores,
                            calibration_block)

SCRIPT_VERSION = "1.1"
KEY = RCY.KEY
FORECASTS = (("adopted", RNS.LEADER), ("previous", RNS.PRIOR_LEADER))
SCORING_LINE = "adopted"


def price_and_simulate(label, cls, sample, table, cohorts, simulate: bool = True):
    """One forecast's point valuations and price lines, and -- if `simulate` --
    its 2,000-path term distribution per contract (draws kept for repricing on
    another line). Returns (priced rows, lines, simulated rows or None, draws)."""
    C.log(f"FORECAST: {label} ({cls.__name__})")
    pt, lines = RNS.point_valuation(sample, table, cohorts, cls)
    if not simulate:
        C.log(f"  {len(pt)} contracts priced (point valuation only)")
        C.log("")
        return pt, lines, None, {}
    s = sample[sample[KEY].isin(pt[KEY])]
    blocks, spreads = RNS.forecast_blocks(s, table, model_factory=cls)
    # PARITY: the band's expected term production equals the priced one.
    gaps = [abs(float(np.mean(blocks[c][1] * blocks[c][3]))
                - float(pt.loc[pt[KEY] == c, "war_per_season"].iloc[0]))
            for c in pt[KEY] if c in blocks]
    assert max(gaps) < 1e-9, f"{label}: band and point valuation disagree by {max(gaps):.2e}"
    C.log(f"  {len(pt)} contracts priced; {len(gaps)} carry a band, whose expected")
    C.log(f"  season equals the priced forecast on every one (largest gap {max(gaps):.1e})")
    keep = {}
    span = {int(c): [] for c in pt[KEY]}          # the term only
    out = RCY.price_span(span, s, table, pt, lines, label, check_leakage=True,
                         blocks=(blocks, spreads), extra=term_extra(lines, keep))
    ok = out[out["status"] == "ok"].merge(pt[[KEY, "pkey", "end_yr"]], on=KEY)
    C.log(f"  {len(ok)} contracts simulated; {int((out['status'] != 'ok').sum())} "
          f"skipped for a band that did not reach every season")
    C.log("")
    return pt, lines, ok, keep


def main() -> None:
    C.banner("run_skater_dollar_scoring.py", SCRIPT_VERSION)
    path, how = birthdate_source()
    C.log(f"  birthdates: {how}")
    table = build_table(birthdate_csv=path, verbose=False)
    sample = contract_sample()
    dev = [int(y) for y in sorted(sample["start_yr"].dropna().unique())
           if int(y) not in C.CONFIRMATORY_START_YEARS]
    cohorts = C.check_market_cohorts(dev, "run_skater_dollar_scoring")
    C.log("")

    priced, results, draws = {}, {}, {}
    for label, cls in FORECASTS:
        pt, lines, ok, keep = price_and_simulate(label, cls, sample, table, cohorts)
        priced[label] = (pt, lines)
        results[label], draws[label] = ok, keep

    C.log("THE TERM AS A DISTRIBUTION, each forecast on its own line (a valuation,")
    C.log("not a score). $M a contract.")
    C.log(f"    {'forecast':<10}{'n':>6}{'point':>9}{'simulated':>11}{'gap':>8}{'cost':>8}"
          f"{'sd':>8}{'10-90 width':>13}")
    for label, ok in results.items():
        C.log(f"    {label:<10}{len(ok):>6}{ok['value_point'].mean() / 1e6:>9.3f}"
              f"{ok['term_sim_mean'].mean() / 1e6:>11.3f}"
              f"{(ok['term_sim_mean'] - ok['value_point']).mean() / 1e6:>+8.3f}"
              f"{ok['cost'].mean() / 1e6:>8.3f}{ok['term_sim_sd'].mean() / 1e6:>8.3f}"
              f"{(ok['term_sim_q90'] - ok['term_sim_q10']).mean() / 1e6:>13.3f}")
    C.log("")

    real = realised_path(table)
    common = sorted(set.intersection(*[
        set(ok.loc[ok["end_yr"] <= C.LAST_SOURCE_SEASON, KEY]) for ok in results.values()]))
    rows_of = {lab: priced[lab][0].set_index(KEY) for lab in priced}
    labels = tuple(l for l, _ in FORECASTS)
    C.log("AGAINST WHAT HAPPENED, IN ONE CURRENCY. Ended terms simulated under both")
    C.log("forecasts. Every valuation and the realised path are priced on the same")
    C.log("line; the realised target is asserted identical across forecasts. Squared")
    C.log("error is primary; $M; shares are exact counts of 2,000 player-resamples.")
    C.log("")
    scored = {}
    other = [l for l in labels if l != SCORING_LINE][0]
    for line_label in (SCORING_LINE, other):
        d = score_on_line(common, rows_of, priced[line_label][1], draws, labels, real)
        tag = "PRIMARY" if line_label == SCORING_LINE else "sensitivity"
        C.log(f"  on the {line_label} forecast's line ({tag}), {len(d)} contracts, "
              f"{d['pkey'].nunique()} players:")
        report_scores(d, labels, exact=True)
        C.log("")
        scored[line_label] = d

    d = scored[SCORING_LINE]
    C.log("IS THE CONTRACT DISTRIBUTION CALIBRATED? On the primary line.")
    C.log("")
    calibration_block(d, labels)

    sc = d.drop(columns=[c for c in d.columns if c.startswith("draws_")])
    sc.to_csv(C.out_path("skater_dollar_scoring.csv"), index=False)
    C.log("  wrote skater_dollar_scoring.csv")
    C.write_log("skater_dollar_scoring_run_log.txt")


if __name__ == "__main__":
    main()
