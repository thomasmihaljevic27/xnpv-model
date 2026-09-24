# What counts as a star: the three-win cut-off, tested

Run 2026-09-24 in `50_REBUILD/` (`run_star_definition.py` v1.0). Development pages 2015–2021 only.
An evaluation of a reporting group; no model is fitted or changed. Decision: three wins kept (see the end).

## The question

Every star result in the rebuild uses the harness's "3+" tier: a trailing total of three wins or
more, where the trailing total is the locked 60/40 blend of the two latest qualifying seasons,
falling back to the latest, then the second, then the third (`forecast_harness.subjects_at`). The
cut-off was inherited, not tested. Two things were worth knowing: whether three wins picks out the
players the forecast actually misses, and whether any conclusion depends on it.

WAR totals are already stated on an 82-game basis for the two shortened seasons (the locked D20
proration, applied in `player_season_table`), so a fixed cut-off means about the same thing on
every page. The page-relative definitions below check that rather than fix it.

## The definitions, declared before the run

Membership is fixed per player and page, from information the page could see.

| label | definition |
|---|---|
| T2.0 to T4.0 | the 60/40 trailing total at or above 2.0, 2.5, 3.0 (the current definition), 3.5, 4.0 |
| P2, P5, P10 | the top 2%, 5%, 10% of the page's subjects by that total |
| R5 | the top 5% by the 60/40 trailing rate per 82 games, among subjects whose 60/40 games are at least 40 |

What would count as "making a difference" to a candidate was also declared: the share of
career-resamples in which the candidate's squared season-WAR error on the group is below the
adopted leader's lands on the other side of 50%, or moves into or out of the decisive bands (at
least 1,950 or at most 50 of 2,000), compared with the three-win result.

## Who each definition picks

| definition | members a page | distinct players | share of them in 3+ | share of 3+ in them |
|---|---:|---:|---:|---:|
| 2.0+ | 82–93 | 230 | 33% | 100% |
| 2.5+ | 44–59 | 150 | 56% | 100% |
| **3.0+ (current)** | **27–32** | **88** | 100% | 100% |
| 3.5+ | 15–22 | 60 | 100% | 61% |
| 4.0+ | 5–14 | 33 | 100% | 33% |
| top 2% | 20–21 | 69 | 100% | 69% |
| top 5% | 48–51 | 145 | 58% | 100% |
| top 10% | 96–101 | 256 | 29% | 100% |
| top 5% by rate | 31–36 | 103 | 82% | 98% |

About 990 skaters are on each page, so three wins is roughly the **top 3%**. The page-relative
cut-offs are steady: the top 5% starts at 2.37 to 2.64 wins and the top 2% at 3.23 to 3.66. A
fixed three wins sits between them on every page. The rate-based group overlaps heavily: 98% of the
three-win players are in it, and 82% of it is three-win players.

## Where the forecast actually misses, with no cut-off

The adopted leader's miss by the page percentile of the trailing total. Rate miss is among seasons
played, per 82 games; season WAR miss is over every forecast.

| band | mean trailing total | rate, one season out | rate, three out | rate, five out | season WAR, five out | forecasts, five out |
|---|---:|---:|---:|---:|---:|---:|
| bottom half | −0.17 | +0.123 | +0.045 | −0.052 | −0.040 | 2,960 |
| 50th–75th | 0.51 | +0.117 | −0.073 | −0.187 | −0.089 | 1,484 |
| 75th–90th | 1.31 | +0.072 | −0.017 | −0.182 | −0.180 | 890 |
| 90th–95th | 2.16 | +0.171 | −0.084 | −0.216 | −0.302 | 297 |
| 95th–98th | 2.86 | −0.135 | −0.194 | −0.515 | −0.548 | 178 |
| top 2% | 4.12 | −0.285 | −0.671 | −1.037 | −0.988 | 121 |

The miss grows gradually through the 95th percentile and then steps up: five seasons out the rate
miss is −0.05 to −0.22 in the bottom 95%, −0.52 in the next 3% and −1.04 in the top 2%, and one
season out it changes sign at the same place. **The large under-forecast belongs to roughly the top
5% of skaters on a page, and is largest in the top 2%.** Three wins, about the top 3%, sits inside
that zone.

## The headline figures under every definition

| definition | rate, one out | rate, three out | rate, five out | season WAR, five out | forecasts, five out | players |
|---|---:|---:|---:|---:|---:|---:|
| 2.0+ | −0.073 | −0.272 | −0.511 | −0.530 | 520 | 230 |
| 2.5+ | −0.194 | −0.382 | −0.739 | −0.747 | 302 | 150 |
| **3.0+** | **−0.265** | **−0.632** | **−0.921** | **−0.866** | **171** | **88** |
| 3.5+ | −0.335 | −0.775 | −1.125 | −1.026 | 105 | 60 |
| 4.0+ | −0.368 | −1.026 | −1.183 | −1.058 | 56 | 33 |
| top 2% | −0.285 | −0.671 | −1.037 | −0.988 | 121 | 69 |
| top 5% | −0.195 | −0.385 | −0.731 | −0.726 | 299 | 145 |
| top 10% | −0.016 | −0.240 | −0.495 | −0.515 | 596 | 256 |
| top 5% by rate | −0.271 | −0.598 | −0.830 | −0.804 | 211 | 103 |

The size of the headline bias depends on the cut-off, steadily: a higher bar gives a larger miss on
fewer players. Its direction and its growth with the horizon do not depend on it. Picking stars by
rate instead of total gives nearly the three-win figures.

## Whether any candidate's verdict changes

Share of 2,000 career-resamples in which the candidate's squared season-WAR error on the group is
below the adopted leader's, on the same rows.

| candidate | 2.0+ | 2.5+ | 3.0+ | 3.5+ | 4.0+ | top 2% | top 5% | top 10% | top 5% rate | changes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| survivors-only curve | 1997 | 1998 | 1998 | 1981 | 1988 | 1993 | 1997 | 1994 | 1995 | none |
| no level terms, unmatched | 1971 | 1984 | 1975 | 1929 | 1946 | 1952 | 1968 | 1959 | 1976 | 3.5+, 4.0+ |
| per-season regression | 661 | 607 | 546 | 300 | 386 | 409 | 527 | 670 | 471 | none |
| no level terms, matched | 1986 | 1994 | 1993 | 1959 | 1972 | 1978 | 1989 | 1990 | 1992 | none |
| second level slope | 474 | 1410 | 1962 | 1987 | 2000 | 1991 | 1540 | 530 | 1884 | 2.0+, 2.5+, top 5%, top 10%, top 5% rate |
| multi-season level | 3 | 5 | 1 | 7 | 15 | 6 | 3 | 4 | 3 | none |
| sustained level | 0 | 0 | 0 | 6 | 0 | 3 | 1 | 0 | 1 | none |
| recency weighting | 236 | 259 | 463 | 510 | 962 | 501 | 228 | 164 | 332 | none |

- **Six of the eight are unchanged under every definition.**
- **The unmatched no-level curve** drops just under the decisive band at 3.5+ and 4.0+ (1,929 and
  1,946 against 1,950). A change of band, not of side.
- **The second level slope is the one real dependence.** Its star-group gain at three wins (1,962)
  holds at 3.5+, 4.0+ and the top 2%, weakens at the top 5% (1,540), and reverses at 2.0+ and the top
  10% (474, 530). Its hinge sits at a lagged two wins per 82, so which side of two wins a group
  mostly sits on decides whether it helps. Its three-win "gain" was a 0.004 difference in RMSE to
  begin with.
- **No adoption decision depends on the definition.** Every decision rested on pooled squared error
  and dollars, which do not use the star group, and the second level slope lost on both.

## What this settles

- **Three wins is a defensible measuring stick for this purpose.** It is about the top 3% on every
  page, inside the top-5% zone where the forecast's miss steps up, and a rate-based definition picks
  nearly the same players.
- **What depends on it is the size of the headline, not the finding.** Any reported star figure
  should say which definition it uses. For scale, the top 5% and the top 2% give five-season rate
  misses of −0.73 and −1.04, against −0.92 at three wins.

**Decision (2026-09-24): three wins is kept as the star definition**, now as a tested, reasonable
measuring stick rather than an inherited one. The results above are the record of the test; no
additional reporting convention is adopted.
- **Not tested here:** a market definition of a star (cap share or contract rank), which may be the
  right one for claims about star contracts rather than star forecasts; and anything on the
  confirmatory pages.

## Files

- `50_REBUILD/code/run_star_definition.py` v1.0 (reads the harness rows written by
  `run_star_residual.py` v1.0–v1.4)
- output (ignored): `star_definition_run_log.txt`, `star_definition.csv`
