# 02. Prospect Model, Sequenced

Generated 2026-07-29. **Rewritten 2026-09-28** against the current tree and that day's data
work. Position in the overall order: second of the three structural documents.

## Why this pillar goes second

It is the last unbuilt pillar and the largest remaining structural risk: the thesis claims
three asset classes price onto one currency, and only two do so far. It unblocks the
repeat-sales pick discount (01, step 5) and makes the power-analysis re-run meaningful. It goes
after the draft model because it borrows the draft slot as its prior and the same split into
hit chance times conditional value.

## Design constraint, read before anything else

**Apply the market rate; do not fit against it.** Estimate everything in wins or probabilities
(scoring conversions, transition probabilities, how fast the draft prior fades) and convert to
dollars only at the last step. Then a later change to the price per win is a re-point, not a
refit. If a design choice cannot be made without a dollar figure inside the fit, stop and
flag it: it changes the order of all three documents.

## Who has to be priced (counted 2026-09-28)

From the May 2026 trade export, checked against contract signing dates:
- **73 traded rows (70 trades) were unsigned prospects on the trade date:** 36 never appear in
  the contract export, 37 signed later. 72 of the 73 carry an Elite Prospects id.
- **224 more rows were signed players with zero NHL games.** They reach the player chain with
  no NHL record to anchor on. Whether the prospect model should price them too is a decision
  for when this is built. The rebuild's worst-predicted group, players 20 and under, points
  the same way.
- Goaltender rookies (routed here by D19) and the 83 never-played goalie rows priced at the
  league average (see STANDING_FLAGS).

---

## Step 1. The Elite Prospects pull: widened, ready to run (2026-09-28)

`ep_extract.py` v3.0. Run `python 20_CODE/ep_extract.py` on the machine with the PuckPedia
export. Plan on 10-14 hours; every pull is cached, so it can stop and restart.

- **Leagues: 12 to 34** (D32). The rule: the league has factors in `nhle_temporal.csv` and
  is a regular route to the draft or the NHL at 16-22. Added: the Russian, Swedish, Finnish,
  Czech and Slovak second tiers and junior leagues, the Swiss League, the ICE league, the US
  national development program, Canadian junior A (BCHL, AJHL, OJHL, CCHL, SJHL), the NAHL,
  Minnesota high school and prep schools, and the ECHL. Every added league was checked to load
  on Elite Prospects on 2026-09-28. **Coverage measured:** the NHL's draft record gives each
  draftee's draft-season league, and the 34 leagues cover it for 3,912 of the 4,098 players
  drafted 2007-2025 (95.5%, a floor; some unmapped labels are covered). The rest is a long tail
  (Russia's third tier 12, Ontario high school 11, the defunct EJHL 10, Swiss juniors 9).
- **Seasons: from 2006-07** (was 2010-11). The fade rate has to be fitted on finished careers,
  the 2007-2017 classes the curve uses, and their draft seasons start in 2006-07. The scoring
  conversion table starts there too.
- **The "slug crosswalk" is verified.** It was never a separate file: it is the league list in
  `ep_extract.py`, and every slug matches a league name in `nhle_temporal.csv` exactly.
- **New: a draft pass** reads one Elite Prospects page per NHL Entry Draft into
  `ep_draft_selections`. Run on 2026-09-28: 4,765 picks, the same count as the NHL record in
  every year, all but 3 with an EP id (the other 5 slots are forfeits on both sides).
- **Bios** now cover every drafted player as well as every trade asset, so the id bridge can
  check birthdates.

## Step 2. Connect Elite Prospects ids to NHL ids (proposal, tested 2026-09-28)

Elite Prospects pages carry no NHL id (checked on a full player-page payload). The bridge,
`ep_nhl_bridge.py` v1.0, uses two sources and no name matching:
1. **The draft slot.** Each pick is one player, so draft year plus overall pick is a key both
   the Elite Prospects draft pages and the NHL record carry. It covers every drafted player,
   signed or not.
2. **PuckPedia.** The contract export carries both ids for every contracted player (3,055
   pairs), which covers undrafted players who signed.

Names and birthdates are checks, never keys. **Result:** on the 2,233 drafted players both
sources cover, the draft-slot match agrees with PuckPedia on 2,232 (99.96%). The bridge holds
5,573 Elite Prospects ids, 5,572 of them with an NHL id (2,518 from the draft slot only, 822
from PuckPedia only, 2,232 from both). Two exceptions, both caught, neither resolved silently:
- **Nick Henry** (2017, 94th): PuckPedia's NHL id and birthdate disagree with the NHL's own
  draft record. PuckPedia looks wrong. The row is marked as a conflict and no id is chosen.
- **Tyler Vesel** has two Elite Prospects profiles, one linked from the draft page and one from
  PuckPedia. Merge them before reading his production.

Full names disagree on 291 draft slots and surnames on 61, all transliterations
(Kulyomin/Kulemin, Bødker/Boedker). That is why names cannot be the key.

## Step 3. Era-varying conversion factors

`nhle_temporal.csv`, 2,196 league-seasons, 142 leagues, 2006-07 to 2025-26. Use each season's
own factor, never a pooled one. **Look-ahead:** the factors are estimated on the whole panel,
so a 2019 valuation uses factors partly estimated from later seasons. Group this with the
aging-curve window and the Bacon vintage in one limitations paragraph, and consider a
split-sample stability check like the aging curve's.

## Step 4. The draft-slot prior

`draft_slot_baseline.csv`, 225 rows: the chance each pick number reaches the league and
reaches star level. A prospect with no professional record is valued at the slot's baseline;
one with a long record almost entirely on the record. The draft curve's check against these
probabilities prints r = 0.866; using them as the prior means the two pillars share an input,
so say so.

## Step 5. The fading prior

The weight moving from the slot prior to observed production as evidence builds up: the same
idea as the skater and goalie shrinkage, with a slot-specific target.
- **Evidence unit:** games is the most defensible (sample size, not calendar time).
- **Fade rate:** estimate it on held-out players, as the skater 0.55 and goalie 0.35 were. Do
  not fit it to valuations the model itself produces: that is the circularity to avoid.
- **Whether the prior fades to zero:** a tenth-overall pick with four empty professional
  seasons may not be the same asset as an undrafted player with the same record. Answer it
  empirically. The league sweep in step 1 includes undrafted players, which is what makes that
  comparison possible.

## Step 6. Convert to surplus dollars

Only here does a dollar figure enter. Mirror the draft curve's Rule A (production over the
entry-level window at the market rate, less the entry-level cost, no surplus after), with Rule
B as the robustness column. Keep it in its own module so a rate change is a re-point.

## Step 7. Absorb the populations routed here

Goaltender rookies (D19), the 83 never-played goalie rows, and the 73 unsigned traded
prospects above. Stanislav Demin (PuckPedia 17422, the 2020 Lehner three-way) is one of them.

## Step 8. Re-run the power analysis

The 2026-06-30 run (946 trade groups, 205 player-only, 14 fully priceable) measured the state
of the build, not the data. Re-run once picks and prospects are both priced. Specify the second
arm (the smallest difference in clubs' discount rates the sample could detect) before the
re-run.

---

## Answers recorded 2026-09-28

**Does the player-information call return full career league history?** The package's
`get_player_information` returns biography only. The page it reads carries the full career
table (every team, league and season, with the league slug), so it is one request away.

**Is there a downside to using the career table?** For the data itself, little: the leagues
arrive already named in the same slugs as the conversion table. Four things to handle:
1. **As-of-scrape look-ahead.** The table shows every season to date. A valuation must drop
   seasons after the trade date. A season in progress on the trade date appears as the final
   full-season total, which the model could not have known; use the season before, or split
   the season. The same issue applies to the league sweep.
2. **Revisions.** Elite Prospects corrects lines and moves players between teams after the
   fact; keep the scrape date on every row (the script already does).
3. **It only covers the players you ask for.** Pulling careers for drafted players and trade
   assets gives no undrafted comparison group. Keep the league sweep for that.
4. **It is several thousand single requests** (about 4,700 draftees plus assets), slower per
   player than a sweep but covering every league a player ever played in, with no list to keep.

A sensible split: the league sweep for the population (including undrafted players), and
career pages for the drafted players and trade assets whose route runs through a league not
on the list.

**Could Elite Prospects simplify the other data sets?** As an identity hub, yes: the draft
bridge plus PuckPedia's pairs put one EP id beside the NHL id for nearly everyone the model
touches, and EP bios carry birthdates for players the NHL record misses. That could replace the
fuzzy name passes in `age_join.py` for anyone with a bridged id. Two limits. Bacon's
`WAR.csv` has no id at all, so the join to the value data stays a name join whatever EP adds.
And Elite Prospects' NHL scoring lines are not a value source: single-provider discipline
applies, so they may be used for identity, birthdate and games-played evidence, never as
player value.

**Which goalie birthdates are missing?** Counted 2026-09-28 (the earlier "109" was the number
last seen before 2018, not the number missing a birthdate): **98 of the 280 goalies in
`Goalies_WAR.csv` have no birthdate**, because goalie ages come only from contract-export
birthdates matched by name. 93 of the 98 were last seen before 2018. Together they leave 356 of
772 goalie-seasons from 2007-08 to 2016-17 without an age, which is what blocks fitting the
goalie exit risk on seasons before each valuation. **No Elite Prospects scrape is needed:** the
NHL's stats API (`api.nhle.com/stats/rest/en/goalie/bios`, one request per season) returned a
birthdate and NHL id for 96 of the 98. The only same-name case is the two Matt Murrays, which
the join must guard. Chris Gibson and Georgi Romanov remain.

## Identification notes

- **Circularity in the fade rate:** held-out prediction, not fit to model-produced values.
- **Look-ahead:** conversion factors and slot baselines are current-vintage; the career table
  and in-progress seasons as above.
- **Selection:** who has a professional record is not random. Players who stay in junior or go
  to Europe and stop being tracked drop out in a way tied to quality. No analogue in the other
  pillars.
- **Shared input with the draft pillar:** the slot baselines feed both.
