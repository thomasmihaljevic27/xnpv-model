# Valuing Draft Picks: how to reproduce each finding

> **Superseded figures, 2026-10-13 (later the same day).** Thomas adopted the arbitration cost for control
> seasons (`pick_curve.py` v1.4). The figures below are the document's, on the qualifying-offer chain without
> arbitration; a re-run now prints the adopted values as the main ones (star value 13.42, se 1.44; 11.13
> without 2015 and 2016; traded picks $298.8M) and the document's on the line "the qualifying-offer chain
> (main until 2026-10-13): 31.66 ... 27.58". The lookup's `pick`, `round`, `slot`, `player` and `regression`
> commands now read the adopted values. The document needs a new version before these figures are quoted.

For Thomas, for the 2026-10-13 meeting. Every command below was run in Windows PowerShell on the
laptop on 2026-10-13 and gave the value shown. Run them from the repo folder
(`C:\Users\Thomas\Desktop\xNPV`). They write only to `30_OUTPUT\`, which git ignores, so they change no
tracked file. Do not run `sync.ps1` in the middle of a demonstration.

## 1. Rebuild the curve from scratch (about 15 seconds)

```
python 25_TESTS/draft_window_count.py
python 20_CODE/pick_curve.py
python 20_CODE/traded_pick_values.py
```

`pick_curve.py` prints two guards first (`2322 of 2322 equal`, `2089 of 2089 equal`). If either fails, the
inputs have changed; stop and do not quote the numbers. Then it prints the star value: **31.66 (se 2.74)**,
and **27.58** without 2015 and 2016. `traded_pick_values.py` ends with **total $704.8M; sensitivity $614.0M**.

## 2. Each finding in the document

| Finding (section) | Command | Read this line | You should see |
|---|---|---|---|
| Stars produce most of the surplus (2) | `python 25_TESTS/pick_lookup.py stars` | first two lines | 100 stars (5.9%) produced 72.7%; top ten 37.8% of picks, 80.3% of surplus |
| A #1 pick is worth $23.7M (2) | `python 25_TESTS/pick_lookup.py pick 1` | value | 0.7475 x 31.66 = $23.67M |
| Point's season table (Appendix B) | `python 25_TESTS/pick_lookup.py player "Brayden Point"` | the table | total surplus $42.79M |
| Averages by pick, three curves (4, Table 1, Figure 1) | values are in `30_OUTPUT\pick_summary\numbers.json` under `t1` | `curves`, `actual`, `held_out` | held-out error 5.66 / 5.37 / 5.23 |
| Actual players behind any pick (4) | `python 25_TESTS/pick_lookup.py slot 1` | last line | actual average $28.57M against the curve's $23.67M |
| The regression (4, Table 2) | `python 25_TESTS/pick_lookup.py regression` | both lines | 31.66 (2.74); with pick number -0.0018 (0.0030, p 0.554) |
| Bacon's star rates match ours (4) | `python 25_TESTS/pick_star_and_rights_checks.py` | `classes 2007-2015:` | 5.9% against Bacon's 5.3%, and the table by pick range |
| More flexible curves do no better (4, Appendix A) | `python 25_TESTS/pick_curve_shape_test.py` | `HELD-OUT MISS` table | line 5.71, log 5.38, bend 5.22, log squared 5.21, Bacon 5.22 |
| Through zero is the right form (Appendix A) | `python 25_TESTS/pick_star_form_test.py` | `REDRAWS WON`, verdict | intercept beats through-zero in 30 of 2,000; verdict origin |
| Star value differs by draft (5, Figure 2) | `python 25_TESTS/pick_lookup.py draft 2015` (any year) | first line | 2015: 56.92 (se 9.88); 2012: 9.55 |
| No trend once 2015-16 are out (5) | `python 25_TESTS/pick_lookup.py trend` | three lines | +2.08 (p 0.046); +1.46 (p 0.180); +0.84 (p 0.435) |
| Clubs pay 2-3x the qualifying-offer chain (6, Figure 3) | `python 25_TESTS/top_pick_control_look.py` (about 50 s) | the `1-10`, `11-15`, `16-32` rows | cost 8.44 against 27.04; 7.03 against 16.43; 5.88 against 12.20 |
| Arbitration alternative cuts 55% (6) | `python 25_TESTS/pick_cost_and_year_tests.py` (about 15 s) | `arbitration` row | 14.06, -55.17% |
| Slides, floor at zero (Appendix A) | same run | `slides_cba`, `no_slides`, `floor_zero` rows | -0.30%, -0.50%, +4.05% |
| Goalies (Appendix A) | `python 25_TESTS/pick_goalie_test.py` | `SCALES on all classes` | skaters 31.37, pooled 32.00, goalies alone 84.33 |
| Call-ups scaled (Appendix A) | `python 25_TESTS/pick_regression_first_look.py` | `beside it, every NHL season in full` | 1.502 against 1.684 |
| Free-agency rule against PuckPedia (Appendix A) | `python 25_TESTS/draft_window_count.py` | `difference in seasons` table, row `0.0` | 1151 (of 1,183); 29 of 217 windows in 2017 run past 2025-26 |
| Slot persistence, round average's cost (7, Figure 4) | `python 25_TESTS/pick_lookup.py persistence` | the `1 draft(s) later` block | correlation 0.44; top five $9.53M against $6.56M; 25-32 $4.35M |
| Trade-date slot accuracy (7) | open `30_OUTPUT\traded_pick_values_log.txt` | `PROJECTED AGAINST ACTUAL SLOT` | 97 of 156 within 3 slots |

Two notes on these runs:
- `top_pick_control_look.py` ends with a refit on actual cap hits that prints negative values. That line
  is not meaningful. Actual cap hits average in free-agent years and differ on entry-level bonuses, which
  is why the document keeps the qualifying-offer chain (Section 6).
- The cost-variant, goalie and shape tests ran on skaters with the first look's pricing (slides modelled).
  That is why their main star value is 31.37, not the adopted 31.66 (all positions, no slides).

## 3. Questions the document does not answer directly

| Question | Command |
|---|---|
| What is pick #N worth? | `python 25_TESTS/pick_lookup.py pick 16` |
| What is an average 2nd-round pick worth? | `python 25_TESTS/pick_lookup.py round 2` (add `--teams 31` for 2017-2020 drafts) |
| Who was taken at pick N, and what did each return? | `python 25_TESTS/pick_lookup.py slot 10` |
| What did a specific player deliver? | `python 25_TESTS/pick_lookup.py player "McDavid"` (any part of the name) |
| What did one draft produce? | `python 25_TESTS/pick_lookup.py draft 2012` |
| What picks did a team trade, and their values? | `python 25_TESTS/pick_lookup.py team TOR` (original team's code) |
| What picks moved on a given day? | `python 25_TESTS/pick_lookup.py date 2019-06-22` |
| Which version of each output am I reading? | `python 25_TESTS/pick_lookup.py versions` |

## 4. Files to have open

- The document: `40_DOCS\Supervisor_Drafts\Valuing Draft Picks.docx`
- The figures, full size: `30_OUTPUT\pick_summary\f1_shape.png`, `f2_star_value_by_draft.png`,
  `f3_control_cost.png`, `f4_slot_persistence.png`
- Every number in the document's figures and tables: `30_OUTPUT\pick_summary\numbers.json`
- Every drafted player and his surplus: `30_OUTPUT\pick_curve_players.csv` (opens in Excel); season by season:
  `30_OUTPUT\pick_curve_seasons.csv`
- Every traded pick and how it was valued: `30_OUTPUT\traded_pick_values.csv`

## 5. Not for the meeting

- Redrawing the figures needs matplotlib, which is not installed in your main Python. The PNGs above are
  current. Installing it (`python -m pip install matplotlib`) and running
  `python 25_TESTS/pick_summary_figures.py` would redraw them, but it is not needed.
- `25_TESTS/pick_lookahead_check.py` tests the trade-season scale, which was retired on 2026-10-09 in favour of
  one star value. Its figures are not the model's.
