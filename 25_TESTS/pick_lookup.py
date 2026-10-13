"""
pick_lookup.py -- answer questions about the pick curve on the spot (meeting aid, 2026-10-13).

Reads the saved outputs of the live draft scripts; recomputes nothing expensive and changes nothing.
Run 20_CODE/pick_curve.py and 20_CODE/traded_pick_values.py first if the outputs are missing or stale
(each output's first log line names the script version that wrote it).

USAGE (from the repo root, in PowerShell or any shell):
  python 25_TESTS/pick_lookup.py pick 16            value of the 16th pick (star probability x star value)
  python 25_TESTS/pick_lookup.py round 2            average value of a 2nd-round pick (32 teams; --teams 31)
  python 25_TESTS/pick_lookup.py slot 1             the eleven players taken at a pick, 2007-2017, and their surplus
  python 25_TESTS/pick_lookup.py player "Point"     a drafted player's surplus, season by season (name contains)
  python 25_TESTS/pick_lookup.py draft 2015         one draft: its own star value, best and worst players
  python 25_TESTS/pick_lookup.py team TOR           picks originally Toronto's that were traded, and their values
  python 25_TESTS/pick_lookup.py date 2019-02-25    picks traded on a date
  python 25_TESTS/pick_lookup.py regression         Table 2: surplus on star probability (with pick number; with a constant)
  python 25_TESTS/pick_lookup.py trend              the trend in the star value across drafts, with and without 2015-16
  python 25_TESTS/pick_lookup.py stars              share of surplus produced by stars
  python 25_TESTS/pick_lookup.py persistence        how a team's draft slot carries to the next drafts
  python 25_TESTS/pick_lookup.py versions           which script version wrote each output read here

Money is in millions of dollars at the 2025-26 cap ($95.5M). "Star value" = the surplus a pick would be worth
if its player were certain to become a star; a pick's value = star value x Bacon's star probability for its slot.
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

load_dotenv()
OUT, SRC = Path(os.environ["OUTPUT_DIR"]), Path(os.environ["SOURCE_DIR"])
pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)


def need(name):
    p = OUT / name
    if not p.exists():
        sys.exit(f"missing {p}: run 20_CODE/pick_curve.py and 20_CODE/traded_pick_values.py first")
    return p


def bacon():
    return pd.read_csv(SRC / "draft_slot_baseline.csv").set_index("draft_pick")["p_star"]


def star_values():
    sc = pd.read_csv(need("pick_curve_scales.csv")).set_index("scale_kind")
    return float(sc.loc["main", "scale_M"]), float(sc.loc["sensitivity", "scale_M"])


def players():
    d = pd.read_csv(need("pick_curve_players.csv"))
    d["surplus_M"] = d["surplus"] / 1e6
    return d


def year_cols(frame):
    yrs = frame["draftYear"].values
    cl = sorted(set(yrs))
    return [(yrs == c).astype(float) - (yrs == cl[-1]).astype(float) for c in cl[:-1]]


def cmd_pick(a):
    b, (sv, ss) = bacon(), star_values()
    p = float(b[a.n])
    print(f"Pick #{a.n}: star probability {100 * p:.1f}%")
    print(f"  value  = {p:.4f} x star value {sv:.2f} = ${p * sv:.2f}M")
    print(f"  sensitivity (star value without the 2015 and 2016 drafts, {ss:.2f}): ${p * ss:.2f}M")


def cmd_round(a):
    b, (sv, ss) = bacon(), star_values()
    slots = range((a.r - 1) * a.teams + 1, a.r * a.teams + 1)
    p = float(np.mean([b[s] for s in slots]))
    print(f"Round {a.r} with {a.teams} teams (picks {slots[0]}-{slots[-1]}): average star probability {100 * p:.2f}%")
    print(f"  value ${p * sv:.2f}M  (sensitivity ${p * ss:.2f}M)")


def cmd_slot(a):
    d, b, (sv, _) = players(), bacon(), star_values()
    s = d[d["pick"] == a.n].sort_values("draftYear")
    print(s[["draftYear", "player", "position", "nhl_seasons", "war", "route", "surplus_M"]].round(2).to_string(index=False))
    print(f"\n  actual average ${s['surplus_M'].mean():.2f}M over {len(s)} players; the curve says "
          f"${sv * float(b[a.n]):.2f}M (star probability {100 * float(b[a.n]):.1f}% x {sv:.2f})")


def cmd_player(a):
    d = players()
    m = d[d["player"].str.contains(a.name, case=False, na=False)]
    if m.empty:
        sys.exit(f"no drafted player 2007-2017 matches '{a.name}'")
    se = pd.read_csv(need("pick_curve_seasons.csv"))
    for r in m.itertuples():
        print(f"\n{r.player} ({r.position}), {r.draftYear} #{r.pick} by {r.team}; rights held through "
              f"{int(r.window_end) - 1}-{str(int(r.window_end))[2:]}; route: {r.route}")
        s = se[(se["draftYear"] == r.draftYear) & (se["pick"] == r.pick)].copy()
        if s.empty:
            print("  no NHL season while his drafting club held his rights: surplus $0")
            continue
        s["value_M"], s["cost_M"] = s["value_share"] * 95.5, s["cost_share"] * 95.5
        s["surplus_M"] = s["value_M"] - s["cost_M"]
        s["season"] = s["season"].map(lambda y: f"{y}-{str(y + 1)[2:]}")
        s["contract"] = np.where(s["in_entry_level"], "entry-level", "qualifying offer")
        print(s[["season", "gp", "war_82", "contract", "value_M", "cost_M", "surplus_M"]].round(2).to_string(index=False))
        note = " (counted as zero: rights lapsed)" if r.surplus == 0 and r.surplus_before_rights != 0 else ""
        print(f"  total surplus ${r.surplus_before_rights / 1e6:.2f}M{note}")


def cmd_draft(a):
    d = players()
    s = d[d["draftYear"] == a.year]
    if s.empty:
        sys.exit("drafts 2007-2017 only")
    # Same model as Figure 2 of "Valuing Draft Picks" (pick_summary_figures.py): one star value per draft,
    # fitted jointly with the draft-year indicators, robust standard errors.
    cl = sorted(d["draftYear"].unique())
    yrs = d["draftYear"].values
    X = np.column_stack([d["p_star"].values * (yrs == c) for c in cl] + year_cols(d))
    m = sm.OLS(d["surplus_M"].values, X).fit(cov_type="HC1")
    k = cl.index(a.year)
    sv, _ = star_values()
    print(f"{a.year} draft: {len(s)} picks, {int((s['nhl_seasons'] > 0).sum())} played an NHL game; "
          f"mean surplus ${s['surplus_M'].mean():.2f}M; star value fitted on this draft {m.params[k]:.2f} "
          f"(se {m.bse[k]:.2f}; Figure 2); all drafts {sv:.2f}")
    print("\n  largest surpluses:")
    print(s.nlargest(8, "surplus_M")[["pick", "player", "team", "surplus_M"]].round(2).to_string(index=False))
    print("\n  smallest:")
    print(s.nsmallest(4, "surplus_M")[["pick", "player", "team", "surplus_M"]].round(2).to_string(index=False))


def traded():
    t = pd.read_csv(need("traded_pick_values.csv"))
    return t[["trade_date", "trade_id", "original_team", "pick_year", "pick_round", "method", "projected_slot",
              "actual_slot", "star_chance", "value_M", "value_sensitivity_M", "conditional"]]


def cmd_team(a):
    t = traded()
    s = t[t["original_team"].str.upper() == a.team.upper()].sort_values("trade_date")
    print(s.round(3).to_string(index=False))
    print(f"\n  {len(s)} picks, total ${s['value_M'].sum():.2f}M (sensitivity ${s['value_sensitivity_M'].sum():.2f}M)")


def cmd_date(a):
    t = traded()
    s = t[t["trade_date"] == a.date]
    print(s.round(3).to_string(index=False) if len(s) else f"no picks traded on {a.date} in trades.db")


def cmd_regression(a):
    d = players()
    Y = year_cols(d)
    mA = sm.OLS(d["surplus_M"].values, np.column_stack([d["p_star"].values] + Y)).fit(cov_type="HC1")
    mB = sm.OLS(d["surplus_M"].values, np.column_stack([np.ones(len(d)), d["p_star"].values,
                                                        d["pick"].values.astype(float)] + Y)).fit(cov_type="HC1")
    sst = ((d["surplus_M"] - d["surplus_M"].mean()) ** 2).sum()
    print(f"Dependent: each drafted player's surplus ($M), {len(d):,} players, drafts 2007-2017; draft-year indicators "
          "(sum to zero); robust standard errors")
    print(f"  Adopted:   star probability {mA.params[0]:.2f} (se {mA.bse[0]:.2f}); no constant; R-squared {1 - mA.ssr / sst:.3f}")
    print(f"  With pick: star probability {mB.params[1]:.2f} (se {mB.bse[1]:.2f}); pick number {mB.params[2]:.4f} "
          f"(se {mB.bse[2]:.4f}, p {mB.pvalues[2]:.3f}); constant {mB.params[0]:.2f} (se {mB.bse[0]:.2f}); "
          f"R-squared {1 - mB.ssr / sst:.3f}")
    # Karl's form (meeting 2026-10-13): a constant plus a dummy for every draft but one (base = the last draft).
    # The adopted form has no column of ones and ten sum-to-zero year columns, so it is not the dummy-variable
    # trap; what it does do is force the average draft's intercept to zero. This line frees that intercept.
    yrs = d["draftYear"].values
    cl = sorted(set(yrs))
    mC = sm.OLS(d["surplus_M"].values, np.column_stack([np.ones(len(d)), d["p_star"].values]
                                                       + [(yrs == c).astype(float) for c in cl[:-1]])).fit(cov_type="HC1")
    stz = np.array(year_cols(d)).T                                        # the same intercept read at an average draft
    mD = sm.OLS(d["surplus_M"].values, np.column_stack([np.ones(len(d)), d["p_star"].values, stz])).fit(cov_type="HC1")
    print(f"  Constant:  star probability {mC.params[1]:.2f} (se {mC.bse[1]:.2f}); constant {mC.params[0]:.3f} "
          f"(se {mC.bse[0]:.3f}, p {mC.pvalues[0]:.3f}) for the {cl[-1]} draft, {mD.params[0]:.3f} "
          f"(se {mD.bse[0]:.3f}, p {mD.pvalues[0]:.3f}) at an average draft; dummies for {cl[0]}-{cl[-2]}; "
          f"R-squared {1 - mC.ssr / sst:.3f}")


def cmd_trend(a):
    d = players()

    def fit(f):
        t = (f["draftYear"].values - 2012).astype(float)
        r = sm.OLS(f["surplus_M"].values, np.column_stack([f["p_star"].values, f["p_star"].values * t] + year_cols(f))).fit(cov_type="HC1")
        return r.params[1], r.bse[1], r.pvalues[1]
    for lab, f in (("all eleven drafts", d), ("without 2015", d[d["draftYear"] != 2015]),
                   ("without 2015 and 2016", d[~d["draftYear"].isin([2015, 2016])])):
        b, se, p = fit(f)
        print(f"  {lab:24s} trend {b:+.2f} a draft year (se {se:.2f}, p {p:.3f})")


def cmd_stars(a):
    d = players()
    st = pd.read_csv(need("pick_star_and_rights_checks.csv"))[["draftYear", "pick", "star"]]
    m = d.merge(st, on=["draftYear", "pick"])
    m = m[m["draftYear"] <= 2015]
    print(f"Skaters drafted 2007-2015: {len(m):,} picks; {int(m['star'].sum())} stars ({100 * m['star'].mean():.1f}%) "
          f"produced {100 * m.loc[m['star'], 'surplus'].sum() / m['surplus'].sum():.1f}% of surplus")
    for lo, hi in ((1, 10), (11, 32), (33, 217)):
        g = m[m["pick"].between(lo, hi)]
        print(f"  picks {lo}-{hi}: stars {100 * g['star'].mean():.1f}% of picks, "
              f"{100 * g.loc[g['star'], 'surplus'].sum() / g['surplus'].sum():.1f}% of surplus")


def cmd_persistence(a):
    ps = pd.read_csv(need("pick_slot_persistence.csv"))
    sv, _ = star_values()
    for k in (1, 2):
        j = ps[ps["gap"] == k]
        print(f"{k} draft(s) later: correlation {np.corrcoef(j['slot'], j['later'])[0, 1]:.2f}, "
              f"median move {(j['later'] - j['slot']).abs().median():.0f} slots ({len(j)} team-pairs)")
        for lo, hi in ((1, 5), (6, 10), (11, 16), (17, 24), (25, 32)):
            g = j[j["slot"].between(lo, hi)]
            print(f"  picked {lo:2d}-{hi:2d}: later slot mean {g['later'].mean():5.1f} (10th-90th "
                  f"{g['later'].quantile(.1):.0f}-{g['later'].quantile(.9):.0f}); next first worth "
                  f"${sv * g['later_star'].mean():.2f}M against the round average ${sv * g['round_avg_star'].mean():.2f}M")


def cmd_versions(a):
    for f in ("pick_curve_log.txt", "traded_pick_values_log.txt", "pick_first_look_log.txt"):
        p = OUT / f
        print(f"  {f}: {p.read_text(encoding='utf-8').splitlines()[0] if p.exists() else 'MISSING'}")
    for f in ("pick_curve_players.csv", "pick_curve_scales.csv", "traded_pick_values.csv", "pick_slot_persistence.csv",
              "pick_star_and_rights_checks.csv", "top_pick_control_look.csv"):
        p = OUT / f
        print(f"  {f}: {'written ' + pd.Timestamp(p.stat().st_mtime, unit='s').strftime('%Y-%m-%d %H:%M') if p.exists() else 'MISSING'}")


ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
sub = ap.add_subparsers(dest="cmd", required=True)
sub.add_parser("pick").add_argument("n", type=int)
r = sub.add_parser("round"); r.add_argument("r", type=int); r.add_argument("--teams", type=int, default=32)
sub.add_parser("slot").add_argument("n", type=int)
sub.add_parser("player").add_argument("name")
sub.add_parser("draft").add_argument("year", type=int)
sub.add_parser("team").add_argument("team")
sub.add_parser("date").add_argument("date")
for c in ("regression", "trend", "stars", "persistence", "versions"):
    sub.add_parser(c)
args = ap.parse_args()
globals()[f"cmd_{args.cmd}"](args)
