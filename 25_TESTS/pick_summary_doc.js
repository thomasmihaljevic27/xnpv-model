// pick_summary_doc.js -- builds "Valuing Draft Picks.docx" (40_DOCS/Supervisor_Drafts/).
//
// WHY (Thomas, 2026-10-09): a summary of the draft-pick work for the supervisor, set out as the
// problem, the approach and where the work stands, with graphs and tables that show why each
// decision was made. Reader-facing: it does not name its reader or refer to a meeting (CLAUDE.md).
//
// NUMBERS: computed figures come from OUTPUT_DIR/pick_summary/numbers.json (pick_summary_figures.py,
// which reads the live outputs of pick_curve.py v1.1 and traded_pick_values.py v1.1). Test results
// are literals copied from the recorded runs, each marked with its source below:
//   [shape]  25_TESTS/pick_curve_shape_test.py v1.0 log (held-out misses, redraws won)
//   [valid]  25_TESTS/pick_bacon_validation.py v1.0
//   [form]   25_TESTS/pick_star_form_test.py v1.0 and the star-only comparison of 2026-10-09
//   [look]   25_TESTS/pick_lookahead_check.py v1.0 (shape by era)
//   [cost]   25_TESTS/pick_cost_and_year_tests.py v1.0
//   [goal]   25_TESTS/pick_goalie_test.py v1.0
//   [win]    25_TESTS/draft_window_count.py v1.0
//   [rights] 25_TESTS/pick_star_and_rights_checks.py v1.1
// The price line's dollar figures at the 2025-26 cap are from skater_forward_projection.py's
// XNPV1_RATE comment block (the locked line).
//
// Run (docx installed in a folder on NODE_PATH):  node 25_TESTS/pick_summary_doc.js

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType,
  AlignmentType, HeadingLevel, BorderStyle, ShadingType, LevelFormat, Footer, PageNumber,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const FIG = path.join(ROOT, "30_OUTPUT", "pick_summary");
const N = JSON.parse(fs.readFileSync(path.join(FIG, "numbers.json"), "utf8"));
const OUTFILE = path.join(ROOT, "40_DOCS", "Supervisor_Drafts", "Valuing Draft Picks.docx");

// ---- helpers ------------------------------------------------------------------------------------
const FONT = "Calibri";
const f1 = (x) => Number(x).toFixed(1);
const f2 = (x) => Number(x).toFixed(2);
const money = (x) => `$${f1(x)}M`;
const money2 = (x) => `$${f2(x)}M`;
const comma = (x) => Number(x).toLocaleString("en-US");

function runs(text, base = {}) {
  // **bold** and *italic* markers inside a string
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), font: FONT, ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, font: FONT, ...base }));
    else out.push(new TextRun({ text: t.slice(1, -1), italics: true, font: FONT, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), font: FONT, ...base }));
  return out;
}
const P = (text, opts = {}) => new Paragraph({ children: runs(text, opts.run || {}), spacing: { before: 60, after: 120, line: 276 },
  alignment: opts.align || AlignmentType.LEFT, ...(opts.para || {}) });
const H1 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text, font: FONT })],
  spacing: { before: 280, after: 120 } });
const H2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text, font: FONT })],
  spacing: { before: 200, after: 80 } });
const BUL = (text) => new Paragraph({ numbering: { reference: "bul", level: 0 }, children: runs(text), spacing: { after: 60 } });
const NUM = (text, ref = "num") => new Paragraph({ numbering: { reference: ref, level: 0 }, children: runs(text), spacing: { after: 60 } });
const FORMULA = (text) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 120 },
  children: [new TextRun({ text, font: "Cambria Math", italics: true })] });
const CAPTION = (text) => new Paragraph({ spacing: { before: 40, after: 200 },
  children: runs(text, { size: 18, color: "52514E" }) });
const TABLE_TITLE = (text) => new Paragraph({ spacing: { before: 160, after: 60 }, keepNext: true,
  children: runs(text, { size: 20, bold: true }) });

function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20), data: b };
}
function FIGURE(file, caption) {
  const { w, h, data } = pngSize(path.join(FIG, file));
  const width = 520;                                  // px at 96 dpi, about 5.4 in
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120 }, keepNext: true,
      children: [new ImageRun({ type: "png", data, transformation: { width, height: Math.round(width * h / w) } })] }),
    CAPTION(caption),
  ];
}

const border = { style: BorderStyle.SINGLE, size: 4, color: "C9C8C3" };
const borders = { top: border, bottom: border, left: border, right: border };
function TABLE(header, rows, widths, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (text, i, head, keep) => new TableCell({
    borders, width: { size: widths[i], type: WidthType.DXA },
    shading: head ? { fill: "EFEEEA", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: [new Paragraph({ keepNext: keep,          // keep each row with the next, so a table stays on one page
      alignment: (i > 0 && (opts.numeric || []).includes(i)) ? AlignmentType.RIGHT : AlignmentType.LEFT,
      children: runs(String(text), { size: 18, bold: !!head }) })],
  });
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: header.map((t, i) => cell(t, i, true, true)) }),
      ...rows.map((r, j) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, i, false, j < rows.length - 1)) }))],
  });
}

// ---- computed numbers ---------------------------------------------------------------------------
const sc = Object.fromEntries(N.scales.map((r) => [r.scale_kind === "pooled" ? "pooled" : String(r.trade_season), r]));
const POOLED = sc.pooled.scale_M;
const V = N.values_by_pick;
const pt = N.worked_point;
const ptVal = pt.seasons.reduce((a, s) => a + s.value_M, 0);
const ptCost = pt.seasons.reduce((a, s) => a + s.cost_M, 0);
const tt = N.traded_totals;
const method = Object.fromEntries(N.traded_by_method.map((r) => [r.method, r]));
const f5 = N.f5;
const f3 = N.f3;
const pl = N.players;

// ---- the document -------------------------------------------------------------------------------
const children = [];
const add = (...xs) => xs.flat().forEach((x) => children.push(x));

add(new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 60 },
  children: [new TextRun({ text: "Valuing Draft Picks", bold: true, size: 40, font: FONT })] }));
add(P("The problem, the approach, and where the work stands. October 2026.", { run: { color: "52514E" } }));

// 1
add(H1("1. The Problem"));
add(P("The trade study compares what each club gave and received in a trade, and it needs each asset on one scale. Players are valued from their contracts: the surplus a club expects from a player is the market price of the wins he is forecast to deliver, less his cap hit, summed over the seasons the club controls him. A draft pick has no contract and no player yet. It is a claim on whoever the club selects at a slot, so its value has to come from what selections at that slot have delivered in the past."));
add(P(`Two features of the draft make this hard. First, outcomes are very uneven: ${comma(N.routes['never played'])} of the ${comma(pl.picks)} players drafted from 2007 to 2017 never played an NHL game, while a few became stars who returned tens of millions of dollars in surplus. Second, a pick's outcome takes about nine seasons to arrive. The drafts that can be measured completely are, therefore, years older than the trades being priced, and a curve built from all of the history available today uses information that no club had at the time of most trades. This is look-ahead bias, and the design below is built to keep it out of the value of a pick at the moment it is traded.`));
add(P("The document follows the build in order: pricing each drafted player in the player model's currency (Section 3), turning those prices into a value for each draft slot (Section 4), limiting that value to what was knowable at each trade (Section 5), and valuing the picks that changed hands (Section 6). Section 7 tests the cost side, Section 8 outlines the prospect model, which is not yet built, and Section 9 lists the limits and the remaining work."));

// 2
add(H1("2. The Approach in Brief"));
add(P("A pick's value is a dollar scale for the trade season times the probability that a player taken at that slot becomes a star:"));
add(FORMULA("value of a pick at slot k, traded in season T  =  b(T) × P(star | slot k)"));
add(P(`The probability comes from Patrick Bacon's draft baseline, the same provider as the WAR used throughout the model. A star is a player whose career WAR per 82 games is 1.8 or more for a forward, or 1.23 or more for a defenceman, which Bacon describes as roughly the top 20% of forwards and top 15% of defencemen. The scale b(T) is estimated from our own data: it is the surplus, in dollars at the 2025-26 cap, that one unit of star probability has historically delivered, fitted only on drafts that had played out before trade season T. For example, a #1 pick (star probability ${f1(100 * V["1"].p_star)}%) traded in 2019-20 is worth ${money(V["1"].knowable_2019)}, and a #32 pick (${f1(100 * V["32"].p_star)}%) is worth ${money2(V["32"].knowable_2019)}.`));
add(P("Table 1 lists each decision, what it was chosen over, and the evidence. The sections that follow walk through them in order."));
add(TABLE_TITLE("Table 1. Decisions behind the pick curve"));
add(TABLE(["Step", "Chosen", "Tested against", "Evidence"], [
  ["Control window", "Draft to free agency under CBA Group 3 (27, or seven accrued seasons)", "A fixed nine seasons", "Section 3; matches PuckPedia's free-agency year for 1,151 of 1,183 players"],
  ["Value of a season", "Wins delivered, on the player contracts' price line, as a one-year deal", "The entry-level deal's remaining term", "One currency for picks and players"],
  ["Cost", "Entry-level maximum, then one-year qualifying offers", "Actual cap hits; market cost once arbitration-eligible", "Section 7, Figure 5"],
  ["Shape across picks", "Bacon's star probability", "Straight line, log, bendable curve, log squared, two-part model", "Table 3, Figures 1 and 2"],
  ["Form on the probability", "Straight line through zero", "Intercept, squared term, power curve", "Table 4"],
  ["Scale", "Fitted on drafts complete by the trade", "All drafts pooled (kept as sensitivity)", "Section 5, Figures 3 and 4"],
  ["Entry-level slides", "None", "CBA slides; slides at any age", "Scale moves under 0.5%"],
  ["Negative careers", "Counted as negative", "Floored at zero", "Floor raises the scale 4.1%"],
  ["Goalies", "Pooled with skaters", "Skaters only; separate goalie scale", "Pooling moves the scale 2%"],
  ["Rights that lapsed", "Worth zero to the pick", "Credited to the pick", "2.6% of surplus; scale moves under 1%"],
  ["Future picks", "Round average", "Last draft's slot", "A slot a year or more ahead is not known"],
], [1600, 2700, 2400, 2660]));

// 3
add(H1("3. Pricing One Drafted Player"));
add(P(`The curve starts from what each drafted player delivered to the club that held his rights, priced the same way the player model prices a contract. Each selection in the 2007-2017 drafts enters, ${comma(pl.picks)} picks in all (${pl.goalies} goalies), including the ${comma(N.routes['never played'])} who never played an NHL game. Those players are a large part of what a pick is, and leaving them out would value a pick as if it always produced an NHL player.`));
add(H2("The window: the seasons of club control"));
add(P("A pick buys a club the exclusive right to sign and retain a player until he reaches unrestricted free agency. After that he is paid a market salary, so the surplus a pick can deliver ends there. The window, therefore, runs from the draft to free agency under the collective agreement's Group 3 rule (Section 10.1(a)): a player becomes free once his contract has expired and he is 27 as of June 30, or has seven accrued seasons. An accrued season is a league year with 40 or more games on an NHL active roster, 30 for a goalie (Article 1)."));
add(P("The data has games played, not roster games, so games played stand in. That under-counts accrued seasons for injured players and backup goalies. As a check, the rule's free-agency year matches PuckPedia's for 1,151 of the 1,183 drafted players PuckPedia covers; PuckPedia is earlier for 19 (injured players and backup goalies) and later for 13. The data ends with 2025-26, which cuts short 29 of the 217 windows in the 2017 class by one season. These are kept and stated as a limitation. Under the scale adopted in Section 5 they touch no trade studied here, since the 2017 draft enters that scale only for trades from 2026-27 on; in the pooled sensitivity, leaving the 2017 draft out moved the log curve of Section 4 by at most $0.35M, at the first overall pick."));
add(H2("Value: wins delivered, on the contracts' price line"));
add(P("Each season the player spends in the NHL is valued at the market price of the wins he delivered, on the same price line that values player contracts. On that line, at the 2025-26 cap, a forward's season is priced at -$0.416M, plus $1.668M per win ($2.012M for a defenceman), plus $0.853M for each year of contract length, and never below the league minimum. Each drafted player's season is priced as a one-year deal, so it carries one year of the length term. Goalies are priced on the goalie line in the same way. Two adjustments keep the seasons comparable:"));
add(BUL("**Short seasons.** WAR in 2012-13, 2019-20, and 2020-21 is scaled to 82 games (by 82/48, 82/70, and 82/56), because a shortened schedule deflates each season's total without saying anything about the player."));
add(BUL("**Brief call-ups.** A season under 10 NHL games has its value and cost scaled by games over 82, because the club carries his cap hit only for the days he is on the roster."));
add(H2("Cost: what the club had to pay to keep him"));
add(P("While his entry-level contract runs, the player costs the maximum entry-level salary for his draft class ($875K for 2007-08, $900K for 2009-10, and $925K for 2011-2017). The contract lasts three seasons if he is 18 to 21 at his first NHL season, two at 22 or 23, and one at 24 or older (CBA Section 9.1(b)), counted by calendar from that season. After it, the club holds his rights by offering a one-year qualifying offer each summer: for salaries under $1M, 105% or 110% of the prior salary under the agreement's bands, capped at $1M, and never below the league minimum. A season he spends outside the NHL is worth nothing and costs nothing, since a minor-league salary does not count against the cap."));
add(P("The qualifying-offer chain prices the club's right, which is what the club can compel. In practice, clubs often pay more, either through salary arbitration or by signing a star to a long contract early. Section 7 measures that gap and keeps the alternatives as sensitivities."));
add(H2("Three rules about whose surplus counts"));
add(BUL("**Negative careers stay negative.** A player who holds a roster spot while delivering less than his cost was a loss to the club. Flooring each career at zero would raise the scale by 4.1%."));
add(BUL(`**Rights that lapsed are worth zero to the pick.** A club that never signs its pick loses him. ${N.routes.lapsed} picks played their first NHL season for another club without being traded (for example, Jared Spurgeon, drafted by the Islanders and signed by Minnesota). Their ${money(pl.lapsed_zeroed_M)} of surplus never reached the club holding the pick, of ${money(pl.total_before_M)} in all.`));
add(BUL("**Goalies are pooled with skaters.** When a pick is traded, nobody knows whether it will become a goalie, so its value averages over everyone drafted at that slot."));
add(H2("A worked case"));
add(P(`Table 2 prices Brayden Point, drafted 79th in 2014. He played junior hockey for two seasons, which count as zero, and reached free agency after 2022-23. He delivered ${money(ptVal)} of value for ${money(ptCost)} of cost, a surplus of ${money(pt.total_M)}, one of the largest in the sample. His slot's star probability was ${f1(100 * pt.p_star)}%, so the curve values a #79 pick at about ${money2(POOLED * pt.p_star)} on the pooled scale. Point is one of the few draws that pays off at that slot; the curve averages him with the many that do not.`));
add(TABLE_TITLE("Table 2. Brayden Point (2014, #79), season by season ($M at the 2025-26 cap)"));
const ptRows = pt.seasons.map((s) => [`${s.season}-${String(s.season + 1).slice(2)}`, String(s.gp), f2(s.war_82),
  s.in_entry_level ? "Entry-level" : "Qualifying offer", f2(s.value_M), f2(s.cost_M), f2(s.value_M - s.cost_M)]);
ptRows.push(["Total", "", "", "", f2(ptVal), f2(ptCost), f2(pt.total_M)]);
add(TABLE(["Season", "NHL games", "Season WAR", "Contract", "Value", "Cost", "Surplus"], ptRows,
  [1150, 1100, 1500, 1700, 1300, 1300, 1310], { numeric: [1, 2, 4, 5, 6] }));
add(CAPTION("Value and cost are shares of each season's cap, stated at the 2025-26 cap of $95.5M; with 3% cap growth and 3% discounting, summing cap shares is the player model's convention. WAR in 2019-20 and 2020-21 is scaled to 82 games. Source: pick_curve.py, pick_curve_seasons.csv."));

// 4
add(H1("4. From Players to a Curve"));
add(P("With each drafted player priced, the next step relates the dollars to the draft slot. A single slot has only 11 picks across the eleven drafts, far too few to average on its own, but about 2,300 picks are enough to estimate one smooth relationship between slot and value. The question is which shape that relationship should take."));
add(H2("Which shape"));
add(P("Figure 1 shows the average surplus at each pick and three of the candidate curves. Value falls steeply over the first ten picks and then flattens into a long tail where most picks return little or nothing. A straight line in pick number cannot follow that, and it values the first overall pick at $4.6M against the $28.6M that first picks actually returned."));
add(FIGURE("f1_shape.png", "Figure 1. Average surplus at each pick (skaters, 2007-2017) and three fitted shapes, at an average draft year. Each shape is fitted with draft-year indicators. Source: pick_curve_shape_test.py."));
add(P("Seven shapes were scored on how well they predict a draft they were not fitted on: each is fitted on ten drafts, predicts each pick in the eleventh, and the process repeats for all eleven. The rule for choosing was set before the run. A shape with more fitted numbers must predict better than each simpler shape in at least 1,950 of 2,000 redraws of the eleven drafts; otherwise the simpler one stands. Table 3 gives the results."));
add(TABLE_TITLE("Table 3. Held-out miss by shape ($M a pick; skaters, 2007-2017)"));
add(TABLE(["Shape", "Numbers fitted", "Miss (RMSE)", "Beats log curve in", "Note"], [
  ["Straight line in pick number", "2", "5.712", "0 of 2,000", "Values #1 at $4.6M"],
  ["Log of the pick", "2", "5.384", "-", "Values #1 at $13.2M"],
  ["Bendable curve, a + b(pick^c - 1)/c", "3", "5.219", "1,946", "Misses the bar by four"],
  ["Log plus log squared", "3", "5.213", "1,985", "Rises after pick 137"],
  ["Bacon's NHL and star probabilities", "3", "5.224", "1,981", "Falls throughout; adopted"],
  ["Two-part: P(plays) × value if he plays", "4", "5.324", "2,000", "Loses to each three-number shape"],
  ["Benchmark: the average at each pick, forced to fall", "-", "5.258", "-", "Reported only"],
], [3100, 1000, 1100, 1400, 2760], { numeric: [1, 2, 3] }));
add(CAPTION("Miss is the root mean squared error over held-out picks. The bendable curve nests the straight line (c = 1) and the log (c → 0) (Box and Cox, 1964). Source: pick_curve_shape_test.py v1.0."));
add(P("The log curve beats the straight line in each of the 2,000 redraws. Three shapes with a third number improve on the log curve by a similar margin, and they differ from each other by less than $0.02M a pick. Of these, log plus log squared cleared the bar but turns back up after pick 137, so it values a seventh-round pick above a fifth-round one; the bendable curve fell four redraws short. Bacon's probabilities cleared the bar and fall throughout. They were adopted because they fit as well as the best flexible curve, they are fixed in advance rather than fitted to these drafts' dollars, and they come from the same provider as the rest of the model's player data. The benchmark, which follows the data pick by pick, predicts held-out drafts worse than the best formulas, so the formulas are not leaving much on the table."));
add(H2("Do our data support Bacon's probabilities?"));
add(P("Two checks say they do. First, once his probabilities are in the regression, adding the log of the pick adds nothing (coefficient +0.14, standard error 1.21, p = 0.91), and our own slot-only curves land within $0.15M to $0.24M a pick of his on average. Second, Figure 2 applies his star definition to our drafted skaters from the 2007-2015 drafts, whose careers are mostly complete. Reading a star as also needing 200 NHL games, so that a rate over a handful of games does not count, " +
  `${N.f2_overall.stars} of ${comma(N.f2_overall.picks)} became stars (${f1(N.f2_overall.ours)}%) against his ${f1(N.f2_overall.bacon)}%, and each pick range is within two standard errors of his probability.`));
add(FIGURE("f2_star_rates.png", "Figure 2. Bacon's star probability against the share of our drafted skaters who became stars, by pick range (2007-2015 drafts; bars on our share are two standard errors). Source: pick_star_and_rights_checks.py v1.1."));
add(P("These checks are not independent confirmation. His probabilities are fitted on largely the same drafts with the same WAR, so they show that our data and his agree, not that both are right."));
add(H2("The form on the star probability"));
add(P("Bacon provides two probabilities by slot: becoming an NHL player (200 or more games) and becoming a star. In dollars, the NHL-player probability adds nothing once the star probability is in (coefficient -0.05, standard error 2.15, against +31.3 with standard error 6.9 for the star probability), so the curve uses the star probability alone. That leaves two questions: whether the line needs an intercept, and whether it is straight. Table 4 answers both under the same rule."));
add(TABLE_TITLE("Table 4. Dollars on the star probability: four forms ($M a pick)"));
add(TABLE(["Form", "Numbers fitted", "Miss (RMSE)", "Beats through-zero in"], [
  ["Straight line through zero: b × P(star)", "1", "5.214", "-"],
  ["With an intercept: a + b × P(star)", "2", "5.215", "30 of 2,000"],
  ["With a squared term", "3", "5.232", "5 of 2,000"],
  ["Power curve, a + b × P(star)^k (fitted k = 1.03)", "3", "5.227", "0 of 2,000"],
], [4200, 1300, 1400, 2460], { numeric: [1, 2, 3] }));
add(CAPTION("Source: pick_star_form_test.py v1.0 (skaters, first-look pricing)."));
add(P("The simplest form wins: a pick is worth its star probability times a fixed number of dollars. The line is straight in the star probability, not in the pick number. Across picks the curve keeps the steep shape of Bacon's probabilities: the value falls by about a fifth from #1 to #2, and by about a third from #20 to #32, from a much smaller base. The scale, however, is not the value of a star. It also carries the surplus of good players who are not stars, who are more common where the star probability is higher; it is best read as dollars per point of star probability."));

// 5
add(H1("5. Look-Ahead: Which Drafts Set the Scale"));
add(P("Two parts of the curve could carry information a club did not have when it traded. The shape comes from Bacon's probabilities, which are fitted on drafts through 2021. The scale is fitted on the realised careers of the 2007-2017 drafts. Each was checked."));
add(P("The shape holds in early and late drafts alike: fitted separately on the 2007-2011 drafts and the 2012-2017 drafts, adding the log of the pick to his probabilities adds nothing in either (p = 0.61 and p = 0.79). A curve shaped on early drafts alone would, therefore, have the same shape. His own model cannot be refitted on earlier drafts, so this shows his shape is supported by early drafts, not that his model never saw later ones."));
add(P(`The scale does not hold. Figure 3 fits it on each draft separately. The test that all eleven are equal rejects (chi-squared ${f1(f3.wald_chi2)} on ${f3.wald_df} degrees of freedom, p = ${f3.wald_p.toFixed(4)}); after allowing for sampling noise, a typical draft's scale sits about ${f1(f3.sd_beyond_noise)} (in $M per 100% star probability) from the average, ${Math.round(100 * f3.sd_beyond_noise / POOLED)}% of the pooled scale. The 2012 draft is the weakest (${f1(f3.scale[5])}) and 2015 the strongest (${f1(f3.scale[8])}). The 2014-2017 drafts all sit above the pooled scale, and none of them had played out at the time of any trade studied here.`));
add(FIGURE("f3_class_scales.png", "Figure 3. The scale fitted on each draft class (adopted pricing, all positions), with the pooled scale. Source: pick_summary_figures.py on pick_curve_players.csv."));
add(P("The pick's value at the trade, therefore, uses the scale a club could have known: fitted only on drafts made nine or more seasons before the trade season, whose windows had largely run out. Figure 4 and Table 5 show the result. The study asks two questions about each pick: what it was worth when it was traded, and what it turned out to be worth. Realised careers answer the second. A pooled scale would let part of that answer leak into the first, and because the later drafts were richer it would make each pick look more valuable at the trade than it could have seemed. The pooled scale is kept as the sensitivity."));
add(FIGURE("f4_knowable_scale.png", "Figure 4. The knowable scale by trade season against the pooled scale (bars: two standard errors). Source: pick_curve.py v1.1, pick_curve_scales.csv."));
add(TABLE_TITLE("Table 5. Value of a pick by slot ($M at the 2025-26 cap)"));
const t5 = ["1", "2", "3", "5", "10", "16", "20", "32", "64", "100", "200"].map((k) => [
  `#${k}`, f1(100 * V[k].p_star) + "%", f2(V[k].knowable_2017), f2(V[k].knowable_2019), f2(V[k].knowable_2021), f2(V[k].pooled)]);
add(TABLE(["Pick", "Star probability", `Traded 2017-18 (scale ${f1(sc["2017"].scale_M)})`, `Traded 2019-20 (scale ${f1(sc["2019"].scale_M)})`,
  `Traded 2021-22 (scale ${f1(sc["2021"].scale_M)})`, `Pooled (scale ${f1(POOLED)})`], t5,
  [900, 1300, 1800, 1800, 1800, 1760], { numeric: [1, 2, 3, 4, 5] }));
add(CAPTION(`Standard errors of the knowable scale: ${f1(sc["2017"].se_M)} (2017-18, two drafts), ${f1(sc["2019"].se_M)} (2019-20), ${f1(sc["2021"].se_M)} (2021-22); pooled ${f1(sc.pooled.se_M)}. Source: pick_curve.py v1.1.`));
add(P(`The cost is noise early on: the 2017-18 scale rests on two drafts. Across the ${tt.picks} traded picks, the knowable scale values them at ${money(tt.knowable)} in all against ${money(tt.pooled)} pooled, ${f1(100 * (tt.knowable / tt.pooled - 1))}%. The player model pools its price line across seasons; that is defensible there because the line passed its test of stability over time, which the pick scale fails.`));

// 6
add(H1("6. Valuing the Picks That Changed Hands"));
add(P("A traded pick's slot is often unknown at the trade. The curve needs a slot, or a set of slots, for each one:"));
add(NUM("**Traded during its own draft:** the actual slot, which is known on the draft floor."));
add(NUM("**The next draft's pick, traded during the season:** the slot that the original team's place in the standings on the trade date gives (points percentage, worst first). The lottery and playoff results that later reorder the draft are not modelled; once the regular season ends, the standings are final."));
add(NUM("**The next draft's pick traded before that season's first game, or any later draft's pick:** the average star probability over the round's slots, for that draft's number of teams. A slot a year or more ahead is not known, and the round average assumes no information about it."));
add(P(`"The next draft" is the first draft on or after the trade date. This matters because the 2020 draft was held in October and the 2021 draft in late July, so picks for them were still being traded after July 1. Table 6 counts the ${tt.picks} picks traded from July 2017 to March 28, 2022, where the trade inventory ends. Projected from the trade-date standings, ${N.projection.within3} of ${N.projection.picks} slots land within three of the slot actually used (median miss ${N.projection.median_miss}); the largest miss among first-round picks is ${N.projection.first_round_max}, which is lottery movement.`));
add(TABLE_TITLE("Table 6. Traded picks by how the slot was set ($M)"));
const mrow = (k, lab) => [lab, String(method[k].picks), f1(method[k].knowable), f1(method[k].pooled)];
add(TABLE(["How the slot was set", "Picks", "Knowable scale", "Pooled scale"], [
  mrow("actual slot (traded during the draft)", "Actual slot, traded during the draft"),
  mrow("slot on the trade date", "Standings on the trade date"),
  mrow("round average (before the season's first game)", "Round average, before the season began"),
  mrow("round average (a later draft)", "Round average, a later draft"),
  ["Total", String(tt.picks), f1(tt.knowable), f1(tt.pooled)],
], [4200, 1100, 2000, 2060], { numeric: [1, 2, 3] }));
add(P("By round, a first-round pick averages " + money2(N.traded_by_round[0].mean) + ", a second-round pick " + money2(N.traded_by_round[1].mean) +
  ", a third " + money2(N.traded_by_round[2].mean) + ", and a seventh " + money2(N.traded_by_round[6].mean) +
  `. Most traded picks are late: of these ${tt.picks}, 61 were first-round picks. The ${tt.conditional} conditional picks are valued as if unconditional until each condition is resolved against what happened.`));

// 7
add(H1("7. The Cost Side and Its Alternatives"));
add(P("The qualifying-offer chain is the main cost, and its alternatives are kept beside it. Each one changes what a player's surplus is, so they are compared by how far they move the curve, not by predictive fit. Table 7 gives the effect of each on the scale, measured on skaters."));
add(TABLE_TITLE("Table 7. Cost and definition alternatives (effect on the scale)"));
add(TABLE(["Alternative", "Scale", "Change", "Status"], [
  ["Main: qualifying-offer chain, slides modelled (test basis)", "31.37", "-", "Reference"],
  ["Slides only for 18- and 19-year-olds (CBA 9.1(d))", "31.27", "-0.3%", "Not adopted"],
  ["No slides", "31.21", "-0.5%", "Adopted (simplest)"],
  ["Each career floored at zero", "32.64", "+4.1%", "Not adopted"],
  ["Market cost once eligible for arbitration (CBA 12.1)", "14.06", "-55%", "Kept as sensitivity"],
  ["Actual cap hits (first round only)", "-", "2-3 times the chain's cost", "Reference only (hindsight)"],
], [4400, 1000, 1700, 2260], { numeric: [1, 2] }));
add(CAPTION("Scale in $M per 100% star probability, pooled over all drafts. Source: pick_cost_and_year_tests.py v1.0; actual cap hits from top_pick_control_look.py v1.1."));
add(P("Slides and the floor barely matter. The cost rule itself matters a great deal. Figure 5 compares the chain with what clubs actually paid their first-round picks over the same windows, using PuckPedia's cap hits from 2018-19 and CapWages' before then."));
add(FIGURE("f5_control_cost.png", "Figure 5. Value delivered and cost over the control window, per first-round skater who reached the NHL (2007-2017 drafts). Source: top_pick_control_look.py v1.1."));
add(P(`Clubs paid ${f1(f5[0].cost_actual / f5[0].cost_model)} times the chain's cost for picks 1-10, ${f1(f5[1].cost_actual / f5[1].cost_model)} times for picks 11-15, and ${f1(f5[2].cost_actual / f5[2].cost_model)} times for picks 16-32. The gap runs through the whole first round. Actual cap hits are not adopted, for two reasons. They add hindsight to the cost side, since they record what each club and player negotiated years after the draft. And a long extension averages the price of the free-agent years it buys into each season's cap hit, so it charges the control window for seasons outside it.`));
add(P("The gap still matters for the trade study. Picks are costed on the chain and players on their actual cap hits, so pick surplus is overstated relative to player surplus. In a back-test, that asymmetry could make clubs look as if they give picks away too cheaply. The arbitration version, which charges market cost from the point a player can elect arbitration and cuts the scale by more than half, is the check: a finding about picks that survives it is not a product of the cost rule. It is to be run before the back-test results are read."));
add(P("Goalies were tested the same way. The 233 goalie picks average $2.40M of surplus against $1.68M for skaters, but their value sits in late picks (Braden Holtby at #93, Juuse Saros at #99, Igor Shesterkin at #118) and does not follow the slot. A separate goalie scale comes out at 84.3, which would value a first-overall goalie near $63M, and pooling goalies with skaters moves the scale by 2%."));

// 8
add(H1("8. Prospects: The Next Model"));
add(P("A prospect is a drafted or undrafted player who has not reached an NHL roster and whose signing rights are traded. Unlike a pick, the player is known: his draft slot, his production since the draft, his age, and his size. The planned approach starts from the pick curve's value for his slot and updates it with his own record:"));
add(BUL("**The starting value.** The pick curve's value for his draft slot, which already prices the chance that a player taken there becomes a star."));
add(BUL("**His production.** Points per game in junior, college, and European leagues, converted to NHL terms with Bacon's era-varying equivalency factors, with his recent seasons weighted 50/30/20 as everywhere else in the model."));
add(BUL("**His age and size.** Both are candidate inputs; whether each adds anything once production is known is a question for the specification's tests."));
add(BUL("**Undrafted prospects.** The same model without the slot's starting value."));
add(P("The data is in hand. The Elite Prospects pull covers 34 leagues from 2006-07 to 2025-26 (459,898 skater seasons), with biographies for 4,953 players, and the link from Elite Prospects to NHL records agrees on birthdates for 4,734 of 4,760 drafted players. The open questions for the specification are how much weight the slot keeps once a player's own production is observed, how the outcome is defined (the same control-window surplus as the pick curve is the natural choice), and how goalies are handled."));

// 9
add(H1("9. Limitations and Remaining Work"));
add(P("The main limitations of the pick curve as built:"));
add(BUL("Bacon's probabilities are fitted on drafts through 2021. The shape was shown to hold in early drafts, but his model cannot be refitted on what was knowable at each trade."));
add(BUL("The cost side understates what clubs pay for control (Figure 5). Entry-level performance bonuses are not charged, and the Group 6 rule that frees older players with few NHL games is not applied."));
add(BUL("Games played stand in for roster games in the window, the lottery is not modelled in projected slots, and 29 windows in the 2017 draft are one season short."));
add(P("The remaining work on picks and prospects, in order:"));
add(NUM("Resolve the 113 conditional picks against what happened.", "num2"));
add(NUM("Run the arbitration cost version as a sensitivity before the back-test is read.", "num2"));
add(NUM("Specify the prospect model step by step, then build it on the data above.", "num2"));

add(H2("References"));
add(P("Bacon, P. Draft model guide and baseline probability by draft slot. hockeystats.com/draft/guide, accessed October 9, 2026."));
add(P("Box, G. E. P., and Cox, D. R. (1964). An analysis of transformations. Journal of the Royal Statistical Society, Series B, 26(2), 211-252."));
add(P("National Hockey League and National Hockey League Players' Association (2013). Collective Bargaining Agreement, Article 1 and Sections 9.1, 10.1, and 12.1."));

// ---- assemble -------------------------------------------------------------------------------------
const doc = new Document({
  creator: "Thomas Mihaljevic",
  title: "Valuing Draft Picks",
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: FONT, color: "0B0B0B" }, paragraph: { outlineLevel: 0, keepNext: true } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 23, bold: true, font: FONT, color: "2A2A28" }, paragraph: { outlineLevel: 1, keepNext: true } },
    ],
  },
  numbering: { config: [
    { reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
    { reference: "num", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] },
    { reference: "num2", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1260, bottom: 1260, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "52514E", font: FONT })] })] }) },
    children,
  }],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUTFILE, buf); console.log("wrote", OUTFILE, buf.length, "bytes"); });
