# xNPV Model

Pricing NHL trade assets on a common surplus-dollar scale.

## What this does

Most hockey asset-valuation work prices one thing at a time: a pick chart here, a player
surplus-value model there, prospects mostly by feel. Trades mix all three, so those models
cannot be compared against each other at the moment a general manager actually decides.

This project builds a net-present-value framework that puts rostered players, draft picks, and
non-roster prospects on one scale, projected surplus value in dollars, and then back-tests
historical trades against realized outcomes to identify where the market misprices
systematically. The cross-asset integration is the contribution, not any single pillar.

Written as a Master's economics thesis at Lakehead University.

## Status

Active build. No manuscript exists yet, and none is written until the model is finished.

- **Player pillar:** closed. Produces real discounted contract-level NPVs for skaters and
  goalies, reproducible across two machines.
- **Draft pillar:** yield curve closed. Pricing actual traded picks is the next step.
- **Prospect pillar:** not started. Blocked on an Elite Prospects production pull.
- **Back-test engine:** game-level model chain closed and validated. Circularity validation
  closed with three independent validators agreeing in a 0.56 to 0.61 band. Mid-season
  allocation application still open.

`00_STATE/PROJECT_STATE.md` carries the full picture. It is current to 2026-07-30 and its
refresh is the first open task in this repo.

## Structure

    00_STATE/     state anchor, sequence documents, file manifest
    10_SOURCE/    source data. Code reads it, never writes it
    20_CODE/      all scripts, flat, current version only
    30_OUTPUT/    generated spines, panels, curves, logs (not committed)
    40_DOCS/      reports, reviews, research brief
    90_ARCHIVE/   superseded material by date (not committed)

The numbered flat layout is deliberate and predates this repo. Scripts import each other as
modules and read and write outputs by hardcoded filename, so the directory names and the
filenames inside them are load-bearing. This is a documented deviation from the conventional
`src/` and `data/` layout.

## Setup

    git clone <repo-url>
    cd xnpv-model
    cp .env.example .env      # then fill in real paths
    pip install pandas numpy statsmodels scipy requests python-dotenv

Run order for each pillar is documented in `CLAUDE.md`.

## Data

Four source datasets are included for reproducibility. See `10_SOURCE/README.md` for provenance
and attribution.

Three things are not in this repo and cannot be:

- **PuckPedia contract and trades exports.** Confidential vendor data, provided under terms that
  do not permit redistribution.
- **The NHL game-log database** (2.3 GB) and its associated event CSVs. Rebuildable from
  scratch with `20_CODE/nhl_gamelog_scraper.py`, which pulls from the public NHL API.
- **Everything in `30_OUTPUT/`.** Regenerable by running the chains in order.

## Migration checklist

Carried over from the transfer into Claude Code. Not yet done:

- [ ] Extract hardcoded absolute paths from scripts into `.env` (blocking, repo is public)
- [ ] Scrub any personal email from scraper user-agent strings (blocking)
- [ ] Refresh `PROJECT_STATE.md`, stale since 2026-07-30
- [ ] Regenerate downstream spines after the 2026-07-28 rebuild
- [ ] Resolve `uncertainty_correction.py` against `uncertainty_correction_v2.py`, the version
      suffix breaks the naming rule and one of them belongs in `90_ARCHIVE/`
- [ ] Confirm a license, or state deliberately that none is offered

## License

None yet. See the checklist above. Until one is added, default copyright applies and no
reuse rights are granted.
