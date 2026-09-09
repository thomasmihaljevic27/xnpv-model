# Repository review and proposed edits to Circularity and Game Value

Reviewed 9 September 2026 against GitHub main at `cd23309a40ebc16debcac96de9f7d26efa9f6e6a`.

The project has a clear research contribution and a substantial working player model. Its strongest feature is the record of decisions, rejected approaches, and reproduction checks. The main weakness is that the explanations sometimes make stronger claims than the implementation supports. A completed diagnostic becomes “circularity resolved,” a stable historical relationship becomes “no look-ahead,” and related versions of one metric become “three independent validators.” Those changes in wording matter for the thesis.

This review covers the repository inventory, all five current explainers, the state and decision records, the eight GitHub pull requests, and the implementing code for the principal valuation and Game Value mechanisms. All 37 tracked Python scripts were parsed and their imports inventoried. The numerical findings below come from source inspection, recorded results, or explicitly labelled small diagnostic examples. This was not a full pipeline rerun, an audit of each vendor observation, or a fresh review of the superseded historical PDFs.

The local Doc 1 contains two edits made since my previous commit. Both should remain: removing the introductory sentence about the distinction between trailing and projected production, and removing the repeated sentence about win units from the main-results paragraph. The document has not been overwritten. The passages below are proposed replacements.

## Edits to Doc 1

### 1 Explain the shot sample and the missing information

The current explanation omits rebounds and does not identify the excluded shots. Replace the first two paragraphs under “How Game Value is calculated” with:

> Game Value uses NHL play-by-play and shift records to identify scoring chances, penalties, and the skaters on the ice. The shot model includes unblocked attempts with a goaltender in net. It excludes blocked shots, empty-net attempts, shootouts, and records without usable coordinates.
>
> Each included shot receives an expected-goals value, which is its estimated probability of becoming a goal. For example, an xG of 0.03 means a 3% chance of scoring. A logistic regression estimates this probability from distance, angle, shot type, manpower situation, and whether the shot followed a save as a rebound. The public data do not record pre-shot passing, so the model cannot distinguish all the circumstances that make two shots from the same location different.

The following score-state paragraph is broadly correct, including the restriction to even strength. [Shot sample and features](https://github.com/thomasmihaljevic27/xnpv-model/blob/cd23309a40ebc16debcac96de9f7d26efa9f6e6a/20_CODE/xg_model.py#L35).

### 2 Separate accounting checks from validation on unseen data

Replace the paragraph beginning “The metric covers 11,870 games” with:

> The recorded validation covers 11,870 games from 2017–18 through 2025–26. Across the league, the on-ice credits and debits sum to zero. This checks the allocation math. In separate regressions, team Game Value accounts for 3.4% of the variation in goal differential between individual games and 58.3% between team-seasons. These results describe how closely the assembled metric tracks the scoreboard; they do not establish its accuracy for individual players.
>
> The shot model was initially tested on the 2024–25 and 2025–26 seasons after being fitted on earlier seasons. It was then refitted on all regular-season data to produce the final Game Value inputs. The team-season comparison therefore uses games whose shot outcomes also helped estimate the final model. Game Value is constructed without Bacon WAR, but this comparison is not a test on wholly unseen data.

I would remove the MoneyPuck comparison until its target and sample are aligned with this test. The code describes the MoneyPuck benchmark as team-game xG versus goals in 2023–24, while this model is evaluated against goal differential over a different window. The current 3.4%-versus-7% comparison suggests more comparability than the record establishes. I carried that comparison forward in my first edit and would now remove it. [Final xG refit](https://github.com/thomasmihaljevic27/xnpv-model/blob/cd23309a40ebc16debcac96de9f7d26efa9f6e6a/20_CODE/xg_model.py#L474), [team regressions and benchmark description](https://github.com/thomasmihaljevic27/xnpv-model/blob/cd23309a40ebc16debcac96de9f7d26efa9f6e6a/20_CODE/metric_assembly.py#L385).

### 3 Make the adjusted metric concrete

Replace the first paragraph under “Why the model retains Bacon WAR” with:

> An adjusted version, GV-adj, was tested as a possible replacement for Bacon WAR. At five-on-five, it uses changes in lineups to estimate each skater's offensive and defensive contribution while accounting for teammates, opponents, venue, score, and zone starts. Other strength situations retain the equal split. GV-adj also includes penalties and a player's goals above expected, with finishing estimates pulled toward zero when the evidence is weak. Its tuning choices use NHL performance data rather than contract prices or agreement with Bacon WAR.

This explains what is adjusted and what remains unadjusted. GV-adj is also average-relative, whereas Bacon WAR is replacement-relative. Converting both to wins does not give them the same zero point. Correlation is useful for association, but cannot establish agreement in levels. [GV-adj construction](https://github.com/thomasmihaljevic27/xnpv-model/blob/cd23309a40ebc16debcac96de9f7d26efa9f6e6a/20_CODE/gv_adjusted_build.py#L6), [season-value assembly and centering](https://github.com/thomasmihaljevic27/xnpv-model/blob/cd23309a40ebc16debcac96de9f7d26efa9f6e6a/20_CODE/gv_adjusted_build.py#L365).

### 4 Narrow the explanation of the defensive result

Replace the second paragraph in that section with:

> GV-adj recovered a substantial share of Bacon's explanatory power for forwards, but performed poorly for defencemen in the replacement test. Play-by-play data provide limited information about some defensive contributions, which is one possible explanation. The comparison does not establish which measure is closer to a player's true defensive value. The model retains Bacon WAR for skater valuation.

The weak defensive result is observed. Attributing it entirely to Game Value's measurement limitations is an interpretation, not something the comparison alone identifies. The project's earlier model review already raises this distinction. [Existing discussion](https://github.com/thomasmihaljevic27/xnpv-model/blob/cd23309a40ebc16debcac96de9f7d26efa9f6e6a/40_DOCS/player_model_review.md#L173).

### 5 Describe midseason allocation as the next application

Replace the final paragraph of the allocation section with:

> The planned allocation uses Game Value from each team stint to divide the player's full-season Bacon WAR. The game records already identify the team, but this step has not yet been applied to the back-test. A direct proportional split also needs a rule for seasons whose Game Value is near zero or whose team stints have opposite signs. Until that rule is specified and tested, the split remains a design rather than a completed calculation.

For example, stint values of +1 and −1 sum to zero, so division by the season total fails. Values of +2 and −1 produce shares of 200% and −100%. Those may be intentional signed allocations, but the document should not present them as ordinary proportions without explaining the policy. This is an unresolved implementation question, not a reason to discard Game Value. [Open allocation task](https://github.com/thomasmihaljevic27/xnpv-model/blob/cd23309a40ebc16debcac96de9f7d26efa9f6e6a/00_STATE/WORK_QUEUE.md#L61).

### 6 Explain what the raw variants add

Keep the main results paragraph, including the user's latest edit. Replace the paragraph about the two raw checks with:

> Two checks used raw Game Value from the same underlying games. One retained its original zero-sum construction; the other moved the baseline to replacement level. Their correlations with trailing WAR were 0.564 and 0.609, respectively. Both were stable across seasons and weakened slightly at the later horizon. Their agreement shows that the result does not depend entirely on the GV-adj adjustments, although the three versions share data and construction choices.

Elsewhere in the repository, replace “three independent validators” with “three versions of a benchmark built without Bacon.” Independence from Bacon does not make the variants independent of one another. [Raw validation design](https://github.com/thomasmihaljevic27/xnpv-model/blob/cd23309a40ebc16debcac96de9f7d26efa9f6e6a/20_CODE/gv_4b_robustness_check.py#L20).

### 7 Remove instructions to the writer from the results

Replace the final paragraph of the results section with:

> The correlation was 0.648 for forwards and 0.302 for defencemen, so the pooled result gives a stronger impression of agreement than the defensive sample supports. The replacement-based raw variant produced a higher defensive correlation, but that result is sensitive to how the baseline is constructed.

Delete the two sentences about the unrun contract-length extensions. Their corrected attribution belongs in the project record; they interrupt this explanation. Also remove “That difference must accompany the pooled figure” and “it should not replace the main defensive result.” State the limitation directly rather than instructing a future writer how to cite it. This follows the editing preferences recorded in [PR 4](https://github.com/thomasmihaljevic27/xnpv-model/pull/4) and [PR 5](https://github.com/thomasmihaljevic27/xnpv-model/pull/5).

### 8 End with the claim the test can support

Replace the first paragraph under “What the results establish” with:

> The results show that a player's trailing WAR is associated with subsequent performance measured by Game Value. They support the use of the production estimate, particularly for forwards. They do not establish the correct dollar price of a win, validate the full contract NPV, or show that trades are systematically mispriced. Those claims require separate tests.

Keep the final paragraph explaining that both metrics describe the same games. I would remove the pre-registration discussion from this explainer: the correlations can be reported descriptively without reintroducing process detail you had already cut in earlier reviews. The no-threshold decision should remain in the methods record.

## Findings about the repository

### 1 The draft sensitivity calculation has a position mismatch

The primary Rule A curve is separate from this finding. In Rule B, realised skater production is priced with `_slope`, which includes the defence increment, but the trailing-production cost uses `BETA`, the forward slope.

For a defenceman with unchanged two-win production, above the floor, this alone creates about $548,224 of annual surplus at a $95.5 million cap. It is a formula-based illustration, not an estimate of the total effect on the published curve. The sensitivity result therefore includes a positional pricing difference as well as improvement over trailing production. The code and Doc 4 do not describe that as an intended assumption.

Recommended action: review the cost-side slope, then rerun Rule B and its comparison with Rule A before repeating the claim that the alternative is only 7.5% higher at pick 1. No coefficient change is needed to investigate this mismatch. [Value calculation](https://github.com/thomasmihaljevic27/xnpv-model/blob/cd23309a40ebc16debcac96de9f7d26efa9f6e6a/20_CODE/draft_yield_curve.py#L314), [cost calculation](https://github.com/thomasmihaljevic27/xnpv-model/blob/cd23309a40ebc16debcac96de9f7d26efa9f6e6a/20_CODE/draft_yield_curve.py#L343).

### 2 Excluding a player from direct comparables does not exclude his future from the whole aging model

`_weights` sets the target player's direct comparable weight to zero. However, `_build_globals` constructs average levels and age changes from all players, and `_shrunk` adds those global averages back into each projection. The target's later seasons can therefore reach his projection through the global component.

I exercised the actual global-average and shrinkage methods on two synthetic careers. Changing only the excluded target's future changed the resulting estimate despite his direct weight being zero. This confirms the path exists; it does not measure its size in the real panel. The actual effect may be small when the global group is large.

Docs 2 and 5 should not say that no player's own future reaches his valuation. The accurate statement is that it is excluded from direct comparable weights, while pooled parameters retain later information. The built-in aging validation also uses globals from the fitted panel; it should not be described as fully independent held-out validation without identifying the separate experiment that produced the cited figures. Recommended action: measure this exposure, distinguish it from the broader parameter-vintage issue, and consider training-only global estimates in a subsequent validation exercise. [Global construction and weighting](https://github.com/thomasmihaljevic27/xnpv-model/blob/cd23309a40ebc16debcac96de9f7d26efa9f6e6a/20_CODE/aging_curve.py#L329), [projection](https://github.com/thomasmihaljevic27/xnpv-model/blob/cd23309a40ebc16debcac96de9f7d26efa9f6e6a/20_CODE/aging_curve.py#L355), [built-in validation](https://github.com/thomasmihaljevic27/xnpv-model/blob/cd23309a40ebc16debcac96de9f7d26efa9f6e6a/20_CODE/aging_curve.py#L396).

### 3 The surplus-ratio defence needs a deliberate revisit

Common scaling cancels in a ratio of gross values. It does not generally cancel in a ratio of net surpluses, because costs are subtracted first. For example, gross values of $10 million and $8 million with costs of $8 million and $7 million give surpluses of $2 million and $1 million, a ratio of 2. Increasing both gross values by 20% while keeping costs fixed changes the ratio to about 1.54. This example is algebra, not a model rerun.

Near-zero or negative surplus denominators create a second problem. A third is the proposed null that surplus ratios average 1. Even two positive, exchangeable assets worth 1 and 2 give ratios of 2 and 0.5 under opposite orientations, averaging 1.25. Fairness or symmetry alone does not imply a mean ratio of 1.

The comparison statistic and its null should be specified together before the back-test. A cap-normalised signed surplus difference is a candidate for the primary comparison, with ratios retained where meaningful. This would revisit a locked decision, so it is a recommendation rather than an unrequested implementation change. [Locked ratio decision](https://github.com/thomasmihaljevic27/xnpv-model/blob/cd23309a40ebc16debcac96de9f7d26efa9f6e6a/00_STATE/DECISIONS.md#L31), [current null](https://github.com/thomasmihaljevic27/xnpv-model/blob/cd23309a40ebc16debcac96de9f7d26efa9f6e6a/00_STATE/WORK_QUEUE.md#L74).

### 4 Several explanations still confuse assumptions with findings

- Doc 4 labels actual traded-pick pricing “built and locked,” but its own text leaves the unknown-slot convention unsettled and the work queue still lists traded-pick pricing as future work. Separate completed diagnostics from a functioning pricing component.
- Doc 5 says setting positive second-contract surplus to zero “flatters” the top of the draft curve. Under the stated positive-surplus premise, it lowers pick value. That direction is reversed.
- Docs 2 and 5 infer understated exit risk from the 93% recovery figure being conditional on return. That conditional figure is a limitation of the recovery evidence; it does not establish bias in the separate exit-hazard estimate. The hazard builder explicitly records next-season absences. [Exit construction](https://github.com/thomasmihaljevic27/xnpv-model/blob/cd23309a40ebc16debcac96de9f7d26efa9f6e6a/20_CODE/exit_hazard.py#L149).
- Doc 2 treats a large interaction-test p-value as showing that the additive hazard model discards no real structure. It supports choosing the simpler model given the available evidence; it does not prove that interactions are absent.
- Doc 5's “−$1.71 million in cap share” mixes a dollar amount with a proportion. Specify the coefficient's units and any reference cap used to translate it into dollars.
- The goalie rate in Doc 3 repeats the old approximate narrative values, while the engine recovers its live constants from the spine. Quote the verified recovered rate and its vintage rather than treating the loose guard target as the exact rate. [Recovery and guard](https://github.com/thomasmihaljevic27/xnpv-model/blob/cd23309a40ebc16debcac96de9f7d26efa9f6e6a/20_CODE/contract_npv.py#L207).

### 5 Reproducibility is stronger internally than for a new reader

The exact-result guards, identity checks, name-agreement checks, and decision history are useful. They establish continuity with prior runs and catch specific errors. They do not establish that the economic interpretation is correct, and an existing guard can preserve an old mistake as accurately as a sound result.

The public setup needs a narrower promise. The source README says the included datasets allow the chain to run without a separate data request, then correctly says it cannot run without the confidential contract export. The main README still lists completed migration work as unfinished. Its installation line omits dependencies used by tracked scripts, including scikit-learn, openpyxl, Beautiful Soup, and TopDownHockey_Scraper. There is no tracked dependency lock or automated workflow in the reviewed snapshot. [Main README](https://github.com/thomasmihaljevic27/xnpv-model/blob/cd23309a40ebc16debcac96de9f7d26efa9f6e6a/README.md), [source README](https://github.com/thomasmihaljevic27/xnpv-model/blob/cd23309a40ebc16debcac96de9f7d26efa9f6e6a/10_SOURCE/README.md).

Keep the flat folder structure. The more useful cleanup is a current dependency specification, a clear statement of which components a public checkout can reproduce, and a small set of synthetic checks for joins, pricing units, and date boundaries. Confidential data need not be published to test those properties.

## Work I would prioritise

1. Apply the Doc 1 wording changes. They can improve accuracy without changing the model.
2. Measure and resolve the Rule B position mismatch and the aging global-average exposure. Preserve the old outputs for comparison and report effects separately from reproduction status.
3. Revisit the trade comparison statistic and write its null before inspecting back-test results.
4. Specify the signed-value allocation rule and complete a small, inspectable set of player-only trades before expanding to all asset classes.
5. Reconcile the public setup and the five explainers with the resulting implementation status.

The cross-asset framework remains a worthwhile thesis contribution even if the eventual back-test finds little evidence of systematic mispricing. At this stage, a transparent connection from information available at a decision date to a measured outcome will strengthen it more than another layer of explanatory prose.
