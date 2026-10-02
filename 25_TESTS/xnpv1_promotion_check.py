"""xnpv1_promotion_check.py -- does the promoted xNPV 1 forecast what the adopted one did?

WHAT IT CHECKS
    xNPV 1 was adopted (D33) as the rebuild class star_candidates.XNPV1 and
    promoted on 2026-10-02 as 20_CODE/skater_forecast.XNPV1, rewritten from only
    the code it runs. The promotion is right only if the two forecast the same
    thing. Each side is run in ITS OWN PYTHON PROCESS, because the promoted
    supporting modules keep their names (player_season_table, participation_
    model, ...) and one process importing both trees could silently mix them.

    Both sides use the same season table (production's birthdate rule,
    player_season_table.birthdate_source in 20_CODE) and are compared on:
      1. the harness forecasts on the development pages 2015-2021, zero to five
         seasons ahead: rate_82, gp_share, p_play, row for row;
      2. predict_beyond_fit on pages 2015 and 2021, six to twelve seasons ahead
         (the declared extension a long contract needs);
      3. p_play_signed on 300 players per page with dates spread through the
         season (contract status read at a signing).
    PASS means every value agrees to 1e-12.

HOW TO RUN (Windows PowerShell, from the repo root; needs the contract export):
    python 25_TESTS\\xnpv1_promotion_check.py
A cloud code test can add --synthetic (made-up contracts, both sides alike);
its PASS shows the code paths agree, not that the real export reads the same.
The harness lines it writes to the inspection ledger are development pages.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_VERSION = "1.0"
ROOT = Path(__file__).resolve().parents[1]
PAGES = (2015, 2016, 2017, 2018, 2019, 2020, 2021)
TOL = 1e-12

CHILD = r'''
import sys
from pathlib import Path
side, root, out, synthetic = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4] == "1"
code = root / ("20_CODE" if side == "production" else "50_REBUILD/code")
sys.path.insert(0, str(code))
import numpy as np, pandas as pd

# The same season table on both sides: each side's own season-table code,
# fed the one birthdate file the parent wrote with production's rule.
bd_path = Path(sys.argv[5])
import player_season_table as PST
table = PST.build(birthdate_csv=bd_path, verbose=False)

if synthetic:
    import participation_model as PM, contract_source as CS
    s = table[(table["syr"] >= 2017) & (table["GP"] > 0)][["pkey", "syr"]].drop_duplicates()
    spans = pd.DataFrame({"pkey": s["pkey"].to_numpy(), "start_yr": s["syr"].to_numpy(),
                          "end_yr": s["syr"].to_numpy() + 1,
                          "signed": pd.to_datetime([f"{y}-06-01" for y in s["syr"]]),
                          "contract_level": "standard", "signing_status": "UFA"})
    CS.load_contracts = lambda: (pd.DataFrame({"x": [1]}), "utf-8")
    PM.contract_spans = lambda contracts: spans

import forecast_harness as H, information_set as ISET
if side == "production":
    import skater_forecast as SF
    cls = SF.XNPV1
else:
    import star_candidates as SC
    cls = SC.XNPV1
pages = tuple(int(p) for p in sys.argv[6].split(","))
har = H.Harness(table)
d = har.run(cls(), pages=pages, horizons=(0, 1, 2, 3, 4, 5))
d[["career_key", "page", "h", "rate_82", "gp_share", "p_play", "act_war", "played"]].to_csv(out / f"{side}_harness.csv", index=False)

rows, sig = [], []
for t0 in (pages[0], pages[-1]):
    iset = ISET.build(table, ISET.decision_date_for_page(t0), t0=t0)
    subs = H.subjects_at(iset)
    m = cls(); m.fit(iset.seasons, before=t0)
    assert m.reads_contracts, "the model did not read contract status"
    p = m.predict_beyond_fit(iset, subs, list(range(0, 13)))
    rows.append(p.assign(page=t0)[["career_key", "page", "h", "rate_82", "gp_share", "p_play", "extrapolated"]])
    keys = subs["career_key"].to_numpy()[:300]
    dates = pd.to_datetime([f"{t0 - 1}-10-01"] * 100 + [f"{t0}-01-15"] * 100 + [f"{t0}-06-01"] * 100)[:len(keys)]
    ps = m.p_play_signed(iset, keys, list(range(0, 10)), dates)
    for h, v in ps.items():
        sig.append(pd.DataFrame({"career_key": keys, "page": t0, "h": h, "p_signed": v}))
pd.concat(rows).to_csv(out / f"{side}_beyond.csv", index=False)
pd.concat(sig).to_csv(out / f"{side}_signed.csv", index=False)
print(f"{side}: done ({len(d)} harness forecasts)")
'''


def run_side(side, out, synthetic, bd_path, pages):
    child = out / "child.py"
    child.write_text(CHILD, encoding="utf-8")
    r = subprocess.run([sys.executable, str(child), side, str(ROOT), str(out),
                        "1" if synthetic else "0", str(bd_path), ",".join(map(str, pages))],
                       cwd=ROOT, capture_output=True, text=True)
    tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-6:])
    if r.returncode != 0:
        raise SystemExit(f"{side} side failed:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    print(f"  {tail.splitlines()[-1] if tail else side}")


def compare(out, name, keys, cols):
    import numpy as np
    import pandas as pd
    a = pd.read_csv(out / f"production_{name}.csv").sort_values(keys).reset_index(drop=True)
    b = pd.read_csv(out / f"rebuild_{name}.csv").sort_values(keys).reset_index(drop=True)
    assert a[keys].equals(b[keys]), f"{name}: the two sides answered different rows"
    worst = {c: float(np.nanmax(np.abs(a[c].to_numpy(float) - b[c].to_numpy(float)))) for c in cols}
    nan_mismatch = {c: int((a[c].isna() != b[c].isna()).sum()) for c in cols}
    ok = all(v <= TOL for v in worst.values()) and not any(nan_mismatch.values())
    print(f"  {name:<8} {len(a):>6} rows  largest gap " +
          ", ".join(f"{c} {v:.1e}" for c, v in worst.items()) + ("" if not any(nan_mismatch.values())
          else f"  missing-value mismatches {nan_mismatch}") + f"   {'PASS' if ok else 'FAIL'}")
    return ok


def main(argv=sys.argv[1:]):
    print(f"xnpv1_promotion_check.py v{SCRIPT_VERSION}")
    synthetic = "--synthetic" in argv
    pages = (2015, 2021) if "--quick" in argv else PAGES
    if synthetic:
        print("  SYNTHETIC CONTRACTS: a code-path test only")
    sys.path.insert(0, str(ROOT / "20_CODE"))
    import player_season_table as PST                  # production's birthdate rule
    bd_path, how = PST.birthdate_source()
    print(f"  birthdates: {how}")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        for side in ("production", "rebuild"):
            run_side(side, out, synthetic, bd_path, pages)
        ok = [compare(out, "harness", ["career_key", "page", "h"], ["rate_82", "gp_share", "p_play", "act_war"]),
              compare(out, "beyond", ["career_key", "page", "h"], ["rate_82", "gp_share", "p_play", "extrapolated"]),
              compare(out, "signed", ["career_key", "page", "h"], ["p_signed"])]
    print("  VERDICT: " + ("PASS -- the promoted xNPV 1 forecasts what the adopted one did"
                           if all(ok) else "FAIL -- do not wire the promoted model in"))
    return all(ok)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
