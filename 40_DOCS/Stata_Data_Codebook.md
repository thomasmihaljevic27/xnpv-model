# The model's regressions in Stata

Build the CSVs first, from the repo root (about 3 minutes):

```
python 20_CODE/stata_refresh.py
```

Then in Stata, work from the folder the CSVs are in:

```
cd "C:\Users\thoma\Desktop\xNPV\30_OUTPUT\stata"
```

Each section starts by importing its CSV. Above each block: what it does and its equation. Each block is only Stata
commands, one per line, so it can be pasted straight into the Command window. `30_OUTPUT/stata/xnpv_walkthrough.do` has
the same commands, with the figure each one should print.

The same option words recur:

| In the command | What it means |
|---|---|
| `noconstant` | No constant (intercept): the line goes through zero, so a player with a zero input is worth zero |
| `vce(robust)` | Robust standard errors: the size of the misses may differ from player to player |
| `vce(cluster x)` | Clustered standard errors: one player's (or trade's) misses may be related across his rows |
| `if ...` | Use only the rows where the condition holds |
| `ibn.g#c.x` | A separate coefficient on x for each value of g |
| `c.x#c.z` | x times z |
| `testparm`, `test` | Test that the named coefficients are zero (or equal to each other); read the p-value |
| `tobit ..., ll(m)` | A regression where the outcome cannot go below m (the league minimum): a contract at the minimum says only that his price was at or below it |
| `logit` | A regression for a yes/no outcome: the chance of a yes |
| `estimates store n`, `lrtest` | Save a fit under a name; compare two nested fits (does the bigger one fit significantly better?) |
| `quietly` | Fit without printing the table |
| Equation | The regression written out: a, b, c ... are the coefficients Stata estimates; e is the error; `_n` means one coefficient for each season after the draft; L(x) is the logistic function 1/(1 + exp(-x)); max(league_min, ...) is the tobit's floor |

---

## Draft picks

### Load

```stata
import delimited using "draft_players.csv", clear
```

| Variable | What it is |
|---|---|
| `career_npv` | Career NPV to the club that drafted him, $M (the outcome) |
| `star_prob` | Chance a pick at his draft position becomes a star (Bacon) |
| `deceased` | 1 for the six players who died before reaching the NHL |
| `draft_year` | Draft year |
| `pick` | Overall pick number |
| `nhl_prob` | Chance a pick at his draft position becomes an NHL player (Bacon) |
| `star_prob_x_year` | star_prob x (draft year - 2012): lets the star value drift by draft |
| `star_prob_def` | star_prob if he was drafted as a defenceman, else 0 |
| `log_pick` | Log of the overall pick |
| `log_pick_sq` | log_pick squared |
| `star_prob_sq` | star_prob squared |

### 1. The pick curve

Regress career NPV on star probability, leaving out deceased players; no constant, robust standard errors. The coefficient on star_prob is the star value: what a 100% star chance is worth.

Equation: `career_npv = b*star_prob + e`

```stata
regress career_npv star_prob if deceased == 0, noconstant vce(robust)
```

### 2. Without the 2015 and 2016 drafts

The same regression, also leaving out the 2015 and 2016 drafts (the sensitivity).

Equation: `career_npv = b*star_prob + e` (drafts 2007-2017 without 2015 and 2016)

```stata
regress career_npv star_prob if deceased == 0 & !inlist(draft_year, 2015, 2016), noconstant vce(robust)
```

### 3. Each term added to the pick curve

Add a constant: regress career NPV on star probability with an intercept; robust standard errors.

Equation: `career_npv = a + b*star_prob + e`

```stata
regress career_npv star_prob if deceased == 0, vce(robust)
```

Add an intercept for each draft year: star probability plus a dummy per draft, no overall constant.

Equation: `career_npv = a_year + b*star_prob + e` (a_year: one intercept for each draft year)

```stata
regress career_npv star_prob ibn.draft_year if deceased == 0, noconstant vce(robust)
```

Test that all eleven draft intercepts are zero.

```stata
testparm ibn.draft_year
```

Add the overall pick number and a constant.

Equation: `career_npv = a + b*star_prob + c*pick + e`

```stata
regress career_npv star_prob pick if deceased == 0, vce(robust)
```

Add the chance of becoming an NHL player; no constant.

Equation: `career_npv = b*star_prob + c*nhl_prob + e`

```stata
regress career_npv star_prob nhl_prob if deceased == 0, noconstant vce(robust)
```

### 4. One star value for every draft

Regress career NPV on star probability with a separate star value for each draft year; no constant.

Equation: `career_npv = b_year*star_prob + e` (b_year: one star value for each draft year)

```stata
regress career_npv ibn.draft_year#c.star_prob if deceased == 0, noconstant vce(robust)
```

Test that the eleven star values are all equal.

```stata
testparm ibn.draft_year#c.star_prob, equal
```

Regress career NPV on star probability and its trend across draft years: does the star value drift over time?

Equation: `career_npv = b*star_prob + t*star_prob_x_year + e` (star value in draft year y = b + t*(y - 2012))

```stata
regress career_npv star_prob star_prob_x_year if deceased == 0, noconstant vce(robust)
```

The same trend, leaving out the 2015 and 2016 drafts.

Equation: `career_npv = b*star_prob + t*star_prob_x_year + e` (drafts without 2015 and 2016)

```stata
regress career_npv star_prob star_prob_x_year if deceased == 0 & !inlist(draft_year, 2015, 2016), noconstant vce(robust)
```

### 5. A star value for defencemen

Regress career NPV on star probability and on star probability for defencemen; no constant. star_prob's coefficient is forwards' and goaltenders' star value; star_prob_def's is what defencemen's differs by.

Equation: `career_npv = b*star_prob + d*star_prob_def + e` (defencemen's star value = b + d)

```stata
regress career_npv star_prob star_prob_def if deceased == 0, noconstant vce(robust)
```

Add the two coefficients: defencemen's star value.

```stata
lincom star_prob + star_prob_def
```

### 6. Other shapes

Career NPV on the overall pick number: a straight line with a constant.

Equation: `career_npv = a + b*pick + e`

```stata
regress career_npv pick if deceased == 0, vce(robust)
```

Career NPV on the log of the pick, with a constant.

Equation: `career_npv = a + b*log_pick + e`

```stata
regress career_npv log_pick if deceased == 0, vce(robust)
```

Career NPV on the log of the pick and its square, with a constant.

Equation: `career_npv = a + b*log_pick + c*log_pick_sq + e`

```stata
regress career_npv log_pick log_pick_sq if deceased == 0, vce(robust)
```

Career NPV on star probability and its square, no constant.

Equation: `career_npv = b*star_prob + c*star_prob_sq + e`

```stata
regress career_npv star_prob star_prob_sq if deceased == 0, noconstant vce(robust)
```

---

## Prospects

### Load

```stata
import delimited using "prospect_seasons.csv", clear
```

| Variable | What it is |
|---|---|
| `remaining_npv` | His NPV from this season to the end of club control, $M (the outcome) |
| `dplus` | Season after the draft: 1 = D+1, 2 = D+2, 3 = D+3, 4 = D+4, 5 = D+5 and later |
| `prospect` | 1 for a prospect-season (every position) |
| `skater_prospect` | 1 for a skater prospect-season |
| `player_id` | The player (draft year x 1000 + pick): standard errors clustered on it |
| `star_prob` | Chance a pick at his draft position becomes a star (Bacon) |
| `star_prob_d1to3` | star_prob in D+1 to D+3, 0 later |
| `nhle_pts` | Production: NHLe points per 82 games, 50/30/20 over the 3 seasons before |
| `nhle_pts_sq` | nhle_pts squared |
| `nhle_x_age18` | nhle_pts x (age - 18) in D+1 to D+4, 0 later |
| `nhle_x_age18_all` | nhle_pts x (age - 18) in every season |
| `age_minus18` | Age - 18 in D+1 to D+4, 0 later (age on its own; tested, not adopted) |
| `nhle_pts_def` | nhle_pts for a defenceman, else 0 |
| `nhle_pts_sq_def` | nhle_pts_sq for a defenceman, else 0 |
| `star_prob_d1to3_def` | star_prob_d1to3 for a defenceman, else 0 |
| `nhle_x_age19` | nhle_pts x (age - 19) in D+1 to D+4, 0 later |
| `nhle_x_age20` | nhle_pts x (age - 20) in D+1 to D+4, 0 later |

Every regression below has a separate coefficient on each term for each season after the draft (D+1, D+2, D+3, D+4,
D+5 and later), no constant, and standard errors clustered by player.

### 7. The star value in each season after the draft

Regress remaining NPV on star probability, a separate star value for each season after the draft; all prospects.

Equation: `remaining_npv = a_n*star_prob + e`

```stata
regress remaining_npv ibn.dplus#c.star_prob if prospect == 1, noconstant vce(cluster player_id)
```

### 8. How the star value fades

A test reads the most recent regression, so refit step 7 first (not printed).

Equation: `remaining_npv = a_n*star_prob + e`

```stata
quietly regress remaining_npv ibn.dplus#c.star_prob if prospect == 1, noconstant vce(cluster player_id)
```

Test that the star value is the same in all five seasons.

```stata
test 1.dplus#c.star_prob = 2.dplus#c.star_prob = 3.dplus#c.star_prob = 4.dplus#c.star_prob = 5.dplus#c.star_prob
```

Test that it falls by the same amount each season from D+1 to D+4 (a straight line).

```stata
test (2.dplus#c.star_prob - 1.dplus#c.star_prob = 3.dplus#c.star_prob - 2.dplus#c.star_prob) (3.dplus#c.star_prob - 2.dplus#c.star_prob = 4.dplus#c.star_prob - 3.dplus#c.star_prob)
```

Test that it falls by the same percentage each season from D+1 to D+4.

```stata
testnl (_b[2.dplus#c.star_prob]^2 = _b[1.dplus#c.star_prob]*_b[3.dplus#c.star_prob]) (_b[3.dplus#c.star_prob]^2 = _b[2.dplus#c.star_prob]*_b[4.dplus#c.star_prob])
```

### 9. Production

Regress remaining NPV on star probability and production; skater prospects.

Equation: `remaining_npv = a_n*star_prob + b_n*nhle_pts + e`

```stata
regress remaining_npv ibn.dplus#c.(star_prob nhle_pts) if skater_prospect == 1, noconstant vce(cluster player_id)
```

Test that production adds nothing (its five coefficients are zero).

```stata
testparm ibn.dplus#c.nhle_pts
```

Add production squared.

Equation: `remaining_npv = a_n*star_prob + b_n*nhle_pts + c_n*nhle_pts_sq + e`

```stata
regress remaining_npv ibn.dplus#c.(star_prob nhle_pts nhle_pts_sq) if skater_prospect == 1, noconstant vce(cluster player_id)
```

Test that production and its square together add nothing.

```stata
testparm ibn.dplus#c.nhle_pts ibn.dplus#c.nhle_pts_sq
```

Test that production squared adds nothing beyond linear production.

```stata
testparm ibn.dplus#c.nhle_pts_sq
```

Test that star probability adds nothing in D+4 and from D+5 on.

```stata
test 4.dplus#c.star_prob 5.dplus#c.star_prob
```

Keep star probability only in D+1 to D+3 (star_prob_d1to3), with production and its square.

Equation: `remaining_npv = a_n*star_prob_d1to3 + b_n*nhle_pts + c_n*nhle_pts_sq + e`

```stata
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq) if skater_prospect == 1, noconstant vce(cluster player_id)
```

Test that linear production adds nothing beside its square.

```stata
testparm ibn.dplus#c.nhle_pts
```

### 10. Age

Add age on its own (age - 18, D+1 to D+4) to draft position and production.

Equation: `remaining_npv = a_n*star_prob_d1to3 + b_n*nhle_pts + c_n*nhle_pts_sq + g_n*age_minus18 + e`

```stata
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq age_minus18) if skater_prospect == 1, noconstant vce(cluster player_id)
```

Test that age on its own adds nothing.

```stata
testparm ibn.dplus#c.age_minus18
```

Instead add production x (age - 18), D+1 to D+4: each point worth less the older he is when he scores it.

Equation: `remaining_npv = a_n*star_prob_d1to3 + b_n*nhle_pts + c_n*nhle_pts_sq + d_n*nhle_x_age18 + e`

```stata
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq nhle_x_age18) if skater_prospect == 1, noconstant vce(cluster player_id)
```

Test that production x age adds nothing.

```stata
testparm ibn.dplus#c.nhle_x_age18
```

Add both.

Equation: `remaining_npv = a_n*star_prob_d1to3 + b_n*nhle_pts + c_n*nhle_pts_sq + g_n*age_minus18 + d_n*nhle_x_age18 + e`

```stata
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq age_minus18 nhle_x_age18) if skater_prospect == 1, noconstant vce(cluster player_id)
```

Test age on its own, given production x age.

```stata
testparm ibn.dplus#c.age_minus18
```

Test production x age, given age on its own.

```stata
testparm ibn.dplus#c.nhle_x_age18
```

Production x (age - 18) in every season, including D+5 and later.

Equation: `remaining_npv = a_n*star_prob_d1to3 + b_n*nhle_pts + c_n*nhle_pts_sq + d_n*nhle_x_age18_all + e`

```stata
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq nhle_x_age18_all) if skater_prospect == 1, noconstant vce(cluster player_id)
```

Test that it adds nothing from D+5 on.

```stata
test 5.dplus#c.nhle_x_age18_all
```

### 11. The adopted prospect model, and the defenceman tests

The adopted model: remaining NPV on star probability (D+1 to D+3), production, its square, production x (age - 18) (D+1 to D+4) and production for defencemen; skater prospects.

Equation: `remaining_npv = a_n*star_prob_d1to3 + b_n*nhle_pts + c_n*nhle_pts_sq + d_n*nhle_x_age18 + f_n*nhle_pts_def + e` (the adopted model)

```stata
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq nhle_x_age18 nhle_pts_def) if skater_prospect == 1, noconstant vce(cluster player_id)
```

Test that the defenceman terms add nothing.

```stata
testparm ibn.dplus#c.nhle_pts_def
```

Test that production and its square add nothing from D+5 on.

```stata
test 5.dplus#c.nhle_pts 5.dplus#c.nhle_pts_sq
```

Add production squared for defencemen.

Equation: `remaining_npv = a_n*star_prob_d1to3 + b_n*nhle_pts + c_n*nhle_pts_sq + d_n*nhle_x_age18 + f_n*nhle_pts_def + q_n*nhle_pts_sq_def + e`

```stata
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq nhle_x_age18 nhle_pts_def nhle_pts_sq_def) if skater_prospect == 1, noconstant vce(cluster player_id)
```

Test that it adds nothing.

```stata
testparm ibn.dplus#c.nhle_pts_sq_def
```

Add star probability for defencemen.

Equation: `remaining_npv = a_n*star_prob_d1to3 + b_n*nhle_pts + c_n*nhle_pts_sq + d_n*nhle_x_age18 + f_n*nhle_pts_def + s_n*star_prob_d1to3_def + e`

```stata
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq nhle_x_age18 nhle_pts_def star_prob_d1to3_def) if skater_prospect == 1, noconstant vce(cluster player_id)
```

Test that it adds nothing.

```stata
testparm ibn.dplus#c.star_prob_d1to3_def
```

### 12. Linear production, with age measured from 18, 19 and 20

For age measured from 18, then 19, then 20: fit the adopted model (without printing it), then test that linear production adds nothing. The three fits give the same values; only this test changes.

Equation: `remaining_npv = a_n*star_prob_d1to3 + b_n*nhle_pts + c_n*nhle_pts_sq + d_n*nhle_pts*(age - 18, 19 or 20) + f_n*nhle_pts_def + e`

```stata
foreach v in nhle_x_age18 nhle_x_age19 nhle_x_age20 {
    quietly regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq `v' nhle_pts_def) if skater_prospect == 1, noconstant vce(cluster player_id)
    testparm ibn.dplus#c.nhle_pts
}
```

---

## Players

### Load: skater contracts

```stata
import delimited using "price_line_skaters.csv", clear
```

| Variable | What it is |
|---|---|
| `cap_hit` | Cap hit, $M at the 2025-26 cap (the outcome) |
| `league_min` | League minimum, $M at the 2025-26 cap (the tobit's lower limit) |
| `war_fcst` | Forecast WAR if he plays in the contract's first season, at the signing |
| `defence` | 1 for a defenceman |
| `term` | Years of term |
| `player_id` | The player: standard errors clustered on it |
| `rfa` | 1 for an RFA signing |
| `term_war0to1` | term if war_fcst is 0 to 1, else 0 |
| `term_war1to2` | term if war_fcst is 1 to 2, else 0 |
| `term_war2plus` | term if war_fcst is 2 or more, else 0 |
| `term_war0plus` | term if war_fcst is 0 or more, else 0 |
| `war_fcst_over1` | war_fcst above 1 (war_fcst - 1), 0 below |
| `start_2022plus` | 1 if the contract starts in 2022-23 or later |
| `war_fcst_term_avg` | Forecast WAR if he plays, averaged over the contract's term |
| `war_exp_term_avg` | war_fcst_term_avg with each season x his chance of playing |

### 13. The skater price line

Tobit of cap hit on forecast WAR, a defenceman's extra per forecast win, and years of term; floor at the league minimum.

Equation: `cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + g*term + e)` (the adopted price line)

```stata
tobit cap_hit war_fcst c.war_fcst#c.defence term, ll(league_min)
```

The same, with standard errors clustered by player.

Equation: `cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + g*term + e)`

```stata
tobit cap_hit war_fcst c.war_fcst#c.defence term, ll(league_min) vce(cluster player_id)
```

### 14. The price line built up

Cap hit on forecast WAR only; save as "wins".

Equation: `cap_hit = max(league_min, a + b*war_fcst + e)`

```stata
quietly tobit cap_hit war_fcst, ll(league_min)
estimates store wins
```

Add a defenceman's extra per win; save as "defence".

Equation: `cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + e)`

```stata
quietly tobit cap_hit war_fcst c.war_fcst#c.defence, ll(league_min)
estimates store defence
```

Add years of term (the adopted line); save as "adopted".

Equation: `cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + g*term + e)`

```stata
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term, ll(league_min)
estimates store adopted
```

Does the defence term improve on wins only?

```stata
lrtest wins defence
```

Does term improve on wins and defence?

```stata
lrtest defence adopted
```

### 15. Other forms of the price line

Each fits the adopted line plus one change, then tests whether the change improves the fit.

Fit the adopted line (not printed) and save it as "adopted": every test below compares with it.

Equation: `cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + g*term + e)`

```stata
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term, ll(league_min)
estimates store adopted
```

A separate line for RFA signings: their own intercept, price per win, defence extra and term premium.

Equation: `cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + g*term + r0*rfa + r1*rfa*war_fcst + r2*rfa*war_fcst*defence + r3*rfa*term + e)`

```stata
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term rfa c.rfa#c.war_fcst c.rfa#c.war_fcst#c.defence c.rfa#c.term, ll(league_min)
lrtest adopted .
```

A term premium that changes with the forecast (term x forecast WAR).

Equation: `cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + g*term + k*term*war_fcst + e)`

```stata
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term c.term#c.war_fcst, ll(league_min)
lrtest adopted .
```

A term premium for each forecast group (below 0, 0 to 1, 1 to 2, 2 or more wins); save as "groups".

Equation: `cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + g*term + g1*term_war0to1 + g2*term_war1to2 + g3*term_war2plus + e)`

```stata
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term term_war0to1 term_war1to2 term_war2plus, ll(league_min)
estimates store groups
lrtest adopted groups
```

One premium below replacement level (forecast under 0) and another above; save as "onestep".

Equation: `cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + g*term + g0*term_war0plus + e)`

```stata
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term term_war0plus, ll(league_min)
estimates store onestep
lrtest adopted onestep
```

Do the groups improve on the one step?

```stata
lrtest onestep groups
```

Forecast WAR squared.

Equation: `cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + g*term + q*war_fcst^2 + e)`

```stata
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term c.war_fcst#c.war_fcst, ll(league_min)
lrtest adopted .
```

A different price per win above one forecast win.

Equation: `cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + g*term + k*war_fcst_over1 + e)`

```stata
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term war_fcst_over1, ll(league_min)
lrtest adopted .
```

A separate line for contracts starting 2022-23 to 2025-26.

Equation: `cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + g*term + s0*start_2022plus + s1*start_2022plus*war_fcst + s2*start_2022plus*war_fcst*defence + s3*start_2022plus*term + e)`

```stata
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term start_2022plus c.start_2022plus#c.war_fcst c.start_2022plus#c.war_fcst#c.defence c.start_2022plus#c.term, ll(league_min)
lrtest adopted .
```

### 16. Pricing on the forecast over the whole term

Not nested in the adopted line, so compare the log likelihood each prints with the adopted line's (higher fits better).

The price line with forecast WAR averaged over the contract's term in place of the first season's.

Equation: `cap_hit = max(league_min, a + b*war_fcst_term_avg + d*war_fcst_term_avg*defence + g*term + e)`

```stata
tobit cap_hit war_fcst_term_avg c.war_fcst_term_avg#c.defence term, ll(league_min)
```

The same, with each season's forecast times his chance of playing.

Equation: `cap_hit = max(league_min, a + b*war_exp_term_avg + d*war_exp_term_avg*defence + g*term + e)`

```stata
tobit cap_hit war_exp_term_avg c.war_exp_term_avg#c.defence term, ll(league_min)
```

### Load: goaltender contracts

```stata
import delimited using "price_line_goalies.csv", clear
```

| Variable | What it is |
|---|---|
| `cap_hit` | Cap hit, $M at the 2025-26 cap (the outcome) |
| `league_min` | League minimum, $M at the 2025-26 cap (the tobit's lower limit) |
| `war_fcst` | Forecast WAR at the signing: 35% his 50/30/20 WAR, 65% league average |
| `term` | Years of term |

### 17. The goaltender price line

Tobit of goaltender cap hit on forecast WAR and years of term; floor at the league minimum. Save as "g_adopted".

Equation: `cap_hit = max(league_min, a + b*war_fcst + g*term + e)` (the adopted goaltender line)

```stata
tobit cap_hit war_fcst term, ll(league_min)
estimates store g_adopted
```

Without term (not printed).

Equation: `cap_hit = max(league_min, a + b*war_fcst + e)`

```stata
quietly tobit cap_hit war_fcst, ll(league_min)
```

Does term improve the fit?

```stata
lrtest . g_adopted
```

### Load: skater forecast

```stata
import delimited using "skater_forecast_pairs.csv", clear
```

| Variable | What it is |
|---|---|
| `seasons_ahead` | Seasons ahead of the valuation season (0 = the valuation season) |
| `season` | The season forecast; season < 2025 = the rows the 2025-26 valuation uses |
| `player_id` | The player: standard errors clustered on it |
| `gp_share` | Share of his team's games he played that season (outcome) |
| `gp_share_trail` | His share of team games, 50/30/20 over the 3 seasons before |
| `seasons_since_debut` | Seasons since his NHL debut |
| `age_minus27` | Age at the valuation season - 27.22 |
| `age_minus27_sq` | age_minus27 squared |
| `war_trail` | His WAR, 50/30/20 over the 3 seasons before |
| `defence` | 1 for a defenceman |
| `played` | 1 if he played an NHL game that season (outcome) |
| `age_minus27_season` | Age in the season forecast - 27.22 |
| `age_minus27_season_sq` | age_minus27_season squared |
| `under_contract` | 1 if a contract signed by July 1 covers that season |
| `pre_2018` | 1 for seasons before 2018-19, which the contract data cannot see |

These are fitted as the 2025-26 valuation fits them: on seasons before 2025-26 (`season < 2025`), standard errors
clustered by player. `seasons_ahead == 0` is the valuation season itself.

### 18. The games share

Games share on trailing games share; print its R-squared.

Equation: `gp_share = a + b1*gp_share_trail + e`

```stata
quietly regress gp_share gp_share_trail if seasons_ahead == 0 & season < 2025, vce(cluster player_id)
display e(r2)
```

Add seasons since debut; print R-squared.

Equation: `gp_share = a + b1*gp_share_trail + b2*seasons_since_debut + e`

```stata
quietly regress gp_share gp_share_trail seasons_since_debut if seasons_ahead == 0 & season < 2025, vce(cluster player_id)
display e(r2)
```

Add age and age squared; print R-squared.

Equation: `gp_share = a + b1*gp_share_trail + b2*seasons_since_debut + b3*age_minus27 + b4*age_minus27_sq + e`

```stata
quietly regress gp_share gp_share_trail seasons_since_debut age_minus27 age_minus27_sq if seasons_ahead == 0 & season < 2025, vce(cluster player_id)
display e(r2)
```

Add trailing WAR: the adopted games-share regression.

Equation: `gp_share = a + b1*gp_share_trail + b2*seasons_since_debut + b3*age_minus27 + b4*age_minus27_sq + b5*war_trail + e` (the adopted games share)

```stata
regress gp_share gp_share_trail seasons_since_debut age_minus27 age_minus27_sq war_trail if seasons_ahead == 0 & season < 2025, vce(cluster player_id)
```

The adopted regression for each season ahead, 0 to 5.

Equation: `gp_share = a + b1*gp_share_trail + b2*seasons_since_debut + b3*age_minus27 + b4*age_minus27_sq + b5*war_trail + e`

```stata
forvalues s = 0/5 {
    regress gp_share gp_share_trail seasons_since_debut age_minus27 age_minus27_sq war_trail if seasons_ahead == `s' & season < 2025, vce(cluster player_id)
}
```

The same with the defenceman dummy added, for each season ahead (read defence's p-value; it was dropped).

Equation: `gp_share = a + b1*gp_share_trail + b2*seasons_since_debut + b3*age_minus27 + b4*age_minus27_sq + b5*war_trail + b6*defence + e`

```stata
forvalues s = 0/5 {
    regress gp_share gp_share_trail seasons_since_debut age_minus27 age_minus27_sq war_trail defence if seasons_ahead == `s' & season < 2025, vce(cluster player_id)
}
```

### 19. The chance of playing

Logit of whether he played on his age that season; print the pseudo R-squared.

Equation: `Pr(played = 1) = L(a + c1*age_minus27_season)`

```stata
quietly logit played age_minus27_season if seasons_ahead == 0 & season < 2025, vce(cluster player_id)
display e(r2_p)
```

Add trailing WAR, trailing games share and the defenceman dummy; print the pseudo R-squared.

Equation: `Pr(played = 1) = L(a + c1*age_minus27_season + c2*war_trail + c3*gp_share_trail + c4*defence)`

```stata
quietly logit played age_minus27_season war_trail gp_share_trail defence if seasons_ahead == 0 & season < 2025, vce(cluster player_id)
display e(r2_p)
```

Add contract status: the adopted chance-of-playing regression.

Equation: `Pr(played = 1) = L(a + c1*age_minus27_season + c2*war_trail + c3*gp_share_trail + c4*defence + c5*under_contract + c6*pre_2018)` (the adopted chance of playing)

```stata
logit played age_minus27_season war_trail gp_share_trail defence under_contract pre_2018 if seasons_ahead == 0 & season < 2025, vce(cluster player_id)
```

The adopted regression for each season ahead, 0 to 5.

Equation: `Pr(played = 1) = L(a + c1*age_minus27_season + c2*war_trail + c3*gp_share_trail + c4*defence + c5*under_contract + c6*pre_2018)`

```stata
forvalues s = 0/5 {
    logit played age_minus27_season war_trail gp_share_trail defence under_contract pre_2018 if seasons_ahead == `s' & season < 2025, vce(cluster player_id)
}
```

The same with age squared and seasons since debut added, for each season ahead (read their p-values; both dropped).

Equation: `Pr(played = 1) = L(a + c1*age_minus27_season + c2*war_trail + c3*gp_share_trail + c4*defence + c5*under_contract + c6*pre_2018 + c7*age_minus27_season_sq + c8*seasons_since_debut)`

```stata
forvalues s = 0/5 {
    logit played age_minus27_season war_trail gp_share_trail defence under_contract pre_2018 age_minus27_season_sq seasons_since_debut if seasons_ahead == `s' & season < 2025, vce(cluster player_id)
}
```

### Load: goaltender age

```stata
import delimited using "goalie_age_rows.csv", clear
```

| Variable | What it is |
|---|---|
| `war_minus_fcst` | Goaltender's WAR less his track-record forecast (outcome) |
| `age_minus27` | Age - 27.22 |
| `season` | Season; season < 2025 = the rows the 2025-26 valuation uses |

### 20. The goaltender age term

Regress how far a goaltender's WAR beat his track-record forecast on his age, seasons before 2025-26, with a constant.

Equation: `war_minus_fcst = a + b*age_minus27 + e`

```stata
regress war_minus_fcst age_minus27 if season < 2025
```

### Load: goaltender chance of playing

```stata
import delimited using "goalie_play_rows.csv", clear
```

| Variable | What it is |
|---|---|
| `played` | 1 if he played an NHL game that season (outcome) |
| `seasons_ahead` | Seasons ahead of the valuation season (0 = the valuation season) |
| `season` | The season forecast; season < 2025 = the rows the 2025-26 valuation uses |
| `age_minus27_season` | Age in the season forecast - 27.22 |
| `age_minus27_season_sq` | age_minus27_season squared |
| `war_fcst` | His track-record forecast WAR |
| `gp_share_recent` | His games in the season before the valuation season / 82 |

### 21. The goaltender chance of playing

Logit of whether a goaltender played, on his age, his forecast WAR and his most recent season's games; valuation season.

Equation: `Pr(played = 1) = L(a + c1*age_minus27_season + c2*war_fcst + c3*gp_share_recent)`

```stata
logit played age_minus27_season war_fcst gp_share_recent if seasons_ahead == 0 & season < 2025
```

The same with age squared added, for each season ahead 0 to 12 (read age_minus27_season_sq's p-value; it was dropped).

Equation: `Pr(played = 1) = L(a + c1*age_minus27_season + c2*war_fcst + c3*gp_share_recent + c4*age_minus27_season_sq)`

```stata
forvalues s = 0/12 {
    logit played age_minus27_season war_fcst gp_share_recent age_minus27_season_sq if seasons_ahead == `s' & season < 2025
}
```

---

## Back-test

### Load: club sides

```stata
import delimited using "backtest_club_sides.csv", clear
```

| Variable | What it is |
|---|---|
| `net_fcst` | Forecast: what the club received less what it gave up, $M |
| `net_outcome` | Outcome on WAR: realised through 2025-26, the rest revalued, $M |
| `net_realised` | Outcome on WAR, realised seasons only, $M |
| `complete` | 1 if every asset in the trade has an outcome (the tests' sample) |
| `favoured` | 1 for the club the forecast favoured in the trade |
| `came_out_ahead` | 1 if net_outcome is above zero |
| `conditional_pick` | 1 if the trade includes a conditional pick |
| `in_season` | 1 for an in-season trade |
| `net_miss` | net_outcome - net_fcst |
| `c1_futures` | Group C1: received picks and prospects for players |
| `c2_buyer` | Group C2: higher in the standings, in-season two-team trade |
| `c4_retained` | Group C4: retained salary in the trade |
| `c5_nothing_back` | Group C5: received nothing recorded |
| `c6_clause` | Group C6: received a player with a no-trade or no-move clause |
| `net_outcome_gvadj` | Outcome on Game Value (adjusted), $M |
| `net_outcome_gvraw` | Outcome on Game Value (raw), $M |
| `came_out_ahead_gvadj` | 1 if net_outcome_gvadj is above zero |
| `came_out_ahead_gvraw` | 1 if net_outcome_gvraw is above zero |
| `trade_id` | The trade: resampled as a unit |

### 22. Test A: outcome on forecast

Regress each club's outcome on its forecast, no constant, complete trades: a slope of 1 means the forecast's gaps come true.

Equation: `net_outcome = b*net_fcst + e` (b = 1: the forecast's gaps come true)

```stata
regress net_outcome net_fcst if complete == 1, noconstant
```

The correlation between forecast and outcome.

```stata
correlate net_fcst net_outcome if complete == 1
```

The share of trades in which the club the forecast favoured came out ahead (0.5 would be a coin flip).

```stata
mean came_out_ahead if complete == 1 & favoured == 1
```

### 23. Test A: realised seasons only, and without conditional picks

The same slope with the outcome counted on realised seasons only.

Equation: `net_realised = b*net_fcst + e`

```stata
regress net_realised net_fcst if complete == 1, noconstant
```

The same slope leaving out trades with a conditional pick.

Equation: `net_outcome = b*net_fcst + e` (trades without a conditional pick)

```stata
regress net_outcome net_fcst if complete == 1 & conditional_pick == 0, noconstant
```

### 24. Test A: in-season and off-season trades

The slope for trades made during the regular season.

Equation: `net_outcome = b*net_fcst + e` (in-season trades)

```stata
regress net_outcome net_fcst if complete == 1 & in_season == 1, noconstant
```

The slope for trades made outside it.

Equation: `net_outcome = b*net_fcst + e` (off-season trades)

```stata
regress net_outcome net_fcst if complete == 1 & in_season == 0, noconstant
```

### 25. Test C: the groups

For each group, the mean forecast, mean outcome and mean miss (outcome less forecast) of its club sides. C1: clubs that received picks and prospects for players.

```stata
mean net_fcst net_outcome net_miss if complete == 1 & c1_futures == 1
```

C2: the club higher in the standings, in-season two-team trades.

```stata
mean net_fcst net_outcome net_miss if complete == 1 & c2_buyer == 1
```

C4: clubs in trades with retained salary.

```stata
mean net_fcst net_outcome net_miss if complete == 1 & c4_retained == 1
```

C5: clubs that received nothing recorded.

```stata
mean net_fcst net_outcome net_miss if complete == 1 & c5_nothing_back == 1
```

C6: clubs that received a player with a no-trade or no-move clause.

```stata
mean net_fcst net_outcome net_miss if complete == 1 & c6_clause == 1
```

### 26. Test A on Game Value

Test A's slope, correlation and share ahead with the outcome measured on Game Value (adjusted).

Equation: `net_outcome_gvadj = b*net_fcst + e`

```stata
regress net_outcome_gvadj net_fcst if complete == 1, noconstant
correlate net_fcst net_outcome_gvadj if complete == 1
mean came_out_ahead_gvadj if complete == 1 & favoured == 1
```

The same on Game Value (raw).

Equation: `net_outcome_gvraw = b*net_fcst + e`

```stata
regress net_outcome_gvraw net_fcst if complete == 1, noconstant
correlate net_fcst net_outcome_gvraw if complete == 1
mean came_out_ahead_gvraw if complete == 1 & favoured == 1
```

### 27. Test A's interval

Refit Test A's slope on 2,000 resamples of whole trades (both sides of a trade together) for its interval.

Equation: `net_outcome = b*net_fcst + e` (refitted on each resample)

```stata
bootstrap _b, reps(2000) seed(20261020) cluster(trade_id): regress net_outcome net_fcst if complete == 1, noconstant
```

### Load: traded assets

```stata
import delimited using "backtest_assets.csv", clear
```

| Variable | What it is |
|---|---|
| `miss` | The asset's outcome less its forecast, $M |
| `complete` | 1 if the asset's trade is in the tests' sample |
| `asset_class` | players, picks, prospects or retained salary |

### 28. Test B: by asset class

The mean miss (outcome less forecast) per traded asset, for each asset class.

```stata
mean miss if complete == 1, over(asset_class)
```

---

## Game Value

### Load: team-games

```stata
import delimited using "gv_team_games.csv", clear
```

| Variable | What it is |
|---|---|
| `goal_diff` | Team's goal differential in the game, shootout goal removed |
| `game_value` | Team's skaters' Game Value in the game, summed |

### 29. Goal differential on Game Value, by game

Regress each team's goal differential in a game on its skaters' summed Game Value, with a constant.

Equation: `goal_diff = a + b*game_value + e`

```stata
regress goal_diff game_value
```

### Load: team-seasons

```stata
import delimited using "gv_team_seasons.csv", clear
```

| Variable | What it is |
|---|---|
| `goal_diff_gv_games` | Goal differential in the games with Game Value |
| `game_value` | Team's skaters' Game Value over the season, summed |
| `wins` | Team wins |
| `goal_diff` | Team's goal differential, shootout goals removed |
| `season` | Season (20172018 = 2017-18) |

### 30. Goal differential on Game Value, by season

Regress each team's season goal differential on its skaters' summed Game Value, with a constant.

Equation: `goal_diff_gv_games = a + b*game_value + e`

```stata
regress goal_diff_gv_games game_value
```

### 31. Goals per win

Regress team wins on goal differential, all seasons together; goals per win is one over the slope.

Equation: `wins = a + b*goal_diff + e` (goals per win = 1/b)

```stata
regress wins goal_diff
display "goals per win: " 1/_b[goal_diff]
```

For each season: the same regression (not printed), then that season's goals per win.

Equation: `wins = a + b*goal_diff + e` (one season at a time)

```stata
levelsof season, local(ss)
foreach s of local ss {
    quietly regress wins goal_diff if season == `s'
    display "`s'  goals per win " %6.3f 1/_b[goal_diff]
}
```
