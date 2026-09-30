"""run_contract_status_test.py -- Model 3 with contract status in its chance of playing.

EXPERIMENTAL (50_REBUILD). Development pages and development start years only.
Nothing is adopted and no production file is edited. RUNS ON THE LAPTOP: it
needs the contract export, which is not in the cloud container, and it REFUSES
to run without it (the participation model would otherwise fall back to "no
contract data" silently and Model 6 would quietly equal Model 3).

THE MODELS (numbered as in Dollar_Rescore.md and Star_Late_Test.md)
    Model 1  the current model as it runs (production_adapter.ProductionChain)
    Model 3  the current model with every listed fix, comparable-player aging,
             and the games-share forecast reading the player's level
             (star_candidates.candidate(gp=True)); the base
    Model 6  Model 3 with ONE change: its chance of playing reads visible
             contract status, with exactly the adopted rebuilt model's settings
             (star_candidates.candidate(gp=True, contracts=True))
    Model 4  the adopted rebuilt model (visible contract status)
    Model 7  Model 4 with the games-share change (RebuiltStatusGamesLevel), so
             Model 6 against Model 7 differs only in the aging method

WHY
    Model 3 under-forecasts good players' chance of playing three to five
    seasons out at every age (Star_Late_Test.md): 3+ win players aged 29-31 are
    given 0.84 and played 0.96; 2-3 win players aged 25-28 0.88 against 0.96.
    Level-by-age and a level hinge did not fix it. Whether a player is under
    contract for the season is information the club has and Model 3 does not
    use; a star three years into an eight-year deal is on a roster.

THE RULE, DECLARED BEFORE THE RUN (season forecasts, rows the current model answers)
    Model 6 IMPROVES Model 3 only if its season-WAR squared error is lower in at
    least 1,950 of 2,000 player resamples and its Brier score is not higher in
    1,950 or more. (Its rate and games share are identical to Model 3's, which
    is asserted.) Dollars are reported beside, on the same lines as the
    2026-09-30 re-score, and do not decide the verdict.

GUARDS
    * every contract-reading model has actually read the export (reads_contracts);
    * Model 6 moves only the chance of playing relative to Model 3, Model 7 only
      the games share relative to Model 4;
    * one row set and target for every arm;
    * in dollars, Models 1, 3 and 4 reproduce the recorded re-score
      (Dollar_Rescore.md, adopted line, answerable contracts) to $1,000 of RMSE.

HOW TO RUN (Windows PowerShell, from the repo root, after syncing):
    python 50_REBUILD\\code\\run_contract_status_test.py
    (add --no-dollars to run the season part alone; the dollar part takes
    several minutes more)
Output: 50_REBUILD/output/contract_status_run_log.txt, the file to send back.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import forecast_harness as H
from player_season_table import build as build_table, birthdate_source
import production_adapter as PA
import run_npv_simulation as RNS
import star_candidates as SC
from run_skater_contract_test import Boot, _count

SCRIPT_VERSION = "1.0"
HORIZONS = (0, 1, 2, 3, 4, 5)
KEYS = ["career_key", "page", "h"]
KEY = "contract_id"
AGE_BANDS = ([0, 24, 28, 31, 60], ["<=24", "25-28", "29-31", "32+"])
MODELS = {"model1": PA.ProductionChain, "model3": SC.candidate(gp=True),
          "model6": SC.candidate(gp=True, contracts=True),
          "model4": RNS.LEADER, "model7": SC.RebuiltStatusGamesLevel}
LABEL = {"model1": "Model 1 current", "model3": "Model 3 (base)",
         "model6": "Model 6 = 3 + contract status", "model4": "Model 4 rebuilt (adopted)",
         "model7": "Model 7 = 4 + games change"}
READS = ("model6", "model4", "model7")
# Dollar_Rescore.md, adopted line, the current model's answerable contracts, point RMSE ($M)
RECORDED_RMSE = {"model1": 3.681, "model3": 3.555, "model4": 3.614}


# --------------------------------------------------------------------------- seasons
def run_seasons(table, pages=C.DEV_PAGES):
    har = H.Harness(table)
    runs, inst = {}, {}
    for k, cls in MODELS.items():
        inst[k] = cls()
        runs[k] = har.run(inst[k], pages=pages, horizons=HORIZONS)
        C.log(f"  ran {LABEL[k]} ({cls.__name__}): {len(runs[k])} forecasts")
    for k in READS:
        assert getattr(inst[k], "reads_contracts", False), (
            f"{LABEL[k]} did not read the contract export: its participation fell back "
            "to no contract data. Check PUCKPEDIA_CONTRACTS_XLSX / the contracts CSV "
            "path in .env before running this test.")
    C.log("  guard: Models 6, 4 and 7 each read the contract export")
    al = {k: d.set_index(KEYS).sort_index() for k, d in runs.items()}
    ref = al["model3"]
    for k, d in al.items():
        assert d.index.equals(ref.index), f"{k} answered different rows"
        for c in ("act_war", "played"):
            assert np.array_equal(d[c].to_numpy(), ref[c].to_numpy()), f"{k}: target {c} differs"
    same = lambda a, b, c: np.array_equal(al[a][c].to_numpy(), al[b][c].to_numpy())
    assert same("model6", "model3", "rate_82") and same("model6", "model3", "gp_share")
    assert not same("model6", "model3", "p_play"), "contract status changed nothing"
    assert same("model7", "model4", "rate_82") and same("model7", "model4", "p_play")
    assert not same("model7", "model4", "gp_share")
    C.log("  guards: one row set and target; Model 6 moves only the chance of playing")
    C.log("  against Model 3; Model 7 only the games share against Model 4")
    return al


def score_seasons(al, label, keep):
    base = al["model3"].reset_index()[keep]
    boot = Boot(base["career_key"])
    se_of = lambda k: ((al[k].reset_index()[keep]["pred_war"] - base["act_war"]) ** 2)
    br_of = lambda k: ((al[k].reset_index()[keep]["p_play"] - base["played"].astype(float)) ** 2)
    star = (base["tier"] == "3+").to_numpy()
    s15 = star & (base["h"] >= 1).to_numpy()
    boot_s15 = Boot(base.loc[s15, "career_key"])
    C.log(f"  SEASON FORECASTS, {label}: {int(keep.sum())} forecasts, "
          f"{base['career_key'].nunique()} players; 3+ tier {base.loc[star, 'career_key'].nunique()} players")
    C.log(f"    {'model':<32}{'RMSE':>8}{'lower':>11}{'MAE':>8}{'Brier':>8}{'higher':>11}"
          f"{'3+ bias, seasons 1-5 [95%]':>30}")
    for k in MODELS:
        d = al[k].reset_index()[keep]
        e = d["pred_war"] - d["act_war"]
        lo = "--" if k == "model3" else _count(boot.lower_share(se_of("model3"), se_of(k)))
        hb = "--" if k == "model3" else _count(boot.lower_share(br_of(k), br_of("model3")))
        m, a, b = boot_s15.mean_ci(e[s15])
        C.log(f"    {LABEL[k]:<32}{np.sqrt((e ** 2).mean()):>8.4f}{lo:>11}{e.abs().mean():>8.4f}"
              f"{br_of(k).mean():>8.4f}{hb:>11}      {m:+.3f} [{a:+.3f}, {b:+.3f}]")
    C.log("    ('lower' = resamples, of 2,000, with lower squared error than Model 3; 'higher' =")
    C.log("    with HIGHER Brier than Model 3)")
    for a_, b_ in (("model7", "model6"), ("model4", "model6"), ("model4", "model7")):
        C.log(f"    {LABEL[b_]} against {LABEL[a_]}: squared error lower in "
              f"{_count(boot.lower_share(se_of(a_), se_of(b_)))}")
    C.log("    3+ tier season-WAR bias by seasons ahead:")
    for k in MODELS:
        d = al[k].reset_index()[keep]
        e = d["pred_war"] - d["act_war"]
        C.log(f"      {LABEL[k]:<32}" + "".join(
            f"{e[star & (d['h'] == h).to_numpy()].mean():>+8.2f}" for h in HORIZONS))
    C.log("    chance of playing, three to five seasons out, predicted/observed, by tier and age:")
    for tier in ("3+", "2 to 3", "1 to 2", "0 to 1"):
        C.log(f"      tier {tier}:")
        for k in ("model3", "model6", "model4", "model7"):
            d = al[k].reset_index()[keep]
            d = d[(d["tier"] == tier) & (d["h"] >= 3)].copy()
            d["band"] = pd.cut(d["age"], AGE_BANDS[0], labels=AGE_BANDS[1])
            C.log(f"        {LABEL[k]:<30} " + " | ".join(
                f"{b} {d.loc[d['band'] == b, 'p_play'].mean():.2f}/{d.loc[d['band'] == b, 'played'].mean():.2f}"
                for b in AGE_BANDS[1]))
    if label.startswith("rows the current model answers"):
        better = boot.lower_share(se_of("model3"), se_of("model6")) >= 0.975
        worse_brier = boot.lower_share(br_of("model6"), br_of("model3")) >= 0.975
        C.log("    THE DECLARED RULE: Model 6 " +
              ("IMPROVES Model 3" if better and not worse_brier else "does not improve Model 3"))
    C.log("")


# --------------------------------------------------------------------------- dollars
def run_dollars(table):
    import run_skater_dollar_scoring as SDS
    from contract_price_model import contract_sample
    from run_model_scorecard import production_unanswerable
    from dollar_scoring import realised_path, score_on_line, report_scores
    from run_dollar_rescore import by_term
    sample = contract_sample()
    dev = [int(y) for y in sorted(sample["start_yr"].dropna().unique())
           if int(y) not in C.CONFIRMATORY_START_YEARS]
    cohorts = C.check_market_cohorts(dev, "run_contract_status_test")
    priced, results = {}, {}
    for k, cls in MODELS.items():
        pt, lines, ok, _ = SDS.price_and_simulate(k, cls, sample, table, cohorts, simulate=False)
        priced[k] = (pt, lines)
        results[k] = pt[[KEY, "end_yr"]]
    common = sorted(set.intersection(*[
        set(r.loc[r["end_yr"] <= C.LAST_SOURCE_SEASON, KEY]) for r in results.values()]))
    rows_of = {k: priced[k][0].set_index(KEY) for k in priced}
    labels = tuple(MODELS)
    real = realised_path(table)
    fallback = production_unanswerable(sample, common)
    C.log(f"CONTRACT DOLLARS, $M per contract. {len(common)} ended contracts; {len(fallback)} "
          "have no current-model anchor at signing. Point valuations.")
    C.log("  labels: " + "; ".join(f"{k} = {LABEL[k]}" for k in MODELS))
    C.log("")
    for line_label in ("model4", "model1"):
        d = score_on_line(common, rows_of, priced[line_label][1], {}, labels, real)
        d["production_answerable"] = ~d[KEY].isin(fallback)
        tag = "PRIMARY" if line_label == "model4" else "sensitivity"
        for sub, dd in (("all contracts", d),
                        ("the current model's answerable contracts", d[d["production_answerable"]].copy())):
            C.log(f"  on {LABEL[line_label]}'s line ({tag}), {sub}: {len(dd)} contracts, "
                  f"{dd['pkey'].nunique()} players")
            report_scores(dd, labels, exact=True)
            report_scores(dd, ("model3", "model6"), exact=True)
            report_scores(dd, ("model7", "model6"), exact=True)
            by_term(dd, rows_of["model4"], labels)
            C.log("")
            if line_label == "model4" and sub.startswith("the current"):
                for k, want in RECORDED_RMSE.items():
                    got = float(np.sqrt((((dd[f"point_{k}"] - dd["realised"]) / 1e6) ** 2).mean()))
                    assert abs(got - want) < 0.001, (
                        f"{LABEL[k]} dollar RMSE {got:.3f} does not reproduce the recorded {want:.3f}")
                C.log("  guard: Models 1, 3 and 4 reproduce the recorded re-score on this table")
                C.log("")
        if line_label == "model4":
            d.to_csv(C.out_path("contract_status_dollars.csv"), index=False)


def check_contracts() -> None:
    """Fail fast, before any model runs, if the contract export cannot be read."""
    from contract_source import load_contracts
    try:
        df, _ = load_contracts()
    except Exception as e:                                  # noqa: BLE001
        raise SystemExit(
            f"The contract export could not be read ({type(e).__name__}: {e}). This test needs "
            f"it at {C.F_CONTRACTS_CSV}. Nothing was run.") from e
    C.log(f"  contract export read: {len(df):,} rows from {C.F_CONTRACTS_CSV}")


def main() -> None:
    C.banner("run_contract_status_test.py", SCRIPT_VERSION)
    check_contracts()
    SFP = PA._production()[0]
    C.log(f"  production age table read: {Path(SFP.F_WAR_AGE).resolve()}")
    path, how = birthdate_source()
    C.log(f"  birthdates: {how}")
    table = build_table(birthdate_csv=path, verbose=False)
    C.log("")
    al = run_seasons(table)
    C.log("")
    ans = al["model1"]["outside_production"].eq(0).to_numpy()
    score_seasons(al, "rows the current model answers", ans)
    score_seasons(al, "full grid (current model plus its fallback)", np.ones(len(ans), bool))
    pd.concat([d.reset_index().assign(model=k) for k, d in al.items()], ignore_index=True).to_csv(
        C.out_path("contract_status_seasons.csv"), index=False)
    C.write_log("contract_status_run_log.txt")        # the season part is saved even if dollars fail
    if "--no-dollars" not in sys.argv:
        run_dollars(table)
        C.write_log("contract_status_run_log.txt")


if __name__ == "__main__":
    main()
