"""xnpv0_removal_check.py -- did archiving xNPV 0 change any value xNPV 1 produces?

WHY (2026-10-02). The anchor-and-ratio projection (xNPV 0), its switch and its
skater exit-hazard path were removed from skater_forward_projection.py (v2.0),
rfa_terminal_value.py (v2.0) and contract_npv.py (v2.0). The removal must not
move a single xNPV 1 value. The cloud checked that on a synthetic contract
spine (24 valuations, 3,312 numbers, every one identical). This repeats the
check on the real spine and the real contract export, which only the laptop
has.

WHAT IT DOES
    1. Copies 30_OUTPUT/contract_npv_spine.csv, the spine the PRE-removal code
       wrote (the switch check or Update-Dashboard run on 2026-10-02), to a
       temporary folder OUTSIDE the repository. It refuses to go on unless
       every skater row in it says "xNPV 1", so it cannot compare against an
       xNPV 0 spine by mistake.
    2. Runs 20_CODE/contract_npv.py, the post-removal code, in its own process.
    3. Compares the two spines contract by contract. What must hold:
         * the same contracts, with the same player, position, seasons and
           model label;
         * npv_total, npv_contract and npv_terminal identical to the dollar
           (both rounded to $1 before comparing; exact float equality is not
           asked for, see CLAUDE.md on comparing money).

HOW TO RUN (Windows PowerShell, from the repo root, AFTER syncing the removal
commit and BEFORE running Update-Dashboard, which would overwrite the spine
this compares against; about one contract_npv run):
    python 25_TESTS\\xnpv0_removal_check.py
Send back 30_OUTPUT\\xnpv0_removal_check_log.txt.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

SCRIPT_VERSION = "1.0"
ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "20_CODE"
FAIL_RE = re.compile(r"GUARD FAILED|HALTED|\bFAIL(ED)?\b|Traceback|AssertionError")
LINES = []


def say(s=""):
    print(s)
    LINES.append(str(s))


def main():
    say(f"xnpv0_removal_check.py v{SCRIPT_VERSION}")
    sys.path.insert(0, str(CODE))
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    import pandas as pd
    out_dir = Path(os.environ["OUTPUT_DIR"])
    spine = out_dir / "contract_npv_spine.csv"
    log_path = out_dir / "xnpv0_removal_check_log.txt"
    assert spine.exists(), f"no spine at {spine}: there is nothing to compare against"

    with tempfile.TemporaryDirectory() as tmp:
        before = Path(tmp) / "spine_before_removal.csv"
        shutil.copy2(spine, before)
        say(f"\n[1] spine written by the pre-removal code: {spine}")
        say(f"    last written {datetime.fromtimestamp(spine.stat().st_mtime):%Y-%m-%d %H:%M}")
        # The spine must come from the PRE-removal code. contract_npv v2.0 (the
        # removal) prints its version in the run log; v1.6 and earlier did not.
        run_log = out_dir / "contract_npv_run_log.txt"
        assert not (run_log.exists() and "contract_npv.py v2.0" in run_log.read_text(encoding="utf-8")), (
            "the spine on disk was already written by the post-removal code (its run log says "
            "contract_npv.py v2.0), so comparing would test the new code against itself. "
            "Rebuild the before-spine from the commit before the removal (7f91f0e) first.")
        old = pd.read_csv(before)
        labels = sorted(old.loc[old["position"] == "skater", "model"].dropna().unique())
        say(f"    {len(old):,} contracts; skater model label {labels}")
        assert labels == ["xNPV 1"], (
            "the spine on disk is not an xNPV 1 spine, so it cannot test the removal. "
            "Re-run 25_TESTS/xnpv1_switch_check.py from the commit before the removal (7f91f0e).")

        say("\n[2] contract_npv.py on the post-removal code")
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        env.pop("XNPV_SKATER_MODEL", None)       # the switch no longer exists
        r = subprocess.run([sys.executable, str(CODE / "contract_npv.py")], cwd=ROOT, env=env,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = r.stdout + r.stderr
        for line in [x for x in out.splitlines() if x.strip()][-8:]:
            say("  | " + line)
        bad = [x for x in out.splitlines() if FAIL_RE.search(x)]
        if r.returncode != 0 or bad:
            say(f"  STOPPED: exit code {r.returncode}; failure lines: {bad[:5]}")
            log_path.write_text("\n".join(LINES) + "\n", encoding="utf-8")
            raise SystemExit(1)
        new = pd.read_csv(spine)

    say("\n[3] contract by contract")
    key = ["contract_id", "valuation_season"]
    m = old.merge(new, on=key, how="outer", suffixes=("_0", "_1"), indicator=True)
    only_old = int((m["_merge"] == "left_only").sum())
    only_new = int((m["_merge"] == "right_only").sum())
    say(f"    {len(old):,} before, {len(new):,} after; {only_old} only before, {only_new} only after")
    b = m[m["_merge"] == "both"]
    ident = ["player_id", "full_name", "position", "n_seasons", "model"]
    mism = {c: int((b[c + "_0"].astype(str) != b[c + "_1"].astype(str)).sum()) for c in ident}
    say(f"    identity fields that differ: {mism}")
    gaps = {}
    for c in ("npv_total", "npv_contract", "npv_terminal"):
        d = (b[c + "_0"].round(0) - b[c + "_1"].round(0)).abs()
        gaps[c] = (int((d > 0).sum()), float(d.max()) if len(d) else 0.0)
        say(f"    {c:<13} contracts that moved: {gaps[c][0]:,}   largest move ${gaps[c][1]:,.0f}")
    ok = (only_old == 0 and only_new == 0 and not any(mism.values())
          and all(n == 0 for n, _ in gaps.values()))
    say(f"\nRESULT: {'PASS: the removal moved no xNPV 1 value' if ok else 'FAIL: see the counts above'}")
    log_path.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    say(f"written: {log_path}")
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
