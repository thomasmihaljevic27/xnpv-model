# xNPV Package — Run Order (Windows, `python` or `py -3.14`)

Everything from the D20/D21 build **plus** the new year-by-year panel, in one drop.
Drop all files into your data folder (or set `XNPV_DATA`), overwriting old versions.

## What changed since your last local run
- **D20** — COVID schedule proration (2019-20 ×82/70, 2020-21 ×82/56) at every anchor path; both rates refit on prorated inputs; goalie λ re-estimated (stays 0.65).
- **D21** — aging-curve routing re-based to age−1, closing a t0-season look-ahead leak (fixed the O'Connor #2 anomaly).
- **`goalie_value_engine.py`** — the goalie builder, rebuilt as a real file with a parity gate.
- **`contract_npv_panel.py`** — NEW. Year-by-year league panel; convergence diagnostic, **not** a back-test input.
- Housekeeping: `undiscounted_surplus`→`surplus_no_survival`; exit_hazard standalone NameError fixed; NPV top-8 header reframed.

## Files
| File | Version | Role |
|---|---|---|
| `skater_value_engine.py` | v1.1 | Layer 1 skater spine + D20 rate (raw-continuity guard inside) |
| `goalie_value_engine.py` | v1.0 NEW | Goalie spine, parity-gated, writes `goalie_value_spine_v2.csv` |
| `skater_forward_projection.py` | v1.1 | Layer 2 projection, D20 + D21 |
| `exit_hazard.py` | v1.1 | Exit-hazard table, D20 bucketing |
| `contract_npv.py` | v1.1 | Full NPV sweep → `contract_npv_spine.csv` (reads goalie v2 spine) |
| `contract_npv_panel.py` | v1.0 NEW | Year-by-year panel → `contract_npv_panel.csv` |
| `rfa_terminal_value.py` | — | **Unchanged — keep your copy** (zero-diff verified) |

Reference outputs from my run, for parity diffing: `contract_npv_spine.csv`,
`goalie_value_spine_v2.csv`, `contract_npv_panel.csv`. Re-upload `PROJECT_STATE.md` (v2.0) to the project.

## Run order — each step's guards must PASS before the next
1. `python skater_value_engine.py`
   → Stage 0a raw guard, 0b raw-continuity + D20-rate guards; writes `skater_value_spine.csv`.
2. `python goalie_value_engine.py`
   → **Stage P parity gate** (must reproduce your existing `goalie_value_spine.csv` to the cent) → rate guard → λ re-estimation → writes `goalie_value_spine_v2.csv`.
3. `python skater_forward_projection.py`
   → battery; **k=0 consistency must be $0.00**.
4. `python contract_npv.py`
   → full sweep; writes `contract_npv_spine.csv` (the back-test input).
5. `python contract_npv_panel.py`
   → writes `contract_npv_panel.csv` (the validation panel). Depends on steps 1–4 having produced clean spines on this machine.
6. *(optional report)* `python exit_hazard.py` — now runs standalone.

**No re-run needed:** `age_join.py` / `aging_curve.py` / `WAR_with_age.csv` — the curve works in per-82 units internally, untouched by proration.

## Parity check
Your step-4 `contract_npv_spine.csv` and step-5 `contract_npv_panel.csv` should match the reference copies row-for-row. If anything diverges, stop and send me the run log.

## Reading the panel (`contract_npv_panel.csv`)
- **One row per (contract, active league-year).** A contract appears on every season it's active, re-anchored each year.
- `artifact_role` = `VALIDATION_PANEL_not_backtest_input` on every row — **the firewall.** Never join this to trades to score mispricing; that's what `contract_npv_spine.csv` is for (each trade valued at its own date). Grading a past trade on a later page = look-ahead violation.
- `is_elc_season` = True flags rookie-deal valuation years. Kept in the data (cheap ELC surplus is real) but filter these out for any veteran-contract leaderboard.
- **Convergence exhibit** (the Karl slide): trace one player across years. Quinn Hughes runs 2021 −$30M → 2023 −$13M → **2025 +$3M** — the model stops seeing an overpay as the breakout enters the trailing window. Proof the framework isn't permanently broken on stars; it just can't see the future at signing.

## Two known display notes (data-correct, cosmetic only)
- Same-name players (e.g. the forward and defenseman **Elias Pettersson**) share a display name but are distinct `player_id`s — filter/group by `player_id`, not name. (You asked to leave display names as-is.)
- ELC-year rows sit atop each page's raw ranking; the `is_elc_season` flag is there to exclude them when you want a veteran-only view.
