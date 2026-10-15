// prospect_model_doc.js v1.0 -- builds "Valuing Prospects.docx" (40_DOCS/Supervisor_Drafts/).
//
// Asked (Thomas, 2026-10-14): "create a document for the prospect model. use /anthropic-skills:writing-style. ensure
// that decisions are clearly explained and alternatives are outlined along with the reason for the decision. graphs and
// charts and tables are welcome"; then "ensure that the various model parameters and decisions are legibly comparable
// and that you include information about statistical significance". Spine agreed with Thomas before drafting (five
// take-aways: currency and handover; the slot's fade; production; age; the traded prospects). Format: Word, like the
// other supervisor documents. Reader-facing: names no reader.
//
// NUMBERS: every computed figure comes from OUTPUT_DIR/prospect_doc/numbers.json (prospect_doc_figures.py v1.0, on
// prospect_values.py v1.5, prospect_slot_years_check.py v1.0, prospect_nhle_look.py v1.1, prospect_age_look.py v1.0).
// Recorded figures copied from the records:
//   post-season trades on the next page: 23 prospects, -$3.51M      25_TESTS/next_page_moves.py (session 2026-10-14)
//   undrafted: NHL contracts only; 75 / 83 premise corrected         MODEL_DIRECTIVES directive 6, undrafted
//
// Run:  NODE_PATH=<folder with docx> node 25_TESTS/prospect_model_doc.js   (LINT_OUT=<file.md> writes the prose)

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType,
  AlignmentType, HeadingLevel, BorderStyle, ShadingType, Footer, PageNumber, PageBreak,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const FIG = path.join(ROOT, "30_OUTPUT", "prospect_doc");
const N = JSON.parse(fs.readFileSync(path.join(FIG, "numbers.json"), "utf8"));
const OUTFILE = path.join(ROOT, "40_DOCS", "Supervisor_Drafts", "Valuing Prospects.docx");
const TEXT = [];

// ---- helpers (as pick_summary_doc.js) -------------------------------------------------------------------
const FONT = "Calibri";
const f1 = (x) => Number(x).toFixed(1);
const f2 = (x) => Number(x).toFixed(2);
const f3 = (x) => Number(x).toFixed(3);
const f4 = (x) => Number(x).toFixed(4);
const comma = (x) => Number(x).toLocaleString("en-US");
const money = (x) => (x < 0 ? `-$${f2(-x)}M` : `$${f2(x)}M`);
const pfmt = (p) => (p < 0.001 ? "<0.001" : f3(p));
function p2(z) {
  const x = Math.abs(z) / Math.SQRT2, tt = 1 / (1 + 0.3275911 * x);
  const erfc = tt * Math.exp(-x * x) * (0.254829592 + tt * (-0.284496736 + tt * (1.421413741 + tt * (-1.453152027 + tt * 1.061405429))));
  return erfc;
}
const pct = (x) => `${x > 0 ? "+" : ""}${f2(x)}%`;
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
const H2 = (text) => { TEXT.push(`### ${text}`); return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text, font: FONT })], spacing: { before: 200, after: 80 } }); };
const FORMULA = (text) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 140 },
  children: [new TextRun({ text, font: FONT, italics: true, size: 23 })] });
const CAPTION = (text) => { TEXT.push(text); return new Paragraph({ spacing: { before: 40, after: 220 }, children: runs(text, { size: 18, color: "52514E" }) }); };
const TITLE = (text) => new Paragraph({ spacing: { before: 180, after: 60 }, keepNext: true, children: runs(text, { size: 20, bold: true }) });
function FIGURE(file, title, caption, width = 540) {
  const b = fs.readFileSync(path.join(FIG, file));
  const w = b.readUInt32BE(16), h = b.readUInt32BE(20);
  return [TITLE(title), new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true,
    children: [new ImageRun({ type: "png", data: b, transformation: { width, height: Math.round(width * h / w) } })] }), CAPTION(caption)];
}
const border = { style: BorderStyle.SINGLE, size: 4, color: "C9C8C3" };
const borders = { top: border, bottom: border, left: border, right: border };
function TABLE(header, rows, widths, numeric = [], shade = []) {
  const cell = (text, i, head, keep, fill) => new TableCell({
    borders, width: { size: widths[i], type: WidthType.DXA },
    shading: head ? { fill: "EFEEEA", type: ShadingType.CLEAR, color: "auto" } : (fill ? { fill, type: ShadingType.CLEAR, color: "auto" } : undefined),
    margins: { top: 40, bottom: 40, left: 80, right: 80 },
    children: [new Paragraph({ keepNext: keep, alignment: numeric.includes(i) ? AlignmentType.RIGHT : AlignmentType.LEFT,
      children: runs(String(text), { size: 17, bold: !!head }) })],
  });
  return new Table({ width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: header.map((t, i) => cell(t, i, true, true)) }),
      ...rows.map((r, j) => new TableRow({ cantSplit: true,
        children: r.map((t, i) => cell(t, i, false, j < rows.length - 1, shade.includes(j) ? "F4F1E6" : undefined)) }))] });
}
const gap = () => new Paragraph({ spacing: { after: 60 }, children: [] });

// ---- numbers -------------------------------------------------------------------------------------------
const S1 = N.step1, PA = Object.fromEntries(N.prod_arms.map((a) => [a.arm, a])), AA = Object.fromEntries(N.age_arms.map((a) => [a.arm, a]));
const TR = N.traded, ALT = N.alt_totals, W = N.worked, CH = N.chosen, PS = N.p_star, SL = N.slot_late;
const k = (g) => S1.find((r) => r.k === g);
const pOne = (wins) => (2000 - wins) / 2000;                       // share of redraws in which it is not lower
const ch = (v, g) => CH[v].find((t) => t.k === g);
const AC = (g, arm) => N.age_coefs.find((r) => r.k_group === g && r.arm === arm);

const kids = [];
const add = (...xs) => xs.flat().forEach((x) => kids.push(x));
add(new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: "Valuing Prospects", bold: true, size: 40, font: FONT })] }));
add(new Paragraph({ spacing: { after: 200 }, children: [new TextRun({ text: "October 2026", color: "52514E", font: FONT })] }));

// 1 ------------------------------------------------------------------------------------------------------
add(H1("1. The Problem"));
add(P("The trade study prices each asset in a trade on one scale, which is the surplus the asset is expected to give the club that holds it. For a player under contract, the surplus is the market price of the wins he is forecast to deliver, less his cap hit, over the seasons his club controls him. The player model builds that forecast from a player's recent NHL seasons. A prospect has none, so he needs a model of his own."));
add(P("A prospect is a player the player model does not yet value. For a skater, that is a player with no NHL season of 10 or more games in the three seasons before the valuation date. For a goaltender, it is a player with no NHL game in the six seasons before it. The goaltender forecast uses any NHL season in the three before and looks back three more when the last is missing. The definition copies the player model's own entry point, so each player is valued by exactly one of the two models. A player called up for a handful of games stays a prospect, because the player model cannot forecast from a season under 10 games. The alternative, handing any player with an NHL game to the player model, would have required changing that model's forecast."));
add(P("A prospect is valued in the same currency as a draft pick and a contract: the surplus of his remaining NHL seasons until his club's control ends. Control ends when he becomes an unrestricted free agent under the collective agreement, at 27 or after seven seasons on an NHL roster. Each season counts the market price of the wins he delivers, less what the club pays to keep him. That cost is the entry-level salary, then the qualifying offer, or the arbitration price once he is eligible. A season outside the NHL counts as zero. This is the pricing behind the draft pick curve, so a prospect and a pick traded together add on one scale. Counting only the entry-level years was considered and rejected, because a club controls a drafted player for years after his entry-level contract ends."));
add(P(`The model learns from the ${comma(k("0").rows)} players drafted from 2007 to 2017, whose careers are long enough to observe. The outcome is each player's remaining surplus, measured at each season after his draft in which he was still a prospect. Remaining surplus is the surplus he went on to deliver from that season to the end of his club's control. A traded prospect is valued at the season of his trade. A trade after the regular season has ended is valued at the next season, because by then the season's games are played and its information is complete.`));

// 2 ------------------------------------------------------------------------------------------------------
add(H1("2. How Candidate Models Are Compared"));
add(P("Each addition to the model is a choice between a simpler version and a richer one. Each is judged by two questions: does the addition predict a prospect's remaining surplus better, and is the improvement reliable rather than the product of a few drafts?"));
add(P(`**Held-out error.** Each draft is predicted from a model fitted without it. The error is the root mean squared miss, in millions of dollars of remaining surplus, for a prospect valued at one season after his draft (a prospect-season). Lower is better. Each candidate is scored on the same ${comma(N.prod_rows.rows)} prospect-seasons of ${comma(N.prod_rows.players)} drafted skaters.`));
add(P("**Reliability across drafts.** The 11 drafts are redrawn with replacement 2,000 times, and each redraw counts whether the candidate's total squared error is lower than the simpler version's. The share of redraws in which it is not lower works as a one-sided p-value: 1,950 of 2,000 corresponds to p = 0.025, the bar the draft pick curve's tests used. Drafts are redrawn, rather than players, because players drafted together share a draft's depth, so a draft is the independent unit."));
add(P("**Coefficients.** Each regression reports robust standard errors, clustered by player where one player appears in several seasons, and two-sided p-values from the ratio of each coefficient to its standard error."));

// 3 ------------------------------------------------------------------------------------------------------
add(H1("3. The Draft Slot and How It Fades"));
add(P(`At the draft, a pick is worth its slot's star probability times the star value. The star probability is the chance that a player taken at that slot becomes a star, from Patrick Bacon's draft model. The star value is the surplus a pick would be worth if its player were certain to become a star: $${f2(k("0").star)} million at the 2025-26 cap. The first overall pick has a star probability of ${f1(100 * PS["1"])}%, so it is worth $${f2(k("0").pick1)} million. A prospect starts with his pick's value. The question is how that value changes while he remains unproven.`));
add(P("To answer it, I re-estimate the star value on the players still prospects at each season since their draft. The regression is the draft pick curve's own. It regresses each prospect's remaining surplus on his slot's star probability, through zero, with draft-year indicators that sum to zero, so the star value is that of an average draft."));
add(FORMULA("prospect value  =  star probability for his slot  ×  star value for his seasons since the draft"));
add(TITLE("Table 1. The star value for a player still a prospect, by seasons since his draft"));
add(TABLE(["Seasons since the draft", "Prospects", "Star value (s.e.)", "p-value", "#1 pick", "#10 pick", "#32 pick", "Each draft left out", "Top-10 picks still prospects"],
  S1.map((r) => [r.k === "0" ? "0 (the draft)" : r.k === "4+" ? "4 and later" : r.k, comma(r.k === "4+" ? r.players : r.rows) + (r.k === "4+" ? ` (${comma(r.rows)} prospect-seasons)` : ""),
    `$${f2(r.star)}M (${f2(r.se)})`, pfmt(r.p), money(r.pick1), money(r.pick10), money(r.pick32), `$${f2(r.lodo_min)}-${f2(r.lodo_max)}M`, comma(r.top10)]),
  [1150, 1300, 1150, 720, 820, 820, 820, 1200, 1100], [1, 2, 3, 4, 5, 6, 8]));
add(CAPTION(`Drafted players 2007-2017 still prospects at each season since their draft (season 0 is the season after the draft). Star value in millions of dollars at the 2025-26 cap; robust standard errors (clustered by player for 4 and later). The pick columns multiply the star value by Bacon's star probability (${f1(100 * PS["1"])}%, ${f1(100 * PS["10"])}% and ${f1(100 * PS["32"])}%). "Each draft left out" is the range of the star value when each of the 11 drafts is left out of the fit in turn.`));
add(...FIGURE("fig1_star_value.png", "Figure 1. The star value falls in a step between the second and fourth seasons after the draft",
  "Star value for players still prospects, by seasons since their draft, in millions of dollars at the 2025-26 cap. Bars are the estimates in Table 1; lines are 95% intervals (1.96 robust standard errors)."));
add(P(`A prospect keeps most of his slot's value for two seasons ($${f2(k("1").star)} million one season on, $${f2(k("2").star)} million two seasons on) and loses most of it in the next two ($${f2(k("3").star)} million three seasons on, $${f2(k("4+").star)} million from the fourth). Each estimate is far from zero; the largest p-value is ${f3(k("4+").p)}, four or more seasons on. The fall is a step because the prospects who remain unproven are increasingly those who will not reach the NHL. Of the ${k("0").top10} top-ten picks of 2007-2017, ${k("2").top10} were still prospects two seasons after their draft and ${k("3").top10} three seasons after it.`));
add(H2("Decision: one star value for each season since the draft"));
add(P(`The model estimates the star value separately for each of the first four seasons after the draft and once for the seasons after that. I considered two simpler alternatives. The first keeps the draft-day value however long ago the draft was. On the slot alone it would value the 197 traded drafted prospects at $${f2(ALT.slot_no_fade)} million, against $${f2(ALT.step1_slot)} million with the fade. It would value a prospect four seasons on at nine times his re-estimated worth ($${f2(k("0").star)} million against $${f2(k("4+").star)} million). The second applies one fitted rate of decline each season. It would need one parameter fewer, but the decline is a step between the second and fourth seasons rather than a constant rate, so a single rate would overstate the value early and understate it late. Re-estimating the same regression for each season matches the step and adds no new form.`));
add(P(`The seasons from the fourth on are pooled into one estimate on ${comma(k("4+").rows)} prospect-seasons of ${comma(k("4+").players)} players, because few prospects that old remain and little value is left to estimate. Each player appears in several of those seasons, so the standard error is clustered by player.`));
add(H2("Decision: the overlap with the fit is a stated limitation"));
add(P(`A prospect drafted from 2007 to 2017 is valued from a fit that contains his own outcome. Leaving his draft out of the fit moves the star value within the ranges in Table 1, and moves the 197 traded drafted prospects from $${f2(ALT.adopted)} million to $${f2(ALT.own_draft_out)} million under the adopted model. The value with his draft left out is reported beside each traded prospect's value. Refitting without each prospect's own draft as the main value was rejected for two reasons. It would take eleven fits for each season since the draft, and the prospect values would no longer use the same star value as the draft picks traded beside them.`));

// 4 ------------------------------------------------------------------------------------------------------
add(H1("4. Production Adjusted to NHL Terms"));
add(P("The slot records what scouts knew at the draft. After it, a prospect's own scoring adds information, because a player who scores at a high rate in junior, college or a European league is more likely to reach the NHL and to contribute when he does. Scoring in different leagues is put on one scale with NHL equivalency (NHLe) factors, which convert a point in a given league and season into the NHL points it is worth."));
add(P(`**The measure.** A season's production is the player's Elite Prospects points times his league-season's NHLe factor (the era-varying factors of Bacon and TopDownHockey), per 82 games, counted for seasons of 10 or more games. His production level weights his three seasons before the valuation season 50/30/20, most recent first, rescaled over the seasons he has. A prospect with no counting season (${f1(100 * N.prod_rows.no_record_share)}% of prospect-seasons) gets an indicator for having no record, so missing data is not read as zero scoring. The median level rises from ${f1(N.prod_median_by_k["0"])} NHL-equivalent points per 82 games at the draft to ${f1(N.prod_median_by_k["4+"])} four or more seasons on.`));
add(TITLE("Table 2. Each production candidate against the slot alone, on the same prospect-seasons"));
const pr = (name, lab, wins) => {
  const a = PA[name];
  return [lab, f4(a.rmse), name === "slot" ? "-" : pct(a.pct), ...a.by_k.map(f4), wins === undefined ? (a.wins === null ? "-" : comma(a.wins)) : wins,
    a.wins === null ? "-" : f3(pOne(a.wins))];
};
add(TABLE(["Candidate", "Held-out error", "vs slot alone", "Season 0", "1", "2", "3", "4+", "Redraws lower than slot (of 2,000)", "One-sided p"],
  [pr("slot", "Slot alone (Section 3)"), pr("production", "Production alone"), pr("slot+production", "Slot + production, straight line"),
    pr("slot+production by position", "Straight line, separate rate for defencemen"), pr("slot+production curved", "Slot + production, curved"),
    pr("production curved", "Production alone, curved"), pr("chosen", "Adopted: curved; slot in seasons 0-2 only")],
  [2250, 900, 850, 720, 720, 720, 720, 720, 1050, 750], [1, 2, 3, 4, 5, 6, 7, 8, 9], [6]));
add(CAPTION("Held-out error is the root mean squared miss in millions of dollars of remaining surplus per prospect-season, each draft predicted from a fit without it; lower is better. Seasons 0-4+ are the same error within each season since the draft. The one-sided p-value is the share of 2,000 redraws of the 11 drafts in which the candidate's error is not lower than the slot alone's. 13,152 prospect-seasons of 2,089 drafted skaters, 2007-2017; goaltenders stay on the slot alone."));
add(H2("Decision: production adds to the slot"));
add(P(`Production alone predicts worse than the slot alone (${pct(PA.production.pct)} in held-out error; lower than the slot in ${PA.production.wins} of 2,000 redraws), so production does not replace the slot at the draft. Added to the slot, it improves the prediction in each season group. Undrafted prospects, who have no slot, use the adopted model with the star probability set to zero (Section 6).`));
add(H2("Decision: production enters curved"));
add(P(`The straight-line version lets each additional NHL-equivalent point add the same dollars. The curved version adds the square of the production level, so the value of an elite scorer rises faster than in proportion. The curved version has the lower held-out error in each season group and improves on the slot alone by ${f2(-PA["slot+production curved"].pct)}%, against ${f2(-PA["slot+production"].pct)}% for the straight line. Its improvement is less consistent across drafts. It is lower than the slot alone in ${comma(PA["slot+production curved"].wins)} of 2,000 redraws (p = ${f3(pOne(PA["slot+production curved"].wins))}), against ${comma(PA["slot+production"].wins)} for the straight line (p = ${f3(pOne(PA["slot+production"].wins))}). I chose the curved version because most of a pick's surplus comes from the few players who become stars, and a straight line cannot let the prospects most likely to become stars rise above the rest. The squared term is significant in each of the first four season groups of the adopted model (p ≤ ${f3(Math.max(...["0", "1", "2", "3"].map((g) => ch("main", g).terms.nhle82_sq.p)))}, Table 5).`));
add(...FIGURE("fig2_production.png", "Figure 2. A #20 pick one season after his draft: value against production",
  `Value in millions of dollars at the 2025-26 cap for a #20 pick (star probability ${f1(100 * PS["20"])}%) one season after his draft, from each candidate's fit on all drafts. Production is NHL-equivalent points per 82 games, weighted 50/30/20 over the three seasons before the valuation season. Vertical lines mark the 25th, 50th, 75th and 90th percentiles of production among prospects one season after their draft (${f1(N.prod_pct_k1["25"])}, ${f1(N.prod_pct_k1["50"])}, ${f1(N.prod_pct_k1["75"])} and ${f1(N.prod_pct_k1["90"])} points). The age-discounted lines use the adopted model (Section 5) for a first-time eligible player with a late birthday (0.4 years younger than the middle of his draft year) and for one drafted a year older.`));
const CO = (g, arm) => N.prod_coefs.find((r) => r.k_group === g && r.arm === arm);
const st1 = CO("1", "slot+production"), cu1 = CO("1", "slot+production curved");
const vS = (q) => st1.p_star * PS["20"] + st1.nhle82 * q, vC = (q) => cu1.p_star * PS["20"] + cu1.nhle82 * q + cu1.nhle82_sq * q * q / 10;
let cross = null, gapMax = 0, gapAt = 0;
for (let q = 0; q <= 25; q += 0.01) { const d = vS(q) - vC(q); if (d > gapMax) { gapMax = d; gapAt = q; } if (cross === null && q > 1 && d < 0) cross = q; }
add(P(`Below ${f1(cross)} points, which is above the 75th percentile, the curved line sits under the straight one; the largest gap is $${f2(gapMax)} million, at ${f1(gapAt)} points. The curved line also dips slightly before it rises. That dip is a property of the quadratic shape, not evidence that a little scoring lowers a prospect's value. The gap between the two versions there is small next to the held-out error of about $3 million in the first season.`));
add(H2("Decision: from the third season, production replaces the slot"));
add(P(`Once production is in the model, the slot stops carrying information three seasons after the draft. Its coefficient is ${money(SL["3"].b).replace("M", " million")} (standard error ${f2(SL["3"].se)}, p = ${f3(SL["3"].p)}) three seasons on and ${money(SL["4+"].b).replace("M", " million")} (standard error ${f2(SL["4+"].se)}, p = ${f3(SL["4+"].p)}) from the fourth. A negative weight on the slot would value a top pick below a later pick with the same production, for which there is no hockey reason. The adopted model keeps the slot for the first three seasons (0, 1 and 2) and uses production alone from the third. This drops one parameter in each later group at no cost: the held-out error is $${f4(PA.chosen.rmse)} million against $${f4(PA["slot+production curved"].rmse)} million with the slot kept throughout.`));
add(H2("Decision: one production rate for forwards and defencemen"));
add(P(`A separate production rate for defencemen was tested. It changes the held-out error by ${pct(PA["slot+production by position"].pct - PA["slot+production"].pct)} against the straight line with one rate, and it is lower than the slot alone in fewer redraws (${comma(PA["slot+production by position"].wins)} against ${comma(PA["slot+production"].wins)}). One rate is kept.`));
add(TITLE("Table 3. The production measure's settings"));
add(TABLE(["Setting", "Adopted", "Alternative", "Why"], [
  ["A counting season", "10 or more games", "Any games", "The same threshold the player model uses for an NHL season; a handful of games gives an unreliable scoring rate."],
  ["Weighting of recent seasons", "50/30/20 over the three seasons before, rescaled over those he has", "Other weights", "The weighting each part of the model uses for recent seasons."],
  ["2012-13 (no NHLe factor; lockout season)", "The mean of the league's 2011-12 and 2013-14 factors", "Leave 2012-13 out", "Keeps a full season of scoring for the 2011-2013 drafts."],
  ["Goaltenders", "The slot alone", "A save-based measure", "NHLe converts scoring, which says nothing about a goaltender."],
  ["No production record", "An indicator, 0 or 1", "Read as zero scoring", "Missing data (an unlisted league) is not evidence of poor play."],
], [2000, 2300, 1700, 4000]));
add(CAPTION("Each setting is applied identically to each candidate in Table 2. The no-record indicator is not significant in any season group (p from 0.131 to 0.640, Table 5); it is kept so that a missing record does not move a prospect's value."));

// 5 ------------------------------------------------------------------------------------------------------
add(H1("5. Age"));
add(P("A player who scores at a given rate at 18 is commonly rated a better prospect than one who scores at the same rate at 20. This section tests whether the data agree. Age enters as years past first eligibility, which is the player's age on September 15 of the autumn after his draft, less 18.5 (a first-time eligible player is between 18.0 and 19.0 then). Within one season group, being older now and having been drafted older are the same quantity, so one measure covers both."));
add(TITLE("Table 4. Each age candidate against the production model without age, on the same prospect-seasons"));
const ar = (name, lab) => { const a = AA[name]; return [lab, f4(a.rmse), name === "chosen" ? "-" : pct(a.pct), pct(a.pct_vs_slot), a.wins === null ? "-" : comma(a.wins), a.wins === null ? "-" : f3(pOne(a.wins))]; };
add(TABLE(["Candidate", "Held-out error", "vs production without age", "vs slot alone", "Redraws lower than without age (of 2,000)", "One-sided p"],
  [ar("chosen", "Production without age (Section 4)"), ar("+ age", "Plus age: a flat amount per year"), ar("+ age x production", "Plus age discounting production, each season group"),
    ar("+ age and age x production", "Plus both"), ar("age x production, seasons 0-3", "Adopted: age discounting production, seasons 0-3")],
  [3000, 1100, 1300, 1100, 1700, 900], [1, 2, 3, 4, 5], [4]));
add(CAPTION("Held-out error as in Table 2. Each candidate keeps the production model of Section 4 and adds the age term shown. With both terms, the redraw comparison against the age discount alone is lower in 1,603 of 2,000 redraws (p = 0.199)."));
add(H2("Decision: age discounts production"));
add(P(`Two forms were tested. Age as a flat amount subtracts the same dollars for each year past eligibility whatever the player scores. Age discounting production multiplies production by years past eligibility, so the same scoring counts for less from an older player. Both are reliable improvements (lower than the model without age in ${comma(AA["+ age"].wins)} and ${comma(AA["+ age x production"].wins)} of 2,000 redraws), and the discount improves held-out error more (${pct(AA["+ age x production"].pct)} against ${pct(AA["+ age"].pct)}). I chose the discount because it is the larger gain and it measures what age was included for, which is how much a player's scoring says about him given his age. Using both terms improves the error slightly further (${pct(AA["+ age and age x production"].pct)}), but it is lower than the discount alone in only 1,603 of 2,000 redraws (p = 0.199). The flat age term also changes sign once the discount is in (Appendix B), which shows the two terms measure the same thing.`));
add(P(`From the fourth season on, age adds nothing: the held-out error in that group is $0.7383 million with the discount against $0.7377 million without it. The adopted model applies the discount in seasons 0-3 only, which improves the error by ${f2(-AA["age x production, seasons 0-3"].pct)}% on the production model and is lower than it in ${comma(AA["age x production, seasons 0-3"].wins)} of 2,000 redraws (p = ${f4(pOne(AA["age x production, seasons 0-3"].wins))}). The discount is significant in each of those groups (p ≤ ${f3(Math.max(...["0", "1", "2", "3"].map((g) => ch("main", g).terms.prod_x_age.p)))}, Table 5).`));
add(H2("Decision: the version without age is kept beside the adopted one"));
add(P(`Age improves the prediction reliably but by little, and it adds one parameter in each of four season groups. On the 197 traded drafted prospects it raises the total from $${f2(TR.tot_noage)} million to $${f2(TR.tot_main)} million. It moves ${TR.age_moved_025} values by $0.25 million or more (${TR.age_moved_050} by $0.5 million or more, the largest by $${f2(TR.age_largest)} million) and leaves the ranking almost unchanged (rank correlation ${f3(TR.age_rank)}). The version without age is reported beside the adopted one, and whether age changes any finding of the trade back-test decides whether it stays.`));
add(TITLE("Table 5. The adopted model: regression by season since the draft"));
const term = (g, c) => { const t = ch("main", g).terms[c]; return t ? `${f3(t.b)} (${f3(t.se)}) [${pfmt(t.p)}]` : "-"; };
add(TABLE(["Term", "Season 0", "Season 1", "Season 2", "Season 3", "4 and later"], [
  ["Star probability for his slot", ...["0", "1", "2", "3", "4+"].map((g) => term(g, "p_star"))],
  ["Production (NHL-equivalent points per 82)", ...["0", "1", "2", "3", "4+"].map((g) => term(g, "nhle82"))],
  ["Production squared, per 10", ...["0", "1", "2", "3", "4+"].map((g) => term(g, "nhle82_sq"))],
  ["No production record", ...["0", "1", "2", "3", "4+"].map((g) => term(g, "no_record"))],
  ["Production × years past first eligibility", ...["0", "1", "2", "3", "4+"].map((g) => term(g, "prod_x_age"))],
  ["Prospect-seasons", ...["0", "1", "2", "3", "4+"].map((g) => comma(ch("main", g).rows))],
  ["Players", ...["0", "1", "2", "3", "4+"].map((g) => comma(ch("main", g).players))],
  ["Drafts", ...["0", "1", "2", "3", "4+"].map((g) => ch("main", g).drafts)],
  ["R-squared", ...["0", "1", "2", "3", "4+"].map((g) => f3(ch("main", g).r2))],
], [2600, 1480, 1480, 1480, 1480, 1480], [1, 2, 3, 4, 5]));
add(CAPTION("Dependent variable: remaining surplus in millions of dollars at the 2025-26 cap. Each cell gives the coefficient, its robust standard error in parentheses (clustered by player for 4 and later) and its two-sided p-value in brackets. Each regression runs through zero with draft-year indicators that sum to zero (not shown), so the coefficients describe an average draft. Production squared is divided by 10 so its coefficient reads on the same scale as production. The low R-squared reflects how uneven outcomes are: most prospects deliver no NHL surplus."));
add(H2("A worked prospect"));
add(P(`${W.name} was traded on ${W.date}, ${W.k === 1 ? "one season" : `${W.k} seasons`} after he was drafted ${W.pick}th overall in ${W.draft}. His slot's star probability is ${f1(100 * W.inputs.p_star)}%, his production level is ${f1(W.prod)} NHL-equivalent points per 82 games${W.k === 1 && W.prod > N.prod_pct_k1["90"] ? " (above the 90th percentile one season after a draft, " + f1(N.prod_pct_k1["90"]) + ")" : ""}, and he was ${f2(Math.abs(W.past))} years ${W.past < 0 ? "younger" : "older"} than the middle of his draft year. Table 6 builds his value from the season-${W.k} regression.`));
add(TITLE(`Table 6. ${W.name}'s value, term by term`));
const lab = { p_star: "Star probability for his slot", nhle82: "Production", nhle82_sq: "Production squared, per 10", no_record: "No production record", prod_x_age: "Production × years past first eligibility" };
add(TABLE(["Term", "His input", "Coefficient (season 1)", "Contribution"], [
  ...Object.keys(W.parts).map((c) => [lab[c], c === "p_star" ? f3(W.inputs[c]) : f2(W.inputs[c]), f3(W.coefs[c]), money(W.parts[c])]),
  ["Value, adopted model", "", "", `**${money(W.value)}**`],
  ["Value without age", "", "", money(W.noage)],
  ["Value on the slot alone (Section 3)", "", "", money(W.slot)],
  ["Value with his draft left out of the fit", "", "", money(W.own_out)],
], [3600, 1500, 1800, 1500], [1, 2, 3], [5]));
add(CAPTION("Millions of dollars at the 2025-26 cap. Contributions are input times coefficient and sum to the adopted value. His production of 15.37 enters squared as 15.37² / 10 = 23.61; years past first eligibility are -0.40, so the age term adds value."));
add(P(`His scoring raises his value from $${f2(W.slot)} million on his slot to $${f2(W.noage)} million, and his youth raises it further to $${f2(W.value)} million.`));

// 6 ------------------------------------------------------------------------------------------------------
add(H1("6. The Traded Prospects"));
add(P(`From July 2017 to March 2022, clubs traded ${TR.drafted} drafted prospects (${TR.drafted_players} players) and ${TR.undrafted} undrafted prospects. The adopted model values them at $${f2(TR.tot_all_main)} million: $${f2(TR.tot_main)} million for the drafted prospects and $${f2(TR.tot_undrafted)} million for the undrafted. Table 7 values the same ${TR.drafted} drafted prospects under each alternative considered above, so each decision's effect can be read in dollars on the same assets.`));
add(TITLE("Table 7. The 197 traded drafted prospects under each version"));
add(TABLE(["Version", "Total value", "vs adopted"], [
  ["Slot alone, draft-day value however long ago (no fade)", money(ALT.slot_no_fade), money(ALT.slot_no_fade - ALT.adopted)],
  ["Slot alone, star value by seasons since the draft (Section 3)", money(ALT.step1_slot), money(ALT.step1_slot - ALT.adopted)],
  ["Slot + production, straight line, slot in each season group", money(ALT.straight_slot_throughout), money(ALT.straight_slot_throughout - ALT.adopted)],
  ["Slot + production, curved, slot in each season group", money(ALT.curved_slot_throughout), money(ALT.curved_slot_throughout - ALT.adopted)],
  ["Curved, slot in seasons 0-2 only, without age", money(ALT.chosen_no_age), money(ALT.chosen_no_age - ALT.adopted)],
  ["Plus age as a flat amount", money(ALT.age_alone), money(ALT.age_alone - ALT.adopted)],
  ["Plus age as a flat amount and discounting production", money(ALT.age_both), money(ALT.age_both - ALT.adopted)],
  ["**Adopted: plus age discounting production, seasons 0-3**", `**${money(ALT.adopted)}**`, "-"],
  ["Adopted, each prospect's draft left out of the fit", money(ALT.own_draft_out), money(ALT.own_draft_out - ALT.adopted)],
], [5600, 1500, 1500], [1, 2], [7]));
add(CAPTION(`Millions of dollars at the 2025-26 cap; ${ALT.skaters_priced} skaters priced under each version and ${ALT.others_on_slot} goaltenders on the slot alone in each. Each version applies its fit on all drafts 2007-2017 to each prospect at the season of his trade.`));
add(P(`Production changes the values far more than age does. Moving from the slot alone to the model without age moves ${TR.prod_moved_025} of the ${TR.drafted} values by $0.25 million or more and leaves ${TR.top20_same_slot} of the 20 most valuable prospects in the top 20 (rank correlation ${f3(TR.prod_rank)}). Adding age moves ${TR.age_moved_025} values by that much and leaves ${TR.top20_same_noage} of the top 20 in place (rank correlation ${f3(TR.age_rank)}).`));
add(...FIGURE("fig3_traded.png", "Figure 3. Production raises some prospects well above their slot's value and lowers others",
  `Each point is one of the ${TR.drafted} traded drafted prospects, valued on the slot alone (horizontal) and on the adopted model (vertical), in millions of dollars at the 2025-26 cap. Points above the dashed line gained value from production and age. Colour shows seasons since the draft at the trade.`, 430));
add(TITLE("Table 8. The ten most valuable traded drafted prospects"));
add(TABLE(["Traded", "Player", "Drafted", "Seasons since the draft", "Production", "Years past eligibility", "Slot alone", "Without age", "Adopted"],
  TR.top10.map((r) => [r.date, r.name, `${r.draft} #${r.pick}`, r.k, r.prod === null ? "-" : f1(r.prod), r.past === null ? "-" : f2(r.past), money(r.slot), money(r.noage), money(r.main)]),
  [1050, 1650, 950, 900, 900, 950, 950, 950, 950], [3, 4, 5, 6, 7, 8]));
add(CAPTION("Production in NHL-equivalent points per 82 games; years past first eligibility as in Section 5 (negative is younger); values in millions of dollars at the 2025-26 cap. Nikita Gusev, a 2012 draftee playing in the KHL, has the highest production level in the data four or more seasons after a draft, and his own career is in the fit that values him."));
add(H2("Undrafted prospects"));
add(P(`An undrafted player has no draft rights, so a club holds his NHL rights only through an NHL contract; an undrafted player on a minor-league contract is worth nothing to an NHL club in this currency. The ${TR.undrafted} undrafted prospects on NHL contracts are valued by the same model with the star probability set to zero. Their seasons are counted from the first draft at which they were eligible, which is the rule for drafted prospects without the slot. They total $${f2(TR.tot_undrafted)} million; the largest is $${f2(TR.max_undrafted)} million. Each is four or more seasons past his first eligible draft, so production alone values him. Because the fit uses drafted players only, the model assumes an undrafted scorer turns production into NHL surplus at the rate a drafted one does.`));
add(H2("Values below zero"));
add(P(`${TR.negative} of the ${TR.all} traded prospects have a value below zero, totalling ${money(TR.negative_sum).replace("M", " million")}; the lowest is ${money(TR.negative_min).replace("M", " million")}. They are low scorers well past their draft: 75 are three or more seasons after it, and 77 score below the median of the traded prospects (13.2 points). In the data, prospects like these deliver a slightly negative remaining surplus on average. Those who never reach the NHL deliver zero, so those who do reach it deliver less than they cost, on average. The draft pick curve counts negative careers in the same way.`));

// Appendix A ---------------------------------------------------------------------------------------------
add(new Paragraph({ children: [new PageBreak()] }));
add(H1("Appendix A. The Decisions"));
add(P("Each row is one decision: what the model does, the alternatives considered, the reason for the choice, and the evidence, with the alternative's effect on the 197 traded drafted prospects where it was measured."));
add(TABLE(["Decision", "Adopted", "Alternatives", "Why", "Evidence and effect"], [
  ["Currency", "Remaining surplus to the end of the club's control", "Entry-level years only", "Control runs to 27 or seven roster seasons; one scale with picks and contracts", "Not measured; the entry-level years alone omit the control years"],
  ["Who is a prospect", "The player model's entry point (no 10+ game season in three; goaltenders no game in six)", "Any NHL game sends him to the player model", "No player is valued twice or by neither model", "The alternative would change the player model's forecast"],
  ["The slot over time", "One star value for each season since the draft, 4 and later pooled", "Draft-day value; one yearly rate of decline", "The decline is a step between the second and fourth seasons", `${money(ALT.slot_no_fade)} without a fade against ${money(ALT.step1_slot)} (slot alone)`],
  ["The overlap with the fit", "A stated limitation; value with his draft left out reported beside", "Refit without each prospect's draft", "Consistent with the draft pick curve", `${money(ALT.own_draft_out)} against ${money(ALT.adopted)}`],
  ["Production's role", "Added to the slot", "Production alone", "Production alone predicts worse at the draft", `Held-out error ${pct(PA.production.pct)} against the slot; ${PA.production.wins} of 2,000 redraws`],
  ["Production's form", "Curved (production and its square)", "Straight line", "Most surplus comes from stars; the curve lets elite scorers rise faster", `Error ${pct(PA["slot+production curved"].pct)} against ${pct(PA["slot+production"].pct)}; p ${f3(pOne(PA["slot+production curved"].wins))} against ${f3(pOne(PA["slot+production"].wins))}; ${money(ALT.curved_slot_throughout)} against ${money(ALT.straight_slot_throughout)}`],
  ["The slot from the third season", "Dropped; production alone", "Keep it in each season group", "Its coefficient is not significant at three and negative from four", `Season 3: ${f2(SL["3"].b)} (p ${f3(SL["3"].p)}); 4+: ${f2(SL["4+"].b)} (p ${f3(SL["4+"].p)}); ${money(ALT.chosen_no_age)} against ${money(ALT.curved_slot_throughout)}`],
  ["Position", "One production rate", "A separate rate for defencemen", "No gain in prediction", `Error ${pct(PA["slot+production by position"].pct - PA["slot+production"].pct)} against one rate; ${PA["slot+production by position"].wins} against ${PA["slot+production"].wins} redraws`],
  ["Production settings", "10+ games; 50/30/20; 2012-13 filled; goaltenders on the slot; a no-record indicator", "See Table 3", "See Table 3", "Applied to each candidate alike"],
  ["Age's form", "Discounting production", "A flat amount; both", "The larger gain; age matters through scoring", `Error ${pct(AA["+ age x production"].pct)} against ${pct(AA["+ age"].pct)} and ${pct(AA["+ age and age x production"].pct)}; ${money(ALT.adopted)} against ${money(ALT.age_alone)} and ${money(ALT.age_both)}`],
  ["Where age applies", "Seasons 0-3", "Each season group", "No gain from the fourth season", "Season-4+ error 0.7383 with age against 0.7377 without"],
  ["Keeping age", "Adopted, the version without age beside it", "Drop age", "A reliable but small gain; the back-test decides", `p ${f4(pOne(AA["age x production, seasons 0-3"].wins))}; ${money(ALT.chosen_no_age)} without age`],
  ["Undrafted prospects", "On NHL contracts only; the same model with the star probability at zero", "All undrafted; a separate fit", "Only an NHL contract gives a club NHL rights; one model for both", `${TR.undrafted} assets, ${money(TR.tot_undrafted)}`],
  ["Trades after the regular season", "Valued at the next season", "The season just ended", "The season's games are played and its data complete at the trade", "23 traded prospects move, -$3.51M in total"],
], [1400, 2000, 1500, 2100, 2600]));
add(CAPTION("Dollar figures are totals for the 197 traded drafted prospects in millions at the 2025-26 cap, from Table 7, except where the row names other assets. Held-out errors and p-values are from Tables 2 and 4."));

// Appendix B ---------------------------------------------------------------------------------------------
add(H1("Appendix B. The Version Without Age, and the Age Terms Tested"));
add(TITLE("Table B1. The version without age: regression by season since the draft"));
const term0 = (g, c) => { const t = ch("no_age", g).terms[c]; return t ? `${f3(t.b)} (${f3(t.se)}) [${pfmt(t.p)}]` : "-"; };
add(TABLE(["Term", "Season 0", "Season 1", "Season 2", "Season 3", "4 and later"], [
  ["Star probability for his slot", ...["0", "1", "2", "3", "4+"].map((g) => term0(g, "p_star"))],
  ["Production (NHL-equivalent points per 82)", ...["0", "1", "2", "3", "4+"].map((g) => term0(g, "nhle82"))],
  ["Production squared, per 10", ...["0", "1", "2", "3", "4+"].map((g) => term0(g, "nhle82_sq"))],
  ["No production record", ...["0", "1", "2", "3", "4+"].map((g) => term0(g, "no_record"))],
  ["R-squared", ...["0", "1", "2", "3", "4+"].map((g) => f3(ch("no_age", g).r2))],
], [2600, 1480, 1480, 1480, 1480, 1480], [1, 2, 3, 4, 5]));
add(CAPTION("As Table 5, on the same prospect-seasons, without the age term."));
add(TITLE("Table B2. The age terms in each tested form"));
const at = (g, arm, c) => {
  const r = AC(g, arm);
  if (!r || r[c] === null || r[c] === undefined) return "-";
  const se = r[`${c}_se`];
  return `${f3(r[c])} (${f3(se)}) [${pfmt(p2(r[c] / se))}]`;
};
add(TABLE(["Form and term", "Season 0", "Season 1", "Season 2", "Season 3", "4 and later"], [
  ["Flat: years past first eligibility", ...["0", "1", "2", "3", "4+"].map((g) => at(g, "+ age", "past_elig"))],
  ["Discount: production × years past eligibility", ...["0", "1", "2", "3", "4+"].map((g) => at(g, "+ age x production", "prod_x_age"))],
  ["Both: years past first eligibility", ...["0", "1", "2", "3", "4+"].map((g) => at(g, "+ age and age x production", "past_elig"))],
  ["Both: production × years past eligibility", ...["0", "1", "2", "3", "4+"].map((g) => at(g, "+ age and age x production", "prod_x_age"))],
], [3100, 1380, 1380, 1380, 1380, 1380], [1, 2, 3, 4, 5]));
add(CAPTION("Coefficients in millions of dollars per year past first eligibility (flat) or per NHL-equivalent point per year (discount), robust standard errors in parentheses and two-sided p-values in brackets; each fitted with the production terms of Section 4. The flat term is negative on its own and turns positive once the discount is in the same regression, which is why both terms together were not adopted."));

// ---- build -------------------------------------------------------------------------------------------
const doc = new Document({
  styles: { default: { document: { run: { font: FONT, size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 28, bold: true, font: FONT, color: "1F1E1C" } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 23, bold: true, font: FONT, color: "2B2A28" } }] },
  sections: [{ properties: { page: { margin: { top: 1080, bottom: 1080, left: 1080, right: 1080 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18, color: "8A8984" })] })] }) },
    children: kids }],
});
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUTFILE, buf);
  console.log(`wrote ${OUTFILE}`);
  if (process.env.LINT_OUT) fs.writeFileSync(process.env.LINT_OUT, TEXT.join("\n\n"), "utf8");
});
