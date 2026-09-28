"""run_exit_hazard_window_test.py -- the exit hazard fitted only on what a page could know.

EXPERIMENTAL (50_REBUILD). Development pages 2015-2021 only. Nothing is
adopted by this run and no production file is edited.

THE QUESTION
    Production's exit hazard (`20_CODE/exit_hazard.py`) is one table,
    estimated on transitions t = 2018-2024 (exit read at t+1) and applied to
    every valuation page. A 2018 valuation therefore reads exits that
    happened in 2019-2025: the look-ahead the aging curve's D3 revision
    removed (2026-09-28), left in the hazard as review item 5.1.

    The window started at 2018 for a stated reason (exit_hazard.py, "Design
    choices"): the age join was essentially complete only from 2018, so
    older years would undercount exits among the players it missed. Since
    2026-09-28 the age join carries the Elite Prospects ages (99.9% of rows),
    so that reason is gone, and a window reaching back to 2007 is usable.

THE ARMS (the live chain as adopted: per-page aging curve; only the hazard changes)
    current           production: t = 2018-2024 for every page
    pre_expanding     page t0 uses t = 2007 .. t0-2 (the exit season t+1 finished
                      before the page; every earlier transition kept)
    pre_rolling7      page t0 uses the seven transition years t0-8 .. t0-2, the
                      same width as production's window
    all_2007_2024     t = 2007-2024 for every page: still sees the future, but
                      moves the start back; it separates "more history" from
                      "no future" (neither pre-valuation arm can)
    The rolling width (seven) is production's own, not searched. For the 2015
    page both pre-valuation arms read t = 2007-2013.

THE SCORES, DECLARED BEFORE THE RUN
    Participation: Brier score on the harness's played-or-not outcome (the
    thing the hazard predicts). Season WAR (rate x games share x
    participation): squared error. Both on the same rows for every arm, the
    full grid and the rows production answers. The rate per 82 cannot move
    (asserted), so any WAR change is the hazard's. Shares of 2,000 player
    resamples print as counts.

GUARDS
    * an arm set to t = 2018-2024 reproduces ProductionChain exactly;
    * every arm returns identical rate_82 and gp_share on every row;
    * the hazard table's own guards (no certain cells, calibration) run on
      every page's fit, as they do in production.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import forecast_harness as H
from player_season_table import build as build_table
import production_adapter as PA
from run_skater_contract_test import Boot, _count
import run_aging_choices_test as RAC

SCRIPT_VERSION = "1.0"
HORIZONS = RAC.HORIZONS
FIRST_SEASON = 2007          # WAR.csv starts at 2007-08


class HazardWindow(PA.ProductionChain):
    """The live chain with its exit-hazard table refitted for the page."""
    WINDOW = None            # callable(t0) -> (t_first, t_last)
    _tables: dict = {}

    def fit(self, table, before):
        super().fit(table, before)
        t_first, t_last = self.WINDOW(before)
        key = (t_first, t_last)
        if key not in self._tables:
            SFP = sys.modules["skater_forward_projection"]
            from exit_hazard import build_transitions, build_hazard_table
            d = build_transitions(C.F_WAR_SKATERS, Path(SFP.F_WAR_AGE),
                                  t_first=t_first, t_last=t_last)
            self._tables[key] = (build_hazard_table(d), len(d), float(d["exited"].mean()),
                                 float(d["age"].notna().mean()))
        self.haz_ = self._tables[key][0]
        self.window_ = key


def _arm(tag, label, window):
    return type(f"Hazard_{tag}", (HazardWindow,), {"name": f"current, {label}",
                                                   "WINDOW": staticmethod(window)})


ARMS = {
    "current": PA.ProductionChain,
    "pre_expanding": _arm("pre_exp", "hazard on transitions finished before the page (from 2007)",
                          lambda t0: (FIRST_SEASON, t0 - 2)),
    "pre_rolling7": _arm("pre_roll7", "hazard on the seven transition years before the page",
                         lambda t0: (t0 - 8, t0 - 2)),
    "all_2007_2024": _arm("all_2007", "hazard on 2007-2024 for every page",
                          lambda t0: (FIRST_SEASON, 2024)),
}
_SAME_AS_PRODUCTION = _arm("prod_window", "hazard on 2018-2024 (guard)", lambda t0: (2018, 2024))


def scores(runs, ref, label, mask=None):
    keys = ["career_key", "page", "h"]
    lead = runs[ref].set_index(keys).sort_index()
    al = {k: d.set_index(keys).sort_index() for k, d in runs.items()}
    for k, d in al.items():
        assert d.index.equals(lead.index), f"{k} answered different rows"
        assert np.array_equal(d["act_war"].to_numpy(), lead["act_war"].to_numpy()), f"{k} target differs"
    sel = np.ones(len(lead), bool) if mask is None else np.asarray(mask(lead.reset_index()), bool)
    base = lead.reset_index()[sel]
    boot = Boot(base["career_key"])
    out = []
    C.log(f"  {label}: {int(sel.sum())} forecasts, {base['career_key'].nunique()} players")
    C.log(f"    {'arm':<16}{'Brier':>9}{'lower':>11}{'WAR RMSE':>10}{'lower':>11}{'WAR MAE':>9}"
          f"{'bias':>9}{'mean p_play':>13}")
    for k, d in al.items():
        d = d.reset_index()[sel]
        se = d["e_war"] ** 2
        lb = "--" if k == ref else _count(boot.lower_share(base["brier"], d["brier"]))
        lw = "--" if k == ref else _count(boot.lower_share(base["e_war"] ** 2, se))
        row = dict(sample=label, arm=k, n=int(sel.sum()), brier=float(d["brier"].mean()),
                   rmse=float(np.sqrt(se.mean())), mae=float(d["e_war"].abs().mean()),
                   bias=float(d["e_war"].mean()), p_play=float(d["p_play"].mean()))
        C.log(f"    {k:<16}{row['brier']:>9.4f}{lb:>11}{row['rmse']:>10.4f}{lw:>11}"
              f"{row['mae']:>9.4f}{row['bias']:>+9.4f}{row['p_play']:>13.4f}")
        out.append(row)
    C.log("")
    C.log(f"    Brier by seasons ahead ({label}):")
    C.log("    " + f"{'arm':<16}" + "".join(f"{'h' + str(h):>9}" for h in HORIZONS))
    for k, d in al.items():
        d = d.reset_index()[sel]
        C.log("    " + f"{k:<16}" + "".join(f"{d.loc[d['h'] == h, 'brier'].mean():>9.4f}" for h in HORIZONS))
    C.log(f"    predicted minus observed participation by seasons ahead ({label}):")
    for k, d in al.items():
        d = d.reset_index()[sel]
        C.log("    " + f"{k:<16}" + "".join(
            f"{(d.loc[d['h'] == h, 'p_play'] - d.loc[d['h'] == h, 'played'].astype(float)).mean():>+9.3f}"
            for h in HORIZONS))
    C.log("")
    return pd.DataFrame(out)


def main() -> None:
    C.banner("run_exit_hazard_window_test.py", SCRIPT_VERSION)
    path, how = RAC._birthdates()
    C.log(f"  birthdates: {how}")
    table = build_table(birthdate_csv=path, verbose=False)
    har = H.Harness(table)
    runs = {"current": har.run(PA.ProductionChain(), pages=C.DEV_PAGES, horizons=HORIZONS)}
    g = har.run(_SAME_AS_PRODUCTION(), pages=C.DEV_PAGES, horizons=HORIZONS)
    key = ["career_key", "page", "h"]
    a, b = runs["current"].set_index(key).sort_index(), g.set_index(key).sort_index()
    assert a.index.equals(b.index) and all(np.array_equal(a[c].to_numpy(), b[c].to_numpy())
                                           for c in ("rate_82", "gp_share", "p_play")), \
        "the 2018-2024 arm does not reproduce production"
    C.log(f"  guard: the 2018-2024 window arm reproduces production on {len(a)} forecasts")
    for k, cls in ARMS.items():
        if k in runs:
            continue
        runs[k] = har.run(cls(), pages=C.DEV_PAGES, horizons=HORIZONS)
        x = runs[k].set_index(key).sort_index()
        assert np.array_equal(x["rate_82"].to_numpy(), a["rate_82"].to_numpy()) and \
               np.array_equal(x["gp_share"].to_numpy(), a["gp_share"].to_numpy()), f"{k} moved the rate"
        C.log(f"  ran {k}: {len(runs[k])} forecasts")
    C.log("  guard: every arm has production's rate and games share on every row")
    C.log("")
    C.log("  hazard tables fitted (window: transitions, overall exit rate, age coverage):")
    for (t1, t2), (_, n, rate, cov) in sorted(HazardWindow._tables.items()):
        C.log(f"    t = {t1}-{t2}: {n:>6,} transitions  exit {rate:6.2%}  ages {cov:6.1%}")
    C.log("")
    answer = lambda d: d["outside_production"].eq(0)
    s1 = scores(runs, "current", "full grid (production plus its fallback)")
    s2 = scores(runs, "current", "rows production answers", mask=answer)
    pd.concat([s1, s2]).to_csv(C.out_path("exit_hazard_window_summary.csv"), index=False)
    pd.concat([d.assign(arm=k) for k, d in runs.items()], ignore_index=True).to_csv(
        C.out_path("exit_hazard_window_forecasts.csv"), index=False)
    C.write_log("exit_hazard_window_run_log.txt")


if __name__ == "__main__":
    main()
