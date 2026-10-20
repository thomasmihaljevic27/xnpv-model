"""
backtest.py -- the back-test: what each traded asset delivered, added up club by club, against what the models said
at the trade.

THE PROTOCOL: 40_DOCS/Backtest_Protocol.md, committed before this script first ran. Every rule below is a rule there;
the label says whose it is. Thomas's choices of 2026-10-20: "Played + rest re-valued" (the outcome), "The model's rule"
(the cost of control and draftee seasons), "Dollar gap per club" (the statistic), "Leave the extension out" (built
upstream: traded_player_values v1.4, page_2017_values v1.6).

AN ASSET'S OUTCOME ($M at the 2025-26 cap) covers the span its forecast covered, in two parts:
  REALISED  seasons through 2025-26, priced on what happened. Each season in cap shares of that season's actual cap:
            value  = max(line(WAR delivered, scaled to 82 games in short seasons), league minimum), under 10 games
                     scaled by games/82; zero with no NHL game (open decision 3; the pick curve's rules 2-5).
                     Skaters: alpha + beta(position) x WAR + gamma_term x term, the term the forecast used for a
                     contract season, one year for a control or draftee season. Goalies: the goalie line.
            cost   = a contract season: the cap hit the forecast charged (PuckPedia's), net of any retention for the
                     acquirer, paid whether or not he played; a control or draftee season: the pick curve's rule
                     (entry-level maximum, qualifying offer, arbitration price once eligible), only when he played.
            the season of an in-season trade: the share of days left (as the forecast) for the intercept, the floor
                     and the cap hit; the wins after the trade = season WAR x his games after the trade date / his
                     games that season (nhl_gamelogs.sqlite).
  REVALUED  seasons from 2026-27 on, by the same models at the 2026-27 page (everything through 2025-26 known): a
            prospect by the prospect model at season 2026 (its fitted coefficients, prospect_production_fits.csv and
            prospect_star_values.csv); an NHL player by xNPV 1's forecast at page 2026 (value x chance of playing,
            minus the cap hit or the rule's cost), goalies by the goalie forecast and exit hazard.
  The asset is followed whoever holds it later. Club sides: trade_sides.club_sides, the forecast's own rule.

WHERE EACH ASSET'S SPAN AND FORECAST COME FROM (the files trade_asset_values joined; each re-derived here and checked)
  player model, 2018-19 on   NPVEngine.npv re-run exactly as traded_player_values (GUARD: npv_total to $1)
  rights                     rights_values.csv: control seasons from the page to the UFA year
  the 2017 page              the CapWages chain as page_2017_values builds it (GUARD: chain end, extensions)
  buried contracts           outcome = forecast (a deterministic cost; stated)
  prospects                  pick-curve seasons from the valuation season (pick_curve_seasons.csv, 2007-2017 drafts;
                             pick_curve_later_seasons.csv, 2018-2025, pick_curve.py v1.10); lapsed rights zero
  picks                      the player drafted with it (traded_pick_values actual_slot), from his draft
  undrafted prospects        priced by this script's copy of the pick curve's cost chain (GUARD: the copy reproduces
                             every 2007-2017 draftee's seasons in pick_curve_seasons.csv)

INPUTS: OUTPUT_DIR/trade_asset_values.csv and the files above; SOURCE_DIR/WAR.csv, Goalies_WAR.csv, games.csv,
nhl_gamelogs.sqlite, trades.db, draft_slot_baseline.csv; the contract chain's spines through NPVEngine.
OUTPUTS: OUTPUT_DIR/backtest_assets.csv (one row per asset: forecast, realised, revalued, outcome),
backtest_sides.csv (one row per club per trade, forecast and outcome), backtest_results.csv (every test, group and
sensitivity), backtest_log.txt.
Run from the repo root, after trade_refresh.py and trade_sides.py:  python 20_CODE/backtest.py
"""

import os
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "backtest.py v1.0 (2026-10-20)"
load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_npv as CN                                     # noqa: E402  the engine, goalie line and hazard
import skater_forward_projection as SFP                       # noqa: E402  price line, caps, minimums
from skater_forward_projection import cap_path, league_min_path, page_date, chain_rows, expected_floored_value  # noqa: E402
import rfa_terminal_value as RTV                              # noqa: E402  qualifying offer, salary, eligibility
import trade_page as TP                                       # noqa: E402
import contract_source as CS                                  # noqa: E402
import contracts_2017 as K                                    # noqa: E402
import prospect_values as PV                                  # noqa: E402  prospect features, windows
import trade_sides as TSD                                      # noqa: E402  club sides, one rule for both
from skater_forecast import war_if_plays_sd                   # noqa: E402

SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])
LAST, NOW = 2025, 2026                       # the last season played; the page the rest is revalued on
CAP_NOW = SFP.CAP_CEILING[2025]
CAP = {y: SFP.CAP_CEILING[y] for y in range(2015, 2026)}
LMIN = {y: league_min_path(y) for y in range(2015, 2026)}
SHORT = {2012: 82 / 48, 2019: 82 / 70, 2020: 82 / 56}       # WAR to 82 games (pick_curve)
CAMEO_GP = 10                                               # under 10 games: value and cost x games/82 (pick_curve)
ARB_GP = {2012: 6, 2019: 9, 2020: 7}                        # a season of professional experience (pick_curve)
ARB_NEED = lambda age: 4 if age <= 20 else 3 if age == 21 else 2 if age <= 23 else 1   # CBA 12.1(a)
ELC_MAX = {**{y: 875_000 for y in (2007, 2008)}, **{y: 900_000 for y in (2009, 2010)},
           **{y: 925_000 for y in range(2011, 2022)}, 2022: 950_000, 2023: 950_000, 2024: 975_000, 2025: 975_000,
           2026: 1_000_000}                                  # by draft year (pick_curve v1.10)
ALPHA, BETA_F, BETA_D, GAMMA, LINE = SFP.price_constants()
ALPHA_G, BETA_G = CN.ALPHA_G, CN.BETA_G
N_BOOT, SEED = 2000, 20261020
LAPSED = ("lapsed", "drafted twice (earlier pick)")
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


# ---- prices ----------------------------------------------------------------------------------------------------------
def line(w, gk, pos, term):
    """The contract line (cap share): goalies' line, or skaters' with the defence slope and the term premium."""
    if gk:
        return ALPHA_G + BETA_G * w
    return ALPHA + (BETA_D if pos == "D" else BETA_F) * w + GAMMA * term


def played_value(w82, gp, y, gk, pos, term):
    """A full season played (cap share of season y's cap): floored at the minimum, cameo-scaled."""
    if gp <= 0:
        return 0.0
    v = max(line(w82, gk, pos, term), LMIN[y] / CAP[y])
    return v * (gp / 82 if gp < CAMEO_GP else 1.0)


def part_value(w82_season, gp_season, gp_post, f, y, gk, pos, term):
    """The part of the trade season after the trade: the intercept, term and floor for the share of days left f, the
    wins he delivered after the trade (season WAR x his games after / his games that season)."""
    if gp_post <= 0 or gp_season <= 0:
        return 0.0
    w_post = w82_season * gp_post / gp_season
    return f * max(line(w_post / f, gk, pos, term), LMIN[y] / CAP[y])


# ---- the seasons each player played ------------------------------------------------------------------------------------
TABLES = {False: PV.season_table(SOURCE_DIR / "WAR.csv", "Player"),
          True: PV.season_table(SOURCE_DIR / "Goalies_WAR.csv", "Goalie")}


def seasons_for(name, gk):
    """GP and WAR by start year for a WAR spelling (PV.norm), as pick_curve.season_table."""
    t, n = TABLES[gk], PV.norm(name)
    return t.loc[n] if n in t.index.get_level_values(0) else pd.DataFrame({"GP": [], "WAR": []})


def gp_war(s, y):
    if y not in s.index:
        return 0.0, 0.0
    return float(s.loc[y, "GP"]), float(s.loc[y, "WAR"]) * SHORT.get(y, 1.0)


def trailing_total(s, page):
    """The forecast's 50/30/20 trailing WAR total before the page (10+ game seasons, rescaled): the harness's tiers."""
    got = [(w, float(s.loc[z, "WAR"])) for w, z in zip((0.5, 0.3, 0.2), (page - 1, page - 2, page - 3))
           if z in s.index and s.loc[z, "GP"] >= 10]
    return sum(w * x for w, x in got) / sum(w for w, _ in got) if got else np.nan


def game_log_counts():
    """{(nhl_id, season start): sorted regular-season game dates}, skaters and goalies."""
    con = sqlite3.connect(SOURCE_DIR / "nhl_gamelogs.sqlite")
    out = {}
    for tbl in ("skater_games", "goalie_games"):
        q = pd.read_sql(f"select s.player_id, g.season, g.game_date from {tbl} s join games g using(game_id) "
                        f"where g.game_type = 2", con)
        q["syr"] = q["season"].astype(str).str[:4].astype(int)
        for (p, y), g in q.groupby(["player_id", "syr"]):
            out.setdefault((int(p), int(y)), set()).update(g["game_date"])
    return {k: sorted(v) for k, v in out.items()}


# ---- the cost chain of a control or draftee season (the pick curve's rule) --------------------------------------------
class Chain:
    """Where the rule's cost stands: the last salary paid (the next qualifying offer is computed on it)."""

    def __init__(self, salary, cap_hit, s20):
        self.sal, self.cap, self.s20 = salary, cap_hit, s20

    def cost(self, y, tw, gk, pos, cap_y, lmin_y):
        """Season y's cost: the qualifying offer, or once eligible (tw given) the higher of it and the line's price
        of tw (one year of term), floored at the minimum. Returns (cost, qualifying offer)."""
        qo = RTV.qualifying_offer(self.sal, self.cap, y, self.s20)
        if tw is None:
            return qo, qo
        return max(qo, max(line(tw, gk, pos, 1) * cap_y, lmin_y)), qo

    def paid(self, amount):
        self.sal = self.cap = amount


# ---- the forecasts at the 2026-27 page ---------------------------------------------------------------------------------
def career_for(eng, war_names, gp_by_season):
    """pick_curve.career_of: the forecast's career key among his WAR spellings, the one whose 10+ game seasons cover
    most of his; and the forecast's player key (pkey) for it. (None, None) when none is in the forecast's table."""
    import player_season_table as PST
    fc = eng.sp.forecaster
    if not hasattr(fc, "_pkey_of"):
        fc._pkey_of = fc.table.drop_duplicates("career_key").set_index("career_key")["pkey"].to_dict()
        fc._careers = set(fc.table["career_key"])
    if war_names is None or (isinstance(war_names, float) and pd.isna(war_names)):
        return None, None
    mine = {z for z, g in gp_by_season.items() if g >= 10}
    best, score = None, -1
    for nm in str(war_names).split("|"):
        ck = PST.career_key(nm)
        if ck not in fc._careers:
            continue
        t = fc.table[(fc.table["career_key"] == ck) & (fc.table["GP"] >= 10)]
        sc = len(mine & set(t["syr"]))
        if sc > score:
            best, score = ck, sc
    return best, (fc._pkey_of.get(best) if best is not None else None)


class Now:
    """xNPV 1 and the goalie forecast at page 2026, for the seasons left after 2025-26."""

    def __init__(self, eng):
        self.eng, self.fc = eng, eng.sp.forecaster
        self._cache = {}

    def skater(self, nk, horizon):
        key = (nk, horizon)
        if key not in self._cache:
            self._cache[key] = self.fc.forecast(nk, NOW, horizon, page_date(NOW))
        return self._cache[key]

    def goalie(self, nname, bd, horizon):
        pw, src = self.eng.g_proj.shrunk_projection(nname, NOW)
        if pd.isna(pw):
            return None
        age0 = None if pd.isna(bd) else int(NOW - bd.year - ((9, 15) < (bd.month, bd.day)))
        S = CN.STALE_GATE if src == "stale_anchor" else 1.0
        out = []
        for k in range(horizon + 1):
            if k > 0:
                S *= 1.0 - self.eng._hazard(self.eng.h_g, pw, None if age0 is None else age0 + k - 1)
            out.append({"h": k, "war_if_plays": pw, "p_play": S})
        return pd.DataFrame(out)


def main():
    sys.stdout.reconfigure(errors="replace")
    log(SCRIPT_VERSION)
    log(f"  skater line: {LINE} alpha {ALPHA:.10f} beta F {BETA_F:.10f} D {BETA_D:.10f} term {GAMMA:.10f}; "
        f"goalie line: {ALPHA_G:.6f} + {BETA_G:.6f} x WAR")
    for f in ("trade_asset_values.csv", "trade_sides.csv", "traded_player_values.csv", "rights_values.csv",
              "page_2017_values.csv", "prospect_values.csv", "traded_pick_values.csv", "pick_curve_seasons.csv",
              "pick_curve_later_seasons.csv", "pick_curve_later_players.csv", "prospect_production_fits.csv"):
        p = OUTPUT_DIR / f
        log(f"  input {f}: modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M} UTC")
    tav = pd.read_csv(OUTPUT_DIR / "trade_asset_values.csv")
    eng = CN.NPVEngine()
    sp, now = eng.sp, None
    now = Now(eng)
    games = game_log_counts()
    log(f"  game logs: {len(games):,} player-seasons")
    rows = {}                                   # asset_id -> outcome record (player and pick assets)
    retained_out = {}                           # asset_id -> the retaining club's realised + revalued cost ($M)
    names_note = []

    def gp_after(nhl_id, y, date):
        d = games.get((int(nhl_id), y)) if pd.notna(nhl_id) else None
        if not d:
            return 0, 0
        return sum(1 for x in d if x > str(date)[:10]), len(d)

    # ======================================================================================================
    # 1. PLAYERS ON THE PLAYER MODEL, 2018-19 ON: the engine's own span, re-run as traded_player_values
    # ======================================================================================================
    tp = pd.read_csv(OUTPUT_DIR / "traded_player_values.csv")
    RET = TP.retention()["retention_pct"].to_dict()

    def engine_detail(pid, y, date, share, rpct):
        """traded_player_values' call: as_of, the masked contracts (signed on or after the trade date), the share and
        the retention. Returns (detail, summary, masked) with the masks still set; the caller restores them."""
        as_of = date if page_date(y) <= date < page_date(y + 1) else page_date(y)
        spine = sp.spine if (sp.spine["player_id"] == pid).any() else eng.gp_spine
        masked = {}
        for c in spine.loc[spine["player_id"] == pid, "contract_id"].unique():
            sg = sp.signed.get(int(c))
            if pd.notna(sg) and date <= sg <= as_of:
                masked[int(c)] = sg
                sp.signed[int(c)] = pd.NaT
        d, s = eng.npv(pid, y, as_of, first_season_share=share, retained_pct=rpct)
        return d, s, masked, as_of

    def control_part(*, gk, pos, name_seasons, nhl_id, nk, ck, nname, bd, seasons, chain, flag, need, y0, share,
                     trade_date, first_is_trade_season):
        """Control seasons (rule cost): realised through 2025-26 (only when he played), revalued after.
        Returns (realised $M, revalued $M)."""
        real = rev = 0.0
        obs = {z: g for z, g in name_seasons["GP"].items()} if len(name_seasons) else {}
        later = [z for z in seasons if z >= NOW]
        fc = None
        if later:
            H = max(later) - NOW
            fc = now.goalie(nname, bd, H) if gk else (now.skater(nk, H) if nk is not None else None)
        for j, z in enumerate(seasons, start=1):
            if z <= LAST:
                gp, w = gp_war(name_seasons, z)
                if flag is None:
                    pro = sum(1 for q, g in obs.items() if q < z and g >= ARB_GP.get(q, 10))
                    elig = need is not None and pro >= need
                else:
                    elig = flag == 1 or j >= 2
                tw = None
                if elig and gp > 0:
                    if gk:
                        pw_z, _ = eng.g_proj.shrunk_projection(nname, z)
                        tw = None if pd.isna(pw_z) else eng.g_proj.arbitration_war(nname, z, z, pw_z)
                    elif ck is not None:
                        r = now.fc.arbitration_war(ck, z, z)
                        tw = None if r is None else r[0]
                cost, qo = chain.cost(z, tw, gk, pos, CAP[z], LMIN[z])
                if gp > 0:
                    f = share if (first_is_trade_season and j == 1) else 1.0
                    if f < 1.0:
                        gpp, gps = gp_after(nhl_id, z, trade_date)
                        v = part_value(w, gp, gpp, f, z, gk, pos, 1)
                        c = cost / CAP[z] * f
                    else:
                        sc = gp / 82 if gp < CAMEO_GP else 1.0
                        v, c = played_value(w, gp, z, gk, pos, 1), cost / CAP[z] * sc
                    real += (v - c) * CAP_NOW / 1e6
                    chain.paid(cost)
                else:
                    chain.paid(qo)                         # no NHL game: the qualifying offer carries the chain
            else:
                h = z - NOW
                if fc is None or h >= len(fc):
                    continue                               # no forecast for him at 2026-27: nothing left to value
                w, p = float(fc.iloc[h]["war_if_plays"]), float(fc.iloc[h]["p_play"])
                elig = (flag == 1 or j >= 2) if flag is not None else (
                    need is not None and RTV.arb_eligible(z, NOW, need, obs))
                tw = None
                if elig:
                    if gk:
                        tw = eng.g_proj.arbitration_war(nname, NOW, z, w)
                    elif ck is not None:
                        r = now.fc.arbitration_war(ck, NOW, z)
                        tw = None if r is None else r[0]
                ceil = cap_path(NOW, h)
                cost, qo = chain.cost(z, tw, gk, pos, ceil, league_min_path(z))
                val = max(line(w, gk, pos, 1) * ceil, league_min_path(z))
                rev += p * (val - cost) / ceil * CAP_NOW / 1e6
                chain.paid(cost)
        return real, rev

    n_eng = 0
    for _, r in tp.iterrows():
        st = str(r["status"])
        if st != "ok":
            continue
        pid, y, date = int(r["player_id"]), int(r["valuation_page"]), pd.Timestamp(r["trade_date"])
        share = float(r["season_share"]) if pd.notna(r["season_share"]) else 1.0
        rpct = float(r["retained_pct"]) if pd.notna(r["retained_pct"]) else 0.0
        d, s, masked, as_of = engine_detail(pid, y, date, share, rpct)
        try:
            assert abs(s["npv_total"] - r["npv_total"]) < 1.0, (r["player_name"], s["npv_total"], r["npv_total"])   # GUARD
            gk = s["position"] == "goalie"
            spine = eng.gp_spine if gk else sp.spine
            chain_ids = s["chain"]
            mine = spine[spine["player_id"] == pid]
            crow0 = mine.iloc[0]
            name = crow0["full_name"]
            nn = PV.norm(name)
            ns = seasons_for(name, gk)
            pos = "G" if gk else ("D" if str(crow0["posgrp"]).startswith("D") else "F")
            nk = None if gk else crow0["nk"]
            ck = None if gk else sp.forecaster.career_of.get(nk)
            if not ns.index.isin(range(y - 3, y)).any() and not gk:
                names_note.append(f"{r['player_name']} ({name}): no WAR season in the three before page {y}")
            c = d[d["row_type"] == "contract"].sort_values("season_start")
            term = int(s.get("term_years", len(c)))
            real = rev = ret = 0.0
            later = c[c["season_start"] >= NOW]
            fc = None
            if len(later):
                H = int(later["season_start"].max()) - NOW
                fc = (now.goalie(crow0["nname"], crow0["bd"], H) if gk else now.skater(nk, H))
            for _, q in c.iterrows():
                z = int(q["season_start"])
                keep = (1.0 - rpct) if int(q["contract_id"]) == int(chain_ids[0]) else 1.0
                f = share if z == y else 1.0
                cost = float(q["cost_dollars"])
                if z <= LAST:
                    gp, w = gp_war(ns, z)
                    if f < 1.0:
                        gpp, gps = gp_after(crow0["nhl_id"], z, date)
                        v = part_value(w, gp, gpp, f, z, gk, pos, term)
                    else:
                        v = played_value(w, gp, z, gk, pos, term)
                    real += (v - cost * keep * f / CAP[z]) * CAP_NOW / 1e6
                    ret -= cost * (1 - keep) * f / CAP[z] * CAP_NOW / 1e6
                else:
                    h = z - NOW
                    ceil = cap_path(NOW, h)
                    if fc is not None and h < len(fc):
                        w, p = float(fc.iloc[h]["war_if_plays"]), float(fc.iloc[h]["p_play"])
                        if gk:
                            val = max(line(w, True, "G", 0) * ceil, league_min_path(z))
                        else:
                            sl = BETA_D if pos == "D" else BETA_F
                            val = expected_floored_value(line(w, False, pos, term) * ceil,
                                                         sl * war_if_plays_sd(h) * ceil, league_min_path(z))
                    else:
                        val, p = 0.0, 0.0                  # no forecast at 2026-27: he is not expected to play
                    rev += (p * val - cost * keep) / ceil * CAP_NOW / 1e6
                    ret -= cost * (1 - keep) / ceil * CAP_NOW / 1e6
            # control seasons: the forecast's own list (the chain end's expiry and UFA year)
            ctrl_real = ctrl_rev = 0.0
            t = d[d["row_type"] == "terminal"].sort_values("season_start")
            lrows = chain_rows(spine, pid, [int(chain_ids[-1])], 0, sp.signed, as_of)
            end = int(lrows["season_start"].max())
            final = lrows[lrows["season_start"] == end].iloc[0]
            rfa = final["pp_expiry"] == "RFA" and pd.notna(final["ufa_year"]) and int(final["ufa_year"]) > end + 1
            assert rfa or not len(t), (r["player_name"], final["pp_expiry"])                   # GUARD
            if rfa:
                if gk:
                    sal = float(final["cs_nhl_salary"]) if pd.notna(final["cs_nhl_salary"]) else float(final["pp_aav"])
                else:
                    sal, _ = RTV.final_year_salary(lrows, final)
                s20 = int(lrows["season_start"].min()) >= 2020
                ch = Chain(sal, float(final["cost"]), s20)
                flag = eng.tv.arb_flag.get(int(chain_ids[-1]))
                need = None
                if flag is None:
                    if gk:
                        need = None
                    else:
                        _, need = eng.tv._arb_history(nk, y, crow0.get("nhl_id"), crow0.get("bd"))
                # every control season to the UFA year (the forecast's span; a goalie's forecast stops listing them at
                # its walk-away, D13, which an outcome does not)
                ctrl = list(range(end + 1, int(final["ufa_year"])))
                if not gk and len(t):
                    assert [int(z) for z in t["season_start"]] == ctrl, (r["player_name"], ctrl)   # GUARD: the same seasons
                    qo1 = RTV.qualifying_offer(sal, float(final["cost"]), ctrl[0], s20)
                    tv0 = eng.tv.terminal_value(pid, y, as_of)[0]
                    assert abs(float(tv0.iloc[0]["qo_cost"]) - qo1) < 1.0, (r["player_name"], qo1)   # GUARD: chain start
                ctrl_real, ctrl_rev = control_part(
                    gk=gk, pos=pos, name_seasons=ns, nhl_id=crow0["nhl_id"], nk=nk, ck=ck, nname=crow0["nname"],
                    bd=crow0["bd"], seasons=ctrl, chain=ch, flag=flag, need=need, y0=y, share=share,
                    trade_date=date, first_is_trade_season=False)
        finally:
            sp.signed.update(masked)
        rows[int(r["asset_id"])] = {"realised_M": real + ctrl_real, "revalued_M": rev + ctrl_rev,
                                   "trailing_war": np.nan if gk else trailing_total(ns, y),
                                   "outcome_route": "player model"}
        retained_out[int(r["asset_id"])] = ret
        n_eng += 1
    log(f"\n1. player model, 2018-19 on: {n_eng} assets re-run, each npv_total within $1 of traded_player_values")

    # ======================================================================================================
    # 2. RIGHTS (rights_values.csv): control seasons from the page to the UFA year
    # ======================================================================================================
    rv = pd.read_csv(OUTPUT_DIR / "rights_values.csv").set_index("asset_id")
    tpi = tp.set_index("asset_id")
    n_r = 0
    for aid, r in rv.iterrows():
        if str(tpi.at[aid, "status"]) != "rights: RFA control years":
            rows[int(aid)] = {"realised_M": 0.0, "revalued_M": 0.0, "outcome_route": "rights, UFA: zero"}
            continue
        P, pid = int(r["page"]), tpi.at[aid, "player_id"]
        gk = r["position"] == "G"
        cid = int(r["expired_contract"])
        spine = eng.gp_spine if gk else sp.spine
        mine = spine[spine["player_id"] == pid] if pd.notna(pid) else spine.iloc[0:0]
        if len(mine):
            crow0 = mine.iloc[0]
            name, nk, nname, bd, nid = crow0["full_name"], (None if gk else crow0["nk"]), crow0["nname"], crow0["bd"], crow0["nhl_id"]
        else:
            name, nk, nname, bd, nid = r["player_name"], None, PV.norm(r["player_name"]), pd.NaT, tpi.at[aid, "nhl_id"]
        if cid >= 0:
            lr = spine[spine["contract_id"] == cid].sort_values("season_start")
            final = lr.iloc[-1]
            sal = (RTV.final_year_salary(lr, final)[0] if not gk else
                   (float(final["cs_nhl_salary"]) if pd.notna(final["cs_nhl_salary"]) else float(final["pp_aav"])))
            s20, flag = int(lr["season_start"].min()) >= 2020, eng.tv.arb_flag.get(cid)
        else:
            sal, s20, flag = float(r["last_cap_hit"]), False, None   # CapWages contract: its cap hit stands in (stated)
        need = None
        if flag is None and not gk and nk is not None:
            _, need = eng.tv._arb_history(nk, P, nid, bd)
        ns = seasons_for(name, gk)
        ck = None if (gk or nk is None) else sp.forecaster.career_of.get(nk)
        seasons = list(range(P, int(r["ufa_year"])))
        share = float(r["season_share"]) if pd.notna(r["season_share"]) else 1.0
        real, rev = control_part(gk=gk, pos=r["position"], name_seasons=ns, nhl_id=nid, nk=nk, ck=ck, nname=nname,
                                 bd=bd, seasons=seasons, chain=Chain(sal, float(r["last_cap_hit"]), s20), flag=flag,
                                 need=need, y0=P, share=share, trade_date=pd.Timestamp(r["trade_date"]),
                                 first_is_trade_season=True)
        rows[int(aid)] = {"realised_M": real, "revalued_M": rev, "outcome_route": "rights",
                          "trailing_war": np.nan if gk else trailing_total(ns, P)}
        n_r += 1
    log(f"2. rights: {n_r} with control seasons, {len(rv) - n_r} zero")

    # ======================================================================================================
    # 3. THE 2017 PAGE: the CapWages chain, as page_2017_values v1.6 builds it
    # ======================================================================================================
    p17 = pd.read_csv(OUTPUT_DIR / "page_2017_values.csv")
    n17 = 0
    for _, r in p17.iterrows():
        if r["status"] != "ok":
            continue
        aid, date = int(r["asset_id"]), pd.Timestamp(r["trade_date"])
        gk = r["position"] == "G"
        pos = r["position"]
        ns = seasons_for(r["war_name"], gk)
        share = float(r["season_share"]) if pd.notna(r["season_share"]) else 1.0
        rpct = float(r["retained_pct"]) if pd.notna(r["retained_pct"]) else 0.0
        real = rev = ret = 0.0
        if str(r["contract"]).startswith("PuckPedia"):
            # FALLBACK rows: PuckPedia's own contract, on the engine (page_2017_values' fallback path)
            d, s, masked, as_of = engine_detail(int(r["player_id"]), 2017, date, share, rpct)
            sp.signed.update(masked)
            c = d[d["row_type"] == "contract"]
            assert abs(s["npv_total"] - r["npv_total"]) < 1.0, r["player_name"]                    # GUARD
            seasons = [(int(q["season_start"]), float(q["cost_dollars"]), int(q["contract_id"]) == int(s["chain"][0]))
                       for _, q in c.iterrows()]
            ctrl, ch, flag = [], None, None
        else:
            f = K.find_page(r["player_name"])
            cons = K.parse_contracts(K.page_lines(f.read_text(encoding="utf-8", errors="ignore")))
            run = [x for x in cons if 2017 in x["seasons"] and pd.notna(x.get("signing_date")) and x["signing_date"] <= date]
            c0 = max(run, key=lambda x: x["signing_date"])
            chain = [c0]
            while True:
                nxt = [x for x in cons if pd.notna(x.get("signing_date")) and x["signing_date"] < date
                       and x["seasons"] and min(x["seasons"]) == max(chain[-1]["seasons"]) + 1]
                if not nxt:
                    break
                chain.append(min(nxt, key=lambda x: x["signing_date"]))
            assert len(chain) - 1 == int(r["extensions"]) and max(chain[-1]["seasons"]) == int(r["chain_last_season"]), \
                r["player_name"]                                                                   # GUARD
            seasons = [(z, cc["seasons"][z], i == 0) for i, cc in enumerate(chain) for z in sorted(cc["seasons"])
                       if z >= 2017]
            raw = str(chain[-1].get("expiry_status"))
            rfa = raw.startswith("RFA") or raw.startswith("10.2")
            end = max(z for z, _, _ in seasons)
            ctrl = list(range(end + 1, int(r["ufa_year"]))) if rfa and pd.notna(r["ufa_year"]) else []
            base = chain[-1].get("base", {}).get(end)
            ch = Chain(float(base) if base else float(chain[-1]["seasons"][end]), float(chain[-1]["seasons"][end]), False)
            flag = (1 if "Arb" in raw else 0) if rfa else None
        term = len(seasons)
        for z, cost, first in seasons:
            keep = (1.0 - rpct) if first else 1.0
            f = share if z == 2017 else 1.0
            if z <= LAST:
                gp, w = gp_war(ns, z)
                if f < 1.0:
                    gpp, gps = gp_after(r["nhl_id"], z, date)
                    v = part_value(w, gp, gpp, f, z, gk, pos, term)
                else:
                    v = played_value(w, gp, z, gk, pos, term)
                real += (v - cost * keep * f / CAP[z]) * CAP_NOW / 1e6
                ret -= cost * (1 - keep) * f / CAP[z] * CAP_NOW / 1e6
            else:
                raise AssertionError(f"2017-page contract past 2025-26: {r['player_name']}")       # GUARD: none expected
        if ctrl:
            nk = None
            pid = r["player_id"]
            if not gk and pd.notna(pid) and (sp.spine["player_id"] == pid).any():
                nk = sp.spine.loc[sp.spine["player_id"] == pid, "nk"].iloc[0]
            ck = sp.forecaster.career_of.get(nk) if nk is not None else None
            cr, cv = control_part(gk=gk, pos=pos, name_seasons=ns, nhl_id=r["nhl_id"], nk=nk, ck=ck,
                                  nname=PV.norm(r["war_name"]), bd=pd.NaT, seasons=ctrl, chain=ch, flag=flag, need=None,
                                  y0=2017, share=share, trade_date=date, first_is_trade_season=False)
            real, rev = real + cr, rev + cv
        rows[aid] = {"realised_M": real, "revalued_M": rev, "outcome_route": "player model, 2017 page",
                     "trailing_war": np.nan if gk else trailing_total(ns, 2017)}
        retained_out[aid] = ret
        n17 += 1
    log(f"3. the 2017 page: {n17} assets")

    # ======================================================================================================
    # 4. PROSPECTS AND PICKS: the drafted player's pick-curve seasons, then the 2026-27 page
    # ======================================================================================================
    pcs = pd.concat([pd.read_csv(OUTPUT_DIR / "pick_curve_seasons.csv"),
                     pd.read_csv(OUTPUT_DIR / "pick_curve_later_seasons.csv")], ignore_index=True)
    pcp = pd.concat([pd.read_csv(OUTPUT_DIR / "pick_curve_players.csv"),
                     pd.read_csv(OUTPUT_DIR / "pick_curve_later_players.csv")], ignore_index=True)
    pcp = pcp.drop_duplicates(["draftYear", "pick"]).set_index(["draftYear", "pick"])
    by_pick = {k: g.set_index("season") for k, g in pcs.groupby(["draftYear", "pick"])}
    link = pd.read_csv(OUTPUT_DIR / "draft_pick_linkage.csv", parse_dates=["birthDate"]).set_index(
        ["draftYear", "overallPickNumber"])
    bacon = pd.read_csv(SOURCE_DIR / "draft_slot_baseline.csv").set_index("draft_pick")["p_star"]
    fits = pd.read_csv(OUTPUT_DIR / "prospect_production_fits.csv")
    fits = fits[(fits["version"] == "main") & (fits["left_out"] == "none")].set_index("k_group")
    stars = pd.read_csv(OUTPUT_DIR / "prospect_star_values.csv")
    stars = stars[stars["left_out"] == "none"].set_index("k_group")["star_value_M"]
    rates = PV.production_rates()
    con = sqlite3.connect(OUTPUT_DIR / "ep_out" / "ep_prospects.db")
    ep_draft = pd.read_sql("select draft_year, draft_overall, ep_player_id from ep_draft_selections", con)
    EPD = {(int(a), int(b)): str(int(c)) for a, b, c in zip(ep_draft["draft_year"], ep_draft["draft_overall"],
                                                           ep_draft["ep_player_id"]) if pd.notna(c)}
    pc_all, _ = CS.load_contracts()
    EP_BY_NHL = {int(a): str(int(b)) for a, b in zip(pc_all["nhl_id"], pc_all["eliteprospects_id"])
                 if pd.notna(a) and pd.notna(b)}

    def prospect_now(k, p_star, ep, birth, gk):
        """The prospect model at season 2026, k seasons after his draft (or first eligibility)."""
        g = PV.k_group(k)
        if gk:
            return p_star * float(stars[g])
        fr = pd.DataFrame({"ep_player_id": [ep or "none"], "season": [NOW], "k": [k], "birthDate": [birth]})
        fr = PV.production_features(fr, rates)
        cols = PV.cols_for(g, "main")
        fr["p_star"] = p_star
        return float(sum(fits.at[g, cc] * fr[cc].iloc[0] for cc in cols))

    def draftee_rest(*, gk, pos, base_year, window_end, played, birth, ep, p_star, k_now, name, state, war_names):
        """Seasons 2026-27 to the end of club control. A prospect at 2026: the prospect model. An NHL player: xNPV 1
        (goalies the goalie forecast) at page 2026, value x chance of playing minus the rule's cost when he plays."""
        if window_end - 1 < NOW:
            return 0.0, "control over"
        gpby = played["gp"] if len(played) else pd.Series(dtype=float)
        sea = pd.DataFrame({"GP": gpby})
        if PV.is_prospect(sea, NOW, gk):
            return prospect_now(k_now, p_star, ep, birth, gk), "prospect at 2026"
        if state is None or pd.isna(state.get("first")):
            return 0.0, "no chain"
        H = window_end - 1 - NOW
        if gk:
            fc = now.goalie(PV.norm(name), birth, H)
            ck = None
        else:
            ck, pkey = career_for(eng, war_names, gpby)
            fc = now.skater(pkey, H) if pkey is not None else None
        if fc is None:
            return 0.0, "no forecast at 2026"
        first, n_elc, need = int(state["first"]), int(state["n_elc"]), int(state["need"])
        prior = state.get("prior")
        prior = None if prior is None or pd.isna(prior) else float(prior)
        pro = sum(1 for z, g in gpby.items() if z < NOW and g >= ARB_GP.get(z, 10))
        tot = 0.0
        for z in range(NOW, window_end):
            h = z - NOW
            ceil = cap_path(NOW, h)
            in_elc = first <= z < first + n_elc
            if in_elc:
                cost = ELC_MAX[base_year]
            else:
                base = prior or ELC_MAX[base_year]
                qo = RTV.qualifying_offer(base, base, z, False)
                tw = None
                if pro >= need:
                    if gk:
                        tw = eng.g_proj.arbitration_war(PV.norm(name), NOW, z, float(fc.iloc[h]["war_if_plays"]))
                    elif ck is not None:
                        r_ = now.fc.arbitration_war(ck, NOW, z)
                        tw = None if r_ is None else r_[0]
                cost = max(qo, max(line(tw, gk, pos, 1) * ceil, league_min_path(z))) if tw is not None else qo
                prior = cost
            w, p = float(fc.iloc[h]["war_if_plays"]), float(fc.iloc[h]["p_play"])
            val = max(line(w, gk, pos, 1) * ceil, league_min_path(z))
            tot += p * (val - cost) / ceil * CAP_NOW / 1e6
            pro += 1                                       # a forecast season counts as played (rfa_terminal_value)
        return tot, "NHL at 2026"

    # 4a. the cost chain's state for the 2007-2017 draftees (pick_curve_later_players carries it for 2018-2025):
    # this script's copy of pick_curve.price's chain, GUARDED against pick_curve_seasons season by season
    elc = pd.read_csv(OUTPUT_DIR / "elc_signing_dates.csv").dropna(subset=["draftYear", "signing_year"])
    SIGNED = {(int(a), int(b)): int(c) for a, b, c in zip(elc["draftYear"], elc["pick"], elc["signing_year"])}

    def chain_state(dy, pk, gk, pos, birth, played, war_names):
        """pick_curve.price's adopted chain through 2025-26: (state, {season: cost_$}) from his played seasons."""
        if not len(played):
            return {"first": np.nan}, {}
        first = int(played.index.min())
        sy = SIGNED.get((dy, pk))
        age = RTV.cba_age(birth, sy if sy is not None else first)
        n_elc = 3 if age <= 21 else 2 if age <= 23 else 1
        need = ARB_NEED(age)
        ck = None
        if not gk:
            ck, _ = career_for(eng, war_names, played["gp"])
        prior, costs = None, {}
        gp_of = played["gp"]
        for z in range(dy, LAST + 1):
            if z >= first + n_elc:
                qo = RTV.qualifying_offer(prior or ELC_MAX[dy], prior or ELC_MAX[dy], z, False)
                pro = sum(1 for q, g in gp_of.items() if q < z and g >= ARB_GP.get(q, 10))
                tw = None
                if z in gp_of.index and gp_of[z] > 0 and pro >= need:
                    if gk:
                        tw = None   # goalies: read from the season rows below
                    elif ck is not None:
                        r_ = now.fc.arbitration_war(ck, z, z)
                        tw = None if r_ is None else r_[0]
                if gk and z in played.index and bool(played.at[z, "arb_eligible"]):
                    tw = float(played.at[z, "arb_market_war"])
                prior = max(qo, max(line(tw, gk, pos, 1) * CAP[z], LMIN[z])) if tw is not None else qo
                if z in played.index:
                    costs[z] = prior
            elif z in played.index:
                costs[z] = ELC_MAX[dy]
        return {"first": first, "n_elc": n_elc, "need": need, "prior": prior}, costs

    pv = pd.read_csv(OUTPUT_DIR / "prospect_values.csv")
    pvi = pv.set_index("asset_id")
    checked, n_pro, n_pick = 0, 0, 0
    cache_state = {}

    def draftee(dy, pk):
        """(played seasons frame, route, window_end, state) for a drafted player, cached."""
        if (dy, pk) in cache_state:
            return cache_state[(dy, pk)]
        pl = pcp.loc[(dy, pk)] if (dy, pk) in pcp.index else None
        played = by_pick.get((dy, pk), pcs.iloc[0:0].set_index("season"))
        lk = link.loc[(dy, pk)] if (dy, pk) in link.index else None
        gk = bool(lk["is_goalie"]) if lk is not None else False
        pos = "G" if gk else ("D" if lk is not None and lk["position"] == "D" else "F")
        name = (str(lk["war_names"]).split("|")[0] if lk is not None and pd.notna(lk["war_names"])
                else (lk["playerName"] if lk is not None else ""))
        birth = lk["birthDate"] if lk is not None else pd.NaT
        if dy >= 2018 and pl is not None:
            state = {"first": pl["chain_first"], "n_elc": pl["chain_n_elc"], "need": pl["chain_need"],
                     "prior": pl["chain_prior"]}
        elif pd.notna(birth):
            state, costs = chain_state(dy, pk, gk, pos, birth, played, lk["war_names"])
            # GUARD: the copy reproduces the pick curve's adopted cost in every season he played
            for z, cst in costs.items():
                assert abs(float(played.at[z, "cost_$"]) / float(played.at[z, "games_scale"]) - cst) < 1.0, (dy, pk, z)
        else:
            state = None
        wn = lk["war_names"] if lk is not None else None
        out = (played, (pl["route"] if pl is not None else "not in the pick curve"),
               (int(pl["window_end"]) if pl is not None else None), state, gk, pos, name, birth, wn)
        cache_state[(dy, pk)] = out
        return out

    # 4b. the traded prospects
    for aid, r in pvi.iterrows():
        st = str(r["status"])
        if not st.startswith(("prospect, valued", "undrafted prospect, valued")):
            continue
        y = int(r["valuation_page"])
        if st.startswith("prospect, valued"):
            dy, pk = int(r["draftYear"]), int(r["pick"])
            played, route, wend, state, gk, pos, name, birth, wn = draftee(dy, pk)
            checked += 1
            if route in LAPSED:
                rows[int(aid)] = {"realised_M": 0.0, "revalued_M": 0.0, "outcome_route": f"prospect, {route}"}
                continue
            real = float(played.loc[(played.index >= y) & (played.index <= LAST), "surplus_2025_cap"].sum()) / 1e6
            ep = EPD.get((dy, pk))
            rest, how = draftee_rest(gk=gk, pos=pos, base_year=dy, window_end=wend, played=played, birth=birth, ep=ep,
                                     p_star=float(bacon[pk]), k_now=NOW - dy, name=name, state=state, war_names=wn)
            rows[int(aid)] = {"realised_M": real, "revalued_M": rest, "outcome_route": f"prospect, {how}"}
        else:
            # undrafted on an NHL contract: the same chain from his first NHL season, the slot term zero
            gk = bool(r["is_goalie"]) if pd.notna(r["is_goalie"]) else False
            name = r["player_name"]
            nid = r["nhl_id_undrafted"] if pd.notna(r.get("nhl_id_undrafted")) else r.get("nhl_id")
            birth = pd.to_datetime(r["birthDate"])
            fe = int(r["first_eligible_draft"])
            ns = seasons_for(name, gk)
            wend = PV.window_end(birth, gk, ns)
            pos = "G" if gk else ("D" if str(r.get("position")) == "D" else "F")
            pl = ns[(ns["GP"] > 0) & (ns.index <= LAST)].rename(columns={"GP": "gp"})
            pl = pl[pl.index < wend]
            real, state = 0.0, {"first": np.nan}
            if len(pl):
                first = int(pl.index.min())
                age = RTV.cba_age(birth, first)
                n_elc, need = (3 if age <= 21 else 2 if age <= 23 else 1), ARB_NEED(age)
                prior = None
                for z in range(fe, min(wend - 1, LAST) + 1):
                    cost = None
                    if first <= z < first + n_elc:
                        cost = ELC_MAX[min(fe, 2026)]
                    elif z >= first + n_elc:
                        cost = RTV.qualifying_offer(prior or ELC_MAX[min(fe, 2026)], prior or ELC_MAX[min(fe, 2026)], z, False)
                        prior = cost
                    if z in pl.index and z >= y:
                        gp, w = gp_war(ns, z)
                        sc = gp / 82 if gp < CAMEO_GP else 1.0
                        real += (played_value(w, gp, z, gk, pos, 1) - (cost or 0) / CAP[z] * sc) * CAP_NOW / 1e6
                state = {"first": first, "n_elc": n_elc, "need": need, "prior": prior}
            ep = EP_BY_NHL.get(int(nid)) if pd.notna(nid) else None
            rest, how = draftee_rest(gk=gk, pos=pos, base_year=min(fe, 2026), window_end=wend,
                                     played=pl, birth=birth, ep=ep, p_star=0.0, k_now=NOW - fe, name=name, state=state,
                                     war_names=name)
            rows[int(aid)] = {"realised_M": real, "revalued_M": rest, "outcome_route": f"undrafted prospect, {how}"}
        n_pro += 1
    log(f"4. prospects: {n_pro} valued assets; the chain copy checked against the pick curve for {checked} draftees "
        f"(every played season equal to $1)")

    # 4c. the traded picks: the player drafted with each
    tpk = pd.read_csv(OUTPUT_DIR / "traded_pick_values.csv")
    no_slot = []
    for _, r in tpk.iterrows():
        aid = int(r["asset_id"])
        dy = int(r["pick_year"])
        if pd.isna(r["actual_slot"]) or dy > LAST:
            no_slot.append(f"{r['trade_date']} {dy} round {int(r['pick_round'])} ({r['original_team']})")
            rows[aid] = {"realised_M": np.nan, "revalued_M": np.nan, "outcome_route": "pick, no selection recorded"}
            continue
        pk = int(r["actual_slot"])
        played, route, wend, state, gk, pos, name, birth, wn = draftee(dy, pk)
        if route in LAPSED or wend is None:
            rows[aid] = {"realised_M": 0.0, "revalued_M": 0.0, "outcome_route": f"pick, {route}"}
            continue
        real = float(played.loc[played.index <= LAST, "surplus_2025_cap"].sum()) / 1e6
        rest, how = draftee_rest(gk=gk, pos=pos, base_year=dy, window_end=wend, played=played, birth=birth,
                                 ep=EPD.get((dy, pk)), p_star=float(bacon[pk]), k_now=NOW - dy, name=name, state=state,
                                 war_names=wn)
        rows[aid] = {"realised_M": real, "revalued_M": rest, "outcome_route": f"pick, {how}"}
        n_pick += 1
    log(f"   picks: {n_pick} followed to their player; no selection recorded: {len(no_slot)}"
        + "".join(f"\n     {x}" for x in no_slot))

    # ======================================================================================================
    # 5. THE ASSET TABLE: forecast beside outcome
    # ======================================================================================================
    a = tav.copy()
    a["realised_M"] = np.nan
    a["revalued_M"] = np.nan
    a["outcome_route"] = None
    a["trailing_war"] = np.nan
    for i, r in a.iterrows():
        aid = int(r["asset_id"])
        if r["asset_type"] == "retained salary":
            if aid in retained_out:
                a.at[i, "realised_M"], a.at[i, "revalued_M"] = retained_out[aid], 0.0
                a.at[i, "outcome_route"] = "retained salary (realised cap)"
            continue
        src = r["source"]
        if aid in rows and not (src.startswith(("buried", "prospect model (zero)", "not valued"))):
            for k, v in rows[aid].items():
                a.at[i, k] = v
        elif src.startswith(("buried", "prospect model (zero)")):
            a.at[i, "realised_M"], a.at[i, "revalued_M"] = r["value_2025_cap_M"], 0.0
            a.at[i, "outcome_route"] = "outcome = forecast (" + src + ")"
    # the revalued part's retained share is already in the retained rows' realised part (cap hits are fixed); the
    # retained cost after 2025-26 is in `ret` for engine players (realised_M carries both parts for retained rows)
    a["outcome_M"] = a["realised_M"] + a["revalued_M"]
    miss = a[(a["source"] != "not valued") & a["outcome_M"].isna()]
    log(f"\n5. assets with a forecast and no outcome: {len(miss)}")
    for r in miss.itertuples():
        log(f"     {r.trade_date} {r.name} ({r.source}; {r.status})")
    if names_note:
        log(f"   players with no WAR season in the three before the page under the spine's spelling: {len(names_note)}")
        for x in names_note[:20]:
            log(f"     {x}")
    a.to_csv(OUTPUT_DIR / "backtest_assets.csv", index=False)
    analyse(a)
    (OUTPUT_DIR / "backtest_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    log(f"\nwrote backtest_assets.csv, backtest_sides.csv, backtest_results.csv and backtest_log.txt in {OUTPUT_DIR}")


# ======================================================================================================
# THE TESTS (the protocol's A, B, C and sensitivities)
# ======================================================================================================
def boot(trades, stat, rng, null=0.0):
    """Resample trades with replacement N_BOOT times; stat(list of trade ids) -> float. Percentile 95% interval and
    the two-sided p-value against `null` (the share of resamples on the other side of it, doubled)."""
    ids = np.array(trades)
    vals = np.array([stat(ids[rng.integers(0, len(ids), len(ids))]) for _ in range(N_BOOT)])
    vals = vals[np.isfinite(vals)]
    est = stat(ids)
    lo, hi = np.percentile(vals, [2.5, 97.5])
    p = min(1.0, 2 * min((vals <= null).mean(), (vals >= null).mean()))
    return est, lo, hi, p


def analyse(a):
    clubs, cond = TSD.trade_clubs()
    ok = a.copy()
    fore = TSD.club_sides(ok, "value_2025_cap_M", clubs, cond)
    out = TSD.club_sides(ok.assign(o=ok["outcome_M"]), "o", clubs, cond)
    real_only = TSD.club_sides(ok.assign(o=ok["realised_M"]), "o", clubs, cond)
    key = ["trade_id", "club"]
    s = fore.merge(out[key + ["net_M"]].rename(columns={"net_M": "out_net_M"}), on=key).merge(
        real_only[key + ["net_M"]].rename(columns={"net_M": "real_net_M"}), on=key)
    # trades whose every asset has an outcome (picks with no selection, unvalued assets out)
    bad = set(ok.loc[(ok["source"] != "not valued") & ok["outcome_M"].isna(), "trade_id"]) | set(
        ok.loc[ok["source"] == "not valued", "trade_id"])
    s["complete"] = ~s["trade_id"].isin(bad)
    s["miss_M"] = s["out_net_M"] - s["net_M"]
    # ---- group flags ---------------------------------------------------------------------------------------------------
    pl = ok[ok["asset_type"] == "player"]
    fut = ok[ok["source"].str.startswith(("pick curve", "prospect model"))]
    two = s.groupby("trade_id")["club"].transform("size") == 2
    got_fut = s.apply(lambda r: ((fut["trade_id"] == r.trade_id) & (fut["acquiring_team"] == r.club)).any(), axis=1)
    got_pl = s.apply(lambda r: ((pl["trade_id"] == r.trade_id) & (pl["acquiring_team"] == r.club)).any(), axis=1)
    s["got_futures"], s["got_players"] = got_fut, got_pl
    g1 = pd.Series(False, index=s.index)
    for tid, g in s[two].groupby("trade_id"):
        if len(g) != 2:
            continue
        i, j = g.index
        for x, y in ((i, j), (j, i)):
            if s.at[x, "got_futures"] and not s.at[y, "got_futures"] and s.at[y, "got_players"]:
                g1[x] = True
    s["g_futures"] = g1
    # standings at the trade date (points percentage, games before it)
    gm = pd.read_csv(SOURCE_DIR / "games.csv")
    gm = gm[gm["game_type"] == 2].copy()
    gm["date"] = pd.to_datetime(gm["game_date"])

    def pts_pct(season, on):
        g = gm[(gm["season"] == season) & (gm["date"] < on)]
        rec = {}
        for r in g.itertuples():
            hw = r.home_score > r.away_score
            for t, won in ((r.home_team, hw), (r.away_team, not hw)):
                w, gpl, pts = rec.get(t, (0, 0, 0))
                rec[t] = (w, gpl + 1, pts + (2 if won else (1 if r.last_period in ("OT", "SO") else 0)))
        return {t: v[2] / (2 * v[1]) for t, v in rec.items() if v[1] > 0}
    CODE = {"L.A": "LAK", "N.J": "NJD", "S.J": "SJS", "T.B": "TBL", "VEG": "VGK", "PHX": "ARI"}
    s["g_buyer"] = False
    s["standing"] = np.nan
    for tid, g in s[two & s["during_regular_season"]].groupby("trade_id"):
        d = pd.Timestamp(g["trade_date"].iloc[0])
        y = TP.trade_season(d)
        tab = pts_pct(int(f"{y}{y + 1}"), d)
        pp = {i: tab.get(CODE.get(c, c)) for i, c in zip(g.index, g["club"])}
        for i, v in pp.items():
            s.at[i, "standing"] = v
        if len(pp) == 2 and all(v is not None for v in pp.values()) and len(set(pp.values())) == 2:
            s.at[max(pp, key=pp.get), "g_buyer"] = True
    stars = pl[(pl["trailing_war"] >= 3.0)]
    s["g_star"] = s.apply(lambda r: ((stars["trade_id"] == r.trade_id) & (stars["acquiring_team"] == r.club)).any(), axis=1)
    ret = ok[ok["asset_type"] == "retained salary"]
    s["g_retained"] = s.apply(lambda r: ((ret["trade_id"] == r.trade_id) & (ret["acquiring_team"] == r.club)).any(), axis=1)
    s["g_nothing_back"] = s["n_received"] == 0
    # clauses: the season spine's clause flag for the player's contract in the trade's page season
    ss = pd.read_csv(OUTPUT_DIR / "contract_season_spine.csv", usecols=["nhl_id", "season_start", "has_any_clause"])
    cl = set((int(a), int(b)) for a, b, c in zip(ss["nhl_id"], ss["season_start"], ss["has_any_clause"])
             if pd.notna(a) and c == 1)
    tpv = pd.read_csv(OUTPUT_DIR / "traded_player_values.csv").set_index("asset_id")
    pl_cl = pl[pl["asset_id"].map(lambda x: x in tpv.index and pd.notna(tpv.at[x, "nhl_id"])
                                  and (int(tpv.at[x, "nhl_id"]), int(tpv.at[x, "valuation_page"])) in cl)]
    s["g_clause"] = s.apply(lambda r: ((pl_cl["trade_id"] == r.trade_id) & (pl_cl["acquiring_team"] == r.club)).any(), axis=1)
    s.to_csv(OUTPUT_DIR / "backtest_sides.csv", index=False)

    rng = np.random.default_rng(SEED)
    res = []
    c = s[s["complete"]]
    n_t = c["trade_id"].nunique()
    log(f"\nTHE BACK-TEST: {n_t} complete trades of {s['trade_id'].nunique()} ({len(c)} club sides); $M at the 2025-26 cap")
    log(f"  outcome = realised through 2025-26 + the rest revalued at 2026-27; sum of |outcome net| over sides "
        f"{c['out_net_M'].abs().sum():,.1f}, of which revalued (|outcome - realised-only|) "
        f"{(c['out_net_M'] - c['real_net_M']).abs().sum():,.1f}")
    by = {t: g for t, g in c.groupby("trade_id")}

    def cat(ids, col):
        return pd.concat([by[t] for t in ids])[col] if len(ids) else pd.Series(dtype=float)

    # ---- A: does the forecast predict the outcome ---------------------------------------------------------------------
    def slope(ids, ycol="out_net_M"):
        d = pd.concat([by[t] for t in ids])
        x, yv = d["net_M"].values, d[ycol].values
        return float((x * yv).sum() / (x * x).sum()) if (x * x).sum() > 0 else np.nan

    def corr(ids):
        d = pd.concat([by[t] for t in ids])
        return float(np.corrcoef(d["net_M"], d["out_net_M"])[0, 1])

    fav = c.loc[c.groupby("trade_id")["net_M"].idxmax()]
    fav = fav[fav["net_M"] > 0]
    favd = fav.set_index("trade_id")["out_net_M"]

    def agree(ids):
        v = favd.reindex(ids).dropna()
        return float((v > 0).mean()) if len(v) else np.nan

    trades = sorted(by)
    for name, fn in (("A. slope of outcome net on forecast net (1 = the forecast's gaps come true)", slope),
                     ("A. correlation of forecast net and outcome net", corr),
                     ("A. share of trades whose favoured club came out ahead (0.5 = a coin)", agree)):
        est, lo, hi, p = boot(trades, fn, rng, null=0.5 if name.startswith("A. share") else 0.0)
        res.append({"test": name, "group": "all complete trades", "n_trades": n_t, "estimate": est, "lo95": lo,
                    "hi95": hi, "p": p})
        log(f"  {name}: {est:.3f} [{lo:.3f}, {hi:.3f}] (p of the sign {p:.4f})" if not name.startswith("A. share")
            else f"  {name}: {est:.3f} [{lo:.3f}, {hi:.3f}] (p against 0.5: {p:.4f})")
    est, lo, hi, p = boot(trades, lambda ids: slope(ids, "real_net_M"), rng)
    res.append({"test": "A, sensitivity: realised only (nothing revalued)", "group": "all complete trades",
                "n_trades": n_t, "estimate": est, "lo95": lo, "hi95": hi, "p": p})
    log(f"  sensitivity, outcome through 2025-26 only: slope {est:.3f} [{lo:.3f}, {hi:.3f}]")
    nc = [t for t in trades if not by[t]["has_conditional_pick"].any()]
    est, lo, hi, p = boot(nc, slope, rng)
    res.append({"test": "A, sensitivity: trades with a conditional pick left out", "group": "no conditional pick",
                "n_trades": len(nc), "estimate": est, "lo95": lo, "hi95": hi, "p": p})
    log(f"  sensitivity, conditional picks left out ({len(nc)} trades): slope {est:.3f} [{lo:.3f}, {hi:.3f}]")
    for lab, flag in (("in-season", True), ("off-season", False)):
        ids = [t for t in trades if bool(by[t]["during_regular_season"].iloc[0]) == flag]
        est, lo, hi, p = boot(ids, slope, rng)
        res.append({"test": "C7. slope by timing", "group": lab, "n_trades": len(ids), "estimate": est, "lo95": lo,
                    "hi95": hi, "p": p})
        log(f"  C7. {lab} trades ({len(ids)}): slope {est:.3f} [{lo:.3f}, {hi:.3f}]")

    # ---- B: each class's outcome against its forecast --------------------------------------------------------------------
    log("\nB. EACH CLASS, outcome minus forecast per asset ($M; resampling trades)")
    ac = a[a["trade_id"].isin(trades) & a["outcome_M"].notna()].copy()
    ac["cls"] = ac["source"].map(TSD.asset_class)
    ac["d"] = ac["outcome_M"] - ac["value_2025_cap_M"]
    for k in ("players", "picks", "prospects", "retained"):
        g = ac[ac["cls"] == k]
        gb = {t: x for t, x in g.groupby("trade_id")}
        ids = sorted(gb)
        est, lo, hi, p = boot(ids, lambda ii: float(pd.concat([gb[t] for t in ii])["d"].mean()), rng)
        res.append({"test": "B. mean outcome minus forecast per asset", "group": k, "n_trades": len(ids),
                    "n_assets": len(g), "estimate": est, "lo95": lo, "hi95": hi, "p": p,
                    "forecast_sum_M": g["value_2025_cap_M"].sum(), "outcome_sum_M": g["outcome_M"].sum(),
                    "realised_sum_M": g["realised_M"].sum()})
        log(f"  {k:<10} {len(g):>4} assets: forecast ${g['value_2025_cap_M'].sum():>8,.1f}M, outcome "
            f"${g['outcome_M'].sum():>8,.1f}M (realised ${g['realised_M'].sum():,.1f}M); mean miss {est:+.3f} "
            f"[{lo:+.3f}, {hi:+.3f}] p {p:.4f}")
    # the pick curve's sensitivity star value (the forecast side of picks only)
    tpk = pd.read_csv(OUTPUT_DIR / "traded_pick_values.csv").set_index("asset_id")
    g = ac[ac["cls"] == "picks"].copy()
    g["fs"] = g["asset_id"].map(tpk["value_sensitivity_M"])
    log(f"  picks on the sensitivity star value (without 2015-2016): forecast ${g['fs'].sum():,.1f}M against outcome "
        f"${g['outcome_M'].sum():,.1f}M; mean miss {(g['outcome_M'] - g['fs']).mean():+.3f}")
    res.append({"test": "B, sensitivity: picks on the sensitivity star value", "group": "picks", "n_assets": len(g),
                "estimate": float((g["outcome_M"] - g["fs"]).mean()), "forecast_sum_M": g["fs"].sum(),
                "outcome_sum_M": g["outcome_M"].sum()})

    # ---- C: groups of clubs --------------------------------------------------------------------------------------------
    log("\nC. GROUPS OF CLUBS (mean per club side, $M; resampling trades): forecast net, outcome net, outcome - forecast")
    groups = (("C1. received the picks and prospects for players", "g_futures"),
              ("C2. higher in the standings, in-season two-team trades", "g_buyer"),
              ("C3. received a skater with a 3+ trailing WAR total", "g_star"),
              ("C4. retained salary", "g_retained"),
              ("C5. received nothing recorded", "g_nothing_back"),
              ("C6. received a player with a no-trade or no-move clause", "g_clause"))
    for lab, col in groups:
        gs = c[c[col]]
        gb = {t: x for t, x in gs.groupby("trade_id")}
        ids = sorted(gb)
        line_ = f"  {lab} ({len(gs)} sides, {len(ids)} trades):"
        for what, colv in (("forecast", "net_M"), ("outcome", "out_net_M"), ("outcome - forecast", "miss_M")):
            if not ids:
                continue
            est, lo, hi, p = boot(ids, lambda ii, cv=colv: float(pd.concat([gb[t] for t in ii])[cv].mean()), rng)
            res.append({"test": f"{lab}: {what}", "group": col, "n_trades": len(ids), "n_sides": len(gs),
                        "estimate": est, "lo95": lo, "hi95": hi, "p": p})
            line_ += f"\n      {what:<19} {est:+7.2f} [{lo:+7.2f}, {hi:+7.2f}] p {p:.4f}"
        log(line_)
    pd.DataFrame(res).to_csv(OUTPUT_DIR / "backtest_results.csv", index=False)


if __name__ == "__main__":
    main()
