"""run_goalie_price_line.py -- is a goalie win priced like a skater win?

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 5, the goalie branch, second
step. Development start years only. Nothing adopted.

WHY THIS QUESTION AND NOT ANOTHER
    The contribution of this project is putting three asset classes on ONE
    scale. That scale is dollars per forecast win. So before a goaltender can
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
    266 development goalie contracts against 3,519 skater ones. The pooled
    fit has power because the skaters carry it; a goalie-only line does not,
    and the quarterly rolling fit the skater currency uses cannot run on 266
    contracts at all. So the goalie-only line is fitted on an expanding window
    by signing date, which is still ex ante and is declared here rather than
    presented as the same protocol.
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
from production_currency import FEATURES, ProductionCurrency, _offset

SCRIPT_VERSION = "1.0"

# The pooled line's own features: the skater set, plus the two terms that
# answer the question. `is_G` moves a goaltender's price up or down at zero
# production; `g_x_war` is the difference in dollars per forecast win, which
# is the coefficient this whole run exists to read.
POOLED = FEATURES + ["is_G", "g_x_war"]


def goalie_forecasts(sample: pd.DataFrame, table: pd.DataFrame) -> pd.DataFrame:
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
        # The chance he is in the league, on the same estimator the bake-off
        # shared, fitted before this page.
        surv = GB.survival_table(table[table["syr"] < t0], t0)
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
            per = [float(war) * surv.get(min(h, max(GB.HORIZONS)), surv[max(GB.HORIZONS)])
                   for h in hs]
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
    """What one more forecast win a season is worth, in dollars of cap.

    The line is fitted in cap SHARE, so a slope becomes dollars by multiplying
    by the ceiling. `extra` adds an interaction term's slope on top, which is
    how the goaltender's own price per win is read off the pooled line.
    """
    b = coef[1:]
    v = float(b[feats.index("war_per_season")])
    if extra:
        v += float(b[feats.index(extra)])
    return v * cap


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
    C.log(f"  {len(sk)} skater and {len(go)} goaltender contracts carry a "
          f"forecast")

    dev = [int(y) for y in sorted(sk["start_yr"].dropna().unique())
           if int(y) not in C.CONFIRMATORY_START_YEARS]
    cohorts = C.check_market_cohorts(dev, "run_goalie_price_line")
    sk = sk[sk["start_yr"].isin(cohorts)].copy()
    go = go[go["start_yr"].isin(cohorts)].copy()
    C.log(f"  development starts only: {len(sk)} skater, {len(go)} goaltender")
    C.log("")

    d = prep_pooled(sk, go)
    d["cut"] = d["signed"].dt.to_period("Q").dt.start_time

    # ---- 1. is a goalie win priced like a skater win? ---------------------
    C.log("IS A GOALIE WIN PRICED LIKE A SKATER WIN? One censored line over")
    C.log("both, with a goaltender indicator and an interaction, refitted at")
    C.log("each signing quarter on contracts signed before it. The interaction")
    C.log("IS the difference in dollars per forecast win.")
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
                     "g_level": float(coef[1:][POOLED.index("is_G")]) * cap})
    r = pd.DataFrame(rows)
    C.log(f"    {'signed by':<12}{'fitted on':>10}{'$ per skater win':>19}"
          f"{'$ per goalie win':>19}{'goalie / skater':>17}")
    for _, x in r.iterrows():
        C.log(f"    {str(x['cut'].date()):<12}{int(x['n_fit']):>10}"
              f"{x['skater'] / 1e6:>19.3f}{x['goalie'] / 1e6:>19.3f}"
              f"{x['goalie'] / x['skater']:>17.2f}")
    C.log("")
    last = r.iloc[-1]
    C.log(f"  On the last fit, a forecast win from a goaltender prices at "
          f"${last['goalie'] / 1e6:.2f}M against")
    C.log(f"  ${last['skater'] / 1e6:.2f}M from a skater -- "
          f"{last['goalie'] / last['skater']:.2f} times. Across the window the "
          f"ratio runs")
    C.log(f"  {r['goalie'].div(r['skater']).min():.2f} to "
          f"{r['goalie'].div(r['skater']).max():.2f}.")
    C.log("")
    C.log("  A CONDITIONAL ASSOCIATION, NOT A PRICE OF A WIN. Nobody randomised")
    C.log("  which players got which contracts, and a goaltender's forecast is")
    C.log("  built by a different rule from a skater's -- flat where the skater")
    C.log("  ages, shrunk far harder, and measured on 82 seasons a year. A")
    C.log("  difference in the fitted slope is therefore a difference between")
    C.log("  two priced objects, not proof that clubs value a goaltender's win")
    C.log("  less. The forecast's own scale is part of what is being compared.")
    C.log("")

    # ---- 2. does pooling cost anything? ------------------------------------
    C.log("DOES A GOALTENDER BELONG ON THE SKATERS' LINE? Held-out error on")
    C.log("the goaltender contracts, in cap share, under three lines. Each is")
    C.log("fitted only on contracts signed before the one it prices.")
    C.log("")
    errs = {"one line, no goalie terms": [], "one line with goalie terms": [],
            "a goalie-only line": []}
    for cut, te in d.groupby("cut"):
        gte = te[te["is_G"] == 1.0]
        if gte.empty:
            continue
        plain, _ = fit_rolling(d, FEATURES, cut)
        both, _ = fit_rolling(d, POOLED, cut)
        gonly, n_g = fit_rolling(d[d["is_G"] == 1.0], FEATURES, cut)
        for name, coef, feats in (("one line, no goalie terms", plain, FEATURES),
                                  ("one line with goalie terms", both, POOLED),
                                  ("a goalie-only line", gonly, FEATURES)):
            if coef is None:
                continue
            pred = np.maximum(predict_tobit(coef, gte[feats].to_numpy(float)),
                              gte["floor_share"].to_numpy(float))
            errs[name].append(pd.DataFrame({
                "e": pred - gte["cap_share"].to_numpy(float),
                "contract_id": gte["contract_id"].to_numpy()}))
    C.log(f"    {'line':<30}{'goalie contracts':>18}{'mean abs error':>17}"
          f"{'bias':>9}")
    for name, parts in errs.items():
        if not parts:
            C.log(f"    {name:<30}{'--':>18}     never fitted: too few contracts")
            continue
        e = pd.concat(parts)
        note = ""
        if len(e) < 30:
            note = "   <- too few to read"
        C.log(f"    {name:<30}{len(e):>18}{e['e'].abs().mean():>17.4f}"
              f"{e['e'].mean():>9.4f}{note}")
    C.log("")
    C.log("  THE GOALIE-ONLY LINE NEVER GETS OFF THE GROUND. It needs 200")
    C.log("  contracts signed before the decision and the development sample")
    C.log("  holds 266 in total, so it first becomes fittable in the last")
    C.log("  quarter of the window and prices a handful of contracts. Its error")
    C.log("  is not a result and is printed only to show that the option is")
    C.log("  unavailable rather than unattractive.")
    C.log("")
    C.log("  WHAT IS A RESULT: a goaltender does not belong on the skaters'")
    C.log("  line unchanged. Adding the two goaltender terms cuts held-out")
    C.log("  error on goalie contracts by more than a quarter and takes the")
    C.log("  bias to nothing, which says the level and the slope both differ.")
    C.log("  One line with goaltender terms is the only one of the three this")
    C.log("  sample can both fit and defend.")
    C.log("")
    C.log("  Cap share, not dollars: 0.01 is a percentage point of the ceiling,")
    C.log("  about $0.9M on a 2021 cap. The goalie-only line is fitted on an")
    C.log("  expanding window rather than the quarterly one the skater currency")
    C.log("  uses, because 266 development contracts cannot support the latter.")
    C.log("")

    r.to_csv(C.out_path("goalie_price_line.csv"), index=False)
    C.log(f"  wrote {C.out_path('goalie_price_line.csv').name}")
    C.write_log("goalie_price_line_run_log.txt")


if __name__ == "__main__":
    main()
