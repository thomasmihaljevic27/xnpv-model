"""
one_regression.py - one regression in place of the findings document's two (Thomas, 2026-11-19: "It seems strange to have a
section 3 regression and a section 4 regression"; "let's see the results of this change"; declared in
40_DOCS/Backtest_Protocol.md before it was built. Report only until Thomas decides.)

DESIGN: groups_any.py part 5's. Each two-team trade in the declared window (to 2022-03-28) once, the first club's value
regressed on the differences between the two clubs (A minus B), no constant (B's value is A's with the sign reversed),
robust (HC1) standard errors (v2.3: two rows a trade, clustered by trade), a yes-or-no difference that is non-zero in fewer than five trades dropped.
TERMS, by the rule:
  types of trade (groups_any_sides.csv, groups_any.py v1.4): selling a player for picks and prospects, the deadline buyer,
    the other in-season buyer, rental, retained salary, former top-15 pick below the top-15 average, one asset for two or
    more, taking a contract to clear cap, new GM selling his predecessor's player, final-season restricted free agent, only
    picks in rounds 6 and 7;
  player characteristics (who_overpaid.build(), who_overpaid_any.player_facts(), v1.3's cap-weighted averages): aged 28 to
    31, aged 32 or over, defenceman, clause, signed as an unrestricted free agent, two seasons left, three or more seasons
    left, former top-15 pick, production, record above the forecast, games share;
  received a player: 1 when the club received a player valued by the player model (who_overpaid's main player exists).
A club that received no such player has every player characteristic 0. A club that received one with a main-player
characteristic unknown drops its trade (counted).
GUARDS: (1) part 5's age, defenceman and clause flags equal who_overpaid's on every side with a known player, under both
rules; (2) the same code with only part 5's terms, on part 5's rows, reproduces part 5's coefficients (groups_any.csv).
OUTCOMES: trade-day grade (net_M), realized value on WAR (out_net_M), Game Value (gv_net_M), seasons played (real_net_M).

v1.1 (2026-11-19; Thomas: "Drop the below average one"): the former top-15 pick below the top-15 average is left out
under both rules (it is a subset of the former top-15 pick); the correlation of the two terms is logged.

v2.0 (2026-11-19; Thomas: "I want as many usable trades in the sample as possible"): every missing player fact filled by
facts_fill.py's declared rules before the rows are chosen; a trade is left out only when a main player's birthdate is
unknown.

OUTPUTS: OUTPUT_DIR/one_regression_log.txt, one_regression.csv
"""
import importlib.util
import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
EXT = OUTPUT_DIR / "_extended_run"
SCRIPT_VERSION = "one_regression.py v2.3 (2026-11-19)"   # v2.3: two rows a trade, standard errors clustered by trade, coefficients unchanged (Thomas); v2.2: a goalie indicator beside the defenceman one; missing positions filled; v2.1: the rows built in frame() (results unchanged); v2.0: missing player facts filled (facts_fill.py); v1.2: logs the clubs with two or more players (log only); v1.1: the former top-15 pick below the average dropped (Thomas)
BELOW = {"main player rule": "m_top15", "any player rule": "t_top15"}     # the below-average top-15 term, by rule
DECLARED_END = "2022-03-28"
YS = [("trade-day grade", "net_M"), ("realized value, WAR", "out_net_M"), ("realized value, Game Value", "gv_net_M"),
      ("realized value, seasons played", "real_net_M")]
LOG, OUT = [], []
# part 5's terms, in its order, under each rule (groups_any.py part 4's swaps plus the two v1.2 groups)
P5 = {"main player rule": ["t_futures", "t_deadline_buyer", "t_other_buyer", "t_rental", "m_retained", "t_age28", "t_age32",
                           "t_def", "m_clause", "m_top15", "t_single", "t_dump", "t_newgm", "m_rfa", "t_late"],
      "any player rule": ["t_futures", "t_deadline_buyer", "t_other_buyer", "a_rental", "t_retained", "a_age28", "a_age32",
                          "a_def", "t_clause", "t_top15", "t_single", "t_dump", "a_newgm", "a_rfa", "t_late"]}
# the player characteristics each rule enters (who_overpaid_any v1.4's names)
PC = {"main player rule": ["age28", "age32", "defence", "main_clause", "ufa", "left2", "left3", "top15", "trailing_war",
                           "rep_gap", "gp_share_last", "goalie"],
      "any player rule": ["any_age28", "any_age32", "any_defence", "any_clause", "any_ufa", "any_left2", "any_left3",
                          "any_top15", "avg_war", "avg_gap", "avg_gs", "any_goalie"]}   # v2.2: goalie (Thomas)
DUP = {"main player rule": {"t_age28": "age28", "t_age32": "age32", "t_def": "defence", "m_clause": "main_clause"},
       "any player rule": {"a_age28": "any_age28", "a_age32": "any_age32", "a_def": "any_defence", "t_clause": "any_clause"}}
NAME = {"t_futures": "sold a player for picks and prospects", "t_deadline_buyer": "higher in the standings, deadline",
        "t_other_buyer": "higher in the standings, earlier in season", "t_rental": "rental", "a_rental": "rental",
        "m_retained": "retained salary", "t_retained": "retained salary", "m_top15": "former top-15 pick below the average",
        "t_top15": "former top-15 pick below the average", "t_single": "one asset for two or more",
        "t_dump": "took a contract to clear cap", "t_newgm": "new GM, predecessor's player", "a_newgm": "new GM, predecessor's player",
        "m_rfa": "restricted free agent, final season", "a_rfa": "restricted free agent, final season",
        "t_late": "only picks in rounds 6 and 7", "recv": "received a player"}
for r in PC:
    for k, lab in zip(PC[r], ["aged 28 to 31", "aged 32 or over", "defenceman", "clause", "signed as a free agent",
                              "two seasons left", "three or more seasons left", "former top-15 pick",
                              "production, each WAR", "record above the forecast, each WAR", "games share, all against none",
                              "goalie"]):
        NAME[k] = lab


def log(s=""):
    print(s)
    LOG.append(s)


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def joint(A, B, cols, flags):
    """v2.3 (Thomas, 2026-11-19: "I'd like it if it were presented that way"): each two-team trade enters as TWO rows,
    one a club: the club's value on its side minus the other side in each characteristic (what it received less what it
    sent), no constant, standard errors clustered by trade. The second club's row is the first's with every sign
    reversed, so the coefficients equal the one-row fit's (GUARD, to 1e-9); only the standard errors' small-sample
    correction differs. A result's nobs is 2 x the trades (callers report nobs // 2 as trades)."""
    X = pd.DataFrame({c: A[c].astype(float) - B[c].astype(float) for c in cols}, index=A.index)
    keep = [c for c in cols if c not in flags or (X[c] != 0).sum() >= 5]
    X = X[keep]
    X2 = pd.concat([X, -X], ignore_index=True)
    groups = np.r_[A.index.values, A.index.values]
    out = {}
    for _, y in YS:
        ya, yb = A[y].astype(float), B[y].astype(float)
        assert np.allclose(ya.values, -yb.values, atol=1e-6), f"{y}: the two clubs' values are not mirror images"
        m = sm.OLS(pd.concat([ya, yb], ignore_index=True), X2).fit(cov_type="cluster", cov_kwds={"groups": groups})
        one = sm.OLS(ya, X).fit()
        assert np.allclose(m.params.values, one.params.values, atol=1e-9), f"{y}: two rows and one row differ"
        out[y] = m
    return out, keep


def frame():
    """The rows and terms, both rules (v2.1: shared with clause_disguise.py): returns A, B (two-team trades, first and
    second club), the sides t, the players f and who_overpaid."""
    WO, WA = load("who_overpaid"), load("who_overpaid_any")
    CC = WO.load("clause_checks")
    GC, t = WO.build()
    key = ["trade_id", "club"]
    t = t.merge(pd.read_csv(EXT / "backtest_sides.csv")[key + ["real_net_M"]], on=key, how="left")
    n0 = len(t)
    # ---- the any player rule's characteristics (who_overpaid_any.py v1.3/v1.4, its main()) ----
    flags = ["age28", "age32", "defence", "clause", "ufa", "left2", "left3", "top15", "goalie"]   # v2.2: goalie
    f = WA.player_facts(CC.CS, CC.PST, WO.SEASON_GAMES)
    # v2.0 (Thomas: "I want as many usable trades in the sample as possible"): the missing facts filled (facts_fill.py)
    cc0 = ["age28", "age32", "defence", "clause", "ufa", "left2", "left3", "trailing_war", "rep_gap", "gp_share_last", "top15"]
    known0 = t["name"].notna() & t[cc0 + ["age"]].notna().all(axis=1)          # known before the fill (guard 1's rows)
    t, f = load("facts_fill").fill(t, f, WO, CC, log)
    t = t.join(f.groupby(key)[flags].max().add_prefix("any_"), on=key)
    main_a = f.sort_values("cap_hit", ascending=False, kind="stable").drop_duplicates(key).set_index(key)
    ti = t.set_index(key)
    t["main_clause"] = main_a["clause"].reindex(ti.index).fillna(0).astype(int).values
    g = f.assign(tw=f["trailing_war"].fillna(0), gap=f["trailing_war"].fillna(0) - f["expected_war"].fillna(0),
                 gs=f["gp_share"].fillna(0), cw=f["cap_hit"].fillna(0))
    for c in ("tw", "gap", "gs"):
        g[f"cw_{c}"] = g["cw"] * g[c]
    tot = g.groupby(key).agg(cw=("cw", "sum"), cw_tw=("cw_tw", "sum"), cw_gap=("cw_gap", "sum"), cw_gs=("cw_gs", "sum"),
                             m_tw=("tw", "mean"), m_gap=("gap", "mean"), m_gs=("gs", "mean"))
    den = tot["cw"].where(tot["cw"] > 0, 1)
    for c, out in (("tw", "avg_war"), ("gap", "avg_gap"), ("gs", "avg_gs")):
        tot[out] = np.where(tot["cw"] > 0, tot[f"cw_{c}"] / den, tot[f"m_{c}"])
    t = t.join(tot[["avg_war", "avg_gap", "avg_gs"]], on=key)
    # ---- the types of trade ----
    s = pd.read_csv(OUTPUT_DIR / "groups_any_sides.csv").drop(columns=["trade_date"])
    t = t.drop(columns=[c for c in s.columns if c in t.columns and c not in key]).merge(s, on=key, how="left")
    assert len(t) == n0 == len(s), (len(t), n0, len(s))
    # received a player, and whether his main-player characteristics are all known
    cc = ["age28", "age32", "defence", "clause", "ufa", "left2", "left3", "trailing_war", "rep_gap", "gp_share_last", "top15"]
    t["recv"] = t["name"].notna().astype(int)
    known = t[cc + ["age"]].notna().all(axis=1)
    t["unknown"] = (t["recv"] == 1) & ~known
    # who_overpaid's main player exists exactly where player_facts has a player, on the back-test's sides (player_facts
    # also covers sides of trades the back-test leaves out)
    sides = set(map(tuple, t[key].values))
    assert set(map(tuple, f[key].drop_duplicates().values)) & sides == set(map(tuple, t.loc[t["recv"] == 1, key].values))
    # GUARD 1: part 5's age, defenceman and clause flags equal who_overpaid's on sides with a known player
    pf_side = f.groupby(key)["pos_filled"].max().reindex(pd.MultiIndex.from_frame(t[key])).fillna(0).values == 1
    # v2.0: the sides known before the fill; v2.2: and with no player whose position was filled
    kp = t[(t["recv"] == 1) & ~t["unknown"] & known0.values & ~pf_side]
    pairs = [("t_age28", "age28"), ("t_age32", "age32"), ("t_def", "defence"), ("m_clause", "main_clause"),
             ("a_age28", "any_age28"), ("a_age32", "any_age32"), ("a_def", "any_defence"), ("t_clause", "any_clause")]
    bad = {a: int((kp[a].astype(int) != kp[b].fillna(0).astype(int)).sum()) for a, b in pairs}
    log(f"  check 1: on {len(kp)} sides with a known player, part 5's flags differing from who_overpaid's: {bad}")
    assert all(v == 0 for v in bad.values()), bad
    log("  (PASS)")
    # a club with no player: every player characteristic 0
    allpc = sorted(set(PC["main player rule"] + PC["any player rule"]))
    for c in allpc:
        t[c] = np.where(t["recv"] == 1, t[c], 0.0)
    t[allpc] = t[allpc].astype(float)

    n = t.groupby("trade_id")["club"].transform("size")
    two = t[(n == 2) & (t["trade_date"] <= DECLARED_END)].sort_values(key)
    A = two.groupby("trade_id").nth(0).set_index("trade_id")
    B = two.groupby("trade_id").nth(1).set_index("trade_id")
    # GUARD 2: part 5's terms alone, part 5's rows, reproduce part 5
    ref = pd.read_csv(OUTPUT_DIR / "groups_any.csv")
    ref = ref[ref["part"] == "v1.2 joint, one rule, declared window, two groups added"]
    for rule in P5:
        fs, keep = joint(A, B, P5[rule], set(P5[rule]))
        for lab, y in YS[:3]:
            got = fs[y].params[keep].values
            want = ref[(ref["rule"] == rule) & (ref["outcome"] == {"net_M": "priced", "out_net_M": "outcome, WAR",
                                                                     "gv_net_M": "outcome, Game Value"}[y])]["estimate"].values
            assert len(got) == len(want) and np.allclose(got, want), (rule, y)
    log(f"  check 2: part 5's terms alone reproduce part 5 on its {len(A)} trades, both rules (PASS)")

    drop = A["unknown"].astype(bool) | B["unknown"].astype(bool)
    A, B = A[~drop], B[~drop]
    log(f"  trades dropped for a player with an unknown characteristic: {int(drop.sum())}; trades in the fit: {len(A)}")
    log(f"  clubs that received a player: {int(A['recv'].sum() + B['recv'].sum())} of {2 * len(A)}")
    return A, B, t, f, key, WO


def main():
    log(SCRIPT_VERSION)
    A, B, t, f, key, WO = frame()
    npl = f.groupby(key).size()                                       # v1.2 (log only): clubs with two or more players
    m2 = sum(int(npl.get((tid, s["club"]), 0) >= 2) for X in (A, B) for tid, s in X.iterrows())
    log(f"  of them, received two or more players: {m2}")
    for rule, top in (("main player rule", "top15"), ("any player rule", "any_top15")):
        dx, dy = A[BELOW[rule]].astype(float) - B[BELOW[rule]].astype(float), A[top].astype(float) - B[top].astype(float)
        log(f"  {rule}: correlation of the two top-15 terms' differences {np.corrcoef(dx, dy)[0, 1]:.2f}; trades where the "
            f"below-average term differs {int((dx != 0).sum())}, the top-15 term {int((dy != 0).sum())}")
    res = {}
    for rule in P5:
        # v1.1 (Thomas: "Drop the below average one"): the below-average top-15 term left out; the former top-15 pick stays
        cols = [c for c in P5[rule] if c not in DUP[rule] and c != BELOW[rule]] + PC[rule] + ["recv"]
        fl = set(cols) - {"trailing_war", "rep_gap", "gp_share_last", "avg_war", "avg_gap", "avg_gs"}
        res[rule] = joint(A, B, cols, fl)
    log("\nONE REGRESSION, declared window ($M a club, positive = the club gained; two rows a trade, standard errors clustered by trade)")
    log("  F = a finding (trade-day grade and realized WAR both p < 0.05, same sign); checks: g = Game Value p < 0.05 same sign,"
        " s = seasons played p < 0.05 same sign")
    for rule in P5:
        fs, keep = res[rule]
        log(f"\n  {rule}")
        log(f"  {'term':<44}" + "".join(f"{y:>30}" for y, _ in YS) + "   finding")
        for k in keep:
            cells, ps, bs = [], [], []
            for ylab, y in YS:
                m = fs[y]
                cells.append(f"{m.params[k]:+.2f} ({m.bse[k]:.2f}) p={m.pvalues[k]:.3f}")
                ps.append(m.pvalues[k]); bs.append(m.params[k])
                OUT.append({"rule": rule, "term": NAME[k], "col": k, "outcome": ylab, "n_trades": int(m.nobs) // 2,
                            "estimate": m.params[k], "se": m.bse[k], "p": m.pvalues[k]})
            same = lambda i: ps[i] < 0.05 and np.sign(bs[i]) == np.sign(bs[0])      # noqa: E731
            tag = ("F" + ("g" if same(2) else "") + ("s" if same(3) else "")) if (ps[0] < 0.05 and same(1)) else ""
            log(f"  {NAME[k]:<44}" + "".join(f"{x:>30}" for x in cells) + f"   {tag}")
    pd.DataFrame(OUT).to_csv(OUTPUT_DIR / "one_regression.csv", index=False)
    (OUTPUT_DIR / "one_regression_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
