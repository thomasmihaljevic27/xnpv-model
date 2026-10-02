"""xnpv1_switch_check.py -- what switching skater contracts from xNPV 0 to xNPV 1 moves.

Migration plan step 3 (40_DOCS/model_evidence/xNPV1_Migration_Plan.md). Runs
20_CODE/contract_npv.py twice on this machine's live inputs, once under each
skater forecast (XNPV_SKATER_MODEL), each in its own process, and compares the
two NPV spines contract by contract with 20_CODE/npv_spine_compare.py.

ORDER, AND WHAT IS LEFT BEHIND
    1. xNPV 0 first. Its spine and run log are copied to a temporary folder
       OUTSIDE the repository (the working folder is staged wholesale by the
       sync, so no copy is left in it).
    2. xNPV 1 second, so 30_OUTPUT/contract_npv_spine.csv ends as the xNPV 1
       spine, with 30_OUTPUT/xnpv1_forecasts.csv beside it.
    3. The comparison log is written to 30_OUTPUT/xnpv1_switch_compare_log.txt
       (gitignored), plus this script's own summary in
       30_OUTPUT/xnpv1_switch_check_log.txt.

WHAT MUST HOLD
    * both runs exit cleanly with no guard-failure line;
    * every goalie contract is unchanged to $1 (the switch touches skaters only);
    * the skater spine rows say "xNPV 1" in the second run and "xNPV 0" in the
      first.
    The dollar movements themselves are reported, not judged: they are the
    switch's effect, to be read and explained.

HOW TO RUN (Windows PowerShell, from the repo root, after syncing; about two
contract_npv runs, so several minutes):
    python 25_TESTS\\xnpv1_switch_check.py
Send back 30_OUTPUT\\xnpv1_switch_check_log.txt and
30_OUTPUT\\xnpv1_switch_compare_log.txt.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_VERSION = "1.0"
ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "20_CODE"
FAIL_RE = re.compile(r"GUARD FAILED|HALTED|\bFAIL(ED)?\b|Traceback")
LINES = []


def say(s=""):
    print(s)
    LINES.append(str(s))


def run_npv(model: str) -> str:
    env = dict(os.environ, XNPV_SKATER_MODEL=model, PYTHONIOENCODING="utf-8")
    say(f"\n--- contract_npv.py under {model} ---")
    r = subprocess.run([sys.executable, str(CODE / "contract_npv.py")], cwd=ROOT, env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = r.stdout + r.stderr
    tail = [l for l in out.splitlines() if l.strip()][-12:]
    for l in tail:
        say("  | " + l)
    bad = [l for l in out.splitlines() if FAIL_RE.search(l)]
    if r.returncode != 0 or bad:
        say(f"  STOPPED: exit code {r.returncode}; failure lines: {bad[:5]}")
        raise SystemExit(1)
    return out


def main():
    say(f"xnpv1_switch_check.py v{SCRIPT_VERSION}")
    sys.path.insert(0, str(CODE))
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    out_dir = Path(os.environ["OUTPUT_DIR"])
    spine = out_dir / "contract_npv_spine.csv"
    import pandas as pd
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        run_npv("xNPV 0")
        shutil.copy2(spine, tmp / "spine_xnpv0.csv")
        run_npv("xNPV 1")
        old, new = pd.read_csv(tmp / "spine_xnpv0.csv"), pd.read_csv(spine)

        say("\n--- checks ---")
        for d, want in ((old, "xNPV 0"), (new, "xNPV 1")):
            sk = d[d["position"] == "skater"]
            labels = sorted(sk["model"].dropna().unique())
            say(f"  {want} spine: {len(d):,} contracts ({len(sk):,} skater); skater model label {labels}")
            assert labels == [want], f"the {want} spine's skater rows are labelled {labels}"
        key = ["contract_id", "valuation_season"]
        g = old[old["position"] == "goalie"].merge(new[new["position"] == "goalie"], on=key,
                                                  suffixes=("_0", "_1"), how="outer", indicator=True)
        assert (g["_merge"] == "both").all(), "a goalie contract is priced in only one run"
        gmax = float((g["npv_total_0"].round(0) - g["npv_total_1"].round(0)).abs().max())
        say(f"  goalies: {len(g):,} contracts in both runs, largest change ${gmax:,.0f}")
        assert gmax <= 1.0, "the switch moved a goalie contract"

        sk = old[old["position"] == "skater"].merge(new[new["position"] == "skater"], on=key,
                                                    suffixes=("_0", "_1"), how="outer", indicator=True)
        say(f"  skaters: {int((sk['_merge'] == 'both').sum()):,} priced by both, "
            f"{int((sk['_merge'] == 'left_only').sum()):,} by xNPV 0 only, "
            f"{int((sk['_merge'] == 'right_only').sum()):,} by xNPV 1 only")
        b = sk[sk["_merge"] == "both"].copy()
        b["d"] = (b["npv_total_1"] - b["npv_total_0"]).round(0)
        say(f"  on the {len(b):,} priced by both: {int((b['d'] > 0).sum()):,} up, {int((b['d'] < 0).sum()):,} down, "
            f"{int((b['d'] == 0).sum()):,} unchanged; net ${b['d'].sum() / 1e6:+,.1f}M; "
            f"median ${b['d'].median() / 1e6:+.2f}M")
        for lo, hi, lab in ((1, 2, "1-2 seasons"), (3, 5, "3-5 seasons"), (6, 20, "6+ seasons")):
            x = b[b["n_seasons_0"].between(lo, hi)]
            if len(x):
                say(f"    {lab:<12} {len(x):>5,} contracts: mean change ${x['d'].mean() / 1e6:+.2f}M, "
                    f"contract part ${(x['npv_contract_1'] - x['npv_contract_0']).mean() / 1e6:+.2f}M, "
                    f"terminal part ${(x['npv_terminal_1'] - x['npv_terminal_0']).mean() / 1e6:+.2f}M")
        say("  largest rises:")
        for r in b.nlargest(5, "d").itertuples():
            say(f"    {r.full_name_1:<24} {r.valuation_season}  {int(r.n_seasons_1)}yr  "
                f"${r.npv_total_0 / 1e6:+.2f}M -> ${r.npv_total_1 / 1e6:+.2f}M")
        say("  largest falls:")
        for r in b.nsmallest(5, "d").itertuples():
            say(f"    {r.full_name_1:<24} {r.valuation_season}  {int(r.n_seasons_1)}yr  "
                f"${r.npv_total_0 / 1e6:+.2f}M -> ${r.npv_total_1 / 1e6:+.2f}M")

        say("\n--- contract-by-contract comparison (npv_spine_compare.py) ---")
        import npv_spine_compare as NSC
        NSC.main(tmp / "spine_xnpv0.csv", spine, out_dir / "xnpv1_switch_compare_log.txt")
    (out_dir / "xnpv1_switch_check_log.txt").write_text("\n".join(LINES) + "\n", encoding="utf-8")
    say(f"\nwritten: {out_dir / 'xnpv1_switch_check_log.txt'} and {out_dir / 'xnpv1_switch_compare_log.txt'}")
    say("30_OUTPUT/contract_npv_spine.csv is now the xNPV 1 spine.")


if __name__ == "__main__":
    main()
