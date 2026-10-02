"""xnpv1_position_compression.py -- does xNPV 1 pull defencemen's forecasts toward the league
harder than forwards', and do real outcomes do the same?

WHY (2026-10-02). The price line re-fitted on xNPV 1's forecast (xnpv1_price_line.py) raised
the forward price per win from $2.03M to $2.95M and the defence price from $2.30M to $4.35M.
If the forecast compresses defencemen more, a per-forecast-win slope must rise more for them.
This measures that compression, and checks it against what actually happened.

WHAT IT MEASURES. Every player-page xNPV 1 forecasts on pages 2018-2025 (the Stage 3 start
years) that also has a Stage 3 trailing total (prorated 60/40, skater_value_engine). This is
the forecast population, not the 2,347 contracts. Rows repeat players across pages; the
player counts are printed beside the rows. For each position, it fits two straight lines on
the trailing total:
    forecast  xNPV 1's WAR if he plays, the page season (h = 0);
    realised  the page season's actual WAR, among players who played in it.

CONTRACT STATUS IS SYNTHETIC. The cloud has no PuckPedia export, so contract status is
stubbed (every played season under contract). It feeds only the chance of playing. WAR if he
plays (rate per 82 x games share) reads no contract input, so the figures here do not depend
on the stub.

RESULT (cloud, 2026-10-02): forwards forecast 0.206 + 0.690 x trailing and realised 0.195 +
0.734 x trailing (4,646 rows, 1,022 players); defence forecast 0.106 + 0.609 x trailing and
realised 0.151 + 0.618 x trailing (2,471 rows, 539 players).

HOW TO RUN (from the repo root): python 25_TESTS/xnpv1_position_compression.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
import numpy as np
import pandas as pd
import participation_model as PM
import contract_source as CS
import player_season_table as PST
import skater_value_engine as SVE
import skater_forecast as SF

# ---- synthetic contract status (feeds only the chance of playing; see the docstring) ----
bd, _ = PST.birthdate_source()
t = PST.build(birthdate_csv=bd, verbose=False)
s = t[(t["syr"] >= 2010) & (t["GP"] > 0)][["pkey", "syr"]].drop_duplicates()
spans = pd.DataFrame({"pkey": s["pkey"].to_numpy(), "start_yr": s["syr"].to_numpy(),
                      "end_yr": s["syr"].to_numpy() + 1,
                      "signed": pd.to_datetime([f"{y}-06-01" for y in s["syr"]]),
                      "contract_level": "standard", "signing_status": "UFA"})
CS.load_contracts = lambda: (pd.DataFrame({"x": [1]}), "utf-8")
PM.contract_spans = lambda contracts: spans

# ---- trailing total (the Stage 3 input), the forecast, and the realised season ---------
lut = SVE.build_skater_war_lookup(exclude_merged=False, prorate=True)   # same lookup Stage 3 uses
real = t.groupby(["pkey", "syr"]).agg(WAR=("WAR", "sum"), GP=("GP", "sum")).reset_index()
fc = SF.ContractForecaster()
rows = []
for t0 in range(2018, 2026):
    for pk in sorted(fc.career_of):
        tr = SVE.trailing_weighted_war(pk, t0, lut)[0]
        if tr is None or pd.isna(tr):
            continue
        f = fc.forecast(pk, t0, 0)          # the same call xnpv1_price_line.py makes
        if f is None:
            continue
        rows.append((pk, t0, pk.endswith("|D"), float(tr), float(f.iloc[0]["war_if_plays"])))
d = (pd.DataFrame(rows, columns=["pkey", "syr", "is_d", "trail", "xw"])
     .merge(real, on=["pkey", "syr"], how="left"))
for lab, g in (("forwards", d[~d.is_d]), ("defence", d[d.is_d])):
    b = np.polyfit(g.trail, g.xw, 1)
    pl = g[g.GP.fillna(0) > 0]                # realised only where he played
    r = np.polyfit(pl.trail, pl.WAR, 1)
    print(f"{lab:<9} n {len(g):>5} ({g.pkey.nunique()} players): forecast = {b[1]:+.3f} + {b[0]:.3f} x trailing;"
          f"  realised (n {len(pl)}) = {r[1]:+.3f} + {r[0]:.3f} x trailing")
    for lo, hi in ((1, 2), (2, 3), (3, 99)):
        x = g[(g.trail >= lo) & (g.trail < hi)]
        y = x[x.GP.fillna(0) > 0]
        print(f"     trailing {lo}-{hi if hi < 99 else '+'}: n {len(x):>4}  trailing {x.trail.mean():.2f}  "
              f"forecast {x.xw.mean():.2f}  realised {y.WAR.mean():.2f} (n {len(y)})")
