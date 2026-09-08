"""
check_stale_anchor_agreement2.py                              2026-07-29
===========================================================================
READ-ONLY. Writes one text file. Changes nothing, rebuilds nothing.

FIXES v1's CRASH
----------------
v1 used a positional itertuples attribute (r._11) that did not resolve. This
version iterates over dicts instead, so column naming cannot break it.

ALSO ADDS WHAT v1 SHOULD HAVE HAD
---------------------------------
v1 found 92 disagreeing rows out of 1,008 comparable, against only 13 in the
[1b] guard. Those two numbers are not measuring the same thing and the gap is
probably mostly my tolerance:

  * [1b] compares DOLLAR VALUE with a $1 threshold, over the 776 rows that
    are a contract's first season in 2018-2025.
  * v1 compared the PROJECTION with a 1e-6 threshold, over all 1,008 rows
    priced by both files.

A projection difference of 0.001 WAR is a real disagreement but worth about
$1,000, so it passes [1b] and fails mine. So this version reports the
distribution of the differences and splits them by size, which tells us
whether we are looking at 92 real problems or 13 real problems and 79
rounding artifacts.

It also splits the disagreements by whether the row is one the stale-anchor
fix touched. Rows tagged 50/30/20, 60/40 or t-1 only were priced by both
files before any of this work, so a disagreement there is PRE-EXISTING and
not something the fix caused. That distinction matters more than the total.

HOW TO RUN
----------
    python check_stale_anchor_agreement2.py

Writes stale_anchor_agreement2.txt. Send me that.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

OUT = []


def say(msg=""):
    print(msg)
    OUT.append(str(msg))


def dump():
    (HERE / "stale_anchor_agreement2.txt").write_text(
        "\n".join(OUT), encoding="utf-8")
    print("\nwrote stale_anchor_agreement2.txt")


say("=" * 78)
say("STALE-ANCHOR AGREEMENT CHECK v2")
say("=" * 78)

try:
    import contract_npv as C
except Exception as e:
    say(f"\nFAILED to import contract_npv: {type(e).__name__}: {e}")
    dump()
    sys.exit(1)

say(f"\nSTALE_TARGET={C.STALE_TARGET}  STALE_GATE={C.STALE_GATE}"
    f"  STALE_MAXBACK={C.STALE_MAXBACK}  LAMBDA_G={C.LAMBDA_G}")
say(f"GOALIE_LEAGUE_AVG={C.GOALIE_LEAGUE_AVG:.9f}")

eng = C.NPVEngine()
gp = eng.gp_spine.copy()
v2 = pd.read_csv(HERE / "goalie_value_spine_v2.csv")

# --------------------------------------------------------------------------
# Ask contract_npv for its own projection on every goalie row.
# --------------------------------------------------------------------------
rec = []
for r in gp.itertuples():
    t0 = int(r.season_start)
    try:
        pw, src = eng.g_proj.shrunk_projection(r.nname, t0)
    except Exception as e:
        pw, src = np.nan, f"ERROR:{type(e).__name__}"
    rec.append({"player_id": r.player_id, "season_start": t0,
                "nname": r.nname, "npv_proj": pw, "npv_src": src})
mine = pd.DataFrame(rec)

j = mine.merge(
    v2[["player_id", "season_start", "full_name", "weight_scheme",
        "shrunk_projection"]],
    on=["player_id", "season_start"], how="inner")
j["eng_proj"] = pd.to_numeric(j["shrunk_projection"], errors="coerce")
j["absdiff"] = (j["npv_proj"] - j["eng_proj"]).abs()
j["family"] = (j["weight_scheme"].astype(str)
               .str.replace(r"\[.*\]", "[...]", regex=True))

# Rows the stale-anchor fix created. Everything else was priced by both files
# before this work started.
j["touched_by_fix"] = j["family"].isin(
    ["stale_anchor_carry[...]", "flat_carry_out_year[...]"])

both = j[j["npv_proj"].notna() & j["eng_proj"].notna()].copy()
say(f"\nrows comparable on both sides: {len(both):,}")

# --------------------------------------------------------------------------
# Magnitude distribution. This is the question v1 could not answer.
# --------------------------------------------------------------------------
say("\n--- SIZE OF THE DISAGREEMENTS " + "-" * 47)
say("  a projection difference of X WAR is worth roughly X * $1.01M, since")
say(f"  BETA_G = {C.BETA_G:.8f} of the cap per WAR at a ~$95.5M ceiling.")
say("")
BANDS = [(1e-9, 1e-6, "negligible  (<1e-6)"),
         (1e-6, 1e-4, "tiny        (1e-6 to 1e-4)"),
         (1e-4, 1e-2, "small       (1e-4 to 0.01)"),
         (1e-2, 0.1, "moderate    (0.01 to 0.1)"),
         (0.1, 1.0, "large       (0.1 to 1.0)"),
         (1.0, 1e9, "severe      (>1.0 WAR)")]
say(f"  exact matches (diff == 0): {int((both['absdiff'] == 0).sum()):,}")
for lo, hi, lab in BANDS:
    n = int(((both["absdiff"] > lo) & (both["absdiff"] <= hi)).sum())
    if n:
        sub = both[(both["absdiff"] > lo) & (both["absdiff"] <= hi)]
        say(f"  {lab:<30}{n:>6,}   worth up to ~${hi * 1.01:,.0f}M"
            f"   (fix-touched: {int(sub['touched_by_fix'].sum())})")

MATERIAL = 0.01          # ~$10k of value; below this nothing is actionable
bad = both[both["absdiff"] > MATERIAL].sort_values("absdiff", ascending=False)
say(f"\n  MATERIAL disagreements (>{MATERIAL} WAR): {len(bad)}")

# --------------------------------------------------------------------------
# Pre-existing versus caused by the fix. The decisive split.
# --------------------------------------------------------------------------
say("\n--- PRE-EXISTING versus CAUSED BY THE FIX " + "-" * 35)
for lab, mask in [("touched by the stale-anchor fix", bad["touched_by_fix"]),
                  ("PRE-EXISTING (both files priced these before)",
                   ~bad["touched_by_fix"])]:
    say(f"  {lab}: {int(mask.sum())}")
say("")
say("  by engine weight_scheme family:")
for k, n in bad["family"].value_counts().items():
    say(f"    {n:5,}  {k}")
say("")
say("  by contract_npv source tag:")
for k, n in bad["npv_src"].value_counts().items():
    say(f"    {n:5,}  {k}")

# --------------------------------------------------------------------------
# The proration hypothesis.
# --------------------------------------------------------------------------
say("\n--- PRORATION HYPOTHESIS " + "-" * 52)
say("  The engine builds v2 with prorate=True, scaling the shortened 2019")
say("  and 2020 seasons. If contract_npv does not, any anchor reaching those")
say("  seasons diverges. 'window' below is the span of seasons the row's")
say("  anchor can draw on.")
say("")


def window(season):
    """Widest span of seasons this row's anchor can touch: the walk-back may
    start at season-1 and reach STALE_MAXBACK back, and the cascade at each
    step looks three seasons further."""
    return (season - 1 - C.STALE_MAXBACK - 3, season - 1)


if len(bad):
    n_touch = sum(1 for s in bad["season_start"]
                  if window(s)[0] <= 2020 and window(s)[1] >= 2019)
    say(f"  material disagreements whose window reaches 2019 or 2020: "
        f"{n_touch} of {len(bad)}")
    if n_touch == len(bad):
        say("  ALL of them. Proration is the cause.")
    elif n_touch == 0:
        say("  NONE of them. Proration is not the cause.")
    else:
        say("  Mixed, so there is more than one cause.")

    say("\n--- WORST 40 " + "-" * 63)
    say(f"  {'name':<24}{'seas':>6}{'npv':>8}{'engine':>8}{'diff':>8}"
        f" {'19/20':<6}{'engine scheme':<26}{'npv src'}")
    for r in bad.head(40).to_dict("records"):
        lo, hi = window(r["season_start"])
        touch = "YES" if (lo <= 2020 and hi >= 2019) else "no"
        say(f"  {str(r['full_name'])[:23]:<24}{r['season_start']:>6}"
            f"{r['npv_proj']:>8.3f}{r['eng_proj']:>8.3f}{r['absdiff']:>8.3f}"
            f" {touch:<6}{str(r['weight_scheme'])[:25]:<26}{r['npv_src']}")
else:
    say("  no material disagreements to test")

# --------------------------------------------------------------------------
# One-sided rows.
# --------------------------------------------------------------------------
only_npv = j[j["npv_proj"].notna() & j["eng_proj"].isna()]
only_eng = j[j["npv_proj"].isna() & j["eng_proj"].notna()]
say(f"\n--- ONE-SIDED ROWS " + "-" * 57)
say(f"  priced by contract_npv but not the engine: {len(only_npv)}")
say(f"  priced by the engine but not contract_npv: {len(only_eng)}")
for lab, sub in [("npv-only", only_npv), ("engine-only", only_eng)]:
    if len(sub):
        say(f"\n  {lab}, first 12:")
        for r in sub.head(12).to_dict("records"):
            say(f"    {str(r['full_name'])[:23]:<24}{r['season_start']:>6}"
                f"  {str(r['weight_scheme'])[:32]:<34}{r['npv_src']}")

say("\n--- SPINE COMPOSITION " + "-" * 54)
for k, n in j["family"].value_counts().items():
    say(f"  {n:6,}  {k}")

say("\n" + "=" * 78)
dump()
