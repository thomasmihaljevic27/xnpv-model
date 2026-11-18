// findings_doc.js v2.1 -- builds "Trade Back-test, What We Found and How, revised.docx" (40_DOCS/); v2.0 built "Trade
// Back-test, What We Found and How.docx" (Thomas's commented copy of it is kept in git); v1.x "Back-test Findings and Methods.docx".
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
const VERSION = "findings_doc.js v2.4";

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
add(H1("1. How a Finding Is Made"));
add(H2("Step 1: grade every trade on trade day"));
add(B("Every player, pick and prospect in a trade gets a dollar value from the models, using only what was known that day. "
  + "This value is its expected net present value (xNPV)."),
  B(L("A player's value", "is what his forecasted performance is worth on the market, less what he costs against the cap, "
    + "over the rest of his contract, with the seasons of continued team control included for restricted free agents.")),
  B(L("A pick's or a prospect's value", "is what a pick in that spot, or a prospect with that record, has typically turned into.")),
  B("For each club: what it received less what it gave up. That is the club's trade-day grade. Positive means it got more "
    + "value than it gave; negative means it paid too much. The two clubs' grades always sum to zero."));
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
  B("Seasons from 2026-27 on have not been played yet, so for those the realized value uses the models' forecast. A pick is "
    + "followed to the player drafted with it; a pick or prospect who has not reached the NHL by 2026-27 is valued again by "
    + "the appropriate model."));
add(H2("Step 3: look at categories of trades"));
add(B("Take every club that made the same type of trade, for example acquired a player aged 28 to 31, and average their "
  + "trade-day grades and their realized values."),
  B("Standard errors are clustered by trade."));
add(H2("Step 4: make sure it is not something else in disguise"));
add(B("Characteristics overlap. A club acquiring a 30-year-old at the trade deadline might also take on a clause and give up "
  + "picks. A regression puts all the characteristics in at once, so each one's effect is measured with the others held "
  + "fixed. A characteristic that matters alone but fades here was standing in for something else."));
add(H2("Step 5: try to break each finding"));
add(B(L("Fresh trades.", "Does the finding hold on the trades after March 2022, which were not in the sample of trades in which "
  + "it was first found?")),
  B(L("A second performance measure.", "Does it hold when performance is measured with Game Value instead of WAR?")),
  B(L("Played seasons only.", "Does it hold when a club's realized value counts only the seasons played through 2025-26, with "
    + "no model projection of the seasons after?")));
add(H2("Step 6: price and realized value"));
add(B("A finding must show in both the trade-day grade and the realized value. A gap that shows in the trade-day grade only "
  + "is reported as not a finding."));

// ==== 2 ====
add(H1("2. The Models Predict How Trades Turn Out"));
add(ANSWER("The club the models favour on trade day comes out ahead in about 57% to 61% of trades."));
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
add(B("Each club's main player is the player with the highest cap hit it received. A club joins a group through its main "
  + "player only: for example, a club is in the former top-15 pick group when its main player is a former top-15 pick, not "
  + "when a former top-15 pick came with a more expensive player. Of the 1,152 clubs that received a player, 1,026 received "
  + "only one; the rule decides the main player for the other 126. The clause is the exception: a club is in the clause "
  + "group when any player it received has a no-trade or no-move clause."),
  B("The club's trade-day grade and its realized value are each regressed on the main player's characteristics: age, "
    + "position, clause, signed as an unrestricted free agent, seasons left, production (his recent WAR, weighted 50/30/20 "
    + "across his three most recent seasons), how much his production exceeds its forecast, his share of games played in the "
    + "most recent season, and whether he is a former top-15 pick (chosen 15th overall or earlier in the NHL draft)."),
  B("His cap hit is left out on purpose. A contract's value is already its performance value less its cap hit, so \"clubs "
    + "overpay for expensive players\" would restate the models' own definition."));
add(H2("Findings"));
add(table(["Club acquiring a main player who is", "Trade-day grade", "Realized value, WAR", "Realized value, Game Value",
  "Realized value, WAR, 2017-22, played seasons only", "Realized value, WAR, after 2022"], [
  ["Aged 28 to 31", "-1.60 (0.44)\np < 0.001", "-1.78 (0.61)\np = 0.003", "-1.74 (0.62)\np = 0.005", "-2.07 (0.90)\np = 0.021", "-0.82 (0.57)\np = 0.152"],
  ["With a clause (any player received)", "-1.69 (0.50)\np < 0.001", "-1.55 (0.53)\np = 0.003", "-1.49 (0.61)\np = 0.015", "-1.94 (0.89)\np = 0.029", "-1.22 (0.50)\np = 0.015"],
  ["A former top-15 pick", "-1.53 (0.45)\np < 0.001", "-1.52 (0.58)\np = 0.008", "-1.62 (0.63)\np = 0.010", "-1.37 (0.85)\np = 0.108", "-1.50 (0.54)\np = 0.006"],
], [26, 14, 14, 15, 17, 14]));
add(NOTE("Figures in millions of dollars as of the 2025-26 salary cap. Negative means the club paid more than the models' value "
  + "(trade-day grade) or lost value (realized value). Standard errors in brackets, clustered by trade. All characteristics "
  + "are in the regression together; the other terms are in Section 5. 735 clubs (540 trades) for all trades; 431 for "
  + "2017-22; 304 after 2022."));
add(B(L("The clause and former top-15 pick findings", "hold in both the trade-day grade and the realized value on the trades "
  + "after 2022 alone, and on played seasons only across all trades. On played seasons in 2017-22 alone, the former top-15 "
  + "pick realized value is about the same size (-1.37) but not statistically significant (p = 0.11).")),
  B(L("The age 28 to 31 finding", "holds in both in 2017-22 and on played seasons only. On the trades after 2022 the overpay "
    + "result replicates (trade-day grade -1.24, p = 0.039); the realized value (-0.82) points the same way but is not yet "
    + "statistically significant, as those trades have fewer seasons played.")),
  B(L("Without the main-player rule.", "If each characteristic counts when any player the club received has it, the three "
    + "findings keep their direction and statistical significance on all trades: aged 28 to 31, trade-day grade -1.30 and "
    + "realized value -1.28; former top-15 pick, -1.30 and -1.29; clause, -1.80 and -1.71. The age and draft pedigree figures "
    + "are about a fifth smaller, and the age 28 to 31 realized value on played seasons in 2017-22 is no longer statistically "
    + "significant (-1.35, p = 0.16). Only 78 of the 735 clubs received two or more players.")),
  B(L("Grouped the simple way,", "2017-22: clubs acquiring a player aged 28 to 31 had a trade-day grade of -1.56 (0.31) and a "
    + "realized value of -1.49 (0.44); clubs acquiring a clause player, -2.95 (0.53) and -2.50 (0.65). Each is statistically "
    + "significant at the 5% level (p = 0.001 or less). The clause group was declared before the main test was first run.")));
add(H2("What it means"));
add(B("Clubs pay for the name, the draft pedigree and the past, more than for what the player is likely to deliver next."),
  B("Each of the three findings holds with the others fixed: paying more for a 29-year-old is separate from paying more for a "
    + "former high pick or for a clause."));

// ==== 4 ====
add(H1("4. Teams Respond to Only About 40% of a Contract's Value"));
add(ANSWER("Teams only respond to mispriced contracts by about 40%: for every dollar of mispricing on a contract, the trade "
  + "price only moves by about 40 cents. Bargain contracts sell for too little, and bad contracts for too much."));
add(H2("How it was measured"));
add(B("Each main player's contract is split into two parts: the value of his forecasted performance over the rest of the "
  + "contract (with the seasons of continued team control included for restricted free agents), and the present value of "
  + "his cap hit over the seasons left."),
  B("The price the club paid for its main player alone is the models' value of everything it gave up, less the models' value "
    + "of everything else it received in the trade."),
  B("A market that priced contracts correctly would pay more for players on value contracts and less for overpaid players."),
  B(L("A correction for the models' own error.", "The models' values are estimates, and part of each is error. The price "
    + "cannot follow that error, so regressing the price on the models' value gives a smaller slope than the market's true "
    + "response. Two-stage least squares removes this in two steps. First, the models' value is regressed on what the "
    + "contract actually delivered; this keeps only the part of the models' value that the player's real performance bears "
    + "out. Second, the price is regressed on that part. The result says whether the low response belongs to the market or "
    + "to the models' error.")));
add(H2("Findings"));
add(table(["Price paid, per $1 of", "Performance value", "Cap cost"], [
  ["The models' value", "+0.26 (0.11)\np = 0.017", "-0.27 (0.10)\np = 0.007"],
  ["What the contract actually delivered", "+0.19 (0.09)\np = 0.027", "-0.23 (0.09)\np = 0.008"],
  ["The models' value, corrected for its error", "+0.41 (0.18)\np = 0.030", "-0.39 (0.15)\np = 0.020"],
  ["The same, using played seasons only for the correction", "+0.39 (0.19)\np = 0.045", "-0.37 (0.16)\np = 0.028"],
], [52, 24, 24]));
add(NOTE("886 clubs, all trades. Standard errors in brackets, clustered by trade; for the corrected rows, standard errors and "
  + "p-values by resampling trades. The p-values test against zero; against a full dollar (+1 and -1), each corrected figure "
  + "has p = 0.001 or less. The cap cost is approximate (injured-reserve relief left out). In 2017-22 alone the corrected "
  + "figures are +0.33 (0.29) and -0.33 (0.21): not statistically different from zero (p = 0.24 and 0.14), but statistically "
  + "different from a full dollar (p = 0.012 and 0.001)."));
add(H2("What it means"));
add(B("About 40 cents is far below a full dollar, and the confidence interval excludes a full dollar, so the market does not "
  + "separate good contracts from bad ones by as much as it should."),
  B(L("This is why clubs selling players for picks and prospects come out ahead.", "Their trade-day grade is +1.54 (0.18) and "
    + "their realized value +0.91 (0.25) in 2017-22, and +0.77 (0.22) after 2022. The players they sell are mostly on "
    + "expensive contracts, and the buyers do not charge enough for the cost. Once the cap hit of the player sold is held "
    + "fixed, selling for picks and prospects gains nothing extra (-0.10, not statistically significant): the gain comes from "
    + "the contract shed, not from taking picks and prospects.")),
  B(L("Cap dumps are the same pattern.", "In 43 trades a club sent a player at $2.5M or more with a pick or prospect and took "
    + "back no player at $1M or more. It attached $0.096M of picks and prospects for each $1M of cap cleared [0.057, 0.154], "
    + "and the club taking the contract came out behind.")));

// ==== 5 ====
add(H1("5. What Is Not Mispriced"));
add(H2("Categories of trades"));
add(table(["Group", "Clubs", "Trade-day grade, alone", "Realized value, alone", "Realized value, others held"], [
  ["Higher in the standings, last 14 days before the deadline", "193", "-0.92 (0.13)\np < 0.001", "-0.54 (0.21)\np = 0.010", "+0.01 (0.17)\np = 0.94"],
  ["Retained salary", "86", "+1.30 (0.35)\np < 0.001", "+1.03 (0.48)\np = 0.034", "+0.27 (0.49)\np = 0.62"],
  ["Received a rental (final season, unrestricted, in season)", "260", "-0.35 (0.09)\np < 0.001", "-0.16 (0.15)\np = 0.30", "+0.93 (0.29)\np = 0.002"],
  ["Main player a defenceman", "181", "-0.99 (0.24)\np < 0.001", "-1.00 (0.31)\np = 0.001", "-0.82 (0.29)\np = 0.002"],
  ["Main player a former top-15 pick below the top-15 average, D+5 or later", "60", "-1.02 (0.65)\np = 0.12", "-1.32 (0.80)\np = 0.10", "-0.96 (0.52)\np = 0.057"],
  ["Received one asset for two or more", "178", "-1.40 (0.22)\np < 0.001", "-0.48 (0.37)\np = 0.19", "-0.08 (0.27)\np = 0.77"],
  ["Sold under a new general manager, his predecessor's contract", "65", "+1.69 (0.52)\np = 0.001", "+0.36 (0.68)\np = 0.60", "-0.12 (0.54)\np = 0.83"],
], [36, 8, 18, 18, 20]));
add(NOTE("$M a club; positive means the club gained. \"Alone\": the group's average, 2017-22. \"Others held\": all characteristics "
  + "in one regression, all trades. Standard errors in brackets, clustered by trade."));
add(B(L("The deadline-buying and retained-salary results", "disappear once the player taken and the picks given are held "
  + "fixed: alone, each realized value is statistically significant; with the others held, neither is.")),
  B(L("The rental result", "turns positive with the others held (+0.93) because a rental is usually paid for with picks and "
    + "prospects, which the regression counts separately (across trades the two are linked at a correlation of 0.50 in size). "
    + "Taken together, the usual deadline deal, a rental for picks and prospects, is priced about even for the buyer (+0.02 "
    + "[-0.36, +0.38]) and turns out about even (+0.47 [-0.04, +1.03]).")),
  B(L("The defenceman result", "is not a mispricing of defencemen. With the others held, the trade-day grade is not "
    + "statistically significant (-0.29, p = 0.17); the realized value stays negative. That gap is not in the defencemen: "
    + "traded defencemen delivered their forecast (-0.02 WAR a season [-0.08, +0.04]) in games, ice time and each part of "
    + "WAR, and clubs acquiring one came out where their trade-day grade predicted (realized minus predicted -0.02 [-0.42, "
    + "+0.39], 2017-22). It shows because the comparison is clubs acquiring forwards, who came out better than their grade "
    + "(+0.47 [+0.19, +0.76]), mostly because they paid with picks, and picks under-deliver (Section 2).")),
  B(L("Former top-15 picks below the top-15 average.", "The group is a former top-15 pick whose output five or more seasons "
    + "after his draft (D+5 or later) is below the average for top-15 picks at that stage (1.08 WAR a season). Neither its "
    + "trade-day grade nor its realized value is statistically significant. Across the league, 42% of 125 such players later "
    + "reached that average.")),
  B(L("One asset for two or more, and a new general manager selling his predecessor's players:", "the trade-day grade differs "
    + "from zero, but the realized value is not statistically significant, alone or with the others held.")));
add(H2("Other characteristics in the Section 3 regression"));
add(table(["Club acquiring a main player", "Trade-day grade", "Realized value, WAR", "Realized value, Game Value"], [
  ["Aged 32 or over", "-2.03 (0.60)\np < 0.001", "-1.17 (0.65)\np = 0.070", "-1.45 (0.65)\np = 0.026"],
  ["With three or more seasons left", "-2.71 (0.58)\np < 0.001", "-0.20 (0.74)\np = 0.78", "-0.57 (0.71)\np = 0.42"],
  ["Production, per WAR", "+0.05 (0.48)\np = 0.91", "-0.40 (0.54)\np = 0.46", "+0.06 (0.46)\np = 0.89"],
  ["Production above its forecast, per WAR", "-0.30 (1.36)\np = 0.83", "+1.29 (1.62)\np = 0.43", "+0.07 (1.54)\np = 0.96"],
  ["Games share in the most recent season (all games = 1)", "-0.26 (0.61)\np = 0.67", "-0.41 (0.58)\np = 0.48", "-1.02 (0.49)\np = 0.038"],
], [40, 20, 20, 20]));
add(NOTE("The same regression as the Section 3 table, all trades, 735 clubs. Standard errors in brackets, clustered by trade."));
add(B(L("Players aged 32 or over.", "Clubs overpay for them (trade-day grade -2.03), but the realized value is statistically "
  + "significant on Game Value only, not on WAR.")),
  B(L("Long contracts.", "Clubs overpay on trade day for a player with three or more seasons left (-2.71), but the realized "
    + "value is small and not statistically significant (-0.20).")),
  B(L("A strong recent record, high production and a full share of games.", "Alone, each predicts a lower trade-day grade "
    + "(-2.31 per WAR above the forecast, -0.70 per WAR of production, -1.74 for a full games share; p = 0.001 or less each), "
    + "but none does with the others held: their effect alone came from the age and draft pedigree they overlap with. The "
    + "games share keeps a realized effect on Game Value only.")));
add(H2("Other categories"));
add(B(L("Late picks.", "Picks in rounds 6 and 7 are valued at $0.09M each on trade day, on average, and deliver $0.09M less "
  + "(p = 0.001), so about nothing. The amounts are too small to matter: clubs whose whole return was late picks were neither "
  + "ahead nor behind (realized value -0.07, p = 0.79).")),
  B(L("Restricted free agents in their final contract season:", "realized value +0.45 [-0.33, +1.42], not statistically "
    + "significant.")),
  B(L("No change over time.", "We found no difference in how efficiently teams transacted over time. The average size of the "
    + "gap between the price paid and the models' value changed by -0.019 a season [-0.084, +0.052] from 2017-18 to 2025-26, "
    + "which is not statistically significant. This uses trade-day grades only, which are complete for every trade.")));

// ==== 6 ====
add(H1("6. How Far the Evidence Reaches"));
add(H2("The mispricing is captured by the model"));
add(B("No type of trade, on average, over- or under-performed the models' prediction in a statistically significant way: "
  + "across the fourteen groups tested in 2017-22, each club's realized value compared with what its trade-day grade "
  + "predicted, on WAR and on Game Value, the smallest p-value is 0.063."));
add(H2("The limits"));
add(B(L("Recent realized values are part forecast.", "Picks and prospects traded after 2022 have mostly not reached the NHL, so "
  + "their realized values rest partly on the models.")),
  B(L("How term is priced.", "Each year of term adds 0.89% of the cap ($0.851M) to a season's value, and each season counts the "
    + "term left on the contract, not the term it was signed for, because longer contracts out-perform their forecast by only "
    + "9% to 20% of that premium. The choice matters for the realized values: with each season priced on the term signed, 49 "
    + "of the 52 trade-day grades by group that are statistically significant stay so, but only 5 of the 30 realized values "
    + "on WAR. The regression in Section 3 has not been re-run that way.")),
  B(L("Declared and found.", "The clause group and the clubs selling players for picks and prospects are groups declared "
    + "before the main test was first run, and both differ from zero in it. The age and draft pedigree results, and Section "
    + "4, were found after the first results were read; for those, replication on the trades after 2022 is the main defence "
    + "against chance.")),
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
