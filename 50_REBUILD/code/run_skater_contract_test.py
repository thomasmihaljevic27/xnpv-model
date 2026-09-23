"""run_skater_contract_test.py -- should the skater leader's participation use contract data?

EXPERIMENTAL (50_REBUILD). Development pages and development start years
only. A matched test; nothing adopted.

THE QUESTION, AND WHY IT IS OPEN
    The standing leader fits participation WITHOUT contract data, partly on a
    Phase 2 finding that contract data made the forecast worse. That finding was
    withdrawn in conclusion (2026-09-22): part of it was a singular-design defect.
    The re-measured ablation left a near tie, but it used a different ability
    configuration from the leader, and it read contract state the old way. The
    goalie branch has since shown what the old way does: the vendor export is a
    snapshot of contracts ending in 2018 or later, so on early pages "known to
    the export" and "under a visible contract" encode survival.

WHAT IS COMPARED -- THE LEADER AND FOUR MATCHED VARIANTS
    Every variant is the leader (`A1HingeExposure`) with ONE thing changed: the
    contract inputs its participation model reads. Ability, aging, the rate and
    games halves, and the harness are identical.

        leader          no contract inputs (the standing leader)
        as_known        export membership + contract status as known (old way)
        observable      before/after-2018 period indicator + visible status
        period_only     the period indicator alone
        contract_only   visible contract status alone

    The last three separate the two inputs the "observable" definition carries.
    CLAUDE.md, after two corrections: a multi-part change is scored part by part
    before any part is credited.

HOW IT IS SCORED, DECLARED BEFORE THE RUN
    1. Participation: Brier score, and the confident fifth's calibration.
    2. Season WAR: squared error PRIMARY, absolute error and bias beside it.
    3. Contract dollars: every variant's point valuation, and the WAR each
       player actually delivered, priced on ONE fixed line -- the leader's --
       with the realised target asserted identical across variants. Squared
       dollar error primary. The observable variant's line is the sensitivity.
       Ended terms only; realised seasons are read only for scoring.
    Paired comparisons resample PLAYERS, one career being many forecasts.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import forecast_harness as H
from ability_forecast import A1HingeExposure, _anchors, W_T1, W_T2
from contract_price_model import contract_sample, attach_forecasts
from participation_model import contract_spans, players_with_any_contract, under_contract_at
from player_season_table import build as build_table, birthdate_source
from production_currency import ProductionCurrency
from run_phase4_decisions import prep

SCRIPT_VERSION = "1.0"
HORIZONS = (0, 1, 2, 3, 4, 5)
N_BOOT = 2000
SEED = 20260924


def _variant(tag: str, label: str, use: bool, state: str = "as_known", exclude=()):
    return type(f"Skater_{tag}", (A1HingeExposure,), {
        "name": label, "USE_CONTRACTS": use, "CONTRACT_STATE": state,
        "PART_EXCLUDE": tuple(exclude)})


VARIANTS = {
    "leader": A1HingeExposure,
    "as_known": _variant("as_known", "leader, contract state as known", True),
    "observable": _variant("observable", "leader, period + contract status", True, "observable"),
    "period_only": _variant("period_only", "leader, period indicator only", True,
                            "observable", ("under_contract",)),
    "contract_only": _variant("contract_only", "leader, contract status only", True,
                              "observable", ("contract_unknown",)),
}


class Boot:
    """Resampling players fast: per-player sums, resampled indices, reused
    for every statistic so every comparison sees the same draws."""

    def __init__(self, keys: pd.Series, n: int = N_BOOT, seed: int = SEED):
        self.codes, self.uniq = pd.factorize(keys)
        rng = np.random.default_rng(seed)
        self.idx = rng.integers(0, len(self.uniq), size=(n, len(self.uniq)))
        self.cnt = np.bincount(self.codes, minlength=len(self.uniq)).astype(float)

    def sums(self, x) -> np.ndarray:
        return np.bincount(self.codes, weights=np.asarray(x, float), minlength=len(self.uniq))

    def mean_ci(self, x) -> tuple:
        s = self.sums(x)
        b = s[self.idx].sum(1) / self.cnt[self.idx].sum(1)
        lo, hi = np.percentile(b, [2.5, 97.5])
        return float(np.asarray(x, float).mean()), float(lo), float(hi)

    def lower_share(self, a, b) -> float:
        """Share of resamples in which b's mean is below a's."""
        sa, sb = self.sums(a), self.sums(b)
        return float((sb[self.idx].sum(1) < sa[self.idx].sum(1)).mean())


def mechanism(table: pd.DataFrame, spans: pd.DataFrame) -> None:
    C.log("DOES THE SKATER EXPORT CARRY SURVIVAL TOO? Share of skater anchors the")
    C.log("export knows, under a visible contract, and how often each group played:")
    C.log("")
    a = _anchors(table[table["GP"] >= C.MIN_GP], 2, W_T2 / W_T1)
    act = table.set_index(["career_key", "syr"])["GP"]
    C.log(f"    {'page':<6}{'h':>3}{'known':>8}{'under':>8}{'played if':>12}"
          f"{'played if known,':>18}{'played if':>11}")
    C.log(f"    {'':<6}{'':>3}{'':>8}{'':>8}{'unknown':>12}{'not under (n)':>18}{'under':>11}")
    for h in (0, 3):
        for t0 in (2010, 2012, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2022):
            if t0 + h > C.LAST_SOURCE_SEASON:
                continue
            grp = a[a["t0"] == t0]
            asof = pd.Timestamp(year=t0, month=7, day=1)
            k = grp["pkey"].isin(players_with_any_contract(spans, asof)).to_numpy()
            uc = under_contract_at(spans, asof, [t0 + h])
            u = grp["pkey"].isin(set(uc["pkey"]) if len(uc) else set()).to_numpy()
            ix = pd.MultiIndex.from_arrays([grp["career_key"], grp["t0"] + h])
            y = act.reindex(ix).fillna(0).to_numpy() >= C.PARTICIPATION_GP
            f = lambda m: f"{y[m].mean():.2f}" if m.any() else "--"
            C.log(f"    {t0:<6}{h:>3}{k.mean():>8.2f}{u.mean():>8.2f}{f(~k):>12}"
                  f"{f(k & ~u) + ' (' + str(int((k & ~u).sum())) + ')':>18}{f(u):>11}")
        C.log("")


def season_scores(runs: dict) -> None:
    lead = runs["leader"]
    keys = ["career_key", "page", "h"]
    for d in runs.values():
        assert len(d) == len(lead)
    boot = Boot(lead["career_key"])
    al = {k: d.set_index(keys).reindex(lead.set_index(keys).index).reset_index()
          for k, d in runs.items()}
    for d in al.values():
        d["se"] = d["e_war"] ** 2
    C.log("PARTICIPATION AND SEASON WAR, development pages, horizons 0-5, "
          f"{len(lead)} forecasts each.")
    C.log("'beats leader' is the share of player-resamples in which the variant's")
    C.log("error is lower than the leader's. Squared error is the primary score.")
    C.log("")
    C.log(f"    {'variant':<16}{'Brier':>8}{'beats':>7}{'WAR RMSE':>10}{'beats':>7}"
          f"{'WAR MAE':>9}{'bias':>8}")
    for k, d in al.items():
        tail = ("" if k == "leader" else
                f"{boot.lower_share(al['leader']['brier'], d['brier']):>7.0%}")
        tail2 = ("" if k == "leader" else
                 f"{boot.lower_share(al['leader']['se'], d['se']):>7.0%}")
        C.log(f"    {k:<16}{d['brier'].mean():>8.4f}{tail or '--':>7}"
              f"{np.sqrt(d['se'].mean()):>10.4f}{tail2 or '--':>7}"
              f"{d['e_war'].abs().mean():>9.4f}{d['e_war'].mean():>+8.4f}")
    C.log("")
    C.log("  THE INPUTS SEPARATED (share in which the second is lower, Brier / WAR sq.):")
    for a, b in (("leader", "period_only"), ("leader", "contract_only"),
                 ("contract_only", "observable"), ("observable", "period_only"),
                 ("leader", "as_known")):
        C.log(f"    {b:<14} against {a:<14} {boot.lower_share(al[a]['brier'], al[b]['brier']):>5.0%}"
              f"  /  {boot.lower_share(al[a]['se'], al[b]['se']):>5.0%}")
    C.log("")
    C.log("  Brier by horizon:")
    C.log("    " + f"{'h':<4}" + "".join(f"{k:>15}" for k in al))
    for h in HORIZONS:
        C.log("    " + f"{h:<4}" + "".join(
            f"{d.loc[d['h'] == h, 'brier'].mean():>15.4f}" for d in al.values()))
    C.log("")
    C.log("  The confident fifth of each variant's own predictions, predicted minus")
    C.log("  observed participation, player-resampled interval:")
    for k, d in al.items():
        top = d["p_play"] >= d["p_play"].quantile(0.8)
        bt = Boot(d.loc[top, "career_key"])
        v, lo, hi = bt.mean_ci(d.loc[top, "p_play"] - d.loc[top, "played"].astype(float))
        C.log(f"    {k:<16}{v:+.3f} [{lo:+.3f}, {hi:+.3f}]")
    C.log("")


def dollars(table: pd.DataFrame) -> None:
    sample = contract_sample()
    dev = [int(y) for y in sorted(sample["start_yr"].dropna().unique())
           if int(y) not in C.CONFIRMATORY_START_YEARS]
    cohorts = C.check_market_cohorts(dev, "run_skater_contract_test")
    rows = {}
    for k, cls in VARIANTS.items():
        d = prep(attach_forecasts(sample, cls, table, verbose=False))
        d = d[d["start_yr"].isin(cohorts) & (d["signed"] >= pd.Timestamp("2015-07-01"))].copy()
        d["cut"] = d["signed"].dt.to_period("Q").dt.start_time
        rows[k] = d.drop_duplicates("contract_id").set_index("contract_id")
    common = sorted(set.intersection(*[set(d.index) for d in rows.values()]))
    played = table[table["GP"] >= C.PARTICIPATION_GP].groupby(["pkey", "syr"])["WAR"].sum()

    def lines_from(d: pd.DataFrame) -> dict:
        out = {}
        for cut in sorted(d["cut"].unique()):
            cur = ProductionCurrency("in").fit(d.reset_index(), before_date=cut)
            if cur.coef_ is not None:
                out[cut] = cur
        return out

    C.log("CONTRACT DOLLARS, every variant's point valuation and the realised")
    C.log(f"production priced on ONE line; {len(common)} contracts every variant prices.")
    C.log("")
    lead = rows["leader"].loc[common]
    for line_tag in ("leader", "observable"):
        lines = lines_from(rows[line_tag].reset_index())
        ids = [c for c in common if lead.loc[c, "cut"] in lines]
        val = {k: [] for k in rows}
        real, ended, pk = [], [], []
        for c in ids:
            cur = lines[lead.loc[c, "cut"]]
            tg = []
            for k, d in rows.items():
                r = d.loc[[c]].copy()
                val[k].append(float(cur.value(r).iloc[0]))
                yrs = range(int(r["start_yr"].iloc[0]), int(r["end_yr"].iloc[0]) + 1)
                w = np.array([float(played.get((r["pkey"].iloc[0], y), 0.0)) for y in yrs])
                rr = r.copy()
                rr["war_per_season"], rr["war_year1"] = w.mean(), w[0]
                rr["rfa_x_war"] = rr["is_RFA"] * rr["war_per_season"]
                tg.append(float(cur.value(rr).iloc[0]))
            assert max(tg) - min(tg) < 1e-6, f"contract {c}: the realised target moved"
            real.append(tg[0])
            ended.append(int(lead.loc[c, "end_yr"]) <= C.LAST_SOURCE_SEASON)
            pk.append(lead.loc[c, "pkey"])
        real, ended = np.array(real), np.array(ended)
        base = np.array(val["leader"])
        C.log(f"  on the {line_tag} variant's line "
              f"({'PRIMARY' if line_tag == 'leader' else 'sensitivity'}); "
              f"{len(ids)} contracts valued, {int(ended.sum())} with an ended term scored:")
        C.log(f"    {'variant':<16}{'moves value, mean abs $M':>26}{'RMSE $M':>10}"
              f"{'MAE':>8}{'bias':>9}{'beats leader':>14}")
        boot = Boot(pd.Series(np.array(pk)[ended]))
        e_lead = (base[ended] - real[ended]) / 1e6
        for k in rows:
            v = np.array(val[k])
            e = (v[ended] - real[ended]) / 1e6
            share = "--" if k == "leader" else f"{boot.lower_share(e_lead ** 2, e ** 2):.0%}"
            C.log(f"    {k:<16}{np.abs(v - base).mean() / 1e6:>26.3f}"
                  f"{np.sqrt((e ** 2).mean()):>10.3f}{np.abs(e).mean():>8.3f}"
                  f"{e.mean():>+9.3f}{share:>14}")
        C.log("")


def main() -> None:
    C.banner("run_skater_contract_test.py", SCRIPT_VERSION)
    path, how = birthdate_source()
    C.log(f"  birthdates: {how}")
    table = build_table(birthdate_csv=path, verbose=False)
    from contract_source import load_contracts
    contracts, _ = load_contracts()
    spans = contract_spans(contracts)
    spans = spans[~spans["pkey"].str.endswith("|G")]
    mechanism(table, spans)
    har = H.Harness(table)
    runs = {}
    for k, cls in VARIANTS.items():
        runs[k] = har.run(cls(), pages=C.DEV_PAGES, horizons=HORIZONS)
        C.log(f"  ran {k}: {len(runs[k])} forecasts")
    C.log("")
    season_scores(runs)
    dollars(table)
    out = pd.concat([d.assign(variant=k) for k, d in runs.items()], ignore_index=True)
    out.to_csv(C.out_path("skater_contract_test.csv"), index=False)
    C.write_log("skater_contract_test_run_log.txt")


if __name__ == "__main__":
    main()
