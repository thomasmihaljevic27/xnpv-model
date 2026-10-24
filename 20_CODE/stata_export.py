"""
stata_export.py -- the draft pick curve's and the prospect model's regression data as flat CSVs, for Stata (v1.0).

WHY: every regression in "Valuing Draft Picks" and "Valuing Prospects" should be reproducible by hand in Stata from
files on disk (supervisor meeting, 2026-10-23). This script writes those files. It builds no data of its own: every
row and every variable comes from the functions the model runs (prospect_values.star_values, production_rates,
production_fits, production_features), so the CSVs cannot drift from the model.

OUTPUTS (OUTPUT_DIR/stata/; the codebook is 40_DOCS/Stata_Data_Codebook.md):
  draft_players.csv       one row per drafted player, 2007-2017 (2,322): the pick curve's outcome (his career
                          net present value) and his draft position's star probability.
  prospect_seasons.csv    one row per drafted player and season D+1 to D+8 (k = 0..7, seasons to 2025-26): the
                          prospect model's outcome (his remaining net present value from that season) and every input, with the
                          flags that pick out each regression's sample.
  production_seasons.csv  one row per Elite Prospects season line (player, season, league) for the 2007-2017
                          skater draftees: games, points and the NHLe factor, from which nhle82 is built.
  stata_export_log.txt    the run log, with every check below.

CHECKS (each must PASS or the script stops; each regression is refitted from the CSV as written, read back from disk):
  1. The prospect-season rows used by the model equal the CSV's sample flags, row for row, with the same outcome and
     inputs (to 1e-9).
  2. The pick curve: draft_players.csv refitted (through zero, robust errors) gives pick_curve_scales.csv's star
     value and standard error.
  3. The star values by season (Valuing Prospects Table 2): prospect_seasons.csv refitted gives prospect_values'
     star values and clustered standard errors.
  4. The adopted model (Table 9): prospect_seasons.csv refitted with years past first eligibility gives
     prospect_values' coefficients; refitted with age less 18 (the document's form) it gives the same fitted values
     and age coefficient, with production's coefficient shifted by k times the age coefficient.
  5. production_seasons.csv, collapsed as the model collapses it, gives the model's NHLe rate for every
     player-season.

Run from the repo root:  python 20_CODE/stata_export.py   (after prospect_values.py; reads its inputs only)
"""

import sqlite3

import numpy as np
import pandas as pd
import statsmodels.api as sm

import prospect_values as PV

SCRIPT_VERSION = "stata_export.py v1.0 (2026-10-23)"
OUTPUT_DIR, SOURCE_DIR = PV.OUTPUT_DIR, PV.SOURCE_DIR
OUT = OUTPUT_DIR / "stata"
TOL = 1e-9
GROUP_NUM = {"0": 1, "1": 2, "2": 3, "3": 4, "4+": 5}              # season_group 1..5 = D+1, D+2, D+3, D+4, D+5 on
GROUP_LABEL = {1: "D+1", 2: "D+2", 3: "D+3", 4: "D+4", 5: "D+5 and later"}

LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def season_label(y):
    return f"{y}-{(y + 1) % 100:02d}"


def ols(y, X, groups=None):
    """Through zero (no constant), as every pick and prospect regression. Clustered errors when groups is given
    (Stata: vce(cluster player_id)), robust HC1 otherwise (Stata: vce(robust)); both carry Stata's small-sample
    corrections."""
    if groups is None:
        return sm.OLS(y, X).fit(cov_type="HC1")
    return sm.OLS(y, X).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(groups)[0]})


def stacked(frame, cols_by_group):
    """One regression on every row of frame: each column of cols_by_group[g] multiplied by the indicator for season
    group g, through zero, errors clustered by player (prospect_values.fit_stacked, on the CSV's own columns)."""
    blocks, names = [], []
    for g in sorted(cols_by_group):
        on = (frame["season_group"] == g).values
        for c in cols_by_group[g]:
            blocks.append(np.where(on, frame[c].values, 0.0))
            names.append((g, c))
    m = ols(frame["remaining_npv_m"].values, np.column_stack(blocks), frame["player_id"].values)
    return {n: (float(m.params[i]), float(m.bse[i])) for i, n in enumerate(names)}, m


def main():
    log(SCRIPT_VERSION)
    OUT.mkdir(parents=True, exist_ok=True)
    pc_log = (OUTPUT_DIR / "pick_curve_log.txt").read_text(encoding="utf-8").splitlines()[0]
    pv_log = (OUTPUT_DIR / "prospect_values_log.txt").read_text(encoding="utf-8").splitlines()[0]
    log(f"  built from: {pc_log}; {pv_log} (outputs in {OUTPUT_DIR.resolve()})")
    if pv_log != PV.SCRIPT_VERSION:
        log(f"  NOTE: prospect_values_log.txt was written by {pv_log}, the code here is {PV.SCRIPT_VERSION}")

    # ---- the model's own rows -----------------------------------------------------------------------------------
    sv, fitrows = PV.star_values()            # every drafted player 2007-2017 (deceased out) x k = 0..7, to 2025-26
    rates = PV.production_rates()             # {(EP id, season): NHLe points per 82}, seasons of 10+ games
    fits, prow = PV.production_fits(fitrows, rates)   # the skater prospect-seasons the adopted model is fitted on

    # ---- identities: who each drafted player is ------------------------------------------------------------------
    pl = pd.read_csv(OUTPUT_DIR / "pick_curve_players.csv")
    link = pd.read_csv(OUTPUT_DIR / "draft_pick_linkage.csv", parse_dates=["birthDate"])
    link = link[["draftYear", "overallPickNumber", "birthDate"]].rename(columns={"overallPickNumber": "pick"})
    con = sqlite3.connect(OUTPUT_DIR / "ep_out" / "ep_prospects.db")
    ep = pd.read_sql("select draft_year draftYear, draft_overall pick, ep_player_id, position_ep "
                     "from ep_draft_selections", con)
    ep = ep[ep["draftYear"].between(2007, 2017)]
    assert not ep.duplicated(["draftYear", "pick"]).any(), "two Elite Prospects rows for one draft position"
    assert not link.duplicated(["draftYear", "pick"]).any(), "two linkage rows for one draft position"
    ep["ep_player_id"] = pd.to_numeric(ep["ep_player_id"]).astype("Int64").astype(str).replace("<NA>", "")
    ident = (pl.merge(link, on=["draftYear", "pick"], how="left")
               .merge(ep, on=["draftYear", "pick"], how="left"))
    ident["player_id"] = ident["draftYear"] * 1000 + ident["pick"]              # e.g. 2017013 = 2017, 13th overall
    ident["is_defence"] = ident["position_ep"].astype(str).str.startswith("D").astype(int)   # as prospect_nhle_look

    # ---- 1. draft_players.csv --------------------------------------------------------------------------------------
    players = pd.DataFrame({
        "player_id": ident["player_id"], "draft_year": ident["draftYear"], "pick": ident["pick"],
        "round": ident["round"], "player_name": ident["player"], "position": ident["position"],
        "position_ep": ident["position_ep"], "is_goalie": ident["is_goalie"].astype(int),
        "is_defence": ident["is_defence"], "team": ident["team"],
        "birth_date": ident["birthDate"].dt.strftime("%Y-%m-%d"), "ep_player_id": ident["ep_player_id"],
        "p_star": ident["p_star"], "control_ends": ident["window_end"], "nhl_seasons": ident["nhl_seasons"],
        "career_war": ident["war"], "route": ident["route"],
        "career_npv_m": ident["surplus"] / 1e6,                                     # the pick curve's outcome
        "excluded_deceased": ident["excluded_deceased"].astype(int)})
    players.to_csv(OUT / "draft_players.csv", index=False)

    # ---- 2. prospect_seasons.csv ------------------------------------------------------------------------------------
    d = fitrows.merge(ident[["draftYear", "pick", "player_id", "player", "position", "position_ep", "is_goalie",
                             "is_defence", "birthDate", "ep_player_id", "window_end"]],
                      on=["draftYear", "pick"], how="left", validate="many_to_one")
    d["season"] = d["draftYear"] + d["k"]
    sk = ~d["is_goalie"].astype(bool)
    assert d["player_id"].notna().all() and d.loc[sk, "birthDate"].notna().all()   # as production_fits (skaters)
    assert (d.loc[sk, "ep_player_id"] != "").all(), "a skater without an Elite Prospects id"
    feats = PV.production_features(d.loc[sk, ["ep_player_id", "season", "k", "birthDate"]].reset_index(drop=True), rates)
    feats.index = d.index[sk]
    age = (pd.to_datetime(d["season"].astype(str) + "-09-15") - d["birthDate"]).dt.days / 365.25   # as production_features
    rows = pd.DataFrame({
        "player_id": d["player_id"], "draft_year": d["draftYear"], "pick": d["pick"], "player_name": d["player"],
        "position": d["position"], "position_ep": d["position_ep"], "is_goalie": d["is_goalie"].astype(int),
        "is_defence": d["is_defence"], "birth_date": d["birthDate"].dt.strftime("%Y-%m-%d"),
        "ep_player_id": d["ep_player_id"], "p_star": d["p_star"],
        "k": d["k"], "dplus": d["k"] + 1, "season": d["season"], "season_label": d["season"].map(season_label),
        "season_group": d["k_group"].astype(str).map(GROUP_NUM), "season_group_label": None,
        "in_control": (d["season"] < d["window_end"]).astype(int),
        "prospect": d["prospect"].astype(int),
        "sample_star": d["prospect"].astype(int),                                  # Section 1: every position
        "sample_production": (d["prospect"] & sk).astype(int),                     # Sections 2-3: skaters
        "remaining_npv_m": d["remaining_M"],
        "nhle82": feats["nhle82"], "nhle82_sq": feats["nhle82_sq"],
        "n_prod_seasons": feats["n_prod_seasons"], "no_record": feats["no_record"],
        "age": age, "age_m18": age - 18.0,
        "prod_x_age_m18": feats["nhle82"] * (age - 18.0),                           # the document's age term
        "years_past_elig": feats["past_elig"], "prod_x_years_past_elig": feats["prod_x_age"]})   # the code's
    rows["season_group_label"] = rows["season_group"].map(GROUP_LABEL)
    assert rows["season_group"].notna().all()
    rows.to_csv(OUT / "prospect_seasons.csv", index=False)

    # ---- 3. production_seasons.csv ----------------------------------------------------------------------------------
    nh = pd.read_csv(SOURCE_DIR / "nhle_temporal.csv")
    fac = {(r.league, int(r.season_start_year)): float(r.nhle) for r in nh.itertuples()}
    imputed = set()
    for lg in nh["league"].unique():                                                # as production_rates
        if (lg, 2012) not in fac and (lg, 2011) in fac and (lg, 2013) in fac:
            fac[(lg, 2012)] = (fac[(lg, 2011)] + fac[(lg, 2013)]) / 2
            imputed.add(lg)
    s = pd.read_sql("select ep_player_id, season, league, gp, tp from ep_skater_seasons", con)
    s["ep_player_id"] = pd.to_numeric(s["ep_player_id"]).astype(int).astype(str)
    s["gp"], s["tp"] = pd.to_numeric(s["gp"], errors="coerce"), pd.to_numeric(s["tp"], errors="coerce")
    s = s[(s["gp"] > 0) & s["tp"].notna()].copy()                                   # as production_rates
    who = ident.loc[~ident["is_goalie"].astype(bool) & (ident["ep_player_id"] != ""), ["ep_player_id", "player_id"]]
    s = s.merge(who, on="ep_player_id", how="inner")
    s["season_start"] = s["season"].str[:4].astype(int)
    s["nhle_factor"] = [fac.get((lg, y)) for lg, y in zip(s["league"], s["season_start"])]
    s["factor_imputed_2012"] = [int(y == 2012 and lg in imputed) for lg, y in zip(s["league"], s["season_start"])]
    s["nhle_points"] = s["tp"] * s["nhle_factor"]
    prod = s[["player_id", "ep_player_id", "season_start", "season", "league", "gp", "tp", "nhle_factor",
              "factor_imputed_2012", "nhle_points"]].rename(columns={"season": "season_ep", "tp": "points"})
    prod = prod.sort_values(["player_id", "season_start", "league"]).reset_index(drop=True)
    prod.to_csv(OUT / "production_seasons.csv", index=False)
    log(f"\n  wrote draft_players.csv ({len(players):,} rows), prospect_seasons.csv ({len(rows):,} rows), "
        f"production_seasons.csv ({len(prod):,} rows) in {OUT.resolve()}")

    # =============================== the checks, on the CSVs as written ===============================================
    P = pd.read_csv(OUT / "draft_players.csv")
    R = pd.read_csv(OUT / "prospect_seasons.csv", dtype={"ep_player_id": str})
    Q = pd.read_csv(OUT / "production_seasons.csv", dtype={"ep_player_id": str})

    # 1. the model's rows are the CSV's flagged rows, with the same values
    r2 = R[R["sample_production"] == 1].sort_values(["draft_year", "pick", "k"]).reset_index(drop=True)
    pm = prow.sort_values(["draftYear", "pick", "k"]).reset_index(drop=True)
    assert len(r2) == len(pm) and (r2["draft_year"].values == pm["draftYear"].values).all() \
        and (r2["pick"].values == pm["pick"].values).all() and (r2["k"].values == pm["k"].values).all()
    for a_, b_ in (("remaining_npv_m", "remaining_M"), ("nhle82", "nhle82"), ("nhle82_sq", "nhle82_sq"),
                   ("years_past_elig", "past_elig"), ("prod_x_years_past_elig", "prod_x_age"), ("p_star", "p_star")):
        gap = float(np.max(np.abs(r2[a_].values - pm[b_].values)))
        assert gap < TOL, (a_, gap)
    assert int(R["sample_star"].sum()) == int(fitrows["prospect"].sum())
    log(f"  check 1: the CSV's production sample is the model's {len(pm):,} skater prospect-seasons, row for row, "
        f"same outcome and inputs; its star sample is the model's {int(R['sample_star'].sum()):,} (PASS)")

    # 2. the pick curve (Valuing Draft Picks; Valuing Prospects' D+1 star value)
    pf = P[P["excluded_deceased"] == 0]
    m = ols(pf["career_npv_m"].values, pf[["p_star"]].values)
    sc = pd.read_csv(OUTPUT_DIR / "pick_curve_scales.csv").set_index("scale_kind").loc["main"]
    assert abs(m.params[0] - sc["scale_M"]) < TOL and abs(m.bse[0] - sc["se_M"]) < TOL
    log(f"  check 2: the pick curve from draft_players.csv: star value {m.params[0]:.4f} (robust s.e. {m.bse[0]:.4f}), "
        f"{int(m.nobs):,} players, R-squared {m.rsquared:.3f} = pick_curve_scales.csv (PASS)")

    # 3. the star values by season (Valuing Prospects Table 2)
    s1 = R[R["sample_star"] == 1]
    st, _ = stacked(s1, {g: ["p_star"] for g in range(1, 6)})
    svm = sv[sv["left_out"] == "none"].set_index("k_group")
    log("\n  check 3: star value by season (Valuing Prospects Table 2), from prospect_seasons.csv:")
    for k_, g in GROUP_NUM.items():
        b, se = st[(g, "p_star")]
        assert abs(b - svm.loc[k_, "star_value_M"]) < TOL and abs(se - svm.loc[k_, "se_M"]) < TOL, k_
        log(f"    {GROUP_LABEL[g]:<14} {b:7.3f} (clustered s.e. {se:.3f}); {int((s1['season_group'] == g).sum()):,} "
            f"prospect-seasons")
    log("    = prospect_star_values.csv (PASS)")

    # 4. the adopted model (Valuing Prospects Table 9)
    s2 = R[R["sample_production"] == 1]
    cols_code = {GROUP_NUM[g]: [{"p_star": "p_star", "nhle82": "nhle82", "nhle82_sq": "nhle82_sq",
                                 "prod_x_age": "prod_x_years_past_elig"}[c] for c in PV.cols_for(g, "main")]
                 for g in GROUP_NUM}
    st_code, m_code = stacked(s2, cols_code)
    for g_, gnum in GROUP_NUM.items():
        cols_m, b_m, se_m = fits[("main", g_, "none")]
        for i, c in enumerate(cols_code[gnum]):
            assert abs(st_code[(gnum, c)][0] - b_m[i]) < TOL and abs(st_code[(gnum, c)][1] - se_m[i]) < TOL, (g_, c)
    cols_doc = {g: [c.replace("prod_x_years_past_elig", "prod_x_age_m18") for c in cs] for g, cs in cols_code.items()}
    st_doc, m_doc = stacked(s2, cols_doc)
    assert float(np.max(np.abs(m_doc.fittedvalues - m_code.fittedvalues))) < TOL       # the same values
    log("\n  check 4: the adopted model (Valuing Prospects Table 9), from prospect_seasons.csv, age less 18:")
    names = {"p_star": "star probability", "nhle82": "production", "nhle82_sq": "production squared",
             "prod_x_age_m18": "production x (age - 18)"}
    for gnum, cs in cols_doc.items():
        kk = int(s2.loc[s2["season_group"] == gnum, "k"].iloc[0])
        if "prod_x_age_m18" in cs:
            assert s2.loc[s2["season_group"] == gnum, "k"].nunique() == 1
            e_doc, e_code = st_doc[(gnum, "prod_x_age_m18")][0], st_code[(gnum, "prod_x_years_past_elig")][0]
            assert abs(e_doc - e_code) < TOL                                            # the same age coefficient
            assert abs(st_doc[(gnum, "nhle82")][0] - (st_code[(gnum, "nhle82")][0] - kk * e_code)) < TOL
        x = s2[s2["season_group"] == gnum]
        own = ols(x["remaining_npv_m"].values, x[cs].values)                        # the season's own R-squared
        log(f"    {GROUP_LABEL[gnum]:<14} " + "; ".join(f"{names[c]} {st_doc[(gnum, c)][0]:.4f} ({st_doc[(gnum, c)][1]:.4f})"
                                                     for c in cs)
            + f"; {len(x):,} rows, R-squared {own.rsquared:.3f}")
    log("    = prospect_production_fits.csv, the same fitted values and age coefficient (PASS)")

    # 5. production_seasons.csv rebuilds the model's NHLe rate for every player-season
    # by player_id, as Stata would collapse it: a player drafted twice (five of them) has his one Elite Prospects record
    # under both draft rows, so adding up by Elite Prospects id would count his games twice
    q = Q[Q["nhle_factor"].notna()]
    g = q.groupby(["player_id", "ep_player_id", "season_start"]).agg(gp=("gp", "sum"), pts=("nhle_points", "sum"))
    g = g[g["gp"] >= PV.PROD_MIN_GP].reset_index()
    rate = {(p_, e_, y_): v_ for p_, e_, y_, v_ in zip(g["player_id"], g["ep_player_id"], g["season_start"],
                                                       g["pts"] / g["gp"] * 82)}
    pid_of = Q.groupby("ep_player_id")["player_id"].unique().to_dict()
    mine = {(p_, e_, y_): v_ for (e_, y_), v_ in rates.items() if e_ in pid_of for p_ in pid_of[e_]}
    assert set(rate) == set(mine) and max(abs(rate[k_] - mine[k_]) for k_ in rate) < TOL
    log(f"\n  check 5: production_seasons.csv gives the model's NHLe rate for all {len(rate):,} player-seasons (PASS)")

    (OUT / "stata_export_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
