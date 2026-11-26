"""doc_check.py v1.0 (2026-11-25): list each banned pattern in a reader-facing document.

Why it exists. The writing-style skill's hard bans (no first person, no "against" between two figures,
no script names or run dates, no forward references to sections, the project's retired terms) were
broken dozens of times in "Valuing Players, Draft Picks, and Prospects" v5.0 although each was a written
rule. A rule a reviewer has to remember gets missed; a rule a script prints on every build does not.
Thomas: "Yes, merge and add it" (2026-11-25).

What it reads. A .docx (every paragraph of word/document.xml, table cells and captions included; equation
text in m:t runs is skipped, so a symbol such as I in a formula is not read as first person) or a plain
text / markdown file (the builders' LINT_OUT).

What it does. Each rule is a regular expression with a short name and the fix the skill asks for. The
script prints, rule by rule, every hit with its paragraph number and about 50 characters either side,
then a count table. It never edits the document. Some rules are hard bans (BAN), others only point at
a sentence to look at (LOOK): a colon, the word "trend", a section number, which are right in some
sentences and wrong in others.

Run:   python 25_TESTS/doc_check.py "40_DOCS/Findings.docx"           (list the hits; exit 0)
       python 25_TESTS/doc_check.py --strict FILE                      (exit 1 if any BAN rule hits)
       python 25_TESTS/doc_check.py --only first_person,against FILE   (named rules only)
       python 25_TESTS/doc_check.py --quiet --out hits.txt FILE        (count table; each hit to a file)
Both document builders (model_doc.js, findings_doc.js) call it on the file they have just written.
A copy sits in the writing-style skill's scripts/ folder; this file is the one the builders run.
"""
import argparse
import html
import re
import sys
import zipfile

SCRIPT_VERSION = "doc_check v1.0"

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"

# (name, kind, pattern, fix). kind: BAN = the skill forbids it; LOOK = read the sentence and decide.
# Patterns run on one paragraph at a time, case-sensitive unless (?i) is given.
RULES = [
    # Register
    ("first_person", "BAN", r"\b(?:I(?![_\w])|me|my|mine|myself)\b(?![-_])",
     "No first person: use an impersonal construction (\"The model estimates\", \"was chosen\")."),
    ("contraction", "BAN", r"(?i)\b\w+n't\b|\b(?:it|that|there|here|what|he|they|we|you)(?:'|\u2019)(?:s|re|ll|ve|d)\b(?!\w)",
     "No contractions: write \"do not\", \"it is\"."),
    # Hard bans of the revamp, section 2.3
    ("against", "BAN", r"(?:[\d%]\S*|million|WAR|cap)\s*\)?\s+against\s+\S{0,3}[\d$\u2212-]|(?i:\bagainst\s+[$\u2212-]?\d)",
     "No \"against\" between figures: \"compared with\", \"versus\", or state the change (\"lowered RMSE from A to B\")."),
    ("if_he_plays", "BAN", r"(?i)\bif he plays\b|\bif he plays at all\b",
     "Cut \"if he plays\"."),
    ("starts_with_and", "BAN", r"(?:^|[.!?]\s+)And\b",
     "No sentence opens with \"And\": use \"In addition,\", \"Moreover,\" or join the sentences."),
    ("em_dash", "BAN", "\u2014",
     "No em dashes: a comma, a period or parentheses."),
    ("script_name", "BAN", r"\b[\w-]+\.(?:py|js|csv|json|do|db|ipynb)\b",
     "No script or file names: describe what the step does."),
    # A trade's date, a sample window or a birthdate is data and is not flagged; a date beside a script
    # name, or after "measured", "tested", "locked" and the like, is a run date.
    ("run_date", "BAN",
     rf"(?i:\b(?:measured|tested|locked|run|re-?fitted|fitted|audited|built|checked|computed)(?: on)?,? )(?:{MONTHS}) \d{{1,2}}, 20\d\d\b"
     rf"|\.(?:py|js)\b[^.]{{0,40}}?(?:{MONTHS}) \d{{1,2}}, 20\d\d\b|\b20\d\d-\d\d-\d\d\b",
     "No run or audit dates in the text."),
    ("section_ref", "LOOK", r"\b[Ss]ections? \d+(?:\.\d+)?\b",
     "A section pointer: no forward references; a backward one only when the reader needs to go back."),
    ("defined_by_negation", "LOOK", r"(?i)\bhas no \w+ and no \b|\bis not an? \w+(?:,| but)",
     "Define a term by what it is, not by what it is not."),
    # A colon followed by a subject and, before the next stop, a finite verb: two sentences joined.
    ("colon_clause", "LOOK",
     r":\s+(?:[Tt]he|[Aa]n?|[Tt]his|[Tt]hat|[Tt]hese|[Ii]ts?|[Ee]ach|[Hh]e|[Hh]is|[Tt]hey|[Tt]heir|[Oo]ne|[Nn]o)\b[^.;:()]{0,80}?"
     r"\b(?:is|are|was|were|has|have|had|gives?|moves?|falls?|rises?|holds?|stays?|costs?|lowers?|raises?|reaches?|takes?|makes?|"
     r"cancels?|counts?|delivers?|becomes?|returns?|shows?|means?)\b",
     "A colon joining two sentences: use a period, or \"X, which is Y\" for a definition."),
    # Project vocabulary (CLAUDE.md and the skill)
    ("surplus", "BAN", r"(?i)\bsurplus\b",
     "Retired term: expected net present value (xNPV), NPV, or net value for one season."),
    ("held_out_error", "BAN", r"(?i)\b(?:held|left)[- ]out (?:error|errors|root mean)\b",
     "Write \"out-of-sample RMSE\" (root mean squared error, defined once)."),
    ("yes_or_no", "BAN", r"(?i)\byes[- ]or[- ]no\b|\byes/no\b",
     "Write \"dummy variable\" (or \"indicator variable\")."),
    ("the_fit", "LOOK", r"(?i)\bthe fit\b(?!ted)|\beach fit\b|\bthe fits\b",
     "Write \"regression\" (or name the estimator)."),
    ("slope_for", "LOOK", r"(?i)\ba (?:separate )?slope for\b",
     "If it is an interaction term, call it one."),
    ("trend", "LOOK", r"(?i)\btrend\b",
     "Name the variable exactly (\"year-over-year change\" when it is two seasons)."),
    ("draft_slot", "BAN", r"(?i)\b(?:the|his|a|draft) slot\b",
     "Write \"draft position\"."),
    ("season_zero", "BAN", r"(?i)\bseason 0\b",
     "Name seasons from the draft: D0, D+1."),
    ("last_season", "LOOK", r"(?i)\blast (?:season|seasons|counted season)\b",
     "Write \"most recent\" for the latest season (\"last\" also means final)."),
    ("play_for_performance", "BAN", r"(?i)\b(?:his|their|the player's) play\b|\bforecast(?:ed)? play\b",
     "Write \"performance\"."),
    ("reliable", "BAN", r"(?i)\breliabl[ey]\b",
     "Write \"statistically significant at the 5% level (p = ...)\"."),
    ("redraw", "LOOK", r"(?i)\bredraws?\b",
     "Report the p-value alone; define the bootstrap once in a caption."),
    ("yardstick", "LOOK", r"(?i)\byardstick\b",
     "A coined label: use the technical name (bandwidth) once defined."),
    ("decision_heading", "BAN", r"^Decision:",
     "No \"Decision:\" headings: name the topic."),
    # Personification (CLAUDE.md, 2026-10-21)
    ("personification", "BAN",
     r"(?i)\b(?:the )?(?:model|forecast|regression|discount(?:ing)?|price line|pick curve|curve|data|test|chain)s? "
     r"(?:knows?|sees?|asks?|reads?|learns?|acts?|wants?|thinks?|believes?|decides?|chooses?|prefers?|expects?|tells?|treats?|cares?)\b",
     "Do not personify the model: say what is done to what."),
    # The general AI checklist
    ("ai_vocabulary", "BAN",
     r"(?i)\b(?:actually|additionally|crucial|delve|delves|emphasi[sz]ing|enhance|enhances|fostering|interplay|intricate|"
     r"pivotal|showcase|showcases|tapestry|testament|underscores?|vibrant|landscape)\b",
     "Plain word, or cut."),
    ("intensifier", "BAN", r"(?i)\bat all\b|\bbadly\b|\bgenuinely\b|\bdeliberately\b",
     "Cut the intensifier when the sentence is true without it."),
    ("copula_avoidance", "BAN", r"(?i)\bserves? as\b|\bboasts?\b",
     "Use \"is\", \"are\", \"has\"."),
    ("filler", "BAN", r"(?i)\bin order to\b|\bdue to the fact that\b|\bat this point in time\b",
     "\"to\", \"because\", \"now\"."),
    ("not_just", "BAN", r"(?i)\bnot just\b.{0,60}\bbut\b|\bnot only\b.{0,60}\bbut also\b",
     "State it directly."),
]


def paragraphs_docx(path):
    """Each w:p of the body as plain text: w:t runs only (m:t, equation text, is skipped)."""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    out = []
    for p in re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S):
        runs = re.findall(r"<w:t(?: [^>]*)?>(.*?)</w:t>", p, flags=re.S)
        t = html.unescape("".join(runs)).strip()
        if t:
            out.append(t)
    return out


def paragraphs_text(path):
    with open(path, encoding="utf-8") as f:
        return [p.strip() for p in re.split(r"\n\s*\n", f.read()) if p.strip()]


def main():
    ap = argparse.ArgumentParser(description="List banned patterns in a reader-facing document.")
    ap.add_argument("file")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any BAN rule hits")
    ap.add_argument("--only", default="", help="comma-separated rule names")
    ap.add_argument("--quiet", action="store_true", help="print the count table only")
    ap.add_argument("--out", default="", help="also write the full list of hits to this file")
    a = ap.parse_args()

    print(SCRIPT_VERSION)
    paras = paragraphs_docx(a.file) if a.file.lower().endswith(".docx") else paragraphs_text(a.file)
    only = {x.strip() for x in a.only.split(",") if x.strip()}
    unknown = only - {r[0] for r in RULES}
    if unknown:
        sys.exit(f"unknown rule(s): {sorted(unknown)}")
    rules = [r for r in RULES if not only or r[0] in only]

    counts, full = [], []
    for name, kind, pat, fix in rules:
        rx = re.compile(pat, flags=re.M)
        hits = []
        for i, p in enumerate(paras, 1):
            for m in rx.finditer(p):
                lo, hi = max(0, m.start() - 50), min(len(p), m.end() + 50)
                ctx = ("..." if lo else "") + p[lo:m.start()] + "[[" + m.group(0) + "]]" + p[m.end():hi] + ("..." if hi < len(p) else "")
                hits.append((i, ctx))
        counts.append((name, kind, len(hits)))
        if hits:
            full.append(f"\n{kind} {name} ({len(hits)}): {fix}")
            full += [f"  para {i}: {ctx}" for i, ctx in hits]
    if not a.quiet:
        print("\n".join(full))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(SCRIPT_VERSION + "\n" + a.file + "\n" + "\n".join(full) + "\n")

    words = sum(len(p.split()) for p in paras)
    print(f"\n{a.file}: {len(paras)} paragraphs, {words} words")
    print(f"{'rule':<22}{'kind':<6}{'hits':>5}")
    for name, kind, n in counts:
        if n:
            print(f"{name:<22}{kind:<6}{n:>5}")
    nban = sum(n for _, k, n in counts if k == "BAN")
    nlook = sum(n for _, k, n in counts if k == "LOOK")
    print(f"{'total BAN':<28}{nban:>5}\n{'total LOOK':<28}{nlook:>5}")
    if a.out:
        print(f"each hit, with its paragraph: {a.out}")
    if a.strict and nban:
        sys.exit(1)


if __name__ == "__main__":
    main()
