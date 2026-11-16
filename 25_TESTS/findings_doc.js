// findings_doc.js v1.0 -- builds "Back-test Findings and Methods.docx" (40_DOCS/), a bullet-point draft of the back-test's
// methods and findings on the five take-aways agreed 2026-11-15 (Thomas: "give me a word doc of bullet points but show
// numerical results").
//
// NUMBERS: each figure is a constant below, read from the run log or results file named beside it (all written
// 2026-11-11 to 2026-11-15 on the model as decided: each contract season on the term left). Declared window = trades
// 2017-07-01 to 2022-03-28; all trades = to 2026-03-13; "after 2022" = trades after 2022-03-28.
//   G  = 30_OUTPUT/_extended_run/groups_clustered.csv (group means, clustered SEs, Holm, outcome on price)
//   J  = 30_OUTPUT/_extended_run/joint_regression_log.txt and joint_regression_played_log.txt
//   BT = 30_OUTPUT/backtest_log.txt, backtest_gv_compare_log.txt, _extended_run/backtest_log.txt
//   M  = 30_OUTPUT/_extended_run/backtest_cuts_more_log.txt (cap, offer sheets, top picks, GMs)
//   T  = 30_OUTPUT/term_quality_test_log.txt, _extended_run/contract_value_by_age_log.txt, _original_term_run/
//   DC = 30_OUTPUT/defence_checks_log.txt
//
// Run:  node 25_TESTS/findings_doc.js

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType, HeadingLevel,
  BorderStyle, ShadingType, LevelFormat, Footer, PageNumber,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const OUTFILE = process.env.DOC_OUT || path.join(ROOT, "40_DOCS", "Back-test Findings and Methods.docx");
const FONT = "Arial";

// ---- building blocks ---------------------------------------------------------------------------------------------------
const runs = (t) => (Array.isArray(t) ? t : [t]).map((x) => (typeof x === "string" ? new TextRun({ text: x, font: FONT }) : x));
const B = (t, level = 0) => new Paragraph({ numbering: { reference: "bullets", level }, children: runs(t), spacing: { after: 60 } });
const P = (t) => new Paragraph({ children: runs(t), spacing: { after: 120 } });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: t, font: FONT })] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: t, font: FONT })] });
const NOTE = (t) => new Paragraph({ children: [new TextRun({ text: t, font: FONT, size: 17, italics: true })], spacing: { before: 40, after: 160 } });

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
      children: [new TextRun({ text, font: FONT, size: 17, bold: header })] })],
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

add(new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun({ text: "Trade Back-test: Methods and Findings", font: FONT })] }),
  P("A bullet-point draft. Money is in millions of dollars at the 2025-26 salary cap ($95.5M), per club side of a trade unless a line "
    + "says otherwise. Standard errors are in brackets; intervals are 95%."));

// ==== 1. methods ====
add(H1("1. How the Findings Were Made"));
add(H2("The trades"));
add(B("Declared window. Every NHL trade from 2017-07-01 to 2022-03-28: 567 trades, 563 with an outcome for each asset (1,133 club sides). "
  + "The trades come from CapFriendly's public trade record, which lists each asset, its cap hit and any retained salary. This window is the "
  + "confirmatory test; its rules were committed before it was run."),
  B("Extended to 2026-03-13 with PuckPedia's trades export (PuckPedia is a salary-cap data provider whose contract export the player model "
    + "already uses): 1,085 trades, 927 with an outcome for each asset (1,868 club sides). Rebuilt from PuckPedia's export, the 2019-20 to "
    + "2021-22 trades give the same value to $1,000 for 844 of 855 matched assets."),
  B("A trade with a pick for a draft not yet held has no outcome and is left out; most of the 158 extended trades left out are of that kind."));
add(H2("Two numbers for each club in each trade"));
add(B("Priced net. What the club received less what it gave up, each asset at its expected net present value (xNPV) on the trade date, "
  + "using only information available before that date. Players are valued by the contract model, picks by the pick curve and "
  + "prospects by the prospect model. Retained salary is charged to the retaining club, an in-season trade counts only the share of "
  + "the season left, and long-term injured reserve relief is applied. Each trade sums to zero across its clubs."),
  B("Outcome net. The same sum, with each asset's xNPV replaced by what it delivered over the same seasons, whoever held it later."),
  B("The value of one season, in both: max(-0.0043 + 0.0175 x W (+0.0041 for a defenceman) + 0.0089 x T, league minimum) x that season's "
    + "cap, less the cap hit. W is the WAR (wins above replacement), forecast or delivered; T is the years of term left on the contract. "
    + "Each future season k is divided by (1.03)^k. A season's value and cost are in that season's dollars at a cap growing 3% a year, "
    + "so stated at the 2025-26 cap the growth and the discount cancel."),
  B("Example. A forward who delivered 2.0 WAR with three years of term left is worth (-0.0043 + 0.0175 x 2 + 0.0089 x 3) x $95.5M = "
    + "$5.49M for the season. On a $4.0M cap hit, the season's net value is +$1.49M.", 1),
  B("Seasons played through 2025-26 use the WAR delivered and that season's actual cap; a season with no NHL game is worth zero. "
    + "Seasons from 2026-27 on are valued again by the same models at July 2026. A pick is followed to the player drafted with it."),
  B("WAR is Patrick Bacon's public model (TopDownHockey), which adds a player's even-strength offence and defence, power play, penalty "
    + "kill, penalties and shooting into one number of wins."));
add(H2("The checks on each result"));
add(B("Group means. For each group of club sides (for example, clubs that acquired a player aged 28 to 31), the mean priced net and "
  + "mean outcome net, with standard errors clustered by trade, because a trade's two club sides are mirror images. A p-value is the "
  + "chance of an estimate this far from zero if the true mean were zero."),
  B("Holm's adjustment. Fourteen groups are tested, so about one would pass at the 5% level by chance. Holm's adjustment raises each "
    + "p-value so that the chance of any false finding among the fourteen stays at 5%."),
  B("Outcome on price. Every club side's outcome net regressed on its priced net, the group indicator and their product, clustered by "
    + "trade. The group coefficient is the group's outcome beyond what its price predicts."),
  B("Joint regression. One row a two-team trade (913); each group enters as club A's indicator less club B's (+1, 0 or -1), with no "
    + "constant, robust standard errors. Each coefficient is the group's effect with the other twelve groups held."),
  B("Replication. Each group is tested again on the 364 complete trades after 2022-03-28, which played no part in choosing the groups."),
  B("Game Value. A second measure of what a skater delivered, built from the NHL's game logs (on-ice expected goals for and against, "
    + "adjusted for score, plus penalties drawn and taken), with no Bacon inputs. It is put on WAR's scale by matching the league's mean "
    + "and spread each season. Each test is run on both measures; goaltenders keep WAR."),
  B("Seasons played only. Each test is run again with the seasons from 2026-27 on set to zero, so no outcome rests on the models' own "
    + "re-valuation."),
  B("Each group and test was written into the back-test protocol and committed before it was computed. The groups beyond the "
    + "protocol's first seven were chosen after the first results were read, and are reported as exploratory."));

// ==== 2. take-away 1 ====
add(H1("2. One Scale Predicts How Trades Turn Out"));
add(B("Players, picks and prospects priced on one scale predict which club comes out ahead, on both measures of performance."));
add(table(["Measure", "Declared window, WAR", "Declared window, Game Value", "All trades, WAR"], [
  ["Club the models favoured came out ahead", "57.1% [53.3, 61.1]", "56.9% [52.9, 60.8]", "60.7% [57.5, 63.9]"],
  ["Slope of outcome net on priced net", "0.749 [0.553, 0.901]", "0.731 [0.530, 0.957]", "0.633 [0.463, 0.782]"],
  ["Correlation of priced and outcome net", "0.556", "0.544", "0.512"],
], [34, 22, 24, 20]));
add(NOTE("A slope of 1 would mean each gap the models see at the trade comes true in full; 0, that it carries no information. "
  + "Intervals from 2,000 resamples of trades. Source: backtest.py v1.7."));
add(B("With standard errors clustered by trade, the slope in the declared window is 0.749 (0.086)."),
  B("By asset class, outcome less forecast per asset in the declared window: players +0.104 [-0.078, +0.294] (664 assets); picks "
    + "-0.188 [-0.330, -0.041] (633); prospects +0.158 [-0.138, +0.521] (253). Only picks miss their forecast by a statistically "
    + "significant amount at the 5% level."),
  B("Without any dollar rate, the net wins each club received on WAR and on Game Value correlate at 0.90 (1,133 club sides)."));

// ==== 3. take-away 2 ====
add(H1("3. Clubs Overpay for Players Aged 28 to 31, Defencemen and Clause Players"));
add(B("The club that acquires such a player pays more than the models' value and comes out behind by about the amount it overpaid."));
add(table(["Club acquiring", "Sides", "Priced", "Outcome, WAR", "Outcome, Game Value", "Beyond its price, WAR", "After 2022, WAR"], [
  ["A main player aged 28 to 31", "159", "-1.56 (0.31)", "-1.49 (0.44), Holm p 0.008", "-1.56 (0.46), Holm p 0.008", "-0.28 (0.36)", "-0.87 (0.26), Holm p 0.009"],
  ["A defenceman", "181", "-0.99 (0.24)", "-1.00 (0.31), Holm p 0.015", "-1.17 (0.33), Holm p 0.006", "-0.22 (0.27)", "-0.57 (0.21), Holm p 0.046"],
  ["A player with a no-trade or no-move clause", "66", "-2.95 (0.53)", "-2.50 (0.65), Holm p 0.002", "-2.66 (0.79), Holm p 0.008", "-0.22 (0.84)", "-1.61 (0.39), Holm p < 0.001"],
], [22, 7, 11, 16, 16, 12, 16]));
add(NOTE("Declared window unless headed otherwise. The main player is the player with the highest cap hit the club received. "
  + "\"Beyond its price\" is the group coefficient of the outcome-on-price regression; none is statistically significant at the 5% level. "
  + "Source: groups_clustered.py v1.0."));
add(B("With the other groups held (joint regression, all trades, outcome on WAR): aged 28 to 31 -1.12 (p = 0.001); a clause -1.48 "
  + "(p = 0.009); a defenceman -0.82 (p = 0.002). On the seasons played only: -1.03 (p = 0.003), -1.41 (p = 0.006) and -0.70 (p = 0.006)."),
  B("A typical deal: a clause veteran aged 28 to 31 for picks and prospects. The buying club is priced at -3.36 [-4.41, -2.40] and "
    + "comes out at -3.07 [-4.42, -1.89] on WAR."),
  B("Traded defencemen delivered their forecast: delivered less expected WAR a season -0.02 [-0.08, +0.04] (880 seasons, 253 players). "
    + "Neither games played, ice time nor any part of WAR shows a shortfall specific to defencemen, so the result does not come from "
    + "the measures' weakness on defence."));

// ==== 4. take-away 3 ====
add(H1("4. Clubs Selling Players for Picks and Prospects Come Out Ahead"));
add(table(["Club that received only picks and prospects", "Sides", "Priced", "Outcome, WAR", "Outcome, Game Value"], [
  ["Declared window", "275", "+1.54 (0.18)", "+0.91 (0.25), Holm p 0.003", "+1.02 (0.24), Holm p < 0.001"],
  ["After 2022", "159", "+1.20", "+0.77 (0.22), Holm p 0.006", "+0.75"],
], [34, 8, 14, 22, 22]));
add(NOTE("Source: groups_clustered.py v1.0 and backtest_cuts.py v1.5."));
add(B("This holds although picks themselves deliver less than forecast: -0.188 a pick in the declared window, -0.233 across all trades."),
  B("With the other groups held (all trades), the seller's priced gain is +0.89 (p < 0.001) and its outcome +0.47 (p = 0.071): the "
    + "outcome gain is partly carried by the age and clauses of the players the buying clubs take."));

// ==== 5. take-away 4 ====
add(H1("5. What Looks Like Timing or Deal Structure Is the Player"));
add(table(["Group", "Sides", "Priced, alone", "Outcome WAR, alone", "Outcome WAR, others held"], [
  ["Higher in the standings, deadline window (14 days)", "193", "-0.92 (0.13)", "-0.54 (0.21), Holm p 0.089", "+0.01 (p 0.94)"],
  ["Retained salary", "86", "+1.30 (0.35)", "+1.03 (0.48), Holm p 0.274", "+0.27 (p 0.62)"],
  ["Received a rental (final season, unrestricted, in-season)", "260", "-0.35 (0.09)", "-0.16 (0.15)", "read with the deal below"],
  ["Took a contract another club paid to move", "23", "-4.90 (0.88)", "-2.73 (1.02), Holm p 0.077", "-1.19 (p 0.10)"],
  ["Received one asset for two or more", "178", "-1.40 (0.22)", "-0.48 (0.37)", "-0.08 (p 0.77)"],
  ["Sold under a new general manager, his predecessor's contract", "65", "+1.69 (0.52)", "+0.36 (0.68)", "-0.12 (p 0.83)"],
], [36, 8, 14, 22, 20]));
add(NOTE("\"Alone\": the group's mean, declared window. \"Others held\": the joint regression, all trades. Source: groups_clustered.py "
  + "v1.0, joint_regression.py v1.2."));
add(B("Deadline buying and retained salary carry no effect of their own; the player taken and the picks given carry them. A deadline "
  + "rental for picks and prospects is priced at +0.02 [-0.36, +0.38] for the buyer and comes out at +0.47 [-0.04, +1.03]; the same "
  + "rental aged 28 to 31 comes out at -0.65 [-1.31, -0.01]."),
  B("Cap dumps. In 43 trades a club sent a player at $2.5M or more with a pick or prospect and took back no player at $1M or more. It "
    + "cleared $8.3M of cap on average and attached $0.096M of picks and prospects per $1M cleared [0.057, 0.154]."),
  B("New general managers. Selling a player signed by the predecessor in the first 365 days in the job gets more than the models' "
    + "value (+1.69 in the declared window, +1.41 after 2022); the outcome difference does not hold with the other groups held."),
  B("Offer sheets, a what-if on 1,215 contracts signed by restricted free agents since 2018, at the same term and the signed average "
    + "annual value, less the compensation picks at the pick curve's values:"),
  B("Positive payoff for 61% at the signed value, 54% at 10% more, 45% at 20% more; most of it below the compensation line (683 "
    + "contracts, mean +1.01).", 1),
  B("Where a first-round pick is owed (terms of seven seasons or fewer): positive for 18 of 146, 10 of 169 and 4 of 189.", 1),
  B("The four sheets tendered 2018 to 2025, at their own terms: Aho (2019) -17.08, Kotkaniemi (2021) -9.64, Broberg (2024) -6.95, "
    + "Holloway (2024) -1.33. Matching rights are not modelled, so this is an upper bound on how much offer sheets are under-used.", 1),
  B("Former top-15 picks below the benchmark at D+5 or later (134 players): 42% of the 125 with a later contract season reached the "
    + "benchmark later. Kept from D+5, their xNPV fell by 1.31 [-2.23, -0.43] by the next July; from D+6 on the change is not "
    + "statistically significant."),
  B("Not findings: rentals as such; restricted free agents in their final season (outcome +0.45 [-0.33, +1.42]); learning over time "
    + "(the size of the gap between the price paid and the models' value changes by -0.019 a season [-0.084, +0.052]); picks in rounds 6 and 7, priced "
    + "at 0.09 each and delivering 0.09 less."));

// ==== 6. take-away 5 ====
add(H1("6. The Mispricing Is in the Price, and One Modelling Choice Sets Its Reach"));
add(B("No group comes out beyond what its trade-day price predicts. In the declared window, none of the fourteen group coefficients "
  + "of the outcome-on-price regression is statistically significant at the 5% level, on WAR or on Game Value."),
  B("The term rule. Each year of term is worth 0.0089 of a cap a season ($0.851M), and a contract season is priced on the term left. "
    + "A contract fair when signed is therefore marked down as its term runs out:"));
add(table(["Standard contracts of two or more seasons", "At signing", "1 season on", "2 seasons on", "3 seasons on", "4 seasons on"], [
  ["Mean xNPV", "-0.58", "-1.77", "-4.90", "-6.93", "-7.82"],
  ["The term rule's shortfall alone", "0.00", "-1.88", "-4.83", "-6.71", "-7.71"],
], [36, 13, 13, 13, 13, 12]));
add(NOTE("Every skater contract at every July 1, 2018 to 2025. Source: contract_value_by_age.py v1.1."));
add(B("Priced on each contract's original term instead, the traded players sum to -108.1 rather than -1,028.5. Of the club-side "
  + "results whose interval excludes zero, 49 of 52 priced results still do (all trades), against 5 of 30 outcome results on WAR."),
  B("Longer contracts out-perform their forecast by 0.076 to 0.174 a season per extra year of term (statistically significant at the 5% "
    + "level in a contract's first and second seasons): 9% to 20% of the term premium. Most of the premium is not performance the "
    + "forecast misses, which supports pricing on the term left."),
  B("Limits:"),
  B("Wins are regular-season only; playoff value is outside the currency.", 1),
  B("The forecast and the outcome convert wins to dollars on the same price line; Game Value removes the shared performance "
    + "measure, not the shared rate.", 1),
  B("Game Value agrees with the WAR-based forecast at r = 0.65 for forwards and r = 0.30 for defencemen.", 1),
  B("Only traded assets are observed, apart from the top-15 picks check.", 1),
  B("Conditional picks are valued as unconditional (94 trades in the declared window).", 1));

const doc = new Document({
  creator: "xNPV", title: "Trade Back-test: Methods and Findings",
  styles: {
    default: { document: { run: { font: FONT, size: 20 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", run: { font: FONT, size: 36, bold: true }, paragraph: { spacing: { before: 0, after: 160 }, keepNext: true } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 26, bold: true, color: "1F3864" }, paragraph: { spacing: { before: 280, after: 100 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 22, bold: true }, paragraph: { spacing: { before: 160, after: 80 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "bullets", levels: [
    { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 260 } } } },
    { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 260 } } } },
  ] }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16 })] })] }) },
    children: body,
  }],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUTFILE, buf); console.log("findings_doc.js v1.0 wrote " + OUTFILE); });
