"""
groups_any.py - the five back-test categories built from one player, each with an any-player version (Thomas, 2026-11-18:
"yes check all other categories for the any player version"; declared in 40_DOCS/Backtest_Protocol.md before it was built.
Report only.)

THE FIVE (groups_clustered.py's flags built from one player, and their any-player versions):
  rental     one player: the main player (highest cap hit received) is in his final season, unrestricted at expiry, and
             the trade is in-season. Any: any player received is.
  age 28-31, age 32+, defenceman
             one player: the main player's age at the trade date / position. Any: any player received.
  new GM     one player: in a general manager's first 365 days, the highest-paid player the club SENT signed before the
             manager's first day (backtest_cuts_more.py cut GM). Any: any player sent did, the manager in his first 365 days.
Two of groups_clustered's categories are already any-player (the clause, backtest.py C6; a former top-15 pick below the
benchmark, backtest_cuts.py 5b) and seven are not about a player; none of them changes.

EACH PLAYER'S FACTS, as the one-player flags build them:
  players    backtest_assets.csv rows with asset_type "player" and source starting "player model" or "buried"
  age        contract_level_spine.csv birthdate to the trade date, years of 365.25 days (backtest_cuts.py)
  status     backtest_cuts.py's status(): the contract running at the page (season spine at (nhl_id, page), earliest
             signed on or before the trade date, else the earliest); the 2017 page from page_2017_values.csv; rights only
             is not a contract; a rental is "final season, unrestricted at expiry" and the trade in the regular season
  sender     from_team in a trade of three or more clubs, else the other club (backtest_cuts_more.load_sides)
  new GM     backtest_cuts_more_gm_sides.csv's new_gm (first 365 days) and days (the manager's start = trade date - days);
             a player sent counts when his contract's signing date is before that start
A fact unknown for a player counts as "no" for him.

GUARDS: (1) groups_clustered.sides() gives its recorded group sizes and means back (defenceman 181 sides, -0.99 priced,
declared window); (2) on sides with exactly one player received (one player sent, for the manager) each any-player flag
equals the one-player flag.

REPORTS, standard errors clustered by trade, beside the one-player figures:
  1 each group's mean trade-day grade and realized value (WAR, Game Value), declared window
  2 the outcome-on-price coefficient c (the group beyond its price), declared window, WAR and Game Value
  3 the joint regression (groups_clustered.py part 4's design), all trades, the five replaced together

INPUTS: OUTPUT_DIR/_extended_run (the back-test's sides and assets, spines, page_2017_values.csv, gm sides, trades db)
OUTPUTS: OUTPUT_DIR/groups_any_log.txt, groups_any.csv
"""
import importlib.util
import os
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
EXT = OUTPUT_DIR / "_extended_run"
SCRIPT_VERSION = "groups_any.py v1.0 (2026-11-18)"
DECLARED_END = "2022-03-28"
LOG, OUT = [], []
FIVE = [("rental", "t_rental"), ("aged 28 to 31", "t_age28"), ("aged 32 or over", "t_age32"),
        ("a defenceman", "t_def"), ("sold under a new GM, predecessor's contract", "t_newgm")]


def log(s=""):
    print(s)
    LOG.append(s)


def player_rows():
    """Every player asset with its receiver, sender, age, position, rental status and contract signing date."""
    a = pd.read_csv(EXT / "backtest_assets.csv")
    pv = pd.read_csv(EXT / "prospect_values.csv", low_memory=False)[["asset_id", "nhl_id", "cap_hit"]].drop_duplicates("asset_id")
    con = sqlite3.connect(EXT / "trades_extended.db")
    legs = pd.read_sql("select trade_id, acquiring_team from trade_legs", con)
    clubs = legs.groupby("trade_id")["acquiring_team"].apply(lambda x: sorted(set(x))).to_dict()
    a["sender"] = [r.from_team if pd.notna(r.from_team) else next((c for c in clubs.get(r.trade_id, []) if c != r.acquiring_team), None)
                   for r in a.itertuples()]
    pl = a[(a["asset_type"] == "player") & a["source"].str.startswith(("player model", "buried"))].merge(pv, on="asset_id", how="left")
    pl["date"] = pd.to_datetime(pl["trade_date"])
    ls = pd.read_csv(EXT / "contract_level_spine.csv", usecols=["nhl_id", "birthdate"]).drop_duplicates("nhl_id")
    pl["age"] = (pl["date"] - pd.to_datetime(pl["nhl_id"].map(ls.set_index("nhl_id")["birthdate"]))).dt.days / 365.25
    ss = pd.read_csv(EXT / "contract_season_spine.csv", low_memory=False)
    ss["signed"] = pd.to_datetime(ss["pp_signing_date"])
    by = {k: g for k, g in ss.groupby(["nhl_id", "season_start"])}
    p17 = pd.read_csv(EXT / "page_2017_values.csv").set_index("asset_id")
    status = []
    for r in pl.itertuples():                       # backtest_cuts.py status(), the status label only, and the signing date
        if r.source == "player model, rights":
            status.append("rights only"); continue
        if r.valuation_page == 2017:
            if r.asset_id not in p17.index or pd.isna(p17.at[r.asset_id, "contract_last_season"]):
                status.append("unknown"); continue
            x = p17.loc[r.asset_id]
            left, exp, elc = int(x["contract_last_season"]) - 2017 + 1, str(x["expiry"]), "Entry" in str(x["contract"])
            exp = "RFA" if exp.startswith("RFA") else "UFA"
        else:
            g = by.get((r.nhl_id, r.valuation_page)) if pd.notna(r.nhl_id) else None
            if g is None:
                status.append("unknown"); continue
            g = g[g["signed"] <= r.date] if (g["signed"] <= r.date).any() else g
            x = g.sort_values("signed").iloc[0]
            left, exp, elc = int(x["pp_signed_end"]) - int(r.valuation_page) + 1, str(x["pp_expiry"]), x["cs_entry_level"] == 1
            exp = "RFA" if exp == "RFA" else "UFA"
        if elc:
            status.append("entry-level contract")
        elif left <= 1:
            status.append("final season, restricted at expiry" if exp == "RFA" else "final season, unrestricted at expiry")
        else:
            status.append("two or more seasons left")
    pl["cstatus"] = status
    # the signing date as backtest_cuts_more.py cut GM reads it: the season spine at (nhl_id, page) for every page, the 2017
    # page included (status() above reads the 2017 page from page_2017_values.csv, which has no signing date)
    sg = []
    for r in pl.itertuples():
        g = by.get((r.nhl_id, int(r.valuation_page))) if pd.notna(r.nhl_id) else None
        if g is None:
            sg.append(pd.NaT); continue
        g = g[g["signed"] <= r.date] if (g["signed"] <= r.date).any() else g
        sg.append(g.sort_values("signed").iloc[0]["signed"])
    pl["signed"] = sg
    return pl


def main():
    log(SCRIPT_VERSION)
    spec = importlib.util.spec_from_file_location("groups_clustered", Path(__file__).resolve().parent / "groups_clustered.py")
    GC = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(GC)
    GC.OUTPUT_DIR = EXT
    t = GC.sides()
    key = ["trade_id", "club"]
    dec = t["trade_date"] <= DECLARED_END
    # GUARD 1: groups_clustered's recorded defenceman figures (declared window)
    x = t[dec & t["t_def"]]
    assert len(x) == 181 and abs(x["net_M"].mean() + 0.99) < 0.005, (len(x), x["net_M"].mean())
    log("  check 1: groups_clustered.sides() gives its recorded figures back (defenceman, 181 sides, -0.99 priced) (PASS)")

    pl = player_rows()
    # in-season: the asset row's own during_regular_season (backtest_assets.csv; the trade's, the same on every row)
    rec = pd.DataFrame({"trade_id": pl["trade_id"], "club": pl["acquiring_team"]})
    rec["a_rental"] = ((pl["cstatus"] == "final season, unrestricted at expiry") & pl["during_regular_season"].fillna(False).astype(bool)).astype(int)
    rec["a_age28"] = pl["age"].between(28, 32, inclusive="left").astype(int)
    rec["a_age32"] = (pl["age"] >= 32).astype(int)
    rec["a_def"] = (pl["pos"] == "D").astype(int)
    anyr = rec.groupby(key)[["a_rental", "a_age28", "a_age32", "a_def"]].max()
    nrec = rec.groupby(key).size().rename("n_received_players")
    # the manager: a player sent signed before the manager's first day, the manager in his first 365 days
    gm = pd.read_csv(EXT / "backtest_cuts_more_gm_sides.csv")
    gm = gm.merge(t[key + ["trade_date"]], on=key, how="left")
    gm["since"] = pd.to_datetime(gm["trade_date"]) - pd.to_timedelta(gm["days"], unit="D")
    snt = pl[["trade_id", "sender", "signed"]].rename(columns={"sender": "club"}).merge(gm[key + ["new_gm", "since"]], on=key, how="inner")
    snt["a_newgm"] = (snt["new_gm"].astype(bool) & (snt["signed"] < snt["since"])).astype(int)
    anys = snt.groupby(key)["a_newgm"].max()
    nsent = pl.groupby(["trade_id", "sender"]).size().rename("n_sent_players")
    nsent.index = nsent.index.set_names(key)
    t = t.join(anyr, on=key).join(anys, on=key).join(nrec, on=key).join(nsent, on=key)
    for c in ("a_rental", "a_age28", "a_age32", "a_def", "a_newgm"):
        t[c] = t[c].fillna(0).astype(bool)
    pairs = [("rental", "t_rental", "a_rental", "n_received_players"), ("aged 28 to 31", "t_age28", "a_age28", "n_received_players"),
             ("aged 32 or over", "t_age32", "a_age32", "n_received_players"), ("a defenceman", "t_def", "a_def", "n_received_players"),
             ("sold under a new GM, predecessor's contract", "t_newgm", "a_newgm", "n_sent_players")]
    # GUARD 2: one player received (sent): the flags agree
    log("  check 2: sides with exactly one player received (sent, for the manager): any-player flag against the one-player flag")
    bad = {}
    for lab, o, n_, cnt in pairs:
        one = t[t[cnt] == 1]
        bad[lab] = int((one[o].astype(bool) != one[n_]).sum())
        log(f"    {lab:<46} {len(one):>5} sides, {bad[lab]} differ")
    assert all(v == 0 for v in bad.values()), bad
    log("  (PASS)")
    log("\n  clubs in each group, all trades: one player -> any player")
    for lab, o, n_, _ in pairs:
        log(f"    {lab:<46}{int(t[o].sum()):>6} -> {int(t[n_].sum()):>6}   (declared window {int(t.loc[dec, o].sum())} -> {int(t.loc[dec, n_].sum())})")

    # ---- 1 group means, declared window ------------------------------------------------------------------------------------
    d = t[dec]
    log("\n1. GROUP MEANS, declared window ($M a club; mean (clustered se) p): one player -> any player")
    log(f"  {'group':<46}" + "".join(f"{y:>44}" for y, _ in GC.YS))
    for lab, o, n_, _ in pairs:
        cells = []
        for ylab, y in GC.YS:
            r = []
            for rule, f in (("one player", o), ("any player", n_)):
                x = d[d[f].astype(bool)]
                b, se, lo, hi, p = GC.clustered_mean(x[y].to_numpy(float), x["trade_id"].to_numpy())
                r.append(f"{b:+.2f} ({se:.2f}) p={p:.3f}")
                OUT.append({"part": "group mean, declared window", "group": lab, "rule": rule, "outcome": ylab, "n": len(x),
                            "estimate": b, "se": se, "p": p})
            cells.append(" -> ".join(r))
        log(f"  {lab:<46}" + "".join(f"{c:>44}" for c in cells))
        log(f"  {'':<46}{'sides: ' + str(int(d[o].sum())) + ' -> ' + str(int(d[n_].sum())):>44}")

    # ---- 2 beyond its price ------------------------------------------------------------------------------------------------
    log("\n2. OUTCOME ON PRICE, declared window: c, the group beyond what its price predicts (clustered by trade): one -> any")
    for ylab, y in GC.YS[1:]:
        log(f"  outcome: {ylab}")
        for lab, o, n_, _ in pairs:
            r = []
            for rule, f in (("one player", o), ("any player", n_)):
                X = pd.DataFrame({"const": 1.0, "priced": d["net_M"], "G": d[f].astype(float), "GxP": d[f].astype(float) * d["net_M"]})
                m = sm.OLS(d[y], X).fit(cov_type="cluster", cov_kwds={"groups": d["trade_id"]})
                r.append(f"{m.params['G']:+.2f} ({m.bse['G']:.2f}) p={m.pvalues['G']:.3f}")
                OUT.append({"part": "beyond its price, declared window", "group": lab, "rule": rule, "outcome": ylab,
                            "estimate": m.params["G"], "se": m.bse["G"], "p": m.pvalues["G"]})
            log(f"    {lab:<46}{' -> '.join(r)}")

    # ---- 3 the joint regression, all trades ---------------------------------------------------------------------------------
    n = t.groupby("trade_id")["club"].transform("size")
    two = t[n == 2].sort_values(key)
    A = two.groupby("trade_id").nth(0).set_index("trade_id")
    B = two.groupby("trade_id").nth(1).set_index("trade_id")
    base = [g for _, g in GC.GROUPS[:-1]]
    swap = {o: n_ for _, o, n_, _ in pairs}
    nm = dict((g, l) for l, g in GC.GROUPS)
    fits = {}
    for rule, cols in (("one player", base), ("any player", [swap.get(g, g) for g in base])):
        X = pd.DataFrame({g: A[g].astype(int) - B[g].astype(int) for g in cols}, index=A.index)
        X = X.loc[:, (X != 0).sum() >= 5]
        fits[rule] = {y: sm.OLS(A[y], X).fit(cov_type="HC1") for _, y in GC.YS}
    log(f"\n3. THE JOINT REGRESSION, all trades, {len(A)} two-team trades, robust standard errors: one player -> any player")
    log(f"  {'characteristic':<46}" + "".join(f"{y:>44}" for y, _ in GC.YS))
    for g in base:
        g2 = swap.get(g, g)
        cells = []
        for ylab, y in GC.YS:
            m1, m2 = fits["one player"][y], fits["any player"][y]
            if g not in m1.params.index or g2 not in m2.params.index:
                cells.append("dropped"); continue
            cells.append(f"{m1.params[g]:+.2f} ({m1.bse[g]:.2f}) -> {m2.params[g2]:+.2f} ({m2.bse[g2]:.2f}) p={m2.pvalues[g2]:.3f}")
            for rule, m, k in (("one player", m1, g), ("any player", m2, g2)):
                OUT.append({"part": "joint, all trades", "group": nm[g], "rule": rule, "outcome": ylab,
                            "estimate": m.params[k], "se": m.bse[k], "p": m.pvalues[k]})
        log(f"  {nm[g]:<46}" + "".join(f"{c:>44}" for c in cells))
    pd.DataFrame(OUT).to_csv(OUTPUT_DIR / "groups_any.csv", index=False)
    (OUTPUT_DIR / "groups_any_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
