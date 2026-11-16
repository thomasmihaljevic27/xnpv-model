"""
term_quality_test.py - does a longer contract predict that the player out-performs his forecast?
(Thomas, 2026-11-13: "Yes, run it"; declared in 40_DOCS/Backtest_Protocol.md before it was built. Report only.)

WHY. The price line pays gamma_term = 0.0089103 of a cap a season ($0.851M at the 2025-26 cap) for each year of term.
If that premium is QUALITY THE FORECAST MISSES (clubs give long deals to players better than the forecast says), the
player keeps that quality all through the deal, and a mid-contract season should be priced on the contract's original
term. If the premium BUYS LENGTH ALONE, the forecast already holds all the quality there is, and pricing on the term
left (the model as built, directive 4) is defensible. Only the first predicts that longer contracts out-perform their
forecast. STANDING_FLAGS, "The remaining-term rule".

WHAT IT COMPARES
  sample     the price line's 2,336 skater contracts (30_OUTPUT/term_average_price_line_rows.csv: standard UFA and RFA
             contracts starting 2018-2025, forecast dated at the signing; its row order is the Stata export's
             price_line_skaters.csv, asserted, which carries the RFA flag; birthdates from xnpv1_birthdates.csv by the player key)
  forecast   for contract season j (j = 1 is the first season), the forecast's expected season WAR from the SIGNING
             page: chance of playing x WAR if he plays, at h = (seasons from the signing page to the start) + j - 1
             (30_OUTPUT/xnpv1_forecasts.csv, skater_forecast v2.4, by the career key player_season_table gives the
             contract's player key). GUARD: WAR if he plays in the first season equals the price line's own x_first.
  delivered  the forecast harness's target (forecast_harness.outcomes): his season WAR in the player-season table,
             short seasons on 82 games (D20), ZERO for a season he did not play. Seasons through 2025-26 only.
  the miss   delivered minus forecast, in dollars a season at the 2025-26 cap, on the price line's slope (forwards
             0.0175093 of a cap per win, defencemen 0.0215858)
  the fit    the miss regressed on the contract's length in years, separately for the first, second and third season
             of the contract (so the forecast horizon is the same for every contract in a fit):
               fit 1  length, the first-season forecast (WAR if he plays), defence
               fit 2  fit 1 + signed as an RFA + age at signing
               fit 3  length, defence, and the first-season forecast in fifths (no straight-line form imposed)
  intervals  2,000 resamples of players (a player with several contracts counts once), seed 20261113
  benchmark  a length coefficient of $0.851M a season per year means the whole term premium is quality the forecast
             misses; zero means it buys length alone

LIMITS (stated, not fixed)
  - the forecast is known to under-forecast the best players (STANDING_FLAGS); fits 1 and 3 hold the forecast fixed, so
    length is credited only with what it adds beyond the forecast
  - a contract's later seasons are seen only for contracts signed early enough; the second- and third-season fits are
    on fewer, older contracts (counts printed)
  - a player bought out keeps his delivered WAR (the question is the player, not the deal)

INPUTS: OUTPUT_DIR/term_average_price_line_rows.csv, stata/price_line_skaters.csv, xnpv1_forecasts.csv,
        contract_level_spine.csv; the player-season table (player_season_table.build)
OUTPUTS: OUTPUT_DIR/term_quality_test_log.txt, term_quality_test.csv, term_quality_test_rows.csv
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
load_dotenv()
import forecast_config as C                          # noqa: E402  the last season in the source
import player_season_table as PST                    # noqa: E402  the harness's table
import skater_forward_projection as SFP              # noqa: E402  the price line in force, the cap

OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
SCRIPT_VERSION = "term_quality_test.py v1.1 (2026-11-15)"   # v1.1: birthdates by player key (v1.0 joined the Stata cluster id to the spine: 75 of 2,297)
N_BOOT, SEED = 2000, 20261113
CAP_NOW = SFP.CAP_CEILING[2025]
LOG, OUT = [], []


def log(s=""):
    print(s)
    LOG.append(s)


def ols(y, X):
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    return b


def fit(d, cols, rng, label):
    """OLS of the dollar miss on [constant] + cols; the length coefficient with a player-resampled interval."""
    X = np.column_stack([np.ones(len(d))] + [d[c].to_numpy(float) for c in cols])
    y = d["miss_M"].to_numpy(float)
    b = ols(y, X)
    i_len = 1 + cols.index("length")
    groups = d["nk"].to_numpy()
    uniq = np.unique(groups)
    idx_by = {g: np.flatnonzero(groups == g) for g in uniq}
    bs = []
    for _ in range(N_BOOT):
        pick = np.concatenate([idx_by[g] for g in uniq[rng.integers(0, len(uniq), len(uniq))]])
        try:
            bs.append(ols(y[pick], X[pick])[i_len])
        except np.linalg.LinAlgError:
            continue
    bs = np.array(bs)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    p = min(1.0, 2 * min((bs <= 0).mean(), (bs >= 0).mean()))
    return b[i_len], lo, hi, p


def main():
    rng = np.random.default_rng(SEED)
    log(SCRIPT_VERSION)
    log(f"  reads {OUTPUT_DIR}")
    alpha, bf, bd, gamma, line = SFP.price_constants()
    bench = gamma * CAP_NOW / 1e6
    log(f"  price line: {line}; per win F {bf:.7f}, D {bd:.7f}; term {gamma:.7f} of a cap a season per year = ${bench:.3f}M at the 2025-26 cap")
    r = pd.read_csv(OUTPUT_DIR / "term_average_price_line_rows.csv")
    st = pd.read_csv(OUTPUT_DIR / "stata" / "price_line_skaters.csv")
    assert len(r) == len(st) and (r["start_yr"].values == st["first_season"].values).all() \
        and (r["length"].values == st["term"].values).all() and (r["is_d"].values == st["defence"].values).all()   # GUARD: same rows, same order
    r["rfa"] = st["rfa"].values
    # birthdates by the contract's player key (xnpv1_birthdates.csv, the forecast's own; the Stata file's player_id is a
    # renumbered cluster id, not PuckPedia's, so it cannot be joined to the spine)
    bdt = pd.read_csv(OUTPUT_DIR / "xnpv1_birthdates.csv").drop_duplicates("pkey").set_index("pkey")["birthdate"]
    r["birth"] = pd.to_datetime(r["nk"].map(bdt), errors="coerce")
    r["age"] = (pd.to_datetime(r["signed"]) - r["birth"]).dt.days / 365.25
    bdsrc, _ = PST.birthdate_source()
    T = PST.build(birthdate_csv=bdsrc, verbose=False)
    ck = T.drop_duplicates("pkey").set_index("pkey")["career_key"]
    r["career_key"] = r["nk"].map(ck)
    assert r["career_key"].notna().all()                                            # GUARD: every contract's player in the table
    act = T.groupby(["career_key", "syr"])["WAR"].sum()                               # one row a player-season (traded mid-season: added up)
    fc = pd.read_csv(OUTPUT_DIR / "xnpv1_forecasts.csv", usecols=["career_key", "page", "h", "p_play", "war_if_plays",
                                                                 "skater_forecast_version"])
    log(f"  forecasts: skater_forecast v{sorted(fc['skater_forecast_version'].unique())}; last season in the source {C.LAST_SOURCE_SEASON}")
    fc = fc.set_index(["career_key", "page", "h"])
    # GUARD: the saved forecast's first-season WAR if he plays is the price line's own x_first
    f1 = [fc["war_if_plays"].get((k, int(p), int(h)), np.nan) for k, p, h in zip(r["career_key"], r["sign_page"], r["sign_h"])]
    gap = np.nanmax(np.abs(np.array(f1) - r["x_first"].to_numpy()))
    n_miss = int(np.isnan(f1).sum())
    log(f"  guard: first-season forecast against the price line's x_first: largest gap {gap:.2e} WAR; contracts without a saved forecast {n_miss}")
    assert gap < 1e-6, gap
    # season rows
    rows = []
    for c in r.itertuples():
        for j in range(1, int(c.length) + 1):
            s = int(c.start_yr) + j - 1
            if s > C.LAST_SOURCE_SEASON:
                break
            h = int(c.sign_h) + j - 1
            k = (c.career_key, int(c.sign_page), h)
            if k not in fc.index:
                continue
            p_, w_ = float(fc.at[k, "p_play"]), float(fc.at[k, "war_if_plays"])
            got = float(act.get((c.career_key, s), 0.0))                              # not in the table: did not play, zero
            slope = bd if c.is_d == 1 else bf
            rows.append({"nk": c.nk, "contract": c.Index, "j": j, "season": s, "length": int(c.length), "is_d": int(c.is_d),
                         "rfa": int(c.rfa), "age": c.age, "x_first": c.x_first, "expected_war": p_ * w_, "delivered_war": got,
                         "miss_war": got - p_ * w_, "miss_M": (got - p_ * w_) * slope * CAP_NOW / 1e6})
    d = pd.DataFrame(rows)
    d.to_csv(OUTPUT_DIR / "term_quality_test_rows.csv", index=False)
    log(f"  age at signing known for {int(r['age'].notna().sum())} of {len(r)} contracts")
    log(f"  contract-seasons scored: {len(d):,} ({d['contract'].nunique():,} contracts, {d['nk'].nunique():,} players)")

    # ---- the plain picture: mean miss by length -----------------------------------------------------------------------------
    log("\nTHE MISS BY CONTRACT LENGTH (delivered minus forecast, $M a season at the 2025-26 cap; WAR in brackets)")
    bands = [("1 season", [1]), ("2 seasons", [2]), ("3 or 4", [3, 4]), ("5 or 6", [5, 6]), ("7 or 8", [7, 8])]
    log(f"  {'length':<12}" + "".join(f"{'season ' + str(j) + ' of the contract':>34}" for j in (1, 2, 3)))
    for lab, ls in bands:
        cells = []
        for j in (1, 2, 3):
            g = d[(d["j"] == j) & d["length"].isin(ls)]
            cells.append(f"{g['miss_M'].mean():+.2f} ({g['miss_war'].mean():+.2f} WAR, n={len(g)})" if len(g) else "-")
        log(f"  {lab:<12}" + "".join(f"{c_:>34}" for c_ in cells))

    # ---- the fits ---------------------------------------------------------------------------------------------------------
    log(f"\nTHE LENGTH COEFFICIENT ($M a season of out-performance per extra year of term; ${bench:.3f}M would be the whole premium)")
    log(f"  {'fit':<56}{'season':>7}{'contracts':>10}{'players':>9}{'per year of term':>26}{'p':>8}{'share of premium':>18}")
    for j in (1, 2, 3):
        g = d[d["j"] == j].copy()
        for q, edges in enumerate(np.quantile(g["x_first"], [0.2, 0.4, 0.6, 0.8])):
            g[f"fifth_{q + 2}"] = (g["x_first"] > edges).astype(float)
        g2 = g.dropna(subset=["age"])
        for lab, gg, cols in (("1: length, forecast, defence", g, ["length", "x_first", "is_d"]),
                              ("2: + signed as an RFA, age at signing", g2, ["length", "x_first", "is_d", "rfa", "age"]),
                              ("3: length, defence, forecast in fifths", g, ["length", "is_d"] + [f"fifth_{q}" for q in (2, 3, 4, 5)])):
            e, lo, hi, p = fit(gg, cols, rng, lab)
            log(f"  {lab:<56}{j:>7}{len(gg):>10}{gg['nk'].nunique():>9}{f'{e:+.3f} [{lo:+.3f}, {hi:+.3f}]':>26}{p:>8.3f}{e / bench:>17.0%}")
            OUT.append({"fit": lab, "season_of_contract": j, "contracts": len(gg), "players": gg["nk"].nunique(), "coef_M": e,
                        "lo": lo, "hi": hi, "p": p, "share_of_premium": e / bench, "benchmark_M": bench})
    pd.DataFrame(OUT).to_csv(OUTPUT_DIR / "term_quality_test.csv", index=False)
    (OUTPUT_DIR / "term_quality_test_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
