// findings_doc.js v2.0 -- builds "Trade Back-test, What We Found and How.docx" (40_DOCS/); v1.x built "Back-test Findings and Methods.docx".
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
const OUTFILE = process.env.DOC_OUT || path.join(ROOT, "40_DOCS", "Trade Back-test, What We Found and How.docx")   // v2.0: a new file (the v1 file was open in Word);
const FONT = "Arial";
const VERSION = "findings_doc.js v2.0";

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
      children: [T(text, { size: 17, bold: header })] })],
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

add(new Paragraph({ heading: HeadingLevel.TITLE, children: [T("Trade Back-test: What We Found and How")] }));
add(B(L("What this covers.", "How each finding about the NHL trade market was made, and what the findings are. Each section "
  + "opens with its answer in bold, then shows how it was measured and the numbers behind it.")),
  B(L("Money.", "Millions of dollars at the 2025-26 salary cap ($95.5M), per club in a trade, unless a line says otherwise.")),
  B(L("Reading the statistics.", "A figure in brackets after an estimate, such as -1.56 (0.31), is its standard error: the "
    + "typical size of the estimate's error. A range in square brackets, such as [53.3, 61.1], is a 95% interval: the range "
    + "the true value very likely sits in. A star (*) means statistically significant at the 5% level: a gap this large would "
    + "turn up by luck less than one time in twenty.")));

// ==== 1 ====
add(H1("1. How a Finding Is Made"));
add(H2("Step 1: grade every trade on trade day"));
add(B("Every player, pick and prospect in a trade gets a dollar value from the models, using only what was known that day. "
  + "This value is its expected net present value (xNPV)."),
  B(L("A player's value", "is what his forecasted performance is worth on the market, less what he costs against the cap, "
    + "over the rest of his contract and the control seasons after it.")),
  B(L("A pick's or a prospect's value", "is what a pick in that spot, or a prospect with that record, has typically turned into.")),
  B("For each club: what it received less what it gave up. That is the club's trade-day grade. Positive means it got more "
    + "value than it gave; negative means it paid too much. The two clubs' grades always cancel out."));
add(H2("Step 2: see how each trade actually turned out"));
add(B("Each asset is followed after the trade, whoever held it later, and what it actually delivered is valued at the same "
  + "prices. That gives each club a result."),
  B(L("One season's value", "= max(-0.0043 + 0.0175 x W + 0.0089 x T, league minimum) x that season's cap, less the cap hit. W "
    + "is the wins above replacement (WAR) delivered; T is the years of term left on the contract; a defenceman adds 0.0041 "
    + "x W. Each future season k is divided by (1.03)^k.")),
  B(L("Example.", "A forward who delivers 2.0 WAR with three years of term left is worth (-0.0043 + 0.0175 x 2 + 0.0089 x 3) "
    + "x $95.5M = $5.49M for the season. On a $4.0M cap hit, the club's net for that season is +$1.49M."), 1),
  B("Seasons from 2026-27 on have not been played yet, so they are still the models' forecast. A pick is followed to the "
    + "player drafted with it."));
add(H2("Step 3: look at groups of clubs"));
add(B("Take every club that did one thing, for example acquired a player aged 28 to 31, and average their trade-day grades "
  + "and their results."),
  B("Standard errors are clustered by trade: a trade's two clubs are mirror images, so they count as one piece of evidence, "
    + "not two."));
add(H2("Step 4: make sure it is not something else in disguise"));
add(B("Characteristics overlap. A club buying a 30-year-old at the deadline might also take on a clause and give up picks. A "
  + "regression puts all the characteristics in at once, so each one's effect is measured with the others held fixed. A "
  + "characteristic that matters alone but fades here was standing in for something else."));
add(H2("Step 5: try to break each finding"));
add(B(L("Fresh trades.", "Does it hold on the trades after March 2022, which played no part in finding it?")),
  B(L("A second performance measure.", "Does it hold when performance is measured with Game Value instead of WAR?")),
  B(L("Seasons played only.", "Does it hold when only seasons already played count, so nothing rests on the models' own "
    + "forecast of the future?")),
  B(L("Many tests at once.", "Testing many groups turns up some by luck. Holm's adjustment raises each p-value so the chance "
    + "of any false finding among the groups tested stays at 5%.")));
add(H2("Step 6: price or result?"));
add(B("Some findings show only in the trade-day grade: the market paid differently from the models' value, but the results "
  + "do not confirm it. The strongest findings show in both."));
add(H2("The data"));
add(B(L("Trades, 2017-07-01 to 2022-03-28.", "567 trades (563 with every asset's result known) from CapFriendly's public "
  + "record of each trade, its assets and cap hits. This is the main test; its rules were committed before it was run.")),
  B(L("Trades to 2026-03-13.", "1,085 trades (927 with results) from PuckPedia, a salary-cap data provider whose contract "
    + "data the player model already uses. Where both sources cover 2019-22, they give the same asset value to $1,000 for 844 "
    + "of 855 matched assets.")),
  B(L("WAR", "is Patrick Bacon's public model (TopDownHockey), which adds a player's even-strength offence and defence, power "
    + "play, penalty kill, penalties and shooting into one number of wins.")),
  B(L("Game Value", "is our own measure built from the NHL's game logs (on-ice expected goals for and against, adjusted for the "
    + "score, plus penalties drawn and taken), with no WAR inputs. It is put on WAR's scale by matching the league's average "
    + "and spread each season.")));

// ==== 2 ====
add(H1("2. The Models Predict How Trades Turn Out"));
add(ANSWER("The club the models favour on trade day comes out ahead in about 57% to 61% of trades, against 50% for a coin."));
add(table(["", "2017-22, WAR", "2017-22, Game Value", "All trades, WAR"], [
  ["Favoured club came out ahead", "57.1% [53.3, 61.1]", "56.9% [52.9, 60.8]", "60.7% [57.5, 63.9]"],
  ["Share of the trade-day gap that came true", "0.749 [0.553, 0.901]", "0.731 [0.530, 0.957]", "0.633 [0.463, 0.782]"],
  ["Correlation of grade and result", "0.556", "0.544", "0.512"],
], [34, 22, 24, 20]));
add(NOTE("The share is the slope of each club's result on its trade-day grade: 1 would mean every gap the models see comes true "
  + "in full, 0 that the grade says nothing. Intervals from 2,000 resamples of trades. Source: backtest.py v1.7."));
add(B(L("What it means.", "One dollar scale for players, picks and prospects works: about three-quarters of the gap seen on "
  + "trade day shows up in the result, and the result does not depend on which performance measure is used.")),
  B(L("By type of asset (2017-22),", "result less trade-day value per asset: players +0.104 [-0.078, +0.294] (664 assets); "
    + "prospects +0.158 [-0.138, +0.521] (253); picks -0.188 [-0.330, -0.041] (633). Only picks fall short of their forecast "
    + "by a statistically significant amount.")));

// ==== 3 ====
add(H1("3. Clubs Overpay for Age, Draft Pedigree and Clauses"));
add(ANSWER("Clubs pay more than a player is worth when he is 28 or older, a former top-15 pick, or on a contract with a "
  + "no-trade or no-move clause, and they come out behind by about as much."));
add(H2("How it was measured"));
add(B("Each club's main player is the one with the highest cap hit it received."),
  B("The overpay is how far the club's trade-day grade fell below zero; the loss is how far its result did."),
  B("Both are compared across the main player's characteristics, all held fixed together: age, position, clause, signed in "
    + "free agency, seasons left, production (his recent WAR, weighted 50/30/20 across his three most recent seasons), "
    + "how far that record sits above his forecast, his share of games played last season, and draft pedigree."),
  B("His cap hit is left out on purpose. A contract's value is already its performance value less its cap hit, so \"clubs "
    + "overpay for expensive players\" would restate the models' own definition."));
add(H2("What was found"));
add(table(["Club acquiring a player who is", "Overpaid", "Lost, WAR", "Lost, Game Value", "Lost, 2017-22, seasons played", "Lost, after 2022"], [
  ["Aged 28 to 31", "+1.60*", "+1.78*", "+1.74*", "+2.07*", "+0.82"],
  ["Aged 32 or over", "+2.03*", "+1.17", "+1.45*", "+1.43", "+0.47"],
  ["On a contract with a clause", "+1.69*", "+1.55*", "+1.49*", "+1.94*", "+1.22*"],
  ["A former top-15 pick", "+1.53*", "+1.52*", "+1.62*", "+1.37", "+1.50*"],
], [30, 12, 12, 14, 18, 14]));
add(NOTE("$M a side, all trades unless headed otherwise. Compared with a forward aged 27 or under with one season left, all other "
  + "characteristics held. * = statistically significant at 5%, standard errors clustered by trade. 735 club sides (540 trades) "
  + "for all trades; 431 for 2017-22; 304 after 2022. Source: who_overpaid.py v1.0, who_overpaid_checks.py v1.1."));
add(B(L("Clauses and draft pedigree", "hold in price and in results on the newer trades alone and on seasons played. In "
  + "2017-22 alone the pedigree result is the same size (+1.37) but not statistically significant (p = 0.11).")),
  B(L("Age 28 to 31", "holds in price and results in 2017-22 and on seasons played. On the newer trades the overpay "
    + "replicates (+1.24, p = 0.039); the loss (+0.82) points the same way but is not yet significant, as those trades have "
    + "fewer seasons played.")),
  B(L("Age 32 or over", "is a pricing finding: clubs clearly pay more (+2.03), and the results confirm it on Game Value only.")),
  B(L("Grouped the simple way,", "2017-22: clubs acquiring a player aged 28 to 31 paid -1.56 (0.31) and came out -1.49 (0.44); "
    + "clubs acquiring a clause player paid -2.95 (0.53) and came out -2.50 (0.65). Both pass Holm's adjustment.")));
add(H2("What it means"));
add(B("Clubs pay for the name, the draft pedigree and the past, more than for what the player is likely to deliver next."),
  B("Each of the three holds with the others fixed: paying more for a 29-year-old is separate from paying more for a former "
    + "high pick or for a clause."));
add(H2("Things that look like this but are not"));
add(B(L("A strong recent record, high production and a full share of games", "each predict an overpay alone, but none does "
  + "once age and pedigree are held: they travel with those.")),
  B(L("Long contracts", "(three or more seasons left) show in price (+2.71) but not in results (+0.20). The gap comes from "
    + "how term is priced (Section 6).")),
  B(L("Defencemen", "are not a finding: see Section 5.")));

// ==== 4 ====
add(H1("4. Trade Prices Only Partly Reflect Contract Quality"));
add(ANSWER("When a contract is $1 better or worse than the models say it should be, the trade price adjusts by only about 40 "
  + "cents. Bargain contracts sell for too little, and bad contracts for too much."));
add(H2("How it was measured"));
add(B("Each main player's contract is split into two parts: the value of his forecasted performance (with the control "
  + "seasons after it), and the present value of his cap hit over the seasons left."),
  B("The price paid for him is what the club gave up, less everything else it received."),
  B("A market that priced contracts fully would move the price $1 for each $1 of performance value, and down $1 for each $1 of "
    + "cap cost."),
  B(L("A correction for the models' own error.", "Any error in the models' values pulls this kind of estimate toward zero by "
    + "itself. Two-stage least squares corrects for it: the models' value is first predicted from what the contract actually "
    + "delivered, and the price is compared with that prediction. Only the part of the models' value that turned out to be "
    + "real is used.")));
add(H2("What was found"));
add(table(["Price paid, per $1 of", "Performance value", "Cap cost"], [
  ["The models' value", "+0.26 (0.11)", "-0.27 (0.10)"],
  ["What the contract actually delivered", "+0.19 (0.09)", "-0.23 (0.09)"],
  ["The models' value, corrected for its error", "+0.41 [+0.05, +0.76]", "-0.39 [-0.67, -0.07]"],
  ["The same, using seasons played only for the correction", "+0.39 [+0.00, +0.75]", "-0.37 [-0.65, -0.05]"],
], [52, 24, 24]));
add(NOTE("886 club sides, all trades; standard errors clustered by trade; the corrected rows' intervals from 2,000 resamples of "
  + "trades. The cap cost is approximate (injured-reserve relief left out). In 2017-22 alone the corrected figures are +0.33 and "
  + "-0.33, with intervals that include zero. Source: who_overpaid.py v1.0, who_overpaid_checks.py v1.1."));
add(H2("What it means"));
add(B("About 40 cents is far below a full dollar, and the interval excludes a full dollar, so the market does not sort good "
  + "contracts from bad ones as much as their value differs."),
  B(L("This is why clubs selling players for picks and prospects come out ahead.", "They are usually shedding expensive "
    + "contracts, and are not charged enough to do it. Those clubs' trade-day grade is +1.54 (0.18) a trade and their result "
    + "+0.91 (0.25) in 2017-22, and +0.77 (0.22) after 2022. Once the cap hit is accounted for, this result disappears (-0.10, "
    + "not significant): it is the same finding seen from the other side.")),
  B(L("Cap dumps are the same pattern.", "In 43 trades a club sent a player at $2.5M or more with a pick or prospect and took "
    + "back no player at $1M or more. It attached $0.096M of picks and prospects for each $1M of cap cleared [0.057, 0.154], "
    + "and the club taking the contract came out behind.")),
  B(L("In cap-hit terms,", "each $1M of the main player's cap hit costs the acquiring club 0.98 in trade-day grade and 0.54 in "
    + "result (all trades), and 0.76 and 0.44 on the trades after 2022 alone; each is statistically significant.")));

// ==== 5 ====
add(H1("5. What Is Not Mispriced, and What Has Not Changed"));
add(ANSWER("Deadline buying, retaining salary, rentals and defencemen carry no mispricing of their own, and the market's "
  + "mispricing has not changed since 2017."));
add(table(["Group", "Clubs", "Grade, alone", "Result, alone", "Result, others held"], [
  ["Higher in the standings, last 14 days before the deadline", "193", "-0.92 (0.13)", "-0.54 (0.21), Holm p 0.089", "+0.01 (p 0.94)"],
  ["Retained salary", "86", "+1.30 (0.35)", "+1.03 (0.48), Holm p 0.274", "+0.27 (p 0.62)"],
  ["Received a rental (final season, unrestricted, in season)", "260", "-0.35 (0.09)", "-0.16 (0.15)", "see the deal below"],
  ["Received one asset for two or more", "178", "-1.40 (0.22)", "-0.48 (0.37)", "-0.08 (p 0.77)"],
  ["Sold under a new general manager, his predecessor's contract", "65", "+1.69 (0.52)", "+0.36 (0.68)", "-0.12 (p 0.83)"],
], [36, 8, 14, 22, 20]));
add(NOTE("\"Alone\": the group's average, 2017-22. \"Others held\": all characteristics in one regression, all trades. Source: "
  + "groups_clustered.py v1.0, joint_regression.py v1.2."));
add(B(L("Deadline buying and retained salary", "disappear once the player taken and the picks given are held: those carry "
  + "them. A younger rental for picks and prospects is priced about even (+0.02 [-0.36, +0.38]) and turns out about even "
  + "(+0.47 [-0.04, +1.03]).")),
  B(L("One asset for two or more, and new general managers,", "show a price that differs from the models' value, but the "
    + "results are too noisy to confirm or contradict it.")),
  B(L("Defencemen.", "Traded defencemen delivered their forecast (-0.02 WAR a season [-0.08, +0.04]) by games, ice time and "
    + "each part of WAR, and clubs acquiring one came out where their price said. They only look worse next to clubs acquiring "
    + "forwards, who tend to pay with picks, and picks under-deliver.")),
  B(L("No change over time.", "The gap between the price paid and the models' value changed by -0.019 a season [-0.084, "
    + "+0.052] from 2017-18 to 2025-26. This uses trade-day prices only, which are complete for every trade.")),
  B(L("Offer sheets", "(a what-if on 1,215 contracts signed by restricted free agents since 2018, at the same term and salary, "
    + "less the draft-pick compensation at the pick curve's values):")),
  B("They would have paid off for 61% at the signed salary, 54% at 10% more and 45% at 20% more, but mostly below the line "
    + "where compensation starts (683 contracts, average +1.01).", 1),
  B("Where a first-round pick is owed (terms of seven seasons or fewer): 18 of 146, 10 of 169 and 4 of 189.", 1),
  B("The four signed since 2018, at their own terms: Aho (2019) -17.08, Kotkaniemi (2021) -9.64, Broberg (2024) -6.95, "
    + "Holloway (2024) -1.33. The original club's right to match is not modelled, so this overstates how under-used offer "
    + "sheets are.", 1),
  B(L("Former top-15 picks who have not broken out", "(134 players at D+5 or later): 42% of the 125 with a later contract "
    + "season caught up later. Kept from D+5, their value fell by 1.31 [-2.23, -0.43] by the next July.")),
  B(L("Late picks", "(rounds 6 and 7) are priced at 0.09 each and deliver 0.09 less: nothing either way. Restricted free agents "
    + "in their final season show no gap (+0.45 [-0.33, +1.42]).")));

// ==== 6 ====
add(H1("6. How Far the Evidence Reaches"));
add(ANSWER("The mispricing is in the trade-day price; the results confirm the models rather than revealing something they "
  + "missed. Six limits apply."));
add(H2("The mispricing is in the price"));
add(B("For each group, each club's result was compared with what its trade-day grade predicted. In 2017-22, no group came out "
  + "beyond its prediction by a statistically significant amount, on WAR or on Game Value, among the fourteen tested."));
add(H2("How term is priced"));
add(B("Each year of term is worth 0.0089 of a cap a season ($0.851M). Each remaining season of a contract is priced on the "
  + "term left, so a contract fair when signed is marked down as its term runs out:"));
add(table(["Contracts of two or more seasons", "At signing", "1 season on", "2 seasons on", "3 seasons on", "4 seasons on"], [
  ["Average xNPV", "-0.58", "-1.77", "-4.90", "-6.93", "-7.82"],
  ["The term rule's markdown alone", "0.00", "-1.88", "-4.83", "-6.71", "-7.71"],
], [34, 13, 13, 13, 13, 14]));
add(NOTE("Every skater contract at every July 1, 2018 to 2025. Source: contract_value_by_age.py v1.1."));
add(B(L("Why term left:", "longer contracts out-perform their forecast by only 0.076 to 0.174 a season per extra year of term "
  + "(significant in a contract's first two seasons), 9% to 20% of what term pays. Most of the premium is not performance "
  + "the forecast misses.")),
  B(L("If each season were priced on the contract's original term instead,", "traded players would total -108.1 rather than "
    + "-1,028.5. Of the club results that are statistically significant, 49 of 52 trade-day grades stay so, but only 5 of 30 "
    + "results on WAR.")));
add(H2("The limits"));
add(B(L("Recent results are part forecast.", "Picks and prospects traded after 2022 have mostly not reached the NHL, so their "
  + "results rest partly on the models. Section 3 shows each finding on seasons played as well.")),
  B(L("Sections 3 and 4 are exploratory.", "Their characteristics were chosen after the first results were read; replication "
    + "on the newer trades is the main defence against chance.")),
  B(L("Regular-season wins only.", "A contender's playoff run is outside the currency.")),
  B(L("A shared dollar rate.", "The forecast and the result convert wins to dollars on the same price line. Game Value removes "
    + "the shared performance measure, not the shared rate.")),
  B(L("Game Value is weaker on defence.", "It agrees with the WAR-based forecast at r = 0.65 for forwards and r = 0.30 for "
    + "defencemen.")),
  B(L("Traded assets only.", "Only traded assets are observed, apart from the top-15 picks check, and conditional picks are "
    + "valued as unconditional (94 trades in 2017-22).")));

const doc = new Document({
  creator: "xNPV", title: "Trade Back-test: What We Found and How",
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
