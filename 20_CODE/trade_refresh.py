"""
=============================================================================
 trade_refresh.py   v1.0                            Launcher (2026-10-18)
=============================================================================
 WHAT THIS DOES (plain English)
 ------------------------------
 Re-runs, in order, every script behind the trade valuations: the draft
 linkage, the pick curve and the traded picks, the prospect model and the
 traded prospects, the traded players (their rights, buried contracts and the
 2017 page), and the join that gives every traded asset one value. It uses the
 code as it is on disk right now. It changes no value: it only runs the
 existing scripts in their order and checks each one. Until it existed each
 step was run by hand, and the 2026-10-18 bug sweep found outputs on the
 laptop written by older versions of their scripts.

 RUN THE CONTRACT CHAIN FIRST WHEN ITS INPUTS CHANGE
 ---------------------------------------------------
 This chain reads the contract chain's outputs (the contract spines, the
 player ages, the name crosswalk, the goalie spine, the valuation panel) and
 prices players on the player model's code. dashboard_refresh.py
 (Update-Dashboard.cmd) rebuilds those. When anything on the contract side
 changes -- the PuckPedia export, WAR.csv, the ages, the price line, any
 script in dashboard_refresh.py's chain -- run dashboard_refresh.py first,
 then this. Its own step 3 (elc_signing_dates.py) runs here too, because the
 pick curve reads it. The pre-flight prints when each contract-side file was
 written and which commit the last dashboard refresh ran on; it does not
 decide for you whether they are current.

 THE CHAIN, IN ORDER
 -------------------
 Each step reads 10_SOURCE, the PuckPedia exports, the contract chain's
 outputs, the caches listed below, or files written by an earlier step, so
 the order below is also the dependency order. Scripts are in 20_CODE unless
 the path says 25_TESTS.

    1  draft_pick_linkage.py              draft_pick_linkage.csv (each pick linked
                                          to his WAR rows)
    2  25_TESTS/draft_window_count.py     draft_window_count.csv (each drafted
                                          player's control window; step 4 checks
                                          its own windows against it)
    3  elc_signing_dates.py               elc_signing_dates.csv (entry-level
                                          signing years, for the CBA ages)
    4  pick_curve.py                      pick_curve_players / _seasons / _scales
    5  traded_pick_values.py              traded_pick_values.csv
    6  25_TESTS/prospect_slot_years_check.py  prospect_slot_years.csv, _rows.csv
    7  25_TESTS/prospect_nhle_look.py     prospect_nhle_look / _coefficients /
                                          _rows.csv
    8  25_TESTS/prospect_age_look.py      prospect_age_look / _coefficients.csv
                                          (asserts a fingerprint of its rows)
          Steps 6-8 are the checks that measured the prospect model; step 9
          compares each of its fits with their files and stops if one differs.
    9  prospect_values.py                 prospect_values.csv, prospect_star_values,
                                          prospect_production_fits
   10  traded_player_values.py            traded_player_values.csv
   11  rights_values.py                   rights_values.csv, and its values written
                                          back into traded_player_values.csv
   12  buried_contract_values.py          buried_contract_values.csv
   13  25_TESTS/uncovered_assets_audit.py uncovered_assets_audit.csv (step 15 reads
                                          which 2017-18 assets no model values)
   14  contracts_2017.py                  contracts_2017.csv (from CapWages pages
                                          already cached; never --fetch here)
   15  page_2017_values.py                page_2017_values.csv
   16  25_TESTS/uncovered_assets_audit.py again, so the audit counts the 2017 page
   17  trade_asset_values.py              trade_asset_values.csv (every traded
                                          asset once, one value)

 No network: step 1 pulls a draft year from records.nhl.com only when its
 file is missing from OUTPUT_DIR/draft_raw (the pre-flight says how many are
 cached), and steps 3 and 14 read only CapWages pages already cached.
 Fetching new CapWages pages (contracts_2017.py / elc_signing_dates.py
 --fetch) needs Thomas's approval each time, so it is never done here.

 WHAT COUNTS AS A STEP PASSING -- all four, because an exit code is not enough
 -----------------------------------------------------------------------------
   (a) the script exits with code 0;
   (b) no guard-failure line in its output (GUARD FAILED, FAIL, FAILED,
       HALTED), as in dashboard_refresh.py;
   (c) it printed its version line, naming itself ("pick_curve.py v1.8 ...";
       draft_pick_linkage.py prints "SCRIPT_VERSION 1.2"), so the log records
       which version wrote each file;
   (d) every file the step owns was rewritten during this run. A step that
       stops early leaves last run's file in place, and the next step would
       read it without complaint.
 The first failing step stops the chain. Files from the steps after it are
 then last run's, so the summary says the chain is incomplete.

 BEFORE THE CHAIN
 ----------------
   * Scripts up to date: `git fetch`, then compare this branch with its
     GitHub copy. If GitHub has commits this machine does not, stop and say
     so (run the sync launcher first), unless --allow-behind. Offline, the
     check is skipped with a note. Nothing is committed, pulled or pushed.
   * Inputs present: the vendor files, the PuckPedia exports, the contract
     chain's outputs and the caches (draft records, Elite Prospects, CapWages).

 WHAT IT RECORDS
 ---------------
   OUTPUT_DIR/trade_refresh_log.txt        every step's full output
   OUTPUT_DIR/trade_refresh_manifest.json  commit, uncommitted script changes,
       the contract-side inputs' write dates and SHA-256, and for each step
       its script's SHA-256 and version line, its time, and the SHA-256 of
       each file it owns right after it ran
   OUTPUT_DIR/trade_refresh_summary.txt    what this window printed

 USAGE (from the repo root)
   python 20_CODE/trade_refresh.py [--allow-behind] [--output-dir DIR]
   --output-dir runs the whole chain into another folder (a test run); the
   live 30_OUTPUT is not touched. Inputs that folder lacks (the contract
   chain's outputs and the caches) are copied in from the live folder first.
   A new script the trade values depend on must be added to CHAIN below, or
   this runner will not run it.
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
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

SCRIPT_VERSION = "trade_refresh.py v1.0 (2026-10-18)"

CODE_DIR = Path(__file__).resolve().parent
REPO = CODE_DIR.parent

# (script relative to the repo root, files it must rewrite in this run, what it
# is for). Output names are the hardcoded names inside each script; if a script
# is changed to write somewhere else, check (d) fails loudly rather than
# passing stale.
CHAIN = [
    ("20_CODE/draft_pick_linkage.py",
     ["draft_pick_linkage.csv"],
     "picks linked to careers"),
    ("25_TESTS/draft_window_count.py",          # pick_curve.py guards against its output
     ["draft_window_count.csv"],
     "control windows (the pick curve's check)"),
    ("20_CODE/elc_signing_dates.py",            # also step 4 of dashboard_refresh.py
     ["elc_signing_dates.csv", "elc_signing_dates_log.txt"],
     "entry-level signing years"),
    ("20_CODE/pick_curve.py",
     ["pick_curve_players.csv", "pick_curve_seasons.csv", "pick_curve_scales.csv", "pick_curve_log.txt"],
     "pick curve"),
    ("20_CODE/traded_pick_values.py",
     ["traded_pick_values.csv", "traded_pick_values_log.txt"],
     "traded picks"),
    ("25_TESTS/prospect_slot_years_check.py",   # prospect_values.py guards against its output
     ["prospect_slot_years.csv", "prospect_slot_years_rows.csv", "prospect_slot_years_log.txt"],
     "prospect check: draft position by season"),
    ("25_TESTS/prospect_nhle_look.py",          # same
     ["prospect_nhle_look.csv", "prospect_nhle_coefficients.csv", "prospect_nhle_rows.csv",
      "prospect_nhle_look_log.txt"],
     "prospect check: production"),
    ("25_TESTS/prospect_age_look.py",           # same; asserts a fingerprint of its rows
     ["prospect_age_look.csv", "prospect_age_coefficients.csv", "prospect_age_look_log.txt"],
     "prospect check: age"),
    ("20_CODE/prospect_values.py",
     ["prospect_values.csv", "prospect_star_values.csv", "prospect_production_fits.csv",
      "prospect_values_log.txt"],
     "prospects"),
    ("20_CODE/traded_player_values.py",
     ["traded_player_values.csv", "traded_player_values_log.txt"],
     "traded players"),
    ("20_CODE/rights_values.py",                # writes its values back into traded_player_values.csv
     ["rights_values.csv", "rights_values_log.txt", "traded_player_values.csv"],
     "rights"),
    ("20_CODE/buried_contract_values.py",
     ["buried_contract_values.csv", "buried_contract_values_log.txt"],
     "buried contracts"),
    ("25_TESTS/uncovered_assets_audit.py",      # page_2017_values.py reads which assets it lists
     ["uncovered_assets_audit.csv", "uncovered_assets_audit_log.txt"],
     "assets no model values"),
    ("20_CODE/contracts_2017.py",               # no --fetch: fetching needs Thomas's approval each time
     ["contracts_2017.csv", "contracts_2017_log.txt"],
     "2017-18 contracts from cached CapWages pages"),
    ("20_CODE/page_2017_values.py",
     ["page_2017_values.csv", "page_2017_values_log.txt"],
     "the 2017 page"),
    ("25_TESTS/uncovered_assets_audit.py",      # again, so it counts the 2017 page
     ["uncovered_assets_audit.csv", "uncovered_assets_audit_log.txt"],
     "assets no model values, with the 2017 page"),
    ("20_CODE/trade_asset_values.py",
     ["trade_asset_values.csv", "trade_asset_values_log.txt"],
     "every traded asset once"),
]

# Files this chain READS from OUTPUT_DIR but does not write: the contract
# chain's outputs (dashboard_refresh.py writes them), then the caches and
# scraped stores no runner writes. Their write dates are printed and recorded.
CONTRACT_SIDE = ["contract_level_spine.csv", "contract_season_spine.csv", "WAR_with_age.csv",
                 "war_name_crosswalk.csv", "goalie_value_spine_v2.csv", "contract_npv_panel.csv"]
CACHE_DIRS = ["draft_raw",            # NHL Records draft data, one JSON per year (step 1 pulls missing years)
              "ep_out",               # Elite Prospects store (ep_prospects.db)
              "capwages_top_picks", "capwages_elc", "capwages_2017"]   # cached CapWages pages
DRAFT_YEARS = range(2005, 2027)       # draft_pick_linkage.PULL_YEARS

# Guard-failure markers, case-sensitive, as dashboard_refresh.py. None of them
# appears in the logs of the 2026-10-18 runs of these scripts, so a match
# means a real failure.
FAIL_RE = re.compile(r"GUARD FAILED|HALTED|\bFAIL(ED)?\b")

LOG = []


def say(msg=""):
    """Console + combined log. The console may be a cp1252 window, so anything
    unprintable is replaced rather than crashing the launcher."""
    print(msg, flush=True)
    LOG.append(str(msg))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def version_re(script):
    """The version line a step must print, naming the script itself (an
    imported module may print its own first): 'name.py v1.2' or, for
    draft_pick_linkage.py, 'name.py SCRIPT_VERSION 1.2'."""
    return re.compile(re.escape(Path(script).name) + r"\s+(?:SCRIPT_VERSION\s+)?v?\d+(?:\.\d+)*")


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
    r = git("status", "--porcelain", "--", "20_CODE", "25_TESTS")   # the chain runs scripts from both
    info["uncommitted_code"] = [l[3:] for l in r.stdout.splitlines()] if r else []
    say(f"  scripts: commit {info['commit']} on {info['branch']}"
        + (f", {len(info['uncommitted_code'])} uncommitted change(s) in 20_CODE/25_TESTS"
           if info["uncommitted_code"] else ", 20_CODE and 25_TESTS match the commit"))

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
        say("(Sync-Desktop.cmd / Sync-Laptop.cmd), then run this again.")
        say("To run on this machine's scripts anyway: python 20_CODE/trade_refresh.py --allow-behind")
        return None
    return info


def check_inputs(out_dir):
    src = Path(os.environ["SOURCE_DIR"])
    need = {
        "Bacon skater WAR": src / "WAR.csv",
        "Bacon goalie WAR": src / "Goalies_WAR.csv",
        "Bacon draft-position star chances": src / "draft_slot_baseline.csv",
        "Elite Prospects birthdates": src / "ep_birthdates.csv",
        "trades database": src / "trades.db",
        "regular-season results": src / "games.csv",
        "NHL-equivalence factors": src / "nhle_temporal.csv",
        "CapWages pages from the clause scrape": src / "capwages_cache",
        "PuckPedia contract export": Path(os.environ["PUCKPEDIA_CONTRACTS_XLSX"]),
        "PuckPedia contract export, CSV copy":
            src / "PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.csv",
        "Elite Prospects store": out_dir / "ep_out" / "ep_prospects.db",
    }
    need.update({f"contract chain output {n}": out_dir / n for n in CONTRACT_SIDE})
    need.update({f"cache {d}": out_dir / d for d in CACHE_DIRS})
    missing = [f"    {k}: {p}" for k, p in need.items() if not p.exists()]
    if missing:
        say("\nSTOPPED: required inputs are missing:")
        for m in missing:
            say(m)
        return False
    say("  inputs present.")
    cached = [y for y in DRAFT_YEARS if (out_dir / "draft_raw" / f"draft_{y}.json").exists()]
    say(f"  draft records cached for {len(cached)} of {len(DRAFT_YEARS)} years"
        + ("" if len(cached) == len(DRAFT_YEARS) else
           "; step 1 pulls the others from records.nhl.com"))
    return True


def contract_side(out_dir):
    """Write date and SHA-256 of each contract-chain file this chain reads, and
    the last dashboard refresh's commit, so a stale contract side is visible."""
    say("  contract-side inputs (written by dashboard_refresh.py; run it first if the contract side changed):")
    rec = []
    for n in CONTRACT_SIDE:
        p = out_dir / n
        when = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        say(f"    {when}  {n}")
        rec.append({"file": n, "written": when, "sha256": sha256(p)})
    m = out_dir / "dashboard_refresh_manifest.json"
    if m.exists():
        try:
            d = json.loads(m.read_text(encoding="utf-8"))
            say(f"  last dashboard refresh: commit {d.get('commit')}, finished {d.get('finished', 'unfinished')}")
        except (OSError, ValueError):
            say("  last dashboard refresh: its manifest could not be read")
    else:
        say("  last dashboard refresh: no manifest in this folder")
    return rec


# ---------------------------------------------------------------------------
# One step
# ---------------------------------------------------------------------------
def run_step(n, total, step, env, out_dir, logf):
    script, outputs, what = step
    path = REPO / script
    say(f"\n[{n}/{total}] {script}  ({what})")
    if not path.exists():
        say(f"  FAILED: {path} does not exist.")
        return None
    start = time.time()
    logf.write(f"\n{'=' * 78}\n{script}  started {datetime.now():%H:%M:%S}\n{'=' * 78}\n")
    proc = subprocess.Popen([sys.executable, "-u", str(path)], cwd=REPO, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    vre = version_re(script)
    tail, flagged, version = [], [], None
    for line in proc.stdout:
        logf.write(line)
        s = line.rstrip()
        tail = (tail + [s])[-25:]
        if FAIL_RE.search(s):
            flagged.append(s.strip())
        if version is None and vre.search(s):
            version = vre.search(s).group(0)
    rc = proc.wait()
    secs = time.time() - start
    logf.flush()

    # check (d): each owned file rewritten during this run. One second of
    # slack for filesystem timestamp rounding.
    stale = [o for o in outputs
             if not (out_dir / o).exists() or (out_dir / o).stat().st_mtime < start - 1]
    problems = []
    if rc != 0:
        problems.append(f"exit code {rc}")
    if flagged:
        problems.append("guard failure in output: " + " | ".join(flagged[:3]))
    if version is None:
        problems.append(f"no version line naming {Path(script).name}")
    if stale:
        problems.append("not rewritten this run: " + ", ".join(stale))
    if problems:
        say(f"  FAILED after {secs:.0f}s -- " + "; ".join(problems))
        say("  last lines of its output:")
        for s in tail:
            say("    " + s)
        return None
    say(f"  ok  {secs:5.0f}s   {version}")
    return {"script": script, "sha256": sha256(path), "version": version,
            "seconds": round(secs, 1),
            "outputs": {o: sha256(out_dir / o) for o in outputs}}


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Refresh the draft, prospect and trade-valuation chain.")
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
    copied = []
    if args.output_dir:
        out_dir = Path(args.output_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        env["OUTPUT_DIR"] = str(out_dir)     # children's load_dotenv won't override it
        live = Path(os.environ["OUTPUT_DIR"]).resolve()
        if live != out_dir:
            for name in CONTRACT_SIDE + CACHE_DIRS:
                if not (out_dir / name).exists() and (live / name).exists():
                    if (live / name).is_dir():
                        shutil.copytree(live / name, out_dir / name)
                    else:
                        shutil.copy2(live / name, out_dir / name)
                    copied.append(name)
    else:
        out_dir = Path(os.environ["OUTPUT_DIR"]).resolve()
    os.environ["OUTPUT_DIR"] = str(out_dir)
    env["PYTHONIOENCODING"] = "utf-8"        # stdio only; file encodings unchanged

    started = datetime.now()
    say(SCRIPT_VERSION)
    say(f"started {started:%Y-%m-%d %H:%M:%S}   output folder: {out_dir}")
    if copied:
        say(f"  test run: copied from the live output folder: {', '.join(copied)}")
    say("=" * 78)
    say("Pre-flight")
    info = check_scripts(args.allow_behind)
    if info is None or not check_inputs(out_dir):
        return finish(out_dir, ok=False)
    inputs = contract_side(out_dir)

    manifest_path = out_dir / "trade_refresh_manifest.json"
    manifest = {"refresh": SCRIPT_VERSION, "started": started.strftime("%Y-%m-%d %H:%M"),
                "commit": info["commit"], "branch": info["branch"],
                "uncommitted_code": info["uncommitted_code"],
                "behind_upstream": info["behind_upstream"],
                "contract_side_inputs": inputs, "steps": []}

    log_path = out_dir / "trade_refresh_log.txt"
    with open(log_path, "w", encoding="utf-8") as logf:
        for i, step in enumerate(CHAIN, 1):
            res = run_step(i, len(CHAIN), step, env, out_dir, logf)
            if res is None:
                manifest["stopped_at"] = f"{i}: {step[0]}"
                manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
                say(f"\nThe chain stopped at step {i}, {step[0]}. Full output: {log_path}")
                say("The files of this step and every later one are from an earlier run, not from")
                say("the code on disk. Fix the failure and run the chain again.")
                return finish(out_dir, ok=False)
            manifest["steps"].append(res)
    manifest["finished"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")

    total = sum(s["seconds"] for s in manifest["steps"])
    say("\n" + "=" * 78)
    say(f"All {len(CHAIN)} steps passed in {total / 60:.1f} min. "
        f"Every traded asset: {out_dir / 'trade_asset_values.csv'}")
    return finish(out_dir, ok=True)


def finish(out_dir, ok):
    try:
        (out_dir / "trade_refresh_summary.txt").write_text(
            "\n".join(LOG), encoding="utf-8")
    except OSError:
        pass
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
