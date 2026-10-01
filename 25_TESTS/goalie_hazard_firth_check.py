"""goalie_hazard_firth_check.py -- does the goalie exit-risk table take the separation path?

READ-ONLY. Writes nothing. Run on the laptop (it needs the contract season
spine, which is built from the PuckPedia export).

WHY
    exit_hazard.py v1.3 (2026-09-30) fits a table with Firth's penalty when a
    quality bucket or age group in its data has no exits, or no stays. Skater
    tables were checked. The goalie table (contract_npv.NPVEngine.h_g, fitted
    once on every goalie transition, ages from the spine birthdates) was not,
    because the cloud has no spine. If it takes the Firth path, goalie values
    changed with v1.3 and the dashboard should be refreshed; if not, the goalie
    table is byte-for-byte what it was.

WHAT IT PRINTS
    exits and transitions per quality bucket and per age group, which levels
    (if any) are separated, the path the fit took, and the fitted table.

HOW TO RUN (Windows PowerShell, from the repo root):
    python 25_TESTS\\goalie_hazard_firth_check.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))

SCRIPT_VERSION = "1.0"


def report(d_g, fit_additive):
    """Print the separation check and the fit path for a goalie transition table."""
    dd = d_g[d_g["age_grp"] != "unknown"].copy()
    dd["y"] = dd["exited"].astype(int)
    print(f"  goalie transitions with an age: {len(dd):,} of {len(d_g):,}")
    sep = []
    for col in ("bucket", "age_grp"):
        g = dd.groupby(col)["y"].agg(["sum", "count"])
        print(f"  exits by {col}: " + ", ".join(f"{k} {int(r['sum'])}/{int(r['count'])}"
                                                 for k, r in g.iterrows()))
        sep += [f"{col}={k}" for k, r in g.iterrows() if r["sum"] in (0, r["count"])]
    res, _ = fit_additive(d_g)
    path = getattr(res, "mle_retvals", {}).get("method", "ordinary maximum likelihood")
    print(f"  separated levels: {', '.join(sep) if sep else 'none'}")
    print(f"  fit path: {path}")
    print("  VERDICT: " + ("the goalie table TAKES the Firth path, so goalie values changed with "
                          "exit_hazard v1.3; refresh the dashboard" if sep else
                          "the goalie table takes the unchanged path; goalie values did not move"))
    return sep


def main():
    print(f"goalie_hazard_firth_check.py v{SCRIPT_VERSION}")
    import contract_npv as N
    import exit_hazard as EH
    print(f"  reading {Path(N.__file__).resolve()} and {Path(EH.__file__).resolve()}")
    eng = N.NPVEngine()          # builds the goalie table exactly as pricing does
    report(eng._d_g, EH._fit_additive)
    print("  fitted goalie table (bucket, age group): exit risk")
    for k, v in sorted(eng.h_g.items()):
        print(f"    {k}: {v:.4f}")


if __name__ == "__main__":
    main()
