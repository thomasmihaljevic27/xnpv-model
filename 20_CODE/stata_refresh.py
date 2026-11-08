"""
=============================================================================
 stata_refresh.py   v1.1                            Launcher (2026-11-08)
=============================================================================
 WHAT THIS DOES (plain English)
 ------------------------------
 One command builds everything needed to run the model's regressions in
 Stata, in 30_OUTPUT/stata/:
   - the CSV files: every row and variable of every regression the model
     runs, plus the variables its tests use. In Stata each is read with
     import delimited, and its variables show in the Variables window;
   - xnpv_walkthrough.do: the commands, in the guide's order, each followed
     by the figure Stata should print, filled in from this run.
 The guide, 40_DOCS/Stata_Data_Codebook.md, is the commands alone, by pillar
 (Thomas, 2026-11-08: "just the command I need to write out to get the
 regression for each thing"; "I want to import csvs"). This script stops if
 any command in the guide is not in the do-file, so the two cannot drift.

 THE STEPS, IN ORDER (each must finish cleanly or the run stops)
   1  stata_export.py            draft picks and prospects   (about 15 seconds)
   2  stata_export_players.py    the player model            (1 to 3 minutes)
   3  stata_export_backtest.py   the back-test, Game Value   (about 10 seconds)
   4  fill stata_walkthrough_template.do with the expected figures; check
      that every file it imports exists and every guide command is in it
 Each export refits every regression from its CSVs and stops on any
 difference from the model. It changes no value and writes nothing outside
 30_OUTPUT/stata/.

 WHEN TO RUN IT
   After everything it reads is current: the dashboard chain
   (dashboard_refresh.py), then the trade chain (trade_refresh.py), then the
   back-test and its two Game Value runs (backtest.py). It does not run those.

 HOW TO RUN (repo root):   python 20_CODE/stata_refresh.py
=============================================================================
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

SCRIPT_VERSION = "stata_refresh.py v1.1 (2026-11-08)"   # v1.1: CSVs imported section by section (no frames); the guide is commands only
CODE = Path(__file__).resolve().parent
REPO = CODE.parent
sys.path.insert(0, str(CODE))
load_dotenv(REPO / ".env")
OUT = Path(os.environ["OUTPUT_DIR"]) / "stata"
TEMPLATE = CODE / "stata_walkthrough_template.do"
GUIDE = REPO / "40_DOCS" / "Stata_Data_Codebook.md"
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


def command_lines(text, comment):
    """The command lines of a do-file (comment = '*') or of the guide's code blocks (comment = None)."""
    if comment is None:
        blocks = re.findall(r"```stata\n(.*?)```", text, re.S)
        text = "\n".join(blocks)
    out = []
    for l in text.splitlines():
        l = re.sub(r"\s*//.*$", "", l).rstrip()
        if l.strip() and not l.lstrip().startswith("*"):
            out.append(l.strip())
    return out


def main():
    say(SCRIPT_VERSION)
    say(f"  writing to {OUT.resolve()}; code at {git_commit()}")
    OUT.mkdir(parents=True, exist_ok=True)
    expected, versions = {}, []
    n = len(STEPS) + 1
    for i, (script, js) in enumerate(STEPS, 1):
        f = OUT / js
        if f.exists():
            f.unlink()                                       # never read a figure left by an earlier run
        say(f"\n[{i}/{n}] {script}")
        v, secs = run(script)
        if not f.exists():
            raise SystemExit(f"STOPPED: {script} finished but wrote no {js}.")
        part = json.loads(f.read_text(encoding="utf-8"))
        clash = set(part) & set(expected)
        assert not clash, f"two exports set the same figure: {sorted(clash)}"
        expected.update(part)
        versions.append(v)
        say(f"  {v}: done in {secs / 60:.1f} min, {len(part)} expected figures")

    say(f"\n[{n}/{n}] the do-file and the guide check")
    expected["BUILT"] = f"{datetime.now():%Y-%m-%d %H:%M} (code at {git_commit()})"
    expected["VERSIONS"] = "; ".join(versions)
    text = TEMPLATE.read_text(encoding="utf-8")
    keys = set(re.findall(r"\{\{(\w+)\}\}", text))
    missing = sorted(keys - set(expected))
    if missing:
        raise SystemExit(f"STOPPED: the template asks for figures no export computed: {missing}")
    for k in keys:
        text = text.replace("{{" + k + "}}", expected[k])
    assert "{{" not in text and "}}" not in text
    (OUT / "xnpv_walkthrough.do").write_text(text, encoding="utf-8")
    if (OUT / "xnpv_load.do").exists():                      # v1.0's frame loader, no longer used
        (OUT / "xnpv_load.do").unlink()
    imports = sorted(set(re.findall(r'import delimited using "([^"]+)"', text)))
    gone = [c for c in imports if not (OUT / c).exists()]
    if gone:
        raise SystemExit(f"STOPPED: the do-file imports files that are not there: {gone}")
    do_cmds = command_lines(text, "*")
    guide_cmds = command_lines(GUIDE.read_text(encoding="utf-8"), None)
    absent = [c for c in guide_cmds if c not in do_cmds]
    if absent:
        raise SystemExit(f"STOPPED: commands in the guide that the do-file does not run: {absent}")
    unshown = [c for c in do_cmds if c not in guide_cmds]
    say(f"  wrote xnpv_walkthrough.do ({len(keys)} expected figures filled in); the guide's {len(guide_cmds)} commands "
        f"are all in it" + (f"; {len(unshown)} do-file lines are not in the guide: {unshown}" if unshown else ""))
    unused = sorted(set(expected) - keys - {"BUILT", "VERSIONS"})
    if unused:
        say(f"  note: {len(unused)} computed figures are not shown in the do-file: {', '.join(unused)}")
    say(f"\nDone. In Stata: cd \"{OUT.resolve()}\", then run the guide's commands section by section "
        f"({len(imports)} CSVs, all present)")
    (OUT / "stata_refresh_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
