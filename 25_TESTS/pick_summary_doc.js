// pick_summary_doc.js v3.1 -- builds "Valuing Draft Picks.docx" (40_DOCS/Supervisor_Drafts/).
//
// v3.1 (2026-10-09): carries Thomas's own edits to the final version (Downloads/"Valuing Draft Picksv3.docx"):
// "lottery ticket", "market rate", the future-version sentences after the round average, "A Worked
// Example"; deleted the roadmap paragraph, the Appendix B pointer, the conditional-picks/total paragraph
// and the Limitations and Next Steps section. The committed .docx is his final version.
// v3.0 (2026-10-09): revised from Thomas's 38 comments on v2.0. Evidence for each claim (stars' share
// of surplus; the regression behind the star value; the trend test behind one star value; the
// persistence data behind the round average); his phrasings adopted; "dollar scale" renamed "star
// value" (the surplus of a pick certain to produce a star); one star value for every draft (decided
// 2026-10-09, option (a)); Figure 1 on a linear axis; each actual average shown; Appendix A says why
// each choice was made and what the alternative would do, in pick dollars; Brayden Point's draft and
// junior seasons in his table. Written to the writing-style skill; reader-facing (no reader named).
//
// NUMBERS: computed figures from OUTPUT_DIR/pick_summary/numbers.json (pick_summary_figures.py v1.2,
// on pick_curve.py v1.2, traded_pick_values.py v1.2, pick_slot_persistence.py v1.0). Test results
// copied from the recorded runs:
//   5.9% / 5.3% stars, 2007-2015 skaters          pick_star_and_rights_checks.py v1.1
//   flexible curves within ~$0.01M; logsq up      pick_curve_shape_test.py v1.0 (rule 1,950 of 2,000)
//   form test: none beat through-zero > 30/2000   pick_star_form_test.py v1.0
//   NHL-player probability -0.05 (se 2.15)        the star-only comparison of 2026-10-09
//   arbitration -55%; slides < 0.5%; floor +4.1%  pick_cost_and_year_tests.py v1.0 (skaters)
//   goalies +2%, 84.3, ~$63M                      pick_goalie_test.py v1.0
//   lapsed 2.6% of surplus, scale 0.5%            pick_curve.py log; pick_star_and_rights_checks.py v1.1
//   1,151 of 1,183; 29 of 217                     draft_window_count.py v1.0
//   call-ups $1.68M against $1.50M                pick_regression_first_look.py v1.1 (skaters)
//   about $2.6M of length premium                 MODEL_DIRECTIVES directive 6 (entry-level term)
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
const TEXT = [];

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
  return [TITLE(title), new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true,
    children: [new ImageRun({ type: "png", data: b, transformation: { width, height: Math.round(width * h / w) } })] }), CAPTION(caption)];
}
const border = { style: BorderStyle.SINGLE, size: 4, color: "C9C8C3" };
const borders = { top: border, bottom: border, left: border, right: border };
function TABLE(header, rows, widths, numeric = [], together = true) {
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

// ---- numbers -------------------------------------------------------------------------------------------
const SV = N.star_value, T1 = N.t1, C = T1.curves, A = T1.actual, HO = T1.held_out, T2 = N.t2, ST = N.stars;
const F2 = N.f2, F3 = N.f3, F4 = N.f4, TR = N.traded, PT = N.point, VAL = N.values, P10 = N.pick10;
const pv = PT.seasons.reduce((a, s) => a + s.value_M, 0), pcst = PT.seasons.reduce((a, s) => a + s.cost_M, 0);
const ratio = (r) => f1(r.cost_actual / r.cost_model);
const per = (k, band) => F4.rows.find((r) => r.gap === k && r.band === band);
const sensPct = Math.round(100 * (1 - SV.sens / SV.main));

const kids = [];
const add = (...xs) => xs.flat().forEach((x) => kids.push(x));
add(new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: "Valuing Draft Picks", bold: true, size: 40, font: FONT })] }));
add(new Paragraph({ spacing: { after: 200 }, children: [new TextRun({ text: "October 2026", color: "52514E", font: FONT })] }));

// 1
add(H1("1. The Problem"));
add(P("The trade study prices each asset in a trade on one scale, which is the surplus the asset is expected to give the club that holds it. For a player, the surplus is the market price of the wins he is forecast to deliver, less his cap hit, over the seasons his club controls him. A draft pick has no contract and no player yet. It is a claim on whoever the club selects, so its value has to come from what past selections at the same slot delivered."));
add(P(`Two features of the draft make this difficult. The first is that outcomes are uneven. Of the ${comma(T1.picks)} players drafted from 2007 to 2017, ${comma(T1.never_played)} played no NHL game while their drafting club held their rights, and a few became stars worth tens of millions of dollars in surplus. The second is that outcomes arrive slowly. A club holds a drafted player's rights for about nine seasons, so the drafts that can be measured completely are years older than the trades being priced.`));

// 2
add(H1("2. The Approach"));
add(P(`Most of the surplus that draft picks produce comes from the few players who become stars. Of the ${comma(ST.picks)} skaters drafted from 2007 to 2015, the ${ST.stars} who became stars (${f1(ST.share_picks)}%, by the definition below, with at least 200 NHL games) produced ${f1(ST.share_surplus)}% of all the surplus those picks returned. Among the first ten picks, stars were ${f1(ST.top10_share_picks)}% of the players and produced ${f1(ST.top10_share_surplus)}% of the surplus. The model, therefore, values a pick as a lottery ticket on a star:`));
add(FORMULA("pick value  =  star value  ×  star probability for the slot"));
add(P(`The star probability is the chance that a player taken at that slot becomes a star. It comes from Patrick Bacon's draft model, the source of the WAR used throughout this model, which defines a star as a player whose career WAR per 82 games is at least 1.8 for a forward or 1.23 for a defenceman. The star value is the surplus a pick would be worth if its player were certain to become a star. Section 4 estimates it at $${f1(SV.main)} million at the 2025-26 cap. For example, the first overall pick has a star probability of ${f1(100 * VAL["1"].p)}%, so it is worth ${(VAL["1"].p).toFixed(3)} × $${f1(SV.main)} million = $${f1(VAL["1"].v)} million.`));

// 3
add(H1("3. What a Drafted Player Delivered"));
add(P("To learn what a slot returns, I price each player drafted from 2007 to 2017 the way the player model prices a contract. Only the seasons while his club holds his rights count. These run from his draft until he becomes an unrestricted free agent under the collective agreement, at 27 or after seven seasons on an NHL roster. They are the years the pick secures for the club; after them, the player is paid at market rate."));
add(P("For each of those seasons, the player's surplus is his value less his cost. His value is the market price of the wins he delivered that season, on the same price line that values player contracts. His cost is what the club paid to keep him. That is the maximum entry-level salary while his first contract runs, then a one-year qualifying offer each summer, which is the least the club can offer to keep his rights. A season he spends outside the NHL counts as zero, because a minor-league salary does not count against the cap. I sum the seasons and state the total at the 2025-26 cap, so picks and players are in the same currency."));

// 4
add(H1("4. Estimating the Star Value"));
add(P(`Figure 1 plots the average surplus of the players taken at each pick. Value falls steeply over the first ten picks, which returned $${f1(T1.mean_1_10)} million on average, and is close to flat after the 32nd pick, where picks returned $${f1(T1.mean_after_32)} million on average.`));
add(FIGURE("f1_shape.png", "Figure 1. Average surplus by draft pick, and three candidate curves",
  `Each grey dot is the average surplus of the eleven players taken at that pick in the 2007-2017 drafts (all positions), in millions of dollars at the 2025-26 cap. Each line is a curve fitted to all ${comma(T1.picks)} picks with an indicator for each draft year, read at an average draft year.`));
add(P(`The relationship between surplus and pick number is not linear: a straight line values the first overall pick at $${f1(C.line["1"])} million, against the $${f1(A["1"])} million that first overall picks returned. The expected surplus of a pick cannot be represented by the log of the pick number either, which values the first pick at $${f1(C.log["1"])} million. The best-performing indicator of surplus is Bacon's star probability. Multiplied by the star value, it values the first pick at $${f1(C.star["1"])} million, and it predicts drafts left out of the fit better than either alternative (Table 1).`));
add(TITLE("Table 1. The three curves of Figure 1, against the actual averages"));
add(TABLE(["Curve", "Parameters estimated", "#1", "#10", "#32", "#64", "Held-out error"], [
  ["Straight line in the pick number", "2", f1(C.line["1"]), f1(C.line["10"]), f1(C.line["32"]), f1(C.line["64"]), f2(HO.line)],
  ["Log of the pick number", "2", f1(C.log["1"]), f1(C.log["10"]), f1(C.log["32"]), f1(C.log["64"]), f2(HO.log)],
  ["Star value × star probability (adopted)", "1", f1(C.star["1"]), f1(C.star["10"]), f1(C.star["32"]), f1(C.star["64"]), f2(HO.star)],
  ["Actual average of the eleven players taken", "", f1(A["1"]), f1(A["10"]), f1(A["32"]), f1(A["64"]), ""],
], [3200, 1050, 900, 900, 900, 900, 1510], [1, 2, 3, 4, 5, 6]));
add(CAPTION("Values in millions of dollars at the 2025-26 cap, at an average draft year. Each actual average rests on eleven players, so one draft's outcome moves it a great deal. Parameters estimated leaves out the indicators for each draft year, which every curve includes. Held-out error: each curve is refitted eleven times, each time leaving one draft out, and predicts the surplus of each pick in the draft left out; the error is the root mean squared error over all picks, in millions of dollars."));
add(P(`The model's $${f1(C.star["1"])} million for the first pick is below the $${f1(A["1"])} million that first picks returned, because the star value is fitted on all 217 slots; eleven first picks are too few to set a value on their own. The star value itself, $${f1(SV.main)} million, is a different quantity: it is the surplus of a pick whose star probability is 100%, which no slot reaches.`));
add(P(`Table 2 gives the regression behind the star value. Each drafted player's surplus is regressed on his slot's star probability, with an indicator for each draft year and no constant, so a slot with no chance of a star is worth nothing. The coefficient on the star probability is the star value, $${f1(T2.A.b)} million (standard error $${f1(T2.A.se)} million). The second column adds the pick number to the same regression. Its coefficient is close to zero and not statistically significant (p = ${T2.B.b2_p.toFixed(2)}), and the star value barely moves, so once the star probability is known, the pick number carries no further information about surplus.`));
add(TITLE("Table 2. Regression of a drafted player's surplus on his slot"));
add(TABLE(["", "Adopted", "With the pick number added"], [
  ["Star probability (the star value)", `${f2(T2.A.b)} (${f2(T2.A.se)})`, `${f2(T2.B.b1)} (${f2(T2.B.b1_se)})`],
  ["Pick number", "", `${T2.B.b2.toFixed(4)} (${T2.B.b2_se.toFixed(4)})`],
  ["Constant", "", `${f2(T2.B.a)} (${f2(T2.B.a_se)})`],
  ["Draft-year indicators", "Yes", "Yes"],
  ["Drafted players", comma(T2.n), comma(T2.n)],
  ["R-squared", T2.A.r2.toFixed(3), T2.B.r2.toFixed(3)],
], [3600, 2700, 3060], [1, 2]));
add(CAPTION(`Dependent variable: each drafted player's surplus while his club held his rights, in millions of dollars at the 2025-26 cap, for all ${comma(T2.n)} players drafted from 2007 to 2017. Robust standard errors in parentheses. The draft-year indicators sum to zero, so the coefficients describe an average draft.`));
add(P("Two further checks support Bacon's probability. When his definition of a star is applied to our own data (also requiring 200 NHL games), 5.9% of the skaters drafted from 2007 to 2015 became stars, against the 5.3% his probabilities imply, and each range of picks is within sampling error. This agreement is not independent confirmation, since his model is fitted on largely the same drafts. I also tested more flexible curves (Appendix A); none predicted held-out drafts better by more than about $0.01 million a pick."));

// 5
add(H1("5. One Star Value for Every Draft"));
add(P(`Fitted on each draft separately, the star value differs between drafts, and the differences are statistically significant (p = ${F2.wald_p.toFixed(4)}; Figure 2). It ranges from $${f1(F2.scale[5])} million for the 2012 draft to $${f1(F2.scale[8])} million for 2015. Some drafts are deeper than others, so this is expected.`));
add(FIGURE("f2_star_value_by_draft.png", "Figure 2. The star value fitted on each draft",
  "Each blue dot is the star value fitted on one draft alone (all positions), with bars two standard errors either side. The solid line is the star value fitted on all eleven drafts and used by the model; the dashed line is the same fit without the 2015 and 2016 drafts. The star value is the surplus, in millions of dollars at the 2025-26 cap, of a pick certain to produce a star."));
add(P(`What matters for the model is whether the star value drifts over time, because a drift would make an average over all eleven drafts wrong for any one trade. Fitted with a linear trend across draft years, the star value rises by $${f1(F2.trend_all)} million a draft (p = ${F2.trend_all_p.toFixed(3)}). That rise rests on two drafts, however. Without 2015 (Connor McDavid, Jack Eichel) and 2016 (Auston Matthews), the trend falls to $${f1(F2.trend_wo)} million a draft and is not statistically significant (p = ${F2.trend_wo_p.toFixed(2)}).`));
add(P(`The model, therefore, uses one star value for every draft, $${f1(SV.main)} million, fitted on all eleven. This treats each club as expecting the same value from a given slot each year, with an exceptional draft as noise. The 2015 and 2016 drafts finished after most of the trades studied, so the same fit without them, $${f1(SV.sens)} million, is reported beside it as a sensitivity; it lowers each pick's value by ${sensPct}%. Table 3 gives the value of a pick at selected slots under both.`));
add(TITLE("Table 3. Value of a pick by slot"));
add(TABLE(["Pick", "Star probability", "Value (all eleven drafts)", "Value (without 2015 and 2016)"],
  ["1", "2", "3", "5", "10", "20", "32", "64", "100", "200"].map((k) => [`#${k}`, `${f1(100 * VAL[k].p)}%`, f2(VAL[k].v), f2(VAL[k].v_s)]),
  [1500, 2200, 2800, 2860], [1, 2, 3]));
add(CAPTION(`Millions of dollars at the 2025-26 cap: the star value ($${f1(SV.main)} million, or $${f1(SV.sens)} million without 2015 and 2016) times Bacon's star probability for the slot.`));

// 6
add(H1("6. The Cost of Keeping a Drafted Player"));
add(P(`How cost is assigned to a drafted player once he is in the NHL affects pick values more than any other choice, and it is the main risk to what the trade study concludes about picks. The model charges the qualifying-offer chain, which represents the cost of holding a player's rights. In practice, clubs pay more. A star's club usually signs him to a long contract while the team holds his rights, and a player who is eligible for salary arbitration can push his pay toward market. Figure 3 compares the two costs for the first-round picks who reached the NHL. Clubs actually paid ${ratio(F3[0])} times the qualifying-offer chain's cost for players taken in the top ten, ${ratio(F3[1])} times for those taken 11th to 15th, and ${ratio(F3[2])} times for those taken 16th to 32nd.`));
add(FIGURE("f3_control_cost.png", "Figure 3. Value delivered, and two measures of cost, for first-round picks",
  "Average per first-round skater who played in the NHL (2007-2017 drafts), over the seasons his club held his rights, in millions of dollars at the 2025-26 cap. Value delivered and the cost charged by the model are as in Section 3. Cost actually paid uses each season's cap hit (PuckPedia from 2018-19, CapWages before)."));
add(P("Actual contracts are not used as the cost, for two reasons. They bring hindsight into the cost side, since they record what each club and player negotiated years after the draft. And many of these contracts are long contracts that buy free-agent years as well as restricted years, while the model is concerned only with the years of team control."));
add(P("This has a consequence for the trade study. Players in a trade are costed at their actual cap hits, while picks are costed using the qualifying-offer chain, so picks look more valuable relative to players than they are. That could make clubs appear to give picks away too cheaply when they do not. The check is an alternative cost that charges market prices once a player becomes eligible for arbitration; it lowers each pick's value by 55%. I will run it before reading the trade back-test, because a finding about picks that survives it does not come from how the cost was assigned."));

// 7
add(H1("7. Valuing a Traded Pick"));
add(P(`A pick is often traded before anyone knows its slot, so the model assigns one in three ways. A pick traded during its own draft takes its actual slot. A pick for the coming draft, traded during the season, takes the slot implied by its original team's place in the standings on the trade date. For ${TR.projection.within3} of ${TR.projection.picks} such picks, this lands within three slots of the draft slot the pick went on to become. A pick traded before that season starts, or for a later draft, takes the average star probability of its round.`));
add(P(`The round average rests on how little a team's current slot says about its slot a year or two later. Across the 2005-2026 drafts, a team's own first-round slot correlates ${f2(F4.corr["1"])} with its slot in the next draft and ${f2(F4.corr["2"])} with its slot two drafts later, and it moves a median of ${F4.median_move["1"]} places in a year (Figure 4). A team that picked in the top five went on to pick anywhere from ${per(1, "1-5").p10.toFixed(0)}nd to ${Math.round(per(1, "1-5").p90)}nd the next year, in 80% of cases.`));
add(FIGURE("f4_slot_persistence.png", "Figure 4. How a team's draft slot carries over to later drafts",
  "For teams whose own first-round pick fell in each range of slots, the dot is the average slot of their own first-round pick in the next draft (blue) and two drafts later (orange); the bars span the 10th to 90th percentiles. A team's own pick is the one it originally held, wherever it was later traded. Drafts 2005-2026, from the NHL's draft records (actual slots, after the lottery); slot 1 is the first pick."));
add(P(`The round average does give up some information, because the slot is not purely random: teams near the top of the draft tend to stay near the top. Valued at the slots they went on to pick, the next first-round pick of a team that just picked in the top five was worth $${f1(per(1, "1-5").value)} million on average, against the round average of $${f1(per(1, "1-5").round_avg)} million; that of a team that just picked 25th to 32nd was worth $${f1(per(1, "25-32").value)} million. The round average, therefore, undervalues a weak team's future first-round pick and overvalues a strong team's. It is kept for its simplicity, and this difference is stated as a limitation. A future version of the model could value a traded first-round pick from a later draft on its original team’s current place in the draft order, which would capture this difference. The same is not needed for picks in the second to seventh rounds, because the pick curve is close to flat after the first round.`));
// Appendix A
add(H1("Appendix A. Other Choices"));
add(P(`Each row gives a choice made in building the curve, why it was made, and what the alternative would have done. Where a choice changes each pick's value by the same percentage, the effect is shown on the 10th pick, worth $${f2(P10.main)} million in the model.`));
add(TABLE(["Choice", "What the model does", "Why", "What the alternative would do"], [
  ["End of the years the club holds his rights", "Unrestricted free agency under Section 10.1(a): 27 as of June 30, or seven seasons of 40 or more games on an NHL roster (30 for goalies); games played stand in for roster games", "The pick secures the player only until he can sign with any club", "As a check, PuckPedia records a projected free-agency year for each player under contract; this rule gives the same year for 1,151 of the 1,183 drafted players it covers"],
  ["Length of each season's contract", "Each season priced as a one-year contract, so it carries one year of the price line's premium for contract length", "Clubs pay that premium for the security of a long contract; an entry-level or qualifying-offer season buys no security beyond that season", "Pricing entry-level seasons at the contract's remaining length would add about $2.6 million to a player who plays all three, for security nobody bought"],
  ["Brief call-ups", "A season under 10 NHL games has its value and cost scaled by games played over 82", "A call-up's cap hit counts only for his days on the roster", "Counting each as a full season charges a full year's cost for a few games: the average pick would fall from $1.68 million to $1.50 million (skaters)"],
  ["Entry-level slides", "Not modelled; the entry-level contract runs 3, 2, or 1 seasons from his first NHL season, by his age then (Section 9.1(b))", "The CBA lets an 18- or 19-year-old's contract slide a year when he plays under 10 NHL games, but modelling it changes little", `Modelling slides changes each pick's value by under 0.5% (the 10th pick by under $0.04 million)`],
  ["Careers that lost money", "Counted as negative", "A player who holds a roster spot while delivering less than his cost was a loss to his club", `Flooring each career at zero would raise each pick's value by 4.1% (the 10th pick to $${f2(P10.main * 1.041)} million)`],
  ["Rights that lapsed", "Counted as zero", "68 drafted players never signed with their drafting club and first played for another club without a trade (for example, Jared Spurgeon, drafted by the Islanders, signed by Minnesota); their surplus never reached the club holding the pick", "Crediting them to the pick would raise each pick's value by about 0.5%; they hold 2.6% of all surplus"],
  ["Goalies", "Pooled with skaters, priced on the goalie price line", "At a trade, nobody knows whether a pick will become a goalie", "A separate goalie curve is not credible: goalie value does not follow the slot (Braden Holtby #93, Juuse Saros #99, Igor Shesterkin #118), and one would value a first-overall goalie near $63 million. Leaving goalies out would lower each pick's value by about 2%"],
  ["More flexible curves", "Not used", "A bendable curve, log plus log squared, and a two-part model (chance of reaching the NHL times value if he does) were scored as in Table 1; a curve with more parameters had to beat each simpler one in 1,950 of 2,000 redraws of the drafts", "None predicted held-out drafts better than the star probability by more than about $0.01 million a pick, and log plus log squared values the 200th pick above the 137th"],
  ["Form of the star-probability term", "A straight line through zero", "A slot with no chance of a star should be worth nothing", "Adding a constant, a squared term, or a power did not improve the fit; none beat the straight line in more than 30 of 2,000 redraws"],
  ["Bacon's NHL-player probability", "Not used", "He also gives each slot's chance of producing a 200-game NHL player; once the star probability is in, it adds nothing (coefficient -0.05, standard error 2.15)", "-"],
  ["The 2017 draft's last season", "Kept", "The data end with 2025-26, which cuts 29 of the 217 players' years short by one season", `Leaving the 2017 draft out lowers the star value from $${f1(SV.main)} million to $${f1(F2.star_no2017)} million`],
], [1700, 2500, 2500, 2660], [], false));

// Appendix B
add(H1("Appendix B. A Worked Example"));
add(P(`Brayden Point was taken 79th in 2014, a slot with a star probability of ${f1(100 * PT.p_star)}%, so the model values that pick at $${f2(SV.main * PT.p_star)} million. Table 4 prices each season from his draft until he became an unrestricted free agent after 2022-23.`));
add(TITLE("Table 4. Brayden Point (2014, #79), from his draft to free agency"));
const jr = { "2014-2015": "Junior (Moose Jaw, WHL) and 9 AHL games (Syracuse)", "2015-2016": "Junior (Moose Jaw, WHL)" };
const rows4 = [["2014-15", jr["2014-2015"], "0", "", "", "0.00", "0.00", "0.00"], ["2015-16", jr["2015-2016"], "0", "", "", "0.00", "0.00", "0.00"],
  ...PT.seasons.map((s) => [`${s.season}-${String(s.season + 1).slice(2)}`, "Tampa Bay", String(s.gp), f2(s.war_82),
    s.in_entry_level ? "Entry-level" : "Qualifying offer", f2(s.value_M), f2(s.cost_M), f2(s.value_M - s.cost_M)]),
  ["Total", "", "", "", "", f2(pv), f2(pcst), f2(PT.total)]];
add(TABLE(["Season", "Where he played", "NHL games", "Season WAR", "Contract charged", "Value", "Cost", "Surplus"], rows4,
  [900, 2300, 900, 900, 1400, 1000, 950, 1010], [2, 3, 5, 6, 7]));
add(CAPTION("Value, cost, and surplus in millions of dollars at the 2025-26 cap. A season outside the NHL is worth nothing and costs nothing, since a minor-league salary does not count against the cap. Each NHL season's amount is a share of that season's cap, restated at the 2025-26 cap of $95.5 million. Season WAR for 2019-20 and 2020-21 is scaled to 82 games."));

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
