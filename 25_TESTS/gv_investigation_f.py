"""gv_investigation_f.py -- investigation F: the Game Value circularity checks on the model as built.

WHY (00_STATE/MODEL_DIRECTIVES.md, investigation F; plan of record step 7). The checks in
`Circularity and Game Value.docx` compare the model's production measure with Game Value, a metric
built from NHL play-by-play with no Bacon WAR input, so agreement between them is evidence the
measure tracks real play rather than one vendor's model. They were run on the 60/40 two-season
trailing total (gv_4b_circularity_check.py, gv_4b_robustness_check.py). The model now reads a
50/30/20 trailing total and prices a forecast; none of the checks has been run on either. MEASUREMENT
ONLY: nothing changes.

WHAT IT DOES
  0. GUARD. Rebuilds the recorded checks from the same inputs the old scripts read (the skater value
     spine's 60/40 trailing_war; GV-adj from `gv_adjusted`; the raw variants from
     `player_game_value_repl`, regular season) and requires the recorded figures back: 0.576 on 6,027
     player-seasons; forwards 0.648, defence 0.302; one season further 0.538; raw against
     replacement 0.609, zero-sum 0.564 (Pearson r, equal at the three decimals recorded). Stops if any
     differs.
  1. On those same player-seasons, the measures the model now uses, each read off the valuation page
     of that season (July 1, seasons before it only):
       trailing 50/30/20   the forecast's trailing WAR total (skater_forecast._anchors tw_WAR)
       starting level      the forecast's rate per 82 in the valuation season (rate_82, h = 0)
       WAR if he plays     rate_82 x games share, h = 0 (what the price line prices)
       expected WAR        chance of playing x WAR if he plays, h = 0
       expected WAR, no contract status   the same with the chance of playing refitted on the page
                           without the contract columns (participation_model with no contracts)
     All measures are compared on ONE common sample (rows where every measure exists), with the
     60/40 reference beside them on that sample, so the comparison is like for like.
  2. Outcomes: GV-adj, raw GV against replacement, raw GV zero-sum, all in wins (5.903 goals a win,
     the locked rate); the starting level, a rate, is also compared with GV-adj per 82 games.
  3. Breakdowns: overall, by season, forwards and defence, and one season further (the trailing
     measures as they stand; the forecast measures at h = 1, the forecast for that season).
  4. The contract-status channel: on players who played (the old checks' sample) and on all
     contracted player-seasons with a season the player did not play counted as zero Game Value,
     where the chance of playing matters. Reports how much of expected WAR's agreement survives
     without contract status.

HOW TO RUN (repo root, laptop; needs GAMELOG_DB, the contract export, WAR_with_age.csv at 99%+ and
the skater value spine from the dashboard chain; about ten minutes):
    python 25_TESTS/gv_investigation_f.py
Writes 30_OUTPUT/gv_investigation_f_log.txt.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd

import forecast_config as C

SCRIPT_VERSION = "1.1"
RECORDED = {"n": 6027, "primary": 0.576, "F": 0.648, "D": 0.302, "next": 0.538,
            "repl": 0.609, "zero_sum": 0.564}
# The recorded figures are rounded to three decimals, so a figure reproduces when today's value rounds
# to the same three decimals (v1.1). v1.0 allowed a gap of 0.0005, which sits on the rounding edge: on
# the laptop the forwards' 0.648 failed at a value printed as 0.6485 (2026-10-05).
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def r_of(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    return float(np.corrcoef(x, y)[0, 1])


def rho_of(x, y):
    from scipy import stats
    return float(stats.spearmanr(x, y)[0])


# =========================================================================== 0. the guard
def load_inputs():
    """The old scripts' own loaders, so the reference is built exactly as recorded."""
    import gv_4b_circularity_check as P
    import gv_4b_robustness_check as R
    spine = P.load_bacon_side()
    gv_adj = P.load_gv_side()
    gv_raw = R.load_gv_raw_side()
    gv = gv_adj.merge(gv_raw, on=["nhl_id", "season_start"], how="outer")
    return spine, gv


def guard(spine, gv):
    same = spine.merge(gv.dropna(subset=["gv_adj_wins"]), on=["nhl_id", "season_start"], how="inner")
    pos = same["position"].str.startswith("D").map({True: "D", False: "F"})
    nxt = spine.merge(gv.dropna(subset=["gv_adj_wins"]).assign(season_start=lambda d: d["season_start"] - 1)
                      [["nhl_id", "season_start", "gv_adj_wins"]].rename(columns={"gv_adj_wins": "next"}),
                      on=["nhl_id", "season_start"], how="inner")
    raw = spine.merge(gv.dropna(subset=["gv_repl_wins"]), on=["nhl_id", "season_start"], how="inner")
    got = {"n": len(same), "primary": r_of(same["trailing_war"], same["gv_adj_wins"]),
           "F": r_of(same.loc[pos == "F", "trailing_war"], same.loc[pos == "F", "gv_adj_wins"]),
           "D": r_of(same.loc[pos == "D", "trailing_war"], same.loc[pos == "D", "gv_adj_wins"]),
           "next": r_of(nxt["trailing_war"], nxt["next"]),
           "repl": r_of(raw["trailing_war"], raw["gv_repl_wins"]),
           "zero_sum": r_of(raw["trailing_war"], raw["gv_raw_wins"])}
    ok = True
    for k, want in RECORDED.items():
        g = got[k]
        good = (g == want) if k == "n" else round(g, 3) == round(want, 3)
        ok &= good
        log(f"  {k:9s} recorded {want:>7}  now {g:>10.6f}  {'PASS' if good else 'FAIL'}" if k != "n"
            else f"  {k:9s} recorded {want:>7,}  now {g:>10,}  {'PASS' if good else 'FAIL'}")
    assert ok, "the recorded 60/40 checks do not reproduce; nothing below is read"


# =========================================================================== 1. the measures
def attach_measures(spine, gv):
    """One row per spine player-season in Game Value's window, with every measure from its page."""
    import skater_forecast as SF
    import skater_forward_projection as SFP
    from participation_model import ParticipationModel
    fc = SF.ContractForecaster()
    # production's player key: cleaned name + "|" + F/D, with the one known alias (as SkaterProjector)
    sv = pd.read_csv(Path(os.environ["OUTPUT_DIR"]) / "skater_value_spine.csv",
                     usecols=["player_id", "season_start", "full_name", "posgrp"]).drop_duplicates(["player_id", "season_start"])
    sv["nn"] = sv["full_name"].map(SFP.norm_name)
    sv["nk"] = [(SFP.NAME_ALIASES.get((n, g)) or n) + "|" + str(g) for n, g in zip(sv["nn"], sv["posgrp"])]
    d = spine.merge(sv[["player_id", "season_start", "nk"]], on=["player_id", "season_start"], how="left")
    d["career_key"] = d["nk"].map(fc.career_of)
    pages = sorted(int(t) for t in gv["season_start"].dropna().unique() if t in set(d["season_start"]))
    d = d[d["season_start"].isin(pages)].copy()
    # each measure is written onto ITS OWN row by index (v1.0's first draft appended page by page and
    # glued the lists onto rows in another order; the cloud smoke test caught the misalignment)
    d = d.reset_index(drop=True)
    for k in ("tw502", "start82", "wip0", "pp0", "pp0_nc", "wip1", "pp1", "pp1_nc"):
        d[k] = np.nan
    for t0 in pages:
        m, iset, p, a = fc.page(t0)
        # the no-contract twin of the chance of playing, fitted on the same page and rows
        nc = ParticipationModel(None).fit(iset.seasons, t0, anchors_fn=lambda q: SF._anchors(q, SF.XNPV1.N_SEASONS),
                                          horizons=m.fitted_horizons_)
        rows = a.reset_index()
        nc0 = nc.predict(rows, 0); nc0 = nc0[~nc0.index.duplicated()]
        nc1 = nc.predict(rows, 1); nc1 = nc1[~nc1.index.duplicated()]
        g = d[d["season_start"] == t0]
        n_have = 0
        for i, ck in g["career_key"].items():
            if not (isinstance(ck, str) and ck in a.index):
                continue
            n_have += 1
            f = p.loc[ck]
            d.loc[i, ["tw502", "start82", "wip0", "pp0", "pp0_nc", "wip1", "pp1", "pp1_nc"]] = [
                float(a.loc[ck, "tw_WAR"]), float(f.loc[0, "rate_82"]), float(f.loc[0, "war_if_plays"]),
                float(f.loc[0, "p_play"]), float(nc0.get(ck, np.nan)), float(f.loc[1, "war_if_plays"]),
                float(f.loc[1, "p_play"]), float(nc1.get(ck, np.nan))]
        log(f"  page {t0}: {len(g):,} spine player-seasons, {n_have:,} with an xNPV 1 anchor")
    # alignment guard: each filled row's trailing 50/30/20 must be ITS player's anchor on ITS page
    chk = d.dropna(subset=["tw502"]).sample(min(200, int(d["tw502"].notna().sum())), random_state=0)
    for i, r in chk.iterrows():
        a = fc.page(int(r["season_start"]))[3]
        assert abs(float(a.loc[r["career_key"], "tw_WAR"]) - r["tw502"]) < 1e-12, f"row {i} is misaligned"
    log(f"  alignment guard: {len(chk)} sampled rows carry their own player's page values")
    d["exp0"] = d["pp0"] * d["wip0"]
    d["exp0_nc"] = d["pp0_nc"] * d["wip0"]
    d["exp1"] = d["pp1"] * d["wip1"]
    d["exp1_nc"] = d["pp1_nc"] * d["wip1"]
    # games in the season (for GV per 82 and for "did not play")
    tbl = fc.table
    gp = tbl.groupby(["career_key", "syr"])["GP"].sum()
    d["gp_t"] = [float(gp.get((ck, t), 0.0)) if isinstance(ck, str) else np.nan
                 for ck, t in zip(d["career_key"], d["season_start"])]
    d["gp_t1"] = [float(gp.get((ck, t + 1), 0.0)) if isinstance(ck, str) else np.nan
                  for ck, t in zip(d["career_key"], d["season_start"])]
    return d


MEASURES = [("trailing_war", "trailing 60/40 (reference)"), ("tw502", "trailing 50/30/20"),
            ("start82", "starting level (per 82)"), ("wip0", "WAR if he plays"),
            ("exp0", "expected WAR"), ("exp0_nc", "expected WAR, no contract status")]
NEXT = [("trailing_war", "trailing 60/40 (reference)"), ("tw502", "trailing 50/30/20"),
        ("wip1", "WAR if he plays, next season"), ("exp1", "expected WAR, next season"),
        ("exp1_nc", "expected WAR, next season, no contract status")]
OUTCOMES = [("gv_adj_wins", "GV-adj"), ("gv_repl_wins", "raw GV vs replacement"), ("gv_raw_wins", "raw GV zero-sum")]


def table(d, measures, outcomes, title):
    log(f"\n{title}")
    log(f"  {'measure':48s}" + "".join(f"{lab:>24s}" for _, lab in outcomes))
    for col, lab in measures:
        log(f"  {lab:48s}" + "".join(f"{r_of(d[col], d[o]):>16.3f} ({rho_of(d[col], d[o]):.3f})" for o, _ in outcomes))
    log("  (Pearson r, Spearman rho in brackets)")


def run(d, gv):
    need = [c for c, _ in MEASURES]
    # ---- played-only sample (the old checks' sample): inner join on GV, every measure present ----
    same = d.merge(gv, on=["nhl_id", "season_start"], how="inner").dropna(subset=need + [o for o, _ in OUTCOMES])
    log(f"\nCOMMON SAMPLE, same season: {len(same):,} player-seasons ({same['player_id'].nunique():,} players) "
        f"of the guard's {RECORDED['n']:,} (rows with every measure and every Game Value variant)")
    table(same, MEASURES, OUTCOMES, "SAME SEASON, all positions")
    pos = same["position"].str.startswith("D").map({True: "D", False: "F"})
    for p_, lab in (("F", "forwards"), ("D", "defence")):
        table(same[pos == p_], MEASURES, OUTCOMES, f"SAME SEASON, {lab} (n {int((pos == p_).sum()):,})")
    same["gv_adj_82"] = same["gv_adj_wins"] / same["gp_t"].where(same["gp_t"] > 0) * 82
    s82 = same.dropna(subset=["gv_adj_82"])
    log(f"\nRATE AGAINST RATE: starting level (per 82) against GV-adj per 82 games, n {len(s82):,} "
        f"(seasons of 10+ games: n {int((s82['gp_t'] >= 10).sum()):,})")
    for lab, g in (("all", s82), ("10+ games", s82[s82["gp_t"] >= 10])):
        log(f"  {lab:10s} r {r_of(g['start82'], g['gv_adj_82']):.3f}  (trailing 50/30/20 against the same: "
            f"{r_of(g['tw502'], g['gv_adj_82']):.3f})")
    log("\nBY SEASON, against GV-adj (Pearson r):")
    log(f"  {'season':>7}{'n':>7}" + "".join(f"{lab[:22]:>24s}" for _, lab in MEASURES))
    for t, g in same.groupby("season_start"):
        log(f"  {int(t):>7}{len(g):>7,}" + "".join(f"{r_of(g[c], g['gv_adj_wins']):>24.3f}" for c, _ in MEASURES))
    # ---- one season further ----
    gn = gv.assign(season_start=gv["season_start"] - 1).rename(columns={o: o + "_n" for o, _ in OUTCOMES})
    nxt = d.merge(gn, on=["nhl_id", "season_start"], how="inner").dropna(
        subset=[c for c, _ in NEXT] + [o + "_n" for o, _ in OUTCOMES])
    log(f"\nONE SEASON FURTHER: {len(nxt):,} player-seasons with Game Value the next season")
    table(nxt, NEXT, [(o + "_n", lab) for o, lab in OUTCOMES], "NEXT SEASON, all positions")
    # ---- the contract-status channel, with seasons not played counted as zero ----
    allr = d.dropna(subset=need).copy()
    allr = allr.merge(gv, on=["nhl_id", "season_start"], how="left")
    absent = allr["gp_t"] <= 0
    allr.loc[absent, "gv_adj_wins"] = 0.0
    allr = allr.dropna(subset=["gv_adj_wins"])     # played but no GV row: a coverage gap, not a zero
    log(f"\nCONTRACT-STATUS CHANNEL. Contracted player-seasons with every measure: {len(allr):,}, of which "
        f"{int(absent.loc[allr.index].sum()):,} not played (GV-adj counted as 0); played with no GV row dropped")
    for lab, g in (("played only", same), ("not-played counted as zero", allr)):
        rw = r_of(g["wip0"], g["gv_adj_wins"]); re_ = r_of(g["exp0"], g["gv_adj_wins"])
        rn = r_of(g["exp0_nc"], g["gv_adj_wins"])
        log(f"  {lab:28s} n {len(g):6,}  WAR if he plays {rw:.3f}  expected WAR {re_:.3f}  "
            f"no contract status {rn:.3f}  (contract status adds {re_ - rn:+.3f}; the chance of playing adds {re_ - rw:+.3f})")


def main():
    log(f"gv_investigation_f.py v{SCRIPT_VERSION}")
    log("\n0. GUARD: the recorded 60/40 checks, rebuilt from the old scripts' own loaders")
    spine, gv = load_inputs()
    guard(spine, gv)
    log("\n1. MEASURES from each valuation page")
    d = attach_measures(spine, gv)
    run(d, gv)
    p = Path(os.environ["OUTPUT_DIR"]) / "gv_investigation_f_log.txt"
    p.write_text("\n".join(LOG) + "\n", encoding="utf-8")
    log(f"\nwritten: {p}")


if __name__ == "__main__":
    main()
