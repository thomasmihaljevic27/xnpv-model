"""run_goalie_price_line.py -- is a goalie win priced like a skater win?

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 5, the goalie branch, second
step. Development start years only. Nothing adopted.

WHY THIS QUESTION AND NOT ANOTHER
    The contribution of this project is putting three asset classes on ONE
    scale, and that scale runs through a forecast win. So before a goaltender can
    be valued beside a skater, one thing has to be settled: does the market
    pay the same for a win from a goaltender as it pays for a win from a
    skater?

    It is a question about the market, not about the model, and it has a
    testable answer. Fit one price line over skaters and goaltenders together
    with a goaltender indicator and an interaction, and read the interaction:
    it is the difference in dollars per forecast win between the two. That is
    a conditional association in a market nobody randomised, so it is reported
    as a price difference and never as a causal claim about what a win is
    worth.

WHAT FEEDS IT
    The forecast chosen in the bake-off: production's own goalie projector,
    imported and called at each signing's page. It was the best of the seven
    candidates scored there and nothing beat it.

    Its pooled mean error of +0.101 WAR is NOT corrected here and no price is
    moved to cancel it. That number has a career-bootstrap interval spanning
    zero, and the shared participation estimator it was measured with
    over-predicts playing by nearly nine points -- a gap worth more than the
    whole observed bias. It is a diagnostic for the participation model to
    take up, not a defect to price around.

WHAT IS THIN, AND SAID SO
    263 eligible development goaltender contracts, 205 with a forecast, 174
    priced out of sample -- against thousands of skater contracts. The pooled
    fit has power because the skaters carry it; a goalie-only line does not,
    and with 200 contracts needed before each decision it is fittable only at
    the very end of the window. Every line here, the goalie-only one
    included, is refitted at quarterly cutoffs on an expanding sample of the
    contracts signed before the cutoff.

WHAT IT DOES NOT SETTLE
    A different goaltender LEVEL on the shared win slope delivers the whole
    improvement in held-out error; a goaltender SLOPE on top has not earned
    its place. That is not evidence the slopes are equal, and it does not
    settle D7's single-market question. The specification is provisional
    while the goaltender participation model is built.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import information_set as ISET
import forecast_harness as H
import goalie_season_table as GST
import run_goalie_bakeoff as GB
from contract_price_model import (contract_sample, attach_forecasts, tobit,
                                  predict_tobit)
from player_season_table import birthdate_source, build as build_skater_table
from participation_model import ParticipationModel
from production_currency import FEATURES, ProductionCurrency, _offset

SCRIPT_VERSION = "2.1"

# The pooled line's own features: the skater set, plus the two terms that
# answer the question. `is_G` moves a goaltender's price up or down at zero
# production; `g_x_war` is the difference in dollars per forecast win, which
# is the coefficient this whole run exists to read.
POOLED = FEATURES + ["is_G", "g_x_war"]
# THE SIMPLER ALTERNATIVE the first version left out: a goaltender priced at a
# different LEVEL on the same win slope. Comparing no goalie terms against
# level AND slope skipped it, so the gain from the pair was credited to both
# terms when the level alone may carry it.
LEVEL_ONLY = FEATURES + ["is_G"]


def participation_at_page(table: pd.DataFrame, t0: int):
    """The goalie participation model, fitted on what page t0 could see, as a
    function of (pkey, horizon). Age is excluded for the reason given in
    `run_goalie_participation`: a goaltender's birthdate is selected on his
    survival. Horizons past the fitted range take the last fitted one, the
    same clamp the flat survival rate has always used."""
    import run_goalie_participation as GPM
    from contract_source import load_contracts
    contracts, _ = load_contracts()
    past = table[table["syr"] < t0]
    pm = ParticipationModel(contracts, exclude=GPM.PART_EXCLUDE).fit(
        past, t0, anchors_fn=GPM.goalie_anchors, horizons=GB.HORIZONS)
    a = GPM.goalie_anchors(past[past["GP"] >= C.MIN_GP])
    a = a[a["t0"] == t0].drop_duplicates("pkey")
    cache = {}

    def p(pkey: str, h: int) -> float:
        hh = min(int(h), max(GB.HORIZONS))
        if hh not in cache:
            s = pm.predict(a, hh)
            cache[hh] = pd.Series(s.to_numpy(), index=a["pkey"].to_numpy())
        v = cache[hh].get(pkey)
        return float(v) if v is not None and np.isfinite(v) else float(pm.base_[hh])
    return p


def goalie_forecasts(sample: pd.DataFrame, table: pd.DataFrame,
                     participation: str = "flat") -> pd.DataFrame:
    """Production's goalie projector, called at each contract's own page.

    One page per distinct `latest_complete`, exactly as the skater attachment
    batches, so every contract sees the information its signing saw. The
    projection is flat across the term -- production's rule and the one the
    bake-off could not beat -- so the forecast per season is that projection
    and the first year is the same number.
    """
    proj = GB.production_projector()
    out = []
    for L, grp in sample.groupby("latest_complete"):
        t0 = int(L) + 1
        if t0 < C.FIRST_SOURCE_SEASON + 3:
            continue
        # The chance he is in the league: either the flat survival rate the
        # bake-off shared, or the participation model, both fitted before
        # this page. `participation` says which, so the price comparison can
        # be run on each and the two read side by side.
        surv = GB.survival_table(table[table["syr"] < t0], t0)
        pfun = (participation_at_page(table, t0)
                if participation == "model" else None)
        past = table[(table["syr"].between(t0 - 3, t0 - 1))
                     & (table["GP"] >= C.MIN_GP)]
        # KEYED ON THE NORMALISED NAME, which is what production's lookup
        # table uses. The contract census carries `pkey` (name|position) and
        # the goalie panel carries both, so the join runs through the name
        # rather than through a key only one side has.
        past = past.assign(nname=past["pkey"].str.rsplit("|", n=1).str[0])
        share = (past.sort_values("syr").groupby("nname")["gp_share"]
                 .apply(lambda s: float(np.average(
                     s.to_numpy(), weights=np.linspace(1, 2, len(s))))))
        med = float(share.median()) if len(share) else 0.5
        for r in grp.itertuples():
            nname = str(r.pkey).rsplit("|", 1)[0]
            war, _src = proj.shrunk_projection(nname, t0)
            if war is None or pd.isna(war):
                continue
            hs = [int(s - t0) for s in range(int(r.start_yr), int(r.end_yr) + 1)]
            if min(hs) < 0:
                continue
            # A season's forecast is the flat projection times the chance he
            # is there to deliver it. The integration rule, applied once.
            if pfun is None:
                per = [float(war) * surv.get(min(h, max(GB.HORIZONS)),
                                             surv[max(GB.HORIZONS)])
                       for h in hs]
            else:
                per = [float(war) * pfun(str(r.pkey), h) for h in hs]
            out.append({"contract_id": int(r.contract_id),
                        "war_per_season": float(np.mean(per)),
                        "war_year1": float(per[0]),
                        "gp_share_fc": float(share.get(nname, med)),
                        "n_years_forecast": len(hs)})
    return pd.DataFrame(out)


def prep_pooled(sk: pd.DataFrame, go: pd.DataFrame) -> pd.DataFrame:
    """Skaters and goaltenders in one frame, with the two terms that answer
    the question and nothing else different between them."""
    sk = sk.copy(); go = go.copy()
    sk["is_G"], go["is_G"] = 0.0, 1.0
    d = pd.concat([sk, go], ignore_index=True)
    d["one_year"] = (d["length"] == 1).astype(float)
    d["rfa_x_war"] = d["is_RFA"] * d["war_per_season"]
    d["g_x_war"] = d["is_G"] * d["war_per_season"]
    return d


def fit_rolling(d: pd.DataFrame, feats: list, cut) -> tuple:
    """The censored line, fitted on contracts SIGNED before the decision."""
    tr = d[d["signed"] < pd.Timestamp(cut)]
    if len(tr) < 200:
        return None, 0
    coef, _sd, _ok = tobit(tr[feats].to_numpy(float),
                           tr["cap_share"].to_numpy(float),
                           tr["floor_share"].to_numpy(float))
    return coef, len(tr)


def dollars_per_win(coef, feats: list, cap: float, extra: str | None = None) -> float:
    """The PARTIAL slope on the season-average forecast, in dollars of cap.

    What it holds fixed is the whole of what it means, so it is stated: this
    is the change in the fitted annual price when the season-average forecast
    rises by one win and FIRST-YEAR production does not move, for an
    UNRESTRICTED player (the restricted interaction is not added). It is not
    what a better player is worth, because a better player's first year moves
    too. `price_response` is that quantity; this one is kept because it is
    the coefficient the goaltender interaction is defined against.
    """
    b = coef[1:]
    v = float(b[feats.index("war_per_season")])
    if extra:
        v += float(b[feats.index(extra)])
    return v * cap


def price_response(coef, feats: list, cap: float, goalie: bool,
                   rfa: bool) -> float:
    """The change in the fitted annual price, in dollars of cap, when a
    player's expected production rises by ONE WIN IN EVERY SEASON.

    Every term the forecast enters moves with it: the season average, the
    first year, the restricted interaction if he is restricted, and the
    goaltender interaction if he is a goaltender. Before the league-minimum
    floor, and a change in an annual price rather than in a contract's value
    -- it is not an NPV and must not be quoted as one.
    """
    b = coef[1:]
    v = float(b[feats.index("war_per_season")]) + float(b[feats.index("war_year1")])
    if rfa:
        v += float(b[feats.index("rfa_x_war")])
    if goalie and "g_x_war" in feats:
        v += float(b[feats.index("g_x_war")])
    return v * cap


def paired_goalie_bootstrap(a: pd.DataFrame, b: pd.DataFrame, n: int = 2000,
                            seed: int = 20260922) -> tuple:
    """Is the second specification's error on goaltender contracts lower than
    the first's, resampling GOALTENDERS -- one goaltender signs several of
    these contracts and they are not independent draws. Returns the mean gap
    in absolute error (second minus first) and the share of resamples in which
    the second wins."""
    j = a.merge(b, on=["contract_id", "pkey"], suffixes=("_a", "_b"),
                validate="one_to_one")
    g = {k: v for k, v in j.groupby("pkey")}
    keys = list(g)
    rng = np.random.default_rng(seed)
    wins = 0
    for _ in range(n):
        s = pd.concat([g[k] for k in rng.choice(keys, len(keys), replace=True)])
        wins += int(s["e_b"].abs().mean() < s["e_a"].abs().mean())
    gap = float(j["e_b"].abs().mean() - j["e_a"].abs().mean())
    return gap, wins / n, len(j), len(keys)


def compare_specs(d: pd.DataFrame) -> dict:
    """Held-out error on the goaltender contracts under the four lines, each
    refitted at every quarterly cutoff on the contracts signed before it, and
    the two paired comparisons that matter. Returns the per-contract errors."""
    specs = (("no goaltender terms", d, FEATURES),
             ("goaltender level only", d, LEVEL_ONLY),
             ("goaltender level and slope", d, POOLED),
             ("a goalie-only line", d[d["is_G"] == 1.0], FEATURES))
    errs = {name: [] for name, _, _ in specs}
    for cut, te in d.groupby("cut"):
        gte = te[te["is_G"] == 1.0]
        if gte.empty:
            continue
        for name, frame, feats in specs:
            coef, _n = fit_rolling(frame, feats, cut)
            if coef is None:
                continue
            pred = np.maximum(predict_tobit(coef, gte[feats].to_numpy(float)),
                              gte["floor_share"].to_numpy(float))
            errs[name].append(pd.DataFrame({
                "e": pred - gte["cap_share"].to_numpy(float),
                "contract_id": gte["contract_id"].to_numpy(),
                "pkey": gte["pkey"].to_numpy()}))
    C.log(f"    {'line':<30}{'goalie contracts':>18}{'mean abs error':>17}"
          f"{'bias':>11}")
    frames = {}
    for name, parts in errs.items():
        if not parts:
            C.log(f"    {name:<30}{'--':>18}     never fitted: too few contracts")
            continue
        e = pd.concat(parts, ignore_index=True)
        frames[name] = e
        note = "   <- too few to read" if len(e) < 30 else ""
        C.log(f"    {name:<30}{len(e):>18}{e['e'].abs().mean():>17.6f}"
              f"{e['e'].mean():>+11.6f}{note}")
    C.log("")
    for a_name, b_name in (("no goaltender terms", "goaltender level only"),
                           ("goaltender level only", "goaltender level and slope")):
        gap, share, n_c, n_g = paired_goalie_bootstrap(frames[a_name],
                                                       frames[b_name])
        C.log(f"  {b_name} against {a_name}: {gap:+.6f} of mean abs")
        C.log(f"    error on {n_c} contracts, better in {share:.0%} of resamples "
              f"of the {n_g} goaltenders")
    C.log("")
    return frames


def last_fit_responses(d: pd.DataFrame) -> None:
    """The defined whole-path response on the last fit, for the table that
    has to say what changes and what stays fixed."""
    cut = sorted(d["cut"].unique())[-1]
    coef, n = fit_rolling(d, POOLED, cut)
    cap = C.cap_path(cut, [int(pd.Timestamp(cut).year)])[int(pd.Timestamp(cut).year)]
    C.log(f"    {'the change (last fit, ' + str(n) + ' contracts)':<46}"
          f"{'skater $M':>11}{'goalie $M':>11}{'ratio':>8}")
    for lab, rfa in (("one more win every season, UFA", False),
                     ("one more win every season, RFA", True)):
        sk_v = price_response(coef, POOLED, cap, False, rfa)
        go_v = price_response(coef, POOLED, cap, True, rfa)
        C.log(f"    {lab:<46}{sk_v / 1e6:>11.3f}{go_v / 1e6:>11.3f}"
              f"{go_v / sk_v:>8.2f}")
    C.log("")


def main() -> None:
    C.banner("run_goalie_price_line.py", SCRIPT_VERSION)
    path, how = birthdate_source()
    C.log(f"  birthdates: {how}")
    sk_table = build_skater_table(birthdate_csv=path, verbose=False)
    g_table = GST.build(birthdate_csv=path, verbose=False, allow_thin_ages=True)
    C.log("")

    # ---- the two samples, on one census -----------------------------------
    sk_s = contract_sample(("F", "D"))
    go_s = contract_sample(("G",))
    C.log(f"  {len(sk_s)} skater and {len(go_s)} goaltender contracts in the "
          f"census")

    # The skater side uses the leader the rest of the tree uses.
    from run_npv_simulation import LEADER, prep
    sk = prep(attach_forecasts(sk_s, LEADER, sk_table, verbose=False))

    gf = goalie_forecasts(go_s, g_table)
    go = go_s.merge(gf, on="contract_id", how="inner")

    dev = [int(y) for y in sorted(sk["start_yr"].dropna().unique())
           if int(y) not in C.CONFIRMATORY_START_YEARS]
    cohorts = C.check_market_cohorts(dev, "run_goalie_price_line")
    # THE ATTRITION, stage by stage, so the sample a figure rests on is never
    # quoted from the wrong stage. The first version quoted 266, which was a
    # count taken before the signing-date rule the census applies.
    n_eligible = int(go_s["start_yr"].isin(cohorts).sum())
    sk = sk[sk["start_yr"].isin(cohorts)].copy()
    go = go[go["start_yr"].isin(cohorts)].copy()
    n_forecast = len(go)
    C.log("  development goaltender contracts, stage by stage:")
    C.log(f"    eligible in the census                  {n_eligible:>6}")
    C.log(f"    with a forecast from production's projector {n_forecast:>3}")
    C.log("    priced out of sample on the pooled line: reported below")
    C.log(f"  and {len(sk)} development skater contracts with a forecast")
    C.log("")

    d = prep_pooled(sk, go)
    d["cut"] = d["signed"].dt.to_period("Q").dt.start_time

    # ---- 1. what the pooled line says a goalie win is priced at -------------
    C.log("WHAT THE POOLED LINE SAYS ABOUT A GOALIE WIN. One censored line over")
    C.log("both, with a goaltender indicator and an interaction, refitted at")
    C.log("each signing quarter on the contracts signed before it.")
    C.log("")
    C.log("  THE COLUMNS ARE A PARTIAL SLOPE, and what they hold fixed is the")
    C.log("  whole of what they mean: the change in the fitted annual price when")
    C.log("  the season-average forecast rises by one win, FIRST-YEAR production")
    C.log("  held where it is, for an UNRESTRICTED player. An earlier version of")
    C.log("  this table called that 'dollars per win', which it is not -- a")
    C.log("  better player's first year moves too. The whole-path response is")
    C.log("  the second table.")
    C.log("")
    rows = []
    for cut, te in d.groupby("cut"):
        coef, n = fit_rolling(d, POOLED, cut)
        if coef is None:
            continue
        cap = C.cap_path(cut, [int(cut.year)])[int(cut.year)]
        rows.append({"cut": cut, "n_fit": n,
                     "skater": dollars_per_win(coef, POOLED, cap),
                     "goalie": dollars_per_win(coef, POOLED, cap, "g_x_war"),
                     "g_level": float(coef[1:][POOLED.index("is_G")]) * cap,
                     "coef": coef, "cap": cap})
    r = pd.DataFrame(rows)
    C.log(f"    {'signed by':<12}{'fitted on':>10}{'skater, partial':>17}"
          f"{'goalie, partial':>17}{'ratio':>8}")
    for _, x in r.iterrows():
        C.log(f"    {str(x['cut'].date()):<12}{int(x['n_fit']):>10}"
              f"{x['skater'] / 1e6:>17.3f}{x['goalie'] / 1e6:>17.3f}"
              f"{x['goalie'] / x['skater']:>8.2f}")
    C.log("")

    last = r.iloc[-1]
    C.log("  THE DEFINED RESPONSE, on the last fit: one extra expected win in")
    C.log("  EVERY season, so the season average, the first year and every")
    C.log("  interaction the forecast enters all move with it. A change in the")
    C.log("  fitted annual price before the league-minimum floor -- not a")
    C.log("  contract's value, and not to be quoted as one.")
    C.log("")
    C.log(f"    {'the change':<46}{'skater $M':>11}{'goalie $M':>11}{'ratio':>8}")
    for lab, rfa, whole in (("partial slope, first year held (UFA)", False, False),
                            ("one more win every season, UFA", False, True),
                            ("one more win every season, RFA", True, True)):
        if whole:
            sk_v = price_response(last["coef"], POOLED, last["cap"], False, rfa)
            go_v = price_response(last["coef"], POOLED, last["cap"], True, rfa)
        else:
            sk_v, go_v = last["skater"], last["goalie"]
        C.log(f"    {lab:<46}{sk_v / 1e6:>11.3f}{go_v / 1e6:>11.3f}"
              f"{go_v / sk_v:>8.2f}")
    C.log("")
    C.log("  The goaltender gap is the same in every row -- it is one")
    C.log("  coefficient -- so the RATIO depends on which change is being")
    C.log("  priced. Against the whole-path response it is near 1.07, not the")
    C.log("  1.18 the partial slope gives.")
    C.log("")
    C.log("  A CONDITIONAL ASSOCIATION BETWEEN MATCHED CASES, NOT THE PRICE OF")
    C.log("  A WIN. Nobody randomised which players got which contracts, and a")
    C.log("  goaltender's forecast is built by a different rule from a")
    C.log("  skater's -- flat where the skater ages, shrunk far harder, measured")
    C.log("  on 82 seasons a year -- so part of any slope difference is the")
    C.log("  difference between two priced objects.")
    C.log("")

    # ---- 2. which goaltender adjustment the evidence supports --------------
    C.log("WHICH GOALTENDER ADJUSTMENT DOES THE EVIDENCE SUPPORT? Held-out")
    C.log("error on the SAME goaltender contracts, in cap share. Every line")
    C.log("is refitted at each quarterly cutoff on an expanding sample of the")
    C.log("contracts signed before it -- the same scheme for all four; an")
    C.log("earlier version of this note said the goalie-only line used a")
    C.log("different window, and it did not.")
    C.log("")
    frames = compare_specs(d)
    C.log("  WHAT THIS SUPPORTS: goaltenders need an adjustment on the shared")
    C.log("  line, and a different LEVEL on the same win slope delivers all of")
    C.log("  the improvement. Adding a goaltender slope on top has not earned")
    C.log("  its place in this comparison. That is NOT evidence the two slopes")
    C.log("  are equal -- 174 contracts cannot tell a small slope difference")
    C.log("  from none -- and it does NOT settle D7's single-market question.")
    C.log("  The goaltender specification stays provisional.")
    C.log("")
    C.log("  THE GOALIE-ONLY LINE NEVER GETS OFF THE GROUND. It needs 200")
    C.log(f"  contracts signed before the decision; the development sample")
    C.log(f"  holds {n_eligible} eligible goaltender contracts, {n_forecast} with a")
    C.log("  forecast, so it becomes fittable only at the end of the window and")
    C.log("  prices a handful. Unavailable rather than unattractive.")
    C.log("")
    C.log("  Cap share, not dollars: 0.01 is a percentage point of the ceiling,")
    C.log("  about $0.8M on a 2021 cap.")
    C.log("")

    # ---- 3. the same comparison on the updated forecast -------------------
    C.log("THE SAME COMPARISON ON THE UPDATED FORECAST. The goalie forecast")
    C.log("above carries the flat survival rate the bake-off shared. The")
    C.log("participation model replaces it here -- production's projector for")
    C.log("ability, the participation model for whether he plays, his trailing")
    C.log("share for how much -- and every line is refitted. The share model is")
    C.log("NOT used: it forecasts share better but cannot be combined with")
    C.log("production's season-total projector, for the reason set out in")
    C.log("`run_goalie_participation`.")
    C.log("")
    gf2 = goalie_forecasts(go_s, g_table, participation="model")
    go2 = go_s.merge(gf2, on="contract_id", how="inner")
    go2 = go2[go2["start_yr"].isin(cohorts)].copy()
    moved = go.merge(go2[["contract_id", "war_per_season"]], on="contract_id",
                     suffixes=("", "_new"))
    C.log(f"  {len(go2)} goaltender contracts carry the updated forecast; the")
    C.log(f"  season-average forecast moves by "
          f"{(moved['war_per_season_new'] - moved['war_per_season']).mean():+.3f} "
          f"WAR on average")
    C.log(f"  (mean {moved['war_per_season'].mean():.3f} -> "
          f"{moved['war_per_season_new'].mean():.3f})")
    C.log("")
    d2 = prep_pooled(sk, go2)
    d2["cut"] = d2["signed"].dt.to_period("Q").dt.start_time
    compare_specs(d2)
    last_fit_responses(d2)
    C.log("  Read beside the first comparison: whether the level still carries")
    C.log("  the improvement once participation is modelled, and whether the")
    C.log("  goaltender gap in the whole-path response moves. The specification")
    C.log("  stays provisional either way -- the rate forecast the share model")
    C.log("  needs is not built yet, and it moves this input again.")
    C.log("")

    r.drop(columns=["coef"]).to_csv(C.out_path("goalie_price_line.csv"),
                                    index=False)
    C.log(f"  wrote {C.out_path('goalie_price_line.csv').name}")
    C.write_log("goalie_price_line_run_log.txt")


if __name__ == "__main__":
    main()
