// pick_summary_doc.js v2.0 -- builds "Valuing Draft Picks.docx" (40_DOCS/Supervisor_Drafts/).
//
// v2.0 (2026-10-09): rewritten on a four-point spine agreed with Thomas after v1.0 read as a long
// info dump: (1) a pick is a ticket on a star, value = star probability x dollar scale; (2) value is
// what a drafted player delivered during his control years, in the contracts' currency; (3) the
// dollar scale uses only drafts a club could have seen finish; (4) the cost of keeping a drafted
// player is the main risk. Everything else is one line in Appendix A. Prospects are left for a
// separate document. Written to the writing-style skill; reader-facing (no reader named, no meeting).
//
// NUMBERS: computed figures come from OUTPUT_DIR/pick_summary/numbers.json (pick_summary_figures.py
// v1.1, which reads pick_curve.py v1.1 and traded_pick_values.py v1.1 outputs). Test results are
// literals copied from the recorded runs:
//   p = 0.91 (pick number added to Bacon)         pick_bacon_validation.py v1.0
//   5.9% / 5.3% stars, 2007-2015 skaters          pick_star_and_rights_checks.py v1.1
//   other shapes within ~$0.01M; logsq turns up   pick_curve_shape_test.py v1.0
//   p = 0.61 / 0.79 by era                        pick_lookahead_check.py v1.0
//   arbitration -55%; slides; floor +4.1%         pick_cost_and_year_tests.py v1.0
//   2.3x for picks 11-15                          top_pick_control_look.py v1.1 (also in numbers.json f5)
//   goalies +2%, 84.3, ~$63M                      pick_goalie_test.py v1.0
//   form test: none beat through-zero > 30/2000   pick_star_form_test.py v1.0
//   NHL-player probability -0.05 (se 2.15)        the star-only comparison of 2026-10-09
//   1,151 of 1,183; 29 of 217                     draft_window_count.py v1.0
//   $1.68M against $1.50M (call-ups)              pick_regression_first_look.py v1.1
//   2.6% / 0.5% (lapsed rights)                   pick_curve.py v1.1 log / pick_star_and_rights_checks.py v1.1
//
// Run:  NODE_PATH=<folder with docx> node 25_TESTS/pick_summary_doc.js   (LINT_OUT=<file.md> also
// writes the prose as markdown for the clarity linter)

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType,
  AlignmentType, HeadingLevel, BorderStyle, ShadingType, Footer, PageNumber,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const FIG = path.join(ROOT, "30_OUTPUT", "pick_summary");
const N = JSON.parse(fs.readFileSync(path.join(FIG, "numbers.json"), "utf8"));
const OUTFILE = path.join(ROOT, "40_DOCS", "Supervisor_Drafts", "Valuing Draft Picks.docx");
const TEXT = [];                                     // prose for the linter

// ---- helpers ------------------------------------------------------------------------------------
const FONT = "Calibri";
const f1 = (x) => Number(x).toFixed(1);
const f2 = (x) => Number(x).toFixed(2);
const comma = (x) => Number(x).toLocaleString("en-US");

function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), font: FONT, ...base }));
    const t = m[0];
    out.push(new TextRun({ text: t.replace(/\*/g, ""), font: FONT, bold: t.startsWith("**"), italics: !t.startsWith("**"), ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), font: FONT, ...base }));
  return out;
}
const P = (text) => { TEXT.push(text); return new Paragraph({ children: runs(text), spacing: { before: 60, after: 120, line: 276 } }); };
const H1 = (text) => { TEXT.push(`## ${text}`); return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text, font: FONT })], spacing: { before: 280, after: 120 } }); };
const FORMULA = (text) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 140 },
  children: [new TextRun({ text, font: FONT, italics: true, size: 23 })] });
const CAPTION = (text) => { TEXT.push(text); return new Paragraph({ spacing: { before: 40, after: 220 }, children: runs(text, { size: 18, color: "52514E" }) }); };
const TITLE = (text) => new Paragraph({ spacing: { before: 180, after: 60 }, keepNext: true, children: runs(text, { size: 20, bold: true }) });

function FIGURE(file, title, caption) {
  const b = fs.readFileSync(path.join(FIG, file));
  const w = b.readUInt32BE(16), h = b.readUInt32BE(20), width = 540;
  return [TITLE(title),
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true,
      children: [new ImageRun({ type: "png", data: b, transformation: { width, height: Math.round(width * h / w) } })] }),
    CAPTION(caption)];
}
const border = { style: BorderStyle.SINGLE, size: 4, color: "C9C8C3" };
const borders = { top: border, bottom: border, left: border, right: border };
function TABLE(header, rows, widths, numeric = [], together = true) {   // together: keep the table on one page
  const cell = (text, i, head, keep) => new TableCell({
    borders, width: { size: widths[i], type: WidthType.DXA },
    shading: head ? { fill: "EFEEEA", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: [new Paragraph({ keepNext: keep, alignment: numeric.includes(i) ? AlignmentType.RIGHT : AlignmentType.LEFT,
      children: runs(String(text), { size: 18, bold: !!head }) })],
  });
  return new Table({ width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: header.map((t, i) => cell(t, i, true, true)) }),
      ...rows.map((r, j) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, i, false, together && j < rows.length - 1)) }))] });
}

// ---- computed numbers -----------------------------------------------------------------------------
const F1 = N.f1, C = F1.curves, HO = F1.held_out_rmse;
const sc = Object.fromEntries(N.scales.map((r) => [r.scale_kind === "pooled" ? "all" : String(r.trade_season), r]));
const V = N.values_by_pick;
const tt = N.traded_totals, pr = N.projection, f5 = N.f5, f3 = N.f3;
const pt = N.worked_point;
const ptVal = pt.seasons.reduce((a, s) => a + s.value_M, 0), ptCost = pt.seasons.reduce((a, s) => a + s.cost_M, 0);
const ratio = (r) => f1(r.cost_actual / r.cost_model);
const scale2019 = sc["2019"].scale_M;

// ---- the document -----------------------------------------------------------------------------------
const kids = [];
const add = (...xs) => xs.flat().forEach((x) => kids.push(x));

add(new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: "Valuing Draft Picks", bold: true, size: 40, font: FONT })] }));
add(new Paragraph({ spacing: { after: 200 }, children: [new TextRun({ text: "October 2026", color: "52514E", font: FONT })] }));

add(H1("1. The Problem"));
add(P("The trade study prices each asset in a trade on one scale, which is the surplus the asset is expected to give the club that holds it. For a player, the surplus is the market price of the wins he is forecast to deliver, less his cap hit, over the seasons his club controls him. A draft pick has no contract and no player yet. It is a claim on whoever the club selects, so its value has to come from what past selections at the same slot delivered."));
add(P(`Two features of the draft make this difficult. The first is that outcomes are uneven. Of the ${comma(F1.picks)} players drafted from 2007 to 2017, ${comma(F1.never_played)} played no NHL game while their drafting club controlled them, and a few became stars worth tens of millions of dollars in surplus. The second is that outcomes arrive slowly. A drafted player's control years run about nine seasons, so the drafts that can be measured completely are years older than the trades being priced. A value built from all of today's data would, therefore, use results that no club could see when it made the trade.`));

add(H1("2. The Approach"));
add(P("Most of what a draft slot returns comes from the few players taken there who become stars. A pick is, in that sense, a ticket on a star, and the model values it that way:"));
add(FORMULA("pick value  =  star probability for the slot  ×  dollar scale"));
add(P(`The star probability is the chance that a player taken at that slot becomes a star. It comes from Patrick Bacon's draft model, the source of the WAR used throughout this model, which defines a star as a player whose career WAR per 82 games is at least 1.8 for a forward or 1.23 for a defenceman. The dollar scale is the surplus that one unit of star probability has delivered in our data, in millions of dollars at the 2025-26 cap. For example, the first overall pick has a star probability of ${f1(100 * V["1"].p_star)}%. Traded in 2019-20, when the dollar scale was $${f1(scale2019)} million, it is worth $${f1(V["1"].knowable_2019)} million.`));
add(P("Sections 3 to 6 build the formula in order. Section 3 measures what each drafted player delivered. Section 4 explains why Bacon's star probability gives the curve its shape, and Section 5 sets the dollar scale using only drafts a club could have seen. Section 6 addresses the choice that matters most for the results, which is what it costs a club to keep a drafted player."));

add(H1("3. What a Drafted Player Delivered"));
add(P("To learn what a slot returns, I price each player drafted from 2007 to 2017 the way the player model prices a contract. Only his control years count. These are the seasons from his draft until he becomes an unrestricted free agent under the collective agreement, at 27 or after seven seasons on an NHL roster. Those are the years the pick secures for the club; after them, the player is paid at market."));
add(P("For each season of control, the player's surplus is his value less his cost. His value is the market price of the wins he delivered that season, on the same price line that values player contracts. His cost is what the club paid to keep him. That is the maximum entry-level salary while his first contract runs, then a one-year qualifying offer each summer, which is the least the club can offer to keep his rights. A season he spends outside the NHL counts as zero, because a minor-league salary does not count against the cap. I sum the seasons and state the total at the 2025-26 cap, so picks and players are in the same currency."));
add(P(`The results are uneven. Brayden Point, taken 79th in 2014, delivered $${f1(ptVal)} million of value for $${f1(ptCost)} million of cost over his control years (Appendix B). About half of all picks return nothing. The pick curve has to average the two.`));

add(H1("4. The Shape of the Curve"));
add(P(`Figure 1 plots the average surplus at each pick. Value falls steeply over the first ten picks, which returned $${f1(F1.raw_mean_1_10)} million on average, and then flattens into a long tail: picks after the 32nd returned $${f1(F1.raw_mean_33plus)} million on average. The curve has to follow that shape.`));
add(FIGURE("f1_shape.png", "Figure 1. Average surplus by draft pick, and three candidate curves",
  `Each grey dot is the average surplus of the eleven players taken at that pick in the 2007-2017 drafts (all positions), in millions of dollars at the 2025-26 cap. Each line is a curve fitted to all ${comma(F1.picks)} picks with an indicator for each draft year, read at an average draft year. The horizontal axis is on a log scale.`));
add(P(`A straight line in the pick number cannot follow that shape: it values the first overall pick at $${f1(C.line["1"])} million, against the $${f1(F1.raw_mean_pick1)} million that first overall picks returned. The log of the pick number bends, but still values the first pick at $${f1(C.log["1"])} million. Bacon's star probability falls the way value does, because value comes mostly from stars. Multiplied by a single dollar scale, it values the first pick at $${f1(C.star["1"])} million, and it predicts best on drafts the curves were not fitted on (Table 1).`));
add(TITLE("Table 1. The three curves of Figure 1"));
add(TABLE(["Curve", "Numbers fitted", "#1", "#10", "#32", "#64", "Held-out miss"], [
  ["Straight line in the pick number", "2", f1(C.line["1"]), f1(C.line["10"]), f1(C.line["32"]), f1(C.line["64"]), f2(HO.line)],
  ["Log of the pick number", "2", f1(C.log["1"]), f1(C.log["10"]), f1(C.log["32"]), f1(C.log["64"]), f2(HO.log)],
  ["Star probability × dollar scale (adopted)", "1", f1(C.star["1"]), f1(C.star["10"]), f1(C.star["32"]), f1(C.star["64"]), f2(HO.star)],
  ["Actual average at that pick", "", f1(F1.raw_mean_pick1), "", "", "", ""],
], [3200, 1050, 900, 900, 900, 900, 1510], [1, 2, 3, 4, 5, 6]));
add(CAPTION("Values at picks #1, #10, #32, and #64 in millions of dollars at the 2025-26 cap, at an average draft year; the actual average is shown for #1 only, because averages at single later picks are too noisy to compare. Held-out miss: each curve is refitted with one draft left out and predicts that draft's picks; the miss is the root mean squared error over the eleven drafts, in millions of dollars a pick. The draft-year indicators are not counted in the numbers fitted."));
add(P("Two checks support using Bacon's probability. First, once it is in the regression, adding the pick number adds nothing (p = 0.91). Second, I applied his definition of a star to our own data: 5.9% of the skaters drafted from 2007 to 2015 became stars, against the 5.3% his probabilities imply, and each range of picks is within sampling error. This agreement is not independent confirmation, since his model is fitted on largely the same drafts. I also tested more flexible curves; none predicted held-out drafts better by more than about $0.01 million a pick (Appendix A)."));
add(P("The curve is a straight line in the star probability, not in the pick number. Across picks it keeps the steep shape of Bacon's probability; the dollar scale sets only its height. The scale is, therefore, best read as dollars per unit of star probability rather than as the value of a star, since it also carries the surplus of good players who are not stars."));

add(H1("5. The Dollar Scale and Look-Ahead"));
add(P("The study asks two questions about each traded pick: what it was worth when it was traded, and what it turned out to be worth. Realised careers answer the second question. The first must use only what a club could have known at the trade; otherwise, part of any mispricing the study finds would be built into the values."));
add(P(`The dollar scale is where this matters. Fitted on each draft separately, it varies more than sampling error explains (p = ${f3.wald_p.toFixed(4)}). It runs from $${f1(f3.scale[5])} million in 2012 to $${f1(f3.scale[8])} million in 2015, and the four most recent drafts, 2014 to 2017, have the four highest scales. None of those drafts had played out by the time of the trades in our data. A scale fitted on all eleven drafts would, therefore, make each traded pick look more valuable than any club could have known it to be.`));
add(P(`The model instead fits a separate scale for each trade season, using only drafts made nine or more seasons earlier, whose control years had largely ended (Figure 2). Trades in 2019-20, for example, use the 2007-2010 drafts. This lowers the value of the ${tt.picks} picks traded from July 2017 to March 2022 by ${f1(100 * (1 - tt.knowable / tt.pooled))}%, from $${f1(tt.pooled)} million to $${f1(tt.knowable)} million. The scale fitted on all eleven drafts is kept as a sensitivity. The cost of this choice is noise: the 2017-18 scale rests on two drafts.`));
add(FIGURE("f4_knowable_scale.png", "Figure 2. The dollar scale available at each trade season",
  "The blue line is the dollar scale used for trades in each season, fitted only on drafts made nine or more seasons earlier (two drafts for 2017-18, rising to ten for 2025-26); the bars are two standard errors. The dashed line is the scale fitted on all eleven drafts (2007-2017), kept as a sensitivity. The dollar scale is the surplus, in millions of dollars at the 2025-26 cap, that one unit (100%) of star probability delivered."));
add(P("The curve's shape does not raise the same concern. Bacon's probabilities are fitted on drafts through 2021, but they fit our 2007-2011 drafts as well as our 2012-2017 drafts (p = 0.61 and p = 0.79 for adding the pick number), so a curve shaped on early drafts alone would look the same. Table 2 gives the resulting value of a pick at selected slots."));
add(TITLE("Table 2. Value of a pick by slot and trade season"));
const t2 = ["1", "2", "3", "5", "10", "20", "32", "64", "100", "200"].map((k) => [
  `#${k}`, `${f1(100 * V[k].p_star)}%`, f2(V[k].knowable_2017), f2(V[k].knowable_2019), f2(V[k].knowable_2021), f2(V[k].pooled)]);
add(TABLE(["Pick", "Star probability", "Traded 2017-18", "Traded 2019-20", "Traded 2021-22", "All drafts (sensitivity)"], t2,
  [900, 1500, 1650, 1650, 1650, 2010], [1, 2, 3, 4, 5]));
add(CAPTION(`Millions of dollars at the 2025-26 cap. Dollar scales: ${f1(sc["2017"].scale_M)} for 2017-18 (2007-2008 drafts), ${f1(sc["2019"].scale_M)} for 2019-20 (2007-2010 drafts), ${f1(sc["2021"].scale_M)} for 2021-22 (2007-2012 drafts), and ${f1(sc.all.scale_M)} for all eleven drafts.`));

add(H1("6. The Cost of Keeping a Drafted Player"));
add(P(`The cost rule moves pick values more than any other choice, and it is the main risk to what the trade study concludes about picks. The qualifying-offer chain charges the least a club can pay to keep a player, which prices the club's right. In practice, clubs pay more. A star's club usually signs him to a long contract before his control ends, and a player who is eligible for salary arbitration can push his pay toward market. Figure 3 compares the two costs for the first-round picks who reached the NHL. Clubs actually paid ${ratio(f5[0])} times the chain's cost for players taken in the top ten, and ${ratio(f5[2])} times for players taken 16th to 32nd.`));
add(FIGURE("f5_control_cost.png", "Figure 3. Value delivered, and two measures of cost, for first-round picks",
  `Average per first-round skater who played in the NHL (2007-2017 drafts), over his control years, in millions of dollars at the 2025-26 cap. Value delivered and the model's cost are as in Section 3. Cost actually paid uses each season's actual cap hit (PuckPedia from 2018-19, CapWages before). Players taken 11th to 15th were paid ${ratio(f5[1])} times the chain's cost.`));
add(P("Actual contracts are not used as the cost, for two reasons. They bring hindsight into the cost side, since they record what each club and player negotiated years after the draft. And a long contract spreads the price of the free-agent years it buys over each of its seasons, so it would charge the control years for seasons outside them."));
add(P("The gap still matters. Players in a trade are costed at their actual cap hits, while picks are costed at the chain. Picks, therefore, look more valuable relative to players than they are, which could make clubs appear to give picks away too cheaply when they do not. The check is an alternative cost that charges market prices once a player becomes eligible for arbitration, and it cuts the dollar scale by 55%. I will run it before reading the trade back-test: a finding about picks that survives it does not come from the cost rule."));

add(H1("7. Valuing a Traded Pick"));
add(P(`A pick is often traded before anyone knows its slot, so the model sets the slot in one of three ways. A pick traded during its own draft takes its actual slot. A pick for the coming draft, traded during the season, takes the slot implied by its original team's place in the standings on the trade date. For ${pr.within3} of ${pr.picks} such picks, this lands within three slots of the actual one. A pick traded before that season starts, or for a later draft, takes the average star probability of its round. The ${tt.conditional} picks traded with conditions attached are valued without their conditions until each is checked.`));

add(H1("8. Limitations and Next Steps"));
add(P("Three limits remain. The cost rule understates what clubs pay for control (Section 6). Bacon's probabilities come from a model fitted on drafts through 2021; their shape holds in early drafts, but the model cannot be refitted on what was known at each trade. And the projected slot ignores the draft lottery."));
add(P("The next steps on picks are to resolve the conditional picks and to run the arbitration alternative. The prospect model will follow in a separate document."));

// ---- appendices ---------------------------------------------------------------------------------------
add(H1("Appendix A. Other Decisions"));
add(P("Each row is a choice made in building the curve that does not change its conclusions. Effects on the dollar scale were measured on skaters in the test that decided each choice."));
add(TABLE(["Decision", "Choice", "Alternative tested", "Result"], [
  ["End of control years", "Free agency under the collective agreement (Section 10.1(a)): 27 as of June 30, or seven seasons of 40 or more roster games (30 for goalies); games played stand in for roster games", "-", "Same free-agency year as PuckPedia for 1,151 of 1,183 drafted players"],
  ["Value of a season", "Wins delivered, on the contract price line, priced as a one-year deal, never below the league minimum", "The entry-level contract's remaining length", "One currency for picks and players"],
  ["Short seasons", "WAR in 2012-13, 2019-20, and 2020-21 scaled to 82 games", "-", "-"],
  ["Brief call-ups", "Under 10 NHL games: value and cost scaled by games over 82", "Counted as full seasons", "Mean surplus a pick $1.68M against $1.50M"],
  ["Entry-level contract length", "3, 2, or 1 seasons by age at his first NHL season (Section 9.1(b)), no slides", "Slides for 18- and 19-year-olds; slides at any age", "Scale moves by under 0.5%"],
  ["Negative careers", "Counted as negative", "Floored at zero", "Floor raises the scale by 4.1%"],
  ["Rights that lapsed", "Worth zero to the pick (68 picks whose first NHL club was not the drafting club, with no trade)", "Credited to the pick", "2.6% of all surplus; scale moves by 0.5%"],
  ["Goalies", "Pooled with skaters, priced on the goalie price line", "Skaters only; a separate goalie scale", "Pooling moves the scale by 2%; a goalie-only scale (84.3) would value a first-overall goalie near $63M"],
  ["Other curve shapes", "Star probability × dollar scale", "A bendable curve; log plus log squared; a two-part model", "Within about $0.01M a pick on held-out drafts; log plus log squared rises after pick 137"],
  ["Form on the star probability", "Straight line through zero", "With an intercept; a squared term; a power curve", "None beat it in more than 30 of 2,000 redraws of the drafts"],
  ["NHL-player probability", "Left out", "Added beside the star probability", "Coefficient -0.05 (standard error 2.15)"],
  ["Draft-to-draft variation in the scale", "Accepted as uncertainty", "-", "Spread beyond sampling noise is 29% of the all-drafts scale"],
  ["Short windows in the 2017 draft", "Kept (29 of 217 cut short by one season)", "Drop the 2017 draft", "Affects no trade under the trade-season scale"],
  ["Picks for later drafts", "Average star probability of the round", "The team's last draft slot", "A slot a year or more ahead is not known"],
], [1800, 3100, 2100, 2360], [], false));
add(CAPTION("Rule for curve shapes, set before the test: a shape with more fitted numbers had to predict held-out drafts better than each simpler shape in at least 1,950 of 2,000 redraws of the eleven drafts."));

add(H1("Appendix B. A Worked Player"));
add(P(`Brayden Point was taken 79th in 2014, a slot with a star probability of ${f1(100 * pt.p_star)}%. He played junior hockey for two seasons, which count as zero, and became an unrestricted free agent after 2022-23. Table 3 prices his seven NHL seasons of control.`));
add(TITLE("Table 3. Brayden Point (2014, #79), season by season"));
const rows3 = pt.seasons.map((s) => [`${s.season}-${String(s.season + 1).slice(2)}`, String(s.gp), f2(s.war_82),
  s.in_entry_level ? "Entry-level" : "Qualifying offer", f2(s.value_M), f2(s.cost_M), f2(s.value_M - s.cost_M)]);
rows3.push(["Total", "", "", "", f2(ptVal), f2(ptCost), f2(pt.total_M)]);
add(TABLE(["Season", "NHL games", "Season WAR", "Contract", "Value", "Cost", "Surplus"], rows3,
  [1150, 1100, 1300, 1800, 1300, 1300, 1410], [1, 2, 4, 5, 6]));
add(CAPTION("Value, cost, and surplus in millions of dollars at the 2025-26 cap: each season's amount is a share of that season's cap, restated at the 2025-26 cap of $95.5 million (with 3% cap growth and 3% discounting, summing cap shares is the player model's convention). Season WAR for 2019-20 and 2020-21 is scaled to 82 games."));

// ---- assemble -------------------------------------------------------------------------------------------
const doc = new Document({
  creator: "Thomas Mihaljevic", title: "Valuing Draft Picks",
  styles: { default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [{ id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: 28, bold: true, font: FONT, color: "0B0B0B" }, paragraph: { outlineLevel: 0, keepNext: true } }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1260, bottom: 1260, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "52514E", font: FONT })] })] }) },
    children: kids,
  }],
});
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUTFILE, buf);
  console.log("wrote", OUTFILE, buf.length, "bytes");
  if (process.env.LINT_OUT) fs.writeFileSync(process.env.LINT_OUT, TEXT.join("\n\n"), "utf8");
});
