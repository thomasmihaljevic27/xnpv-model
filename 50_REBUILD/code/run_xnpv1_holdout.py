"""run_xnpv1_holdout.py -- xNPV 1 against xNPV 0, once, on the 2022-2025 pages.

EXPERIMENTAL (50_REBUILD). Nothing is adopted or changed by this run: xNPV 1
was chosen on 2015-2021 (decision D33). This is the confirmation D33 queued.
RUNS ON THE LAPTOP: xNPV 1 reads the contract export, and the runner refuses to
start without it.

WHAT IS COMPARED
    xNPV 1  the model going forward, star_candidates.XNPV1 (Model 6 of the
            2026-09-30 reports)
    xNPV 0  the model running today, production_adapter.ProductionChain
    also reported, NOT deciding: xNPV 1 without contract status
            (star_candidates.candidate(gp=True), "Model 3"), because D33 took
            contract status by deliberate choice after it fell short of the
            declared season bar on 2015-2021. Reading that comparison here does
            not reopen the choice either way; it is recorded so the choice can
            be judged on seasons it was not made on.

THE PAGES
    2022-2025 valuation pages (rebuild_config.CONFIRMATORY_PAGES). The last
    finished season in the source is 2025, so the 2022 page is scored up to
    three seasons ahead and the 2025 page on its valuation season only.
    These pages are REUSED, not sealed: about thirty variants of the earlier
    player chain were examined on them before the rebuild (plan decision D).
    This run is the first rebuild run to spend them, and the harness logs it.

THE RULE, DECLARED BEFORE THE RUN (rows xNPV 0 answers, player resamples)
    xNPV 1 is CONFIRMED if its season-WAR squared error is lower than xNPV 0's
    in at least 1,950 of 2,000 player resamples. Brier, absolute error and the
    star tier's bias are reported beside it and do not decide.
    Whatever the result, nothing is re-selected on these pages afterwards: a
    miss is reported as a miss, with the rows and players it comes from.

WHY SEASONS ONLY
    Dollar scoring needs contracts that have ENDED. Few contracts starting
    2022-2025 have, and those are mostly one- and two-year deals, a sample
    selected on term. Dollars stay on the 2015-2021 start years
    (Contract_Status_Test.md) until more of the reserved cohorts end.

GUARDS
    * the contract export is read before any model runs (fail fast), and the
      xNPV 1 fit reports reads_contracts;
    * one row set and one realised target for all three arms;
    * xNPV 1 and its no-contract twin differ only in the chance of playing;
    * the age table production reads is logged by its real path;
    * ONE RUN: the runner refuses if the inspection ledger already records
      this runner spending the pages, unless --rerun "<reason>" is given
      (e.g. the first run crashed before scoring); the reason is logged.

HOW TO RUN (Windows PowerShell, from the repo root, after syncing):
    python 50_REBUILD\\code\\run_xnpv1_holdout.py
TO TEST THE CODE WITHOUT SPENDING THE PAGES (v1.1):
    python 50_REBUILD\\code\\run_xnpv1_holdout.py --code-test
    runs the same path on development pages 2018-2021 and scores nothing reserved.
    v1.0 was tested in the cloud by running it, with synthetic contracts, which
    scored xNPV 0 and the no-contract twin for real on 2022-2025 (ledger lines
    labelled CLOUD CODE TEST, 2026-09-30). That is why this switch exists.
Output: 50_REBUILD/output/xnpv1_holdout_run_log.txt, the file to send back.
The ledger line it appends (00_STATE/inspection_ledger.csv) is meant to
be committed: it is the record that the pages were spent.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import forecast_harness as H
from player_season_table import build as build_table, birthdate_source
import production_adapter as PA
import star_candidates as SC
from run_skater_contract_test import Boot, _count

SCRIPT_VERSION = "1.1"
PAGES = C.CONFIRMATORY_PAGES
HORIZONS = (0, 1, 2, 3)            # 2022 + 3 = 2025, the last finished season
KEYS = ["career_key", "page", "h"]
ARMS = {"xnpv1": SC.XNPV1, "xnpv0": PA.ProductionChain, "nocontract": SC.candidate(gp=True)}
LABEL = {"xnpv1": "xNPV 1", "xnpv0": "xNPV 0 (current)",
         "nocontract": "xNPV 1 without contract status"}
REASON_TAG = "D33 confirmation"
REASON = ("D33 confirmation: xNPV 1 against xNPV 0, season WAR, rule declared in "
          "run_xnpv1_holdout.py v1.0 (1,950 of 2,000)")


def already_spent() -> bool:
    """True if the ledger already records this confirmation spending reserved
    pages. The harness writes the ledger line under its own name
    ("forecast_harness"), so the line is found by the reason this runner passes,
    which always starts with REASON_TAG."""
    if not C.INSPECTION_LEDGER.exists():
        return False
    with open(C.INSPECTION_LEDGER, newline="", encoding="utf-8") as fh:
        return any((r.get("reason") or "").startswith(REASON_TAG)
                   and (r.get("reserved_keys") or "").strip()
                   for r in csv.DictReader(fh))


def check_contracts() -> None:
    from contract_source import load_contracts
    try:
        df, _ = load_contracts()
    except Exception as e:                                  # noqa: BLE001
        raise SystemExit(
            f"The contract export could not be read ({type(e).__name__}: {e}). xNPV 1 needs "
            f"it at {C.F_CONTRACTS_CSV}. Nothing was run and no page was spent.") from e
    C.log(f"  contract export read: {len(df):,} rows from {C.F_CONTRACTS_CSV}")


def main(argv=sys.argv[1:]) -> None:
    C.banner("run_xnpv1_holdout.py", SCRIPT_VERSION)
    code_test = "--code-test" in argv
    pages = (2018, 2019, 2020, 2021) if code_test else PAGES
    reason = REASON
    if code_test:
        C.log("  CODE TEST: development pages 2018-2021; nothing reserved is scored, "
              "and the verdict below means nothing")
    elif already_spent():
        if "--rerun" not in argv or argv.index("--rerun") + 1 >= len(argv):
            raise SystemExit(
                "The ledger already records this confirmation spending the 2022-2025 pages. "
                "It is a one-time run. If the first run did not finish scoring, rerun with "
                '--rerun "<why>"; the reason is logged.')
        reason = f"{REASON}; RERUN: {argv[argv.index('--rerun') + 1]}"
        C.log(f"  RERUN of a spent confirmation: {reason}")
    check_contracts()
    SFP = PA._production()[0]
    C.log(f"  production age table read: {Path(SFP.F_WAR_AGE).resolve()}")
    path, how = birthdate_source()
    C.log(f"  birthdates: {how}")
    table = build_table(birthdate_csv=path, verbose=False)
    har = H.Harness(table)
    C.log("")

    # ---- run each arm on the reserved pages (the harness logs the unseal)
    al, inst = {}, {}
    for k, cls in ARMS.items():
        inst[k] = cls()
        al[k] = har.run(inst[k], pages=pages, horizons=HORIZONS, unseal=not code_test,
                        reason="" if code_test else reason).set_index(KEYS).sort_index()
        C.log(f"  ran {LABEL[k]} ({cls.__name__}): {len(al[k])} forecasts")
    assert getattr(inst["xnpv1"], "reads_contracts", False), (
        "xNPV 1 did not read the contract export; its chance of playing fell back to no "
        "contract data, so this would not be xNPV 1. The pages are logged as spent: rerun "
        'with --rerun "export not read" once the export path is fixed.')
    ref = al["xnpv1"]
    for k, d in al.items():
        assert d.index.equals(ref.index), f"{k} answered different rows"
        for c in ("act_war", "played"):
            assert np.array_equal(d[c].to_numpy(), ref[c].to_numpy()), f"{k}: target {c} differs"
    for c in ("rate_82", "gp_share"):
        assert np.array_equal(al["nocontract"][c].to_numpy(), ref[c].to_numpy()), f"twin moved {c}"
    C.log("  guards: xNPV 1 read the export; one row set and target for all arms;")
    C.log("  xNPV 1 and its no-contract twin differ only in the chance of playing")
    C.log("")

    # ---- score on the rows xNPV 0 answers
    keep = al["xnpv0"]["outside_production"].eq(0).to_numpy()
    base = ref.reset_index()[keep]
    boot = Boot(base["career_key"])
    d_of = lambda k: al[k].reset_index()[keep]
    se = lambda k: (d_of(k)["pred_war"] - base["act_war"]) ** 2
    ab = lambda k: (d_of(k)["pred_war"] - base["act_war"]).abs()
    br = lambda k: (d_of(k)["p_play"] - base["played"].astype(float)) ** 2
    star = (base["tier"] == "3+").to_numpy()
    s1 = star & (base["h"] >= 1).to_numpy()
    bs = Boot(base.loc[s1, "career_key"]) if s1.any() else None
    C.log(f"  ROWS xNPV 0 ANSWERS: {int(keep.sum())} forecasts, {base['career_key'].nunique()} "
          f"players, pages {pages[0]}-{pages[-1]}, seasons ahead {HORIZONS[0]}-{HORIZONS[-1]}")
    C.log(f"    by page: " + ", ".join(f"{p} {int((base['page'] == p).sum())}" for p in pages))
    C.log(f"    {'model':<34}{'RMSE':>8}{'MAE':>8}{'Brier':>8}{'3+ bias, 1+ ahead [95%]':>30}")
    for k in ARMS:
        e = d_of(k)["pred_war"] - base["act_war"]
        ci = "n/a"
        if bs is not None:
            m, lo, hi = bs.mean_ci(e[s1])
            ci = f"{m:+.3f} [{lo:+.3f}, {hi:+.3f}]"
        C.log(f"    {LABEL[k]:<34}{np.sqrt(se(k).mean()):>8.4f}{ab(k).mean():>8.4f}"
              f"{br(k).mean():>8.4f}      {ci}")
    C.log("    resamples of 2,000 players in which xNPV 1 is lower than each comparator:")
    for k in ("xnpv0", "nocontract"):
        C.log(f"      against {LABEL[k]:<34} squared error {_count(boot.lower_share(se(k), se('xnpv1')))}"
              f", absolute error {_count(boot.lower_share(ab(k), ab('xnpv1')))}"
              f", Brier {_count(boot.lower_share(br(k), br('xnpv1')))}")
    C.log("    season-WAR RMSE by seasons ahead:")
    for k in ARMS:
        C.log(f"      {LABEL[k]:<34}" + "".join(
            f"{np.sqrt(se(k)[(base['h'] == h).to_numpy()].mean()):>8.4f}" for h in HORIZONS))
    C.log("    season-WAR bias (predicted minus realised) by tier, all seasons ahead:")
    for tier in ("3+", "2 to 3", "1 to 2", "0 to 1", "below 0"):
        m = (base["tier"] == tier).to_numpy()
        C.log(f"      tier {tier:<8} ({int(m.sum()):>5} rows) " + " ".join(
            f"{LABEL[k]} {(d_of(k)['pred_war'] - base['act_war'])[m].mean():+.3f}" for k in ARMS))
    confirmed = boot.lower_share(se("xnpv0"), se("xnpv1")) >= 0.975
    C.log("")
    C.log("    THE DECLARED RULE: xNPV 1 is " + (
        "CONFIRMED against xNPV 0" if confirmed else "NOT confirmed against xNPV 0") +
        " (squared error lower in at least 1,950 of 2,000)")
    C.log("    The comparison with the no-contract twin is reported, not decided.")
    pd.concat([d.reset_index().assign(arm=k) for k, d in al.items()], ignore_index=True).to_csv(
        C.out_path("xnpv1_holdout_code_test.csv" if code_test else "xnpv1_holdout_forecasts.csv"),
        index=False)
    C.write_log("xnpv1_holdout_code_test_log.txt" if code_test else "xnpv1_holdout_run_log.txt")


if __name__ == "__main__":
    main()
