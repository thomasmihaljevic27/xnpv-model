"""run_revalidation_2022_2025.py -- the built skater forecast, scored once on the 2022-2025 pages.

WHY (00_STATE/MODEL_DIRECTIVES.md, plan of record step 7: "decide how the changed model is
validated"). The 2022-2025 confirmation of 2026-10-02 scored the forecast as it was then (its
eight-term start with the fitted decay) against xNPV 0. Since then the forecast was changed by
directives 1-3 and investigations A-E (the 50/30/20 starting level pulled 65/35 toward the
comparables, the additive aging walk, the games-share and chance-of-playing changes), every change
chosen on the 2015-2021 development pages only. Thomas chose (2026-10-05) one more scored run on
2022-2025, with the rule written here before the run, reported as a second use of seasons already
seen.

THE PAGES ARE NOT SEALED. They were used before this run by: about thirty variants of the earlier
player chain (plan decision D); a cloud code test on 2026-09-30 that scored xNPV 0 and the no-contract
twin for real; the confirmation itself (2026-10-02, and its re-run on the rebuilt age table); and,
reading realized 2022-2025 seasons without scoring the forecast against a rival on season WAR,
investigation F (Game Value by season) and the price-line tests (2026-10-05). Any report of this run
says so.

WHAT IS COMPARED (season WAR, pages 2022-2025, zero to three seasons ahead)
    built      the forecast as now built (skater_forecast.XNPV1, run here through the harness)
    confirmed  the forecast confirmed on 2026-10-02, and
    xNPV 0     the old chain (production_adapter.ProductionChain),
               both read row by row from the forecasts that confirmation saved
               (xnpv1_holdout_forecasts.csv, its re-run on the rebuilt age table). Neither is re-run:
               their code is archived (git 7f91f0e), and re-running them would score them on these
               pages again. The file must give back the confirmation's recorded figures (guard).

THE RULE, DECLARED BEFORE THE RUN (the confirmation's rule, unchanged)
    On the rows xNPV 0 answers, the built forecast is CONFIRMED against xNPV 0 if its season-WAR
    squared error is lower in at least 1,950 of 2,000 player resamples (seed 20260924, as the
    confirmation).
    Reported, NOT deciding: the built forecast against the confirmed one (the changes were chosen for
    fewer moving parts, and one of them cost 0.9% start RMSE on the development pages, so a small loss
    is not a failure of the rule); absolute error and Brier; RMSE by seasons ahead; bias by trailing
    tier (the harness's 50/30/20 tier, v1.4, for all three, since the rows are the same); all rows
    beside the answerable ones, xNPV 0 labelled "plus its fallback" there.
    Whatever the result, nothing is re-selected on these pages afterwards.

GUARDS, in this order; each one that fails stops the run before any forecast is scored
    1. one run: the ledger must not already record this runner spending the pages (--rerun "<why>"
       overrides, logged);
    2. the contract export is read, and the age table carries 99%+ birthdates (its real path logged);
    3. the saved file is found (--previous PATH, or the one copy under 90_ARCHIVE/ or 50_REBUILD/),
       its hash logged, and it gives back the confirmation of record: RMSE 0.9001 (confirmed) and
       0.9724 (xNPV 0) on the rows xNPV 0 answers;
    4. ROWS AND TARGETS BEFORE ANY MODEL: the 2022-2025 grid (each page's subjects x seasons ahead)
       and its realised WAR and played flag, built from today's season table with the harness's own
       functions, must equal the saved file's, row for row. This reads realised seasons and no
       forecast (ledger line "targets only");
    then the built forecast runs (the harness logs the unseal), and
    5. it read the contract export, and it answered exactly the rows guard 4 checked, with the same
       targets.

HOW TO RUN (Windows PowerShell, repo root; needs the contract export as CSV in SOURCE_DIR, the
rebuilt age table, and the 10-02 saved forecasts on this machine):
    python 25_TESTS/run_revalidation_2022_2025.py --code-test
        runs the whole path on development pages 2018-2021, with comparators made up from the
        built forecast (figures meaningless), plus guards 2-4 on the real saved file. Scores nothing
        reserved. Run this first; send the log.
    python 25_TESTS/run_revalidation_2022_2025.py
        THE RUN. Once. Writes 30_OUTPUT/revalidation_2022_2025_log.txt and the forecasts beside it.
        The ledger lines it appends (00_STATE/inspection_ledger.csv) are meant to be committed.
"""
from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
import numpy as np
import pandas as pd

import forecast_config as C
import forecast_harness as H
import information_set as ISET

SCRIPT_VERSION = "1.0"
PAGES = tuple(C.CONFIRMATORY_PAGES)                  # 2022-2025
CODE_TEST_PAGES = (2018, 2019, 2020, 2021)
HORIZONS = (0, 1, 2, 3)                              # 2022 + 3 = 2025, the last finished season
KEYS = ["career_key", "page", "h"]
N_BOOT, SEED = 2000, 20260924                        # the confirmation's resamples
RULE_DRAWS = 1950
RECORDED = {"xnpv1": 0.9001, "xnpv0": 0.9724}        # DECISIONS.md, confirmation re-run 2026-10-02
REASON_TAG = "Revalidation of the built forecast"
REASON = (f"{REASON_TAG}: built xNPV 1 (skater_forecast) against the 2026-10-02 confirmed forecast and "
          "xNPV 0, season WAR, rule declared in run_revalidation_2022_2025.py v1.0 (1,950 of 2,000 against "
          "xNPV 0)")
RUNNER = "run_revalidation_2022_2025.py"
LABEL = {"built": "built forecast (now)", "confirmed": "confirmed forecast (10-02)",
         "xnpv0": "xNPV 0 (old chain)"}
TIERS = ("3+", "2 to 3", "1 to 2", "0 to 1", "below 0")


# =========================================================================== resampling
class Boot:
    """Player resamples, the confirmation's own: per-player sums over one fixed set of 2,000 draws,
    reused for every statistic so every comparison sees the same draws."""

    def __init__(self, keys: pd.Series, n: int = N_BOOT, seed: int = SEED):
        self.codes, self.uniq = pd.factorize(keys)
        rng = np.random.default_rng(seed)
        self.idx = rng.integers(0, len(self.uniq), size=(n, len(self.uniq)))
        self.cnt = np.bincount(self.codes, minlength=len(self.uniq)).astype(float)

    def sums(self, x) -> np.ndarray:
        return np.bincount(self.codes, weights=np.asarray(x, float), minlength=len(self.uniq))

    def mean_ci(self, x) -> tuple:
        b = self.sums(x)[self.idx].sum(1) / self.cnt[self.idx].sum(1)
        lo, hi = np.percentile(b, [2.5, 97.5])
        return float(np.asarray(x, float).mean()), float(lo), float(hi)

    def lower_count(self, a, b) -> int:
        """In how many resamples b's mean is below a's (an exact count, never a rounded share)."""
        sa, sb = self.sums(a), self.sums(b)
        return int((sb[self.idx].sum(1) < sa[self.idx].sum(1)).sum())


# =========================================================================== guards
def already_spent() -> bool:
    if not C.INSPECTION_LEDGER.exists():
        return False
    with open(C.INSPECTION_LEDGER, newline="", encoding="utf-8") as fh:
        return any((r.get("reason") or "").startswith(REASON_TAG) and (r.get("reserved_keys") or "").strip()
                   for r in csv.DictReader(fh))


def check_inputs() -> None:
    import skater_forecast as SF
    from contract_source import load_contracts
    try:
        df, _ = load_contracts()
    except Exception as e:                                          # noqa: BLE001
        raise SystemExit(f"The contract export could not be read ({type(e).__name__}: {e}); it is needed at "
                         f"{C.F_CONTRACTS_CSV}. Nothing was run and no page was spent.") from e
    C.log(f"  contract export read: {len(df):,} rows from {Path(C.F_CONTRACTS_CSV).resolve()}")
    SF.check_age_coverage(SF.war_age_path())                        # logs the real path; refuses < 99%


def find_previous(argv) -> Path:
    if "--previous" in argv:
        i = argv.index("--previous")
        if i + 1 >= len(argv):
            raise SystemExit("--previous needs a path to xnpv1_holdout_forecasts.csv")
        p = Path(argv[i + 1])
        if not p.exists():
            raise SystemExit(f"--previous {p}: no such file")
        return p
    root = C.REPO_ROOT
    found = sorted({q.resolve() for base in ("90_ARCHIVE", "50_REBUILD") if (root / base).exists()
                    for q in (root / base).rglob("xnpv1_holdout_forecasts.csv")})
    if len(found) != 1:
        where = "\n".join(f"    {q}" for q in found) or "    (none under 90_ARCHIVE/ or 50_REBUILD/)"
        raise SystemExit("The 2026-10-02 confirmation's saved forecasts (xnpv1_holdout_forecasts.csv) must be "
                         f"named once; found {len(found)}:\n{where}\nPass --previous PATH. Nothing was run.")
    return found[0]


def load_previous(path: Path) -> pd.DataFrame:
    """The confirmation's saved rows, wide: one row per (player, page, seasons ahead), the confirmed
    forecast's and xNPV 0's predictions, xNPV 0's fallback flag, and the realised target."""
    sha = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    d = pd.read_csv(path)
    C.log(f"  saved forecasts: {path.resolve()} (sha256 {sha}, {len(d):,} rows, arms "
          f"{', '.join(sorted(d['arm'].astype(str).unique()))})")
    for a in ("xnpv1", "xnpv0"):
        assert a in set(d["arm"]), f"the saved file has no {a} arm"
    d["played"] = d["played"].astype(str).str.lower().map({"true": True, "false": False, "1": True, "0": False,
                                                           "1.0": True, "0.0": False})
    assert d["played"].notna().all(), "the saved file's played flag did not read as true/false"
    x1 = d[d["arm"] == "xnpv1"].set_index(KEYS).sort_index()
    x0 = d[d["arm"] == "xnpv0"].set_index(KEYS).sort_index()
    assert x1.index.is_unique and x1.index.equals(x0.index), "the saved arms do not answer one row set"
    for c in ("act_war", "played"):
        assert np.array_equal(x1[c].to_numpy(), x0[c].to_numpy()), f"the saved arms' target {c} differs"
    w = pd.DataFrame({"act_war": x1["act_war"].astype(float), "played": x1["played"].astype(bool),
                      "pred_confirmed": x1["pred_war"].astype(float), "p_confirmed": x1["p_play"].astype(float),
                      "pred_xnpv0": x0["pred_war"].astype(float), "p_xnpv0": x0["p_play"].astype(float),
                      "outside_production": x0["outside_production"].fillna(0).astype(int)}, index=x1.index)
    return w


def check_recorded(w: pd.DataFrame) -> None:
    keep = w["outside_production"].eq(0)
    got = {"xnpv1": float(np.sqrt(((w.loc[keep, "pred_confirmed"] - w.loc[keep, "act_war"]) ** 2).mean())),
           "xnpv0": float(np.sqrt(((w.loc[keep, "pred_xnpv0"] - w.loc[keep, "act_war"]) ** 2).mean()))}
    C.log(f"  GUARD 3, the confirmation of record: {int(keep.sum()):,} rows xNPV 0 answers; RMSE confirmed "
          f"{got['xnpv1']:.5f} (recorded {RECORDED['xnpv1']}), xNPV 0 {got['xnpv0']:.5f} (recorded {RECORDED['xnpv0']})")
    for k, rec in RECORDED.items():
        assert abs(got[k] - rec) <= 1.01e-4, (
            f"the saved file does not give back the confirmation of record ({k} {got[k]:.5f} against {rec}); "
            "it may be the first run on the faulty age table. Nothing was run.")


def target_grid(table: pd.DataFrame, pages) -> pd.DataFrame:
    """Each page's subjects x seasons ahead, with the realised target, built by the harness's own
    functions exactly as Harness.run builds and scores its rows -- without running any model."""
    out = []
    for t0 in pages:
        iset = ISET.build(table, ISET.decision_date_for_page(t0), t0=t0, lag_days=ISET.AVAILABILITY_LAG_DAYS)
        subs = H.subjects_at(iset)[["career_key", "tier"]]
        g = subs.merge(pd.DataFrame({"h": list(HORIZONS)}), how="cross")
        g = g[t0 + g["h"] <= C.LAST_SOURCE_SEASON]
        act = H.outcomes(table, t0, HORIZONS)[["career_key", "h", "act_war", "act_gp"]]
        g = g.merge(act, on=["career_key", "h"], how="left")
        g["act_war"] = g["act_war"].fillna(0.0)
        g["played"] = g["act_gp"].fillna(0.0) >= C.PARTICIPATION_GP
        g["page"] = t0
        out.append(g)
    return pd.concat(out, ignore_index=True).set_index(KEYS).sort_index()


def check_targets(grid: pd.DataFrame, w: pd.DataFrame, label: str) -> None:
    both = grid.index.intersection(w.index)
    only_now, only_saved = grid.index.difference(w.index), w.index.difference(grid.index)
    dw = (grid.loc[both, "act_war"] - w.loc[both, "act_war"]).abs() > 1e-9
    dp = grid.loc[both, "played"].to_numpy() != w.loc[both, "played"].to_numpy()
    C.log(f"  {label}: today's grid {len(grid):,} rows, saved {len(w):,}; in both {len(both):,}; only today "
          f"{len(only_now):,}; only saved {len(only_saved):,}; realised WAR differs on {int(dw.sum()):,}, "
          f"played on {int(dp.sum()):,}")
    for name, ix in (("only today", only_now), ("only saved", only_saved), ("WAR differs", both[dw.to_numpy()]),
                     ("played differs", both[dp])):
        for r in list(ix)[:5]:
            C.log(f"      {name}: {r}")
    assert not (len(only_now) or len(only_saved) or dw.any() or dp.any()), (
        "today's rows or targets are not the saved file's; the comparison would not be on one target. "
        "Nothing was scored. Send this log.")


# =========================================================================== scoring
def score(al: pd.DataFrame, pages) -> bool:
    """al: one row per (player, page, seasons ahead) with act_war, played, tier, outside_production
    and pred_/p_ columns for each arm. Returns the rule's verdict."""
    arms = ("built", "confirmed", "xnpv0")
    e = {k: al[f"pred_{k}"] - al["act_war"] for k in arms}
    br = {k: (al[f"p_{k}"] - al["played"].astype(float)) ** 2 for k in arms}
    verdict = None
    for first, (scope, keep) in zip((True, False), (("ROWS xNPV 0 ANSWERS (the rule's rows)", al["outside_production"].eq(0).to_numpy()),
                        ("ALL ROWS (xNPV 0 plus its fallback: where it has no anchor, the trailing total "
                         "carried flat)", np.ones(len(al), bool)))):
        b = al[keep].reset_index()
        boot = Boot(b["career_key"])
        E = {k: e[k][keep].to_numpy() for k in arms}
        B = {k: br[k][keep].to_numpy() for k in arms}
        C.log(f"\n  {scope}: {len(b):,} forecasts, {b['career_key'].nunique():,} players, pages "
              f"{pages[0]}-{pages[-1]} (" + ", ".join(f"{p} {int((b['page'] == p).sum()):,}" for p in pages) +
              f"), seasons ahead {HORIZONS[0]}-{HORIZONS[-1]}")
        s1 = ((b["tier"] == "3+") & (b["h"] >= 1)).to_numpy()
        bs = Boot(b.loc[s1, "career_key"]) if s1.any() else None
        C.log(f"    {'forecast':<30}{'RMSE':>8}{'MAE':>8}{'Brier':>8}{'3+ tier bias, 1+ ahead [95%]':>34}")
        for k in arms:
            ci = "n/a"
            if bs is not None:
                m, lo, hi = bs.mean_ci(E[k][s1])
                ci = f"{m:+.3f} [{lo:+.3f}, {hi:+.3f}]"
            lab = "xNPV 0 plus its fallback" if (k == "xnpv0" and first is False) else LABEL[k]
            C.log(f"    {lab:<30}{np.sqrt((E[k] ** 2).mean()):>8.4f}{np.abs(E[k]).mean():>8.4f}"
                  f"{B[k].mean():>8.4f}    {ci:>30}")
        C.log(f"    resamples of {N_BOOT:,} players in which the built forecast is lower:")
        for k in ("xnpv0", "confirmed"):
            C.log(f"      against {LABEL[k]:<28} squared error {boot.lower_count(E[k] ** 2, E['built'] ** 2):,}"
                  f"/{N_BOOT:,}, absolute error {boot.lower_count(np.abs(E[k]), np.abs(E['built'])):,}/{N_BOOT:,}"
                  f", Brier {boot.lower_count(B[k], B['built']):,}/{N_BOOT:,}")
        m, lo, hi = boot.mean_ci(E["built"] ** 2 - E["confirmed"] ** 2)
        C.log(f"    built minus confirmed, mean squared error: {m:+.4f} [{lo:+.4f}, {hi:+.4f}] "
              f"(negative: the built forecast is closer)")
        C.log("    season-WAR RMSE by seasons ahead (" + ", ".join(
            f"{h}: {int((b['h'] == h).sum()):,} rows" for h in HORIZONS) + "):")
        for k in arms:
            C.log(f"      {LABEL[k]:<30}" + "".join(
                f"{np.sqrt((E[k][(b['h'] == h).to_numpy()] ** 2).mean()):>8.4f}" for h in HORIZONS))
        C.log("    season-WAR bias (predicted minus realised) by trailing tier (50/30/20), all seasons ahead:")
        for t in TIERS:
            tm = (b["tier"] == t).to_numpy()
            C.log(f"      tier {t:<8} ({int(tm.sum()):>5,} rows) " + "  ".join(
                f"{LABEL[k].split(' (')[0]} {E[k][tm].mean():+.3f}" for k in arms))
        if first:
            verdict = boot.lower_count(E["xnpv0"] ** 2, E["built"] ** 2) >= RULE_DRAWS
    C.log("")
    C.log("  THE DECLARED RULE: the built forecast is " + ("CONFIRMED" if verdict else "NOT confirmed") +
          f" against xNPV 0 (squared error lower in at least {RULE_DRAWS:,} of {N_BOOT:,} player resamples, "
          "rows xNPV 0 answers).")
    C.log("  The comparison with the confirmed forecast is reported, not decided.")
    return verdict


# =========================================================================== main
def main(argv=sys.argv[1:]) -> None:
    import player_season_table as PST
    import skater_forecast as SF
    C.banner(RUNNER, SCRIPT_VERSION)
    code_test = "--code-test" in argv
    C.log(f"  skater_forecast v{SF.SCRIPT_VERSION}; forecast_harness v{getattr(H, 'SCRIPT_VERSION', '?')}")
    reason = REASON
    if code_test:
        C.log("  CODE TEST: the built forecast on development pages 2018-2021 against comparators made up from it; "
              "the figures and the verdict mean nothing. Guards 2-4 run on the real saved file.")
    elif already_spent():
        if "--rerun" not in argv or argv.index("--rerun") + 1 >= len(argv):
            raise SystemExit("The ledger already records this revalidation spending the 2022-2025 pages. It is a "
                             'one-time run. If the first run stopped before scoring, rerun with --rerun "<why>"; '
                             "the reason is logged.")
        reason = f"{REASON}; RERUN: {argv[argv.index('--rerun') + 1]}"
        C.log(f"  RERUN: {reason}")

    C.log("\n  GUARD 2, inputs:")
    check_inputs()
    path, how = PST.birthdate_source()
    C.log(f"  birthdates: {how}")
    table = PST.build(birthdate_csv=path, verbose=False)

    C.log("\n  GUARD 3, the saved forecasts:")
    prev = load_previous(find_previous(argv))
    check_recorded(prev)

    C.log("\n  GUARD 4, rows and targets on 2022-2025 before any model runs:")
    C.record_inspection(RUNNER, "targets only", PAGES,
                        "rows and realised targets checked against the 2026-10-02 saved forecasts; no forecast "
                        "run or scored" + (" (code test)" if code_test else ""))
    grid = target_grid(table, PAGES)
    check_targets(grid, prev, "2022-2025")

    pages = CODE_TEST_PAGES if code_test else PAGES
    C.log(f"\n  RUNNING the built forecast on pages {pages[0]}-{pages[-1]}" +
          ("" if code_test else " (the harness logs the unseal)"))
    model = SF.XNPV1()
    built = (H.Harness(table).run(model, pages=pages, horizons=HORIZONS, unseal=not code_test,
                                  reason="" if code_test else reason).set_index(KEYS).sort_index())
    assert model.reads_contracts, (
        "the built forecast did not read the contract export (its chance of playing fell back to no contract "
        'data). The pages are logged as spent: rerun with --rerun "export not read" once the path is fixed.')
    C.log(f"  GUARD 5: the built forecast read the contract export; {len(built):,} forecasts")

    if code_test:
        # made-up comparators on the development pages, so the scoring path runs end to end
        rng = np.random.default_rng(1)
        n = len(built)
        al = pd.DataFrame({"act_war": built["act_war"], "played": built["played"], "tier": built["tier"],
                           "pred_built": built["pred_war"], "p_built": built["p_play"],
                           "pred_confirmed": built["pred_war"] + rng.normal(0, 0.15, n),
                           "p_confirmed": built["p_play"],
                           "pred_xnpv0": built["pred_war"] * 1.1 + rng.normal(0, 0.3, n),
                           "p_xnpv0": np.clip(built["p_play"] + rng.normal(0, 0.05, n), 0, 1),
                           "outside_production": (rng.random(n) < 0.1).astype(int)}, index=built.index)
    else:
        assert built.index.equals(grid.index), "the built forecast answered rows other than guard 4's"
        assert np.array_equal(built["act_war"].to_numpy(), grid["act_war"].to_numpy()) and \
            np.array_equal(built["played"].to_numpy(), grid["played"].to_numpy()), \
            "the harness's targets are not guard 4's"
        assert (built["tier"].astype(str).to_numpy() == grid["tier"].astype(str).to_numpy()).all(), "tiers differ"
        al = pd.DataFrame({"act_war": built["act_war"], "played": built["played"], "tier": built["tier"],
                           "pred_built": built["pred_war"], "p_built": built["p_play"]}, index=built.index)
        al = al.join(prev[["pred_confirmed", "p_confirmed", "pred_xnpv0", "p_xnpv0", "outside_production"]],
                     how="left")
        assert al[["pred_confirmed", "pred_xnpv0"]].notna().all().all(), "a saved forecast did not join"
        C.log("  one row set and one realised target for all three forecasts (guards 4 and 5)")
    score(al, pages)
    al.reset_index().to_csv(C.out_path("revalidation_code_test.csv" if code_test else
                                       "revalidation_2022_2025_forecasts.csv"), index=False)
    p = C.write_log("revalidation_code_test_log.txt" if code_test else "revalidation_2022_2025_log.txt")
    print(f"\nwritten: {p}")


if __name__ == "__main__":
    main()
