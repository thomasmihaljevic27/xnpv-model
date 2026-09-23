"""run_goalie_participation_top.py -- why is the goalie participation model too sure?

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 5, the goalie branch. Development
pages only. A diagnosis and a measured candidate; nothing adopted.

THE SYMPTOM
    In its most confident fifth, the goalie participation model predicts 95%
    of goaltender-seasons played where 86% were -- a gap that survives
    resampling goaltenders -- while the pooled checks pass. Priced, it shows
    up as too many contracts delivering floor-level value.

WHAT THIS RUNNER ESTABLISHES, IN ORDER
    1. Where the gap sits: by valuation page, by target season, by horizon,
       and what happened to the goaltenders it missed.
    2. The mechanism: the contract export is a SNAPSHOT. Every contract in it
       ends in or after one year (2018 here). On an early page the goaltenders
       it "knows" are therefore the ones who went on to sign a deal running
       into its era -- survivors -- and the model's contract columns learned
       survival. On later pages nearly everyone is known, including goaltenders
       who have retired, and the model reads "known" as "will play".
    3. The replacements, scored on the hierarchy declared on 2026-09-22
       (squared error primary; absolute error and bias beside it) and on the
       confident fifth that raised the question. FIVE specifications, because
       the "observable" definition carries TWO new inputs and they have to be
       separated before either is credited:
         current        export membership (every recorded run)
         none           no contract inputs
         observable     both new inputs
         period_only    the before/after-2018 indicator alone
         contract_only  visible contract status alone
       Under "observable", `contract_unknown` is 1 exactly when the target
       season is before 2018 -- the same for every goaltender targeting that
       season. It is a PERIOD indicator, not information about the player.
       Version 1.0 compared "observable" with "none" and credited the gain to
       contract information; the intermediate specifications show the period
       indicator carries it (see the report).

    The measured effect on contract dollars is a separate run: the goalie
    control-year runner with `--participation observable`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import forecast_harness as H
import goalie_season_table as GST
import run_goalie_participation as GP
from participation_model import (contract_spans, players_with_any_contract,
                                 under_contract_at, CONTRACT_FEATURES)
from contract_source import load_contracts
from player_season_table import birthdate_source

SCRIPT_VERSION = "1.1"
HORIZONS = GP.HORIZONS


def _variant(name: str, label: str):
    return type(f"V_{name}", (GP.PartOnly,), {"name": label, "part_variant": name})


Current = _variant("as_known", "current: export membership")
NoContracts = _variant("none", "no contract inputs")
Observable = _variant("observable", "period + contract status")
PeriodOnly = _variant("period_only", "period indicator only")
ContractOnly = _variant("contract_only", "contract status only")
VARIANTS = (Current, NoContracts, Observable, PeriodOnly, ContractOnly)


def ci(d: pd.DataFrame, stat, n: int = 2000, seed: int = 20260923) -> tuple:
    g = {k: v for k, v in d.groupby("career_key")}
    ks = list(g)
    rng = np.random.default_rng(seed)
    b = [stat(pd.concat([g[k] for k in rng.choice(ks, len(ks), replace=True)]))
         for _ in range(n)]
    lo, hi = np.percentile(b, [2.5, 97.5])
    return float(stat(d)), float(lo), float(hi)


def paired(a: pd.DataFrame, b: pd.DataFrame, col: str, n: int = 2000) -> float:
    """Share of goaltender-resamples in which b's mean `col` is lower than a's."""
    keys = ["career_key", "page", "h"]
    j = a[keys + [col]].merge(b[keys + [col]], on=keys, suffixes=("_a", "_b"),
                              validate="one_to_one")
    g = {k: v for k, v in j.groupby("career_key")}
    ks = list(g)
    rng = np.random.default_rng(20260923)
    w = 0
    for _ in range(n):
        s = pd.concat([g[k] for k in rng.choice(ks, len(ks), replace=True)])
        w += int(s[f"{col}_b"].mean() < s[f"{col}_a"].mean())
    return w / n


def mechanism(table: pd.DataFrame, spans: pd.DataFrame) -> None:
    C.log("THE MECHANISM. The contract export is a snapshot.")
    first = int(spans["end_yr"].min())
    g = spans[spans["pkey"].str.endswith("|G")]
    C.log(f"  every contract in it ends in {first} or later; goaltender contracts by")
    C.log(f"  end year: {g.groupby('end_yr').size().to_dict()}")
    C.log("")
    C.log("  So on an early page, the goaltenders the export knows are those who")
    C.log("  signed a deal running into its era. Share of goalie anchors known,")
    C.log("  under a visible contract, and how often each group played:")
    C.log("")
    a = GP.goalie_anchors(table[table["GP"] >= C.MIN_GP])
    act = table.set_index(["career_key", "syr"])["GP"]
    C.log(f"    {'page':<6}{'h':>3}{'known':>8}{'under':>8}{'played if':>12}"
          f"{'played if known,':>18}{'played if':>11}")
    C.log(f"    {'':<6}{'':>3}{'':>8}{'':>8}{'unknown':>12}{'not under (n)':>18}{'under':>11}")
    for h in (0, 3):
        for t0, grp in a.groupby("t0"):
            if t0 < 2010 or t0 > 2022 or t0 + h > C.LAST_SOURCE_SEASON:
                continue
            asof = pd.Timestamp(year=int(t0), month=7, day=1)
            k = grp["pkey"].isin(players_with_any_contract(spans, asof)).to_numpy()
            uc = under_contract_at(spans, asof, [int(t0 + h)])
            u = grp["pkey"].isin(set(uc["pkey"]) if len(uc) else set()).to_numpy()
            ix = pd.MultiIndex.from_arrays([grp["career_key"], grp["t0"] + h])
            y = act.reindex(ix).fillna(0).to_numpy() >= C.PARTICIPATION_GP
            f = lambda m: f"{y[m].mean():.2f}" if m.any() else "--"
            C.log(f"    {int(t0):<6}{h:>3}{k.mean():>8.2f}{u.mean():>8.2f}{f(~k):>12}"
                  f"{f(k & ~u) + ' (' + str(int((k & ~u).sum())) + ')':>18}{f(u):>11}")
        C.log("")
    C.log("  Up to 2015, every goaltender under a visible contract played, at both")
    C.log("  horizons: in those rows the contract columns are a survival flag. From")
    C.log("  2019 nearly every goaltender is known, and the known-but-unsigned ones")
    C.log("  play about half the time. A fit trained on the first and applied to")
    C.log("  the second reads 'known' as 'will play'.")
    C.log("")


def where(d: pd.DataFrame, table: pd.DataFrame) -> None:
    cut = d["p_play"].quantile(0.8)
    top = d[d["p_play"] >= cut].copy()
    top["target"] = top["page"] + top["h"]
    C.log(f"WHERE THE CONFIDENT FIFTH MISSES (current model; predictions >= {cut:.3f},")
    C.log(f"{len(top)} cells). Predicted / observed:")
    for col, lab in (("page", "valuation page"), ("target", "target season"), ("h", "horizon")):
        parts = [f"{int(k)}: {g['p_play'].mean():.2f}/{g['played'].mean():.2f} (n={len(g)})"
                 for k, g in top.groupby(col)]
        C.log(f"  by {lab}:")
        for i in range(0, len(parts), 4):
            C.log("    " + "   ".join(parts[i:i + 4]))
    miss = top[~top["played"]]
    last = table.groupby("career_key")["syr"].max()
    ended = (last.reindex(miss["career_key"]).to_numpy() < miss["target"].to_numpy())
    C.log(f"  {len(miss)} missed cells over {miss['career_key'].nunique()} goaltenders; in "
          f"{ended.mean():.0%} of them the goaltender")
    C.log("  never played an NHL season again -- careers that had ended, predicted")
    C.log("  as near-certain to continue.")
    C.log("")


def period_shape(d: pd.DataFrame) -> None:
    """Is the post-2018 shift a step or a drift? Observed minus predicted
    participation by target season, for the model with no contract inputs
    (which has no period term), with a goaltender-resampled interval. A step
    would sit flat on each side of 2018; a drift would slope through it."""
    C.log("  WHAT THE PERIOD INDICATOR IS ABSORBING. Observed minus predicted")
    C.log("  participation by target season, the model with no contract inputs:")
    x = d.assign(t=d["page"] + d["h"], r=d["played"].astype(float) - d["p_play"])
    for t, g in x.groupby("t"):
        v, lo, hi = ci(g, lambda z: z["r"].mean())
        C.log(f"    {int(t)}  {v:+.3f} [{lo:+.3f}, {hi:+.3f}]   n={len(g)}")
    C.log("  The boundary is the export's earliest end year, not a fact about")
    C.log("  goaltending. These rows say where the residual moves; they do not say")
    C.log("  why, or that 2018 is the right place to put a step.")
    C.log("")


def dollars_across_runs() -> None:
    """How much the candidate moves contract-dollar error, on ONE fixed line.

    The goalie control-year runner is run twice -- default participation, and
    `--participation observable` -- and each run refits its price lines on its
    own forecasts. Comparing the two runs' printed scores would score each
    against a target priced on a different line. So both runs' drawn WAR paths
    are repriced here on one line: the default run's production line (the
    current currency), with the candidate run's production line as the
    sensitivity. The realised target is asserted identical across runs.
    """
    import pickle
    import npv_simulation as SIM
    files = {"current": C.out_path("goalie_control_years.pkl")}
    for v in ("observable", "period_only"):
        files[v] = C.out_path(f"goalie_control_years_{v}.pkl")
    files = {k: f for k, f in files.items() if Path(f).exists()}
    if "current" not in files or len(files) < 2:
        C.log("  (contract dollars across runs skipped: run run_goalie_control_years.py")
        C.log("   with and without --participation observable first)")
        return
    # The control-year runner pickles its price lines as instances of a class
    # defined in the module that was run as a script; map that name back.
    import __main__
    import run_goalie_control_years as GCY
    __main__.GoalieCurrency = GCY.GoalieCurrency
    runs = {k: pickle.load(open(f, "rb")) for k, f in files.items()}
    common = sorted(set.intersection(*[set(r["common"]) for r in runs.values()]))
    table = GST.build(verbose=False, allow_thin_ages=True)
    lut = table[table["GP"] >= C.PARTICIPATION_GP].groupby(["pkey", "syr"])["WAR"].sum()
    C.log("CONTRACT DOLLARS BY PARTICIPATION SPECIFICATION, every run repriced on ONE")
    C.log(f"line; {len(common)} ended contracts both runs price. $M.")
    C.log("")
    for line_run in runs:
        lines = runs[line_run]["priced"]["production"][1]
        C.log(f"  on the {line_run} run's production line"
              f" ({'PRIMARY' if line_run == 'current' else 'sensitivity'}):")
        C.log(f"    {'forecast':<12}{'participation':<14}{'RMSE':>8}{'MAE':>8}{'bias':>9}")
        rec = []
        for cid in common:
            row0 = runs["current"]["priced"]["production"][0].set_index("contract_id").loc[cid]
            cur = lines[row0["cut"]]
            k = SIM.dollar_factor(row0)
            yrs = list(range(int(row0["start_yr"]), int(row0["end_yr"]) + 1))
            w = np.array([float(lut.get((row0["pkey"], y), 0.0)) for y in yrs])
            r = {"contract_id": cid, "career_key": row0["pkey"]}
            tg = []
            for run in runs:
                for fc in ("production", "rate"):
                    row = runs[run]["priced"][fc][0].set_index("contract_id").loc[cid].copy()
                    row["contract_id"] = cid
                    tg.append(float(SIM.contract_value(cur, row, np.array([w.mean()]),
                                                       np.array([w[0]]), k)[0]))
                    wps, y1 = runs[run]["draws"][fc][cid]
                    r[f"{fc}|{run}"] = float(SIM.contract_value(cur, row, wps, y1, k).mean())
            assert max(tg) - min(tg) < 1e-6, f"contract {cid}: the realised target moved"
            r["realised"] = tg[0]
            rec.append(r)
        d = pd.DataFrame(rec)
        g = {kk: v for kk, v in d.assign(**{
            f"se|{fc}|{run}": ((d[f"{fc}|{run}"] - d["realised"]) / 1e6) ** 2
            for fc in ("production", "rate") for run in runs}).groupby("career_key")}
        ks = list(g)
        rng = np.random.default_rng(20260923)
        draws = [rng.choice(ks, len(ks), replace=True) for _ in range(2000)]
        for fc in ("production", "rate"):
            for run in runs:
                e = (d[f"{fc}|{run}"] - d["realised"]) / 1e6
                tail = ""
                if run != "current":
                    wins = 0
                    for pick in draws:
                        ss = pd.concat([g[kk] for kk in pick])
                        wins += int(ss[f"se|{fc}|{run}"].mean() < ss[f"se|{fc}|current"].mean())
                    tail = f"   beats current in {wins / 2000:.0%}"
                C.log(f"    {fc:<12}{run:<14}{np.sqrt((e ** 2).mean()):>8.3f}"
                      f"{e.abs().mean():>8.3f}{e.mean():>+9.3f}{tail}")
        C.log("")


def main() -> None:
    C.banner("run_goalie_participation_top.py", SCRIPT_VERSION)
    path, _ = birthdate_source()
    table = GST.build(birthdate_csv=path, verbose=False, allow_thin_ages=True)
    contracts, _ = load_contracts()
    spans = contract_spans(contracts)
    har = H.Harness(table)
    runs = {}
    for cls in VARIANTS:
        runs[cls.name] = har.run(cls(), pages=C.DEV_PAGES, horizons=HORIZONS)
    cur = runs[Current.name]
    for d in runs.values():
        d["se_war"] = d["e_war"] ** 2
        d["ae_war"] = d["e_war"].abs()
    where(cur, table)
    mechanism(table, spans)

    C.log("THE CANDIDATE, scored. Participation; then the season it feeds, with")
    C.log("production's projector and trailing share held fixed. Squared error is")
    C.log("the primary score (declared 2026-09-22). 'lower in' is the share of")
    C.log("goaltender-resamples in which the variant beats the current model.")
    C.log("")
    C.log(f"    {'variant':<34}{'Brier':>8}{'lower in':>10}{'WAR RMSE':>10}{'lower in':>10}"
          f"{'WAR MAE':>9}{'bias':>8}")
    for name, d in runs.items():
        if d is cur:
            C.log(f"    {name:<34}{d['brier'].mean():>8.4f}{'--':>10}"
                  f"{np.sqrt(d['se_war'].mean()):>10.3f}{'--':>10}"
                  f"{d['ae_war'].mean():>9.3f}{d['e_war'].mean():>+8.3f}")
            continue
        C.log(f"    {name:<34}{d['brier'].mean():>8.4f}{paired(cur, d, 'brier'):>10.0%}"
              f"{np.sqrt(d['se_war'].mean()):>10.3f}{paired(cur, d, 'se_war'):>10.0%}"
              f"{d['ae_war'].mean():>9.3f}{d['e_war'].mean():>+8.3f}")
    C.log("  THE INPUTS SEPARATED. Share of goaltender-resamples in which the second")
    C.log("  specification has the lower Brier / the lower WAR squared error:")
    for a, b in ((NoContracts, Observable), (NoContracts, PeriodOnly),
                 (NoContracts, ContractOnly), (Observable, PeriodOnly),
                 (ContractOnly, Observable)):
        da, db = runs[a.name], runs[b.name]
        C.log(f"    {b.name:<26} against {a.name:<26} Brier {paired(da, db, 'brier'):>5.0%}"
              f"   WAR sq. error {paired(da, db, 'se_war'):>5.0%}")
    C.log("")
    period_shape(runs[NoContracts.name])
    C.log("  Brier by horizon:")
    C.log("    " + f"{'h':<4}" + "".join(f"{n[:22]:>24}" for n in runs))
    for h in HORIZONS:
        C.log("    " + f"{h:<4}" + "".join(
            f"{d.loc[d['h'] == h, 'brier'].mean():>24.4f}" for d in runs.values()))
    C.log("")
    C.log("  Calibration by fifth of each variant's own prediction (predicted/observed),")
    C.log("  and the confident fifth's over-prediction with a goaltender-resampled")
    C.log("  interval:")
    for name, d in runs.items():
        q = pd.qcut(d["p_play"], 5, labels=False, duplicates="drop")
        parts = [f"{g['p_play'].mean():.2f}/{g['played'].mean():.2f}" for _, g in d.groupby(q)]
        top = d[q == q.max()]
        v, lo, hi = ci(top, lambda x: (x["p_play"] - x["played"].astype(float)).mean())
        C.log(f"    {name:<34}" + "  ".join(parts))
        C.log(f"    {'':<34}top fifth {v:+.3f} [{lo:+.3f}, {hi:+.3f}]")
    C.log("")
    C.log("  Bias in season WAR by trailing role (thirds of trailing share):")
    cutr = pd.qcut(cur.set_index(["career_key", "page", "h"])["gp_share"], 3,
                   labels=["backup-ish", "middle", "starter-ish"])
    for role in ["backup-ish", "middle", "starter-ish"]:
        keys = cutr[cutr == role].index
        C.log(f"    {role:<13}" + "".join(
            f"{d.set_index(['career_key', 'page', 'h'])['e_war'].reindex(keys).mean():>+10.3f}"
            for d in runs.values()))
    C.log("")
    dollars_across_runs()
    out = pd.concat([d.assign(variant=n) for n, d in runs.items()], ignore_index=True)
    out.to_csv(C.out_path("goalie_participation_top.csv"), index=False)
    C.write_log("goalie_participation_top_run_log.txt")


if __name__ == "__main__":
    main()
