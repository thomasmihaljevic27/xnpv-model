"""dollar_scoring.py -- scoring contract valuations against what happened, in
ONE currency. Shared by the goalie and skater Phase 5 runners.

EXPERIMENTAL (50_REBUILD). A library, not a runner: it reads realised seasons
only to SCORE, never to forecast or to decide a rule.

WHY ONE MODULE
    The goalie control-year runner built these pieces first, inline. The
    skater acceptance scoring needs the same ones -- the realised path, the
    term priced on the drawn paths, one declared scoring line with the
    realised target asserted identical across forecasts, player-resampled
    intervals, the randomized PIT for lumpy outcomes, and interval coverage
    against the model's own draws. A second copy is how a rule drifts, so they
    live here and both runners import them. Moved 2026-09-24 from
    `run_goalie_control_years.py` v1.4 without changing what they compute.

THE DISCIPLINE THEY ENFORCE
    * Every forecast's valuations AND the realised production are priced on
      the SAME line; the realised target is computed from each forecast's own
      contract row and asserted identical (to $1e-6), contract by contract.
      Each run's own line gives a different realised target, and comparing
      scores against different targets is not a comparison.
    * Squared error is the declared primary score; absolute error and bias sit
      beside it.
    * Intervals resample PLAYERS (`pkey`), because one player signs several
      contracts.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import rebuild_config as C
import npv_simulation as SIM
import predictive_interval as PI

KEY = "contract_id"
PIT_SEED = 20260923


def realised_path(table: pd.DataFrame):
    """WAR by (pkey, season), a season he did not play counting as zero."""
    played = table[table["GP"] >= C.PARTICIPATION_GP]
    lut = played.groupby(["pkey", "syr"])["WAR"].sum()

    def f(pkey, yrs) -> np.ndarray:
        return np.array([float(lut.get((pkey, int(y)), 0.0)) for y in yrs])
    return f


def term_extra(lines: dict, keep: dict):
    """The contract's own term priced on the drawn paths, on the forecast's OWN
    line (the own-line sensitivity), and the paths' term averages kept in
    `keep` so the same draws can be repriced on the common scoring line."""
    def f(cid, r, paths) -> dict:
        L = int(r["length"])
        wps, y1 = paths[:, :L].mean(axis=1), paths[:, 0].copy()
        keep[int(cid)] = (wps, y1)
        v = SIM.contract_value(lines[r["cut"]], r, wps, y1, SIM.dollar_factor(r))
        q10, q90 = np.percentile(v, [10, 90])
        return {"term_sim_mean": float(v.mean()), "term_sim_sd": float(v.std(ddof=1)),
                "term_sim_q10": float(q10), "term_sim_q90": float(q90),
                "cost": float(r["cost"]), "value_point": float(r["value_point"])}
    return f


def ci(values: pd.DataFrame, stat, n: int = 2000, seed: int = 20260923) -> tuple:
    """A statistic and its 95% interval from resampling PLAYERS (`pkey`)."""
    g = {k: v for k, v in values.groupby("pkey")}
    ks = list(g)
    rng = np.random.default_rng(seed)
    b = [stat(pd.concat([g[k] for k in rng.choice(ks, len(ks), replace=True)]))
         for _ in range(n)]
    lo, hi = np.percentile(b, [2.5, 97.5])
    return float(stat(values)), float(lo), float(hi)


def pit_block(d: pd.DataFrame, label: str) -> None:
    """Uniformity of randomized PITs, with player-resampled intervals.
    Under calibration: central 80% share 0.80, central 50% share 0.50, mean
    0.5, variance 1/12 = 0.0833. A variance BELOW 1/12 means outcomes sit
    nearer the middle than the forecast says -- too wide; above, too narrow."""
    rows = [("central 80% (0.1 to 0.9)", 0.80, lambda x: x["pit"].between(0.1, 0.9).mean()),
            ("central 50% (0.25 to 0.75)", 0.50, lambda x: x["pit"].between(0.25, 0.75).mean()),
            ("mean", 0.5, lambda x: x["pit"].mean()),
            ("variance", 1 / 12, lambda x: x["pit"].var(ddof=0))]
    C.log(f"    {label}  ({len(d)} outcomes)")
    for name, want, stat in rows:
        v, lo, hi = ci(d, stat)
        flag = "" if lo <= want <= hi else "   <- outside"
        C.log(f"      {name:<28}{v:>8.3f}   [{lo:.3f}, {hi:.3f}]   calibrated {want:.3f}{flag}")


def career_bootstrap(d: pd.DataFrame, a: str, b: str, n: int = 2000,
                     seed: int = 20260922) -> float:
    """Share of player-resamples in which column b's mean is lower than
    column a's. Resamples players, since one signs several contracts."""
    g = {k: v for k, v in d.groupby("pkey")}
    ks = list(g)
    rng = np.random.default_rng(seed)
    wins = 0
    for _ in range(n):
        s = pd.concat([g[k] for k in rng.choice(ks, len(ks), replace=True)])
        wins += int(s[b].mean() < s[a].mean())
    return wins / n


def score_on_line(common, rows_of: dict, lines: dict, draws: dict, labels,
                  real) -> pd.DataFrame:
    """Every forecast's point and simulated valuations, and the realised path,
    priced on ONE line (`lines`). The realised target is computed from each
    forecast's own contract row and asserted identical -- it cannot depend on
    which forecast is being scored. The first label's row supplies the cut,
    the dollar factor and the seasons, which the assertion then covers."""
    out = []
    for cid in common:
        rp = rows_of[labels[0]].loc[cid]
        cur = lines[rp["cut"]]
        k = SIM.dollar_factor(rp)
        yrs = list(range(int(rp["start_yr"]), int(rp["end_yr"]) + 1))
        w = real(rp["pkey"], yrs)
        targets = []
        rec = {KEY: cid, "pkey": rp["pkey"]}
        for lab in labels:
            row = rows_of[lab].loc[cid].copy()
            row[KEY] = cid
            targets.append(float(SIM.contract_value(cur, row, np.array([w.mean()]),
                                                    np.array([w[0]]), k)[0]))
            rec[f"point_{lab}"] = float(cur.value(pd.DataFrame([row])).iloc[0])
            wps, y1 = draws[lab][cid]
            v = SIM.contract_value(cur, row, wps, y1, k)
            rec[f"sim_{lab}"] = float(v.mean())
            rec[f"draws_{lab}"] = v
        assert max(targets) - min(targets) < 1e-6, (
            f"contract {cid}: the realised target differs by forecast")
        rec["realised"] = targets[0]
        out.append(rec)
    return pd.DataFrame(out)


def report_scores(d: pd.DataFrame, labels, exact: bool = False) -> None:
    """RMSE, MAE and bias for each forecast's point and simulated valuation,
    and each later label against the first on player-resampled shares.
    Adds the squared and absolute error columns to `d`. `exact` prints the
    shares as counts of 2,000 rather than rounded percents."""
    C.log(f"    {'forecast':<12}{'valuation':<11}{'RMSE':>8}{'MAE':>8}{'bias':>9}")
    for lab in labels:
        for how_ in ("point", "sim"):
            e = (d[f"{how_}_{lab}"] - d["realised"]) / 1e6
            d[f"se_{how_}_{lab}"], d[f"ae_{how_}_{lab}"] = e ** 2, e.abs()
            C.log(f"    {lab:<12}{('point' if how_ == 'point' else 'simulated'):<11}"
                  f"{np.sqrt((e ** 2).mean()):>8.3f}{e.abs().mean():>8.3f}{e.mean():>+9.3f}")
    fmt = (lambda x: f"{int(round(x * 2000))}/2000") if exact else (lambda x: f"{x:.0%}")
    ref = labels[0]
    for other in labels[1:]:
        for how_ in ("sim", "point"):
            ws = career_bootstrap(d, f"se_{how_}_{ref}", f"se_{how_}_{other}")
            wa = career_bootstrap(d, f"ae_{how_}_{ref}", f"ae_{how_}_{other}")
            C.log(f"    {other} against {ref}, {('simulated' if how_ == 'sim' else 'point')}: "
                  f"lower squared error in {fmt(ws)}, lower absolute in {fmt(wa)}")


def calibration_block(d: pd.DataFrame, labels) -> None:
    """Is the contract distribution calibrated? The floor puts many draws at
    exactly one value, so an interval's coverage is compared with its coverage
    of the MODEL'S OWN DRAWS, and the randomized PIT (uniform under
    calibration, lumps or not) is tested directly. Seeded per contract."""
    for lab in labels:
        rng_pit = []
        cov = []
        for r in d.itertuples():
            v = getattr(r, f"draws_{lab}")
            u = float(np.random.default_rng([PIT_SEED, int(r.contract_id)]).random())
            rng_pit.append(PI.randomized_pit(v, r.realised, u))
            q10, q25, q75, q90 = np.percentile(v, [10, 25, 75, 90])
            floor = float(v.min())
            cov.append({"own80": np.mean((v >= q10) & (v <= q90)),
                        "obs80": float(q10 <= r.realised <= q90),
                        "own50": np.mean((v >= q25) & (v <= q75)),
                        "obs50": float(q25 <= r.realised <= q75),
                        "atom": np.mean(v == floor),
                        "real_at_floor": float(abs(r.realised - floor) < 1e-6)})
        dd = pd.concat([d[[KEY, "pkey"]].reset_index(drop=True),
                        pd.DataFrame(cov), pd.Series(rng_pit, name="pit")], axis=1)
        v, lo, hi = ci(dd, lambda x: (x["real_at_floor"] - x["atom"]).mean())
        C.log(f"  {lab}: {dd['atom'].mean():.1%} of each contract's draws sit exactly on "
              f"its lowest value (the floor); {dd['real_at_floor'].mean():.1%} of outcomes do")
        C.log(f"    outcomes on the floor minus the model's own share: {100 * v:+.1f} points "
              f"[{100 * lo:+.1f}, {100 * hi:+.1f}]")
        for band in ("80", "50"):
            v, lo, hi = ci(dd, lambda x, b=band: (x[f"obs{b}"] - x[f"own{b}"]).mean())
            C.log(f"    {band}% interval: holds {dd[f'obs{band}'].mean():.1%} of outcomes "
                  f"against {dd[f'own{band}'].mean():.1%} of its own draws; excess "
                  f"{100 * v:+.1f} points [{100 * lo:+.1f}, {100 * hi:+.1f}]")
        pit_block(dd, f"{lab}, randomized PIT of the term value")
        C.log("")
