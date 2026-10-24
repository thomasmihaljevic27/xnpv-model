# Review of the New Draft

The new draft is substantially better at documenting the model than at explaining it continuously. It contains the main calculations, recent test results, useful worked examples, and explicit limitations. However, the reader repeatedly has to leave the calculation to follow a long discussion of model choices. The central problem is the amount and placement of detail, rather than a lack of evidence.

The review covers the supplied old draft and its 39 comments, the supplied new draft, the attached writing skill, the current implementing scripts, and the saved outputs and run logs. The new draft renders to 40 pages in Word. Page references below refer to that rendering. The source files were read without altering them.

## 1. Readability

The draft is readable at the sentence level in many of its worked passages. The explanation of Pacioretty's starting rate gives the inputs, shows the calculation, and interprets the result. The explanation of why a player cannot be his own comparable is also clearer than the wording criticized in the old draft. The addition of Tatar and the Sissons example addresses two specific omissions in the comments.

The difficulty is accumulation. Long paragraphs combine a specification, a numerical result, a comparison with another model, a significance statement, and a judgment about which model to retain. The reader must remember several baselines and units at once. The paragraph on weighting comparables is a clear example: it moves between the distance scale, same-player pairs, starting-rate error, later-rate error, season-WAR error, and resampling evidence.

The opening also delays the main idea. The long source descriptions and glossary arrive before the reader has a worked understanding of surplus. Source credibility matters, but a compact introduction to the inputs would allow the reader to reach the valuation sooner. Technical terms are easier to remember when they solve a problem already established in the text.

Several sentences still need ordinary copyediting. The introduction says assets “are valued and are put on a comparable scale,” with an inconsistent subject construction. “Under a salary cap ensuring that extracting proper value out of assets is critical” is not a complete sentence. “It’s remaining seasons” should be “its remaining seasons.” These are minor individually, but they weaken an otherwise technical document.

Assessment: the worked examples are the most readable material. The surrounding test discussions need shorter paragraphs, stable comparison labels, and fewer claims per paragraph.

## 2. Flow

The overall sequence is sensible: surplus, player forecasting, pricing, contracts, picks, prospects, and the combined trade. The Pacioretty trade gives the document a useful continuing example. The distinction between a player's own performance history and the information used to fit the price line is also eventually made.

Within that sequence, the explanation repeatedly stops. The starting level is followed by its decisions; comparables are followed by their weighting decisions; aging is followed by departure decisions. The approach makes the development history almost as prominent as the current calculation. Detailed tests can remain beside the component, as requested, while being consolidated into a clearly labeled table followed by a short interpretation.

The same point is often made more than once. Terminal value is defined in the glossary, introduced in the player equation, reintroduced at the contract equation, and then explained again under control seasons. The walk-away rule is stated in the initial control list and then restated under a separate heading. The reason for arbitration costs is repeated in the draft-pick section after the same rule has already been explained for terminal value.

The late limitations section is valuable, but the information-date limitation changes the meaning of earlier claims. The opening describes values as of the trade date. Only near the end does the draft explain that price coefficients, prospect fits, qualifying rates, and some inputs contain later information. A short early qualification and a fuller later discussion would prevent a reader from treating the exercise as a fully contemporaneous historical valuation.

Assessment: retain the current broad order and the common trade example. Explain each component once, retain its tests locally, and use cross-references only where they replace repetition rather than interrupt a sentence.

## 3. Explanation of the Concepts

The three-part skater forecast is explained well: performance rate, games conditional on playing, and probability of playing. The distinction between a cost incurred under a signed contract and optional future control is also valuable. The draft does more than state a regression; in several places it explains what the coefficient means in hockey terms.

The weakest passages turn an association or a fitted quantity into a stronger economic conclusion. Contract length is associated with higher cap hits, but the regression does not identify security as the cause. Lower goaltender persistence is evidence that past performance is a weaker predictor; it is not a direct estimate of the variance of annual changes. A nonsignificant period interaction is not proof of price stability.

The star-value explanation becomes careful later in the draft: it explicitly says the coefficient includes the surplus of regular players and extrapolates to a star probability of one. That qualification should be part of the first definition. Without it, “the surplus if certain to become a star” sounds like an estimate conditional on actually becoming a star, which is not what the regression estimates.

The production-by-age discussion contains an important reason for retaining linear production: its individual coefficient and p-value depend on the age reference when an interaction is present. That argument is technically useful and should remain. The stronger statement that the adopted model is “the only one” invariant to the age reference should be narrowed to the compared specification and restrictions. Other properly parameterized models can also be invariant.

Assessment: explain the current mechanics directly, and distinguish what the code does, what a predictive comparison supports, and what remains an economic assumption.

## 4. Checks Against the Current Code and Outputs

The major values are current. The supplied new draft is not simply quoting an obsolete price line. The October 21 skater coefficients match the current assignments in skater_forward_projection.py and xnpv1_price_line.json: intercept −0.0043092485, forward slope 0.0175092736, additional defence slope 0.0040764912, and term coefficient 0.0089103033. The current goalie line also matches the values described in the draft.

Independent arithmetic checks reproduced Pacioretty's −$1.957821 million and Tatar's −$4.056598 million contract values at the 2018-19 cap from their recorded season values, probabilities, retained shares, and discount factors. Suzuki's four contributions sum to $4.241747 million. The pick's round-average probability times the fitted star value gives $0.966335 million. Montreal's net is +$2.686909 million at the 2025-26 cap, and Vegas's is its exact opposite.

These checks validate the recorded arithmetic and agreement between the document's data and current saved outputs. They are not a fresh fit of the forecast, a rerun of the complete valuation pipeline, or independent verification of each vendor observation. Seventeen explicit reconciliation assertions passed. The supporting data include the October 22 document reconstruction, which itself records guards against the underlying valuation outputs.

### Corrections needed

1. Terminal-season floor treatment (Section 4, pages 15–16). The text says terminal value uses the floor discussed for contract seasons. The contract forecast integrates over uncertainty at the minimum, while rfa_terminal_value.py applies max(point price, minimum). The two operations must be distinguished. Historical drafted-player seasons also use the simple floor.

2. Sissons's performance unit (Table 17, page 20). The column labeled WAR per 82 contains season WAR with shortened league schedules normalized. For example, his 17-game season is not converted to an 82-player-game rate. The label should say season WAR, with the shortened-schedule normalization explained separately. Source: pick_curve.py price() and pick_curve_seasons.csv.

3. Sissons's control end (Table 17 note, page 20). The text says control ended after 2021-22. The current output has window_end = 2021, and price() includes seasons through end − 1. The final included season is 2020-21. The seven-row total of $0.742577 million is correct; the explanatory date is wrong.

4. Pricing sample (Section 3, page 12). The draft introduces 2,336 fitted contracts, then calls 2,388 contracts “the sample.” The latter is the candidate set. Fifty-two candidates lack a signing-dated forecast and do not enter the 2,336-contract fit. Name both populations and the exclusion rather than appearing to change sample size.

5. Number of price alternatives (Section 3, page 14). “Six alternatives” does not match the table, which contains seven alternatives after the adopted row. The count should be seven, or the count should be omitted.

6. Price stability (Section 3, page 14). A later-period test with p = 0.24 does not establish stability. Say the test did not detect a difference under that specification and sample. The test also predates the current coefficient lock, which its caption correctly notes.

7. Goaltender variability (Section 4, page 17). The table measures consecutive-season correlations. Replace “varies far more” with “is less persistent from season to season in this sample.” A variance claim requires a variance comparison.

8. Star value at first introduction (Section 6). The later qualification is sound but arrives too late. Define the quantity initially as the fitted coefficient on draft-position star probability, with the value at probability one an extrapolation. Do not imply it is an observed conditional average among stars.

9. Interpretation of the linear production coefficient (Section 7, page 30). In the full specification, the turning point depends on the linear term, the age interaction, and the squared term: P* = −[b + e(A − 18)] / (2c), where c is positive. The linear coefficient alone does not determine the minimum. Below that turning point, the fitted function really does decline as production rises; whether that local decline is substantively credible is a separate question.

10. Same-day contract timing (Section 8). The implemented exclusion is clear, but “the contract did not exist when Vegas acquired him” is stronger than a date-level dataset establishes. Describe a same-day exclusion convention unless intraday evidence is supplied. It should not imply that negotiations were unknown to the clubs.

11. Equality of cap growth and discounting (Section 1). The cancellation works for a fixed cap-share component. The league-minimum path can differ from a fixed share, so a blanket statement that all performance-side growth and discounting cancel needs qualification near the floor. The 3% assumption is a convention, not a result established by the absence of evidence for another rate.

12. Historical tests (throughout). Many captions appropriately identify older tests, but nearby prose calls a row “the adopted model” without consistently distinguishing the specification chosen then from today's full model. Preserve the test date, metric, sample, and baseline. Do not treat an October 5 score as a new score for the October 21 forecast.

13. Historical model discussion (Appendix C). Several sensitivities still refer to the retired qualifying-offer-only cost chain, despite comment 37 asking for that discussion to be removed. Those effects cannot be presented as sensitivities of the current arbitration-cost model. Omit them from the current-model explanation or retain them only in an explicitly historical research record.

### Significant coefficients and model choice

Comment 38 on the old draft requests removal of linear prospect production. The new draft explains why the current code retains it and includes a newer reference-age test. That is an explanation of the implementation, not evidence that the comment was executed. This review does not change the model. A decision to remove that term belongs to a separate modeling task because it changes values and imposes an age-reference-dependent restriction.

Likewise, the late-prospect production terms remain weakly supported. The new draft acknowledges their joint p = 0.085 and the nonsignificant predictive difference when they are removed. That is the correct limitation to retain. It should not be turned into a claim that all retained terms have passed a 5% significance requirement.

## 5. What the Independent Rewrite Changes

The rewrite follows the calculation from surplus to forecasts, prices, contract value, picks, prospects, and the combined trade. Detailed tests remain beside the relevant component. Eighteen tables and three graphs retain the evidence needed to compare choices without reproducing the complete development record.

The graphs each answer a different question: how Pacioretty's performance forecast changes with age, how pick value changes across draft positions, and how scoring and age change the value of a D+2 prospect. The trade is shown in a table because the receiving value, retained liability, and pre-trade value must be reconciled precisely.

All narrative prose was drafted anew. The rewrite preserves the current model, including choices that are open to criticism, and separates those choices from the strength of their evidence. It corrects the Sissons unit and end date, distinguishes the two floor treatments, labels historical tests, and states the later-information limitation directly.

The source Word files and the pre-existing edited repository copy of Valuing Prospects were left unchanged. No production model code was modified.
