"""
contract_value_by_age.py - why do traded players' contracts carry negative model values on average?
(Thomas, 2026-11-12: "start with 1". Report only; values nothing new, changes no model.)

THE QUESTION. The model values the traded players at -$1,028M in total (2017-2026). The price line is fitted on signed
contracts, so a contract should be worth about zero when it is signed. Three readings, each measured here:
  (a) SELECTION: clubs trade their bad contracts (a real finding);
  (b) THE TERM RULE: the price line pays gamma_term a season for each year of term (directive 4), and a contract season is
      priced on the term REMAINING at the valuation date (contract_npv.py v2.1; skater_forward_projection.py line 596:
      val = (alpha + slope x w + gamma x term_years) x ceiling, term_years = the seasons left). The cap hit was set when
      the whole term was ahead. So a deal fair at signing with T seasons, valued with R left, falls short by
      gamma x (T - R) a season on each of its R seasons: gamma x R x (T - R) of a cap, by the rule alone;
  (c) THE FORECAST runs low for some kind of player.

WHAT IT DOES (the contract panel: every contract at every July 1 page 2018-2026; $M at the 2025-26 cap)
  1. each contract at its SIGNING page (valued whole), by how it was signed and its length: on the line with term and on
     the line without (npv_total_term_free)
  2. the same contracts as they AGE: by seasons since signing and by seasons left, on both lines, beside the term rule's
     shortfall gamma x R x (T - R) x the page's ceiling; and each multi-year contract's change from its signing page
  3. TRADED against not traded in the twelve months after a page, at the same seasons left
  4. the traded player assets' total on both lines
  5. the rule's shortfall added back to the traded skaters and to the back-test's groups (approximate, not a re-run)

BAKED-IN ASSUMPTIONS
  - skaters' contracts on xNPV 1 only (goaltenders have their own line; reported in one row beside)
  - a contract's signing page is its first season (start_season_year) with every season still to play
  - traded: the player's name appears in the ledger carried to 2026 between the page's July 1 and the next (by spelling)
  - the panel's value includes the control seasons after the contract (the terminal value), priced at one year of term
  - intervals: 2,000 resamples of players, seed 20261112

INPUTS: OUTPUT_DIR/contract_npv_panel.csv, contract_level_spine.csv, trades_extended.db, traded_player_values.csv,
        trade_asset_values.csv; the PuckPedia contract export (signing status)
OUTPUTS: OUTPUT_DIR/contract_value_by_age_log.txt, contract_value_by_age.csv
"""
import os
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
load_dotenv()
import contract_source as CS                         # noqa: E402
import skater_forward_projection as SFP              # noqa: E402

OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
SCRIPT_VERSION = "contract_value_by_age.py v1.1 (2026-11-12)"   # v1.1: part 5, the rule's shortfall added back (approximate)
N_BOOT, SEED = 2000, 20261112
CAP = SFP.CAP_CEILING
CAP_NOW = CAP[2025]
GAMMA = SFP.price_constants()["gamma_term"] if isinstance(SFP.price_constants(), dict) else None
LOG, ROWS = [], []


def log(s=""):
    print(s)
    LOG.append(s)


def key(s):
    x = re.sub("[^a-z]", "", unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower())
    return x[:2] + x[-6:]


def bm(v, g, rng):
    d = pd.DataFrame({"v": np.asarray(v, float), "g": np.asarray(g)}).dropna()
    if d["g"].nunique() < 2:
        return (float(d["v"].mean()) if len(d) else np.nan), np.nan, np.nan
    s, c = d.groupby("g")["v"].sum().values, d.groupby("g")["v"].size().values
    i = rng.integers(0, len(s), (N_BOOT, len(s)))
    b = s[i].sum(1) / c[i].sum(1)
    return float(s.sum() / c.sum()), *np.percentile(b, [2.5, 97.5])


def f3(x):
    return f"{x[0]:+6.2f} [{x[1]:+6.2f},{x[2]:+6.2f}]" if np.isfinite(x[1]) else f"{x[0]:+6.2f}"


def table(title, groups, rng, extra=None):
    log(f"\n{title}")
    log(f"  {'group':<40}{'contracts':>10}{'players':>9}{'with term: mean':>26}{'median':>8}{'without term: mean':>27}{'median':>8}"
        + (f"{extra[0]:>24}" if extra else ""))
    for lab, g in groups:
        if len(g) == 0:
            continue
        a, b = bm(g["v"], g["player_id"], rng), bm(g["vf"], g["player_id"], rng)
        log(f"  {lab:<40}{len(g):>10}{g['player_id'].nunique():>9}{f3(a):>26}{g['v'].median():>+8.2f}{f3(b):>27}{g['vf'].median():>+8.2f}"
            + (f"{g[extra[1]].mean():>+24.2f}" if extra else ""))
        ROWS.append({"table": title[:60], "group": lab, "n": len(g), "players": g["player_id"].nunique(), "term_in_mean": a[0],
                     "term_in_lo": a[1], "term_in_hi": a[2], "term_in_median": g["v"].median(), "term_free_mean": b[0],
                     "term_free_lo": b[1], "term_free_hi": b[2], "term_free_median": g["vf"].median(),
                     **({extra[1]: g[extra[1]].mean()} if extra else {})})


def main():
    rng = np.random.default_rng(SEED)
    log(SCRIPT_VERSION)
    log(f"  reads {OUTPUT_DIR}")
    pc = SFP.price_constants()
    gamma = float(pc["gamma_term"]) if isinstance(pc, dict) else float(SFP.XNPV1_RATE["gamma_term"])
    log(f"  the term premium in force: {gamma:.10f} of a cap a season per year of term = ${gamma * CAP_NOW / 1e6:.3f}M at the 2025-26 cap")
    pan = pd.read_csv(OUTPUT_DIR / "contract_npv_panel.csv", low_memory=False)
    sp = pd.read_csv(OUTPUT_DIR / "contract_level_spine.csv",
                     usecols=["contract_id", "nhl_id", "start_season_year", "pp_length", "pp_expiry", "birthdate"])
    c, _ = CS.load_contracts()
    c = c.drop_duplicates("contract_id")[["contract_id", "signing_status", "contract_level"]]
    d = pan.merge(sp, on="contract_id").merge(c, on="contract_id", how="left")
    d = d[d["valuation_season"].between(2018, 2025)].copy()
    scale = np.array([CAP_NOW / CAP[int(y)] for y in d["valuation_season"]]) / 1e6
    d["v"], d["vf"] = d["npv_total"] * scale, d["npv_total_term_free"] * scale
    d["T"], d["R"] = d["pp_length"], d["seasons_remaining"]
    d["k"] = d["valuation_season"] - d["start_season_year"]
    d["rule_M"] = -gamma * d["R"] * (d["T"] - d["R"]).clip(lower=0) * CAP_NOW / 1e6      # the term rule's shortfall, at the 2025-26 cap
    d["how"] = np.where(d["contract_level"] == "entry_level", "entry-level", d["signing_status"].fillna("not recorded"))
    d["how"] = d["how"].replace({"UFA Group 6": "UFA", "UFA-Group6": "UFA", "UFA no QO": "UFA"})
    sk = d[d["path"] == "xNPV 1"].copy()
    gk = d[d["path"] != "xNPV 1"]
    log(f"  panel pages 2018-2025: {len(sk)} skater contract-pages ({sk['contract_id'].nunique()} contracts, {sk['player_id'].nunique()} players); "
        f"goaltenders {len(gk)} contract-pages")
    odd = sk[(sk["k"] < 0) | (sk["R"] > sk["T"])]
    log(f"  contract-pages before the contract's first season or with more seasons left than its length (extensions valued early): {len(odd)}, left out")
    sk = sk[(sk["k"] >= 0) & (sk["R"] <= sk["T"])]

    # ---- 1. at signing ---------------------------------------------------------------------------------------------------
    s0 = sk[(sk["k"] == 0) & (sk["R"] == sk["T"])]
    table("1. EACH SKATER CONTRACT AT ITS SIGNING PAGE (valued whole)",
          [("all", s0)] + [(f"signed as {h}", s0[s0["how"] == h]) for h in ("UFA", "RFA", "entry-level", "not recorded")]
          + [("standard contracts (UFA and RFA): 1 season", s0[s0["how"].isin(["UFA", "RFA"]) & (s0["T"] == 1)]),
             ("  2 seasons", s0[s0["how"].isin(["UFA", "RFA"]) & (s0["T"] == 2)]),
             ("  3 or 4 seasons", s0[s0["how"].isin(["UFA", "RFA"]) & s0["T"].isin([3, 4])]),
             ("  5 or 6 seasons", s0[s0["how"].isin(["UFA", "RFA"]) & s0["T"].isin([5, 6])]),
             ("  7 or 8 seasons", s0[s0["how"].isin(["UFA", "RFA"]) & (s0["T"] >= 7)])], rng)
    g0 = gk[(gk["k"] == 0) & (gk["R"] == gk["T"])]
    table("   goaltenders at signing (their own line; shown for comparison)", [("all goaltender contracts", g0)], rng)

    # ---- 2. as they age --------------------------------------------------------------------------------------------------
    std = sk[sk["how"].isin(["UFA", "RFA"]) & (sk["T"] >= 2)]
    table("2. STANDARD CONTRACTS OF TWO OR MORE SEASONS, BY SEASONS SINCE SIGNING",
          [(f"{k} seasons since signing" if k else "at signing", std[std["k"] == k]) for k in range(0, 7)],
          rng, extra=("the term rule alone", "rule_M"))
    long_ = std[std["T"] >= 5]
    table("2. THE SAME, CONTRACTS OF FIVE OR MORE SEASONS",
          [(f"{k} seasons since signing" if k else "at signing", long_[long_["k"] == k]) for k in range(0, 7)],
          rng, extra=("the term rule alone", "rule_M"))
    # each contract against its own signing page (contracts seen at signing and later)
    base = std[std["k"] == 0].set_index("contract_id")[["v", "vf"]]
    later = std[(std["k"] > 0) & std["contract_id"].isin(base.index)].copy()
    later["dv"] = later["v"] - later["contract_id"].map(base["v"])
    later["dvf"] = later["vf"] - later["contract_id"].map(base["vf"])
    log("\n2. EACH MULTI-YEAR CONTRACT AGAINST ITS OWN SIGNING PAGE (contracts seen at both)")
    log(f"  {'seasons since signing':<26}{'contracts':>10}{'change, with term':>26}{'change, without term':>26}{'the term rule alone':>22}")
    for k in range(1, 6):
        g = later[later["k"] == k]
        if len(g) == 0:
            continue
        a, b = bm(g["dv"], g["player_id"], rng), bm(g["dvf"], g["player_id"], rng)
        log(f"  {k:<26}{len(g):>10}{f3(a):>26}{f3(b):>26}{g['rule_M'].mean():>+22.2f}")
        ROWS.append({"table": "2. change from the signing page", "group": f"{k} seasons since signing", "n": len(g), "term_in_mean": a[0],
                     "term_in_lo": a[1], "term_in_hi": a[2], "term_free_mean": b[0], "term_free_lo": b[1], "term_free_hi": b[2],
                     "rule_M": g["rule_M"].mean()})

    # ---- 3. traded against not traded --------------------------------------------------------------------------------------
    con = sqlite3.connect(OUTPUT_DIR / "trades_extended.db")
    ta = pd.read_sql("select a.player_name, t.trade_date from trade_assets a join trades t using(trade_id) where a.asset_type = 'player'", con)
    ta["k"], ta["d"] = ta["player_name"].map(key), pd.to_datetime(ta["trade_date"])
    tk = {k: g["d"].values for k, g in ta.groupby("k")}
    sk["nk"] = sk["full_name"].map(key)

    def traded(k, y):
        x = tk.get(k)
        return False if x is None else bool(((x >= np.datetime64(f"{y}-07-01")) & (x < np.datetime64(f"{y + 1}-07-01"))).any())
    sk["traded"] = [traded(k, int(y)) for k, y in zip(sk["nk"], sk["valuation_season"])]
    st = sk[sk["how"].isin(["UFA", "RFA"])]
    log(f"\n3. standard skater contract-pages: {len(st)}; the player traded within twelve months of the page: {int(st['traded'].sum())} ({st['traded'].mean():.1%})")
    grp = []
    for lab, m in (("1 season left", st["R"] == 1), ("2 seasons left", st["R"] == 2), ("3 or 4 seasons left", st["R"].isin([3, 4])),
                   ("5 or more seasons left", st["R"] >= 5)):
        grp += [(f"{lab}: traded", st[m & st["traded"]]), (f"{lab}: not traded", st[m & ~st["traded"]])]
    table("3. TRADED IN THE NEXT TWELVE MONTHS AGAINST NOT, AT THE SAME SEASONS LEFT", grp, rng, extra=("the term rule alone", "rule_M"))
    log("  the gap, traded minus not traded (resampling players):")
    for lab, m in (("1 season left", st["R"] == 1), ("2 seasons left", st["R"] == 2), ("3 or 4 seasons left", st["R"].isin([3, 4])),
                   ("5 or more seasons left", st["R"] >= 5)):
        g = st[m]
        ids = g["player_id"].unique()
        by = {p: x for p, x in g.groupby("player_id")}
        out = {"v": [], "vf": []}
        for _ in range(500):
            x = pd.concat([by[p] for p in ids[rng.integers(0, len(ids), len(ids))]])
            for c_ in out:
                out[c_].append(x.loc[x["traded"], c_].mean() - x.loc[~x["traded"], c_].mean())
        e = {c_: g.loc[g["traded"], c_].mean() - g.loc[~g["traded"], c_].mean() for c_ in out}
        log(f"    {lab:<24} with term {e['v']:+.2f} [{np.nanpercentile(out['v'], 2.5):+.2f},{np.nanpercentile(out['v'], 97.5):+.2f}]   "
            f"without term {e['vf']:+.2f} [{np.nanpercentile(out['vf'], 2.5):+.2f},{np.nanpercentile(out['vf'], 97.5):+.2f}]")
        ROWS.append({"table": "3. traded minus not traded", "group": lab, "n": len(g), "term_in_mean": e["v"], "term_free_mean": e["vf"]})

    # ---- 4. the traded assets on both lines --------------------------------------------------------------------------------
    tp = pd.read_csv(OUTPUT_DIR / "traded_player_values.csv")
    tp = tp[tp["npv_total"].notna() & tp["npv_total_term_free"].notna()]
    sc = np.array([CAP_NOW / CAP[int(y)] for y in tp["valuation_page"]]) / 1e6
    a, b = tp["npv_total"] * sc, tp["npv_total_term_free"] * sc
    tv = pd.read_csv(OUTPUT_DIR / "trade_asset_values.csv")
    pm = tv[tv["source"].isin(["player model", "player model, rights"])]["value_2025_cap_M"].sum()
    log(f"\n4. THE TRADED PLAYERS (traded_player_values.csv, pages 2018 on; {len(tp)} assets with both lines): total with term ${a.sum():,.1f}M, "
        f"without term ${b.sum():,.1f}M; mean {a.mean():+.2f} against {b.mean():+.2f}; median {a.median():+.2f} against {b.median():+.2f}")
    log(f"   (check: the same assets in trade_asset_values.csv, with term, total ${pm:,.1f}M)")
    for lab, m in (("1 contract season", tp["n_contract_seasons"] == 1), ("2", tp["n_contract_seasons"] == 2), ("3 or more", tp["n_contract_seasons"] >= 3)):
        log(f"   {lab:<20} {int(m.sum()):>4} assets: with term ${a[m].sum():>8,.1f}M (mean {a[m].mean():+.2f}); without ${b[m].sum():>8,.1f}M (mean {b[m].mean():+.2f})")
        ROWS.append({"table": "4. traded players", "group": lab, "n": int(m.sum()), "term_in_mean": a[m].mean(), "term_free_mean": b[m].mean()})
    # ---- 5. what the term rule does to the traded players and to the back-test's groups (APPROXIMATE, not a re-run) -------
    # For each traded skater contract (pages 2018 on), the rule's shortfall is added back: gamma x (T - R) of a cap on each
    # of its R seasons (the trade season by its share left), as if every remaining season were priced on the contract's
    # ORIGINAL term. No chance of playing and no floor are applied, and the same amount is added to the forecast and to the
    # outcome (the back-test prices a played season on the term its forecast used, backtest.py line 482), so this is an
    # upper bound on the shift and leaves outcome minus forecast unchanged. Goaltenders, the 2017 page, rights and buried
    # contracts are not adjusted.
    ss = pd.read_csv(OUTPUT_DIR / "contract_season_spine.csv", low_memory=False,
                     usecols=["nhl_id", "season_start", "pp_first_season", "pp_signed_end", "pp_signing_date", "position"])
    ss["signed"] = pd.to_datetime(ss["pp_signing_date"])
    by_ps = {k_: g_ for k_, g_ in ss.groupby(["nhl_id", "season_start"])}
    tpa = pd.read_csv(OUTPUT_DIR / "traded_player_values.csv")
    tpa = tpa[tpa["npv_total"].notna() & tpa["n_contract_seasons"].notna()].copy()
    add = {}
    for r in tpa.itertuples():
        c_ = by_ps.get((r.nhl_id, r.valuation_page))
        if c_ is None:
            continue
        dt = pd.Timestamp(r.trade_date)
        c_ = c_[c_["signed"] <= dt] if (c_["signed"] <= dt).any() else c_
        x = c_.sort_values("signed").iloc[0]
        if x["position"] == "Goaltender":
            continue
        T_, R_ = int(x["pp_signed_end"]) - int(x["pp_first_season"]) + 1, int(r.n_contract_seasons)
        sh = r.season_share if pd.notna(r.season_share) else 1.0
        add[r.asset_id] = gamma * max(T_ - R_, 0) * (sh + R_ - 1) * CAP_NOW / 1e6
    adds = pd.Series(add)
    v_now = tpa.set_index("asset_id").loc[adds.index, "npv_total"] * [CAP_NOW / CAP[int(y)] / 1e6 for y in tpa.set_index("asset_id").loc[adds.index, "valuation_page"]]
    log(f"\n5. THE TERM RULE AND THE TRADED SKATERS (approximate): {len(adds)} traded skater contracts; total value as the model has it "
        f"${v_now.sum():,.1f}M; the rule's shortfall ${-adds.sum():,.1f}M; with every season priced on the contract's original term about "
        f"${(v_now + adds).sum():,.1f}M (mean {(v_now + adds).mean():+.2f}, median {(v_now + adds).median():+.2f} a contract)")
    bs = pd.read_csv(OUTPUT_DIR / "backtest_sides.csv")
    ba = pd.read_csv(OUTPUT_DIR / "backtest_assets.csv")
    con2 = sqlite3.connect(OUTPUT_DIR / "trades_extended.db")
    legs = pd.read_sql("select trade_id, acquiring_team from trade_legs", con2)
    clubs = legs.groupby("trade_id")["acquiring_team"].apply(lambda x: sorted(set(x))).to_dict()
    ba = ba[ba["asset_type"] == "player"].copy()
    ba["add"] = ba["asset_id"].map(adds).fillna(0.0)
    ba["sender"] = [r.from_team if pd.notna(r.from_team) else next((c for c in clubs[r.trade_id] if c != r.acquiring_team), None)
                    for r in ba.itertuples()]
    got = ba.groupby(["trade_id", "acquiring_team"])["add"].sum()
    gave = ba.groupby(["trade_id", "sender"])["add"].sum()
    bs["shift"] = [got.get((t, c), 0.0) - gave.get((t, c), 0.0) for t, c in zip(bs["trade_id"], bs["club"])]
    bs = bs[bs["complete"]]
    log("   the back-test's groups, all complete trades 2017-2026: mean per club side as run, and with the shortfall added back")
    log(f"   {'group':<58}{'sides':>6}{'priced':>9}{'-> approx.':>12}{'outcome':>10}{'-> approx.':>12}")
    for lab, m in (("received the picks and prospects for players (C1)", bs["g_futures"]),
                   ("higher in the standings, in-season (C2)", bs["g_buyer"]),
                   ("retained salary (C4)", bs["g_retained"]),
                   ("received a player with a clause (C6)", bs["g_clause"])):
        g = bs[m]
        log(f"   {lab:<58}{len(g):>6}{g['net_M'].mean():>+9.2f}{(g['net_M'] + g['shift']).mean():>+12.2f}{g['out_net_M'].mean():>+10.2f}"
            f"{(g['out_net_M'] + g['shift']).mean():>+12.2f}")
        ROWS.append({"table": "5. groups with the term shortfall added back", "group": lab, "n": len(g), "term_in_mean": g["net_M"].mean(),
                     "term_free_mean": np.nan, "priced_adjusted": (g["net_M"] + g["shift"]).mean(), "outcome": g["out_net_M"].mean(),
                     "outcome_adjusted": (g["out_net_M"] + g["shift"]).mean()})
    pd.DataFrame(ROWS).to_csv(OUTPUT_DIR / "contract_value_by_age.csv", index=False)
    (OUTPUT_DIR / "contract_value_by_age_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
