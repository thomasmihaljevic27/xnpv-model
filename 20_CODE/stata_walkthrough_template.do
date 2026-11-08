* =====================================================================================================================
* xnpv_walkthrough.do -- every regression in the xNPV model, step by step, in Stata
*
* Built by stata_refresh.py on {{BUILT}}
* from {{VERSIONS}}
*
* HOW TO USE IT
*   1. In Stata: File > Change Working Directory..., and pick 30_OUTPUT/stata/ (the folder this file is in).
*   2. Open this file in the Do-file Editor. Run the first block (Step 0) to load every data file.
*   3. Then run one step at a time: select its lines and press Ctrl+D. Each command is followed by a comment saying
*      what Stata should print. Those figures were computed from these same CSVs, the way Stata computes them, when
*      this file was built. A difference in the last digit shown can be rounding or the optimiser (tobit, logit);
*      anything larger is a real difference.
*
* Units: every money figure is in millions of dollars at the 2025-26 cap ($95.5M). D+1 is the season after the draft.
* The guide that explains each step in hockey terms: 40_DOCS/Stata_Data_Codebook.md (same step numbers).
* These commands were written from the model's code and have not yet been run in Stata.
* =====================================================================================================================


* ---- STEP 0. Load every data file (13 CSVs), each into its own frame -------------------------------------------------
do xnpv_load.do


* =====================================================================================================================
* PART 1. DRAFT PICKS: what a pick is worth
* Outcome: career_npv_m, a drafted player's net present value to the club that drafted him, from the draft to the
* end of club control. Every regression here has one row per player and robust standard errors.
* The six players who died before reaching the NHL are left out of every fit (excluded_deceased == 1).
* =====================================================================================================================
frame change picks

* ---- STEP 1. The pick curve: career NPV on the pick's star probability, through zero -----------------------------------
* The coefficient is the star value: what a 100% chance of drafting a star would be worth.
regress career_npv_m p_star if excluded_deceased == 0, noconstant vce(robust)
* Should print: p_star {{S1_B}} (robust s.e. {{S1_SE}}); {{S1_N}} observations; R-squared {{S1_R2}} (measured from zero)

* ---- STEP 2. The same, without the 2015 and 2016 drafts (the sensitivity) --------------------------------------------
regress career_npv_m p_star if excluded_deceased == 0 & !inlist(draft_year, 2015, 2016), noconstant vce(robust)
* Should print: p_star {{S2_B}} (robust s.e. {{S2_SE}}); {{S2_N}} observations

* ---- STEP 3. Each term the pick curve leaves out, added one at a time -------------------------------------------------
* 3a. A single intercept
regress career_npv_m p_star if excluded_deceased == 0, vce(robust)
* Should print: p_star {{S3A_B}}; _cons {{S3A_C}} ({{S3A_CP}})

* 3b. An intercept for each draft, and the test that they are all zero
regress career_npv_m p_star ibn.draft_year if excluded_deceased == 0, noconstant vce(robust)
testparm ibn.draft_year
* Should print: p_star {{S3B_B}}; the test F = {{S3B_F}}, {{S3B_P}}

* 3c. Draft position (the overall pick number) with an intercept
regress career_npv_m p_star pick if excluded_deceased == 0, vce(robust)
* Should print: p_star {{S3C_B}}; pick {{S3C_PICK}} ({{S3C_PICKP}}); _cons ({{S3C_CP}})

* 3d. Bacon's probability that the pick becomes an NHL player
regress career_npv_m p_star p_nhler if excluded_deceased == 0, noconstant vce(robust)
* Should print: p_star {{S3D_B}}; p_nhler {{S3D_N}} ({{S3D_NP}})

* ---- STEP 4. One star value for every draft? -------------------------------------------------------------------------
* A separate star value for each draft, and the test that all eleven are equal
regress career_npv_m ibn.draft_year#c.p_star if excluded_deceased == 0, noconstant vce(robust)
testparm ibn.draft_year#c.p_star, equal
* Should print: from {{S4_LO}} to {{S4_HI}}; the test F = {{S4_F}}, {{S4_P}}

* A trend across drafts (p_star_trend is p_star x (draft year - 2012)), with and without 2015 and 2016
regress career_npv_m p_star p_star_trend if excluded_deceased == 0, noconstant vce(robust)
* Should print: p_star_trend {{S4_T}} a draft ({{S4_TP}})
regress career_npv_m p_star p_star_trend if excluded_deceased == 0 & !inlist(draft_year, 2015, 2016), noconstant vce(robust)
* Should print: p_star_trend {{S4_TS}} a draft ({{S4_TSP}})

* ---- STEP 5. A separate star value for defencemen (tested, not adopted) ----------------------------------------------
* p_star_x_d_draft is p_star for a defenceman (position D in the NHL draft record), zero otherwise
regress career_npv_m p_star p_star_x_d_draft if excluded_deceased == 0, noconstant vce(robust)
lincom p_star + p_star_x_d_draft
* Should print: p_star {{S5_F}} (forwards and goaltenders); p_star_x_d_draft {{S5_DADD}} ({{S5_P}});
*               lincom {{S5_D}} (defencemen); R-squared {{S5_R2}}

* ---- STEP 6. Other shapes for the curve (compared on held-out drafts, which has no Stata command) ---------------------
regress career_npv_m pick if excluded_deceased == 0, vce(robust)
* Should print: {{S6A}}
regress career_npv_m log_pick if excluded_deceased == 0, vce(robust)
* Should print: {{S6B}}
regress career_npv_m log_pick log_pick_sq if excluded_deceased == 0, vce(robust)
* Should print: {{S6C}}
regress career_npv_m p_star p_star_sq if excluded_deceased == 0, noconstant vce(robust)
* Should print: {{S6D}}


* =====================================================================================================================
* PART 2. PROSPECTS: what a drafted player is worth in each season after the draft
* Outcome: remaining_npv_m, his net present value from that season to the end of club control.
* One regression on every season at once. "ibn.season_group#c.x" gives x a separate coefficient in each season group
* (1 = D+1, 2 = D+2, 3 = D+3, 4 = D+4, 5 = D+5 and later): one dummy per group, exactly one of them 1 on each row.
* Standard errors are clustered by player, since one player appears in several seasons.
* Variables: p_star = the star probability of his draft position; nhle82 = production, NHLe points per 82 games
* (50/30/20 over the three seasons before); nhle82_sq = its square; s_early = p_star in D+1 to D+3 only;
* age_term = nhle82 x (age - 18) in D+1 to D+4 only; prod_x_defence = nhle82 for a defenceman.
* =====================================================================================================================
frame change prospects

* ---- STEP 7. The star value in each season after the draft (Valuing Prospects, Table 1) -------------------------------
regress remaining_npv_m ibn.season_group#c.p_star if sample_star == 1, noconstant vce(cluster player_id)
* Should print: {{S7}}; {{S7_N}} observations

* ---- STEP 8. How the star value fades (Table 2): three simpler rules, each tested and rejected or not ------------------
* One value for every season
test 1.season_group#c.p_star = 2.season_group#c.p_star = 3.season_group#c.p_star = 4.season_group#c.p_star = 5.season_group#c.p_star
* Should print: F = {{S8_ONE_F}}, {{S8_ONE_P}}
* A straight-line decline: equal drops from D+1 to D+4
test (2.season_group#c.p_star - 1.season_group#c.p_star = 3.season_group#c.p_star - 2.season_group#c.p_star) ///
     (3.season_group#c.p_star - 2.season_group#c.p_star = 4.season_group#c.p_star - 3.season_group#c.p_star)
* Should print: F = {{S8_LINE_F}}, {{S8_LINE_P}}
* The same percentage decline each season: equal ratios from D+1 to D+4 (non-linear, so testnl)
testnl (_b[2.season_group#c.p_star]^2 = _b[1.season_group#c.p_star]*_b[3.season_group#c.p_star]) ///
       (_b[3.season_group#c.p_star]^2 = _b[2.season_group#c.p_star]*_b[4.season_group#c.p_star])
* Should print: F = {{S8_PCT_F}}, {{S8_PCT_P}}

* ---- STEP 9. Production (Table 3), skaters only (sample_production == 1 from here on) ---------------------------------
regress remaining_npv_m ibn.season_group#c.(p_star nhle82) if sample_production == 1, noconstant vce(cluster player_id)
testparm ibn.season_group#c.nhle82
* Should print: {{S9_LIN}} (linear production adds to draft position)

regress remaining_npv_m ibn.season_group#c.(p_star nhle82 nhle82_sq) if sample_production == 1, noconstant vce(cluster player_id)
testparm ibn.season_group#c.nhle82 ibn.season_group#c.nhle82_sq
* Should print: {{S9_PROD}} (production, linear and squared together)
testparm ibn.season_group#c.nhle82_sq
* Should print: {{S9_SQ}} (the square, given linear production)
test 4.season_group#c.p_star 5.season_group#c.p_star
* Should print: {{S9_LATE}} (draft position from D+4 on: not significant, so it is dropped there)

regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq) if sample_production == 1, noconstant vce(cluster player_id)
testparm ibn.season_group#c.nhle82
* Should print: {{S9_NOLIN}} (linear production, on draft position in D+1 to D+3 only)

* ---- STEP 10. Age (Table 5) ------------------------------------------------------------------------------------------
* flat_term = age - 18 on its own, D+1 to D+4: the same dollars for each year of age, whatever he scores
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq flat_term) if sample_production == 1, noconstant vce(cluster player_id)
testparm ibn.season_group#c.flat_term
* Should print: {{S10_FLAT}}
* age_term = production x (age - 18): each point is worth less the older he is when he scores it
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq age_term) if sample_production == 1, noconstant vce(cluster player_id)
testparm ibn.season_group#c.age_term
* Should print: {{S10_DISC}}
* both together: which one carries it
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq flat_term age_term) if sample_production == 1, noconstant vce(cluster player_id)
testparm ibn.season_group#c.flat_term
* Should print: {{S10_FGD}} (the flat amount, given the discount: not significant)
testparm ibn.season_group#c.age_term
* Should print: {{S10_DGF}} (the discount, given the flat amount: significant)
* the discount from D+5 on as well (prod_x_age_m18 is the age term in every season)
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq prod_x_age_m18) if sample_production == 1, noconstant vce(cluster player_id)
test 5.season_group#c.prod_x_age_m18
* Should print: {{S10_LATE}}

* ---- STEPS 11 and 12. Defencemen (Table 6) and the adopted model (Table 7) -------------------------------------------
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq age_term prod_x_defence) if sample_production == 1, noconstant vce(cluster player_id)
* Stata lists s_early from D+4 and age_term from D+5 as omitted: they are zero there by design, not estimated.
* Should print, by season (coefficient, clustered s.e.; S draft position, P production, P2 its square,
* PxAge production x (age - 18), PxD production for a defenceman), {{S12_N}} observations, R-squared {{S12_R2}}:
*   D+1:  {{S12_1}}
*   D+2:  {{S12_2}}
*   D+3:  {{S12_3}}
*   D+4:  {{S12_4}}
*   D+5+: {{S12_5}}
testparm ibn.season_group#c.prod_x_defence
* Should print: {{S11_DEF}} (the defenceman term, all five seasons together)
test 5.season_group#c.nhle82 5.season_group#c.nhle82_sq
* Should print: {{S11_LATEPROD}} (production from D+5 on, together)
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq age_term prod_x_defence prod_sq_x_defence) if sample_production == 1, noconstant vce(cluster player_id)
testparm ibn.season_group#c.prod_sq_x_defence
* Should print: {{S11_DQ}} (a defenceman's production squared: not significant)
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq age_term prod_x_defence s_early_x_defence) if sample_production == 1, noconstant vce(cluster player_id)
testparm ibn.season_group#c.s_early_x_defence
* Should print: {{S11_DS}} (a defenceman's draft position: not significant)

* ---- STEP 13. Why linear production stays: its test depends on where age is measured from -------------------------------
* The three regressions give the same fitted values; only the test of linear production moves.
foreach v in age_term age_term_19 age_term_20 {
    quietly regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq `v' prod_x_defence) if sample_production == 1, noconstant vce(cluster player_id)
    testparm ibn.season_group#c.nhle82
}
* Should print, age measured from 18, 19 and 20: {{S13_18}}; {{S13_19}}; {{S13_20}}


* =====================================================================================================================
* PART 3. PLAYERS: what clubs pay for forecast performance, and how the forecast is built
* =====================================================================================================================
frame change skater_lines

* ---- STEP 14. The skater price line ---------------------------------------------------------------------------------
* Cap hit (cap_m) on forecast WAR at the signing (xwar), a defenceman's extra per win, and years of term. It is a
* tobit, censored below at the league minimum (min_m): a contract at the minimum says only that his market price was
* at or below it.
tobit cap_m xwar c.xwar#c.is_d term_years, ll(min_m)
* Should print: xwar {{S14_W}} ({{S14_WSE}}); c.xwar#c.is_d {{S14_D}} ({{S14_DSE}}); term_years {{S14_T}} ({{S14_TSE}});
*               _cons {{S14_C}} ({{S14_CSE}}); sigma {{S14_SIG}}; log likelihood {{S14_LL}};
*               {{S14_N}} observations, {{S14_CENS}} left-censored
* The same with standard errors clustered by player (the document's table):
tobit cap_m xwar c.xwar#c.is_d term_years, ll(min_m) vce(cluster player_num)
* Should print: s.e. xwar {{S14_WCSE}}; c.xwar#c.is_d {{S14_DCSE}}; term_years {{S14_TCSE}}; _cons {{S14_CCSE}}

* ---- STEP 15. The price line built up: wins, then the defence slope, then term --------------------------------------
quietly tobit cap_m xwar, ll(min_m)
estimates store wins
quietly tobit cap_m xwar c.xwar#c.is_d, ll(min_m)
estimates store defence
quietly tobit cap_m xwar c.xwar#c.is_d term_years, ll(min_m)
estimates store adopted
lrtest wins defence
* Should print: LR chi2(1) = {{S15_DEF_LR}}, {{S15_DEF_P}}
lrtest defence adopted
* Should print: LR chi2(1) = {{S15_TERM_LR}}, {{S15_TERM_P}}
* (log likelihoods: wins {{S15_LLW}}, + defence {{S15_LLWD}}, + term {{S14_LL}})
* The line without term is the term-free line, the sensitivity: xwar {{S15_FW}}, c.xwar#c.is_d {{S15_FD}}

* ---- STEP 16. Other forms of the price line, each against the adopted one ---------------------------------------------
* A separate line for restricted free agents (intercept, both slopes and term)
quietly tobit cap_m xwar c.xwar#c.is_d term_years is_rfa c.is_rfa#c.xwar c.is_rfa#c.xwar#c.is_d c.is_rfa#c.term_years, ll(min_m)
lrtest adopted .
* Should print: LR chi2(4) = {{S16_RFA_LR}}, {{S16_RFA_P}}
* The term premium times the forecast
quietly tobit cap_m xwar c.xwar#c.is_d term_years c.term_years#c.xwar, ll(min_m)
lrtest adopted .
* Should print: LR chi2(1) = {{S16_TXW_LR}}, {{S16_TXW_P}}
* A term premium for each forecast group (below 0, 0 to 1, 1 to 2, 2 or more wins)
quietly tobit cap_m xwar c.xwar#c.is_d term_years term_x_0to1 term_x_1to2 term_x_2plus, ll(min_m)
estimates store groups
lrtest adopted groups
* Should print: LR chi2(3) = {{S16_GRP_LR}}, {{S16_GRP_P}}
* One step: a different premium below replacement level only
quietly tobit cap_m xwar c.xwar#c.is_d term_years term_x_0plus, ll(min_m)
estimates store onestep
lrtest adopted onestep
* Should print: LR chi2(1) = {{S16_STEP_LR}}, {{S16_STEP_P}}
lrtest onestep groups
* Should print: LR chi2(2) = {{S16_GVS_LR}}, {{S16_GVS_P}} (the groups add nothing to the one step)
* A squared forecast
quietly tobit cap_m xwar c.xwar#c.is_d term_years c.xwar#c.xwar, ll(min_m)
lrtest adopted .
* Should print: LR chi2(1) = {{S16_SQ_LR}}, {{S16_SQ_P}}
* A bend at one forecast win (xwar_over1 = forecast above one win, zero below)
quietly tobit cap_m xwar c.xwar#c.is_d term_years xwar_over1, ll(min_m)
lrtest adopted .
* Should print: LR chi2(1) = {{S16_BEND_LR}}, {{S16_BEND_P}}
* A separate line for contracts starting 2022-23 to 2025-26
quietly tobit cap_m xwar c.xwar#c.is_d term_years start_2022_on c.start_2022_on#c.xwar c.start_2022_on#c.xwar#c.is_d c.start_2022_on#c.term_years, ll(min_m)
lrtest adopted .
* Should print: LR chi2(4) = {{S16_LATE_LR}}, {{S16_LATE_P}}

* ---- STEP 17. Pricing on the forecast over the whole term (tested, not adopted) ---------------------------------------
* Not nested in the adopted line, so compare log likelihoods (higher fits better): adopted {{S14_LL}}
tobit cap_m xwar_term_avg c.xwar_term_avg#c.is_d term_years, ll(min_m)
* Should print: log likelihood {{S17_AVG}} (term average of WAR if he plays; xwar_term_avg {{S17_AVG_W}})
tobit cap_m xwar_term_avg_exp c.xwar_term_avg_exp#c.is_d term_years, ll(min_m)
* Should print: log likelihood {{S17_EXP}} (term average times the chance of playing; {{S17_EXP_W}})

* ---- STEP 18. The goaltender price line ------------------------------------------------------------------------------
frame change goalie_lines
tobit cap_m xwar term_years, ll(min_m)
estimates store g_adopted
* Should print: xwar {{S18_W}} ({{S18_WSE}}); term_years {{S18_T}} ({{S18_TSE}}); _cons {{S18_C}} ({{S18_CSE}});
*               log likelihood {{S18_LL}}; {{S18_N}} observations, {{S18_CENS}} left-censored
quietly tobit cap_m xwar, ll(min_m)
lrtest . g_adopted
* Should print: LR chi2(1) = {{S18_LR}}, {{S18_P}} (without term: xwar {{S18_FREE_W}}, log likelihood {{S18_FREE_LL}})

* ---- STEP 19. The skater games share, on the 2025-26 page ------------------------------------------------------------
* The model fits this on every valuation page using only seasons before it; here, the 2025-26 page (season < 2025)
* and the valuation season itself (h == 0, no seasons ahead). Least squares with a constant, clustered by player.
frame change skater_pairs
* Built up one term at a time: his trailing games share; + seasons since debut; + age and age squared; + trailing WAR
quietly regress y_gp_share tr_gp_share if h == 0 & season < 2025, vce(cluster career_num)
display e(r2)
quietly regress y_gp_share tr_gp_share exp_seasons if h == 0 & season < 2025, vce(cluster career_num)
display e(r2)
quietly regress y_gp_share tr_gp_share exp_seasons age_c age_c2 if h == 0 & season < 2025, vce(cluster career_num)
display e(r2)
regress y_gp_share tr_gp_share exp_seasons age_c age_c2 tw_war if h == 0 & season < 2025, vce(cluster career_num)
* Should print: R-squared at each step {{S19_BUILD}}; the adopted regression (the last):
*               tr_gp_share {{S19_TR_GP_SHARE}}; exp_seasons {{S19_EXP_SEASONS}}; age_c {{S19_AGE_C}};
*               age_c2 {{S19_AGE_C2}}; tw_war {{S19_TW_WAR}}; _cons {{S19__CONS}}; {{S19_N}} observations; R-squared {{S19_R2}}
* Each season ahead, 0 to 5 (Appendix A):
forvalues s = 0/5 {
    regress y_gp_share tr_gp_share exp_seasons age_c age_c2 tw_war if h == `s' & season < 2025, vce(cluster career_num)
}
* Should print: R-squared by season ahead {{S19_R2_BY_H}}
* The defenceman term the model dropped, added back in each season ahead:
forvalues s = 0/5 {
    regress y_gp_share tr_gp_share exp_seasons age_c age_c2 tw_war is_d if h == `s' & season < 2025, vce(cluster career_num)
}
* Should print: is_d p by season ahead {{S19_DEF_P}}

* ---- STEP 20. The skater chance of playing, on the 2025-26 page -------------------------------------------------------
* A logit: did he play one NHL game or more in the season (y_played)?
* Built up: age; + trailing WAR, games share and defenceman; + contract status (the adopted regression, the last)
quietly logit y_played p_age_c if h == 0 & season < 2025, vce(cluster career_num)
display e(r2_p)
quietly logit y_played p_age_c tw_war tr_gp_share is_d if h == 0 & season < 2025, vce(cluster career_num)
display e(r2_p)
logit y_played p_age_c tw_war tr_gp_share is_d under_contract contract_unknown if h == 0 & season < 2025, vce(cluster career_num)
* Should print: pseudo R-squared at each step {{S20_BUILD}}; the adopted regression (the last):
*               p_age_c {{S20_P_AGE_C}}; tw_war {{S20_TW_WAR}}; tr_gp_share {{S20_TR_GP_SHARE}}; is_d {{S20_IS_D}};
*               under_contract {{S20_UNDER_CONTRACT}}; contract_unknown {{S20_CONTRACT_UNKNOWN}}; _cons {{S20__CONS}};
*               {{S20_N}} observations; pseudo R-squared {{S20_PR2}}
* Each season ahead, 0 to 5 (Appendix A):
forvalues s = 0/5 {
    logit y_played p_age_c tw_war tr_gp_share is_d under_contract contract_unknown if h == `s' & season < 2025, vce(cluster career_num)
}
* Should print: pseudo R-squared by season ahead {{S20_PR2_BY_H}}
* The two terms the model dropped, age squared and seasons since debut, added back in each season ahead:
forvalues s = 0/5 {
    logit y_played p_age_c tw_war tr_gp_share is_d under_contract contract_unknown p_age_c2 exp_seasons if h == `s' & season < 2025, vce(cluster career_num)
}
* Should print: p_age_c2 p by season ahead {{S20_SQ_P}}; exp_seasons p {{S20_EXP_P}}
* (The model's own logit is very lightly penalised, so its coefficients differ from Stata's by at most 0.0002;
* forecast_fits.csv, in the "fits" frame, lists the model's coefficients for every page.)

* ---- STEP 21. The goaltender age term, on the 2025-26 page -----------------------------------------------------------
* What the track-record forecast misses (WAR less the pulled trailing value), on age
frame change goalie_age
regress war_less_pulled age_c if season < 2025
* Should print: age_c {{S21_B}} WAR a year (s.e. {{S21_SE}}, {{S21_P}}); {{S21_N}} observations

* ---- STEP 22. The goaltender chance of playing, on the 2025-26 page ---------------------------------------------------
frame change goalie_play
logit played age_c pulled gp_share_last if h == 0 & season < 2025
* Should print: age_c {{S22_AGE_C}}; pulled {{S22_PULLED}}; gp_share_last {{S22_GP_SHARE_LAST}}; _cons {{S22__CONS}};
*               {{S22_N}} observations
* Age squared, tested and dropped, in each season ahead the model fits ({{S22_H}}):
forvalues s = 0/{{S22_HMAX}} {
    logit played age_c pulled gp_share_last age_c2 if h == `s' & season < 2025
}
* Should print: age_c2 p by season ahead {{S22_SQ_P}} (the model fits only the seasons ahead with 200+ rows)


* =====================================================================================================================
* PART 4. THE BACK-TEST: do the forecast's verdicts on trades come true?
* forecast_net_m: what the club received less what it gave up, on the forecast at the trade. outcome_net_m: the same
* on what happened (realised through 2025-26, the rest revalued at 2026-27). The tests use the trades where every
* asset has an outcome (complete == 1). The rules and groups: 40_DOCS/Backtest_Protocol.md.
* =====================================================================================================================
frame change sides

* ---- STEP 23. Test A: the outcome on the forecast, through zero (1 = the forecast's gaps come true) -------------------
regress outcome_net_m forecast_net_m if complete == 1, noconstant
* Should print: forecast_net_m {{S23_W_SLOPE}}; {{S23_N}}
correlate forecast_net_m outcome_net_m if complete == 1
* Should print: {{S23_W_R}}
mean ahead if complete == 1 & favoured == 1
* Should print: {{S23_W_AHEAD}} (the share of trades whose favoured club came out ahead; 0.5 would be a coin)

* ---- STEP 24. Test A's sensitivities ---------------------------------------------------------------------------------
regress realised_net_m forecast_net_m if complete == 1, noconstant
* Should print: {{S24_REAL}} (realised seasons only, nothing revalued)
regress outcome_net_m forecast_net_m if complete == 1 & has_conditional_pick == 0, noconstant
* Should print: {{S24_NOCOND}} (trades with a conditional pick left out)

* ---- STEP 25. Test A by timing ---------------------------------------------------------------------------------------
regress outcome_net_m forecast_net_m if complete == 1 & during_regular_season == 1, noconstant
* Should print: {{S25_IN}} (in-season trades)
regress outcome_net_m forecast_net_m if complete == 1 & during_regular_season == 0, noconstant
* Should print: {{S25_OFF}} (off-season trades)

* ---- STEP 26. Test B: outcome less forecast, per asset, by class -----------------------------------------------------
frame change assets
mean miss_m if complete_trade == 1, over(asset_class)
* Should print: {{S26}}

* ---- STEP 27. Test C: the protocol's groups (each club side's mean forecast, outcome, and outcome less forecast) ------
frame change sides
mean forecast_net_m outcome_net_m miss_m if complete == 1 & g_futures == 1
* Should print: {{S27_C1}} (C1: received picks and prospects for players)
mean forecast_net_m outcome_net_m miss_m if complete == 1 & g_buyer == 1
* Should print: {{S27_C2}} (C2: higher in the standings, in-season two-team trades)
mean forecast_net_m outcome_net_m miss_m if complete == 1 & g_retained == 1
* Should print: {{S27_C4}} (C4: retained salary)
mean forecast_net_m outcome_net_m miss_m if complete == 1 & g_nothing_back == 1
* Should print: {{S27_C5}} (C5: received nothing recorded)
mean forecast_net_m outcome_net_m miss_m if complete == 1 & g_clause == 1
* Should print: {{S27_C6}} (C6: received a player with a no-trade or no-move clause)

* ---- STEP 28. Test A on Game Value instead of WAR (the check that the outcome does not just repeat the forecast) -------
regress outcome_net_m_gv_adj forecast_net_m if complete == 1, noconstant
correlate forecast_net_m outcome_net_m_gv_adj if complete == 1
mean ahead_gv_adj if complete == 1 & favoured == 1
* Should print: slope {{S23_GA_SLOPE}}; correlation {{S23_GA_R}}; share ahead {{S23_GA_AHEAD}} (Game Value, adjusted)
regress outcome_net_m_gv_raw forecast_net_m if complete == 1, noconstant
correlate forecast_net_m outcome_net_m_gv_raw if complete == 1
mean ahead_gv_raw if complete == 1 & favoured == 1
* Should print: slope {{S23_GR_SLOPE}}; correlation {{S23_GR_R}}; share ahead {{S23_GR_AHEAD}} (Game Value, raw)

* ---- STEP 29. Test A's interval, by resampling trades -----------------------------------------------------------------
* The model draws 2,000 resamples of trades (a trade's sides move together). Stata's draws differ from Python's, so
* the interval will be close to the model's, not equal.
bootstrap _b, reps(2000) seed(20261020) cluster(trade_id): regress outcome_net_m forecast_net_m if complete == 1, noconstant


* =====================================================================================================================
* PART 5. GAME VALUE: does it track goals and wins?
* =====================================================================================================================
* ---- STEP 30. Team-games: in-play goal differential on the team's summed Game Value ------------------------------------
frame change gv_games
regress goal_diff_in_play game_value_sum
* Should print: game_value_sum {{S30_B}}; R-squared {{S30_R2}}; {{S30_N}} observations

* ---- STEP 31. Team-seasons ------------------------------------------------------------------------------------------
frame change gv_seasons
regress gv_goal_diff game_value_sum
* Should print: game_value_sum {{S31_B}}; R-squared {{S31_R2}}; {{S31_N}} observations

* ---- STEP 32. Goals per win: wins on goal differential; goals per win is one over the slope -------------------------
regress wins goal_diff_in_play
display "goals per win: " 1/_b[goal_diff_in_play]
* Should print: goal_diff_in_play {{S32_B}}; goals per win {{S32_GPW}}
levelsof season, local(ss)
foreach s of local ss {
    quietly regress wins goal_diff_in_play if season == `s'
    display "`s'  goals per win " %6.3f 1/_b[goal_diff_in_play]
}
* Should print: {{S32_BY}}
