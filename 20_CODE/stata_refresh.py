"""
=============================================================================
 stata_refresh.py   v1.2                            Launcher (2026-11-09)
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
 v1.2 (2026-11-09; Thomas: "Apply as listed"): after the exports pass, each CSV is
 rewritten with only the variables the commands use (and a few identity
 columns) under plain names (RENAMES below); check_names stops if a command
 in the do-file still uses an old name.
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

SCRIPT_VERSION = "stata_refresh.py v1.2 (2026-11-09)"   # v1.2: the Stata names (RENAMES); v1.1: CSVs imported section by section
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

# ---- v1.2: the names Stata sees (Thomas, 2026-11-09: "Apply as listed") -------------------------------------------------
# The exports write and check their CSVs under the model's own column names. After they pass, each CSV is rewritten
# with only the columns below, in this order, under these names: the variables the commands use plus a few identity
# columns. Values are not touched. The do-file template and the guide use the new names.
RENAMES = {
    "draft_players.csv": {
        "player_id": "player_id", "player_name": "player_name", "team": "team", "position": "position",
        "draft_year": "draft_year", "pick": "pick", "career_npv_m": "career_npv", "p_star": "star_prob",
        "p_nhler": "nhl_prob", "excluded_deceased": "deceased",
        "p_star_trend": "star_prob_x_year", "p_star_x_d_draft": "star_prob_def", "p_star_sq": "star_prob_sq",
        "log_pick": "log_pick", "log_pick_sq": "log_pick_sq"},
    "prospect_seasons.csv": {
        "player_id": "player_id", "player_name": "player_name", "draft_year": "draft_year", "pick": "pick",
        "season": "season", "season_group": "dplus", "sample_star": "prospect", "sample_production": "skater_prospect",
        "remaining_npv_m": "remaining_npv", "p_star": "star_prob", "s_early": "star_prob_d1to3",
        "nhle82": "nhle_pts", "nhle82_sq": "nhle_pts_sq", "age_term": "nhle_x_age18",
        "prod_x_age_m18": "nhle_x_age18_all", "age_term_19": "nhle_x_age19", "age_term_20": "nhle_x_age20",
        "flat_term": "age_minus18", "prod_x_defence": "nhle_pts_def", "prod_sq_x_defence": "nhle_pts_sq_def",
        "s_early_x_defence": "star_prob_d1to3_def"},
    "price_line_skaters.csv": {
        "player_name": "player_name", "signing_date": "signing_date", "first_season": "first_season",
        "player_num": "player_id", "cap_m": "cap_hit", "min_m": "league_min", "xwar": "war_fcst", "is_d": "defence",
        "term_years": "term", "is_rfa": "rfa", "xwar_over1": "war_fcst_over1", "term_x_0to1": "term_war0to1",
        "term_x_1to2": "term_war1to2", "term_x_2plus": "term_war2plus", "term_x_0plus": "term_war0plus",
        "start_2022_on": "start_2022plus", "xwar_term_avg": "war_fcst_term_avg", "xwar_term_avg_exp": "war_exp_term_avg"},
    "price_line_goalies.csv": {
        "player_name": "player_name", "signing_date": "signing_date", "first_season": "first_season",
        "cap_m": "cap_hit", "min_m": "league_min", "xwar": "war_fcst", "term_years": "term"},
    "skater_forecast_pairs.csv": {
        "player_key": "player", "career_num": "player_id", "season": "season", "h": "seasons_ahead",
        "y_gp_share": "gp_share", "tr_gp_share": "gp_share_trail", "exp_seasons": "seasons_since_debut",
        "age_c": "age_minus27", "age_c2": "age_minus27_sq", "tw_war": "war_trail", "is_d": "defence",
        "y_played": "played", "p_age_c": "age_minus27_season", "p_age_c2": "age_minus27_season_sq",
        "under_contract": "under_contract", "contract_unknown": "pre_2018"},
    "goalie_age_rows.csv": {
        "player_key": "goalie", "season": "season", "war_less_pulled": "war_minus_fcst", "age_c": "age_minus27"},
    "goalie_play_rows.csv": {
        "player_key": "goalie", "season": "season", "h": "seasons_ahead", "played": "played",
        "age_c": "age_minus27_season", "age_c2": "age_minus27_season_sq", "pulled": "war_fcst",
        "gp_share_last": "gp_share_recent"},
    "backtest_club_sides.csv": {
        "trade_id": "trade_id", "trade_date": "trade_date", "club": "club", "complete": "complete",
        "forecast_net_m": "net_fcst", "outcome_net_m": "net_outcome", "realised_net_m": "net_realised",
        "miss_m": "net_miss", "favoured": "favoured", "ahead": "came_out_ahead",
        "has_conditional_pick": "conditional_pick", "during_regular_season": "in_season",
        "g_futures": "c1_futures", "g_buyer": "c2_buyer", "g_retained": "c4_retained",
        "g_nothing_back": "c5_nothing_back", "g_clause": "c6_clause",
        "outcome_net_m_gv_adj": "net_outcome_gvadj", "outcome_net_m_gv_raw": "net_outcome_gvraw",
        "ahead_gv_adj": "came_out_ahead_gvadj", "ahead_gv_raw": "came_out_ahead_gvraw"},
    "backtest_assets.csv": {
        "trade_id": "trade_id", "trade_date": "trade_date", "name": "asset", "acquiring_team": "acquiring_team",
        "asset_class": "asset_class", "complete_trade": "complete", "miss_m": "miss"},
    "gv_team_games.csv": {
        "game_id": "game_id", "season": "season", "team": "team", "goal_diff_in_play": "goal_diff",
        "game_value_sum": "game_value"},
    "gv_team_seasons.csv": {
        "season": "season", "team": "team", "wins": "wins", "goal_diff_in_play": "goal_diff",
        "game_value_sum": "game_value", "gv_goal_diff": "goal_diff_gv_games"},
}


def rename_csvs():
    """Rewrite each Stata CSV with only its listed columns, under the new names; values untouched."""
    import pandas as pd
    for f, m in RENAMES.items():
        d = pd.read_csv(OUT / f, low_memory=False)
        missing = [c for c in m if c not in d.columns]
        if missing:
            raise SystemExit(f"STOPPED: {f} has no column {missing} to rename")
        assert len(set(m.values())) == len(m) and all(len(n) <= 32 for n in m.values()), f
        out = d[list(m)].rename(columns=m)
        out.to_csv(OUT / f, index=False)
        say(f"  {f:<28} {len(out):>8,} rows, {len(m):>2} variables (of {d.shape[1]})")


def check_names(text):
    """Stop if a command line in the do-file uses a name its section's CSV does not have under the new names: every
    old name, in the section of the file it belongs to, must have been replaced."""
    old_all = {o for m in RENAMES.values() for o in m}
    stored = set(re.findall(r"estimates store (\w+)", text))
    current, bad = None, []
    for l in text.splitlines():
        m = re.match(r'import delimited using "([^"]+)"', l.strip())
        if m:
            current = m.group(1)
            continue
        if current is None or not l.strip() or l.lstrip().startswith("*") or l.startswith("label variable"):
            continue
        code = re.sub(r"\s*//.*$", "", l)
        new = set(RENAMES[current].values())
        for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", code):
            if tok in old_all and tok not in new and tok not in stored:
                bad.append((current, tok, l.strip()[:80]))
    if bad:
        raise SystemExit(f"STOPPED: old variable names left in the do-file's commands: {bad[:10]}")


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

    say(f"\n[{n}/{n}] the Stata names, the do-file and the guide check")
    rename_csvs()
    # the shapes' expected figures name their variables: give them the new names
    pk = RENAMES["draft_players.csv"]
    for k in [k for k in expected if k.startswith("S6")]:
        expected[k] = re.sub(r"[A-Za-z_][A-Za-z0-9_]*", lambda m: pk.get(m.group(0), m.group(0)), expected[k])
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
    check_names(text)
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
    unshown = [c for c in do_cmds if c not in guide_cmds and not c.startswith("label variable")]   # labels: do-file only
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
