"""
karl_bundle.py -- every deliverable for the supervisor in one zip: OUTPUT_DIR/xNPV_for_Karl.zip.

ASKED (Thomas, 2026-11-27: "Then zip every deliverable for Karl together").

CONTENTS, numbered in reading order (the entries' names only; no repo file is renamed):
  0 Method Flow.pdf                        40_DOCS/Method_Flow.pdf (flow_diagram.py)
  1 Valuing Players.docx  ...  4 Findings.docx   the four write-up chunks (40_DOCS/)
  5 Figures and Regression Results.docx    the companion (companion_doc.js)
  Stata/                                   OUTPUT_DIR/stata_karl/: the codebook, its do-file and the CSVs (stata_pack.py)
GUARDS: each document is the committed version (git hash-object equals HEAD's blob: no unsaved edit or unbuilt change
goes out), and stata_karl's codebook is 40_DOCS/Stata_Codebook.md as it stands (run stata_pack.py first if not).
The CSVs carry figures derived from PuckPedia's export: the zip stays in OUTPUT_DIR, out of git.

Run from the repo root:  python 25_TESTS/karl_bundle.py
"""

import os
import subprocess
import sys
import zipfile
from pathlib import Path

from dotenv import load_dotenv

SCRIPT_VERSION = "karl_bundle.py v1.0 (2026-11-27)"
load_dotenv(".env")
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ["OUTPUT_DIR"])
STATA = OUT / "stata_karl"
ZIP = OUT / "xNPV_for_Karl.zip"
print(SCRIPT_VERSION)

DOCS = [("0 Method Flow.pdf", "40_DOCS/Method_Flow.pdf"),
        ("1 Valuing Players.docx", "40_DOCS/Valuing Players.docx"),
        ("2 Valuing Draft Picks.docx", "40_DOCS/Valuing Draft Picks.docx"),
        ("3 Valuing Prospects.docx", "40_DOCS/Valuing Prospects.docx"),
        ("4 Findings.docx", "40_DOCS/Findings.docx"),
        ("5 Figures and Regression Results.docx", "40_DOCS/Figures and Regression Results.docx")]


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


bad = []
for _, rel in DOCS:
    if git("hash-object", rel) != git("rev-parse", f"HEAD:{rel}"):
        bad.append(rel)
if bad:
    sys.exit("GUARD FAILED: not the committed version (commit or rebuild first): " + "; ".join(bad))
book = (ROOT / "40_DOCS" / "Stata_Codebook.md").read_bytes()
if (STATA / "Stata_Codebook.md").read_bytes() != book:
    sys.exit("GUARD FAILED: stata_karl's codebook is not 40_DOCS/Stata_Codebook.md (run 25_TESTS/stata_pack.py)")
print(f"  guards: the {len(DOCS)} documents are the committed versions; the Stata folder's codebook is current (PASS)")

with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
    for name, rel in DOCS:
        z.write(ROOT / rel, name)
    for f in sorted(STATA.iterdir()):
        z.write(f, f"Stata/{f.name}")
with zipfile.ZipFile(ZIP) as z:
    for i in z.infolist():
        print(f"  {i.filename:<44} {i.file_size / 1e6:6.2f} MB")
print(f"wrote {ZIP} ({ZIP.stat().st_size / 1e6:.1f} MB)")
