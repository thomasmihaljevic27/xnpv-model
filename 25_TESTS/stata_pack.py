"""
stata_pack.py -- the Stata package for the supervisor: the codebook, a do-file with the same commands, and the CSVs.

ASKED (Thomas, 2026-11-27): "a CSV for all the data (or individual ones, however you think is best) and the codebook for
all the regressions ... ordered the way the docs are ordered (Players, then Picks, then Prospects, then Findings) ... the
stata code and ... the title above the code blocks be what you are testing in plain-ish language."

WHAT IT DOES
  1. Reads 40_DOCS/Stata_Codebook.md (written by hand, in the documents' order).
  2. GUARD: every Stata command in it is a command of a do-file whose figures were checked against the model
     (30_OUTPUT/stata/xnpv_walkthrough.do, written by stata_refresh.py; findings_walkthrough.do, by
     stata_export_findings.py), or one of the ADDED commands below, each checked another way.
  3. Writes OUTPUT_DIR/stata_karl/: the codebook, xnpv_codebook.do (the same commands, each title as a comment), and
     each CSV the codebook imports, copied from OUTPUT_DIR/stata/; then OUTPUT_DIR/xNPV_Stata.zip of that folder.
     Run stata_refresh.py and stata_export_findings.py first when the model has changed: this script only copies.

ADDED commands, not in the checked do-files:
  * the prospect model on draft position alone and on linear production alone, skater prospect-seasons (Valuing
    Prospects Table 3, rows 1 and 2): R-squared from zero 0.1624 and 0.1051 reproduced in Python from the same CSV;
  * the three price-line Tobit regressions with standard errors clustered by player (Table 10's columns): the same
    regressions as the checked ones, which differ only in the standard errors.
The CSVs carry contract figures derived from PuckPedia's export; they go to the supervisor, not into git (30_OUTPUT).

Run from the repo root:  python 25_TESTS/stata_pack.py
"""

import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

from dotenv import load_dotenv

SCRIPT_VERSION = "stata_pack.py v1.1 (2026-11-27)"   # v1.1: the findings Section 2 regressions clustered by trade
load_dotenv(".env")
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ["OUTPUT_DIR"])
SRC = OUT / "stata"
DEST = OUT / "stata_karl"
BOOK = ROOT / "40_DOCS" / "Stata_Codebook.md"
print(SCRIPT_VERSION)

ADDED = {
    "regress remaining_npv ibn.dplus#c.star_prob if skater_prospect == 1, noconstant vce(cluster player_id)",
    "regress remaining_npv ibn.dplus#c.nhle_pts if skater_prospect == 1, noconstant vce(cluster player_id)",
    "tobit cap_hit war_fcst, ll(league_min) vce(cluster player_id)",
    "tobit cap_hit war_fcst c.war_fcst#c.defence, ll(league_min) vce(cluster player_id)",
    # v1.1: Section 2 of the findings clustered by trade (both clubs are mirror-image rows); the slopes are the checked
    # ones (0.7487, 0.7310), the clustered standard errors 0.086 and 0.104 against 0.033 unclustered (session 2026-11-27)
    "regress realized_war tradeday_grade if in_2017_22 == 1, noconstant vce(cluster trade_id)",
    "regress realized_gamevalue tradeday_grade if in_2017_22 == 1, noconstant vce(cluster trade_id)",
}

checked = set()
for f in ("xnpv_walkthrough.do", "findings_walkthrough.do"):
    p = SRC / f
    print(f"  checked commands from {p}  (modified {os.path.getmtime(p):.0f})")
    for line in p.read_text(encoding="utf-8").splitlines():
        t = line.strip()
        if t and not t.startswith("*"):
            checked.add(re.sub(r"^quietly ", "", t))     # quietly only hides the output

text = BOOK.read_text(encoding="utf-8")
blocks = re.findall(r"^(#{2,3} .+?)$|```stata\n(.*?)```", text, flags=re.S | re.M)
missing, csvs, do_lines, n_cmd = [], [], [], 0
for head, code in blocks:
    if head:
        h = head.lstrip("#").strip()
        do_lines += ["", f"* {'=' * 100}", f"* {h}", f"* {'=' * 100}"] if head.startswith("## ") else ["", f"* ---- {h}"]
        continue
    for line in code.rstrip("\n").splitlines():
        t = line.strip()
        if not t:
            continue
        n_cmd += 1
        m = re.match(r'import delimited using "([^"]+)"', t)
        if m and m.group(1) not in csvs:
            csvs.append(m.group(1))
        if t.startswith("cd ") or re.sub(r"^quietly ", "", t) in checked or t in ADDED:
            continue
        missing.append(t)
    do_lines += code.rstrip("\n").splitlines()
if missing:
    sys.exit("GUARD FAILED: commands in the codebook that no checked do-file holds:\n  " + "\n  ".join(missing))
print(f"  guard: all {n_cmd} commands are checked ({len(ADDED)} added, each checked another way)")

if DEST.exists():
    shutil.rmtree(DEST)
DEST.mkdir(parents=True)
for c in csvs:
    shutil.copy2(SRC / c, DEST / c)
shutil.copy2(BOOK, DEST / BOOK.name)
do = ["* xnpv_codebook.do -- the commands of Stata_Codebook.md, in the documents' order (" + SCRIPT_VERSION + ")",
      "* Set the folder holding the CSVs, then run any section: each imports its own CSV.",
      'cd "C:\\path\\to\\the\\csv\\folder"'] + [l for l in do_lines if not l.strip().startswith("cd ")]
(DEST / "xnpv_codebook.do").write_text("\n".join(do) + "\n", encoding="utf-8")
zp = OUT / "xNPV_Stata.zip"
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(DEST.iterdir()):
        z.write(f, f.name)
for c in csvs:
    print(f"  {c:<28} {(DEST / c).stat().st_size / 1e6:6.1f} MB")
print(f"wrote {DEST} and {zp} ({zp.stat().st_size / 1e6:.1f} MB)")
