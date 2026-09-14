# Phase 0: the evaluation harness, and the first look at Phase 1

Built 2026-09-14 in `50_REBUILD/`. Experimental. No production file was changed and no
locked decision was opened. Every figure below comes from development pages 2015–2021;
the confirmatory pages are sealed and untouched.

Reproduce with `python 50_REBUILD/code/run_phase0_acceptance.py`. Input: `10_SOURCE/WAR.csv`,
sha256 prefix `8406059a4db5a677`, 17,123 rows, 2007-08 to 2025-26.

## 1. What was built

Four modules, in dependency order.

**`rebuild_config.py`** — paths, shared constants, and the isolation guarantee. Every write
goes through `out_path()`, which raises on any path resolving outside `50_REBUILD/output/`.
Every vendor read goes through `assert_read_only_source()`. The rebuild cannot overwrite a
production artifact through the only file-handling functions it has.

**`player_season_table.py`** — one season table for the whole rebuild: cleaned career key,
position key, season, the WAR components and total, games, ice time, per-82 rates, games
share, and NHL experience. D20 proration is applied once, here, so nothing downstream can
apply it twice or forget it. It carries a **reproduction guard**: filtered to the production
loader's own rule, its season totals match `skater_value_engine.build_skater_war_lookup()`
on all 14,193 keys to zero difference, and the name-normalisation rule is checked against
the production one on every name in the source. The guard passes.

The two name keys are both emitted and both needed. The production cleaner strips a
parenthesised tag, so "Elias Pettersson(D)" cleans to the same string as the Canucks
forward; the engine survives that because its key carries the position. `aging_curve.py`
keys on the name alone and needs an explicit split. `pkey` (name + position) is
byte-identical to the engine's key and is what the guard compares; `career_key` is one key
per real human and is what anything following a player across seasons uses.

**`information_set.py`** — what was knowable on a date. A model receives an `InformationSet`
and has no other route to the data, so it *cannot* see a future season, rather than being
trusted not to. Two dates are kept apart: when the last regular-season game was played, and
when the vendor's completed-season WAR could be read. A 30-day availability lag sits between
them, declared and adjustable, rather than assumed to be zero. Where a season's end date is
not carried explicitly the fallback is 30 June of the ending year — later than any real
season end, so a wrong fallback can only make information arrive later than it truly did,
never earlier. 2019-20 ends on the 12 March 2020 suspension, because the remaining
regular-season games were never played.

Self-tests pass: for pages 2015, 2020, 2021 and 2025, deleting every season at or after the
decision date leaves that date's information set unchanged; 2019-20 is readable on
2020-07-01 and not on 2019-12-01; 2024-25 is unreadable on 2025-05-01 and readable on
2025-07-01.

**`forecast_harness.py`** — the scoreboard. A model is fitted once per page on outcomes
strictly before that page, then asked for a distribution over horizons 0 to 5. Scoring is by
horizon and by subgroup (level tier, position, experience band, age band where ages exist):
bias and MAE in the per-82 rate among players who played, bias and MAE in the season total
with **zeros for players who did not play**, MAE in games, a Brier score on participation,
and interval coverage. Model-versus-model comparison is paired on identical rows with a
bootstrap **clustered by career**, because one player contributes six overlapping horizons
across seven pages and his seasons are not independent draws.

The expected season total is formed in exactly one place:

    E[WAR] = p_play × rate_82 × gp_share

The rate forecast is conditional on playing and participation multiplies it once. The
production chain's separate exit-hazard haircut on an already-unconditional projection is
the double count this removes.

The holdout seal is code. `run()` refuses a 2022–2025 page unless the caller passes
`unseal=True` with a reason, which is logged. The refusal was tested and fires.

## 2. Phase 0 acceptance: PASS

The gate the plan sets is that the production chain's own forecast, re-expressed as a
harness model, reproduces the tilt already measured on the chain. If the harness scored the
production starting point as unbiased at the top, the harness would be measuring something
other than what the chain does, and every later comparison on it would be worthless.

A0 — the locked 60/40 blend of trailing WAR totals, carried flat, everyone assumed to play a
full season — scores as follows on 6,124 player-page rows per horizon across 1,516 careers:

| tier (trailing WAR) | n | bias, wins | over-projection |
|---|---:|---:|---:|
| below 0 | 5,760 | −0.37 | |
| 0 to 1 | 7,956 | +0.09 | +31% |
| 1 to 2 | 2,847 | +0.48 | +51% |
| 2 to 3 | 1,206 | +0.65 | +37% |
| 3+ | 603 | +1.00 | +35% |

Horizons 0 to 2. The tilt is reproduced: A0 over-projects stars by a full win. The
project's own measurement on the production chain was +24% at 3+ on 2020-25 pages; this is
+35% on 2015-21 pages with non-participation scored as zeros, so the two are not the same
statistic and are not expected to match to the point. Same sign, same tier ordering, same
order of magnitude. The harness measures what the chain does.

## 3. A finding that was not being looked for: the WAR export breaks in 2023-24

The season table's guard asserts that the six WAR components sum to the total. They do, to
floating point, for every season from 2007-08 through 2022-23. **From 2023-24 they stop.**
97.9% of rows in 2023-24 onward carry a residual; it is positive on average, and it grows
with the player's WAR — r = 0.79 for forwards, 0.53 for defencemen, about 2% of WAR at the
median and again at 3+ WAR. In absolute terms it is small: median 0.0026 wins, largest 0.332
(Sam Reinhart, 2023-24).

The cause is on the vendor's side — the export's recent seasons carry something in the total
that is not broken out into the six columns. This tree does not guess what. It appears
nowhere in `00_STATE/` and is, as far as the record shows, new.

**How the rebuild handles it.** The residual is carried as a seventh, explicitly unallocated
component, so the seven sum to the total exactly in every season. Three reasons. A
component-wise forecast that summed the six would systematically under-predict recent
seasons for exactly the players who carry the money — the tilt the rebuild exists to remove,
reintroduced from the side. Rescaling the six to hit the total would spread an unknown
quantity across six known ones in proportion to them, which asserts something about its
nature that no evidence supports. Named and carried, it gets its own persistence estimate
and the data says how much of it is signal.

The data's answer, below, is: none. Its fitted reliability constant pins at the top of the
grid, meaning the residual is shrunk entirely to the positional norm and contributes no
forecast signal. It is a level effect in recent seasons, not a skill.

**This affects the production chain too**, though not through this tree. Any anchor built
from the six components for a 2023-24 or later season is short by about 2%, concentrated on
the best players. The production chain reads the WAR total, not the components, so the level
is unaffected; `component_persistence_test.py`'s covariance shares, which are computed over
pairs including 2023-24 onward and are normalised to sum to one, carry the residual inside
them. The effect on those shares is small and has not been quantified.

## 4. The contract exports, and what they unblocked

The PuckPedia exports arrived as CSV part-way through this session, which closed two things
the earlier draft of this report listed as blockers.

**The CSVs are structurally intact**, where an earlier text extraction of the same workbooks
was not. Contracts: 6,851 rows, every one exactly 40 columns. Trades: 2,615 rows, every one
68 columns. Encodings differ between the two files and are detected per file rather than
assumed — Excel wrote contracts as cp1252 and trades as UTF-8. That detail is not cosmetic:
reading contracts as UTF-8 raises, and reading it with `errors='replace'` would silently
mangle 32 accented surnames (Rosén, Strömgren, Räty, Moser), and those strings are the join
key to `WAR.csv`. A name that fails to match does not error. It quietly drops a contract out
of the market sample.

**They reproduce the locked regression.** `contract_source.py` runs the production guard —
`20_CODE/skater_value_engine.py` `stage0()` — with `read_excel` redirected to the CSV, so the
real guard code path is exercised and production stays unedited.

| | from the CSV | locked |
|---|---:|---:|
| Stage 0a UFA n / a / b | 1,618 / 0.020142 / 0.015340 | 1,616 / 0.020182 / 0.015337 |
| Stage 0a RFA n / a / b | 1,305 / 0.020131 / 0.017060 | 1,301 / 0.020162 / 0.017049 |
| Stage 0b raw n / α / β | 2,349 / 0.01844730 / 0.02021737 | 2,349 / 0.01845160 / 0.02021386 |
| D20 Tobit α / β_F / β_D_add | 0.01324290 / 0.02123747 / 0.00286762 | 0.01324782 / 0.02123229 / 0.00287028 |

Both stages PASS. The n differences of +2 and +4 are not new: the decision record already
documents a "+2/+4 note" on the skater Stage-0a sample from name-variant edge cases. The CSV
reproducing the known quirk as well as the headline coefficients is stronger evidence than
matching the coefficients alone would be.

**Ages are solved.** A birthdate table built from PuckPedia as primary and Elite Prospects as
fallback — the precedence `age_join.py` already established — gives 4,343 keys and **98.3% age
coverage of season rows, 97.7% of careers**. One key was dropped for claiming two different
birthdates. Coverage is flat across the whole panel, 97% to 100% in every season from 2007 to
2025, so the selection that made the EP-only table unusable is gone:

| season | 2007 | 2012 | 2016 | 2020 | 2023 | 2025 |
|---|---:|---:|---:|---:|---:|---:|
| EP only | 83.5% | 54.1% | 16.9% | 0.0% | 0.0% | 0.0% |
| PuckPedia + EP | 98% | 98% | 100% | 99% | 97% | 98% |

This is better than the plan assumed — it put age coverage at roughly 60% and made finishing
the EP pull a Phase 0 task. Phase 0 item 4 is closed.

## 5. Phase 1 with ages: the plan's lead candidate is losing

All four models rerun with ages available, which changes two things: A1 and A2 both get age
terms (centred at 27, plus a square), and A2 shrinks toward an **age-and-position norm**
rather than a position-only one, which is what the plan specifies. That second point matters
on its own — shrinking a 35-year-old toward the average 27-year-old builds an aging curve
into the shrinkage, in the wrong direction, before Phase 3 gets a say.

MAE of the season total, in wins, development pages 2015–2021, 6,124 rows per horizon across
1,516 careers:

| model | h0 | h1 | h2 | h3 | h4 | h5 |
|---|---:|---:|---:|---:|---:|---:|
| A0 production | 0.654 | 0.706 | 0.724 | 0.741 | 0.744 | 0.739 |
| **A1 calibrated** | 0.576 | **0.604** | **0.598** | **0.597** | **0.607** | **0.569** |
| A2 component, shrunk | **0.575** | 0.607 | 0.602 | 0.610 | 0.656 | 0.614 |
| A2-raw, no shrinkage | 0.592 | 0.623 | 0.626 | 0.622 | 0.661 | 0.592 |

**The rebuild's central claim is confirmed and is large.** A1 beats the production baseline by
11.9% at the valuation season, 17.4% at two seasons on, and 23.0% at five. Pricing and
projecting a raw trailing total is the defect, and calibrating it is worth roughly a fifth of
the forecast error at long horizons.

**The plan's Phase 1 acceptance test fails, and more clearly than before ages.** Paired,
clustered by career; positive favours A1:

| horizon | A2 vs A1 | 95% interval | verdict |
|---|---:|---|---|
| 0 | −0.16% | [−1.0%, +0.7%] | tie |
| 1 | +0.57% | [−0.2%, +1.4%] | tie |
| 2 | +0.67% | [−0.2%, +1.5%] | tie |
| 3 | +2.19% | [+1.3%, +3.0%] | A1 better |
| 4 | +8.18% | [+7.0%, +9.4%] | A1 better |
| 5 | +7.80% | [+6.2%, +9.0%] | A1 better |

Before ages, A2 won h0 outright and the long-horizon losses were confined to h4. With ages,
A2 wins nothing and loses decisively at three horizons out of six. The honest reading is that
**ages helped A1 more than they helped A2**: A1's h5 error fell from 0.595 to 0.569 while
A2's rose from 0.597 to 0.614. A plausible mechanism is redundancy — once the age-and-position
norm already carries the age pattern, adding age terms to a regression over seven shrunk
components gives the fit more ways to overfit at the horizons where the trailing signal has
decayed. That is a hypothesis this report does not test.

**The star tilt is where the two now agree.** Horizons 0 to 2, bias in wins, and as a
percentage of the tier's mean outcome:

| model | below 0 | 0 to 1 | 1 to 2 | 2 to 3 | 3+ |
|---|---:|---:|---:|---:|---:|
| A0 | −0.37 | +31% | +51% | +37% | +35% |
| A1 | −0.12 | +10% | +5% | −8% | −11% |
| A2 | −0.12 | +6% | +7% | −5% | −11% |
| A2-raw | −0.26 | −4% | −6% | −16% | −21% |

Both calibrated models cut the production chain's +35% star over-projection to −11%, and both
are inside or near the plan's 5% target in the middle tiers, which they were not before ages.
Neither reaches it at 3+. The residual is now an *under*-projection, and it is the same size
for both, so it is not an argument for either model.

**Shrinkage is still what makes the component structure work at all.** A2-raw — the same seven
component rates, same regression, no shrinkage — is worse than A1 at every horizon, by 2.8% to
9.0%. Splitting the total into components does not help on its own. The fitted reliability
constants, in games of evidence needed before a player's own rate outweighs the norm (page
2021):

| component | k | reading |
|---|---:|---|
| even-strength offence | 40 | trusted quickly |
| power play | 40 | trusted quickly |
| even-strength defence | 80 | |
| penalties drawn/taken | 80 | |
| shooting | 160 | pulled hard |
| penalty kill | 320 | pulled very hard |
| unallocated | 1280 | at the grid edge: no signal, shrunk to the norm |

The ordering matches the persistence measured independently in
`component_persistence_test.py` (shooting r = 0.35, even-strength offence r = 0.66), and the
unallocated residual pinning at the grid edge is the data saying the 2023-24 export break
carries no forecast signal.

## 6. What this means for the plan

The plan named A2 the lead candidate and set "A2 beats A1 at every horizon" as the Phase 1
gate. On the development pages, with the age panel the plan wanted and the shrinkage the plan
specified, **A2 does not clear that gate and A1 is the better model.**

That is a result, not a failure of the rebuild. The rebuild's thesis — that the defect is
pricing and projecting a raw trailing total — is confirmed at 12% to 23% of forecast error.
What is not confirmed is that the fix has to be component-wise.

Three things would settle it, in the plan's own order:

1. **Phase 3, the additive aging curve.** A2's losses are concentrated at horizons 3 to 5,
   where the age path dominates. The plan always said the anchor question is decidable only
   once aging exists. That argument is weaker now than it was before ages — both models
   already carry age terms — but the curve is still the right next test.
2. **Per-horizon reliability constants.** The constants are fitted once per page against a
   one-season-ahead criterion and then reused at every horizon. A five-season-ahead forecast
   should shrink harder than a one-season-ahead one, and A2 currently cannot express that.
   This is the most likely repair for exactly the horizons where A2 loses.
3. **Dropping the age terms from A2's regression** while keeping the age-and-position norm, to
   test the redundancy hypothesis above.

If none of those moves A2 ahead, the plan should adopt A1 and retire the component anchor —
keeping the reliability machinery, which is real, for the places it demonstrably helps.

## 7. What is not built

- **Participation is a placeholder** — everyone plays. Its cost is visible in the Brier scores
  (0.278 at h0 rising to 0.595 at h5) and it is Phase 2's job.
- **Aging is a flat carry-forward.** Phase 3.
- **The two market models are unbuilt.** They are no longer blocked: the contracts CSV is
  validated and `contract_source.load_contracts()` serves it. Decisions A and B in the plan's
  section 2 have to be made first.
- **The trades export is loaded and validated but unused.** 2,615 rows, 68 columns, including
  `trade_date`, `cap_hit`, `retained_hit` and `expiry_status`. It is the back-test's input.
- **`information_set.contracts_known_at()` still raises.** The contracts data exists now, but
  the signing-date-aware contract state builder is Phase 4 work and has not been written.
  Raising is still better than an empty frame that reads as "this player has no contract".
- **Experience is left-censored** for 30.1% of season rows — players who debuted in or before
  2007-08, the first season in the source.
- **The 2023-24 export break has not been taken back to the vendor**, and its effect on the
  published component covariance shares has not been quantified.
- **No confirmatory page has been touched.** Every number in this report is from 2015–2021.
