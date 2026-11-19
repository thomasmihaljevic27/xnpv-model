// findings_doc.js v2.1 -- builds "Trade Back-test, What We Found and How, revised.docx" (40_DOCS/); v2.0 built "Trade
// Back-test, What We Found and How.docx" (Thomas's commented copy of it is kept in git); v1.x "Back-test Findings and Methods.docx".
//
// v3.0 (2026-11-18): Thomas's fourth round (6 comments and his edits on the v2.9 file), his edits carried verbatim ("the
// team received"; "is the same under both rules"; "actually lost value"; "counting each trade only once" and the 5% sentence
// cut; "may also require that player have their salary retained"; "double check each finding" and the colon labels; "the
// following characteristics"; "(defined as the player with the highest cap hit)"; Section 3's "What it means" and the
// declared-first sentence cut; "market value increase"; "along with"; "Team higher in the standings"; "Team retained
// salary"; "final contract season"). The declared window throughout (Thomas: "I would do 2017-22 for both trade day and
// realized value"; protocol amendment 2ec8523), except Section 4 on all trades with the correction instrumented by the
// seasons played ("All trades, played seasons"). Step 4 says how an average is tested; Step 5 shortened and Section 3's
// "How it was measured" moved into it; the "other samples" table gone; the final-season restricted free agent and late
// picks in the joint regression, with its trade-day column (groups_any.py v1.2); who_overpaid_any.py v1.4,
// who_overpaid.py v1.1, trend_both.py v1.1. Repetition cut: figures restated from a table, the measures' rule restated in
// a caption, the not-about-a-player note, the age-in-one-regression bullet (moved to Section 3), the by-construction
// paragraph (the trend is now on played-out years). Previous body: git show 68fcf09^:25_TESTS/findings_doc.js.
//
// v2.9 (2026-11-18; Thomas: "Cap-weighted"): under the any player rule the three measured characteristics are averages
// over the players received, weighted by cap hit (who_overpaid_any.py v1.3); the any player figures updated.
//
// v2.8 (2026-11-18): Thomas's third round (17 comments and his edits on the v2.7 file), his edits carried verbatim (Step 1's
// grade sentence; "2026-27 and onwards"; Step 4's and Step 6's cut sentences; Section 2's and Section 4's bold answers cut;
// the rule paragraph, moved to Section 1 as he asked; "seasons left on contract"; "former top-15 draft pick"; "would be
// circular"; "in the future"; "shedding the contract"; "other factors held constant"; the term and declared-and-found limits
// cut; "partly forecasted"; "There is found no difference"), except "Method" written "rule" (his note: pick one) and "735
// trades" written "735 clubs in Section 3's regressions". Section 1 says how a finding is made statistically. Each rule
// applied to every characteristic (who_overpaid_any.py v1.2) and category (groups_any.py v1.1); the replication figures in
// a table; Section 4's table renamed; both values after 2022 for the futures sellers; late picks and final-season
// restricted free agents in the category table; the change over time on both values with p-values (trend_both.py v1.0).
//
// v2.7 (2026-11-18; Thomas: "yes check all other categories for the any player version"): Section 5's group table shows
// each category's rule and, for the ones built from one player, the any-player figures (groups_any.py v1.0); the former
// top-15 row was mislabelled "main player" (backtest_cuts.py builds it from any player received).
//
// v2.6 (2026-11-18; Thomas: "I want to report both sides. One with the biggest contract lens and one without it"):
// Section 3 shows the main-player and the any-player regressions side by side (who_overpaid.py v1.0,
// who_overpaid_checks.py v1.2, who_overpaid_any.py v1.1), and so does the table of their other terms in Section 5.
//
// v2.5 (2026-11-18; Thomas: "I thought we agreed to switch to just yes or no on the trade types, not by if it's the player
// with the highest cap"): Section 3 and its other terms in Section 5 on the any-player rule (who_overpaid_any.py v1.1);
// the main-player rule is one bullet. Section 5's group table stays on the main player, labelled.
//
// v2.4 (2026-11-18; Thomas: "Move to limits"): the term section (its table and two bullets) becomes one limit.
//
// v2.3 (2026-11-18): Thomas's second round (14 comments and his edits on the v2.1 file), carried verbatim: title "Findings";
// the opening bullets and "The data" cut; "valued at the same market rate"; "For each club what it actually received less
// what it gave up is its realized value."; "valued again by the appropriate model"; "Step 3: look at categories of trades";
// "A club acquiring a 30-year-old at the trade deadline"; Step 6's parentheses cut; the played-out bullet, Section 3's and
// Section 5's bold answers, the base-player bullet and Section 6's answer cut; "Findings" for "What was found"; his table
// note; "Each of the three findings"; "Teams only respond ... for every dollar of mispricing"; "priced contracts correctly";
// "by as much as it should"; "5. What Is Not Mispriced"; "The mispricing is captured by the model". His notes: the player's
// value as an equation; overpay and loss dropped for the trade-day grade and realized value themselves (negative = the club
// lost); every table cell with its standard error and p-value (two-stage rows from who_overpaid_checks.py v1.2); Section
// 3's "look like findings" moved into Section 5 with a table of the regression's other terms; the cap-hit bullet cut; the
// declared groups (clause, futures sellers) named in the limits; the term paragraph rewritten.
//
// v2.2 (2026-11-18): the clause flag described as it is built (any player received, backtest.py's g_clause; it was called the
// main player's); a bullet on the any-player version of the who-is-overpaid regression (who_overpaid_any.py v1.0). Not yet
// written to 40_DOCS: Thomas has the v2.1 file open with edits of his own to carry first.
//
// v2.1 (2026-11-18): Thomas's 35 comments on v2.0 and his own edits, carried verbatim (grades "sum to zero"; "Each asset is
// followed after the trade and what it actually delivered is valued at the same prices."; "Standard errors are clustered by
// trade."; "Creating one metric to evaluate players, picks and prospects works ... the result is replicable when using an
// alternative metric to evaluate performance."; "per asset acquired"; "the overpay result replicates"; each "Source:" line
// cut). "Take every club the same type of trade" gets the missing "that made". "Is explained by the model" is written "shows
// up in the realized value": the slope is not R-squared, which is now its own row. Holm's adjustment is dropped (his call
// to make; no finding changes: no group's beyond-its-price coefficient has an unadjusted p below 0.05). Offer sheets are
// removed. "Result" is "realized value" throughout; overpay and loss are defined by sign; a finding must show in both the
// trade-day grade and the realized value. New figures: the fully played-out trades (played_out_trades.py v1.0), the
// defenceman and former top-15 rows of Section 5 (groups_clustered.py v1.0, joint_regression.py v1.2), the count of clubs
// receiving more than one player (backtest_assets.csv).
//
// v2.0 (2026-11-17; Thomas: "reading that document vs reading in chat is night and day in terms of readability. Maybe go
// back to the drawing board, from scratch, and try to write in a style more like what your last few messages have been? I
// still want point form, but try to maximize for reading comprehension (I still want statistical details, though)"):
// rewritten from scratch in plain point form. Each section opens with its answer in one sentence, then how it was measured,
// what was found (a table) and what it means, with the statistics kept and explained where they first appear. The five
// take-aways of 2026-11-17 are unchanged. v1.0-v1.1 (2026-11-15/17): the first bullet drafts.
//
// NUMBERS: each figure is a constant below, read from the run log or results file named in its table note (all written
// 2026-11-11 to 2026-11-17, on the model as decided: each contract season priced on the term left).
//   groups_clustered.py v1.0, joint_regression.py v1.2, who_overpaid.py v1.0, who_overpaid_checks.py v1.1,
//   backtest.py v1.7 and backtest_gv_compare.py, backtest_cuts_more.py v1.3, contract_value_by_age.py v1.1,
//   term_quality_test.py v1.1, defence_checks.py v1.1; logs in 30_OUTPUT/ and 30_OUTPUT/_extended_run/.
//
// Run:  NODE_PATH=<folder with docx> node 25_TESTS/findings_doc.js

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType, HeadingLevel,
  BorderStyle, ShadingType, LevelFormat, Footer, PageNumber,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const OUTFILE = process.env.DOC_OUT || path.join(ROOT, "40_DOCS", "Trade Back-test Findings.docx")   // v2.3: a new file; the ", revised" file holds Thomas's second round of notes
const FONT = "Arial";
const VERSION = "findings_doc.js v3.0";

// ---- building blocks ---------------------------------------------------------------------------------------------------
// A string is plain text; ["Label", "text"] as L() gives a bold lead-in label followed by plain text.
const T = (text, o = {}) => new TextRun({ text, font: FONT, ...o });
const runs = (t) => (Array.isArray(t) ? t : [t]).map((x) => (typeof x === "string" ? T(x) : x));
const L = (label, text) => [T(label + " ", { bold: true }), T(text)];
const B = (t, level = 0) => new Paragraph({ numbering: { reference: "bullets", level }, children: runs(t), spacing: { after: 70 } });
const P = (t) => new Paragraph({ children: runs(t), spacing: { after: 120 } });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [T(t)] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [T(t)] });
const NOTE = (t) => new Paragraph({ children: [T(t, { size: 17, italics: true })], spacing: { before: 40, after: 160 } });
const ANSWER = (t) => new Paragraph({ children: [T(t, { bold: true })], spacing: { before: 40, after: 120 } });

const W = 9360;                                            // US Letter, 1-inch margins
const border = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(head, rows, widths) {
  const sum = widths.reduce((a, b) => a + b, 0);
  const w = widths.map((x) => Math.round((x * W) / sum));
  w[w.length - 1] += W - w.reduce((a, b) => a + b, 0);
  const cell = (text, i, header) => new TableCell({
    borders, width: { size: w[i], type: WidthType.DXA },
    shading: header ? { fill: "E8EEF4", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 50, bottom: 50, left: 80, right: 80 },
    children: [new Paragraph({ alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
      // v2.3: a line break inside a cell's text starts a new line in the cell
      children: text.split(String.fromCharCode(10)).map((s, k) => T(s, { size: 17, bold: header, break: k ? 1 : 0 })) })],
  });
  return new Table({
    width: { size: W, type: WidthType.DXA }, columnWidths: w,
    rows: [new TableRow({ tableHeader: true, children: head.map((h, i) => cell(h, i, true)) }),
      ...rows.map((r) => new TableRow({ children: r.map((x, i) => cell(x, i, false)) }))],
  });
}

// ---- the content -------------------------------------------------------------------------------------------------------
const body = [];
const add = (...x) => body.push(...x);
// an equation line: a list of [text, "sub" | "sup" | undefined] pieces, centred, in Cambria Math
const EQ = (parts) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 80 },
  children: parts.map(([s, k]) => new TextRun({ text: s, font: "Cambria Math", size: 22, italics: false,
    subScript: k === "sub", superScript: k === "sup" })) });

add(new Paragraph({ heading: HeadingLevel.TITLE, children: [T("Findings")] }));

// ==== 1 ====
// a bold label held with the table that follows it
const MR = "Main player rule", AR = "Any player rule";
const LABEL = (t) => new Paragraph({ keepNext: true, spacing: { before: 120, after: 60 }, children: [T(t, { bold: true })] });
add(H1("1. How a Finding Is Made"));
add(H2("Step 1: grade every trade on trade day"));
// v3.0 (Thomas: "I think it hurts the models credibility to include these trades"; "I would do 2017-22 for both trade day
// and realized value"): the sample and its reason
add(B("The trades are the 563 made from July 1, 2017 to March 28, 2022. Later trades are left out: more of their realized "
  + "value would be the models' forecast standing in for seasons not yet played."),
  B("Every player, pick and prospect in a trade gets a dollar value from the models, using only what was known that day. "
  + "This value is its expected net present value (xNPV)."),
  B(L("A player's value", "is what his forecasted performance is worth on the market, less what he costs against the cap, "
    + "over the rest of his contract, with the seasons of continued team control included for restricted free agents.")),
  B(L("A pick's or a prospect's value", "is what a pick in that spot, or a prospect with that record, has typically turned into.")),
  B("What each club received less what it gave up is the club's trade-day grade. A positive grade means it got more value "
    + "than it gave; negative means it paid too much. The two clubs' grades always sum to zero."));
add(H2("Step 2: see how each trade actually turned out"));
add(B("Each asset is followed after the trade and what it actually delivered is valued at the same market rate."),
  B("For each club what it actually received less what it gave up is its realized value."),
  B("A player's value:"));
add(EQ([["xNPV = ", undefined], ["Σ", undefined], ["k", "sub"], ["  [ max(α + βW", undefined], ["k", "sub"],
  [" + δDW", undefined], ["k", "sub"], [" + γT", undefined], ["k", "sub"], [", m) × Cap", undefined], ["k", "sub"],
  [" − C", undefined], ["k", "sub"], [" ] / 1.03", undefined], ["k", "sup"]]));
add(B("k counts the seasons left from the trade (k = 0 is the season of the trade). W is the wins above replacement (WAR) "
  + "delivered; T is the years of term left on the contract; D is 1 if the player is a defenceman and 0 otherwise; m is the "
  + "league minimum salary's share of the cap; Cap is that season's salary cap; C is the player's cap hit. The price line is "
  + "α = -0.43%, β = 1.75%, δ = 0.41% and γ = 0.89% of the cap. Each value is then stated at the 2025-26 cap "
  + "($95.5M), and all figures below are in millions of dollars at that cap.", 1),
  B(L("Example.", "A forward who delivers 2.0 WAR with three years of term left is worth (-0.43% + 1.75% x 2 + 0.89% x 3) "
    + "x $95.5M = $5.49M for the season. On a $4.0M cap hit, the club's net for that season is +$1.49M."), 1),
  B("Seasons from 2026-27 and onwards have not been played yet, so for those the realized value uses the models' forecast. A "
    + "pick is followed to the player drafted with it; a pick or prospect who has not reached the NHL by 2026-27 is valued "
    + "again by the appropriate model."));
add(H2("Step 3: sort the clubs into categories of trades"));
// v3.0: Thomas's edits ("the team received", "is the same under both rules"); the counts on 2017-22
add(B("A category is a type of trade, for example acquiring a player aged 28 to 31, or buying at the trade deadline. Each "
  + "club is either in a category or not."),
  B("There are two ways to categorize teams based on the trade, if the main player received in the trade met a certain "
    + "criterion, or if any player received in the trade met a certain criteria:"),
  B(L("Main player rule:", "a club is in a group when its main player has the characteristic; for example, it is in the "
    + "former top-15 pick group when its main player is a former top-15 pick. The main player is defined as the player with "
    + "the highest cap hit the team received."), 1),
  B(L("Any player rule:", "a club is in a group when any player it received has the characteristic. Of the 431 clubs in "
    + "Section 3's regressions, only 45 received two or more players, so this method is a type of robustness check."), 1),
  B("Each result is reported under both rules. A category about a player sent, such as retained salary, uses the main "
    + "player sent (the highest cap hit) or any player sent. A category not about a player, such as buying at the deadline, "
    + "is the same under both rules."));
add(H2("Step 4: test each category on its own"));
// v3.0 (Thomas: "How though"): how the average is tested; his edits ("actually lost value"; "counting each trade only
// once"; the 5% sentence cut)
add(B("For each category, the clubs in it are averaged twice: once on their trade-day grades and once on their realized "
  + "values."),
  B("Each average is tested against zero. A negative average trade-day grade means clubs making that type of trade paid more "
    + "than the models' value; a negative average realized value means they actually lost value."),
  B("The test divides the average by its standard error, which measures how much the average would vary from one sample of "
    + "trades to another. The p-value is the chance of an average at least that far from zero if clubs making that type of "
    + "trade in truth broke even."),
  B("The two clubs in a trade are mirror images of each other, so they are not two independent observations. Standard "
    + "errors are therefore clustered by trade, counting each trade only once."));
add(H2("Step 5: hold the other characteristics constant"));
// v3.0 (Thomas: "Just state that two regressions are then run on both trade day and realized value and which variables";
// "it just feels like this belongs in Section 1"): Section 3's "How it was measured" moved here, his edits verbatim
add(B("Characteristics overlap. A club acquiring a 30-year-old at the trade deadline may also require that player have their "
  + "salary retained or give up picks. Two regressions are therefore run, one on the clubs' trade-day grades and one on their "
  + "realized values, with all the characteristics in at once."),
  B(L("In Section 3,", "the club's trade-day grade and its realized value are each regressed on the following characteristics: "
    + "age, position, clause, signed as an unrestricted free agent, seasons left on contract, production (recent WAR, "
    + "weighted 50/30/20 across the three most recent seasons), how much that production exceeds its forecast, the share of "
    + "games played in the most recent season, and whether a player is a former top-15 draft pick. Standard errors are "
    + "clustered by trade.")),
  B("Under the main player rule each characteristic is the main player's (defined as the player with the highest cap hit). "
    + "Under the any player rule a yes-or-no characteristic, such as the clause, counts when any player received has it; "
    + "production, how much it exceeds its forecast and the games share are averages over the players received, weighted by "
    + "cap hit.", 1),
  B("The cap hit is left out on purpose. A contract's value is already its performance value less its cap hit, so \"clubs "
    + "overpay for expensive players\" would be circular.", 1),
  B(L("In Section 5,", "each two-team trade is taken once, and the first club's value is regressed on the differences between "
    + "the two clubs in every category of trade: those in the Section 5 table, the two age groups and the clause, selling a "
    + "player for picks and prospects, buying earlier in the season while higher in the standings, and taking on a contract "
    + "to clear cap. There is no constant, because the second club's value is the first club's with the sign reversed. Each "
    + "trade is one row, so its standard errors are robust ones.")));
add(H2("Step 6: what counts as a finding"));
add(B("A finding must show in both the trade-day grade and the realized value: the characteristic is statistically "
  + "significant at the 5% level in both regressions, with the same sign."));
// v3.0: his title and colons; the fresh-trades check removed (Thomas: "I want this removed")
add(H2("Step 7: double check each finding"));
add(B(L("A second performance measure:", "Does it hold when performance is measured with Game Value instead of WAR?")),
  B(L("Played seasons only:", "Does it hold when a club's realized value counts only the seasons played through 2025-26, with "
    + "no model projection of the seasons after?")));

// ==== 2 ====
add(H1("2. The Models Predict How Trades Turn Out"));
add(table(["", "WAR", "Game Value"], [
  ["Favoured club came out ahead", "57.1% [53.3, 61.1]\np = 0.001", "56.9% [52.9, 60.8]\np = 0.001"],
  ["Slope of realized value on trade-day grade", "0.749 [0.553, 0.901]\np < 0.001", "0.731 [0.530, 0.957]\np < 0.001"],
  ["R-squared", "0.309", "0.296"],
], [40, 30, 30]));
add(NOTE("The slope is how far a club's realized value moves for each $1 of its trade-day grade: 1 means the predicted gap "
  + "shows up in full on average, 0 that the grade predicts nothing. R-squared is the share of the variation in realized "
  + "values that the trade-day grades account for. The two answer different questions: the prediction is close to right on "
  + "average, but single trades scatter widely around it. 95% confidence intervals in square brackets; the p-values test the "
  + "share against 50% and the slope against zero."));
add(B(L("What it means.", "Creating one metric to evaluate players, picks and prospects works: about three-quarters of the gap "
  + "predicted on trade day shows up in the realized value, and the result is replicable when using an alternative metric to "
  + "evaluate performance.")),
  B(L("By type of asset,", "realized minus predicted value per asset acquired: players +0.104 [-0.078, +0.294] (664 assets); "
    + "prospects +0.158 [-0.138, +0.521] (253); picks -0.188 [-0.330, -0.041] (633). Only picks fall short of their "
    + "prediction by a statistically significant amount.")));

// ==== 3 ====
// v3.0: on 2017-22 (who_overpaid_any.py v1.4); one table with each rule's rows
add(H1("3. Clubs Overpay for Players with Contract Clauses and, by the Main Player Rule, Players Aged 28 to 31"));
add(table(["Club acquiring", "Rule", "Trade-day grade", "Realized value, WAR", "Realized value, Game Value", "Realized value, WAR, played seasons only"], [
  ["A player with a clause", MR, "-2.71 (0.97)\np = 0.005", "-2.64 (1.15)\np = 0.022", "-2.50 (1.20)\np = 0.038", "-2.49 (1.05)\np = 0.017"],
  ["", AR, "-2.21 (0.72)\np = 0.002", "-2.20 (0.92)\np = 0.016", "-2.05 (1.03)\np = 0.047", "-2.19 (0.90)\np = 0.015"],
  ["A player aged 28 to 31", MR, "-1.53 (0.59)\np = 0.009", "-2.31 (0.94)\np = 0.014", "-2.27 (0.97)\np = 0.019", "-1.96 (0.89)\np = 0.027"],
  ["", AR, "-1.07 (0.69)\np = 0.12", "-1.67 (1.04)\np = 0.11", "-2.01 (1.14)\np = 0.077", "-1.36 (0.98)\np = 0.16"],
], [20, 16, 16, 16, 16, 16]));
add(NOTE("Figures in millions of dollars as of the 2025-26 salary cap. Negative means the club paid more than the models' value "
  + "(trade-day grade) or lost value (realized value). Standard errors in brackets, clustered by trade. All characteristics "
  + "are in each regression together; the other terms are in Section 5. 431 clubs (313 trades)."));
add(B(L("The clause finding", "holds in each test under both rules. Clubs that take on a player with a no-trade or no-move "
  + "clause pay more than the models' value and lose value, on WAR, on Game Value and on played seasons only.")),
  B(L("The age 28 to 31 finding", "holds in each test under the main player rule. Under the any player rule none of its four "
    + "figures is statistically significant (the smallest p-value is 0.077, on Game Value).")),
  B(L("Why the rules differ.", "Under the any player rule a cheaper second player who is 28 to 31 puts his club in the group. "
    + "The figures are smaller that way, by 11% to 31% for age and by 12% to 18% for the clause.")),
  B(L("With every category of trade held constant", "as well (the Section 5 regression), both findings stand: the clause under "
    + "both rules (p = 0.011 or less), and age under the main player rule (trade-day grade -1.07, p = 0.004; realized value "
    + "-1.36, p = 0.024) but not under the any player rule (p = 0.074 and 0.082).")),
  B(L("Grouped the simple way,", "clubs acquiring a player with a clause had a trade-day grade of -3.38 (0.63) and a realized "
    + "value of -2.92 (0.74) under the main player rule, and -2.95 (0.53) and -2.50 (0.65) under the any player rule; each "
    + "is statistically significant at the 5% level (p < 0.001).")));

// ==== 4 ====
add(H1("4. Teams Respond to Only About 40% of a Contract's Value"));
add(H2("How it was measured"));
add(B("Each main player's contract is split into two parts: the value of his forecasted performance over the rest of the "
  + "contract (with the seasons of continued team control included for restricted free agents), and the present value of "
  + "his cap hit over the seasons left."),
  B("The price the club paid for its main player alone is the models' value of everything it gave up, less the models' value "
    + "of everything else it received in the trade. A price belongs to one player, so this section uses the main player rule "
    + "only."),
  // v3.0 (Thomas: "the finding about how the trades respond to contract value shouldn't be changed"; "All trades, played
  // seasons"): every trade to March 2026, the correction instrumented by the seasons played
  B("This section uses every trade to March 2026. The price is set on trade day, and the correction below uses only the "
    + "seasons played, so no forecast enters it."),
  B("A market that priced contracts correctly would pay more for players on value contracts and less for overpaid players."),
  B(L("A correction for the models' own error:", "The models' values are estimates, and part of each is error. The price "
    + "cannot follow that error, so regressing the price on the models' value gives a smaller slope than the market's true "
    + "response. Two-stage least squares removes this in two steps. First, the models' value is regressed on what the "
    + "contract actually delivered in the seasons played through 2025-26; this keeps only the part of the models' value that "
    + "the player's real performance bears out. Second, the price is regressed on that part. The result says whether the low "
    + "response belongs to the market or to the models' error.")));
add(H2("Findings"));
add(LABEL("How much the price paid for a player moves for each $1 of his contract's two parts"));
add(table(["How the contract's two parts are measured", "Price change per $1 market value increase", "Price change per $1 more cap cost"], [
  ["The models' value on trade day", "+0.26 (0.11)\np = 0.017", "-0.27 (0.10)\np = 0.007"],
  ["What the contract delivered in the seasons played", "+0.18 (0.09)\np = 0.048", "-0.22 (0.09)\np = 0.014"],
  ["The models' value, corrected for its error (two-stage least squares)", "+0.39 (0.19)\np = 0.045", "-0.37 (0.16)\np = 0.028"],
], [46, 27, 27]));
add(NOTE("A market that priced contracts in full would move the price by +1.00 for each $1 of performance value and by -1.00 "
  + "for each $1 of cap cost. 886 clubs, all trades to March 2026. Standard errors in brackets, clustered by trade; for the "
  + "corrected row, standard errors and p-values by resampling trades. The p-values test against zero; against a full "
  + "dollar (+1 and -1), each corrected figure has p < 0.001. The cap cost is approximate (injured-reserve relief left out). "
  + "In 2017-22 alone the corrected figures are +0.34 (0.29) and -0.34 (0.21): not statistically different from zero "
  + "(p = 0.20 and 0.10), but statistically different from a full dollar (p = 0.023 and 0.001)."));
add(H2("What it means"));
add(B("About 40 cents is far below a full dollar, and the confidence interval excludes a full dollar, so the market does not "
  + "separate good contracts from bad ones by as much as it should."),
  B(L("This is why clubs selling players for picks and prospects come out ahead.", "In 2017-22 their trade-day grade is +1.54 "
    + "(0.18) and their realized value +0.91 (0.25). The players they sell are mostly on expensive contracts, and the buyers "
    + "do not charge enough for the cost. Once the cap hit of the player sold is held fixed, teams selling players for picks "
    + "and prospects get fair value (trade-day grade -0.13, p = 0.56; realized value -0.12, p = 0.79): the gain comes from "
    + "shedding the contract, not from taking picks and prospects.")),
  B(L("Cap dumps are the same pattern.", "In 23 trades in 2017-22 a club sent a player at $2.5M or more along with a pick or "
    + "prospect and took back no player at $1M or more. It attached $0.083M of picks and prospects for each $1M of cap "
    + "cleared [0.036, 0.157], and the club taking the contract came out behind (realized value -2.73 [-4.76, -0.82]).")));

// ==== 5 ====
add(H1("5. What Is Not Mispriced"));
add(H2("Categories of trades"));
// v3.0: on 2017-22; the trade-day grade with the other factors held constant beside the realized value; the restricted
// free agent and late picks in the regression (Thomas: "Well it really should be added to the regression"); groups_any.py
// v1.2 part 5; his row labels
add(table(["Group", "Rule", "Clubs", "Trade-day grade, alone", "Realized value, alone", "Trade-day grade, other factors held constant", "Realized value, other factors held constant"], [
  ["Team higher in the standings, last 14 days before the deadline", MR, "193", "-0.92 (0.13)\np < 0.001", "-0.54 (0.21)\np = 0.010", "-0.16 (0.17)\np = 0.34", "-0.14 (0.25)\np = 0.56"],
  ["", AR, "193", "-0.92 (0.13)\np < 0.001", "-0.54 (0.21)\np = 0.010", "-0.15 (0.17)\np = 0.38", "-0.17 (0.26)\np = 0.51"],
  ["Team retained salary", MR, "84", "+1.32 (0.36)\np < 0.001", "+0.98 (0.50)\np = 0.052", "-0.24 (0.41)\np = 0.55", "-0.02 (0.62)\np = 0.98"],
  ["", AR, "86", "+1.30 (0.35)\np < 0.001", "+1.03 (0.48)\np = 0.034", "-0.10 (0.49)\np = 0.83", "+0.25 (0.68)\np = 0.71"],
  ["Received a rental (final contract season, unrestricted, in season)", MR, "260", "-0.35 (0.09)\np < 0.001", "-0.16 (0.15)\np = 0.30", "+1.31 (0.25)\np < 0.001", "+1.20 (0.44)\np = 0.006"],
  ["", AR, "265", "-0.33 (0.09)\np < 0.001", "-0.08 (0.16)\np = 0.60", "+1.27 (0.24)\np < 0.001", "+1.35 (0.48)\np = 0.005"],
  ["Received a defenceman", MR, "181", "-0.99 (0.24)\np < 0.001", "-1.00 (0.31)\np = 0.001", "-0.52 (0.26)\np = 0.048", "-1.12 (0.40)\np = 0.005"],
  ["", AR, "194", "-0.81 (0.21)\np < 0.001", "-0.74 (0.27)\np = 0.006", "-0.42 (0.27)\np = 0.12", "-0.83 (0.37)\np = 0.026"],
  ["Received a former top-15 pick below the top-15 average, D+5 or later", MR, "56", "-1.44 (0.66)\np = 0.029", "-1.11 (0.78)\np = 0.16", "-0.68 (0.57)\np = 0.23", "-0.43 (0.77)\np = 0.58"],
  ["", AR, "60", "-1.02 (0.65)\np = 0.12", "-1.32 (0.80)\np = 0.10", "-0.48 (0.57)\np = 0.40", "-0.99 (0.83)\np = 0.23"],
  ["Received a restricted free agent in his final contract season", MR, "55", "+0.78 (0.34)\np = 0.021", "+0.45 (0.45)\np = 0.31", "+1.40 (0.30)\np < 0.001", "+0.83 (0.58)\np = 0.15"],
  ["", AR, "58", "+0.49 (0.26)\np = 0.060", "+0.45 (0.42)\np = 0.29", "+1.33 (0.33)\np < 0.001", "+1.16 (0.61)\np = 0.057"],
  ["Received only picks in rounds 6 and 7", MR, "77", "+0.08 (0.08)\np = 0.31", "-0.07 (0.19)\np = 0.73", "-0.79 (0.22)\np < 0.001", "-0.83 (0.36)\np = 0.022"],
  ["", AR, "77", "+0.08 (0.08)\np = 0.31", "-0.07 (0.19)\np = 0.73", "-0.79 (0.21)\np < 0.001", "-0.72 (0.36)\np = 0.046"],
  ["Received one asset for two or more", MR, "178", "-1.40 (0.22)\np < 0.001", "-0.48 (0.37)\np = 0.19", "-0.65 (0.19)\np < 0.001", "+0.04 (0.40)\np = 0.92"],
  ["", AR, "178", "-1.40 (0.22)\np < 0.001", "-0.48 (0.37)\np = 0.19", "-0.66 (0.20)\np = 0.001", "+0.04 (0.40)\np = 0.92"],
  ["Sold under a new general manager, his predecessor's contract", MR, "65", "+1.69 (0.52)\np = 0.001", "+0.36 (0.68)\np = 0.60", "+0.51 (0.49)\np = 0.30", "-0.86 (0.76)\np = 0.26"],
  ["", AR, "65", "+1.69 (0.52)\np = 0.001", "+0.36 (0.68)\np = 0.60", "+0.63 (0.56)\np = 0.26", "-0.75 (0.81)\np = 0.36"],
], [22, 16, 6, 14, 14, 14, 14]));
add(NOTE("$M a club; positive means the club gained. \"Alone\": the group's average, standard errors clustered by trade. "
  + "\"Other factors held constant\": every category in one regression, each built by the row's rule, robust standard "
  + "errors. For the three groups not about a player, only the held-constant columns differ between the rules, because the "
  + "other categories in the regression change. Standard errors in brackets."));
add(B(L("The deadline-buying and retained-salary results", "disappear once the player taken and the picks given are held "
  + "fixed: with the other factors held constant, none of their figures is statistically significant.")),
  B(L("The rental result", "turns positive with other factors held constant because a rental is usually paid for with picks "
    + "and prospects, which the regression counts separately. Taken together, the usual deadline deal, a rental for picks "
    + "and prospects, is priced about even for the buyer (-0.18 [-0.65, +0.29] under the main player rule, -0.31 [-0.73, "
    + "+0.12] under the any player rule) and turns out about even (+0.30 [-0.43, +1.03] and +0.26 [-0.46, +0.98]).")),
  B(L("Defencemen.", "Under the main player rule, with the other factors held constant, clubs acquiring a defenceman pay more "
    + "on trade day (-0.52, p = 0.048) and lose value (-1.12, p = 0.005). In the Section 3 regression the trade-day grade "
    + "falls short of statistical significance (-0.73, p = 0.062), and under the any player rule it falls short in both "
    + "regressions (p = 0.12 and 0.16). Traded defencemen delivered their forecast (-0.02 WAR a season [-0.08, +0.04]) in "
    + "games, ice time and each part of WAR, and clubs acquiring one came out where their trade-day grade predicted "
    + "(realized minus predicted -0.02 [-0.42, +0.39]). Part of the gap is the comparison: clubs acquiring forwards came out "
    + "better than their grade (+0.47 [+0.19, +0.76]), mostly because they paid with picks, and picks under-deliver "
    + "(Section 2).")),
  B(L("Former top-15 picks below the top-15 average:", "The group is the main player received (main player rule), or any player "
    + "received (any player rule), who is a former top-15 pick and whose output five or more seasons after his draft (D+5 or "
    + "later) is below the average for top-15 picks at that stage (1.08 WAR a season). Across the league, 42% of 125 such "
    + "players later reached that average.")),
  B(L("Restricted free agents in their final contract season:", "With the other factors held constant, clubs acquiring one "
    + "gain on trade day under both rules, but the realized value is not statistically significant under either.")),
  B(L("Late picks:", "Each pick in rounds 6 and 7 is valued at $0.09M on trade day, on average, and delivers $0.09M less "
    + "(p = 0.001), so about nothing. Clubs whose whole return was late picks were neither ahead nor behind on their own. "
    + "With the other factors held constant the group is negative because it is measured beside the other categories its "
    + "clubs are in: 29 of its 77 clubs sold a player for those picks, and the regression credits a club selling a player for "
    + "picks and prospects with a gain (+1.32 on trade day, main player rule). The two together are +0.53 [-0.04, +1.10] on "
    + "trade day and -0.07 [-1.07, +0.93] realized: a player sold for late picks alone does not bring the seller's usual "
    + "gain. Most of the other 48 clubs swapped one pick for another.")),
  B(L("One asset for two or more, and a new general manager selling his predecessor's players:", "neither realized value is "
    + "statistically significant, alone or with the other factors held constant. The manager's group is the same under both "
    + "rules: no club in it sent a second player signed by the predecessor.")));
add(H2("Other characteristics in the Section 3 regressions"));
add(table(["Characteristic", "Rule", "Trade-day grade", "Realized value, WAR", "Realized value, Game Value"], [
  ["A former top-15 pick", MR, "-1.35 (0.64)\np = 0.034", "-1.55 (0.90)\np = 0.088", "-1.39 (0.97)\np = 0.15"],
  ["", AR, "-1.06 (0.68)\np = 0.12", "-1.36 (0.93)\np = 0.14", "-1.07 (1.02)\np = 0.30"],
  ["A player aged 32 or over", MR, "-1.02 (1.10)\np = 0.35", "-1.44 (1.26)\np = 0.25", "-1.60 (1.18)\np = 0.17"],
  ["", AR, "-0.79 (1.09)\np = 0.47", "-0.87 (1.30)\np = 0.50", "-1.29 (1.24)\np = 0.30"],
  ["A player with three or more seasons left", MR, "-2.48 (0.73)\np < 0.001", "-0.29 (1.06)\np = 0.79", "-0.58 (1.02)\np = 0.57"],
  ["", AR, "-2.29 (0.71)\np = 0.001", "-0.19 (1.05)\np = 0.85", "-0.73 (0.99)\np = 0.46"],
  ["Recent production: each extra WAR a season (WAR weighted 50/30/20 over the three most recent seasons)", MR, "-0.13 (0.66)\np = 0.85", "-0.21 (0.77)\np = 0.79", "+0.04 (0.63)\np = 0.95"],
  ["", AR, "+0.17 (0.71)\np = 0.81", "+0.04 (0.82)\np = 0.96", "+0.37 (0.71)\np = 0.60"],
  ["Recent production above the models' forecast for the season of the trade: each extra WAR", MR, "+0.04 (1.76)\np = 0.98", "+0.86 (2.26)\np = 0.70", "+0.03 (2.16)\np = 0.99"],
  ["", AR, "-1.42 (1.84)\np = 0.44", "+0.16 (2.34)\np = 0.95", "-0.70 (2.41)\np = 0.77"],
  ["Share of games played in the most recent season: all games against none", MR, "-0.88 (0.87)\np = 0.31", "-0.64 (0.92)\np = 0.49", "-1.42 (0.76)\np = 0.062"],
  ["", AR, "-1.00 (0.88)\np = 0.26", "-0.93 (0.90)\np = 0.30", "-1.75 (0.74)\np = 0.018"],
], [34, 17, 16, 17, 17]));
add(NOTE("Each figure is the change in the club's value for the characteristic, with the others held constant: for a yes-or-no "
  + "characteristic, against a club without it; for production, for each extra WAR a season. The same two regressions as "
  + "the Section 3 table, 431 clubs. Standard errors in brackets, clustered by trade."));
add(B(L("Former top-15 picks.", "Under the main player rule clubs pay more for them on trade day, but the realized value is not "
  + "statistically significant under either rule.")),
  B(L("Long contracts and players aged 32 or over.", "Clubs overpay on trade day for a player with three or more seasons left, "
    + "under both rules, but the realized value is not statistically significant. For players aged 32 or over no figure "
    + "is.")),
  B(L("A strong recent record, high production and a full share of games:", "Alone, under the main player rule, each predicts "
    + "a lower trade-day grade (-2.56 per WAR above the forecast, -0.81 per WAR of production, -2.24 for a full games share; "
    + "each statistically significant at the 5% level), but none does with the others held: their effect alone came from "
    + "the age and draft pedigree they overlap with. The games share keeps a realized effect on Game Value under the any "
    + "player rule only.")));
add(H2("Change over time"));
// v3.0: on 2017-22 (trend_both.py v1.1)
add(B(L("No change over time.", "There is found no difference in how efficiently teams transacted over time. From 2017-18 to "
  + "2021-22 the average size of the gap between the price paid and the models' value changed by +0.092 a season (0.094, "
  + "p = 0.33), and the gap in realized value by -0.051 a season (0.122, p = 0.67).")));

// ==== 6 ====
add(H1("6. How Far the Evidence Reaches"));
add(H2("The mispricing is captured by the model"));
add(B("No type of trade, on average, over- or under-performed the models' prediction in a statistically significant way: "
  + "across the sixteen groups tested, under either rule, each club's realized value compared with what its trade-day grade "
  + "predicted, on WAR and on Game Value, the smallest p-value is 0.063."));
add(H2("The limits"));
add(B(L("Realized values are partly forecasted.", "For these trades that is mostly picks and prospects who have not yet reached "
  + "the NHL, and contracts that run past 2025-26.")),
  B(L("Regular-season wins only.", "A contender's playoff run is outside the currency.")),
  B(L("A shared dollar rate.", "The forecast and the realized value convert wins to dollars on the same price line. Game Value "
    + "removes the shared performance measure, not the shared rate.")),
  B(L("Game Value is weaker on defence.", "It agrees with the WAR-based forecast at r = 0.65 for forwards and r = 0.30 for "
    + "defencemen.")),
  B(L("Traded assets only.", "Only traded assets are observed, apart from the top-15 picks check, and conditional picks are "
    + "valued as unconditional (94 trades).")));

const doc = new Document({
  creator: "xNPV", title: "Findings",
  styles: {
    default: { document: { run: { font: FONT, size: 20 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", run: { font: FONT, size: 36, bold: true }, paragraph: { spacing: { before: 0, after: 160 }, keepNext: true } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 26, bold: true, color: "1F3864" }, paragraph: { spacing: { before: 300, after: 80 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 21, bold: true, color: "404040" }, paragraph: { spacing: { before: 140, after: 60 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "bullets", levels: [
    { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 260 } } } },
    { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 260 } } } },
  ] }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [T("", {}), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16 })] })] }) },
    children: body,
  }],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUTFILE, buf); console.log(VERSION + " wrote " + OUTFILE); });
