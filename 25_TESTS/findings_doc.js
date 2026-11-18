// findings_doc.js v2.1 -- builds "Trade Back-test, What We Found and How, revised.docx" (40_DOCS/); v2.0 built "Trade
// Back-test, What We Found and How.docx" (Thomas's commented copy of it is kept in git); v1.x "Back-test Findings and Methods.docx".
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
const OUTFILE = process.env.DOC_OUT || path.join(ROOT, "40_DOCS", "Trade Back-test, What We Found and How, revised.docx")   // v2.1: a new file; v2.0's holds Thomas's comments
const FONT = "Arial";
const VERSION = "findings_doc.js v2.1";

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
  B(L("Signs.", "A club's trade-day grade and realized value (Section 1) are positive when it gained and negative when it "
    + "lost. Section 3 reverses the sign, so that a larger number there is a larger overpay or loss.")),
  B(L("Reading the statistics.", "A figure in brackets after an estimate, such as -1.56 (0.31), is its standard error: the "
    + "typical size of the estimate's error. A range in square brackets, such as [53.3, 61.1], is a 95% confidence interval. "
    + "A star (*) means statistically significant at the 5% level: a difference this large would arise by chance less than "
    + "5% of the time if there were none.")));

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
add(B("Each asset is followed after the trade and what it actually delivered is valued at the same prices."),
  B("For each club, what it received less what it gave up, valued this way, is its realized value."),
  B(L("One season's value", "= max(-0.43% + 1.75% x W + 0.89% x T, league minimum) x that season's cap, less the cap hit. W "
    + "is the wins above replacement (WAR) delivered; T is the years of term left on the contract; a defenceman adds 0.41% "
    + "x W. Each future season k is divided by (1.03)^k.")),
  B(L("Example.", "A forward who delivers 2.0 WAR with three years of term left is worth (-0.43% + 1.75% x 2 + 0.89% x 3) "
    + "x $95.5M = $5.49M for the season. On a $4.0M cap hit, the club's net for that season is +$1.49M."), 1),
  B("Seasons from 2026-27 on have not been played yet, so for those the realized value uses the models' forecast. A pick is "
    + "followed to the player drafted with it; a pick or prospect who has not reached the NHL by 2026-27 is valued again by "
    + "the models then. Section 2 shows how many trades are fully played out, with nothing left to forecast."));
add(H2("Step 3: look at groups of clubs"));
add(B("Take every club that made the same type of trade, for example acquired a player aged 28 to 31, and average their "
  + "trade-day grades and their realized values."),
  B("Standard errors are clustered by trade."));
add(H2("Step 4: make sure it is not something else in disguise"));
add(B("Characteristics overlap. A club buying a 30-year-old at the deadline might also take on a clause and give up picks. A "
  + "regression puts all the characteristics in at once, so each one's effect is measured with the others held fixed. A "
  + "characteristic that matters alone but fades here was standing in for something else."));
add(H2("Step 5: try to break each finding"));
add(B(L("Fresh trades.", "Does the finding hold on the trades after March 2022, which were not in the sample of trades in which "
  + "it was first found?")),
  B(L("A second performance measure.", "Does it hold when performance is measured with Game Value instead of WAR?")),
  B(L("Played seasons only.", "Does it hold when a club's realized value counts only the seasons played through 2025-26, with "
    + "no model projection of the seasons after?")));
add(H2("Step 6: price and realized value"));
add(B("A finding must show in both the trade-day grade (what clubs paid against the models' value) and the realized value "
  + "(how the trade turned out). A gap that shows in the trade-day grade only is reported as not a finding."));
add(H2("The data"));
add(B(L("Trades, 2017-07-01 to 2022-03-28.", "567 trades (563 with every asset's realized value known) from CapFriendly's "
  + "public record of each trade, its assets and cap hits. This is the main test; its rules were committed before it was run.")),
  B(L("Trades to 2026-03-13.", "1,085 trades (927 with realized values) from PuckPedia, a salary-cap data provider whose "
    + "contract data the player model already uses. Where both sources cover 2019-22, they give the same asset value to $1,000 "
    + "for 844 of 855 matched assets.")),
  B(L("WAR", "is Patrick Bacon's public model (TopDownHockey), which adds a player's even-strength offence and defence, power "
    + "play, penalty kill, penalties and shooting into one number of wins.")),
  B(L("Game Value", "is our own measure built from the NHL's game logs (on-ice expected goals for and against, adjusted for the "
    + "score, plus penalties drawn and taken), with no WAR inputs. It is put on WAR's scale by matching the league's average "
    + "and spread each season.")));

// ==== 2 ====
add(H1("2. The Models Predict How Trades Turn Out"));
add(ANSWER("The club the models favour on trade day comes out ahead in about 57% to 61% of trades."));
add(table(["", "2017-22, WAR", "2017-22, Game Value", "All trades, WAR"], [
  ["Favoured club came out ahead", "57.1% [53.3, 61.1]", "56.9% [52.9, 60.8]", "60.7% [57.5, 63.9]"],
  ["Slope of realized value on trade-day grade", "0.749 [0.553, 0.901]", "0.731 [0.530, 0.957]", "0.633 [0.463, 0.782]"],
  ["R-squared", "0.309", "0.296", "0.262"],
], [34, 22, 24, 20]));
add(NOTE("The slope is how far a club's realized value moves for each $1 of its trade-day grade: 1 means the predicted gap "
  + "shows up in full on average, 0 that the grade predicts nothing. R-squared is the share of the variation in realized "
  + "values that the trade-day grades account for. The two answer different questions: the prediction is close to right on "
  + "average, but single trades scatter widely around it. 95% confidence intervals by resampling trades."));
add(B(L("What it means.", "Creating one metric to evaluate players, picks and prospects works: about three-quarters of the gap "
  + "predicted on trade day shows up in the realized value, and the result is replicable when using an alternative metric to "
  + "evaluate performance.")),
  B(L("By type of asset (2017-22),", "realized minus predicted value per asset acquired: players +0.104 [-0.078, +0.294] (664 "
    + "assets); prospects +0.158 [-0.138, +0.521] (253); picks -0.188 [-0.330, -0.041] (633). Only picks fall short of their "
    + "prediction by a statistically significant amount.")),
  B(L("Trades fully played out.", "In 197 of the 563 trades of 2017-22, no asset has anything left for the models to forecast. "
    + "These are mostly small trades of players: they hold 18 of the 633 picks traded, and their median trade-day grade is "
    + "$0.25M against $0.40M for all trades. On them the slope is 0.56 [0.00, 1.04] and the R-squared 0.12. The favoured "
    + "club came out ahead in 45%, because in 45 of these trades no asset ever played and both clubs' realized values are "
    + "zero; with those set aside, it came out ahead in 58% [52, 64].")));

// ==== 3 ====
add(H1("3. Clubs Overpay for Players Aged 28 to 31, Former Top-15 Picks and Clauses"));
add(ANSWER("Clubs pay more than the models' value for a player aged 28 to 31, a former top-15 pick, or a player on a contract "
  + "with a no-trade or no-move clause, and the realized gap in value is as predicted."));
add(H2("How it was measured"));
add(B("Each club's main player is the player with the highest cap hit it received. A club joins a group through its main "
  + "player only: for example, a club is in the former top-15 pick group when its main player is a former top-15 pick, not "
  + "when a former top-15 pick came with a more expensive player. Of the 1,152 clubs that received a player, 1,026 received "
  + "only one; the rule decides the main player for the other 126."),
  B("An overpay is the club's trade-day grade with its sign reversed: a club that gave up $2M more than it received, at the "
    + "models' values, overpaid by $2M, and a club that gained has a negative overpay. A loss is the club's realized value "
    + "with its sign reversed."),
  B("Both are regressed on the main player's characteristics, all at once: age, position, clause, signed as an unrestricted "
    + "free agent, seasons left, production (his recent WAR, weighted 50/30/20 across his three most recent seasons), how far "
    + "that record sits above his forecast, his share of games played in the most recent season, and draft pedigree."),
  B("Each figure is the difference from a club whose main player has none of the characteristics: a forward aged 27 or under "
    + "in the final season of his contract, with no clause, not signed as an unrestricted free agent, and not a former top-15 "
    + "pick. Each figure, therefore, is the effect of that one characteristic with all the others held fixed."),
  B("His cap hit is left out on purpose. A contract's value is already its performance value less its cap hit, so \"clubs "
    + "overpay for expensive players\" would restate the models' own definition."));
add(H2("What was found"));
add(table(["Club acquiring a main player who is", "Overpay", "Loss, WAR", "Loss, Game Value", "Loss, WAR, 2017-22, played seasons only", "Loss, WAR, after 2022"], [
  ["Aged 28 to 31", "1.60*", "1.78*", "1.74*", "2.07*", "0.82"],
  ["Aged 32 or over", "2.03*", "1.17", "1.45*", "1.43", "0.47"],
  ["On a contract with a clause", "1.69*", "1.55*", "1.49*", "1.94*", "1.22*"],
  ["A former top-15 pick", "1.53*", "1.52*", "1.62*", "1.37", "1.50*"],
], [30, 12, 12, 14, 18, 14]));
add(NOTE("$M a club, all trades unless the column says otherwise. * = statistically significant at the 5% level, standard "
  + "errors clustered by trade. 735 clubs (540 trades) for all trades; 431 for 2017-22; 304 after 2022."));
add(B(L("The clause and former top-15 pick findings", "hold in both overpay and loss on the trades after 2022 alone, and on "
  + "played seasons only across all trades. On played seasons in 2017-22 alone, the former top-15 pick loss is about the same "
  + "size (1.37) but not statistically significant (p = 0.11).")),
  B(L("The age 28 to 31 finding", "holds in both overpay and loss in 2017-22 and on played seasons only. On the trades after "
    + "2022 the overpay result replicates (1.24, p = 0.039); the loss (0.82) points the same way but is not yet statistically "
    + "significant, as those trades have fewer seasons played.")),
  B(L("Grouped the simple way,", "2017-22: clubs acquiring a player aged 28 to 31 overpaid by 1.56 (0.31) and lost 1.49 (0.44); "
    + "clubs acquiring a clause player overpaid by 2.95 (0.53) and lost 2.50 (0.65). Each is statistically significant at the "
    + "5% level (p = 0.001 or less).")));
add(H2("What it means"));
add(B("Clubs pay for the name, the draft pedigree and the past, more than for what the player is likely to deliver next."),
  B("Each of the three holds with the others fixed: paying more for a 29-year-old is separate from paying more for a former "
    + "high pick or for a clause."));
add(H2("Things that look like this but are not"));
add(B(L("Players aged 32 or over.", "Clubs overpay for them (2.03), but the loss is statistically significant on Game Value "
  + "only, not on WAR, so this is not a finding.")),
  B(L("A strong recent record, high production and a full share of games.", "Each predicts an overpay when tested alone, but "
    + "none does once age and draft pedigree are held fixed: their effect alone came from the age and pedigree they overlap "
    + "with.")),
  B(L("Long contracts.", "Clubs overpay on trade day for a player with three or more seasons left (2.71), but the loss is "
    + "small and not statistically significant (0.20). The gap shows in the trade-day grade only, so this is not a finding.")),
  B(L("Defencemen.", "The defenceman result is not a mispricing of defencemen: see Section 5.")));

// ==== 4 ====
add(H1("4. Teams Respond to Only About 40% of a Contract's Value"));
add(ANSWER("Teams only respond to mispriced contracts by about 40%: when a contract's performance is worth $1 more or less "
  + "than its cap hit, the trade price moves by about 40 cents. Bargain contracts sell for too little, and bad contracts for "
  + "too much."));
add(H2("How it was measured"));
add(B("Each main player's contract is split into two parts: the value of his forecasted performance over the rest of the "
  + "contract (with the seasons of continued team control included for restricted free agents), and the present value of "
  + "his cap hit over the seasons left."),
  B("The price paid for him is what the club gave up, less everything else it received."),
  B("A market that priced contracts fully would move the price $1 for each $1 of performance value, and down $1 for each $1 of "
    + "cap cost."),
  B(L("A correction for the models' own error.", "The models' values are estimates, and part of each is error. The price "
    + "cannot follow that error, so regressing the price on the models' value gives a smaller slope than the market's true "
    + "response. Two-stage least squares removes this in two steps. First, the models' value is regressed on what the "
    + "contract actually delivered; this keeps only the part of the models' value that the player's real performance bears "
    + "out. Second, the price is regressed on that part. The result says whether the low response belongs to the market or "
    + "to the models' error.")));
add(H2("What was found"));
add(table(["Price paid, per $1 of", "Performance value", "Cap cost"], [
  ["The models' value", "+0.26 (0.11)", "-0.27 (0.10)"],
  ["What the contract actually delivered", "+0.19 (0.09)", "-0.23 (0.09)"],
  ["The models' value, corrected for its error", "+0.41 [+0.05, +0.76]", "-0.39 [-0.67, -0.07]"],
  ["The same, using played seasons only for the correction", "+0.39 [+0.00, +0.75]", "-0.37 [-0.65, -0.05]"],
], [52, 24, 24]));
add(NOTE("886 clubs, all trades; standard errors clustered by trade; the corrected rows' 95% confidence intervals by resampling "
  + "trades. The cap cost is approximate (injured-reserve relief left out). In 2017-22 alone the corrected figures are +0.33 "
  + "and -0.33, with confidence intervals that include zero."));
add(H2("What it means"));
add(B("About 40 cents is far below a full dollar, and the confidence interval excludes a full dollar, so the market does not "
  + "separate good contracts from bad ones by as much as their values differ. The models' error does not explain it."),
  B(L("This is why clubs selling players for picks and prospects come out ahead.", "Their trade-day grade is +1.54 (0.18) and "
    + "their realized value +0.91 (0.25) in 2017-22, and +0.77 (0.22) after 2022. The players they sell are mostly on "
    + "expensive contracts, and the buyers do not charge enough for the cost. Once the cap hit of the player sold is held "
    + "fixed, selling for picks and prospects gains nothing extra (-0.10, not statistically significant): the gain comes from "
    + "the contract shed, not from taking picks and prospects.")),
  B(L("Cap dumps are the same pattern.", "In 43 trades a club sent a player at $2.5M or more with a pick or prospect and took "
    + "back no player at $1M or more. It attached $0.096M of picks and prospects for each $1M of cap cleared [0.057, 0.154], "
    + "and the club taking the contract came out behind.")),
  B(L("In cap-hit terms,", "each $1M of the main player's cap hit lowers the acquiring club's trade-day grade by 0.98 and its "
    + "realized value by 0.54 (all trades), and by 0.76 and 0.44 on the trades after 2022 alone; each is statistically "
    + "significant at the 5% level.")));

// ==== 5 ====
add(H1("5. What Is Not Mispriced, and What Has Not Changed"));
add(ANSWER("The groups below carry no mispricing of their own, and we found no difference in how efficiently teams transacted "
  + "over time."));
add(table(["Group", "Clubs", "Trade-day grade, alone", "Realized value, alone", "Realized value, others held"], [
  ["Higher in the standings, last 14 days before the deadline", "193", "-0.92 (0.13)", "-0.54 (0.21)", "+0.01 (p 0.94)"],
  ["Retained salary", "86", "+1.30 (0.35)", "+1.03 (0.48)", "+0.27 (p 0.62)"],
  ["Received a rental (final season, unrestricted, in season)", "260", "-0.35 (0.09)", "-0.16 (0.15)", "+0.93 (p 0.002)"],
  ["Main player a defenceman", "181", "-0.99 (0.24)", "-1.00 (0.31)", "-0.82 (p 0.002)"],
  ["Main player a former top-15 pick below the top-15 average, D+5 or later", "60", "-1.02 (0.65)", "-1.32 (0.80)", "-0.96 (p 0.057)"],
  ["Received one asset for two or more", "178", "-1.40 (0.22)", "-0.48 (0.37)", "-0.08 (p 0.77)"],
  ["Sold under a new general manager, his predecessor's contract", "65", "+1.69 (0.52)", "+0.36 (0.68)", "-0.12 (p 0.83)"],
], [36, 8, 14, 20, 22]));
add(NOTE("$M a club; positive means the club gained. \"Alone\": the group's average, 2017-22, with its standard error. "
  + "\"Others held\": all characteristics in one regression, all trades, with its p-value."));
add(B(L("The deadline-buying and retained-salary results", "disappear once the player taken and the picks given are held "
  + "fixed. Alone, each realized value is statistically significant (p = 0.010 and 0.034); with the others held, neither is "
  + "(p = 0.94 and 0.62).")),
  B(L("The rental result", "turns positive with the others held (+0.93) because a rental is usually paid for with picks and "
    + "prospects, which the regression counts separately (across trades the two are linked at a correlation of 0.50 in size). Taken together, the usual deadline deal, a rental for picks and "
    + "prospects, is priced about even for the buyer (+0.02 [-0.36, +0.38]) and turns out about even (+0.47 [-0.04, +1.03]).")),
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
    + "from zero, but the realized value is not statistically significant, alone or with the others held.")),
  B(L("Late picks.", "Picks in rounds 6 and 7 are valued at $0.09M each on trade day, on average, and deliver $0.09M less "
    + "(p = 0.001), so about nothing. The amounts are too small to matter: clubs whose whole return was late picks were "
    + "neither ahead nor behind (realized value -0.07, p = 0.79).")),
  B(L("Restricted free agents in their final contract season:", "realized value +0.45 [-0.33, +1.42], not statistically "
    + "significant.")),
  B(L("No change over time.", "We found no difference in how efficiently teams transacted over time. The average size of the "
    + "gap between the price paid and the models' value changed by -0.019 a season [-0.084, +0.052] from 2017-18 to 2025-26, "
    + "which is not statistically significant. This uses trade-day grades only, which are complete for every trade.")));

// ==== 6 ====
add(H1("6. How Far the Evidence Reaches"));
add(ANSWER("The mispricing is in the trade-day price; the realized values confirm the models' predictions rather than "
  + "revealing something they missed. Six limits apply."));
add(H2("The mispricing is in the price"));
add(B("No type of trade, on average, over- or under-performed the models' prediction in a statistically significant way. For "
  + "each of the fourteen groups tested, each club's realized value was compared with what its trade-day grade predicted, in "
  + "2017-22, on WAR and on Game Value."));
add(H2("How term is priced"));
add(B("The models add 0.89% of the cap ($0.851M at the 2025-26 cap) to a season's value for each year of term left on the "
  + "contract. This is the term premium: for the same forecasted performance, clubs pay more a season on longer contracts."),
  B("Each season is priced on the term left at that time, so a contract fair when signed is marked down as its term runs out:"));
add(table(["Contracts of two or more seasons", "At signing", "1 season on", "2 seasons on", "3 seasons on", "4 seasons on"], [
  ["Average xNPV", "-0.58", "-1.77", "-4.90", "-6.93", "-7.82"],
  ["The term rule's markdown alone", "0.00", "-1.88", "-4.83", "-6.71", "-7.71"],
], [34, 13, 13, 13, 13, 14]));
add(NOTE("Every skater contract at every July 1, 2018 to 2025."));
add(B(L("Why the term left, rather than the term signed.", "If the premium paid for performance the forecast misses, the "
  + "player would deliver it for the whole contract, and each season should be priced on the term signed. Longer contracts do "
  + "out-perform their forecast, but by little: 0.076 to 0.174 WAR a season for each extra year of term, statistically "
  + "significant at the 5% level only in a contract's first and second seasons. That is worth 9% to 20% of the premium. The "
  + "other 80% to 91% is not performance, so the models count it only while the term remains.")),
  B(L("What the choice changes.", "Priced on the term signed, the traded players' total xNPV is -$108.1M rather than "
    + "-$1,028.5M. Most trade-day grades by group stay as they are: of the 52 groups whose grade is statistically significant "
    + "(all trades), 49 still are. Most realized values by group do not: of the 30 whose realized value on WAR is "
    + "statistically significant, 5 still are. The regression in Section 3 has not been re-run on the term signed.")));
add(H2("The limits"));
add(B(L("Recent realized values are part forecast.", "Picks and prospects traded after 2022 have mostly not reached the NHL, so "
  + "their realized values rest partly on the models. Section 3 shows each finding on played seasons as well, and Section 2 "
  + "shows the trades fully played out.")),
  B(L("Sections 3 and 4 are exploratory.", "Their characteristics were chosen after the first results were read; replication "
    + "on the trades after 2022 is the main defence against chance.")),
  B(L("Regular-season wins only.", "A contender's playoff run is outside the currency.")),
  B(L("A shared dollar rate.", "The forecast and the realized value convert wins to dollars on the same price line. Game Value "
    + "removes the shared performance measure, not the shared rate.")),
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
