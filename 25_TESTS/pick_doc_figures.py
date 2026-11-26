"""
pick_doc_figures.py -- the pick document's figures that model_doc_figures.py does not compute.

For "Valuing Draft Picks" (40_DOCS/Valuing Draft Picks.docx, built by 25_TESTS/pick_doc.js; Thomas: "Agreed, re-run those
two and build it", 2026-11-26). Everything else the document quotes comes from OUTPUT_DIR/model_doc/numbers.json.

READS, each guarded by a single match or an equality:
  * pick_elc_term_check_log.txt (25_TESTS/pick_elc_term_check.py v1.0): entry-level seasons at the term left;
  * pick_group6_check_log.txt (25_TESTS/pick_group6_check.py v1.1): CBA Group 6 at its upper bound;
  * draft_window_count_log.txt (25_TESTS/draft_window_count.py): PuckPedia's free-agency year against the rule; the
    2017 draft's windows cut by the data's end;
  * pick_curve_players.csv, pick_curve_scales.csv, traded_pick_values.csv, SOURCE_DIR/draft_slot_baseline.csv,
    model_doc/numbers.json: the deceased left out or in, the intercept's effect on traded picks, Bacon's implied star
    share, the example pick's place in its round.
WRITES: OUTPUT_DIR/pick_doc/numbers.json.
Run from the repo root:  python 25_TESTS/pick_doc_figures.py
"""

import json
import os
import re
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "pick_doc_figures.py v1.0 (2026-11-26)"
load_dotenv(".env")
OUT, SRC = Path(os.environ["OUTPUT_DIR"]), Path(os.environ["SOURCE_DIR"])
print(SCRIPT_VERSION)


def one(pat, text, what):
    m = re.findall(pat, text)
    if len(m) != 1:
        sys.exit(f"GUARD FAILED: {what}: {len(m)} matches")
    return m[0]


N = {"script": SCRIPT_VERSION}
MD = json.loads((OUT / "model_doc" / "numbers.json").read_text(encoding="utf-8"))
STAR = MD["picks"]["shapes"]["star probability (adopted)"]["terms"]["p_star"]["b"]
main = float(pd.read_csv(OUT / "pick_curve_scales.csv").set_index("scale_kind").loc["main", "scale_M"])
if abs(STAR - main) > 1e-9:
    sys.exit("GUARD FAILED: model_doc's star value is not pick_curve's")

# entry-level seasons at the term left
el = (OUT / "pick_elc_term_check_log.txt").read_text(encoding="utf-8")
if "pick_elc_term_check.py v1.0" not in el:
    sys.exit("GUARD FAILED: the entry-level check's version")
b0, b1, ch = one(r"one year of term ([\d.]+) \(se [\d.]+\); term left on the entry-level deal ([\d.]+) \(se [\d.]+\); "
                 r"change ([+-][\d.]+)%", el, "entry-level star values")
if abs(float(b0) - main) > 5e-5:
    sys.exit("GUARD FAILED: the entry-level check ran on another pick curve")
full3, mean3, max3 = one(r"all three seasons of a three-year deal: ([\d,]+); mean addition ([\d.]+)% of the cap, largest "
                         r"([\d.]+)%", el, "the three-year players")
N["elc"] = {"star_M": float(b1), "pct": float(ch), "players": int(full3.replace(",", "")), "mean_pct": float(mean3),
            "max_pct": float(max3)}

# Group 6
g6 = (OUT / "pick_group6_check_log.txt").read_text(encoding="utf-8")
if "pick_group6_check.py v1.1" not in g6:
    sys.exit("GUARD FAILED: the Group 6 check's version")
a, b, c = one(r"Group 3 only ([\d.]+); with the Group 6 bound ([\d.]+) \(se [\d.]+\); change ([+-][\d.]+)%", g6, "Group 6")
N["group6"] = {"star_M": float(b), "pct": float(c)}

# PuckPedia's free-agency year; the 2017 draft
wc = (OUT / "draft_window_count_log.txt").read_text(encoding="utf-8")
diffs = re.search(r"difference in seasons \(PuckPedia minus this rule\), counts:\ndiff\n((?:\s*-?[\d.]+\s+\d+\n)+)", wc)
if not diffs:
    sys.exit("GUARD FAILED: the PuckPedia check")
cnt = {float(x.split()[0]): int(x.split()[1]) for x in diffs.group(1).strip().splitlines()}
N["ufa_check"] = {"agree": cnt[0.0], "n": sum(cnt.values())}
y17 = one(r"\n2017\s+(\d+)\s+(\d+)\s", wc, "the 2017 draft's windows")
N["d2017"] = {"picks": int(y17[0]), "past": int(y17[1])}

# the drafted players who died: left out (the model) and left in
pl = pd.read_csv(OUT / "pick_curve_players.csv")
inc = pl[pl["draftYear"].between(2007, 2017)]
fit = lambda d: float((d["surplus"] * d["p_star"]).sum() / (d["p_star"] ** 2).sum() / 1e6)   # through zero
dead = inc["excluded_deceased"].astype(bool)
N["deceased"] = {"out_M": fit(inc[~dead]), "in_M": fit(inc), "n": int(dead.sum())}
if abs(N["deceased"]["out_M"] - main) > 1e-9:
    sys.exit("GUARD FAILED: the fit without the deceased is not the main star value")

# a single intercept: its effect on the traded picks and on the seventh-round ones
SI = MD["picks"]["shapes"]["star probability and an intercept"]["terms"]
tp = pd.read_csv(OUT / "traded_pick_values.csv")
if abs(float((tp["star_chance"] * STAR).sum()) - float(tp["value_M"].sum())) > 1e-6:
    sys.exit("GUARD FAILED: traded picks are not star value x star chance")
with_i = SI["intercept"]["b"] + SI["p_star"]["b"] * tp["star_chance"]
N["intercept"] = {"all_pct": float(100 * (with_i.sum() / tp["value_M"].sum() - 1)),
                  "r7_pct": float(100 * (with_i[tp["pick_round"] == 7].sum() / tp.loc[tp["pick_round"] == 7, "value_M"].sum() - 1)),
                  "r7_n": int((tp["pick_round"] == 7).sum())}

# Bacon's star probabilities: the share of stars they imply among the skaters drafted 2007-2015
sk = pl[pl["draftYear"].between(2007, 2015) & ~pl["is_goalie"].astype(bool) & ~pl["excluded_deceased"].astype(bool)]
if len(sk) != MD["picks"]["stars"]["skaters"]:
    sys.exit(f"GUARD FAILED: {len(sk)} skaters, model_doc counts {MD['picks']['stars']['skaters']}")
N["bacon_implied"] = float(sk["p_star"].mean())

# the example pick: where the round average sits in round 2 of the 2019 draft (31 teams: picks 32 to 62)
bl = pd.read_csv(SRC / "draft_slot_baseline.csv").set_index("draft_pick")["p_star"]
TPK = MD["picks"]["trade_pick"]
r2 = bl.loc[32:62]
if abs(r2.mean() - TPK["star_chance"]) > 1e-9:
    sys.exit("GUARD FAILED: the round-2 average is not the example pick's star chance")
at = int((r2 - r2.mean()).abs().idxmin())
N["example"] = {"first": 32, "last": 62, "middle": 47, "pick_nearest_avg": at, "p_at_50": float(bl.loc[50]),
                "value_at_50_M": float(bl.loc[50] * STAR)}

os.makedirs(OUT / "pick_doc", exist_ok=True)
(OUT / "pick_doc" / "numbers.json").write_text(json.dumps(N, indent=1), encoding="utf-8")
print(json.dumps(N, indent=1))
