# STANDING FLAGS & OPEN QUESTIONS — NHL Trade Market Efficiency

<!-- Extracted from PROJECT_STATE.md on 2026-09-09 (v3.2 restructure). Pure move, no content change. -->
<!-- Karl's identification axes to watch on every design choice, the triaged open
     questions, and the original-conflicts resolution record. A flag is a standing
     watch-item on a design axis; an open question is a specific undecided thing. -->

---

## Standing flags (Karl's identification axes — watch on every design choice)


- **VERIFICATION GAP, NOW COMPOUNDED (updated 2026-09-08).** The Stage 2-5 changes were never run
  locally or cross-checked the way Stage 1 was, and that gap is still open. It is now compounded:
  every script had its paths replaced on 2026-09-08 and nothing has been run end to end since. The
  2026-07-28 figures are carried on the reasoning that only paths changed, which is exactly the
  class of reasoning the reproduce-before-extending rule exists to reject. Until the player chain
  is re-run, treat every figure in this file as unverified on the current codebase.
- **Scripts wrote to the current working directory (found and fixed 2026-09-08).** Six scripts
  resolved paths relative to wherever they were launched, two of them writing load-bearing
  artifacts. This is the mechanism behind the stale duplicates found on disk, some predating the
  2026-07-28 rebuild by three weeks. Standing lesson: a stale duplicate is usually created by a
  script with a relative path, not by a person copying a file.
- **This file now lives on three surfaces (new 2026-09-08).** Local working folder (git-tracked),
  Dropbox `00_STATE`, and the Claude project. Local is authoritative and is now the git copy, so an
  edit made anywhere else is lost on the next pull. Update local first, refresh Dropbox from it,
  then replace the Claude project copy by hand. The project copy does not update itself and has
  already been found serving stale files twice.

- **NEW 2026-07-28 — the yield-curve tail versus the minimum tradeable unit.** The curve prices a pick in the 151-224 band at 0.00853 of the cap, roughly $0.81M. That number is the mean of a lottery: **the median outcome is zero, 74.5% of those picks produce nothing, and the top 5% hold 42% of the band's entire value across eleven cohorts** (round 1, for contrast: median $4.74M, 7.1% produce nothing, top 5% hold 16.3%). The same pick is also the *smallest unit of consideration a club can add to a trade*, since cash cannot be traded. Two readings are observationally equivalent in the pure-pick sample: either the tail is overvalued relative to what clubs treat it as worth, or the curve is right and clubs systematically undervalue late picks. Approximating the rebuilt steeper curve moves the implied discount only from 0.486 to 0.503, so **staleness is not the explanation**. This touches every back-test trade containing a small makeweight, which is most of them.
- **NEW 2026-07-28 — short first seasons lose the age−1 curve base.** Supersedes the Samoskevich note. The MIN_GP=20 panel filter excludes a short rookie cameo, so a player whose first season was (say) 7 games has no age-21 observation and any valuation basing at 21 falls through to flat. Direction is conservative, but it hits precisely the population the young-extension negative-NPV finding lives in. Needs a materiality count before the paper.
- **UPDATED 2026-07-28 — the one-directional-corrections flag is now PARTLY ANSWERED.** The flag recorded that six of ten Stage 1 fixes moved values up and none moved them down, which is the kind of uniform sign a supervisor is right to be suspicious of. **The 2026-07-28 evening run is the first change set to move values DOWN:** median contract NPV fell from +$0.76M to +$0.32M and the distribution tightened at both ends (p10 −8.15→−7.97, p90 +2.97→+2.52), driven by the lower intercept and the tighter retention gate. Forwards fell, defencemen rose on the higher defence slope, and fringe terminal values fell hardest. Visible in named players rather than only in constants: Sandin (D) $12.67M→$14.22M, Samoskevich (F) $14.43M→$13.51M with terminal $11.12M→$10.44M, Rantanen (D) −$73.97M→−$73.18M. **This is direct evidence the corrections are not uniformly signed by construction, and belongs in the robustness section.**

- **Discount rate r — RESOLVED (estimated and locked 2026-07-05, D15-D18; stale flag text corrected 2026-07-14 on Thomas's confirmation).** Structure: survival-weighted value side (exit hazard from the panel by quality × age) + 3% cap-growth denominator, fundamentals-only — GM impatience deliberately excluded (D15) so the back-test can still detect over-discounting as a finding. Kept in this list as a closed record because every pillar's NPV depends on it; see Resolved Decisions D15-D19.
- **Value_t circularity** — the dollars-per-win rate is Bacon-derived, so the risk was "testing" the model against a yardstick made of the same vendor's material. **RESOLVED WITH STATED LIMITATIONS (primary validator run 2026-07-14; was Fatal → Important 2026-07-04).** The Phase 4b primary check executed: the Bacon-derived trailing projection correlates r=0.576 (n=6,027, stable across all nine seasons) with GV-adj, a metric with zero Bacon inputs, in win units with no dollar conversion on the outcome side. Three limitations are load-bearing for how this is cited: (1) it is **convergent validity, not proof the dollar level of a win is correct** — the test runs in win units by design and can only show the projection tracks an independent measure; (2) validation is **strong for forwards (r=0.648), partial for defencemen (r=0.302)** — the known structural weakness of shot-and-shift data on defensive value, to be stated wherever this result appears; (3) the claim is **no shared model or vendor, not no shared reality** — both metrics describe the same underlying games, and the paper must say so before a referee does. **Robustness leg RUN 2026-07-14 — Phase 4b is now FULLY CLOSED.** GV-raw confirms rather than merely fails to contradict: rebased r=0.609, zero-sum r=0.564, bracketing the GV-adj primary (0.576); all three validators land in a tight 0.56-0.61 band across all nine seasons, and the t+1 horizon degrades gently in all three. One honest note preserved: GV-raw correlates as well as or slightly better than GV-adj — explained by GV-raw retaining team-context signal that the RAPM adjustment strips and that Bacon WAR also carries; a finding about what each metric measures, not grounds to revisit the locked primary choice. Rebased-D at 0.442 is treated with caution (the rebase's documented offensive-D inflation plus deployment correlation), not cited as the best defence number. Still flag anything that would re-entangle the input rate and the outcome measure.
- **Look-ahead bias** — enforce the trailing-season rule (t-1, t-2) everywhere; flag any trade-season-row or current-vintage leak.
- **Selection bias** — trades happen only on mutual agreement, inflating apparent mispricing; no-trade counterfactual unobserved. Structural limitation (to be documented in the model overview).
- **Goalie playing-time endogeneity** — goaltender starts are allocated on perceived quality (weaker goalies get benched, stronger ones start more), which inflates naive season-to-season WAR correlations computed on the full population. Confirmed 2026-06-30: restricting to GP>=20 drops the goalie persistence correlation materially, and restricting further to contract-signing-anchored established goalies drops it further still, from r=0.30 down to r=0.08-0.09. Any goalie predictability/persistence statistic must state its population (full league, GP-filtered, or contract-signing-anchored) before being compared to another figure or cited in the paper.
- **Monopsony events** — NTC/NMC-forced trades are a separate back-test category, never residual mispricing. An UPPER BOUND was established 2026-06-30 (53 of 205 clean trades carry a clause-holder flag), but the **forced-trade detection rule is not yet implemented** — presence of a clause is not proof it caused the move.
- **Cap regime breaks** — flag long-term contracts from the 2020-2022 flat-cap window; they need the regime indicator.
- **Retention amendment (2025-26)** — the 75-day re-retention restriction changes third-party-broker strategy; flag any pre/post bridge.
- **Same-name collisions** — flag name-based joins touching Aho / Pettersson / Murphy / Anderson. Separately, WAR.csv merges two different players each under **Ryan Johnson** and **Nathan Smith** — left unmatched in the age join; exclude (don't disambiguate) until split by ID.
- **WAR_with_age.csv nhl_id pollution (2026-07-19)** — the age join's fuzzy/EP-fixed stages stamped **33 NHL IDs onto the wrong lookalike's rows** (Rick Nash carries Riley Nash's ID; Todd Bertuzzi carries Tyler's; Jeff Schultz carries Justin's). Any ID join through this file must require **name agreement** (the 3a linkage does). **COUNTS CORRECTED 2026-07-27 (item 1.8):** measured directly on the file, **23 identifiers carry more than one name, covering 217 rows and 47 players** — not the 33 / 322 / 69 the review recorded, nor the 113 / 36 recorded here previously. All three figures were in circulation; the measured pair is the one to cite. The guard is now built (`join_on_id_and_name()` in `age_join.py`, with a self-test that fires every run), so an ID-only join through this file raises instead of attaching the wrong player. Spillover: wrong birthdates on some of those rows feeding the locked aging curve and exit hazard — some genuinely mis-aged (Schultz aged 17, true 21), some age-correct. Likely immaterial to λ=0.55; audit of age_join.py is **Thomas's open call**.
- **Duplicated loader logic across two files (NEW 2026-07-27, found during item 1.5)** — `skater_value_engine.py` and `skater_forward_projection.py` each build their OWN copy of the season-WAR lookup rather than sharing one. Fixing only the value engine changed nothing downstream, because the projection is the file that actually prices contracts. Any future change to how season data is loaded, filtered, or de-duplicated MUST be applied in both, or it will appear to work and quietly do nothing. Same class of trap as the three historical stale-file incidents.
- **Corrections have run one way (NEW 2026-07-27)** — six of the Stage 1 fixes moved contract values upward and none moved them systematically down. Each is defensible alone; the pattern is what invites a question. Present Stage 1 as a set with a stated net effect in the robustness section rather than as separate corrections scattered through the methodology.
- **Qualifying-offer salary substitute (NEW 2026-07-27, item 1.10)** — ~25% of qualifying offers are computed from average annual value because no final-year salary exists, which switches off the CBA's 120%-of-cap-hit ceiling in exactly the cases it was written for. Direction: offer understated → control-year cost understated → **surplus overstated**. Now tagged in the output (`qo_salary_source`) and counted in the run log. Not fixable with current data; needs per-season salary coverage extended.
- ~~**Stage 2-5 review changes not locally verified (NEW 2026-07-28)**~~ — **CLOSED 2026-09-09.** All four are now run locally and reproduce: the new skater price equation (Stage 3 rate, in force through `skater_forward_projection.py`), the retention-calibration fix (Stage 4, 21.3%→27.0% buckets unmoved), the rebuilt draft curve (to the cent), and the Stage 2 length-term null test (`term_premium_test.py` — decisive null, every spec constant exact, value-side share 0.000). Not provisional any more. GV-raw robustness legs of the Stage 2 test remain an optional, un-run extension.
- **Erik Gustafsson = third WAR.csv merged name (2026-07-19)** — joins Ryan Johnson and Nathan Smith (13-14 PHI row is the undrafted b.1988 player; 15-16+ is the 2012-drafted b.1992 player). Standing rule applied: 2012 #93 pick excluded from the curve. Also: **Goalies_WAR splits traded goalies into one row per team per season** (78 duplicate name-seasons) — always SUM within name-season.

---

## Open questions (triaged)


**IMPORTANT — should the mean-reversion blend weight vary by player type? (new 2026-08-28.)**
Lambda is locked at 0.55 and applied universally to every skater. It was recovered by player-split
cross-validation on the pooled panel, so it is the single weight minimising average held-out error,
not a weight tested for whether it should differ by quality tier, position, age, or career stage.
Raised verbally in the supervisor meeting and previously unlogged anywhere. The question has real
content: a star with a long stable record arguably warrants less shrinkage toward the comparable
norm than a fringe player with two noisy seasons, and the current design gives them the same.
Resolving it means re-running the cross-validation within strata rather than pooled. Any change is
rate-adjacent, since the anchor feeds the projection that feeds the price equation. Not started.


**Fatal**
- *(none open)* — the discount rate r, the sole Fatal item since 2026-06-30, was **estimated and locked 2026-07-05** (Phase 1a; D15-D18). Structure: survival-weighted value + 3% cap-growth denominator, fundamentals-only, exit hazard estimated from the panel. See Resolved Decisions D15-D19 and the Work Queue Phase 1 block. No Fatal-tier open questions remain.

**Important (new 2026-07-28)**
- ~~**Stage 2-5 review changes not yet locally verified.**~~ **CLOSED 2026-09-09** — all four ran locally and reproduced (Stage 3 rate, Stage 4 retention, rebuilt draft curve, Stage 2 `term_premium_test.py` decisive null). See the DECISIONS.md verification-gap entry and the v3.3 change-log line.
- ~~**Scripts and run logs stale relative to two full sessions of changes**~~ — **CLOSED 2026-07-30.** The risk was real and it fired at least twice: a chat read the superseded OLS constants out of the project mirror during the Lane Hutson session, and the project was still serving the pre-rebuild draft curve plus output from a rejected goalie patch. The Claude project no longer holds model outputs or scripts at all; it holds only decision-cadence files. Scripts live in Dropbox `20_CODE/` and are attached per message when worked on.

**Important**
- Value_t circularity — **FULLY RESOLVED 2026-07-14** (primary + robustness legs both run; see Standing Flags for results and the three citation guardrails). The paired validator design executed in full: GV-adj 0.576, GV-raw rebased 0.609, GV-raw zero-sum 0.564 — three affirmative answers in a tight band. Moves to the Decision Log; kept here one cycle as a closed record.
- League-average vs team-specific value: the residual blends mispricing with team-fit premiums, private-information rents, and monopsony. Empirical separation is an open back-test design problem.
- Forced-trade detection rule not yet implemented. UPPER BOUND established 2026-06-30: 53 of 205 clean trades carry a clause-holder flag, but presence of a clause is not proof it caused the move.
- Point-in-time metric availability: single current-vintage export, no archived season snapshots. The 2018 window limits but does not remove look-ahead. The constraint Karl is most likely to press; mitigated, not solved.
- Long-term deals crossing UFA eligibility need separate terminal-value handling.
- Outcome-measurement design: the realized-outcome window and playoff-vs-regular-season weighting are not fixed (a Cup rental != a seven-year accumulator).
- Efficient-market null not yet stated as a possible finding (Work Queue Phase 6).
- Trade-data completeness: the PuckPedia trades export has only one 2017-18 trade (earliest 2018-06-23); realized sample effectively runs 2018-19 -> 2025-26. Intended window is 2017-18 — verify against PuckPedia and re-pull the early window before finalizing the sample (low priority).

**Important (new 2026-07-05)**
- **`WAR_AAV_Regression_Report_v2` is superseded** (see Phase 1b decisions D6-D9): its headline numbers pooled goalies into the skater sample, undocumented. A v3 report restating the skater-only rate, the market-distinctness result, and the regime finding is owed but not yet written — flag if anyone (including future Claude sessions) cites v2's RFA/UFA-distinctness or flat-cap-break figures as current.
- **Value_t floor at league minimum (D10) is implemented but not yet stress-tested** against the back-test: whether floored seasons behave sensibly inside a multi-season NPV (once Layer 2/1d exist) hasn't been checked.

**Important (new 2026-07-27, from the Stage 1 work)**
- ~~**The 83 never-played goalie rows**~~ — **CLOSED 2026-07-29 (evening).** The fix is applied and verified; see the v2.9 changelog entry. What follows is the history, retained because the attribution was wrong twice and should not be re-derived. **SUPERSEDED first on 2026-07-29 (afternoon):** The figure of 83 could not be reproduced from the files: the `no_observed_war_history` tag covers **748 rows and 286 players**, with 203 rows carrying a blank trailing figure. Re-derived, and the underlying defect turned out to be a **missing cascade branch** rather than a pricing choice — a goaltender with no t−1 season but a usable t−2 or t−3 fell through to the no-history branch, which is how Carey Price, Corey Crawford, Ben Bishop, Spencer Knight, and Carter Hart were all tagged as never having played. `patch_goalie_stale_anchor.py` was written to fix it and **has not been run.** It hard-codes `GOALIE_LEAGUE_AVG = 2.189172466` first (the constant had to be broken loose before the rows it reads from could be repriced; alpha/beta are NOT hard-coded and refit identically to twelve decimal places), then adds `STALE_TARGET = 0.650` and `STALE_GATE = 0.312`, then the cascade branch, then the target routing. **Two live items replace this one:** run the patch, and decide the 93 cascade-gap rows (the session that produced the script ended waiting on that decision). Nothing downstream of the goalie branch should be regenerated until the patch runs.
- **Negative-anchor backcast at k=1 slipped after the curve rebuild** — the curve now trails hold-flat by 1.4% at one year out for negative anchors (n=233), where it previously led by 0.2%. It still wins clearly at k=2 (+5.2%) and k=3 (+8.0%), and D12 v3's evidence base is unaffected, so no action taken. Watch it if the population grows.
- **Review Stages 2-5 — RESOLVED 2026-07-28, moved to Resolved Decisions.** All items closed; see the "Player Model Review — Stages 2-5" block. Kept here one cycle as a closed record, per the project's convention for recently-resolved Important items.

**Optional**
- Single discount rate vs player-specific risk (does a 36-year-old carry the same r as a 24-year-old?). NOTE: assumed a baseline r already existed -- see the new Fatal item, r has never actually been estimated at all yet.
- Cap-inflation shock handling beyond the flat-cap regime indicator.
- Contender vs rebuilder marginal-win value.
- Signing-bonus structure / front-back-loading (absent from data; equal-AAV contracts valued identically).
- LTIR as a strategic asset (currently only a dead-cap accounting effect).
- ELC slide rule (extra team control not cleanly captured by the 3+4 window).
- Replacement-level variance by position (position-blind intercept may understate a #1 goaltender).
- Slug normalization pre-flight feasibility.
- Left-truncation — **RESOLVED 2026-07-19 (D25):** fitting cohorts 2007-2017, complete D+9 windows only; 2005-06 dropped rather than backfilled.

---

## Resolution record & remaining housekeeping


*Conflicts raised 2026-06-30 were resolved by Thomas the same day:*

1. **Back-test window** — intended **2017-18 onward** (Thomas to verify and, if needed, re-pull the missing early window; low priority). Data currently effectively begins 2018-19.
2. **ELC valuation** — resolved: **only RFA and UFA regressions exist.** ELC value = project production, price it at the RFA rate (what they would earn as an RFA), then subtract the slotted ELC cost. ELC is folded into the RFA regression; no separate ELC rate. (Reverses an early, abandoned line of thinking.)
3. **The `..._Paper_v6` file** — it is the model **overview / scoping document**, not a manuscript. Out of date and being replaced. No paper is written until the model is built.

*Remaining housekeeping (refreshed 2026-07-28):*
- The items (a)-(d) below this line as of v2.5 were all applied to Craft successfully on 2026-07-27 (the "Craft connection issue" session reconnected and pushed the full Stage 1 update set across seven hubs). That entry is now historical.
- **Craft is unreachable again this session (2026-07-28)** — same intermittent failure mode noted in at least three prior sessions (2026-07-03, 2026-07-05, 2026-07-27 before reconnecting). Craft therefore does not yet carry the Stages 2-5 closure (new rate, retention fix, rebuilt draft curve) documented in this file's v2.6 update. A paste-ready `CRAFT_UPDATE_2026-07-28.md` has been prepared covering: Decision Log (Stages 2-5 close-out entry), Player Model Progress Log (item-by-item narrative), Standing Flags (local-verification-gap flag), Open Questions (verification gap + script staleness, both new Important items), Work Queue (review roadmap fully closed), Regression Results (new skater rate), and the Draft Picks Progress Log (rebuilt curve). Apply next time the connector is reachable.
