"""
=============================================================================
 stata_refresh.py   v1.0                            Launcher (2026-11-08)
=============================================================================
 WHAT THIS DOES (plain English)
 ------------------------------
 One command builds everything the Stata walkthrough needs, in
 30_OUTPUT/stata/:
   - the 13 CSV files: every row and variable of every regression the model
     runs, plus the variables its tests use (three exports, in order);
   - xnpv_load.do: loads all 13 files into Stata with one command;
   - xnpv_walkthrough.do: every regression and test, step by step, each
     followed by the figure Stata should print, filled in from this run.
 Thomas asked for it (2026-11-08): "ensure that all the stata stuff is simple
 and ready to go ... that all data sources are pulled in a single command at
 the beginning". The guide is 40_DOCS/Stata_Data_Codebook.md.

 THE STEPS, IN ORDER (each must finish cleanly or the run stops)
   1  stata_export.py            draft picks and prospects   (about 15 seconds)
   2  stata_export_players.py    the player model            (about 1 minute)
   3  stata_export_backtest.py   the back-test, Game Value   (about 10 seconds)
   4  fill stata_walkthrough_template.do with the three exports' expected
      figures; copy xnpv_load.do; check that every file it loads exists.
 Each export refits every regression from its CSVs and stops on any
 difference from the model, so a run that finishes means the CSVs are the
 model's. It changes no value and writes nothing outside 30_OUTPUT/stata/.

 WHEN TO RUN IT
   After everything it reads is current: the dashboard chain
   (dashboard_refresh.py), then the trade chain (trade_refresh.py), then the
   back-test and its two Game Value runs (backtest.py). It does not run those.
   Each export prints which versions wrote what it reads.

 HOW TO RUN (repo root):   python 20_CODE/stata_refresh.py
=============================================================================
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

SCRIPT_VERSION = "stata_refresh.py v1.0 (2026-11-08)"
CODE = Path(__file__).resolve().parent
REPO = CODE.parent
load_dotenv(REPO / ".env")
OUT = Path(os.environ["OUTPUT_DIR"]) / "stata"
TEMPLATE = CODE / "stata_walkthrough_template.do"
LOADER = CODE / "xnpv_load.do"
STEPS = [("stata_export.py", "expected_picks_prospects.json"),
         ("stata_export_players.py", "expected_players.json"),
         ("stata_export_backtest.py", "expected_backtest.json")]
LOG = []


def say(s=""):
    print(s, flush=True)
    LOG.append(str(s))


def version_of(script):
    """The SCRIPT_VERSION the file on disk declares (its first assignment's string)."""
    m = re.search(r'^SCRIPT_VERSION = "([^"]+)"', (CODE / script).read_text(encoding="utf-8"), re.M)
    return m.group(1)


def git_commit():
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True,
                             timeout=20).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "20_CODE"], cwd=REPO, capture_output=True,
                               text=True, timeout=20).stdout.strip()
        return sha + (" with uncommitted changes in 20_CODE" if dirty else "")
    except (OSError, subprocess.TimeoutExpired):
        return "unknown commit"


def run(script):
    """Run one export, show its output as it comes, stop on an error or a missing version line."""
    want = version_of(script)
    t0 = time.time()
    proc = subprocess.Popen([sys.executable, "-u", str(CODE / script)], cwd=REPO, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    lines = []
    for line in proc.stdout:
        print("    " + line.rstrip(), flush=True)
        lines.append(line.rstrip())
    proc.wait()
    if proc.returncode != 0:
        raise SystemExit(f"STOPPED: {script} ended with an error (exit {proc.returncode}); its last lines are above.")
    if not any(l.strip() == want for l in lines):
        raise SystemExit(f"STOPPED: {script} did not print its version line {want!r}.")
    return want, time.time() - t0


def main():
    say(SCRIPT_VERSION)
    say(f"  writing to {OUT.resolve()}; code at {git_commit()}")
    OUT.mkdir(parents=True, exist_ok=True)
    expected, versions = {}, []
    for i, (script, js) in enumerate(STEPS, 1):
        f = OUT / js
        if f.exists():
            f.unlink()                                       # never read a figure left by an earlier run
        say(f"\n[{i}/{len(STEPS) + 1}] {script}")
        v, secs = run(script)
        if not f.exists():
            raise SystemExit(f"STOPPED: {script} finished but wrote no {js}.")
        part = json.loads(f.read_text(encoding="utf-8"))
        clash = set(part) & set(expected)
        assert not clash, f"two exports set the same figure: {sorted(clash)}"
        expected.update(part)
        versions.append(v)
        say(f"  {v}: done in {secs / 60:.1f} min, {len(part)} expected figures")

    say(f"\n[{len(STEPS) + 1}/{len(STEPS) + 1}] the do-files")
    expected["BUILT"] = f"{datetime.now():%Y-%m-%d %H:%M} (code at {git_commit()})"
    expected["VERSIONS"] = "; ".join(versions)
    text = TEMPLATE.read_text(encoding="utf-8")
    keys = set(re.findall(r"\{\{(\w+)\}\}", text))
    missing = sorted(keys - set(expected))
    if missing:
        raise SystemExit(f"STOPPED: the template asks for figures no export computed: {missing}")
    unused = sorted(set(expected) - keys)
    for k in keys:
        text = text.replace("{{" + k + "}}", expected[k])
    assert "{{" not in text and "}}" not in text
    (OUT / "xnpv_walkthrough.do").write_text(text, encoding="utf-8")
    shutil.copyfile(LOADER, OUT / "xnpv_load.do")
    loads = re.findall(r'import delimited using "([^"]+)"', LOADER.read_text(encoding="utf-8"))
    absent = [c for c in loads if not (OUT / c).exists()]
    if absent:
        raise SystemExit(f"STOPPED: xnpv_load.do loads files that are not there: {absent}")
    say(f"  wrote xnpv_walkthrough.do ({len(keys)} expected figures filled in) and xnpv_load.do "
        f"(loads {len(loads)} files, all present)")
    if unused:
        say(f"  note: {len(unused)} computed figures are not shown in the walkthrough: {', '.join(unused)}")
    say(f"\nDone. In Stata: change the working directory to {OUT.resolve()}, open xnpv_walkthrough.do, run Step 0.")
    (OUT / "stata_refresh_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
