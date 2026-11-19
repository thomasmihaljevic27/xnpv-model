// findings_doc.js v2.1 -- builds "Trade Back-test, What We Found and How, revised.docx" (40_DOCS/); v2.0 built "Trade
// Back-test, What We Found and How.docx" (Thomas's commented copy of it is kept in git); v1.x "Back-test Findings and Methods.docx".
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
const VERSION = "findings_doc.js v2.8";

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
const LABEL = (t) => new Paragraph({ keepNext: true, spacing: { before: 120, after: 60 }, children: [T(t, { bold: true })] });
add(H1("1. How a Finding Is Made"));
add(H2("Step 1: grade every trade on trade day"));
add(B("Every player, pick and prospect in a trade gets a dollar value from the models, using only what was known that day. "
  + "This value is its expected net present value (xNPV)."),
  B(L("A player's value", "is what his forecasted performance is worth on the market, less what he costs against the cap, "
    + "over the rest of his contract, with the seasons of continued team control included for restricted free agents.")),
  B(L("A pick's or a prospect's value", "is what a pick in that spot, or a prospect with that record, has typically turned into.")),
  // v2.8: Thomas's wording
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
// v2.8 (Thomas: "I think just generally this fits best in section 1"): the two rules, in his wording, moved from Section 3
add(B("A category is a type of trade, for example acquiring a player aged 28 to 31, or buying at the trade deadline. Each "
  + "club is either in a category or not."),
  B("There are two ways to categorize teams based on the trade, if the main player received in the trade met a certain "
    + "criterion, or if any player received in the trade met a certain criteria:"),
  B(L("Main player rule:", "a club is in a group when its main player has the characteristic; for example, it is in the "
    + "former top-15 pick group when its main player is a former top-15 pick. The main player is defined as the player with "
    + "the highest cap hit it received."), 1),
  B(L("Any player rule:", "a club is in a group when any player it received has the characteristic. Of the 735 clubs in "
    + "Section 3's regressions, only 78 received two or more players, so this method is a type of robustness check."), 1),
  B("Each result is reported under both rules. A category about a player sent, such as retained salary, uses the main "
    + "player sent (the highest cap hit) or any player sent. A category not about a player, such as buying at the deadline, "
    + "holds the same clubs under both rules."));
add(H2("Step 4: test each category on its own"));
add(B("For each category, the clubs in it are averaged twice: once on their trade-day grades and once on their realized "
  + "values."),
  B("Each average is tested against zero. A negative average trade-day grade means clubs making that type of trade paid more "
    + "than the models' value; a negative average realized value means they lost value."),
  B("The two clubs in a trade are mirror images of each other, so they are not two independent observations. Standard "
    + "errors are therefore clustered by trade: each trade counts once. A p-value below 0.05 means the average is "
    + "statistically significant at the 5% level."));
add(H2("Step 5: hold the other characteristics constant"));
add(B("Characteristics overlap. A club acquiring a 30-year-old at the trade deadline might also take on a clause and give up "
  + "picks. A regression puts all the characteristics in at once, so each one's effect is measured with the others held "
  + "fixed."),
  B("Two regressions are run on the same characteristics: one on the clubs' trade-day grades, the other on their realized "
    + "values. Each characteristic's coefficient is the difference it makes to a club's value with the other "
    + "characteristics held constant."),
  B(L("Section 3", "regresses the grade and the realized value of each club that received a player on the characteristics of "
    + "the players it received, with standard errors clustered by trade.")),
  B(L("Section 5", "takes each two-team trade once: the first club's value is regressed on the difference between the two "
    + "clubs' characteristics, with no constant, because the second club's value is the first club's with the sign "
    + "reversed. Each trade is one row, so its standard errors are robust ones.")));
add(H2("Step 6: what counts as a finding"));
add(B("A finding must show in both the trade-day grade and the realized value: the characteristic is statistically "
  + "significant at the 5% level in both regressions, with the same sign."));
add(H2("Step 7: try to break each finding"));
add(B(L("Fresh trades.", "Does the finding hold on the trades after March 2022, which were not in the sample of trades in which "
  + "it was first found?")),
  B(L("A second performance measure.", "Does it hold when performance is measured with Game Value instead of WAR?")),
  B(L("Played seasons only.", "Does it hold when a club's realized value counts only the seasons played through 2025-26, with "
    + "no model projection of the seasons after?")));

// ==== 2 ====
add(H1("2. The Models Predict How Trades Turn Out"));
add(table(["", "2017-22, WAR", "2017-22, Game Value", "All trades, WAR"], [
  ["Favoured club came out ahead", "57.1% [53.3, 61.1]\np = 0.001", "56.9% [52.9, 60.8]\np = 0.001", "60.7% [57.5, 63.9]\np < 0.001"],
  ["Slope of realized value on trade-day grade", "0.749 [0.553, 0.901]\np < 0.001", "0.731 [0.530, 0.957]\np < 0.001", "0.633 [0.463, 0.782]\np < 0.001"],
  ["R-squared", "0.309", "0.296", "0.262"],
], [34, 22, 24, 20]));
add(NOTE("The slope is how far a club's realized value moves for each $1 of its trade-day grade: 1 means the predicted gap "
  + "shows up in full on average, 0 that the grade predicts nothing. R-squared is the share of the variation in realized "
  + "values that the trade-day grades account for. The two answer different questions: the prediction is close to right on "
  + "average, but single trades scatter widely around it. 95% confidence intervals in square brackets; the p-values test the "
  + "share against 50% and the slope against zero."));
add(B(L("What it means.", "Creating one metric to evaluate players, picks and prospects works: about three-quarters of the gap "
  + "predicted on trade day shows up in the realized value, and the result is replicable when using an alternative metric to "
  + "evaluate performance.")),
  B(L("By type of asset (2017-22),", "realized minus predicted value per asset acquired: players +0.104 [-0.078, +0.294] (664 "
    + "assets); prospects +0.158 [-0.138, +0.521] (253); picks -0.188 [-0.330, -0.041] (633). Only picks fall short of their "
    + "prediction by a statistically significant amount.")));

// ==== 3 ====
add(H1("3. Clubs Overpay for Players Aged 28 to 31, Former Top-15 Picks and Players with Contract Clauses"));
add(H2("How it was measured"));
add(B("The club's trade-day grade and its realized value are each regressed on these characteristics: age, position, clause, "
  + "signed as an unrestricted free agent, seasons left on contract, production (recent WAR, weighted 50/30/20 across the "
  + "three most recent seasons), how much that production exceeds its forecast, the share of games played in the most "
  + "recent season, and whether a player is a former top-15 draft pick."),
  // v2.8 (Thomas: "Why not just actually do the analysis under both methods?"; the measures: "in the any player model it
  // should be your recommended option"): each rule applied to every characteristic (who_overpaid_any.py v1.2)
  B("Under the main player rule each characteristic is the main player's. Under the any player rule a yes-or-no "
    + "characteristic, such as the clause, counts when any player received has it; production and how much it exceeds its "
    + "forecast are totals over the players received, and the games share is their average, weighted by cap hit."),
  B("The cap hit is left out on purpose. A contract's value is already its performance value less its cap hit, so \"clubs "
    + "overpay for expensive players\" would be circular."));
add(H2("Findings"));
const S3HEAD = (who) => [who, "Trade-day grade", "Realized value, WAR", "Realized value, Game Value",
  "Realized value, WAR, 2017-22, played seasons only", "Realized value, WAR, after 2022"];
add(LABEL("By the main player rule"));
add(table(S3HEAD("Club whose main player acquired is"), [
  ["Aged 28 to 31", "-1.53 (0.43)\np < 0.001", "-1.72 (0.60)\np = 0.004", "-1.69 (0.62)\np = 0.006", "-1.96 (0.89)\np = 0.027", "-0.86 (0.57)\np = 0.13"],
  ["On a contract with a clause", "-2.04 (0.59)\np < 0.001", "-1.85 (0.63)\np = 0.003", "-1.73 (0.67)\np = 0.010", "-2.49 (1.05)\np = 0.017", "-1.10 (0.50)\np = 0.027"],
  ["A former top-15 pick", "-1.51 (0.45)\np < 0.001", "-1.50 (0.57)\np = 0.009", "-1.60 (0.62)\np = 0.010", "-1.34 (0.84)\np = 0.11", "-1.51 (0.54)\np = 0.005"],
], [26, 14, 14, 15, 17, 14]));
add(LABEL("By the any player rule"));
add(table(S3HEAD("Club acquiring any player who is"), [
  ["Aged 28 to 31", "-1.23 (0.47)\np = 0.008", "-1.25 (0.64)\np = 0.052", "-1.49 (0.68)\np = 0.029", "-1.39 (1.01)\np = 0.17", "-0.66 (0.51)\np = 0.20"],
  ["On a contract with a clause", "-1.80 (0.50)\np < 0.001", "-1.70 (0.54)\np = 0.002", "-1.55 (0.61)\np = 0.011", "-2.20 (0.91)\np = 0.015", "-1.20 (0.53)\np = 0.025"],
  ["A former top-15 pick", "-1.38 (0.46)\np = 0.003", "-1.32 (0.59)\np = 0.024", "-1.33 (0.66)\np = 0.045", "-1.15 (0.87)\np = 0.19", "-1.37 (0.51)\np = 0.007"],
], [26, 14, 14, 15, 17, 14]));
add(LABEL("The same regressions on other samples"));
add(table(["Club acquiring", "Rule", "Trade-day grade, after 2022", "Realized value, WAR, 2017-22", "Realized value, WAR, played seasons only, all trades"], [
  ["A player aged 28 to 31", "Main player rule", "-1.27 (0.60)\np = 0.034", "-2.31 (0.94)\np = 0.014", "-1.41 (0.56)\np = 0.012"],
  ["", "Any player rule", "-1.53 (0.55)\np = 0.005", "-1.69 (1.06)\np = 0.11", "-1.00 (0.60)\np = 0.098"],
  ["A player with a clause", "Main player rule", "-1.61 (0.68)\np = 0.017", "-2.64 (1.15)\np = 0.022", "-1.71 (0.57)\np = 0.003"],
  ["", "Any player rule", "-1.66 (0.68)\np = 0.014", "-2.20 (0.93)\np = 0.018", "-1.56 (0.51)\np = 0.002"],
  ["A former top-15 pick", "Main player rule", "-1.71 (0.63)\np = 0.007", "-1.55 (0.90)\np = 0.088", "-1.20 (0.52)\np = 0.022"],
  ["", "Any player rule", "-1.55 (0.60)\np = 0.011", "-1.35 (0.93)\np = 0.15", "-1.05 (0.54)\np = 0.052"],
], [22, 18, 20, 20, 20]));
add(NOTE("Figures in millions of dollars as of the 2025-26 salary cap. Negative means the club paid more than the models' value "
  + "(trade-day grade) or lost value (realized value). Standard errors in brackets, clustered by trade. All characteristics "
  + "are in each regression together; the other terms are in Section 5. 735 clubs (540 trades) for all trades; 431 for "
  + "2017-22; 304 after 2022."));
// v2.8 (Thomas: "kinda a slog to read"): one plain claim a bullet; the replication figures are in the third table
add(B(L("The clause finding", "holds in each test under both rules. Clubs that take on a player with a no-trade or no-move "
  + "clause pay more than the models' value and lose value: in 2017-22 alone, after 2022 alone, and on played seasons only.")),
  B(L("The former top-15 pick finding", "holds after 2022 alone under both rules. It is weaker on the earlier trades. In "
    + "2017-22 alone its realized value is not statistically significant under either rule (p = 0.088 and 0.15). On played "
    + "seasons only it is under the main player rule (p = 0.022) but not under the any player rule (p = 0.052).")),
  B(L("The age 28 to 31 finding", "depends on the rule. Under the main player rule clubs overpay and lose value in each test "
    + "except one: the realized value after 2022 alone (p = 0.13). Under the any player rule clubs overpay, but the realized "
    + "value is statistically significant only on Game Value (p = 0.029); on WAR it is not (p = 0.052).")),
  B(L("Why the rules differ.", "Under the any player rule a cheaper second player who is 28 to 31 or a former top-15 pick puts "
    + "his club in the group. The figures are smaller that way: by about a fifth to a quarter for age, and by about a tenth "
    + "for the clause and former top-15 picks.")),
  B(L("Grouped the simple way,", "2017-22: clubs acquiring a player with a clause had a trade-day grade of -3.38 (0.63) and a "
    + "realized value of -2.92 (0.74) under the main player rule, and -2.95 (0.53) and -2.50 (0.65) under the any player "
    + "rule; each is statistically significant at the 5% level (p < 0.001). The any player version was declared before the "
    + "main test was first run.")));
add(H2("What it means"));
add(B("Clubs pay for the name, the draft pedigree and the past, more than for what the player is likely to deliver in the "
  + "future."),
  B("Each of the three findings holds with the others fixed: paying more for a 29-year-old is separate from paying more for a "
    + "former high pick or for a clause."));

// ==== 4 ====
add(H1("4. Teams Respond to Only About 40% of a Contract's Value"));
add(H2("How it was measured"));
add(B("Each main player's contract is split into two parts: the value of his forecasted performance over the rest of the "
  + "contract (with the seasons of continued team control included for restricted free agents), and the present value of "
  + "his cap hit over the seasons left."),
  B("The price the club paid for its main player alone is the models' value of everything it gave up, less the models' value "
    + "of everything else it received in the trade. A price belongs to one player, so this section uses the main player rule "
    + "only."),
  B("A market that priced contracts correctly would pay more for players on value contracts and less for overpaid players."),
  B(L("A correction for the models' own error:", "The models' values are estimates, and part of each is error. The price "
    + "cannot follow that error, so regressing the price on the models' value gives a smaller slope than the market's true "
    + "response. Two-stage least squares removes this in two steps. First, the models' value is regressed on what the "
    + "contract actually delivered; this keeps only the part of the models' value that the player's real performance bears "
    + "out. Second, the price is regressed on that part. The result says whether the low response belongs to the market or "
    + "to the models' error.")));
add(H2("Findings"));
// v2.8 (Thomas: "it is unclear what this table is communicating just from looking at it"): a title, plain row and column
// names, and the full-response benchmark in the note
add(LABEL("How much the price paid for a player moves for each $1 of his contract's two parts"));
add(table(["How the contract's two parts are measured", "Price change per $1 more performance value", "Price change per $1 more cap cost"], [
  ["The models' value on trade day", "+0.26 (0.11)\np = 0.017", "-0.27 (0.10)\np = 0.007"],
  ["What the contract actually delivered", "+0.19 (0.09)\np = 0.027", "-0.23 (0.09)\np = 0.008"],
  ["The models' value, corrected for its error (two-stage least squares)", "+0.41 (0.18)\np = 0.030", "-0.39 (0.15)\np = 0.020"],
  ["The same, corrected using played seasons only", "+0.39 (0.19)\np = 0.045", "-0.37 (0.16)\np = 0.028"],
], [46, 27, 27]));
add(NOTE("A market that priced contracts in full would move the price by +1.00 for each $1 of performance value and by -1.00 "
  + "for each $1 of cap cost. 886 clubs, all trades. Standard errors in brackets, clustered by trade; for the corrected "
  + "rows, standard errors and p-values by resampling trades. The p-values test against zero; against a full dollar (+1 "
  + "and -1), each corrected figure has p = 0.001 or less. The cap cost is approximate (injured-reserve relief left out). In "
  + "2017-22 alone the corrected figures are +0.33 (0.29) and -0.33 (0.21): not statistically different from zero (p = 0.24 "
  + "and 0.14), but statistically different from a full dollar (p = 0.012 and 0.001)."));
add(H2("What it means"));
add(B("About 40 cents is far below a full dollar, and the confidence interval excludes a full dollar, so the market does not "
  + "separate good contracts from bad ones by as much as it should."),
  // v2.8: both values after 2022 (Thomas: "Is this trade day or realized? It should say both"); his "get fair value"
  B(L("This is why clubs selling players for picks and prospects come out ahead.", "Their trade-day grade is +1.54 (0.18) and "
    + "their realized value +0.91 (0.25) in 2017-22; after 2022 they are +1.20 (0.26) and +0.77 (0.22). The players they "
    + "sell are mostly on expensive contracts, and the buyers do not charge enough for the cost. Once the cap hit of the "
    + "player sold is held fixed, teams selling players for picks and prospects get fair value (all trades: trade-day grade "
    + "-0.14, p = 0.38; realized value -0.10, p = 0.73): the gain comes from shedding the contract, not from taking picks and "
    + "prospects.")),
  B(L("Cap dumps are the same pattern.", "In 43 trades a club sent a player at $2.5M or more with a pick or prospect and took "
    + "back no player at $1M or more. It attached $0.096M of picks and prospects for each $1M of cap cleared [0.057, 0.154], "
    + "and the club taking the contract came out behind.")));

// ==== 5 ====
add(H1("5. What Is Not Mispriced"));
add(H2("Categories of trades"));
// v2.8 (Thomas: "this could absolutely be split between the two model types"): each category under both rules
// (groups_any.py v1.1); late picks and final-season restricted free agents moved into the table
const MR = "Main player rule", AR = "Any player rule", NR = "Not in the regression";
add(table(["Group", "Rule", "Clubs", "Trade-day grade, alone", "Realized value, alone", "Realized value, other factors held constant"], [
  ["Higher in the standings, last 14 days before the deadline", MR, "193", "-0.92 (0.13)\np < 0.001", "-0.54 (0.21)\np = 0.010", "-0.01 (0.17)\np = 0.97"],
  ["", AR, "193", "-0.92 (0.13)\np < 0.001", "-0.54 (0.21)\np = 0.010", "+0.02 (0.18)\np = 0.89"],
  ["Kept part of the salary of a player it sent (retained salary)", MR, "84", "+1.32 (0.36)\np < 0.001", "+0.98 (0.50)\np = 0.052", "+0.11 (0.49)\np = 0.82"],
  ["", AR, "86", "+1.30 (0.35)\np < 0.001", "+1.03 (0.48)\np = 0.034", "+0.24 (0.51)\np = 0.64"],
  ["Received a rental (final season, unrestricted, in season)", MR, "260", "-0.35 (0.09)\np < 0.001", "-0.16 (0.15)\np = 0.30", "+0.90 (0.28)\np = 0.001"],
  ["", AR, "265", "-0.33 (0.09)\np < 0.001", "-0.08 (0.16)\np = 0.60", "+0.85 (0.30)\np = 0.005"],
  ["Received a defenceman", MR, "181", "-0.99 (0.24)\np < 0.001", "-1.00 (0.31)\np = 0.001", "-0.84 (0.29)\np = 0.004"],
  ["", AR, "194", "-0.81 (0.21)\np < 0.001", "-0.74 (0.27)\np = 0.006", "-0.70 (0.27)\np = 0.009"],
  ["Received a former top-15 pick below the top-15 average, D+5 or later", MR, "56", "-1.44 (0.66)\np = 0.029", "-1.11 (0.78)\np = 0.16", "-0.64 (0.50)\np = 0.21"],
  ["", AR, "60", "-1.02 (0.65)\np = 0.12", "-1.32 (0.80)\np = 0.10", "-0.98 (0.54)\np = 0.069"],
  ["Received a restricted free agent in his final contract season", MR, "55", "+0.78 (0.34)\np = 0.021", "+0.45 (0.45)\np = 0.31", NR],
  ["", AR, "58", "+0.49 (0.26)\np = 0.060", "+0.45 (0.42)\np = 0.29", NR],
  ["Received only picks in rounds 6 and 7", MR, "77", "+0.08 (0.08)\np = 0.31", "-0.07 (0.19)\np = 0.73", NR],
  ["", AR, "77", "+0.08 (0.08)\np = 0.31", "-0.07 (0.19)\np = 0.73", NR],
  ["Received one asset for two or more", MR, "178", "-1.40 (0.22)\np < 0.001", "-0.48 (0.37)\np = 0.19", "-0.06 (0.27)\np = 0.83"],
  ["", AR, "178", "-1.40 (0.22)\np < 0.001", "-0.48 (0.37)\np = 0.19", "-0.11 (0.27)\np = 0.70"],
  ["Sold under a new general manager, his predecessor's contract", MR, "65", "+1.69 (0.52)\np = 0.001", "+0.36 (0.68)\np = 0.60", "-0.13 (0.55)\np = 0.81"],
  ["", AR, "65", "+1.69 (0.52)\np = 0.001", "+0.36 (0.68)\np = 0.60", "-0.12 (0.57)\np = 0.83"],
], [27, 17, 7, 16, 16, 17]));
add(NOTE("$M a club; positive means the club gained. \"Alone\": the group's average, 2017-22. \"Other factors held constant\": "
  + "all categories in one regression, all trades, each built by the row's rule; the restricted free agent and late-pick "
  + "groups are not in it. Three groups are not about a player (the deadline, picks in rounds 6 and 7, and one asset for two "
  + "or more), so they hold the same clubs under both rules, and only their last column differs, because the other "
  + "categories in the regression change. Standard errors in brackets, clustered by trade."));
add(B(L("The deadline-buying and retained-salary results", "disappear once the player taken and the picks given are held "
  + "fixed. Alone, the deadline buyer's realized value is statistically significant, and so is retained salary's under the "
  + "any player rule (p = 0.034; main player rule p = 0.052); with the other factors held constant, none is.")),
  B(L("The rental result", "turns positive with other factors held constant (+0.90 under the main player rule, +0.85 under the "
    + "any player rule) because a rental is usually paid for with picks and prospects, which the regression counts "
    + "separately (across trades the two are linked at a correlation of 0.50 in size). Taken together, the usual deadline "
    + "deal, a rental for picks and prospects, is priced about even for the buyer (+0.02 [-0.36, +0.38]) and turns out about "
    + "even (+0.47 [-0.04, +1.03]).")),
  B(L("The defenceman result", "is not a mispricing of defencemen, under either rule. With the other factors held constant, the "
    + "trade-day grade is not statistically significant (main player rule -0.27, p = 0.20; any player rule -0.18, p = 0.38); "
    + "the realized value stays negative. That gap is not in the defencemen: traded defencemen delivered their forecast "
    + "(-0.02 WAR a season [-0.08, +0.04]) in games, ice time and each part of WAR, and clubs acquiring one came out where "
    + "their trade-day grade predicted (realized minus predicted -0.02 [-0.42, +0.39], 2017-22). It shows because the "
    + "comparison is clubs acquiring forwards, who came out better than their grade (+0.47 [+0.19, +0.76]), mostly because "
    + "they paid with picks, and picks under-deliver (Section 2).")),
  B(L("Former top-15 picks below the top-15 average:", "The group is the main player received (main player rule), or any player "
    + "received (any player rule), who is a former top-15 pick and whose output five or more seasons after his draft (D+5 or "
    + "later) is below the average for top-15 picks at that stage (1.08 WAR a season). Under the main player rule its "
    + "trade-day grade is statistically significant (-1.44, p = 0.029); under neither rule is its realized value. Across the "
    + "league, 42% of 125 such players later reached that average.")),
  B(L("Restricted free agents in their final contract season.", "Under the main player rule clubs acquiring one gain on trade "
    + "day (+0.78, p = 0.021); under neither rule is the realized value statistically significant.")),
  B(L("Late picks.", "Each pick in rounds 6 and 7 is valued at $0.09M on trade day, on average, and delivers $0.09M less "
    + "(p = 0.001), so about nothing. Clubs whose whole return was late picks were neither ahead nor behind.")),
  B(L("One asset for two or more, and a new general manager selling his predecessor's players:", "the trade-day grade differs "
    + "from zero, but the realized value is not statistically significant, alone or with the other factors held constant. "
    + "The manager's group is the same under both rules: no club in it sent a second player signed by the predecessor.")),
  // v2.8 (Thomas: "What still has none? What is none? Not a complete thought")
  B(L("Age, with every category in one regression.", "Clubs acquiring a player aged 28 to 31 lose value under both rules (main "
    + "player rule -1.07, p = 0.005; any player rule -0.96, p = 0.018). Clubs acquiring a player aged 32 or over do not lose "
    + "value by a statistically significant amount under either rule (-0.16, p = 0.74; -0.11, p = 0.82).")));
add(H2("Other characteristics in the Section 3 regressions"));
// v2.8 (Thomas: "What are we measuring about the main players production"): each measure named by what it is
add(table(["Characteristic", "Rule", "Trade-day grade", "Realized value, WAR", "Realized value, Game Value"], [
  ["A player aged 32 or over", MR, "-1.86 (0.68)\np = 0.006", "-1.03 (0.71)\np = 0.15", "-1.34 (0.70)\np = 0.055"],
  ["", AR, "-1.67 (0.66)\np = 0.011", "-0.53 (0.73)\np = 0.46", "-1.03 (0.70)\np = 0.14"],
  ["A player with three or more seasons left", MR, "-2.67 (0.57)\np < 0.001", "-0.17 (0.73)\np = 0.81", "-0.54 (0.70)\np = 0.44"],
  ["", AR, "-2.62 (0.56)\np < 0.001", "-0.19 (0.71)\np = 0.79", "-0.68 (0.68)\np = 0.32"],
  ["Recent production: each extra WAR a season (WAR weighted 50/30/20 over the three most recent seasons)", MR, "+0.06 (0.48)\np = 0.90", "-0.39 (0.54)\np = 0.47", "+0.07 (0.46)\np = 0.88"],
  ["", AR, "+0.29 (0.41)\np = 0.48", "-0.05 (0.51)\np = 0.93", "+0.17 (0.50)\np = 0.73"],
  ["Recent production above the models' forecast for the season of the trade: each extra WAR", MR, "-0.29 (1.36)\np = 0.83", "+1.29 (1.62)\np = 0.43", "+0.07 (1.54)\np = 0.96"],
  ["", AR, "-1.46 (1.08)\np = 0.18", "+0.32 (1.59)\np = 0.84", "-0.24 (1.65)\np = 0.89"],
  ["Share of games played in the most recent season: all games against none", MR, "-0.20 (0.59)\np = 0.73", "-0.36 (0.56)\np = 0.52", "-0.98 (0.47)\np = 0.039"],
  ["", AR, "-0.22 (0.56)\np = 0.70", "-0.62 (0.52)\np = 0.23", "-1.14 (0.44)\np = 0.010"],
], [34, 17, 16, 17, 17]));
add(NOTE("Each figure is the change in the club's value for the characteristic, with the others held constant: for a yes-or-no "
  + "characteristic, against a club without it; for production, for each extra WAR a season. Under the main player rule "
  + "each measure is the main player's; under the any player rule, the total over the players received (the games share: "
  + "their average, weighted by cap hit). The same two regressions as the Section 3 tables, all trades, 735 clubs. Standard "
  + "errors in brackets, clustered by trade."));
add(B(L("Players aged 32 or over.", "Clubs overpay for them under both rules (trade-day grade -1.86 and -1.67). The realized "
  + "value is not statistically significant on either measure under either rule (the smallest p-value is 0.055).")),
  B(L("Long contracts.", "Clubs overpay on trade day for a player with three or more seasons left (-2.67 and -2.62), but the "
    + "realized value is small and not statistically significant under either rule.")),
  B(L("A strong recent record, high production and a full share of games.", "Alone, under the main player rule, each predicts a "
    + "lower trade-day grade (-2.31 per WAR above the forecast, -0.70 per WAR of production, -1.74 for a full games share; "
    + "p = 0.001 or less each), but none does with the others held: their effect alone came from the age and draft pedigree "
    + "they overlap with. The games share keeps a realized effect on Game Value only, under both rules.")));
add(H2("Change over time"));
// v2.8: his wording; the p-value (Thomas: "Need that p value") and the realized value beside the trade-day grade (Thomas:
// "Why not use both?"), trend_both.py v1.0
add(B(L("No change over time.", "There is found no difference in how efficiently teams transacted over time. The average size "
  + "of the gap between the price paid and the models' value changed by -0.019 a season [-0.084, +0.052] from 2017-18 to "
  + "2025-26, which is not statistically significant (p = 0.58).")),
  B(L("On the realized value", "the gap shrinks by 0.132 a season (0.047, p = 0.005), from 2.21 for the 2017-18 trades to 0.45 for "
    + "the 2025-26 trades. That decline is expected whatever clubs did: the more recent a trade, the more of its realized "
    + "value is the models' own forecast, and the fewer seasons its assets have had to turn out better or worse than "
    + "predicted.")));

// ==== 6 ====
add(H1("6. How Far the Evidence Reaches"));
add(H2("The mispricing is captured by the model"));
add(B("No type of trade, on average, over- or under-performed the models' prediction in a statistically significant way: "
  + "across the sixteen groups tested in 2017-22, under either rule, each club's realized value compared with what its "
  + "trade-day grade predicted, on WAR and on Game Value, the smallest p-value is 0.063."));
add(H2("The limits"));
add(B(L("Recent realized values are partly forecasted.", "Picks and prospects traded after 2022 have mostly not reached the NHL, "
  + "so their values rest partly from the models.")),
  B(L("Regular-season wins only.", "A contender's playoff run is outside the currency.")),
  B(L("A shared dollar rate.", "The forecast and the realized value convert wins to dollars on the same price line. Game Value "
    + "removes the shared performance measure, not the shared rate.")),
  B(L("Game Value is weaker on defence.", "It agrees with the WAR-based forecast at r = 0.65 for forwards and r = 0.30 for "
    + "defencemen.")),
  B(L("Traded assets only.", "Only traded assets are observed, apart from the top-15 picks check, and conditional picks are "
    + "valued as unconditional (94 trades in 2017-22).")));

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
