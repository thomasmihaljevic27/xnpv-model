* =====================================================================================================================
* xnpv_walkthrough.do -- every regression in the xNPV model, step by step, in Stata
*
* Built by stata_refresh.py on {{BUILT}}
* from {{VERSIONS}}
*
* HOW TO USE IT
*   1. In Stata, change the working directory to 30_OUTPUT/stata/ (the folder this file is in): File > Change
*      Working Directory..., or cd "...\30_OUTPUT\stata".
*   2. Each part begins by importing its CSV; its variables then show in the Variables window.
*   3. Run one step at a time: select its lines and press Ctrl+D. Each command is followed by a comment saying what
*      Stata should print, computed from these same CSVs, the way Stata computes them, when this file was built. A
*      difference in the last digit shown can be rounding or the optimiser (tobit, logit); anything larger is real.
*
* Units: every money figure is in millions of dollars at the 2025-26 cap ($95.5M). D+1 is the season after the draft.
* The same commands, without the expected figures: 40_DOCS/Stata_Data_Codebook.md.
* These commands were written from the model's code and have not yet been run in Stata.
* =====================================================================================================================


* =====================================================================================================================
* PART 1. DRAFT PICKS: what a pick is worth
* Outcome: career_npv, a drafted player's net present value to the club that drafted him, from the draft to the
* end of club control. Every regression here has one row per player and robust standard errors.
* The six players who died before reaching the NHL are left out of every fit (deceased == 1).
* =====================================================================================================================
import delimited using "draft_players.csv", clear
label variable career_npv "Career NPV to the club that drafted him, \$M (the outcome)"
label variable star_prob "Chance a pick at his draft position becomes a star (Bacon)"
label variable deceased "1 for the six players who died before reaching the NHL"
label variable draft_year "Draft year"
label variable pick "Overall pick number"
label variable nhl_prob "Chance a pick at his draft position becomes an NHL player (Bacon)"
label variable star_prob_x_year "star_prob x (draft year - 2012): lets the star value drift by draft"
label variable star_prob_def "star_prob if he was drafted as a defenceman, else 0"
label variable log_pick "Log of the overall pick"
label variable log_pick_sq "log_pick squared"
label variable star_prob_sq "star_prob squared"

* ---- STEP 1. The pick curve: career NPV on the pick's star probability, through zero -----------------------------------
* The coefficient is the star value: what a 100% chance of drafting a star would be worth.
* Equation: career_npv = b*star_prob + e
regress career_npv star_prob if deceased == 0, noconstant vce(robust)
* Should print: star_prob {{S1_B}} (robust s.e. {{S1_SE}}); {{S1_N}} observations; R-squared {{S1_R2}} (measured from zero)

* ---- STEP 2. The same, without the 2015 and 2016 drafts (the sensitivity) --------------------------------------------
* Equation: career_npv = b*star_prob + e   (drafts 2007-2017 without 2015 and 2016)
regress career_npv star_prob if deceased == 0 & !inlist(draft_year, 2015, 2016), noconstant vce(robust)
* Should print: star_prob {{S2_B}} (robust s.e. {{S2_SE}}); {{S2_N}} observations

* ---- STEP 3. Each term the pick curve leaves out, added one at a time -------------------------------------------------
* 3a. A single intercept
* Equation: career_npv = a + b*star_prob + e
regress career_npv star_prob if deceased == 0, vce(robust)
* Should print: star_prob {{S3A_B}}; _cons {{S3A_C}} ({{S3A_CP}})

* 3b. An intercept for each draft, and the test that they are all zero
* Equation: career_npv = a_year + b*star_prob + e   (a_year: one intercept for each draft year)
regress career_npv star_prob ibn.draft_year if deceased == 0, noconstant vce(robust)
testparm ibn.draft_year
* Should print: star_prob {{S3B_B}}; the test F = {{S3B_F}}, {{S3B_P}}

* 3c. Draft position (the overall pick number) with an intercept
* Equation: career_npv = a + b*star_prob + c*pick + e
regress career_npv star_prob pick if deceased == 0, vce(robust)
* Should print: star_prob {{S3C_B}}; pick {{S3C_PICK}} ({{S3C_PICKP}}); _cons ({{S3C_CP}})

* 3d. Bacon's probability that the pick becomes an NHL player
* Equation: career_npv = b*star_prob + c*nhl_prob + e
regress career_npv star_prob nhl_prob if deceased == 0, noconstant vce(robust)
* Should print: star_prob {{S3D_B}}; nhl_prob {{S3D_N}} ({{S3D_NP}})

* ---- STEP 4. One star value for every draft? -------------------------------------------------------------------------
* A separate star value for each draft, and the test that all eleven are equal
* Equation: career_npv = b_year*star_prob + e   (b_year: one star value for each draft year)
regress career_npv ibn.draft_year#c.star_prob if deceased == 0, noconstant vce(robust)
testparm ibn.draft_year#c.star_prob, equal
* Should print: from {{S4_LO}} to {{S4_HI}}; the test F = {{S4_F}}, {{S4_P}}

* A trend across drafts (star_prob_x_year is star_prob x (draft year - 2012)), with and without 2015 and 2016
* Equation: career_npv = b*star_prob + t*star_prob_x_year + e   (star value in draft year y = b + t*(y - 2012))
regress career_npv star_prob star_prob_x_year if deceased == 0, noconstant vce(robust)
* Should print: star_prob_x_year {{S4_T}} a draft ({{S4_TP}})
* Equation: career_npv = b*star_prob + t*star_prob_x_year + e   (drafts without 2015 and 2016)
regress career_npv star_prob star_prob_x_year if deceased == 0 & !inlist(draft_year, 2015, 2016), noconstant vce(robust)
* Should print: star_prob_x_year {{S4_TS}} a draft ({{S4_TSP}})

* ---- STEP 5. A separate star value for defencemen (tested, not adopted) ----------------------------------------------
* star_prob_def is star_prob for a defenceman (position D in the NHL draft record), zero otherwise
* Equation: career_npv = b*star_prob + d*star_prob_def + e   (defencemen's star value = b + d)
regress career_npv star_prob star_prob_def if deceased == 0, noconstant vce(robust)
lincom star_prob + star_prob_def
* Should print: star_prob {{S5_F}} (forwards and goaltenders); star_prob_def {{S5_DADD}} ({{S5_P}});
*               lincom {{S5_D}} (defencemen); R-squared {{S5_R2}}

* ---- STEP 6. Other shapes for the curve (compared on held-out drafts, which has no Stata command) ---------------------
* Equation: career_npv = a + b*pick + e
regress career_npv pick if deceased == 0, vce(robust)
* Should print: {{S6A}}
* Equation: career_npv = a + b*log_pick + e
regress career_npv log_pick if deceased == 0, vce(robust)
* Should print: {{S6B}}
* Equation: career_npv = a + b*log_pick + c*log_pick_sq + e
regress career_npv log_pick log_pick_sq if deceased == 0, vce(robust)
* Should print: {{S6C}}
* Equation: career_npv = b*star_prob + c*star_prob_sq + e
regress career_npv star_prob star_prob_sq if deceased == 0, noconstant vce(robust)
* Should print: {{S6D}}


* =====================================================================================================================
* PART 2. PROSPECTS: what a drafted player is worth in each season after the draft
* Outcome: remaining_npv, his net present value from that season to the end of club control.
* One regression on every season at once. "ibn.dplus#c.x" gives x a separate coefficient in each season group
* (1 = D+1, 2 = D+2, 3 = D+3, 4 = D+4, 5 = D+5 and later): one dummy per group, exactly one of them 1 on each row.
* Standard errors are clustered by player, since one player appears in several seasons.
* Variables: star_prob = the star probability of his draft position; nhle_pts = production, NHLe points per 82 games
* (50/30/20 over the three seasons before); nhle_pts_sq = its square; star_prob_d1to3 = star_prob in D+1 to D+3 only;
* nhle_x_age18 = nhle_pts x (age - 18) in D+1 to D+4 only; nhle_pts_def = nhle_pts for a defenceman.
* =====================================================================================================================
import delimited using "prospect_seasons.csv", clear
label variable remaining_npv "His NPV from this season to the end of club control, \$M (the outcome)"
label variable dplus "Season after the draft: 1 = D+1, 2 = D+2, 3 = D+3, 4 = D+4, 5 = D+5 and later"
label variable prospect "1 for a prospect-season (every position)"
label variable skater_prospect "1 for a skater prospect-season"
label variable player_id "The player (draft year x 1000 + pick): standard errors clustered on it"
label variable star_prob "Chance a pick at his draft position becomes a star (Bacon)"
label variable star_prob_d1to3 "star_prob in D+1 to D+3, 0 later"
label variable nhle_pts "Production: NHLe points per 82 games, 50/30/20 over the 3 seasons before"
label variable nhle_pts_sq "nhle_pts squared"
label variable nhle_x_age18 "nhle_pts x (age - 18) in D+1 to D+4, 0 later"
label variable nhle_x_age18_all "nhle_pts x (age - 18) in every season"
label variable age_minus18 "Age - 18 in D+1 to D+4, 0 later (age on its own; tested, not adopted)"
label variable nhle_pts_def "nhle_pts for a defenceman, else 0"
label variable nhle_pts_sq_def "nhle_pts_sq for a defenceman, else 0"
label variable star_prob_d1to3_def "star_prob_d1to3 for a defenceman, else 0"
label variable nhle_x_age19 "nhle_pts x (age - 19) in D+1 to D+4, 0 later"
label variable nhle_x_age20 "nhle_pts x (age - 20) in D+1 to D+4, 0 later"

* ---- STEP 7. The star value in each season after the draft (Valuing Prospects, Table 1) -------------------------------
* Equation: remaining_npv = a_n*star_prob + e
regress remaining_npv ibn.dplus#c.star_prob if prospect == 1, noconstant vce(cluster player_id)
* Should print: {{S7}}; {{S7_N}} observations

* ---- STEP 8. How the star value fades (Table 2): three simpler rules, each tested and rejected or not ------------------
* A test reads the most recent regression, so refit step 7 first (not printed).
* Equation: remaining_npv = a_n*star_prob + e
quietly regress remaining_npv ibn.dplus#c.star_prob if prospect == 1, noconstant vce(cluster player_id)
* One value for every season
test 1.dplus#c.star_prob = 2.dplus#c.star_prob = 3.dplus#c.star_prob = 4.dplus#c.star_prob = 5.dplus#c.star_prob
* Should print: F = {{S8_ONE_F}}, {{S8_ONE_P}}
* A straight-line decline: equal drops from D+1 to D+4
test (2.dplus#c.star_prob - 1.dplus#c.star_prob = 3.dplus#c.star_prob - 2.dplus#c.star_prob) (3.dplus#c.star_prob - 2.dplus#c.star_prob = 4.dplus#c.star_prob - 3.dplus#c.star_prob)
* Should print: F = {{S8_LINE_F}}, {{S8_LINE_P}}
* The same percentage decline each season: equal ratios from D+1 to D+4 (non-linear, so testnl)
testnl (_b[2.dplus#c.star_prob]^2 = _b[1.dplus#c.star_prob]*_b[3.dplus#c.star_prob]) (_b[3.dplus#c.star_prob]^2 = _b[2.dplus#c.star_prob]*_b[4.dplus#c.star_prob])
* Should print: F = {{S8_PCT_F}}, {{S8_PCT_P}}

* ---- STEP 9. Production (Table 3), skaters only (skater_prospect == 1 from here on) ---------------------------------
* Equation: remaining_npv = a_n*star_prob + b_n*nhle_pts + e
regress remaining_npv ibn.dplus#c.(star_prob nhle_pts) if skater_prospect == 1, noconstant vce(cluster player_id)
testparm ibn.dplus#c.nhle_pts
* Should print: {{S9_LIN}} (linear production adds to draft position)

* Equation: remaining_npv = a_n*star_prob + b_n*nhle_pts + c_n*nhle_pts_sq + e
regress remaining_npv ibn.dplus#c.(star_prob nhle_pts nhle_pts_sq) if skater_prospect == 1, noconstant vce(cluster player_id)
testparm ibn.dplus#c.nhle_pts ibn.dplus#c.nhle_pts_sq
* Should print: {{S9_PROD}} (production, linear and squared together)
testparm ibn.dplus#c.nhle_pts_sq
* Should print: {{S9_SQ}} (the square, given linear production)
test 4.dplus#c.star_prob 5.dplus#c.star_prob
* Should print: {{S9_LATE}} (draft position from D+4 on: not significant, so it is dropped there)

* Equation: remaining_npv = a_n*star_prob_d1to3 + b_n*nhle_pts + c_n*nhle_pts_sq + e
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq) if skater_prospect == 1, noconstant vce(cluster player_id)
testparm ibn.dplus#c.nhle_pts
* Should print: {{S9_NOLIN}} (linear production, on draft position in D+1 to D+3 only)

* ---- STEP 10. Age (Table 5) ------------------------------------------------------------------------------------------
* age_minus18 = age - 18 on its own, D+1 to D+4: the same dollars for each year of age, whatever he scores
* Equation: remaining_npv = a_n*star_prob_d1to3 + b_n*nhle_pts + c_n*nhle_pts_sq + g_n*age_minus18 + e
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq age_minus18) if skater_prospect == 1, noconstant vce(cluster player_id)
testparm ibn.dplus#c.age_minus18
* Should print: {{S10_FLAT}}
* nhle_x_age18 = production x (age - 18): each point is worth less the older he is when he scores it
* Equation: remaining_npv = a_n*star_prob_d1to3 + b_n*nhle_pts + c_n*nhle_pts_sq + d_n*nhle_x_age18 + e
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq nhle_x_age18) if skater_prospect == 1, noconstant vce(cluster player_id)
testparm ibn.dplus#c.nhle_x_age18
* Should print: {{S10_DISC}}
* both together: which one carries it
* Equation: remaining_npv = a_n*star_prob_d1to3 + b_n*nhle_pts + c_n*nhle_pts_sq + g_n*age_minus18 + d_n*nhle_x_age18 + e
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq age_minus18 nhle_x_age18) if skater_prospect == 1, noconstant vce(cluster player_id)
testparm ibn.dplus#c.age_minus18
* Should print: {{S10_FGD}} (the flat amount, given the discount: not significant)
testparm ibn.dplus#c.nhle_x_age18
* Should print: {{S10_DGF}} (the discount, given the flat amount: significant)
* the discount from D+5 on as well (nhle_x_age18_all is the age term in every season)
* Equation: remaining_npv = a_n*star_prob_d1to3 + b_n*nhle_pts + c_n*nhle_pts_sq + d_n*nhle_x_age18_all + e
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq nhle_x_age18_all) if skater_prospect == 1, noconstant vce(cluster player_id)
test 5.dplus#c.nhle_x_age18_all
* Should print: {{S10_LATE}}

* ---- STEP 11. Defencemen (Table 6) and the adopted model (Table 7) -------------------------------------------
* Equation: remaining_npv = a_n*star_prob_d1to3 + b_n*nhle_pts + c_n*nhle_pts_sq + d_n*nhle_x_age18 + f_n*nhle_pts_def + e   (the adopted model)
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq nhle_x_age18 nhle_pts_def) if skater_prospect == 1, noconstant vce(cluster player_id)
* Stata lists star_prob_d1to3 from D+4 and nhle_x_age18 from D+5 as omitted: they are zero there by design, not estimated.
* Should print, by season (coefficient, clustered s.e.; S draft position, P production, P2 its square,
* PxAge production x (age - 18), PxD production for a defenceman), {{S12_N}} observations, R-squared {{S12_R2}}:
*   D+1:  {{S12_1}}
*   D+2:  {{S12_2}}
*   D+3:  {{S12_3}}
*   D+4:  {{S12_4}}
*   D+5+: {{S12_5}}
testparm ibn.dplus#c.nhle_pts_def
* Should print: {{S11_DEF}} (the defenceman term, all five seasons together)
test 5.dplus#c.nhle_pts 5.dplus#c.nhle_pts_sq
* Should print: {{S11_LATEPROD}} (production from D+5 on, together)
* Equation: remaining_npv = a_n*star_prob_d1to3 + b_n*nhle_pts + c_n*nhle_pts_sq + d_n*nhle_x_age18 + f_n*nhle_pts_def + q_n*nhle_pts_sq_def + e
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq nhle_x_age18 nhle_pts_def nhle_pts_sq_def) if skater_prospect == 1, noconstant vce(cluster player_id)
testparm ibn.dplus#c.nhle_pts_sq_def
* Should print: {{S11_DQ}} (a defenceman's production squared: not significant)
* Equation: remaining_npv = a_n*star_prob_d1to3 + b_n*nhle_pts + c_n*nhle_pts_sq + d_n*nhle_x_age18 + f_n*nhle_pts_def + s_n*star_prob_d1to3_def + e
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq nhle_x_age18 nhle_pts_def star_prob_d1to3_def) if skater_prospect == 1, noconstant vce(cluster player_id)
testparm ibn.dplus#c.star_prob_d1to3_def
* Should print: {{S11_DS}} (a defenceman's draft position: not significant)

* ---- STEP 12. Why linear production stays: its test depends on where age is measured from -------------------------------
* The three regressions give the same fitted values; only the test of linear production moves.
foreach v in nhle_x_age18 nhle_x_age19 nhle_x_age20 {
    * Equation: remaining_npv = a_n*star_prob_d1to3 + b_n*nhle_pts + c_n*nhle_pts_sq + d_n*nhle_pts*(age - 18, 19 or 20) + f_n*nhle_pts_def + e
    quietly regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq `v' nhle_pts_def) if skater_prospect == 1, noconstant vce(cluster player_id)
    testparm ibn.dplus#c.nhle_pts
}
* Should print, age measured from 18, 19 and 20: {{S13_18}}; {{S13_19}}; {{S13_20}}


* =====================================================================================================================
* PART 3. PLAYERS: what clubs pay for forecast performance, and how the forecast is built
* =====================================================================================================================
import delimited using "price_line_skaters.csv", clear
label variable cap_hit "Cap hit, \$M at the 2025-26 cap (the outcome)"
label variable league_min "League minimum, \$M at the 2025-26 cap (the tobit's lower limit)"
label variable war_fcst "Forecast WAR if he plays in the contract's first season, at the signing"
label variable defence "1 for a defenceman"
label variable term "Years of term"
label variable player_id "The player: standard errors clustered on it"
label variable rfa "1 for an RFA signing"
label variable term_war0to1 "term if war_fcst is 0 to 1, else 0"
label variable term_war1to2 "term if war_fcst is 1 to 2, else 0"
label variable term_war2plus "term if war_fcst is 2 or more, else 0"
label variable term_war0plus "term if war_fcst is 0 or more, else 0"
label variable war_fcst_over1 "war_fcst above 1 (war_fcst - 1), 0 below"
label variable start_2022plus "1 if the contract starts in 2022-23 or later"
label variable war_fcst_term_avg "Forecast WAR if he plays, averaged over the contract's term"
label variable war_exp_term_avg "war_fcst_term_avg with each season x his chance of playing"

* ---- STEP 13. The skater price line ---------------------------------------------------------------------------------
* Cap hit (cap_hit) on forecast WAR at the signing (war_fcst), a defenceman's extra per win, and years of term. It is a
* tobit, censored below at the league minimum (league_min): a contract at the minimum says only that his market price was
* at or below it.
* Equation: cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + g*term + e)   (the adopted price line)
tobit cap_hit war_fcst c.war_fcst#c.defence term, ll(league_min)
* Should print: war_fcst {{S14_W}} ({{S14_WSE}}); c.war_fcst#c.defence {{S14_D}} ({{S14_DSE}}); term {{S14_T}} ({{S14_TSE}});
*               _cons {{S14_C}} ({{S14_CSE}}); sigma {{S14_SIG}}; log likelihood {{S14_LL}};
*               {{S14_N}} observations, {{S14_CENS}} left-censored
* The same with standard errors clustered by player (the document's table):
* Equation: cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + g*term + e)
tobit cap_hit war_fcst c.war_fcst#c.defence term, ll(league_min) vce(cluster player_id)
* Should print: s.e. war_fcst {{S14_WCSE}}; c.war_fcst#c.defence {{S14_DCSE}}; term {{S14_TCSE}}; _cons {{S14_CCSE}}

* ---- STEP 14. The price line built up: wins, then the defence slope, then term --------------------------------------
* Equation: cap_hit = max(league_min, a + b*war_fcst + e)
quietly tobit cap_hit war_fcst, ll(league_min)
estimates store wins
* Equation: cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + e)
quietly tobit cap_hit war_fcst c.war_fcst#c.defence, ll(league_min)
estimates store defence
* Equation: cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + g*term + e)
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term, ll(league_min)
estimates store adopted
lrtest wins defence
* Should print: LR chi2(1) = {{S15_DEF_LR}}, {{S15_DEF_P}}
lrtest defence adopted
* Should print: LR chi2(1) = {{S15_TERM_LR}}, {{S15_TERM_P}}
* (log likelihoods: wins {{S15_LLW}}, + defence {{S15_LLWD}}, + term {{S14_LL}})
* The line without term is the term-free line, the sensitivity: war_fcst {{S15_FW}}, c.war_fcst#c.defence {{S15_FD}}

* ---- STEP 15. Other forms of the price line, each against the adopted one ---------------------------------------------
* Fit the adopted line (not printed) and save it as "adopted": every test below compares with it.
* Equation: cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + g*term + e)
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term, ll(league_min)
estimates store adopted
* A separate line for restricted free agents (intercept, both slopes and term)
* Equation: cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + g*term + r0*rfa + r1*rfa*war_fcst + r2*rfa*war_fcst*defence + r3*rfa*term + e)
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term rfa c.rfa#c.war_fcst c.rfa#c.war_fcst#c.defence c.rfa#c.term, ll(league_min)
lrtest adopted .
* Should print: LR chi2(4) = {{S16_RFA_LR}}, {{S16_RFA_P}}
* The term premium times the forecast
* Equation: cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + g*term + k*term*war_fcst + e)
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term c.term#c.war_fcst, ll(league_min)
lrtest adopted .
* Should print: LR chi2(1) = {{S16_TXW_LR}}, {{S16_TXW_P}}
* A term premium for each forecast group (below 0, 0 to 1, 1 to 2, 2 or more wins)
* Equation: cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + g*term + g1*term_war0to1 + g2*term_war1to2 + g3*term_war2plus + e)
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term term_war0to1 term_war1to2 term_war2plus, ll(league_min)
estimates store groups
lrtest adopted groups
* Should print: LR chi2(3) = {{S16_GRP_LR}}, {{S16_GRP_P}}
* One step: a different premium below replacement level only
* Equation: cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + g*term + g0*term_war0plus + e)
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term term_war0plus, ll(league_min)
estimates store onestep
lrtest adopted onestep
* Should print: LR chi2(1) = {{S16_STEP_LR}}, {{S16_STEP_P}}
lrtest onestep groups
* Should print: LR chi2(2) = {{S16_GVS_LR}}, {{S16_GVS_P}} (the groups add nothing to the one step)
* A squared forecast
* Equation: cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + g*term + q*war_fcst^2 + e)
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term c.war_fcst#c.war_fcst, ll(league_min)
lrtest adopted .
* Should print: LR chi2(1) = {{S16_SQ_LR}}, {{S16_SQ_P}}
* A bend at one forecast win (war_fcst_over1 = forecast above one win, zero below)
* Equation: cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + g*term + k*war_fcst_over1 + e)
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term war_fcst_over1, ll(league_min)
lrtest adopted .
* Should print: LR chi2(1) = {{S16_BEND_LR}}, {{S16_BEND_P}}
* A separate line for contracts starting 2022-23 to 2025-26
* Equation: cap_hit = max(league_min, a + b*war_fcst + d*war_fcst*defence + g*term + s0*start_2022plus + s1*start_2022plus*war_fcst + s2*start_2022plus*war_fcst*defence + s3*start_2022plus*term + e)
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term start_2022plus c.start_2022plus#c.war_fcst c.start_2022plus#c.war_fcst#c.defence c.start_2022plus#c.term, ll(league_min)
lrtest adopted .
* Should print: LR chi2(4) = {{S16_LATE_LR}}, {{S16_LATE_P}}

* ---- STEP 16. Pricing on the forecast over the whole term (tested, not adopted) ---------------------------------------
* Not nested in the adopted line, so compare log likelihoods (higher fits better): adopted {{S14_LL}}
* Equation: cap_hit = max(league_min, a + b*war_fcst_term_avg + d*war_fcst_term_avg*defence + g*term + e)
tobit cap_hit war_fcst_term_avg c.war_fcst_term_avg#c.defence term, ll(league_min)
* Should print: log likelihood {{S17_AVG}} (term average of WAR if he plays; war_fcst_term_avg {{S17_AVG_W}})
* Equation: cap_hit = max(league_min, a + b*war_exp_term_avg + d*war_exp_term_avg*defence + g*term + e)
tobit cap_hit war_exp_term_avg c.war_exp_term_avg#c.defence term, ll(league_min)
* Should print: log likelihood {{S17_EXP}} (term average times the chance of playing; {{S17_EXP_W}})

* ---- STEP 17. The goaltender price line ------------------------------------------------------------------------------
import delimited using "price_line_goalies.csv", clear
label variable cap_hit "Cap hit, \$M at the 2025-26 cap (the outcome)"
label variable league_min "League minimum, \$M at the 2025-26 cap (the tobit's lower limit)"
label variable war_fcst "Forecast WAR at the signing: 35% his 50/30/20 WAR, 65% league average"
label variable term "Years of term"
* Equation: cap_hit = max(league_min, a + b*war_fcst + g*term + e)   (the adopted goaltender line)
tobit cap_hit war_fcst term, ll(league_min)
estimates store g_adopted
* Should print: war_fcst {{S18_W}} ({{S18_WSE}}); term {{S18_T}} ({{S18_TSE}}); _cons {{S18_C}} ({{S18_CSE}});
*               log likelihood {{S18_LL}}; {{S18_N}} observations, {{S18_CENS}} left-censored
* Equation: cap_hit = max(league_min, a + b*war_fcst + e)
quietly tobit cap_hit war_fcst, ll(league_min)
lrtest . g_adopted
* Should print: LR chi2(1) = {{S18_LR}}, {{S18_P}} (without term: war_fcst {{S18_FREE_W}}, log likelihood {{S18_FREE_LL}})

* ---- STEP 18. The skater games share, on the 2025-26 page ------------------------------------------------------------
* The model fits this on every valuation page using only seasons before it; here, the 2025-26 page (season < 2025)
* and the valuation season itself (seasons_ahead == 0, no seasons ahead). Least squares with a constant, clustered by player.
import delimited using "skater_forecast_pairs.csv", clear
label variable seasons_ahead "Seasons ahead of the valuation season (0 = the valuation season)"
label variable season "The season forecast; season < 2025 = the rows the 2025-26 valuation uses"
label variable player_id "The player: standard errors clustered on it"
label variable gp_share "Share of his team's games he played that season (outcome)"
label variable gp_share_trail "His share of team games, 50/30/20 over the 3 seasons before"
label variable seasons_since_debut "Seasons since his NHL debut"
label variable age_minus27 "Age at the valuation season - 27.22"
label variable age_minus27_sq "age_minus27 squared"
label variable war_trail "His WAR, 50/30/20 over the 3 seasons before"
label variable defence "1 for a defenceman"
label variable played "1 if he played an NHL game that season (outcome)"
label variable age_minus27_season "Age in the season forecast - 27.22"
label variable age_minus27_season_sq "age_minus27_season squared"
label variable under_contract "1 if a contract signed by July 1 covers that season"
label variable pre_2018 "1 for seasons before 2018-19, which the contract data cannot see"
* Built up one term at a time: his trailing games share; + seasons since debut; + age and age squared; + trailing WAR
* Equation: gp_share = a + b1*gp_share_trail + e
quietly regress gp_share gp_share_trail if seasons_ahead == 0 & season < 2025, vce(cluster player_id)
display e(r2)
* Equation: gp_share = a + b1*gp_share_trail + b2*seasons_since_debut + e
quietly regress gp_share gp_share_trail seasons_since_debut if seasons_ahead == 0 & season < 2025, vce(cluster player_id)
display e(r2)
* Equation: gp_share = a + b1*gp_share_trail + b2*seasons_since_debut + b3*age_minus27 + b4*age_minus27_sq + e
quietly regress gp_share gp_share_trail seasons_since_debut age_minus27 age_minus27_sq if seasons_ahead == 0 & season < 2025, vce(cluster player_id)
display e(r2)
* Equation: gp_share = a + b1*gp_share_trail + b2*seasons_since_debut + b3*age_minus27 + b4*age_minus27_sq + b5*war_trail + e   (the adopted games share)
regress gp_share gp_share_trail seasons_since_debut age_minus27 age_minus27_sq war_trail if seasons_ahead == 0 & season < 2025, vce(cluster player_id)
* Should print: R-squared at each step {{S19_BUILD}}; the adopted regression (the last):
*               gp_share_trail {{S19_TR_GP_SHARE}}; seasons_since_debut {{S19_EXP_SEASONS}}; age_minus27 {{S19_AGE_C}};
*               age_minus27_sq {{S19_AGE_C2}}; war_trail {{S19_TW_WAR}}; _cons {{S19__CONS}}; {{S19_N}} observations; R-squared {{S19_R2}}
* Each season ahead, 0 to 5 (Appendix A):
forvalues s = 0/5 {
    * Equation: gp_share = a + b1*gp_share_trail + b2*seasons_since_debut + b3*age_minus27 + b4*age_minus27_sq + b5*war_trail + e
    regress gp_share gp_share_trail seasons_since_debut age_minus27 age_minus27_sq war_trail if seasons_ahead == `s' & season < 2025, vce(cluster player_id)
}
* Should print: R-squared by season ahead {{S19_R2_BY_H}}
* The defenceman term the model dropped, added back in each season ahead:
forvalues s = 0/5 {
    * Equation: gp_share = a + b1*gp_share_trail + b2*seasons_since_debut + b3*age_minus27 + b4*age_minus27_sq + b5*war_trail + b6*defence + e
    regress gp_share gp_share_trail seasons_since_debut age_minus27 age_minus27_sq war_trail defence if seasons_ahead == `s' & season < 2025, vce(cluster player_id)
}
* Should print: defence p by season ahead {{S19_DEF_P}}

* ---- STEP 19. The skater chance of playing, on the 2025-26 page -------------------------------------------------------
* A logit: did he play one NHL game or more in the season (played)?
* Built up: age; + trailing WAR, games share and defenceman; + contract status (the adopted regression, the last)
* Equation: Pr(played = 1) = L(a + c1*age_minus27_season)
quietly logit played age_minus27_season if seasons_ahead == 0 & season < 2025, vce(cluster player_id)
display e(r2_p)
* Equation: Pr(played = 1) = L(a + c1*age_minus27_season + c2*war_trail + c3*gp_share_trail + c4*defence)
quietly logit played age_minus27_season war_trail gp_share_trail defence if seasons_ahead == 0 & season < 2025, vce(cluster player_id)
display e(r2_p)
* Equation: Pr(played = 1) = L(a + c1*age_minus27_season + c2*war_trail + c3*gp_share_trail + c4*defence + c5*under_contract + c6*pre_2018)   (the adopted chance of playing)
logit played age_minus27_season war_trail gp_share_trail defence under_contract pre_2018 if seasons_ahead == 0 & season < 2025, vce(cluster player_id)
* Should print: pseudo R-squared at each step {{S20_BUILD}}; the adopted regression (the last):
*               age_minus27_season {{S20_P_AGE_C}}; war_trail {{S20_TW_WAR}}; gp_share_trail {{S20_TR_GP_SHARE}}; defence {{S20_IS_D}};
*               under_contract {{S20_UNDER_CONTRACT}}; pre_2018 {{S20_CONTRACT_UNKNOWN}}; _cons {{S20__CONS}};
*               {{S20_N}} observations; pseudo R-squared {{S20_PR2}}
* Each season ahead, 0 to 5 (Appendix A):
forvalues s = 0/5 {
    * Equation: Pr(played = 1) = L(a + c1*age_minus27_season + c2*war_trail + c3*gp_share_trail + c4*defence + c5*under_contract + c6*pre_2018)
    logit played age_minus27_season war_trail gp_share_trail defence under_contract pre_2018 if seasons_ahead == `s' & season < 2025, vce(cluster player_id)
}
* Should print: pseudo R-squared by season ahead {{S20_PR2_BY_H}}
* The two terms the model dropped, age squared and seasons since debut, added back in each season ahead:
forvalues s = 0/5 {
    * Equation: Pr(played = 1) = L(a + c1*age_minus27_season + c2*war_trail + c3*gp_share_trail + c4*defence + c5*under_contract + c6*pre_2018 + c7*age_minus27_season_sq + c8*seasons_since_debut)
    logit played age_minus27_season war_trail gp_share_trail defence under_contract pre_2018 age_minus27_season_sq seasons_since_debut if seasons_ahead == `s' & season < 2025, vce(cluster player_id)
}
* Should print: age_minus27_season_sq p by season ahead {{S20_SQ_P}}; seasons_since_debut p {{S20_EXP_P}}
* (The model's own logit is very lightly penalised, so its coefficients differ from Stata's by at most 0.0002;
* forecast_fits.csv lists the model's coefficients for every page.)

* ---- STEP 20. The goaltender age term, on the 2025-26 page -----------------------------------------------------------
* How far a goaltender's WAR beat his track-record forecast, on his age
import delimited using "goalie_age_rows.csv", clear
label variable war_minus_fcst "Goaltender's WAR less his track-record forecast (outcome)"
label variable age_minus27 "Age - 27.22"
label variable season "Season; season < 2025 = the rows the 2025-26 valuation uses"
* Equation: war_minus_fcst = a + b*age_minus27 + e
regress war_minus_fcst age_minus27 if season < 2025
* Should print: age_minus27_season {{S21_B}} WAR a year (s.e. {{S21_SE}}, {{S21_P}}); {{S21_N}} observations

* ---- STEP 21. The goaltender chance of playing, on the 2025-26 page ---------------------------------------------------
import delimited using "goalie_play_rows.csv", clear
label variable played "1 if he played an NHL game that season (outcome)"
label variable seasons_ahead "Seasons ahead of the valuation season (0 = the valuation season)"
label variable season "The season forecast; season < 2025 = the rows the 2025-26 valuation uses"
label variable age_minus27_season "Age in the season forecast - 27.22"
label variable age_minus27_season_sq "age_minus27_season squared"
label variable war_fcst "His track-record forecast WAR"
label variable gp_share_recent "His games in the season before the valuation season / 82"
* Equation: Pr(played = 1) = L(a + c1*age_minus27_season + c2*war_fcst + c3*gp_share_recent)
logit played age_minus27_season war_fcst gp_share_recent if seasons_ahead == 0 & season < 2025
* Should print: age_minus27_season {{S22_AGE_C}}; war_fcst {{S22_PULLED}}; gp_share_recent {{S22_GP_SHARE_LAST}}; _cons {{S22__CONS}};
*               {{S22_N}} observations
* Age squared, tested and dropped, in each season ahead the model fits ({{S22_H}}):
forvalues s = 0/{{S22_HMAX}} {
    * Equation: Pr(played = 1) = L(a + c1*age_minus27_season + c2*war_fcst + c3*gp_share_recent + c4*age_minus27_season_sq)
    logit played age_minus27_season war_fcst gp_share_recent age_minus27_season_sq if seasons_ahead == `s' & season < 2025
}
* Should print: age_minus27_season_sq p by season ahead {{S22_SQ_P}} (the model fits only the seasons ahead with 200+ rows)


* =====================================================================================================================
* PART 4. THE BACK-TEST: do the forecast's verdicts on trades come true?
* net_fcst: what the club received less what it gave up, on the forecast at the trade. net_outcome: the same
* on what happened (realised through 2025-26, the rest revalued at 2026-27). The tests use the trades where every
* asset has an outcome (complete == 1). The rules and groups: 40_DOCS/Backtest_Protocol.md.
* =====================================================================================================================
import delimited using "backtest_club_sides.csv", clear
label variable net_fcst "Forecast: what the club received less what it gave up, \$M"
label variable net_outcome "Outcome on WAR: realised through 2025-26, the rest revalued, \$M"
label variable net_realised "Outcome on WAR, realised seasons only, \$M"
label variable complete "1 if every asset in the trade has an outcome (the tests' sample)"
label variable favoured "1 for the club the forecast favoured in the trade"
label variable came_out_ahead "1 if net_outcome is above zero"
label variable conditional_pick "1 if the trade includes a conditional pick"
label variable in_season "1 for an in-season trade"
label variable net_miss "net_outcome - net_fcst"
label variable c1_futures "Group C1: received picks and prospects for players"
label variable c2_buyer "Group C2: higher in the standings, in-season two-team trade"
label variable c4_retained "Group C4: retained salary in the trade"
label variable c5_nothing_back "Group C5: received nothing recorded"
label variable c6_clause "Group C6: received a player with a no-trade or no-move clause"
label variable net_outcome_gvadj "Outcome on Game Value (adjusted), \$M"
label variable net_outcome_gvraw "Outcome on Game Value (raw), \$M"
label variable came_out_ahead_gvadj "1 if net_outcome_gvadj is above zero"
label variable came_out_ahead_gvraw "1 if net_outcome_gvraw is above zero"
label variable trade_id "The trade: resampled as a unit"

* ---- STEP 22. Test A: the outcome on the forecast, through zero (1 = the forecast's gaps come true) -------------------
* Equation: net_outcome = b*net_fcst + e   (b = 1: the forecast's gaps come true)
regress net_outcome net_fcst if complete == 1, noconstant
* Should print: net_fcst {{S23_W_SLOPE}}; {{S23_N}}
correlate net_fcst net_outcome if complete == 1
* Should print: {{S23_W_R}}
mean came_out_ahead if complete == 1 & favoured == 1
* Should print: {{S23_W_AHEAD}} (the share of trades whose favoured club came out ahead; 0.5 would be a coin)

* ---- STEP 23. Test A's sensitivities ---------------------------------------------------------------------------------
* Equation: net_realised = b*net_fcst + e
regress net_realised net_fcst if complete == 1, noconstant
* Should print: {{S24_REAL}} (realised seasons only, nothing revalued)
* Equation: net_outcome = b*net_fcst + e   (trades without a conditional pick)
regress net_outcome net_fcst if complete == 1 & conditional_pick == 0, noconstant
* Should print: {{S24_NOCOND}} (trades with a conditional pick left out)

* ---- STEP 24. Test A by timing ---------------------------------------------------------------------------------------
* Equation: net_outcome = b*net_fcst + e   (in-season trades)
regress net_outcome net_fcst if complete == 1 & in_season == 1, noconstant
* Should print: {{S25_IN}} (in-season trades)
* Equation: net_outcome = b*net_fcst + e   (off-season trades)
regress net_outcome net_fcst if complete == 1 & in_season == 0, noconstant
* Should print: {{S25_OFF}} (off-season trades)

* ---- STEP 25. Test C: the protocol's groups (each club side's mean forecast, outcome, and outcome less forecast) ------
mean net_fcst net_outcome net_miss if complete == 1 & c1_futures == 1
* Should print: {{S27_C1}} (C1: received picks and prospects for players)
mean net_fcst net_outcome net_miss if complete == 1 & c2_buyer == 1
* Should print: {{S27_C2}} (C2: higher in the standings, in-season two-team trades)
mean net_fcst net_outcome net_miss if complete == 1 & c4_retained == 1
* Should print: {{S27_C4}} (C4: retained salary)
mean net_fcst net_outcome net_miss if complete == 1 & c5_nothing_back == 1
* Should print: {{S27_C5}} (C5: received nothing recorded)
mean net_fcst net_outcome net_miss if complete == 1 & c6_clause == 1
* Should print: {{S27_C6}} (C6: received a player with a no-trade or no-move clause)

* ---- STEP 26. Test A on Game Value instead of WAR (the check that the outcome does not just repeat the forecast) -------
* Equation: net_outcome_gvadj = b*net_fcst + e
regress net_outcome_gvadj net_fcst if complete == 1, noconstant
correlate net_fcst net_outcome_gvadj if complete == 1
mean came_out_ahead_gvadj if complete == 1 & favoured == 1
* Should print: slope {{S23_GA_SLOPE}}; correlation {{S23_GA_R}}; share ahead {{S23_GA_AHEAD}} (Game Value, adjusted)
* Equation: net_outcome_gvraw = b*net_fcst + e
regress net_outcome_gvraw net_fcst if complete == 1, noconstant
correlate net_fcst net_outcome_gvraw if complete == 1
mean came_out_ahead_gvraw if complete == 1 & favoured == 1
* Should print: slope {{S23_GR_SLOPE}}; correlation {{S23_GR_R}}; share ahead {{S23_GR_AHEAD}} (Game Value, raw)

* ---- STEP 27. Test A's interval, by resampling trades -----------------------------------------------------------------
* The model draws 2,000 resamples of trades (a trade's sides move together). Stata's draws differ from Python's, so
* the interval will be close to the model's, not equal.
* Equation: net_outcome = b*net_fcst + e, refitted on each resample
bootstrap _b, reps(2000) seed(20261020) cluster(trade_id): regress net_outcome net_fcst if complete == 1, noconstant


* ---- STEP 28. Test B: outcome less forecast, per asset, by class -----------------------------------------------------
import delimited using "backtest_assets.csv", clear
label variable miss "The asset's outcome less its forecast, \$M"
label variable complete "1 if the asset's trade is in the tests' sample"
label variable asset_class "players, picks, prospects or retained salary"
mean miss if complete == 1, over(asset_class)
* Should print: {{S26}}


* =====================================================================================================================
* PART 5. GAME VALUE: does it track goals and wins?
* =====================================================================================================================
* ---- STEP 29. Team-games: in-play goal differential on the team's summed Game Value ------------------------------------
import delimited using "gv_team_games.csv", clear
label variable goal_diff "Team's goal differential in the game, shootout goal removed"
label variable game_value "Team's skaters' Game Value in the game, summed"
* Equation: goal_diff = a + b*game_value + e
regress goal_diff game_value
* Should print: game_value {{S30_B}}; R-squared {{S30_R2}}; {{S30_N}} observations

* ---- STEP 30. Team-seasons ------------------------------------------------------------------------------------------
import delimited using "gv_team_seasons.csv", clear
label variable goal_diff_gv_games "Goal differential in the games with Game Value"
label variable game_value "Team's skaters' Game Value over the season, summed"
label variable wins "Team wins"
label variable goal_diff "Team's goal differential, shootout goals removed"
label variable season "Season (20172018 = 2017-18)"
* Equation: goal_diff_gv_games = a + b*game_value + e
regress goal_diff_gv_games game_value
* Should print: game_value {{S31_B}}; R-squared {{S31_R2}}; {{S31_N}} observations

* ---- STEP 31. Goals per win: wins on goal differential; goals per win is one over the slope -------------------------
* Equation: wins = a + b*goal_diff + e   (goals per win = 1/b)
regress wins goal_diff
display "goals per win: " 1/_b[goal_diff]
* Should print: goal_diff {{S32_B}}; goals per win {{S32_GPW}}
levelsof season, local(ss)
foreach s of local ss {
    * Equation: wins = a + b*goal_diff + e, one season at a time
    quietly regress wins goal_diff if season == `s'
    display "`s'  goals per win " %6.3f 1/_b[goal_diff]
}
* Should print: {{S32_BY}}
