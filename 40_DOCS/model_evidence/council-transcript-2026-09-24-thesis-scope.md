# Thesis scope council, 2026-09-24

Advisory only. Five independent advisor perspectives and five anonymous-response peer reviews, using the same model family. Run in batches under the three-worker concurrency limit. No adoption or scope decision enacted. Formatting normalised.

## Original question

Is the model too complicated for my Masters research project? Both models, the proposed rebuild and the current model, are quite complex. Has there been scope creep? What does the minimum viable product look like? Could I continue with the project using that? Or, given the models do exist, is it best to just continue with them knowing that they also are the highest performant model?

## Framed question and advisor responses

# Question

Is the xNPV Master's thesis too complex? Has scope crept? What is the minimum defensible thesis, and should existing complex player models be retained? The contribution is a common surplus-dollar scale for roster players, picks, and prospects, followed by a historical trade backtest. The player candidate is reviewed and closed but not adopted; picks/prospects and backtest remain incomplete. Its skater forecast improves, dollar squared-error gains are uncertain, and production has historical-information defects. No change is authorized by this discussion.

## Response A

The minimum defensible contribution is a consistent way to express three asset classes in expected surplus dollars, then test whether that common scale reveals patterns in historical trades. The thesis does not require the most sophisticated forecast for each asset. It requires valuations that use information available at the trade date, apply the same economic meaning of surplus, and support conclusions the data can actually establish.

Necessary complexity includes dated inputs and fitted parameters, explicit contract costs, consistent discounting, and a workable way to value picks and prospects. The backtest must also distinguish forecast errors from evidence of systematic mispricing. Addressing the old future-panel aging and future RFA-status problems matters more to credibility than adding predictive features.

The rebuilt Player Model deserves consideration: skater RMSE fell from .913 to .864 across 35,878 answerable rows, and dollar MAE fell from $1.854M to $1.761M across 1,111 rows. Those improvements support a bounded comparison; they do not establish global superiority or settle adoption. Its 48 checks establish completion of that review, not immunity from remaining limitations.

Freeze additional Player Model development while specifying the smallest viable pick model, prospect model, and trade backtest. Adopt complexity only when removing it would undermine timing integrity, economic comparability, or the central conclusion. Treat the already inspected 2022-25 period as inspected evidence when designing evaluation.

## Response B

The thesis becomes too complex when its central claim depends on assumptions you cannot explain, defend, and test within the remaining time. The number of models is a weaker guide. A complicated component can be manageable if its purpose is clear; a simple component can undermine the thesis if it uses information unavailable at the trade date.

From a fresh reader's perspective, the strongest thesis is: put three asset classes on a consistent surplus-dollar scale, then examine historical trades with clear limits on what the comparisons establish. The committee needs to understand how each asset gets its value, which information was available, and how uncertainty affects the trade conclusions.

Your MVP therefore still needs all three asset classes and a historical backtest, but it can use restrained specifications, a narrower defensible sample, and a small set of sensitivity checks. Further player-model infrastructure should earn its place by resolving a specific obstacle to those requirements.

The rebuilt candidate's lower prediction errors support considering it. They do not establish that its dollar valuations identify market mispricing. The dating corrections may matter more to defensibility than the accuracy gains.

Keep adoption deferred until you can compare the candidate with a credible simpler baseline and explain the material assumptions in your own words. Then choose the model that makes the completed thesis strongest, including the time needed to write and defend it.

## Response C

Keep the rebuilt player candidate available, freeze further development, and define the minimum complete thesis around the cross-asset comparison and trade backtest. The relevant choice is how much additional work each route requires to produce defensible results. Work already spent building the candidate is sunk.

Returning to the old model is not automatically the faster defensible route. Its future-panel aging information and future RFA labels require correction before historical valuations can support the thesis. The new candidate addresses those timing problems, but its extra machinery creates explanation and verification work. The forecasting gains alone do not settle adoption: RMSE falls from 0.913 to 0.864, and dollar MAE from $1.854M to $1.761M, with uncertainty remaining around the squared-error improvement.

The next concrete step is a one-page completion contract for the thesis:
1. Specify the common dollar output each asset model must supply at a historical decision date.
2. List only the work needed to produce those outputs, prevent future-information leakage, and run the trade comparison.
3. Define acceptable limitations and the checks that would block use.

Respect the deferred adoption decision. When picks and prospects resume, compare the remaining cost of repairing the old player model against documenting and checking the candidate.

Stop player-model expansion unless a failure threatens historical validity, changes the central conclusion, or prevents cross-asset integration.

## Response D

The danger is that the player rebuild becomes the thesis because it consumed the most effort. Forty-eight passing checks establish that the candidate meets those checks; they do not establish that its additional complexity improves the economic conclusions. The modest forecast gains and uncertain squared-error improvement make that distinction consequential.

But reverting to production solely to simplify would be false economy. Future-panel aging and future-status information threaten the historical interpretation directly. Simplicity cannot compensate for information that was unavailable when a trade occurred.

I would define the minimum thesis around one question: Does a common, historically available surplus-dollar valuation reveal systematic differences in NHL trade pricing?

That requires:
1. Freeze one defensible player specification, choosing on historical-information integrity and practical usability. Document its limitations and stop forecast optimization.
2. Build deliberately simple pick and prospect valuations sufficient for the common-dollar comparison. Exclude asset categories or years that cannot be measured credibly.
3. Restrict the backtest to a declared sample with adequate coverage, checking the assumed completeness from 2018 onward.
4. Test only a few prespecified pricing comparisons, with uncertainty and sensitivity checks.
5. Begin writing now.

Retain the rebuilt machinery as research infrastructure, but include only components necessary for this analysis. If the cross-asset backtest remains infeasible, negotiate a narrower thesis explicitly; silently replacing it with another model-improvement project would obscure the original contribution.

## Response E

The upside worth preserving is the work that makes the thesis's central comparison credible. A common surplus-dollar scale is only useful if player values, pick values, and prospect values reflect information available at the trade date. The rebuilt Player Model's dated fits therefore matter more than its modest forecasting improvement: they address known defects in the old model that could undermine the historical backtest.

I would preserve the candidate as a serious adoption option, while stopping further player-model search. Its closed review and 48 checks are valuable infrastructure, although they do not establish thesis readiness. The reported RMSE and dollar MAE improvements support considering it; the inconclusive squared-error gain does not justify another optimization campaign.

A minimum thesis can retain sophisticated machinery internally while making fewer research claims. It needs defensible valuations for all three asset classes, a bounded historical trade sample, and an explicit account of missing observations and uncertainty. Vendor completeness from 2018 onward makes a later, narrower sample worth evaluating before attempting broader reconstruction.

Stochastic paths and rights options earn their place if they materially change asset comparisons or explain uncertainty in trade valuations. Otherwise, retain them as existing supplementary capabilities.

The scope-creep boundary is new sophistication without a demonstrated effect on the trade question. Preserve working infrastructure; spend remaining effort completing integration and producing an interpretable backtest.


## Anonymisation mapping

{'A': 'First Principles', 'B': 'Outsider', 'C': 'Executor', 'D': 'Contrarian', 'E': 'Expansionist'}

## Peer reviews

### Reviewer 1

Strongest: A. It makes economic comparability and historical information the criteria for necessary complexity, and explicitly separates forecast error from systematic mispricing. That protects the thesis's actual contribution.

Biggest blind spot: D. Excluding poorly measured asset categories can remove precisely the trades whose pricing differs. Missing prospects, conditional picks, or contract details are plausibly related to trade complexity and value. Dropping individual package components also makes the remaining comparison economically incomplete. Restrictions need whole-trade accounting, explicit inclusion rules, and analysis of who gets excluded.

What all five missed: Common surplus dollars needs an operational definition: comparable valuation dates, club-control horizons, discounting, contract costs, terminal rights, and treatment of assets that never reach the NHL. They also need to distinguish a forecasting backtest from a pricing test: realized differences can reflect risk, team circumstances, or omitted consideration. A narrower sample changes the population about which the thesis can claim anything.

### Reviewer 2

Strongest: C. Its remaining-work comparison is the best scope discipline: repairing production and operationalizing the candidate both have costs. The completion contract could expose whether either route actually supplies historically valid outputs without launching another model project.

Biggest blind spot: E. Calling stochastic paths and rights options existing supplementary capabilities risks understating integration work. Their availability does not establish usable historical coverage, compatible outputs, or a defensible valuation interpretation. Materiality checks themselves need a bounded implementation budget.

All five miss: Simple picks and prospects is not an implementation specification. Define the historical inputs already available, the outcome being forecast, the valuation horizon, and the minimum transformations required. Also distinguish a valuation evaluated at point forecasts from expected surplus across simulated outcomes. With nonlinear survival, contract, or rights rules, those quantities can differ. All three asset classes need a consistent expectation target; simulation is one possible method, not automatically a requirement.

### Reviewer 3

Strongest: B. It treats student mastery as a binding constraint: Thomas must explain and defend the assumptions himself. It also clearly separates improved forecasts from identifying market mispricing, which is essential for a supervisor concerned with identification.

Biggest blind spot: E. Keeping sophisticated machinery internally while reducing claims does not remove the burden of understanding, documenting, and defending that machinery. Existing infrastructure can still make the thesis unmanageable.

What all five missed: The minimum defensible thesis requires an explicit agreement with the supervisor about the research claim and required evidence. All three assets plus a backtest may be the current objective, but that does not establish the supervisor's minimum. They also need a concrete distinction between testing forecast accuracy and testing systematic pricing differences: what comparison identifies the latter, and what alternative explanations could produce it?

### Reviewer 4

Strongest: C. It correctly treats past development as sunk cost and compares remaining work: repairing historical-information defects versus documenting, maintaining, and integrating the candidate. Its completion contract turns scope into concrete deliverables.

Weakest: E. Preserving sophisticated machinery as supplementary capabilities can conceal ongoing maintenance and verification costs. It also treats vendor completeness from 2018 onward too confidently: complete vendor records need not supply historical contracts, prospect status, or sufficient follow-up to measure realized outcomes.

All five missed: No recommendation establishes feasibility against an actual submission deadline. First inventory usable trades by year and asset mix, dated-input availability, and realized-outcome horizon; then estimate remaining integration, checking, and writing effort. A later sample may improve input coverage while reducing outcome maturity. Set a dated go/no-go checkpoint for the cross-asset backtest, with a supervisor-approved fallback if coverage or time fails.

### Reviewer 5

Strongest: C. It turns simplification into a concrete completion contract while preserving the three-asset contribution and deferred adoption decision. Comparing remaining work avoids both sunk-cost reasoning and assuming an older model is easier to defend.

Biggest blind spot: D. Exclude asset categories could remove a defining pillar while appearing to preserve the original question. Its explicit warning against silent replacement helps, but category exclusions need a clear distinction between narrower coverage within each class and abandoning a class altogether.

What all five missed: Define which conclusions must survive simplification, then assess omissions against those conclusions. A narrower sample can change the population being studied; omitted rights, conditions, or assets can change what a trade's measured imbalance means. Forecast rankings cannot resolve those issues. Any material change to the research question or target population needs an explicit supervisor agreement, while ordinary specification simplification need not become a new model-selection competition.

## Chairman synthesis

## Where the Council Agrees

Freeze additional player forecasting research. The thesis contribution is comparing players, picks, and prospects in consistent surplus dollars, then examining historical trades. Correct historical information and complete economic accounting are necessary. Global forecasting superiority has not been established, and better forecasts alone do not identify market mispricing.

## Where the Council Clashes

One view favours retaining existing sophistication as infrastructure; another stresses the continuing cost of understanding, documenting, maintaining, and integrating it. These are compatible only if the retained implementation is frozen and usable. Narrowing coverage can help feasibility, but dropping an asset class or ignoring part of a trade changes the research question.

## Blind Spots the Council Caught

The minimum needs a common valuation date, treatment of team-control years, cost schedule, discounting, and outcome horizon. A point forecast passed through a nonlinear price or rights rule need not equal expected value across possible outcomes. Removing simulation is therefore a methodological change, not just deleting optional code. A later sample may improve source coverage while leaving fewer completed outcomes. Actual deadline and supervisor requirements remain unknown. Five perspectives are advisory reasoning, not independent empirical confirmation.

## The Recommendation

Reduce the scope of additional research while retaining the reviewed player candidate as the leading option for the deferred adoption decision. Do not rebuild it again merely to make its code shorter. Treat the previous chain as a diagnostic comparison; known dating defects prevent calling it an equally credible historical baseline without repairs.

The proposed minimum is one dated forecast specification per asset class, one declared dollar currency, explicit contract and control-year costs, complete accounting of included trade packages, and a bounded historical comparison with a few prespecified categories. Picks and prospects need usable historical inputs and restrained cohort-based forecasts, including failures to reach the NHL. These are proposed starting specifications, not already verified implementations. Model uncertainty and sampling uncertainty must be distinguished.

Keep existing simulated mean values if they are already the consistent expectation target. Detailed tail-risk claims, new dependence models, further star-specific tuning, and repeated goalie competitions are optional unless required by the research question. Material rights cannot simply be discarded; use an explicit convention and a bounded sensitivity. The student must be able to explain the assumptions, even when implementation details sit in an appendix.

The completed development comparison favours the rebuilt skater candidate over production on forecast error. That makes it a reasonable leading choice, not the proven highest-performing possible model, a proven winner for all asset classes, or a validated trade-pricing system. No adoption or scope change is enacted here.

## The One Thing to Do First

Agree a one-page thesis completion specification with the supervisor: one research question, included trade population, common valuation target, required tables, remaining tasks, and a stopping rule. Use a coverage inventory and the actual deadline to determine feasibility before expanding the next pillar. This is a focused scope decision, not a request to reopen every technical choice.
