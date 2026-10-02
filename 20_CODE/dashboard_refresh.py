"""
=============================================================================
 dashboard_refresh.py   v1.0                        Launcher (2026-09-28)
=============================================================================
 WHAT THIS DOES (plain English)
 ------------------------------
 Re-runs every script the player dashboard depends on, using the code as
 it is on disk right now, then builds the dashboard and opens it in the
 browser. Double-click Open-Dashboard.cmd in the repo root to run it.

 THE CHAIN, IN ORDER
 -------------------
 Each step reads only 10_SOURCE, the PuckPedia exports, or files written by
 an earlier step, so the order below is also the dependency order.

    1  join_clauses_to_spine.py      contract_season_spine / contract_level_spine
    2  age_join.py                   WAR_with_age.csv (ages for the aging curve
                                     and the exit hazard)
    3  skater_value_engine.py        skater_value_spine.csv (rate guards first)
    4  goalie_value_engine.py        goalie_value_spine_v2.csv (parity gate first)
    5  skater_forward_projection.py  guards + run log; the NPV engine imports it
    6  rfa_terminal_value.py         guards + run log; imported
    7  exit_hazard.py                guards + run log; imported
    8  contract_npv.py               contract_npv_spine.csv (k=0 identity etc.)
    9  contract_npv_panel.py         contract_npv_panel.csv (the xNPV line)
   10  player_dashboard.py           player_dashboard.html (re-prices every page
                                     and refuses to write unless it matches the
                                     panel within $1)

 Optional, --refresh-draft: draft_pick_linkage.py runs before step 10. It
 pulls the NHL Records draft data over the network, so it is off by default;
 the dashboard only uses it to show draft position.

 Not in the chain: draft_yield_curve.py (the dashboard does not price
 picks) and goalie_value_spine.csv, the locked goalie file that step 4's
 parity gate checks against. It is a fixed reference, never regenerated.

 WHAT COUNTS AS A STEP PASSING -- all three, because an exit code is not enough
 ------------------------------------------------------------------------------
   (a) the script exits with code 0;
   (b) no guard-failure line in its output (GUARD FAILED, FAIL, FAILED,
       HALTED). goalie_value_engine.py prints "HALTED at parity gate." and
       exits 0 when its gate fails, without writing its spine;
   (c) every file the step owns was rewritten during this run. A step that
       stops early leaves last run's file in place, and the next step would
       read it without complaint.
 The first failing step stops the chain. The dashboard is then NOT opened:
 it would show values the current code did not produce.

 BEFORE THE CHAIN
 ----------------
   * Scripts up to date: `git fetch`, then compare this branch with its
     GitHub copy. If GitHub has commits this machine does not, stop and say
     so (run Sync-Desktop / Sync-Laptop first), unless --allow-behind.
     Offline, the check is skipped with a note. Nothing is committed,
     pulled or pushed here.
   * Inputs present: the vendor files, the PuckPedia exports, and the two
     reference files the chain reads but does not write.

 WHAT IT RECORDS
 ---------------
   OUTPUT_DIR/dashboard_refresh_log.txt       every step's full output
   OUTPUT_DIR/dashboard_refresh_manifest.json commit, uncommitted script
       changes, each script's SHA-256 and version line, each step's time.
       player_dashboard.py embeds it, and the dashboard header shows which
       commit and which run built it.

 USAGE (from the repo root)
   python 20_CODE/dashboard_refresh.py [--no-open] [--refresh-draft]
                                       [--allow-behind] [--output-dir DIR]
   --output-dir runs the whole chain into another folder (a test run); the
   live 30_OUTPUT is not touched. The two reference files are copied in
   first if that folder lacks them.
=============================================================================
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

SCRIPT_VERSION = "dashboard_refresh.py v1.1 (2026-10-02)"

CODE_DIR = Path(__file__).resolve().parent
REPO = CODE_DIR.parent

# (script, files it must rewrite in this run, what it is for). Output names
# are the hardcoded names inside each script; if a script is changed to
# write somewhere else, check (c) fails loudly rather than passing stale.
CHAIN = [
    ("join_clauses_to_spine.py",
     ["contract_season_spine.csv", "contract_level_spine.csv", "join_clauses_runlog.txt"],
     "contract spines"),
    ("age_join.py",
     ["WAR_with_age.csv", "age_join_log.txt"],
     "player ages"),
    ("skater_value_engine.py",
     ["skater_value_spine.csv", "skater_value_run_log.txt"],
     "skater observed-season value"),
    ("goalie_value_engine.py",
     ["goalie_value_spine_v2.csv", "goalie_value_engine_run_log.txt"],
     "goalie observed-season value"),
    ("skater_forward_projection.py",
     ["skater_projection_run_log.txt"],
     "forward projection checks"),
    ("rfa_terminal_value.py",
     ["rfa_terminal_value_run_log.txt"],
     "RFA control-year checks"),
    ("exit_hazard.py",
     ["exit_hazard_run_log.txt"],
     "exit-risk checks"),
    ("contract_npv.py",
     # v1.1: under xNPV 1 (the default skater model) it also writes the
     # forecasts it priced on, so a stale forecast file cannot pass.
     ["contract_npv_spine.csv", "contract_npv_run_log.txt", "xnpv1_forecasts.csv"],
     "contract NPV"),
    ("contract_npv_panel.py",
     ["contract_npv_panel.csv", "contract_npv_panel_run_log.txt"],
     "valuation panel"),
]
DRAFT_STEP = ("draft_pick_linkage.py", ["draft_pick_linkage.csv"],
              "draft linkage (network pull)")
DASH_STEP = ("player_dashboard.py", ["player_dashboard.html"], "dashboard")

# Files the chain READS from OUTPUT_DIR but does not write. The locked goalie
# spine is step 4's parity reference; the draft linkage is only rewritten
# with --refresh-draft.
REFERENCE_FILES = ["goalie_value_spine.csv", "draft_pick_linkage.csv"]

# Guard-failure markers, case-sensitive. None of them appears in the run logs
# of the accepted 2026-09-28 chain run, so a match means a real failure.
FAIL_RE = re.compile(r"GUARD FAILED|HALTED|\bFAIL(ED)?\b")
VERSION_RE = re.compile(r"\S+\.py\s+v\d+(\.\d+)*")

LOG = []


def say(msg=""):
    """Console + combined log. The console may be a cp1252 cmd window, so
    anything unprintable is replaced rather than crashing the launcher."""
    print(msg, flush=True)
    LOG.append(str(msg))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(*args, timeout=60):
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                              text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None


# ---------------------------------------------------------------------------
# Pre-flight: are the scripts current, and are the inputs there?
# ---------------------------------------------------------------------------
def check_scripts(allow_behind):
    """Commit, uncommitted script changes, and whether GitHub is ahead."""
    info = {"commit": None, "branch": None, "uncommitted_code": [],
            "behind_upstream": None}
    r = git("rev-parse", "--short", "HEAD")
    if r is None or r.returncode != 0:
        say("  git not available: the commit is not recorded.")
        return info
    info["commit"] = r.stdout.strip()
    r = git("rev-parse", "--abbrev-ref", "HEAD")
    info["branch"] = r.stdout.strip() if r and r.returncode == 0 else None
    r = git("status", "--porcelain", "--", "20_CODE")
    info["uncommitted_code"] = [l[3:] for l in r.stdout.splitlines()] if r else []
    say(f"  scripts: commit {info['commit']} on {info['branch']}"
        + (f", {len(info['uncommitted_code'])} uncommitted change(s) in 20_CODE"
           if info["uncommitted_code"] else ", 20_CODE matches the commit"))

    f = git("fetch", "--quiet", "origin")
    if f is None or f.returncode != 0:
        say("  GitHub check skipped: could not fetch (offline?). "
            "Running on the scripts on this machine.")
        return info
    r = git("rev-list", "--count", "HEAD..@{u}")
    if r is None or r.returncode != 0:
        say("  GitHub check skipped: this branch has no upstream.")
        return info
    behind = int(r.stdout.strip() or 0)
    info["behind_upstream"] = behind
    if behind == 0:
        say("  GitHub has nothing newer than this machine.")
    elif allow_behind:
        say(f"  WARNING: GitHub has {behind} commit(s) this machine does not. "
            "Running anyway (--allow-behind).")
    else:
        say(f"\nSTOPPED: GitHub has {behind} commit(s) this machine does not have,")
        say("so this run would use older scripts. Run the sync launcher first")
        say("(Sync-Desktop.cmd / Sync-Laptop.cmd), then open the dashboard again.")
        say("To run on this machine's scripts anyway: Open-Dashboard.cmd --allow-behind")
        return None
    return info


def check_inputs(out_dir, refresh_draft):
    src = Path(os.environ["SOURCE_DIR"])
    need = {
        "Bacon skater WAR": src / "WAR.csv",
        "Bacon goalie WAR": src / "Goalies_WAR.csv",
        "Elite Prospects birthdates": src / "ep_birthdates.csv",
        "PuckPedia contract export": Path(os.environ["PUCKPEDIA_CONTRACTS_XLSX"]),
        # v1.1: xNPV 1's chance of playing reads contract status from the CSV
        # copy of the same export (skater_forecast refuses without it).
        "PuckPedia contract export, CSV copy (xNPV 1)":
            src / "PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.csv",
        "PuckPedia trades export": Path(os.environ["PUCKPEDIA_TRADES_XLSX"]),
        "locked goalie spine (parity reference)": out_dir / "goalie_value_spine.csv",
    }
    if not refresh_draft:
        need["draft linkage"] = out_dir / "draft_pick_linkage.csv"
    missing = [f"    {k}: {p}" for k, p in need.items() if not p.exists()]
    clauses = [src / "capspace_clauses.csv",
               out_dir / "capspace_out" / "capspace_clauses.csv"]
    if not any(p.exists() for p in clauses):
        missing.append(f"    cap-space clause scrape: {clauses[0]} (or {clauses[1]})")
    if missing:
        say("\nSTOPPED: required inputs are missing:")
        for m in missing:
            say(m)
        return False
    say("  inputs present.")
    return True


# ---------------------------------------------------------------------------
# One step
# ---------------------------------------------------------------------------
def run_step(n, total, step, env, out_dir, logf):
    script, outputs, what = step
    path = CODE_DIR / script
    say(f"\n[{n}/{total}] {script}  ({what})")
    if not path.exists():
        say(f"  FAILED: {path} does not exist.")
        return None
    start = time.time()
    logf.write(f"\n{'=' * 78}\n{script}  started {datetime.now():%H:%M:%S}\n{'=' * 78}\n")
    proc = subprocess.Popen([sys.executable, "-u", str(path)], cwd=REPO, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    tail, flagged, version = [], [], None
    for line in proc.stdout:
        logf.write(line)
        s = line.rstrip()
        tail = (tail + [s])[-25:]
        if FAIL_RE.search(s):
            flagged.append(s.strip())
        if version is None and VERSION_RE.search(s):
            version = VERSION_RE.search(s).group(0)
    rc = proc.wait()
    secs = time.time() - start
    logf.flush()

    # check (c): each owned file rewritten during this run. One second of
    # slack for filesystem timestamp rounding.
    stale = [o for o in outputs
             if not (out_dir / o).exists() or (out_dir / o).stat().st_mtime < start - 1]
    problems = []
    if rc != 0:
        problems.append(f"exit code {rc}")
    if flagged:
        problems.append("guard failure in output: " + " | ".join(flagged[:3]))
    if stale:
        problems.append("not rewritten this run: " + ", ".join(stale))
    if problems:
        say(f"  FAILED after {secs:.0f}s -- " + "; ".join(problems))
        say("  last lines of its output:")
        for s in tail:
            say("    " + s)
        return None
    say(f"  ok  {secs:5.0f}s" + (f"   {version}" if version else ""))
    return {"script": script, "sha256": sha256(path), "version": version,
            "seconds": round(secs, 1), "outputs": outputs}


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Refresh the xNPV chain and open the player dashboard.")
    ap.add_argument("--no-open", action="store_true", help="build, but do not open the browser")
    ap.add_argument("--refresh-draft", action="store_true",
                    help="also re-pull the NHL draft records (network)")
    ap.add_argument("--allow-behind", action="store_true",
                    help="run even if GitHub has commits this machine does not")
    ap.add_argument("--output-dir", help="test run: write the chain into this folder instead")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass

    load_dotenv(REPO / ".env")
    env = dict(os.environ)
    if args.output_dir:
        out_dir = Path(args.output_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        env["OUTPUT_DIR"] = str(out_dir)     # children's load_dotenv won't override it
        live = Path(os.environ["OUTPUT_DIR"])
        for name in REFERENCE_FILES:
            if not (out_dir / name).exists() and (live / name).exists():
                shutil.copy2(live / name, out_dir / name)
    else:
        out_dir = Path(os.environ["OUTPUT_DIR"]).resolve()
    os.environ["OUTPUT_DIR"] = str(out_dir)
    env["PYTHONIOENCODING"] = "utf-8"        # stdio only; file encodings unchanged

    started = datetime.now()
    say(SCRIPT_VERSION)
    say(f"started {started:%Y-%m-%d %H:%M:%S}   output folder: {out_dir}")
    say("=" * 78)
    say("Pre-flight")
    info = check_scripts(args.allow_behind)
    if info is None or not check_inputs(out_dir, args.refresh_draft):
        return finish(out_dir, ok=False)

    steps = list(CHAIN) + ([DRAFT_STEP] if args.refresh_draft else []) + [DASH_STEP]
    manifest_path = out_dir / "dashboard_refresh_manifest.json"
    manifest = {"refresh": SCRIPT_VERSION, "started": started.strftime("%Y-%m-%d %H:%M"),
                "commit": info["commit"], "branch": info["branch"],
                "uncommitted_code": info["uncommitted_code"],
                "behind_upstream": info["behind_upstream"],
                "refresh_draft": args.refresh_draft, "steps": []}

    log_path = out_dir / "dashboard_refresh_log.txt"
    with open(log_path, "w", encoding="utf-8") as logf:
        for i, step in enumerate(steps, 1):
            if step is DASH_STEP:
                # The dashboard embeds the record of the run that fed it. The
                # variable is set only here, so a manual build is never
                # mislabelled with an older run's record.
                manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
                env["XNPV_REFRESH_MANIFEST"] = str(manifest_path)
            res = run_step(i, len(steps), step, env, out_dir, logf)
            if res is None:
                say(f"\nThe chain stopped at {step[0]}. Full output: {log_path}")
                say("The dashboard was not rebuilt or opened: the last build no longer")
                say("matches the code. Fix the failure and run it again.")
                return finish(out_dir, ok=False)
            manifest["steps"].append(res)
    manifest["finished"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")

    total = sum(s["seconds"] for s in manifest["steps"])
    html = out_dir / "player_dashboard.html"
    say("\n" + "=" * 78)
    say(f"All {len(steps)} steps passed in {total / 60:.1f} min. Dashboard: {html}")
    say("CONFIDENTIAL: the dashboard embeds PuckPedia data. Keep it on this machine.")
    if not args.no_open:
        try:
            os.startfile(html)                       # Windows: default browser
        except AttributeError:
            webbrowser.open(html.as_uri())
    return finish(out_dir, ok=True)


def finish(out_dir, ok):
    try:
        (out_dir / "dashboard_refresh_summary.txt").write_text(
            "\n".join(LOG), encoding="utf-8")
    except OSError:
        pass
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
