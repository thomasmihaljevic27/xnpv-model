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

## 4. First look at Phase 1: the plan's acceptance test is not met yet

Three candidates, same rows, same information sets, same placeholder participation (everyone
plays — deliberately identical across candidates so it cancels from the comparison and its
cost shows up honestly as a Brier score).

- **A0** production 60/40, flat carry.
- **A1** the mandatory benchmark: the blend pulled back toward the league by a fitted
  coefficient, with position, a one-season flag and experience, plus availability forecast
  from its own trailing share instead of assumed full.
- **A2** the lead candidate: each of the seven components shrunk toward its positional norm
  by its own fitted reliability constant, then regressed with component-specific
  coefficients.

MAE of the season total, in wins, and bias:

| model | h0 | h1 | h2 | h3 | h4 | h5 |
|---|---:|---:|---:|---:|---:|---:|
| A0 | 0.654 | 0.706 | 0.724 | 0.741 | 0.744 | 0.739 |
| A1 | 0.577 | 0.603 | 0.604 | 0.603 | 0.621 | 0.595 |
| A2 | **0.572** | 0.607 | 0.609 | 0.613 | 0.660 | 0.597 |

**A1 and A2 both beat the production baseline decisively and by a lot** — 12% at the
valuation season, 17% at two seasons on, 20% at five. That is the rebuild's central claim
holding up: pricing and projecting a raw trailing total is the defect.

**A2 does not beat A1 at every horizon, which is what the plan's Phase 1 acceptance
requires.** Paired, clustered by career:

| horizon | A2 vs A1 | 95% interval | verdict |
|---|---:|---|---|
| 0 | −0.96% | [−1.7%, −0.2%] | A2 better, interval excludes zero |
| 1 | +0.63% | [−0.2%, +1.4%] | tie |
| 2 | +0.87% | [+0.2%, +1.7%] | A1 better, marginally |
| 3 | +1.60% | [+0.8%, +2.5%] | A1 better |
| 4 | +6.30% | [+5.3%, +7.3%] | A1 better, clearly |
| 5 | +0.38% | [−0.7%, +1.4%] | tie |

A2 wins where the forecast is closest to the evidence and loses as the horizon lengthens.
That pattern is what a missing aging curve looks like: at four seasons out, most of what
separates a good forecast from a bad one is the age path, which neither model has yet, and
A2 spends more parameters on a signal that has decayed. The plan puts the additive aging
curve in Phase 3 for this reason, and the honest reading is that **the A1-versus-A2 question
is not yet decidable** — not that A1 has won.

Two results do favour A2 and are worth keeping:

**The star tilt, horizons 0 to 2.** A2 has the smallest residual tilt at every tier above
replacement and the lowest MAE at 3+ (1.408, against A1's 1.444 and A0's 1.678).

| model | below 0 | 0 to 1 | 1 to 2 | 2 to 3 | 3+ |
|---|---:|---:|---:|---:|---:|
| A0 | −0.37 | +31% | +51% | +37% | +35% |
| A1 | −0.16 | −11% | −9% | −17% | −19% |
| A2 | −0.17 | −12% | −6% | −14% | **−17%** |

The plan asks for every tier within 5%. No candidate is there. Every one of these residual
tilts is *negative* — the calibrated models now under-project, where the production chain
over-projected — and the under-projection is concentrated in the same tiers and grows with
the horizon, which again points at the missing aging curve rather than at the anchor.

**The shrinkage is what makes the component structure work.** A diagnostic variant, A2-raw,
feeds the same seven component rates to the same regression with no shrinkage, and it is
*worse than A1 at every horizon* (by 1.1% to 8.1%). Splitting the total into components does
not help on its own — a per-82 component rate is a far noisier regressor than a trailing
total, and seven of them are seven times as noisy. Shrinking each by its own fitted
reliability recovers all of that and more at short horizons. The argument for the component
structure is that it is the only structure that can express "a forty-game season is the same
number believed half as much"; it is not the headline margin, which is small.

The fitted constants, in games of evidence needed before a player's own rate outweighs the
norm (page 2021):

| component | k | reading |
|---|---:|---|
| even-strength offence | 40 | trusted quickly |
| even-strength defence | 40 | trusted quickly |
| power play | 40 | trusted quickly |
| penalties drawn/taken | 80 | |
| shooting | 160 | pulled hard — two full seasons to half-trust |
| penalty kill | 320 | pulled very hard |
| unallocated | 1280 | at the grid edge: no signal, shrunk to the norm |

These are fitted per page on the rolling window, never carried across pages, and the ordering
matches the persistence measured independently in `component_persistence_test.py` (shooting
r = 0.35, even-strength offence r = 0.66).

## 5. What is not settled, and what is not built

- **A1 versus A2 is open.** It is decidable only once the aging curve exists. Running it
  again after Phase 3 is the plan's own sequence, not a concession.
- **Ages are missing entirely.** 0% coverage in this checkout, because birthdates come from
  the confidential PuckPedia export. The positional norm A2 shrinks toward is therefore
  position-only rather than the age-and-position norm the plan specifies, and no age band
  appears in any table above. Finishing the Elite Prospects pull is Phase 0 item 4 and is
  still open.
- **Participation is a placeholder** — everyone plays. Its cost is visible in the Brier
  scores (0.278 at h0 rising to 0.595 at h5) and it is Phase 2's job.
- **Aging is a flat carry-forward.** Phase 3.
- **Both market models are unbuilt** and blocked on contract data. Phase 4.
- **Experience is left-censored** for 30.1% of season rows — players who debuted in or
  before 2007-08, the first season in the source. The flag travels with the number and the
  models use it, but the censoring is real and is a limitation of any experience term.
- **The 2023-24 export break has not been taken back to the vendor**, and its effect on the
  published component covariance shares has not been quantified.
