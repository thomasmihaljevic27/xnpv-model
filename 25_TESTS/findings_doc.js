// findings_doc.js v2.1 -- builds "Trade Back-test, What We Found and How, revised.docx" (40_DOCS/); v2.0 built "Trade
// Back-test, What We Found and How.docx" (Thomas's commented copy of it is kept in git); v1.x "Back-test Findings and Methods.docx".
//
// v3.9 (2026-11-19; Thomas's edits of 21:01, his copy 29a7abb, carried verbatim with straight apostrophes: Section 4's
// "Each player's contract", the main-player-rule sentence and the "priced contracts correctly" bullet cut, his regression
// sentence, his two-stage passage; and the outside review's changes he accepted ("Yes, make those changes"): Step 3's
// two sentences, Step 4's "group's", Step 5's opening and mirror-image sentences, the new-GM label (list and table),
// the clause bullets, "No change over time" and its sentence, "about 40 cents", the sellers' sentence, Section 5's opening,
// conditional picks their own limitation and the orphaned top-15 check cut; no em dashes)
//
// v3.8 (2026-11-19; Thomas: the clause gap "has to be fixed"; "sold a player for just picks and prospects"; "I'd like it
// if it were presented that way"): every Section 3 figure from one_regression.py v2.3 (two rows a trade, clustered by
// trade) on backtest.py v1.8 (clauses filled from CapWages, clause_fill.py; sellers for just picks and prospects);
// the clause, age, defenceman, rule and clause-reading bullets and Section 4's sellers rewritten on the new figures.
//
// v3.7 (2026-11-19; Thomas's notes on v3.6, his copy f9b0fa2): his edits carried verbatim: no bold lead-in labels (his copy
// has none; L() now plain); Step 7's and Section 2's labels cut; "Why the rules differ:" and "effects"; the clause
// bullet's last sentence cut; the two lower Section 3 tables captioned "As above." with their bullets cut; the types of
// trade table to the regression's two columns, the below-average top-15 row cut; "No Change over time"; Section 4's two
// headings, its label and "so no forecast enters it" cut; Section 5's first heading cut and "Limitations". His comment
// "Best to just list all variables": Step 5 lists the regression's 23 terms (one_regression.py v2.2's P5 and PC).
//
// v3.6 (2026-11-19; Thomas: "Yes, fix them"): three wording points from the final figure check: Step 5 says the
// regressions use the 556 two-team trades (7 three-team trades left out); "Why the rules differ" age range 6% to 27% (from
// the estimates, as the other two ranges; 27.4%); the top-15 benchmark "1.08 WAR per 82 games a season".
//
// v3.5 (2026-11-19; Thomas: "Yes, rebuild it"): one_regression.py v2.2 with the goalie indicator: the defenceman a finding
// again under the main player rule, a goalie row; Thomas's 12:17 edits carried ("in xNPV"; the negative-average bullet,
// Section 3's "How it was measured" and "Main player rule." cut; the types of trade merged into Step 5's bullet; colons);
// Step 5's design bullet reworded as sent in chat.
//
// v3.4 (2026-11-19; Thomas: "Yes, rebuild with it. Just keep the new clause discussion brief"): Section 3 on all 556
// two-team trades (one_regression.py v2.0, the missing player facts filled by facts_fill.py v1.1); the former top-15 pick
// is no longer a finding and moves to the other characteristics; one bullet on whether the clause is a stand-in for the
// cap hit, reputation or cap dumps (clause_disguise.py v1.0); Step 3's counts; Thomas's cut "Each two-team trade is taken
// once." carried into Step 5.
//
// v3.3 (2026-11-19; Thomas: "Yes, rewrite"): one regression in place of two (one_regression.py v1.1; protocol 0349335,
// 08b8a87, e289869). The old Sections 3 and 4 become Section 3, every table from that regression: the findings (clause,
// age 28 to 31, former top-15 pick), the other characteristics, the types of trade; the contract section is Section 4 and
// the evidence section Section 5. Step 5 says the regression also holds the types of trade and takes each trade once.
//
// v3.2 (2026-11-19): Thomas's fifth round (4 comments and his edits on the v3.1 file), his edits carried verbatim: his step
// titles; Step 1's sample sentence and "from either the player, pick, or prospect models"; the value bullets, the player
// equation and the example cut; "Trades can be in multiple categories at once"; "a certain condition"; "a trade is in a
// group"; "uses the main player rule or any player rule"; "buying at the trade deadline"; his Step 4 and Step 5 (the second
// regression's description cut from Step 5); Section 2's and the contract section's captions; "is a result of the market or
// due to the models' error"; "Measurement". Sections 4 and 5 swapped (Thomas: "to better explain the purpose of the two
// different regression types"): the types of trade are Section 4, with the second regression's purpose and design; the
// defenceman moves there, where its regression finds it (Thomas: "It's confusing to look at the table and see no finding by
// rule but then be told it is a finding"); the regression's other characteristics table moves to Section 3 with the
// defenceman's row. "Why the rules differ" reworded ("Clunky wording"); "Grouped the simple way" named as Step 4's average.
// Steps 6 and 7 title-cased to match his.
//
// v3.1 (2026-11-18; Thomas: "Yes, move to Section 3"): the defenceman is a finding under the main player rule (it meets
// Step 6 in the regression with every category held constant); its rows and bullet moved from Section 5 to Section 3.
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
const VERSION = "findings_doc.js v3.12";

// ---- building blocks ---------------------------------------------------------------------------------------------------
// A string is plain text; ["Label", "text"] as L() gives a bold lead-in label followed by plain text.
const T = (text, o = {}) => new TextRun({ text, font: FONT, ...o });
const runs = (t) => (Array.isArray(t) ? t : [t]).map((x) => (typeof x === "string" ? T(x) : x));
const L = (label, text) => [T(label + " "), T(text)];   // v3.7: plain (Thomas's copy has no bold lead-ins)
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
// v3.2: Section 1 as Thomas edited it (his step titles; the value bullets, the equation and the example cut; his Step 3,
// 4 and 5 wording), carried verbatim. Steps 6 and 7 title-cased to match his.
add(H2("Step 1: Trade Day Grade"));
add(B("The sample is the 563 trades made from July 1, 2017 to March 28, 2022."),
  B("Every player, pick and prospect in a trade gets a dollar value from either the player, pick, or prospect models, using "
    + "only what was known that day. This value is its expected net present value (xNPV)."),
  // v3.5: Thomas's "in xNPV" (his copy of 12:17)
  B("What each club received in xNPV less what it gave up in xNPV is the club's trade-day grade. A positive grade means it "
    + "got more value "
    + "than it gave; negative means it paid too much. The two clubs' grades always sum to zero."));
add(H2("Step 2: Calculate Realized Value"));
add(B("Each asset is followed after the trade and what it actually delivered is valued at the same market rate."),
  B("For each club what it actually received less what it gave up is its realized value."),
  B("Seasons from 2026-27 and onwards have not been played yet, so for those the realized value uses the models' forecast. A "
    + "pick is followed to the player drafted with it; a pick or prospect who has not reached the NHL by 2026-27 is valued "
    + "again by the appropriate model."));
add(H2("Step 3: Sort by Trade Category"));
add(B("A category is a type of trade, for example acquiring a player aged 28 to 31, or buying at the trade deadline. Trades "
  + "can be in multiple categories at once."),
  B("Teams are categorized in two ways: by whether the main player received meets a condition, or whether any player "
    + "received does:"),
  B(L("Main player rule:", "a trade is in a group when its main player has the characteristic; for example, it is in the "
    + "former top-15 pick group when its main player is a former top-15 pick. The main player is defined as the player with "
    + "the highest cap hit the team received."), 1),
  B(L("Any player rule:", "a club is in a group when any player it received has the characteristic. Of the 577 clubs in "
    + "Section 3's regression that received a player, only 63 received two or more players, so this method is a type of "
    + "robustness check."), 1),
  B("Each result is reported under both rules. Categories based on outgoing players, such as retained salary, follow "
    + "the same distinction (the highest-cap-hit player sent, or any player sent). A category not about a player, such as buying at the trade deadline, is the same "
    + "under both rules."));
add(H2("Step 4: Test Each Category"));
add(B("For each category, the clubs in it are averaged twice: once on their trade-day grades and once on their realized "
  + "values."),
  B("Each group's average is tested against zero by dividing it by its standard error. The two "
    + "clubs in a trade are mirror images of each other, so they are not two independent observations. Standard errors are "
    + "therefore clustered by trade, counting each trade only once."));
add(H2("Step 5: Run Regressions"));                  // v3.11: his title
add(B("Two regressions are run, one on trade-day grades and one on realized values."),   // v3.11: his cut
  // v3.7 (Thomas: "Best to just list all variables"): the 23 terms, as one_regression.py v2.2 enters them
  B("The club's trade-day grade and its realized value are each regressed on the following 23 variables:"),
  B("The player received (12): aged 28 to 31; aged 32 or over (each against 27 or under); a defenceman; a goalie (each "
    + "against a forward); a no-trade or no-move clause; signed as an unrestricted free agent; two seasons left on contract; "
    + "three or more seasons left (each against one season); a former top-15 draft pick; recent production (WAR weighted "
    + "50/30/20 over the three most recent seasons); how much that production exceeds the models' forecast for the season "
    + "of the trade; the share of games played in the most recent season.", 1),
  B("The type of trade (10): sold a player for just picks and prospects; team higher in the standings, last 14 days before the "
    + "deadline; team higher in the standings, earlier in the season; received a rental; retained salary; received one "
    + "asset for two or more; took on a contract to clear cap; a new general manager selling a contract signed by "
    + "his predecessor; received a restricted free agent in his final contract season; received only picks in rounds 6 and 7.", 1),
  B("Whether the club received a player at all (1).", 1),
  B("Under the main player rule each characteristic is the main player's. Under the any player rule a yes-or-no "
    + "characteristic, such as a contract clause, counts when any player received has it. Production, how much it exceeds its "
    + "forecast, and the games share are averages over the players received, weighted by cap hit."),
  // v3.8 (Thomas, 2026-11-19: "I'd like it if it were presented that way"): two rows a trade, clustered by trade
  B("Each trade enters each regression twice, once for each club. The club's value is regressed on what it received less "
    + "what it sent away in each characteristic: +1 if it received a player with the characteristic, -1 if it sent one "
    + "away, 0 if neither or both; for production, the WAR received less the WAR sent away. Because the second club's row is the "
    + "exact mirror image of the first's (every sign reversed), standard errors are clustered by trade. There is no constant, because one "
    + "club's gain is the other's loss. A club that received no player gets zero for each player characteristic, plus a "
    + "separate term marking whether it received a player. The regressions use the 556 two-team trades; the 7 trades "
    + "among three clubs are left out."));
add(H2("Step 6: What Counts as a Finding"));
add(B("A finding must show in both the trade-day grade and the realized value: the characteristic is statistically "
  + "significant at the 5% level in both regressions, with the same sign."));
add(H2("Step 7: Double Check Each Finding"));
add(B("Does it hold when performance is measured with Game Value instead of WAR?"),          // v3.7: his labels cut
  B("Does it hold when a club's realized value counts only the seasons played through 2025-26, with no model projection of "
    + "the seasons after?"));

// ==== 2 ====
add(H1("2. The Models Predict How Trades Turn Out"));
add(table(["", "WAR", "Game Value"], [
  ["Favoured club came out ahead", "57.1% [53.3, 61.1]\np = 0.001", "56.9% [52.9, 60.8]\np = 0.001"],
  ["Slope of realized value on trade-day grade", "0.749 [0.553, 0.901]\np < 0.001", "0.731 [0.530, 0.957]\np < 0.001"],
  ["R-squared", "0.309", "0.296"],
], [40, 30, 30]));
// v3.2: his caption and his cut of the last sentence of the asset bullet
add(NOTE("The slope is how far a club's realized value moves for each $1 of its trade-day grade. 95% confidence intervals in "
  + "square brackets."));
add(B(("Creating one metric to evaluate players, picks and prospects works: about three-quarters of the gap "
  + "predicted on trade day shows up in the realized value, and the result is replicable when using an alternative metric to "
  + "evaluate performance.")),                                   // v3.7: his label cut
  B(L("By type of asset,", "realized minus predicted value per asset acquired: players +0.104 [-0.078, +0.294] (664 assets); "
    + "prospects +0.158 [-0.138, +0.521] (253); picks -0.188 [-0.330, -0.041] (633).")));

// ==== 3 ====
// v3.5 (Thomas: "yes add the goalie indicator and rerun"; "Yes, rebuild it"): one_regression.py v2.2, a goalie indicator
// beside the defenceman one; the defenceman is a finding again (main player rule); his 12:17 edits ("How it was measured"
// cut; "Main player rule." cut from the clause bullet; colons after the bullet labels).
// v3.4 (Thomas: "Yes, rebuild with it. Just keep the new clause discussion brief"): every figure from one_regression.py
// v2.0, all 556 two-team trades (the missing player facts filled, facts_fill.py v1.1); the clause reading from
// clause_disguise.py v1.0, one bullet. The former top-15 pick is no longer a finding: it moves to the other characteristics.
add(H1("3. Clubs Overpay for Players with Contract Clauses and, by the Main Player Rule, Players Aged 28 to 31 and Defencemen"));
add(H2("Findings"));
add(table(["Club acquiring", "Rule", "Trade-day grade", "Realized value, WAR", "Realized value, Game Value", "Realized value, WAR, played seasons only"], [
  ["A player with a clause", MR, "-1.62 (0.49)\np = 0.001", "-2.58 (0.77)\np < 0.001", "-2.50 (0.87)\np = 0.004", "-2.71 (0.75)\np < 0.001"],
  ["", AR, "-1.74 (0.48)\np < 0.001", "-2.72 (0.79)\np < 0.001", "-2.62 (0.92)\np = 0.005", "-2.84 (0.77)\np < 0.001"],
  ["A player aged 28 to 31", MR, "-1.12 (0.38)\np = 0.003", "-1.68 (0.63)\np = 0.008", "-1.64 (0.65)\np = 0.012", "-1.55 (0.61)\np = 0.011"],
  ["", AR, "-0.76 (0.48)\np = 0.11", "-1.20 (0.74)\np = 0.10", "-1.51 (0.79)\np = 0.057", "-1.16 (0.69)\np = 0.094"],
  ["A defenceman", MR, "-0.66 (0.31)\np = 0.037", "-1.42 (0.44)\np = 0.001", "-1.67 (0.51)\np = 0.001", "-1.39 (0.42)\np < 0.001"],
  ["", AR, "-0.54 (0.30)\np = 0.072", "-1.10 (0.39)\np = 0.005", "-1.19 (0.37)\np = 0.001", "-1.06 (0.36)\np = 0.003"],
], [20, 16, 16, 16, 16, 16]));
add(NOTE("Figures in millions of dollars as of the 2025-26 salary cap. Negative means the club paid more than the models' value. "
  + "Standard errors in brackets, clustered by trade."));
add(B(L("The clause finding", "holds under both rules and in each test. Clubs acquiring a player with a no-trade or "
  + "no-move clause overpay on trade day and lose realized value; the result holds on Game Value and on played seasons only "
  + "as well.")),
  // v3.3: Thomas's own cut of the parenthetical; v3.4: the any player rule now misses on one measure only
  B(L("The age 28 to 31 finding", "holds in each test under the main player rule. Under the any player rule it is not "
    + "statistically significant (p = 0.11 and 0.10).")),
  B(L("The defenceman finding", "holds in each test under the main player rule. Under the any player rule the trade-day "
    + "grade is not statistically significant (p = 0.072).")),
  // v3.11 (Thomas: "say we have the evidence that teams overpaid for D despite them meeting their projections, which is a
  // result of being compared to forwards"): the picks explanation cut (defence_gap_split.py: picks are about a quarter of
  // a forward-defenceman difference that is not significant)
  // v3.11: Thomas's own rewrite of this bullet (his copy 4a92b7e), verbatim, with only the picks clause cut
  B(L("Defencemen are overpaid for, not misjudged.", "Traded defencemen met their forecasts across games played, ice time, "
    + "and every component of WAR (-0.02 WAR per season [-0.08, +0.04]). Accordingly, clubs acquiring a defenceman "
    + "finished right where their trade-day grade predicted (realized minus predicted value of -$0.02M [-$0.42M, "
    + "+$0.39M]). The larger realized gap in the regression (-$1.42M vs. -$0.66M on trade day) is partly a baseline "
    + "effect: defencemen are measured against forwards, and clubs acquiring forwards beat their trade-day grades "
    + "(+$0.47M [+$0.19M, +$0.76M]).")),
  B(L("Why the rules differ:", "Under the any player rule a cheaper second player who is 28 to 31, or a defenceman, puts "
    + "his club in the group, so the effects are smaller than under the main player rule: by 8% to 32% for age and 17% to 28% "
    + "for defencemen. For contract clauses, however, the effects are 5% to 7% larger under the any player rule.")),
  B(L("On its own (Step 4),", "the average club acquiring a player with a clause had a trade-day grade of -2.86 (0.44) and a "
    + "realized value of -2.92 (0.62) under the main player rule, and -2.81 (0.44) and -2.95 (0.61) under the any player "
    + "rule (p < 0.001 each).")),                                    // v3.7: his cut of the last sentence
  // v3.4 (Thomas: "What are the chances that the clause finding is a different finding in disguise?"; "keep the new clause
  // discussion brief"): clause_disguise.py v1.0, main player rule
  B(L("Is the clause a stand-in for something else?", "Clause players are older (32.2 against 27.5 on average), cost more ($3.98M "
    + "against $1.52M a season) and have longer careers behind them. Holding the cap hit constant, the trade-day overpay is "
    + "no longer statistically significant (p = 0.10), suggesting it largely reflects Section 4's finding that clubs "
    + "under-price contract cost. The realized loss remains (-2.06, p = 0.014), and holding the player's reputation (career WAR, best season) or "
    + "leaving out cap dumps changes neither result.")));
add(H2("Other characteristics"));
add(table(["Characteristic", "Rule", "Trade-day grade", "Realized value, WAR", "Realized value, Game Value"], [
  ["A goalie", MR, "-0.63 (0.62)\np = 0.31", "-1.37 (0.70)\np = 0.049", "-1.64 (0.59)\np = 0.006"],
  ["", AR, "-0.63 (0.60)\np = 0.30", "-0.92 (0.66)\np = 0.17", "-1.14 (0.58)\np = 0.050"],
  ["A former top-15 pick", MR, "-1.48 (0.62)\np = 0.016", "-1.33 (0.79)\np = 0.091", "-1.08 (0.81)\np = 0.18"],
  ["", AR, "-1.44 (0.62)\np = 0.021", "-1.33 (0.80)\np = 0.097", "-0.94 (0.85)\np = 0.27"],
  ["A player aged 32 or over", MR, "-0.70 (0.52)\np = 0.18", "-0.51 (0.67)\np = 0.45", "-0.66 (0.65)\np = 0.31"],
  ["", AR, "-0.45 (0.63)\np = 0.48", "-0.08 (0.81)\np = 0.92", "-0.43 (0.78)\np = 0.58"],
  ["A player with three or more seasons left", MR, "-2.85 (0.82)\np < 0.001", "+0.11 (1.45)\np = 0.94", "-0.15 (1.34)\np = 0.91"],
  ["", AR, "-2.94 (0.80)\np < 0.001", "-0.06 (1.43)\np = 0.97", "-0.81 (1.29)\np = 0.53"],
  ["Recent production: each extra WAR a season (WAR weighted 50/30/20 over the three most recent seasons)", MR, "-0.26 (0.31)\np = 0.41", "-0.01 (0.39)\np = 0.98", "-0.03 (0.34)\np = 0.93"],
  ["", AR, "-0.23 (0.35)\np = 0.51", "+0.11 (0.41)\np = 0.79", "+0.22 (0.33)\np = 0.50"],
  ["Recent production above the models' forecast for the season of the trade: each extra WAR", MR, "+0.44 (0.37)\np = 0.24", "+0.22 (0.46)\np = 0.63", "+0.18 (0.41)\np = 0.66"],
  ["", AR, "+0.23 (0.43)\np = 0.59", "+0.05 (0.50)\np = 0.92", "-0.09 (0.43)\np = 0.83"],
  ["Share of games played in the most recent season: all games against none", MR, "-0.83 (0.64)\np = 0.19", "-1.41 (0.73)\np = 0.053", "-1.93 (0.60)\np = 0.001"],
  ["", AR, "-0.60 (0.68)\np = 0.38", "-0.97 (0.73)\np = 0.18", "-1.54 (0.60)\np = 0.010"],
], [34, 17, 16, 17, 17]));
add(NOTE("As above."));                                            // v3.7: his caption; the four bullets cut
add(H2("Types of trade"));
// v3.7: his table (the regression's two columns; the below-average top-15 row cut), "As above.", his heading
add(table(["Group", "Rule", "Trade-day grade", "Realized value"], [
  ["Team higher in the standings, last 14 days before the deadline", MR, "-0.20 (0.15)\np = 0.19", "-0.08 (0.25)\np = 0.74"],
  ["", AR, "-0.22 (0.15)\np = 0.15", "-0.14 (0.26)\np = 0.59"],
  ["Team retained salary", MR, "-0.13 (0.49)\np = 0.78", "-0.44 (0.68)\np = 0.52"],
  ["", AR, "-0.22 (0.50)\np = 0.66", "-0.22 (0.71)\np = 0.75"],
  ["Received a rental (final contract season, unrestricted, in season)", MR, "+0.19 (0.38)\np = 0.61", "+0.67 (0.67)\np = 0.32"],
  ["", AR, "+0.11 (0.38)\np = 0.76", "+0.77 (0.65)\np = 0.24"],
  ["Received a restricted free agent in his final contract season", MR, "+0.20 (0.42)\np = 0.64", "+0.14 (0.77)\np = 0.86"],
  ["", AR, "+0.44 (0.39)\np = 0.25", "+0.65 (0.70)\np = 0.35"],
  ["Received only picks in rounds 6 and 7", MR, "-0.43 (0.24)\np = 0.080", "-0.59 (0.41)\np = 0.15"],
  ["", AR, "-0.45 (0.23)\np = 0.052", "-0.57 (0.40)\np = 0.15"],
  ["Received one asset for two or more", MR, "-0.82 (0.20)\np < 0.001", "-0.21 (0.41)\np = 0.61"],
  ["", AR, "-0.93 (0.20)\np < 0.001", "-0.32 (0.41)\np = 0.44"],
  ["A new general manager selling a contract signed by his predecessor", MR, "+0.49 (0.46)\np = 0.29", "-0.60 (0.73)\np = 0.41"],
  ["", AR, "+0.54 (0.50)\np = 0.28", "-0.59 (0.76)\np = 0.44"],
], [40, 20, 20, 20]));
add(NOTE("As above."));
add(H2("No change over time"));
add(B("The gap between the price paid and the models' value did not change over time: from 2017-18 to 2021-22 its "
  + "average size changed by +0.092 a season (0.094, p = 0.33), and the gap in realized value by -0.051 a season (0.122, "
  + "p = 0.67)."));

// ==== 5 ====
// v3.2: the contract-value section, formerly Section 4, with Thomas's edits ("is a result of the market or due to the
// models' error"; "Measurement"; his caption)
add(H1("4. Teams Respond to Only About 40% of a Contract's Value"));
add(B("Each player's contract is split into two parts: the value of his forecasted performance over the rest of team "
  + "control, and the present value of his cap hit over the seasons left."),           // v3.12: his edit
  B("The price the club paid for its main player alone is the models' value of everything it gave up, less the models' value "
    + "of everything else it received in the trade."),
  // v3.9: Thomas's sentence, with the agreed terms ("the value of his forecasted performance", "present value") and the
  // review's coefficient wording
  B("The price paid for the player is regressed on the value of his forecasted performance over the rest of his contract "
    + "and the present value of his cap hit. In a market that priced contracts correctly, the performance coefficient would "
    + "equal +1 and the cap-cost coefficient would equal -1."),
  B("This section uses every trade to March 2026. The price is set on trade day, and the correction below uses only the "
    + "seasons played."),                                          // v3.7: his cut
  // v3.9: Thomas's two-stage passage, as saved (his cut of the "priced contracts correctly" bullet)
  B("Because the models' values are estimates, they contain noise. Teams do not price that noise, so regressing trade prices "
    + "directly on the models' value pulls the estimated slope toward zero, making the market look less responsive than it "
    + "is. Two-stage least squares (2SLS) separates the models' error from the market's behaviour:"),
  B("First stage: the models' forecasted value is regressed on what the contract actually delivered in the seasons played "
    + "through 2025-26. This keeps only the part of the forecast backed up by real on-ice performance.", 1),
  B("Second stage: the trade price is regressed on that part of the forecast and on the contract's cap cost.", 1),
  B("If the models' error were driving the low estimate, this correction would push the slope close to 1. Instead it rises "
    + "only to about 0.4, and its 95% interval (0.00 to 0.75) excludes 1: teams under-react to contract value."));
add(H2("Findings"));
add(LABEL("How much the price paid for a player moves for each $1 of his contract's two parts"));
add(table(["Measurement", "Price change per $1 market value increase", "Price change per $1 more cap cost"], [
  ["The models' value on trade day", "+0.26 (0.11)\np = 0.017", "-0.27 (0.10)\np = 0.007"],
  ["What the contract delivered in the seasons played", "+0.18 (0.09)\np = 0.048", "-0.22 (0.09)\np = 0.014"],
  ["The models' value, corrected for its error (two-stage least squares)", "+0.39 (0.19)\np = 0.045", "-0.37 (0.16)\np = 0.028"],
], [46, 27, 27]));
add(NOTE("886 clubs, all trades to March 2026. Standard errors in brackets, clustered by trade."));
// v3.10 (Thomas: "Yes, cut it"): the 40-cents bullet cut; his two-stage passage says it before the table
add(B(L("This is why clubs selling players for just picks and prospects come out ahead.", "In 2017-22 their trade-day grade is +1.28 "
    + "(0.18) and their realized value +0.90 (0.24). The players they sell carry higher cap hits than the average traded player "
    + "($1.71M against $1.45M a season), and buyers do not discount enough for that cost. Once the cap hit of the player sold is held fixed, the gain is gone (trade-day "
    + "grade -0.63, p = 0.013; realized value -0.55, p = 0.17): it comes from shedding the contract, not from taking picks "
    + "and prospects.")),
  B(L("Cap dumps are the same pattern.", "In 23 trades in 2017-22 a club sent a player at $2.5M or more along with a pick or "
    + "prospect and took back no player at $1M or more. It attached $0.083M of picks and prospects for each $1M of cap "
    + "cleared [0.036, 0.157], and the club taking the contract came out behind (realized value -2.73 [-4.76, -0.82]).")));

// ==== 6 ====
add(H1("5. How Far the Evidence Reaches"));
add(B("No type of trade over- or under-performed the models' predictions by a statistically significant amount. Comparing "
  + "each club's realized value with what its trade-day grade predicted, across the sixteen groups, under both rules and on "
  + "both WAR and Game Value, the smallest p-value is 0.063."));
add(H2("Limitations"));
add(B(L("Realized values are partly forecasted.", "For these trades that is mostly picks and prospects who have not yet reached "
  + "the NHL, and contracts that run past 2025-26.")),
  B(L("Regular-season wins only.", "A contender's playoff run is outside the currency.")),
  B(L("A shared dollar rate.", "The forecast and the realized value convert wins to dollars on the same price line. Game Value "
    + "removes the shared performance measure, not the shared rate.")),
  B(L("Game Value is weaker on defence.", "It agrees with the WAR-based forecast at r = 0.65 for forwards and r = 0.30 for "
    + "defencemen.")),
  B(L("Traded assets only.", "Only traded assets are observed.")),
  B(L("Conditional picks.", "Conditional picks are valued as unconditional (94 trades).")));

// ==== appendix ====
// v3.12 (Thomas, 2026-11-20: "put full regression result tables in at the end"; scope "the two the findings rest on"):
// Section 3's regression, every variable, each rule (one_regression.csv v2.3; R-squared without a constant refitted from
// stata/findings_data.csv), and Section 4's price regressions (who_overpaid_checks.csv; constants, R-squared and the
// first stage refitted from the same CSV; the two-stage standard errors resampled, as there)
add(H1("Appendix: Full Regression Results"));
add(LABEL("Table A1. Section 3's regression, main player rule"));
add(table(["Variable", "Trade-day grade", "Realized value, WAR", "Realized value, Game Value", "Realized value, WAR, played seasons only"], [
  ["Aged 28 to 31", "-1.12 (0.38)\np = 0.003", "-1.68 (0.63)\np = 0.008", "-1.64 (0.65)\np = 0.012", "-1.55 (0.61)\np = 0.011"],
  ["Aged 32 or over", "-0.70 (0.52)\np = 0.18", "-0.51 (0.67)\np = 0.45", "-0.66 (0.65)\np = 0.31", "-0.48 (0.62)\np = 0.44"],
  ["Defenceman", "-0.66 (0.31)\np = 0.037", "-1.42 (0.44)\np = 0.001", "-1.67 (0.51)\np = 0.001", "-1.39 (0.42)\np < 0.001"],
  ["Goalie", "-0.63 (0.62)\np = 0.31", "-1.37 (0.70)\np = 0.049", "-1.64 (0.59)\np = 0.006", "-1.34 (0.62)\np = 0.030"],
  ["No-trade or no-move clause", "-1.62 (0.49)\np = 0.001", "-2.58 (0.77)\np < 0.001", "-2.50 (0.87)\np = 0.004", "-2.71 (0.75)\np < 0.001"],
  ["Signed as an unrestricted free agent", "+0.36 (0.27)\np = 0.19", "+0.69 (0.42)\np = 0.10", "+0.80 (0.47)\np = 0.087", "+0.66 (0.41)\np = 0.10"],
  ["Two seasons left", "-1.09 (0.54)\np = 0.044", "-0.43 (0.84)\np = 0.61", "-0.14 (1.02)\np = 0.89", "-0.40 (0.83)\np = 0.63"],
  ["Three or more seasons left", "-2.85 (0.82)\np < 0.001", "+0.11 (1.45)\np = 0.94", "-0.15 (1.34)\np = 0.91", "+0.38 (1.39)\np = 0.78"],
  ["Former top-15 draft pick", "-1.48 (0.62)\np = 0.016", "-1.33 (0.79)\np = 0.091", "-1.08 (0.81)\np = 0.18", "-1.11 (0.71)\np = 0.12"],
  ["Recent production, each WAR", "-0.26 (0.31)\np = 0.41", "-0.01 (0.39)\np = 0.98", "-0.03 (0.34)\np = 0.93", "+0.03 (0.36)\np = 0.94"],
  ["Production above the forecast, each WAR", "+0.44 (0.37)\np = 0.24", "+0.22 (0.46)\np = 0.63", "+0.18 (0.41)\np = 0.66", "+0.11 (0.43)\np = 0.79"],
  ["Games share, all games against none", "-0.83 (0.64)\np = 0.19", "-1.41 (0.73)\np = 0.053", "-1.93 (0.60)\np = 0.001", "-1.33 (0.64)\np = 0.038"],
  ["Sold a player for just picks and prospects", "+0.15 (0.28)\np = 0.58", "+0.45 (0.45)\np = 0.32", "+0.16 (0.42)\np = 0.70", "+0.40 (0.43)\np = 0.36"],
  ["Team higher in the standings, last 14 days before the deadline", "-0.20 (0.15)\np = 0.19", "-0.08 (0.25)\np = 0.74", "-0.18 (0.25)\np = 0.46", "+0.00 (0.24)\np = 0.99"],
  ["Team higher in the standings, earlier in the season", "+0.16 (0.25)\np = 0.51", "+0.21 (0.28)\np = 0.45", "+0.24 (0.23)\np = 0.31", "+0.14 (0.25)\np = 0.59"],
  ["Received a rental", "+0.19 (0.38)\np = 0.61", "+0.67 (0.67)\np = 0.32", "+0.80 (0.73)\np = 0.27", "+0.62 (0.63)\np = 0.33"],
  ["Team retained salary", "-0.13 (0.49)\np = 0.78", "-0.44 (0.68)\np = 0.52", "-0.37 (0.71)\np = 0.60", "-0.70 (0.62)\np = 0.26"],
  ["Received one asset for two or more", "-0.82 (0.20)\np < 0.001", "-0.21 (0.41)\np = 0.61", "-0.20 (0.38)\np = 0.59", "-0.20 (0.39)\np = 0.61"],
  ["Took on a contract to clear cap", "-2.94 (0.80)\np < 0.001", "-1.06 (0.98)\np = 0.28", "-0.96 (1.15)\np = 0.41", "-0.75 (0.89)\np = 0.40"],
  ["A new general manager selling a contract signed by his predecessor", "+0.49 (0.46)\np = 0.29", "-0.60 (0.73)\np = 0.41", "+0.19 (0.74)\np = 0.79", "-0.84 (0.69)\np = 0.22"],
  ["Received a restricted free agent in his final contract season", "+0.20 (0.42)\np = 0.64", "+0.14 (0.77)\np = 0.86", "-0.12 (0.82)\np = 0.88", "+0.23 (0.74)\np = 0.76"],
  ["Received only picks in rounds 6 and 7", "-0.43 (0.24)\np = 0.080", "-0.59 (0.41)\np = 0.15", "-0.57 (0.45)\np = 0.20", "-0.56 (0.40)\np = 0.16"],
  ["Received a player at all", "+1.02 (0.48)\np = 0.032", "+1.52 (0.66)\np = 0.022", "+1.67 (0.60)\np = 0.005", "+1.35 (0.59)\np = 0.022"],
  ["Trades (two rows each)", "556", "556", "556", "556"],
  ["R-squared (no constant)", "0.415", "0.145", "0.165", "0.145"],
], [36, 16, 16, 16, 16]));
add(NOTE("Each trade enters twice, once for each club; each variable is the club's side less the other club's (what it "
  + "received less what it sent away). The first twelve variables describe the player received, the next ten the type of "
  + "trade. No constant. Figures in millions of dollars as of the 2025-26 salary cap; standard errors in brackets, clustered "
  + "by trade."));
add(LABEL("Table A2. Section 3's regression, any player rule"));
add(table(["Variable", "Trade-day grade", "Realized value, WAR", "Realized value, Game Value", "Realized value, WAR, played seasons only"], [
  ["Aged 28 to 31", "-0.76 (0.48)\np = 0.11", "-1.20 (0.74)\np = 0.10", "-1.51 (0.79)\np = 0.057", "-1.16 (0.69)\np = 0.094"],
  ["Aged 32 or over", "-0.45 (0.63)\np = 0.48", "-0.08 (0.81)\np = 0.92", "-0.43 (0.78)\np = 0.58", "-0.12 (0.73)\np = 0.87"],
  ["Defenceman", "-0.54 (0.30)\np = 0.072", "-1.10 (0.39)\np = 0.005", "-1.19 (0.37)\np = 0.001", "-1.06 (0.36)\np = 0.003"],
  ["Goalie", "-0.63 (0.60)\np = 0.30", "-0.92 (0.66)\np = 0.17", "-1.14 (0.58)\np = 0.050", "-0.95 (0.59)\np = 0.11"],
  ["No-trade or no-move clause", "-1.74 (0.48)\np < 0.001", "-2.72 (0.79)\np < 0.001", "-2.62 (0.92)\np = 0.005", "-2.84 (0.77)\np < 0.001"],
  ["Signed as an unrestricted free agent", "+0.44 (0.33)\np = 0.18", "+0.54 (0.58)\np = 0.35", "+0.76 (0.75)\np = 0.31", "+0.54 (0.57)\np = 0.34"],
  ["Two seasons left", "-1.07 (0.44)\np = 0.016", "-0.40 (0.79)\np = 0.61", "-0.38 (0.88)\np = 0.66", "-0.37 (0.76)\np = 0.62"],
  ["Three or more seasons left", "-2.94 (0.80)\np < 0.001", "-0.06 (1.43)\np = 0.97", "-0.81 (1.29)\np = 0.53", "+0.20 (1.37)\np = 0.89"],
  ["Former top-15 draft pick", "-1.44 (0.62)\np = 0.021", "-1.33 (0.80)\np = 0.097", "-0.94 (0.85)\np = 0.27", "-1.09 (0.72)\np = 0.13"],
  ["Recent production, each WAR", "-0.23 (0.35)\np = 0.51", "+0.11 (0.41)\np = 0.79", "+0.22 (0.33)\np = 0.50", "+0.17 (0.37)\np = 0.66"],
  ["Production above the forecast, each WAR", "+0.23 (0.43)\np = 0.59", "+0.05 (0.50)\np = 0.92", "-0.09 (0.43)\np = 0.83", "-0.07 (0.45)\np = 0.88"],
  ["Games share, all games against none", "-0.60 (0.68)\np = 0.38", "-0.97 (0.73)\np = 0.18", "-1.54 (0.60)\np = 0.010", "-0.97 (0.65)\np = 0.13"],
  ["Sold a player for just picks and prospects", "+0.23 (0.28)\np = 0.41", "+0.51 (0.44)\np = 0.25", "+0.18 (0.42)\np = 0.67", "+0.45 (0.43)\np = 0.30"],
  ["Team higher in the standings, last 14 days before the deadline", "-0.22 (0.15)\np = 0.15", "-0.14 (0.26)\np = 0.59", "-0.25 (0.25)\np = 0.32", "-0.05 (0.25)\np = 0.84"],
  ["Team higher in the standings, earlier in the season", "+0.18 (0.26)\np = 0.48", "+0.25 (0.30)\np = 0.39", "+0.30 (0.24)\np = 0.22", "+0.17 (0.26)\np = 0.51"],
  ["Received a rental", "+0.11 (0.38)\np = 0.76", "+0.77 (0.65)\np = 0.24", "+0.71 (0.68)\np = 0.30", "+0.75 (0.60)\np = 0.21"],
  ["Team retained salary", "-0.22 (0.50)\np = 0.66", "-0.22 (0.71)\np = 0.75", "-0.21 (0.72)\np = 0.77", "-0.49 (0.64)\np = 0.44"],
  ["Received one asset for two or more", "-0.93 (0.20)\np < 0.001", "-0.32 (0.41)\np = 0.44", "-0.30 (0.38)\np = 0.43", "-0.29 (0.39)\np = 0.45"],
  ["Took on a contract to clear cap", "-3.14 (0.79)\np < 0.001", "-1.28 (0.98)\np = 0.19", "-1.10 (1.15)\np = 0.34", "-0.94 (0.90)\np = 0.30"],
  ["A new general manager selling a contract signed by his predecessor", "+0.54 (0.50)\np = 0.28", "-0.59 (0.76)\np = 0.44", "+0.08 (0.76)\np = 0.92", "-0.85 (0.71)\np = 0.24"],
  ["Received a restricted free agent in his final contract season", "+0.44 (0.39)\np = 0.25", "+0.65 (0.70)\np = 0.35", "-0.12 (0.72)\np = 0.87", "+0.68 (0.66)\np = 0.30"],
  ["Received only picks in rounds 6 and 7", "-0.45 (0.23)\np = 0.052", "-0.57 (0.40)\np = 0.15", "-0.55 (0.45)\np = 0.22", "-0.54 (0.40)\np = 0.17"],
  ["Received a player at all", "+0.76 (0.42)\np = 0.071", "+0.95 (0.61)\np = 0.12", "+1.28 (0.60)\np = 0.034", "+0.83 (0.55)\np = 0.14"],
  ["Trades (two rows each)", "556", "556", "556", "556"],
  ["R-squared (no constant)", "0.405", "0.133", "0.154", "0.133"],
], [36, 16, 16, 16, 16]));
add(NOTE("As Table A1, with each player characteristic counted when any player received has it (production, its "
  + "excess over the forecast and the games share averaged over the players received, weighted by cap hit)."));
add(LABEL("Table A3. Section 4's regressions: the price paid for the main player"));
add(table(["Variable", "Price on the models' value", "Price on what the seasons played delivered", "Price, two-stage least squares", "First stage: the models' value on what was delivered"], [
  ["Performance value: the models' forecast", "+0.26 (0.11)\np = 0.017", "", "", ""],
  ["Performance value: what the seasons played delivered", "", "+0.18 (0.09)\np = 0.048", "", "+0.47 (0.02)\np < 0.001"],
  ["Performance value: the forecast, corrected (two-stage)", "", "", "+0.39 (0.19)\np = 0.045", ""],
  ["Cap cost (present value of the cap hit)", "-0.27 (0.10)\np = 0.007", "-0.22 (0.09)\np = 0.014", "-0.37 (0.16)\np = 0.028", "+0.37 (0.02)\np < 0.001"],
  ["Constant", "-0.21 (0.11)\np = 0.058", "-0.19 (0.11)\np = 0.090", "-0.17", "-0.06 (0.07)\np = 0.41"],
  ["Clubs (trades)", "886 (640)", "886 (640)", "886 (640)", "886 (640)"],
  ["R-squared", "0.057", "0.049", "", "0.926"],
], [36, 16, 16, 16, 16]));
add(NOTE("All trades to March 2026, main player rule. The first three columns regress the price paid for the main player; "
  + "the fourth regresses the models' performance value, and its prediction is the corrected performance value in the "
  + "third. Standard errors in brackets, clustered by trade, except the third column's, which come from 2,000 resamples "
  + "of trades, and the fourth's, which are ordinary."));

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
