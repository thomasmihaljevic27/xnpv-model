# Prospect model: brief for the next session

Written 2026-10-14, at Thomas's request, to open the prospect-model session.

## What Thomas wants

- **Simplest version first, then build up.** "Start as simple as possible and work our way up. I'll decide what the
  parameters of the model will be then." Each step adds one thing, and Thomas decides whether it stays.
- **A plain-English specification, agreed step by step, before code.** The outline so far
  (MODEL_DIRECTIVES directive 6, "Prospects"):
  - the draft slot is the starting value;
  - then the prospect's own information: production history from Elite Prospects, adjusted to NHL terms, and
    physical traits such as size; age is a candidate too;
  - any step that reads his recent seasons uses 50/30/20 unless Thomas decides otherwise;
  - undrafted prospects use the same model without the draft-slot starting value.
- **Its own document**, separate from "Valuing Draft Picks". Agree three to five take-aways first, then draft to the
  writing-style skill (section 1.6).

## How to work (from CLAUDE.md and this week's sessions)

- Put each choice to Thomas in hockey terms: what it changes and what it costs. Never use a label alone.
- Score each added input alone and in combination, on the same rows, before saying which one carries a gain.
- Every age follows the CBA: September 15. Drafted players' signing ages come from `30_OUTPUT/elc_signing_dates.csv`.
- No valuation sees its own season: only information available before the valuation date.
- State which weighting each step uses (50/30/20 by default).

## What is ready

- **The starting value.** The pick curve gives a pick's value as the star value ($18.03M, `pick_curve.py` v1.5)
  times Bacon's probability that the slot produces a star (`10_SOURCE/draft_slot_baseline.csv`).
- **Elite Prospects data.** `30_OUTPUT/ep_out/ep_prospects.db` holds the draft pages, skater and goalie seasons,
  and bios. The pull (`ep_extract.py` v3.5, 2026-10-08) covers 679 of 680 skater league-seasons, 677 of 680 goalie
  league-seasons and 4,953 bios.
- **The bridge to NHL ids.** `30_OUTPUT/ep_out/ep_nhl_bridge.csv` (`ep_nhl_bridge.py` v1.1) has no conflicts and no
  NHL id claimed twice. Nick Henry and Tyler Vesel are resolved.
- **League translation factors.** `10_SOURCE/nhle_temporal.csv` gives era-varying NHLe for 142 leagues, 2006-07 to
  2025-26. These are not yet tested for this use.
- **Inputs checked.** Every input the model will call reads 50/30/20 (`40_DOCS/Age_and_Weighting_Audit.md`).

## Questions to settle with Thomas (bring as options, not answers)

1. **What a prospect's value is.** The pick curve values a drafted player as delivered value minus cost over his
   control window (entry-level deal, then control seasons at the qualifying offer or the arbitration price).
   The default is the same currency for prospects.
2. **Where the prospect model hands over to the player model.** The player forecast needs an NHL season of 10+
   games in the three before the valuation date. Is everyone without one a prospect?
3. **What the simplest version is.** The candidate: a prospect is worth his slot's pick-curve value, adjusted only
   for how many seasons have passed since his draft. Each later step (production, age, size, signed or not) is then
   one addition to that.
4. **The look-ahead point.** A 2007-2017 draftee valued from his slot sits inside the star value's fit. Leaving
   his draft out moves the star value by -8.0% to +7.5% (`25_TESTS/pick_class_overlap_check.py`). Is that stated as
   a limitation, or is the fit refitted without his draft?

## Background

- `00_STATE/sessions/2026-10-06.md`: a first design proposal for one model family covering picks and prospects
  (superseded in its details on 2026-10-09; useful as context).
- `00_STATE/MODEL_DIRECTIVES.md` directive 6: the full draft and prospect specification so far.
- `00_STATE/WORK_QUEUE.md`: the live list (the prospect model is the next item); its pointer to this brief is the first line there.
