// prospect_doc.js v1.0 -- builds "Valuing Prospects.docx" (40_DOCS/), the third of the four write-up chunks (WORK_QUEUE 0a).
//
// v1.0 (2026-11-27; Thomas: "Agreed, build it", on the outline agreed that day). Sections 7 and 8 and Appendix B of
// "Valuing Players, Draft Picks, and Prospects" v5.0 (model_doc.js v5.0) made into a document of their own, built as
// "Valuing Players" and "Valuing Draft Picks" are (player_doc.js, pick_doc.js): no glossary, each term defined where it
// first appears, the remaining-NPV formula in full, each limit said once, under the writing-style skill v2.0.
//   - Thomas's comments on v5.0's prospect sections (his copy, commit 1026401): 93 (the paragraph on how candidates are
//     judged cut; each caption says it), 94 (out-of-sample RMSE, never held-out error), 95 (no first person), 96 (what age
//     measures, rewritten), 97 (D+2 named as the example season), 98 (each age form named adopted or alternative), 99
//     ("not nested" said in words), 100 ("the median forward scores").
//   - The trade, added up, closes the document (Thomas's choice); its rules are cited from "Valuing Players"; the D+2
//     build-up table joins the other seasons in Appendix A.
//   - Figures: OUTPUT_DIR/model_doc/numbers.json (model_doc_figures.py v4.5: the prospect outputs of 2026-11-24 on today's
//     model; nhl_arrival_timing.py re-run 2026-11-27, its summary unchanged).
//
// v1.1 (2026-11-27; Thomas: "made a few notes and changes"). His edits to his copy (64933c8) carried in; cap* defined after
// the formula (his edit removed its definition); his notes: the age equation beside the explanation of age, "no prospect's
// xNPV", "of the cap", "the 2019 second-round pick", the traded-prospects section cut (its total kept in the limitation).
//
// Run:  NODE_PATH=<folder with docx> node 25_TESTS/prospect_doc.js   (DOC_OUT=<file> to write elsewhere; LINT_OUT=<file.md>)

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType, HeadingLevel,
  BorderStyle, ShadingType, Footer, PageNumber, Math: OMath, MathRun, MathSuperScript, MathSubScript,
  MathFraction, MathSum, MathRoundBrackets,
} = require("docx");

const VERSION = "prospect_doc.js v1.1";
const ROOT = path.resolve(__dirname, "..");
const FIG = path.join(ROOT, "30_OUTPUT", "model_doc");
const N = JSON.parse(fs.readFileSync(path.join(FIG, "numbers.json"), "utf8"));
if (!/^model_doc_figures\.py v4\.([5-9]|\d\d)/.test(String(N.script))) throw new Error(`model_doc numbers from ${N.script}`);
const OUTFILE = process.env.DOC_OUT || path.join(ROOT, "40_DOCS", "Valuing Prospects.docx");
const TEXT = [];

// ---- formatting helpers (as model_doc.js v5.0) ---------------------------------------------------------------------------
const FONT = "Calibri";
const fx = (x, d) => Number(x).toFixed(d);
const f0 = (x) => fx(x, 0), f1 = (x) => fx(x, 1), f2 = (x) => fx(x, 2), f3 = (x) => fx(x, 3), f4 = (x) => fx(x, 4);
const comma = (x) => Number(x).toLocaleString("en-US");
const shareOf = (x, capM, d = 2) => `${x < 0 ? "-" : ""}${fx(Math.abs(100 * x / capM), d)}%`;
const pfmt = (p) => (p === null || p === undefined || Number.isNaN(p) ? "–" : (p < 0.001 ? "<0.001" : f3(p)));
const pq = (p) => (p < 0.0005 ? "p < 0.001" : `p = ${p < 0.01 ? f4(p) : f3(p)}`);
const pr = (p) => (p < 0.0005 ? "<0.001" : (p < 0.01 ? f4(p) : f3(p)));
const z = (x, d) => (Math.abs(x) < 0.5 * 10 ** -d ? (0).toFixed(d) : Number(x).toFixed(d));
const pct = (x, d = 1) => `${fx(100 * x, d)}%`;
const cc = (t, d = 3, scale = 1) => (t ? `${z(t.b * scale, d)} (${t.se === null || Math.abs(t.se) < 1e-12 ? "–" : fx(t.se * scale, d)})\n[${t.se === null || Math.abs(t.se) < 1e-12 ? "–" : pfmt(t.p)}]` : "");
const listAnd = (xs) => (xs.length < 3 ? xs.join(" and ") : `${xs.slice(0, -1).join(", ")}, and ${xs[xs.length - 1]}`);

function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|(?<![A-Za-z0-9])\*[^*\s][^*]*\*|_\{[^}]+\}|\^\{[^}]+\})/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), font: FONT, ...base }));
    const t = m[0];
    if (t.startsWith("_{") || t.startsWith("^{")) out.push(new TextRun({ text: t.slice(2, -1), font: FONT, ...base, [t[0] === "_" ? "subScript" : "superScript"]: true }));
    else out.push(new TextRun({ text: t.replace(/\*/g, ""), font: FONT, ...base, bold: t.startsWith("**") || base.bold, italics: !t.startsWith("**") }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), font: FONT, ...base }));
  return out;
}
const P = (text) => { TEXT.push(text); return new Paragraph({ children: runs(text), spacing: { before: 60, after: 120, line: 276 } }); };
const H1 = (text) => { TEXT.push(`## ${text}`); return new Paragraph({ heading: HeadingLevel.HEADING_1, keepNext: true, children: [new TextRun({ text, font: FONT })], spacing: { before: 280, after: 120 } }); };
const H2 = (text) => { TEXT.push(`### ${text}`); return new Paragraph({ heading: HeadingLevel.HEADING_2, keepNext: true, children: [new TextRun({ text, font: FONT })], spacing: { before: 200, after: 80 } }); };
const CAPTION = (text) => { TEXT.push(text); return new Paragraph({ spacing: { before: 40, after: 220 }, children: runs(text, { size: 18, color: "52514E" }) }); };
const TITLE = (text) => new Paragraph({ spacing: { before: 180, after: 60 }, keepNext: true, children: runs(text, { size: 20, bold: true }) });
const BULLET = (text) => { TEXT.push(`- ${text}`); return new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: runs(text), spacing: { before: 20, after: 60, line: 276 } }); };

function mathKids(pieces) {
  const L = (x) => (Array.isArray(x) && !["_", "^", "/", "sum", "()"].includes(x[0]) ? x : [x]);
  return pieces.map((x) => {
    if (!Array.isArray(x)) return new MathRun(x);
    if (x[0] === "^") return new MathSuperScript({ children: mathKids(L(x[1])), superScript: mathKids(L(x[2])) });
    if (x[0] === "_") return new MathSubScript({ children: mathKids(L(x[1])), subScript: mathKids(L(x[2])) });
    if (x[0] === "/") return new MathFraction({ numerator: mathKids(x[1]), denominator: mathKids(x[2]) });
    if (x[0] === "sum") return new MathSum({ children: mathKids(x[2]), subScript: mathKids(L(x[1])) });
    if (x[0] === "()") return new MathRoundBrackets({ children: mathKids(x[1]) });
    throw new Error(`EQ piece ${x[0]}`);
  });
}
function mathText(pieces) {
  const L = (x) => (Array.isArray(x) && !["_", "^", "/", "sum", "()"].includes(x[0]) ? x : [x]);
  return pieces.map((x) => {
    if (!Array.isArray(x)) return x;
    if (x[0] === "^") return `${mathText(L(x[1]))}^${mathText(L(x[2]))}`;
    if (x[0] === "_") return `${mathText(L(x[1]))}_${mathText(L(x[2]))}`;
    if (x[0] === "/") return `(${mathText(x[1])}) / (${mathText(x[2])})`;
    if (x[0] === "sum") return `Σ_${mathText(L(x[1]))} ${mathText(x[2])}`;
    return `(${mathText(x[1])})`;
  }).join("");
}
function EQ(pieces) {
  TEXT.push(mathText(pieces));
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 100, after: 140 }, children: [new OMath({ children: mathKids(pieces) })] });
}
const SUB = (b, i) => ["_", b, i];
const DISC = (i) => [["^", "1.03", i]];

// tables and figures numbered from one list each
const TABS = ["pstar", "fade", "prod", "age", "def", "adopted", "suzuki", "trade", "sides"];
const APPX = { buildAll: "A1" };
const FIGS = ["arrival", "fade", "prospect", "trade"];
const tn = (k) => { if (APPX[k]) return APPX[k]; const i = TABS.indexOf(k); if (i < 0) throw new Error(`table ${k}`); return String(i + 1); };
const T = (k) => `Table ${tn(k)}`;
const F = (k) => { const i = FIGS.indexOf(k); if (i < 0) throw new Error(`figure ${k}`); return `Figure ${i + 1}`; };
const TT = (k, title) => TITLE(`${T(k)}. ${title}`);
function FIGURE(key, file, title, caption, width = 600) {
  const b = fs.readFileSync(path.join(FIG, file));
  const w = b.readUInt32BE(16), h = b.readUInt32BE(20);
  return [TITLE(`${F(key)}. ${title}`), new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true,
    children: [new ImageRun({ type: "png", data: b, transformation: { width, height: Math.round(width * h / w) } })] }), CAPTION(caption)];
}
const border = { style: BorderStyle.SINGLE, size: 4, color: "C9C8C3" };
const borders = { top: border, bottom: border, left: border, right: border };
function TABLE(header, rows, widths, numeric = [], bold = new Set(), size = 17, keep = true) {
  const tot = widths.reduce((a, b) => a + b, 0);
  if (tot > 9660) throw new Error(`table too wide: ${tot}`);
  rows.forEach((r) => { if (r.length !== header.length) throw new Error(`row of ${r.length} cells under ${header.length} headers: ${r[0]}`); });
  const cell = (text, i, j, head, kp) => new TableCell({
    borders, width: { size: widths[i], type: WidthType.DXA },
    shading: head ? { fill: "EFEEEA", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 40, bottom: 40, left: 70, right: 70 },
    children: String(text).split("\n").map((line) => new Paragraph({ keepNext: kp,
      alignment: numeric.includes(i) ? AlignmentType.RIGHT : AlignmentType.LEFT,
      children: runs(line, { size, bold: !!head || bold.has(`${j},${i}`) }) })),
  });
  return new Table({ width: { size: tot, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: header.map((t, i) => cell(t, i, -1, true, true)) }),
      ...rows.map((r, j) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, i, j, false, keep && j < rows.length - 1)) }))] });
}
// the lowest number in each listed column, at the precision shown; each tie bold
function bestKeys(rows, cols, dp = 4) {
  const keys = new Set();
  cols.forEach((c) => {
    const vals = rows.map((r) => { const v = parseFloat(String(r[c]).replace(/[^0-9.-]/g, "")); return Number.isFinite(v) ? Number(v.toFixed(dp)) : null; });
    const ok = vals.filter((v) => v !== null);
    if (!ok.length) return;
    const best = Math.min(...ok);
    vals.forEach((v, j) => { if (v === best) keys.add(`${j},${c}`); });
  });
  return keys;
}

// ---- numbers -------------------------------------------------------------------------------------------------------------
function erf(x) { const s = Math.sign(x); x = Math.abs(x); const t = 1 / (1 + 0.3275911 * x);
  return s * (1 - t * Math.exp(-x * x) * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))))); }
const p2 = (b, se) => 2 * (1 - 0.5 * (1 + erf(Math.abs(b / se) / Math.SQRT2)));   // two-sided normal p
function bestHigh(rows, col, dp = 4) {   // the highest number in a column, at the precision shown; each tie bold
  const vals = rows.map((r) => { const v = parseFloat(String(r[col])); return Number.isFinite(v) ? Number(v.toFixed(dp)) : null; });
  const best = Math.max(...vals.filter((v) => v !== null));
  return new Set(vals.map((v, j) => (v === best ? `${j},${col}` : null)).filter(Boolean));
}
const H = N.heavy;
const CAP = H.cap, CAP25 = CAP["2025"], CAP18 = CAP["2018"], CAP25M = CAP25 / 1e6;
const M = (x) => x / 1e6;
const money = (x) => shareOf(x, CAP25M);                 // x in $M at the 2025-26 cap
const mil = (x) => `${shareOf(x, CAP25M)} of the cap`;
const K25 = 100 / CAP25M;                                 // $M at the 2025-26 cap -> percent of it
const PK = N.picks, PS = PK.p_star;
const PR = N.prospects, TRD = N.trade;
const PD = PR.doc, PM = PD.models, PTS = PD.tests, PMT = PD.model_traded, PC = PD.coefs, PW = PD.worked;
const pdr = (nm) => PMT[nm].drafted;
const SEAS = { "0": "D+1", "1": "D+2", "2": "D+3", "3": "D+4", "4+": "D+5 and later" };
const G5 = ["0", "1", "2", "3", "4+"];
const ARR = PR.arrival;
const cumA = (grp, upto) => { let s = 0; for (let i = 1; i <= upto; i++) s += (ARR[grp][`D+${i}`] || { share_of_all: 0 }).share_of_all; return 100 * s; };
const everA = (grp) => 100 * (1 - ARR[grp].never.share_of_all);
const FS = Object.fromEntries(PR.fade.scores.map((r) => [r.rule, r]));
const FC = PR.fade.curves;
if (PW.name !== "Nick Suzuki" || Math.abs(PW.value - PR.suzuki.value) > 1e-9) throw new Error("the worked prospect is not Suzuki at this trade");

const kids = [];
const add = (...xs) => xs.flat().forEach((x) => kids.push(x));
add(new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: "Valuing Prospects", bold: true, size: 40, font: FONT })] }));

// =====================================================================================================================
// OPENING AND DATA
// =====================================================================================================================
add(P("A prospect is a drafted player who has not yet established himself in the NHL. A club that trades one gives up the chance that he becomes an NHL player before he has shown whether he will. This document values a prospect in the same currency as a player under contract and a draft pick: his expected net present value (xNPV), stated as a share of the salary cap."));
add(P("A drafted player is a prospect while the player model does not yet value him: a skater with no NHL season of 10 or more games in the three before the valuation season, or a goaltender with no NHL game in the six before it. This boundary means no player is valued twice or by neither model at a given valuation date."));
add(P("The example used throughout is Nick Suzuki, drafted 13th overall by Vegas in 2017 and traded to Montreal on September 10, 2018, with Tomas Tatar and a 2019 second-round pick, for Max Pacioretty. With Suzuki valued, all four assets of that trade are on one scale."));
add(H2("The data and their sources"));
add(P("Scoring outside the NHL comes from Elite Prospects, the largest public database of player statistics across junior, college, and professional leagues worldwide, which records each player's games and points by league and season. Scoring in different leagues is put on one scale with the NHL equivalency (NHLe) factors of Patrick Bacon, the data scientist whose WAR and draft model the player and pick models use, published with their method on HockeyStats.com. A league's NHLe factor is the number of NHL points that one point in that league and season is worth. Bacon estimates it from players who played full seasons in two different leagues in consecutive years, adjusted for a year of development, on a rolling four-season window, so a league's factor changes over time. The draft records, the star probabilities, and the pricing of a drafted player's seasons are those of Valuing Draft Picks."));

// =====================================================================================================================
// 1. WHAT A PROSPECT IS WORTH
// =====================================================================================================================
add(H1("1. What a Prospect Is Worth"));
add(P("A prospect's value is estimated from what drafted players in his position went on to deliver. The outcome is his remaining NPV, the net present value he delivered from the valuation season to the end of club control:"));
add(EQ([SUB("remaining NPV", "it"), " = ", ["sum", "s ≥ t", [["()", [SUB("V", "s"), " − ", SUB("C", "s")]], " × ", ["/", ["cap*"], [SUB("cap", "s")]]]]]));
add(P("Here t is the valuation season, V_{s} and C_{s} are season s's value and cost in that season's dollars, priced as for a drafted player, cap_{s} is that season's cap, and cap* is the 2025-26 cap. On the value side, cap growth and the discount cancel, as for a drafted player. Seasons are named from the draft: D0 is the season of the draft, D+1 the season starting the autumn after it, and so on."));
add(P(`The model is estimated on the ${comma(PK.n)} players drafted from 2007 to 2017, in each season from D+1 on in which a player was still a prospect and his club still controlled him. A prospect traded between the draft and the start of D+1 is valued as in D+1. Suzuki was traded at the start of his D+2 season, so D+2 is the example season throughout.`));

// =====================================================================================================================
// 2. DRAFT POSITION AND HOW ITS VALUE FADES
// =====================================================================================================================
add(H1("2. Draft Position and How Its Value Fades"));
const A10 = "picks 1-10", A37 = "rounds 3-7", AALL = "all drafted players";
add(P(`At the draft, a pick is worth its draft position's star probability times the star value. A prospect starts with his pick's value, and how that value changes while he remains unproven depends on when drafted players reach the NHL. Of the ${comma(PK.n)} drafted players, ${f1(everA(AALL))}% played an NHL season of 10 or more games (a goaltender, an NHL game) before their club's control ended (${F("arrival")}). Of the 110 top-ten picks, ${f1(cumA(A10, 3))}% had reached the NHL by D+3. Of the picks from rounds 3 to 7, ${f1(cumA(A37, 4))}% had reached it by D+4, and ${f1(everA(A37))}% ever did. A top pick still a prospect in D+4 is unusual, and later picks who reach the NHL reach it later.`));
add(FIGURE("arrival", "fig_arrival.png", "When drafted players reach the NHL",
  "Drafted players of 2007 to 2017. Each line is the share of a draft group's players who had reached the NHL by each season; the gap above a line at D+9 is the share who never did. Reaching the NHL means a first NHL season of 10 or more games (for a goaltender, a first NHL game), the point at which he is valued by the player model; only seasons within club control are counted."));
add(P("Each prospect's remaining NPV is regressed on the star probability for his draft position, interacted with a dummy variable for each season group, with no intercept:"));
add(EQ([SUB("remaining NPV", "it"), " = ", ["sum", "n", [SUB("θ", "n"), SUB("I", "nt"), SUB("S", "i")]], " + ", SUB("ε", "it")]));
add(P("S_{i} is the star probability for player i's draft position. I_{nt} is a set of five dummy variables, one for each season group: D+1, D+2, D+3, D+4, and D+5 or later. Interacting the set with S_{i} gives the star probability a separate, estimated coefficient θ_{n} in each group, the star value for that group: a prospect's value at a star probability of 100%."));
const S_ = PR.star;
add(P(`A prospect keeps most of his draft position's value through D+3 and loses most of it over the next two seasons (${T("pstar")}). By D+4, most top picks who will reach the NHL have done so. The prospects left are mostly later picks and top picks who did not develop, and among them draft position no longer separates those who will succeed from those who will not.`));
add(TT("pstar", "The star value for a player still a prospect, by season"));
add(TABLE(["Season", "Prospect-seasons", "Star value (s.e.)", "p-value", "#1 pick", "#13 pick", "#32 pick"],
  G5.map((g) => [g === "0" ? "D+1 (at the draft)" : SEAS[g], comma(S_[g].rows), `${money(S_[g].b)} (${f2(S_[g].se * K25)})`, pfmt(p2(S_[g].b, S_[g].se)), money(S_[g].b * PS["1"]), money(S_[g].b * PS["13"]), money(S_[g].b * PS["32"])]),
  [2000, 1600, 1600, 900, 1100, 1100, 1100], [1, 2, 3, 4, 5, 6]));
add(CAPTION("Drafted players of 2007 to 2017 still prospects, within club control. Star value in percent of the 2025-26 cap; one regression with a full set of interaction terms, standard errors clustered by player, since one player appears in several seasons; two-sided p-values. The pick columns multiply the star value by the star probability for the draft position."));
add(P(`Three simpler alternatives were tested and rejected (${T("fade")}, ${F("fade")}): one value for all seasons (the draft-day value kept for as long as a player remains a prospect), a straight-line decline, and the same percentage decline each season.`));
add(FIGURE("fade", "fig_star_fade.png", "The star value by season, and three rejected alternatives",
  "Orange: each rejected alternative, estimated on the same prospect-seasons. Blue: the adopted star values with 95% intervals; from D+5 on, one shared value. Percent of the 2025-26 cap."));
const FRR = [["A separate value for each season (adopted)", "separate", "-"], ["One value for all seasons", "no fade", pr(PD.fade_wald_one.p)],
  ["Straight-line decline", "straight line", `${f3(PD.fade_wald_steps.p)} (equal drops, D+1 to D+4)`], ["Same percentage decline each season", "same percentage", `${f3(PD.fade_wald_ratio.p)} (equal shares, D+1 to D+4)`]];
add(TT("fade", "Each alternative for the star value compared with the adopted one"));
const fadeRows = FRR.map(([lab, k, t]) => [lab, f4(PD.fade_r2[k].r2), t, f4(FS[k].rmse_M * K25), f2(FC[k][4] * K25), money(FS[`traded total: ${k}`].total_M), String(FS[`traded total: ${k}`].below_zero)]);
add(TABLE(["Alternative", "R-squared", "Test against the adopted model (p)", "Out-of-sample RMSE", "Star value, D+5 (% of the cap)", `${PR.traded.drafted} traded prospects, draft position alone`, "Values below zero"],
  fadeRows, [2500, 900, 1800, 1000, 1000, 1400, 1000], [1, 3, 4, 5, 6], bestHigh(fadeRows, 1), 16));
add(CAPTION(`R-squared measured from zero, since the regressions have no constant, over ${comma(FS.separate.rows)} prospect-seasons; the highest is in bold. Wald tests in the adopted regression, standard errors clustered by player: that the five star values are equal; that the star value falls by the same amount from D+1 to D+2, D+2 to D+3, and D+3 to D+4; that it keeps the same share of itself over those steps (a non-linear restriction, tested by the delta method). Out-of-sample RMSE: each draft predicted from a regression on the other ten, in percent of the cap of remaining NPV per prospect-season.`));
add(P(`One value for all seasons is rejected (${pq(PD.fade_wald_one.p)}). Neither the straight-line decline (p = ${f3(PD.fade_wald_steps.p)}) nor the same percentage decline (p = ${f3(PD.fade_wald_ratio.p)}) is rejected at the 5% level, and neither has a lower out-of-sample root mean squared error (RMSE), the square root of the average squared miss when each draft is predicted from a regression on the other ten. A separate value for each season was chosen for two reasons. It assumes no shape for the decline, and the estimates hold through D+3 and then fall, which matches when top picks reach the NHL. The straight-line decline also falls past zero: from D+8 a top pick is valued below a late pick, which makes no logical sense, and it puts ${FS["traded total: straight line"].below_zero} of the traded prospects below zero.`));
if (!(FS["straight line"].rmse_M > FS.separate.rmse_M && FS["same percentage"].rmse_M > FS.separate.rmse_M)) throw new Error("an alternative has the lower out-of-sample RMSE");

// =====================================================================================================================
// 3. PRODUCTION
// =====================================================================================================================
add(H1("3. Production"));
add(P("Draft position is one element of what predicts a prospect's value; how much he scores after the draft is another. A player who scores at a high rate in junior, college, or a European league is more likely to reach the NHL and to contribute when he does."));
add(P(`A season's production is the player's points times his league-season's NHLe factor, per 82 games, counted for seasons of 10 or more games. His production level weights his three seasons before the valuation season 50/30/20, rescaled over the seasons he has, as each part of the model weights recent seasons; a prospect valued in D+1 is measured on D0, D-1, and D-2, the scoring scouts saw before the draft. A prospect with no counted season (${pct(PR.no_record_share)} of prospect-seasons) has a production level of zero, so he is valued on his draft position alone in the model. A dummy variable for having no record was tested and dropped: its statistical significance rests on a single prospect-season in D+3, and no traded prospect's value changed. Goaltenders are valued on draft position alone, since NHLe converts only skater scoring, so the models from here on are estimated on the ${comma(PR.rows)} prospect-seasons of the ${comma(PR.players)} drafted skaters.`));
const PROW = [["(1) Draft position alone", "slot", "-"], ["(2) Linear production alone", "lin_alone", "-"],
  ["(3) Draft position + linear production", "slot_lin", `vs (1): ${pr(PTS.lin_vs_slot.p)}`],
  ["(4) Draft position + linear and squared production", "slot_linsq", `vs (3): ${pr(PTS.sq_given_lin.p)}`],
  ["(5) As (4), draft position in D+1 to D+3 only", "s2", `vs (4), without draft position in D+4 and later: ${pr(PTS.slot_late.p)}`],
  ["(6) As (5), production squared alone", "s2_sq_alone", `vs (5), without linear production: ${pr(PTS.lin_s2.p)}`]];
const MROW = (rows) => rows.map(([lab, nm, t]) => [lab, f4(PM[nm].r2), t, money(pdr(nm))]);
const MHD = (first) => [first, "R-squared", "Test of the added terms (p)", `${PR.traded.drafted} traded drafted prospects`];
add(P(`${T("prod")} adds production to draft position one term at a time.`));
add(TT("prod", "Production added to draft position: each candidate"));
add(TABLE(MHD("Candidate"), MROW(PROW), [4400, 1100, 2700, 1440], [1, 3], bestHigh(MROW(PROW), 1), 16));
add(CAPTION(`Each candidate is one regression with the full set of interaction terms, on the same ${comma(PR.rows)} prospect-seasons, before age and the defenceman term. R-squared measured from zero; the highest is in bold. Test of the added terms: Wald test, standard errors clustered by player, that the coefficients named are zero in every season where they appear; for (5) and (6), the test of the terms dropped. Traded drafted prospects: goaltenders on draft position alone, percent of the 2025-26 cap.`));
add(P(`Added to draft position, NHLe production is statistically significant (${pq(PTS.lin_vs_slot.p)}). With linear production each additional NHLe point adds the same dollars; with production squared, each point adds more the higher a prospect already scores. The squared term was added because most of a pick's value comes from the few players who become stars, and every prospect at a draft position has the same star probability whatever he scores. It is statistically significant (${pq(PTS.sq_given_lin.p)}) and raises R-squared from ${f4(PM.slot_lin.r2)} to ${f4(PM.slot_linsq.r2)}. Production squared alone, without linear production, is rejected (${pq(PTS.lin_s2.p)}). Once production is in the model, draft position stops carrying information in D+4. Its coefficients in D+4 and from D+5 on are together not statistically significant (p = ${f3(PTS.slot_late.p)}), so draft position is kept from D+1 to D+3 only.`));
add(P("With production, where P_{it} is his production level in NHLe points per 82 games in season t, and draft position out from D+4 (a_{4} = a_{5} = 0):"));
add(EQ([SUB("remaining NPV", "it"), " = ", ["sum", "n", [SUB("I", "nt"), ["()", [SUB("a", "n"), SUB("S", "i"), " + ", SUB("b", "n"), SUB("P", "it"), " + ", SUB("c", "n"), ["^", SUB("P", "it"), "2"]]]]], " + ", SUB("ε", "it")]));

// =====================================================================================================================
// 4. AGE
// =====================================================================================================================
add(H1("4. Age"));
add(P("A player who scores at a given rate at 18 is commonly rated a better prospect than one who scores at the same rate at 20. Age is the player's age on September 15 of the valuation season, the date the CBA uses. A player is first eligible for the draft in the year he is 18 by September 15, so in D+1 a player drafted at his first opportunity is 18 to 19."));
add(P("The prospects compared within one season are all the same number of seasons past their draft. Among them, the older prospect scored his points at an older age, which is what age measures here. From one season to the next, every prospect is a year older and a year further from his draft, so age and seasons since the draft move together; age therefore has its own coefficient in each season rather than one across all seasons."));
add(P("Age enters as a discount on production. With A_{it} his age on September 15 of season t, the term d_{n}P_{it}(A_{it} − 18) changes the value of each of his points by d_{n} for each year of age above 18; d_{n} is negative, so the same points are worth less when scored older. The discount is out from D+5 (d_{5} = 0):"));
add(EQ([SUB("remaining NPV", "it"), " = ", ["sum", "n", [SUB("I", "nt"), ["()", [SUB("a", "n"), SUB("S", "i"), " + ", SUB("b", "n"), SUB("P", "it"), " + ", SUB("c", "n"), ["^", SUB("P", "it"), "2"], " + ", SUB("d", "n"), SUB("P", "it"), ["()", [SUB("A", "it"), " − 18"]]]]]], " + ", SUB("ε", "it")]));
const AROW = [["(5) Draft position in D+1 to D+3, linear and squared production", "s2", "-"],
  ["(7) Plus age as a flat amount, D+1 to D+4", "s3_flat", `vs (5): ${pr(PTS.flat.p)}`],
  ["(8) Plus age discounting production, D+1 to D+4 (adopted)", "s3", `vs (5): ${pr(PTS.disc.p)}`],
  ["(9) Plus both", "s3_both", `vs (8), the flat amount: ${pr(PTS.flat_given_disc.p)}`],
  ["(10) As (8), the discount from D+5 on as well", "s3_age_late", `vs (8): ${pr(PTS.age_late.p)}`]];
const d2_ = PC.s3["1"].A.b;
add(P(`Two forms of age were tested (${T("age")}). The adopted form, age discounting production, makes each point worth less the older the player was when he scored it: in D+2, of two prospects with 10 points, the one a year older is worth ${mil(-10 * d2_)} less. The alternative, age as a flat amount, subtracts the same dollars for each year of age whatever the player scores: ${mil(-PC.s3_flat["1"].F.b)} a year in D+2. Each is statistically significant on its own (${pq(PTS.disc.p)} for the discount, ${pq(PTS.flat.p)} for the flat amount). With both in the model, the discount stays statistically significant (${pq(PTS.disc_given_flat.p)}) and the flat amount does not (p = ${f3(PTS.flat_given_disc.p)}), so the discount is adopted. It also directly measures what age was included to account for, which is how much a player's scoring says about him given his age. From D+5 on the discount is not statistically significant (p = ${f3(PTS.age_late.p)}), so it applies from D+1 to D+4.`));
add(TT("age", "Each age candidate added to the model with production"));
add(TABLE(MHD("Candidate"), MROW(AROW), [4400, 1100, 2700, 1440], [1, 3], bestHigh(MROW(AROW), 1), 16));
add(CAPTION(`As ${T("prod")}. Age is his age on September 15 of the valuation season, less 18.`));
add(P(`A third form, which applies the discount to the points themselves so that a point scored a year older counts as a fraction of a point, was tested in four versions and rejected. The closest, age-adjusted points, has a slightly higher R-squared (${f4(PD.disc_forms.adj_disc.r2)} compared with ${f4(PD.disc_forms.adopted.r2)}). Neither model is a special case of the other, so no test of added terms can compare them. Compared on out-of-sample RMSE instead, age-adjusted points is not better by a statistically significant amount (${f4(PD.disc_forms.adj_disc.rmse)} compared with ${f4(PD.disc_forms.adopted.rmse)}; one-sided p = ${f2(PD.disc_p_heldout)}). The linear age discount was adopted for simplicity.`));

// =====================================================================================================================
// 5. DEFENCEMEN
// =====================================================================================================================
add(H1("5. Defencemen"));
const MPP = PD.prod_median_pos, EC = PD.econ;
add(P(`Defencemen score less than forwards: among prospects with a production record in D+2, the median defenceman scores ${f1(MPP["1"].D)} NHLe points per 82 games and the median forward scores ${f1(MPP["1"].F)}. To test whether a defenceman's point is worth a different amount, a defenceman dummy variable D_{i}, equal to 1 for a defenceman and 0 for a forward, is interacted with production, so D_{i} × P_{it} enters each season with its own coefficient f_{n} (${T("def")}).`));
const DROW = [["(8) Model with age", "s3", "-"], ["(11) Plus defenceman × production (adopted)", "adopted", `vs (8): ${pr(PTS.def.p)}`],
  ["(12) As (11), plus defenceman × production squared", "adopted_dq", `vs (11): ${pr(PTS.dq.p)}`],
  ["(13) As (11), plus defenceman × star probability, D+1 to D+3", "adopted_ds", `vs (11): ${pr(PTS.ds.p)}`]];
add(TT("def", "Defenceman terms added to the model with age"));
add(TABLE(MHD("Model"), MROW(DROW), [4400, 1100, 2700, 1440], [1, 3], bestHigh(MROW(DROW), 1), 16));
add(CAPTION(`As ${T("prod")}.`));
add(P(`The defenceman term is statistically significant (${pq(PTS.def.p)}) and positive in each season. A #20 pick in D+2 who is 19.5 and scores 20 points is worth ${mil(EC.fwd_20_k1)} as a forward and ${mil(EC.def_20_k1_value)} as a defenceman. Defenceman × production squared (p = ${f3(PTS.dq.p)}) and a separate star value for defencemen (p = ${f3(PTS.ds.p)}) are not statistically significant given it.`));

// =====================================================================================================================
// 6. THE ADOPTED MODEL
// =====================================================================================================================
add(H1("6. The Adopted Model"));
add(P("The adopted model values a prospect as follows, with draft position out from D+4 (a_{4} = a_{5} = 0) and the age discount out from D+5 (d_{5} = 0):"));
add(EQ([SUB("remaining NPV", "it"), " = ", ["sum", "n", [SUB("I", "nt"), ["()", [SUB("a", "n"), SUB("S", "i"), " + ", SUB("b", "n"), SUB("P", "it"), " + ", SUB("c", "n"), ["^", SUB("P", "it"), "2"], " + ", SUB("d", "n"), SUB("P", "it"), ["()", [SUB("A", "it"), " − 18"]], " + ", SUB("f", "n"), SUB("D", "i"), SUB("P", "it")]]]], " + ", SUB("ε", "it")]));
add(P(`${T("adopted")} gives its coefficients in each season, and ${F("prospect")} shows what they imply for a forward drafted 13th, in D+2. Appendix A builds each season's regression up one term at a time.`));
const BROW = [["S", "Star probability (a)", 3], ["P", "Production (b)", 3], ["Q", "Production squared (c)", 4], ["A", "Production × (age − 18) (d)", 3], ["D", "Defenceman × production (f)", 3]];
add(TT("adopted", "The adopted prospect model, by season"));
add(TABLE(["Term", ...G5.map((g) => SEAS[g])],
  [...BROW.map(([k, lab, d]) => [lab, ...G5.map((g) => cc(PC.adopted[g][k], d, K25))]), ["Prospect-seasons", ...G5.map((g) => comma(PR.adopted[g].rows))], ["R-squared", ...G5.map((g) => f3(PD.season_r2.adopted[g]))]],
  [2440, 1440, 1440, 1440, 1440, 1440], [1, 2, 3, 4, 5]));
add(CAPTION(`Dependent variable: remaining NPV, percent of the 2025-26 cap. One regression with a full set of interaction terms and no intercept, drafted skaters 2007-2017; coefficient (standard error clustered by player) [two-sided p-value]; R-squared within each season, measured from zero (${f4(PM.adopted.r2)} over all prospect-seasons). Production squared is in squared points (15 points enter as 225). A blank cell means the term is not in that season's model. The low R-squared reflects how uneven outcomes are, since most prospects deliver no NHL value.`));
add(FIGURE("prospect", "fig_prospect.png", "A prospect drafted 13th, in D+2",
  `The adopted model's xNPV for a forward against production level, at ages 19, 20, and 21 on September 15 of the valuation season, with Nick Suzuki at the trade. Vertical lines mark the 25th, 50th, 75th, and 90th percentiles of production level among prospects in D+2 with a record. Percent of the 2025-26 cap.`));
const sigD = G5.filter((g) => PC.adopted[g].D.p < 0.05).map((g) => SEAS[g]), nsD = G5.filter((g) => PC.adopted[g].D.p >= 0.05).map((g) => SEAS[g]);
add(P(`Three terms of the adopted model are kept although they are not statistically significant in every season. The defenceman term is statistically significant in ${listAnd(sigD)}, not in ${nsD.join(" or ")}; it is kept in each season because the five together are statistically significant (p = ${f3(PTS.def.p)}).`));
add(P(`Linear production is not statistically significant in any season; it stays because its p-value does not test whether it belongs. With production × (age − 18) in the model, b is the linear value of a point for a prospect who is exactly 18 on September 15. Measuring age from another starting age changes b and its p-value but no prospect's xNPV. The test that b is zero in every season gives p = ${f3(PTS.lin_zero["18"].p)} with age measured from 18, ${pq(PTS.lin_zero["19"].p)} from 19, and ${pq(PTS.lin_zero["20"].p)} from 20, on the same fitted values. Dropping b would set a point's linear value to zero at whichever starting age is chosen, so the values would depend on a choice the data give no way to make.`));
add(P(`From D+5 on, production and its square are together not statistically significant (p = ${f3(PTS.late_prod.p)}). Dropping them would value every prospect from D+5 on at zero, drafted or undrafted, and it raises the out-of-sample RMSE from D+5 on from ${f4(PM.adopted.rmse_by_k["4+"])} to ${f4(PM.no_late.rmse_by_k["4+"])}. Production is kept there because a late prospect's scoring is the only evidence of his progress: without it, a prospect in D+6 scoring at the top of the AHL and one who has stopped scoring would be valued the same.`));
if (!(PM.no_late.rmse_by_k["4+"] > PM.adopted.rmse_by_k["4+"])) throw new Error("dropping late production does not raise the RMSE");

// =====================================================================================================================
// 7. NICK SUZUKI
// =====================================================================================================================
add(H1("7. Nick Suzuki"));
add(P(`Suzuki was traded at the start of his D+2 season. His draft position's star probability is ${pct(PW.inputs.S)}, his production level is ${f1(PW.prod)} NHLe points per 82 games (above the 90th percentile in D+2, ${f1(PR.pct_d2["90"])}), he was ${f1(PW.age)} on September 15, 2018, as a player drafted at his first opportunity, and he is a forward. ${T("suzuki")} builds his value from the D+2 regression.`));
add(TT("suzuki", "Nick Suzuki's xNPV, term by term"));
add(TABLE(["Term", "His input", "Coefficient (D+2)", "Contribution"],
  [...BROW.map(([k, lab]) => [lab.replace(/ \([a-f]\)$/, ""), k === "S" ? f3(PW.inputs[k]) : f2(PW.inputs[k]), k === "Q" ? f4(PW.coefs[k] * K25) : f3(PW.coefs[k] * K25), money(PW.parts[k])]),
   ["xNPV, adopted model", "", "", `**${money(PW.value)}**`], ["xNPV on draft position alone", "", "", money(PW.slot)],
   ["xNPV with his draft left out of the regression", "", "", money(PW.own_out)]],
  [3500, 1800, 2000, 2340], [1, 2, 3]));
add(CAPTION("Percent of the 2025-26 cap. Contributions are input times coefficient and sum to the adopted xNPV; as a forward, his defenceman input is zero."));
add(P(`His scoring raises his xNPV from ${mil(PW.slot)} on his draft position to ${money(PW.value)}: his production and its square add ${money(PW.parts.P + PW.parts.Q)}, and ${money(-PW.parts.A)} is subtracted for his age. He was among the youngest a D+2 prospect can be; a prospect a year older with his production would be worth ${mil(-PW.coefs.A * PW.prod)} less.`));

// =====================================================================================================================
// 8. GOALTENDERS AND UNDRAFTED PLAYERS (the traded-prospects section cut, Thomas 2026-11-27)
// =====================================================================================================================
add(H1("8. Goaltenders and Undrafted Players"));
add(P("NHLe converts scoring, which does not measure a goaltender. Elite Prospects holds goaltenders' save percentages, but no factor translates a save percentage from one league to another, so a goaltender prospect is valued on draft position alone, with the star values by season."));
add(P("An undrafted player has no draft rights, so a club holds his NHL rights only through an NHL contract; one on a minor-league contract is worth nothing to an NHL club in this currency. An undrafted player on an NHL contract is valued with the same model, his star probability set to zero and his seasons counted from his first draft-eligible year."));
const TR_ = PR.traded;

// =====================================================================================================================
// 10. THE TRADE ON ONE SCALE
// =====================================================================================================================
add(H1("9. The Trade on One Scale"));
const to25 = TRD.to_2025, A_ = TRD.assets, RET = TRD.retained, SD_ = TRD.sides;
add(P("With Suzuki valued, each asset in the Pacioretty trade has a value at the trade date: Pacioretty and Tatar from the player model, the 2019 second-round pick from the pick model, and Suzuki from the prospect model. The rules for retained salary, for a trade during the season, and for a contract signed on the trade date are those set out in Valuing Players."));
add(H2("Adding values at one cap"));
add(P(`A player's value comes out of the player model in his valuation season's dollars, at that season's cap ($${f1(M(CAP18))} million in 2018-19), while picks and prospects come from careers restated at the 2025-26 cap. To add the assets of a trade they have to be in one unit. The options were each trade's own season's dollars, or one unit for every trade. One unit was adopted, the share of the cap. A player's value as a share of his valuation season's cap is the same number as his value restated at the 2025-26 cap, multiplied by ${f1(CAP25M)} / ${f1(M(CAP18))} = ${f3(to25)} for 2018-19, and stated as a share of it. Each trade's own dollars would leave trades from different seasons in different units, so they could not be compared or summed. The unit changes the size of a value but never its sign or its order within a trade.`));
add(H2("The trade"));
add(P(`${T("trade")} gives each asset two values: its value to the club that received it, which carries the cap hit less any retained part, and its value to the club that traded it, before the trade, when that club paid the whole cap hit. The retained part is the difference between them. A club's side adds what it received, with any retained salary it pays, and subtracts what it gave up (${T("sides")}, ${F("trade")}). Read this way, a retained share moves value from the retaining club to the acquirer once, and the two clubs' sides sum to zero.`));
add(TT("trade", "The trade, each asset at the trade date"));
const before_ = (a) => a.value - ((RET[a.asset] && RET[a.asset].pv_2025) || 0);
add(TABLE(["Asset", "Traded by", "Received by", "Valued by", "Value to the receiving club", "Retained part, paid by the trading club", "Value to the trading club before the trade"],
  A_.map((a) => [a.asset, a.to === "MTL" ? "Vegas" : "Montreal", a.to === "MTL" ? "Montreal" : "Vegas", a.kind === "player" ? "Player model" : (a.kind === "pick" ? "Pick model" : "Prospect model"), money(a.value), RET[a.asset] ? money(-RET[a.asset].pv_2025) : "", money(before_(a))]),
  [1900, 1000, 1000, 1500, 1400, 1500, 1340], [4, 5, 6], new Set(), 16));
add(CAPTION("xNPV in percent of the cap. Pacioretty's and Tatar's values are their player-model values as shares of the 2018-19 cap; the pick's and Suzuki's as shares of the 2025-26 cap; the retained part is a cost to the club that kept it."));
add(TT("sides", "Each club's side of the trade"));
const side = (c) => SD_[c];
add(TABLE(["Club", "Received", "Given up", "Net: received less given up"],
  [["Montreal", money(side("MTL").received_M), money(side("MTL").given_M), `**${money(side("MTL").net_M)}**`],
   ["Vegas", money(side("VGK").received_M), money(side("VGK").given_M), `**${money(side("VGK").net_M)}**`]],
  [2600, 2300, 2300, 2440], [1, 2, 3], new Set(), 17));
add(CAPTION("Percent of the cap. Received: the assets each club received, at their value to it, and the retained salary it pays. Given up: the assets it traded, at their value to it before the trade."));
add(FIGURE("trade", "fig_trade.png", "The trade on one scale", "Each club's side of the trade at the trade date, in percent of the cap: what it received, what it gave up, and the difference."));
add(P(`Montreal received Tatar (${mil(A_[1].value)}), Suzuki (${money(A_[2].value)}), and the pick (${money(A_[3].value)}), and kept paying the retained part of Pacioretty's cap hit, ${money(RET["Max Pacioretty"].pv_2025)}: ${money(side("MTL").received_M)} in all. It gave up one season of Pacioretty, worth ${money(side("MTL").given_M)} to it at his full cap hit. Its side is ${money(side("MTL").received_M)} less ${money(side("MTL").given_M)}, ${money(side("MTL").net_M)}, and Vegas's is the reverse, ${money(side("VGK").net_M)}. At the trade date both players carried contracts priced above their forecasted performance, so each club took on a player with a negative xNPV. Montreal took on more of it: Tatar's three seasons and the retained part of Pacioretty's cap hit cost it ${money(-(A_[1].value - RET["Max Pacioretty"].pv_2025))}, compared with the ${money(-side("MTL").given_M)} it shed with Pacioretty's season. Suzuki and the pick, worth ${money(A_[2].value + A_[3].value)} together, more than covered the difference.`));
if (A_.map((a) => a.asset).join("|") !== "Max Pacioretty|Tomas Tatar|Nick Suzuki|2019 second-round pick") throw new Error(`trade assets ${A_.map((a) => a.asset)}`);

// =====================================================================================================================
// 11. LIMITATIONS
// =====================================================================================================================
add(H1("10. Limitations of the Prospect Model"));
add(BULLET(`Estimated on its own outcomes. The model is estimated on the 2007-2017 drafts, whose seasons run past many of the trades valued, and a prospect drafted from 2007 to 2017 is valued from a regression that contains his own outcome, so that prospects and the draft picks traded beside them use the same star values. With each prospect's own draft left out of the regression, the ${TR_.drafted} drafted prospects traded from July 2017 to March 2022 are worth ${mil(TR_.own_out)} in total, compared with ${mil(TR_.tot_drafted)}.`));
add(BULLET("NHLe factors. The factors are one current download of a table that Bacon re-estimates with later seasons, so a factor applied to an earlier season may draw on seasons played after it."));
add(BULLET("Undrafted players. The model is estimated on drafted players, including many whose rights lapsed and who delivered nothing, and it assumes an undrafted player converts scoring as a drafted one does. Undrafted players on NHL contracts are players a club chose to sign, so it probably undervalues them."));
add(BULLET("Goaltenders. A goaltender prospect is valued on draft position alone; a measure built on save percentage is untested."));

// =====================================================================================================================
// APPENDIX
// =====================================================================================================================
add(H1("Appendix A. The Prospect Model Built Up, Each Season"));
const BSP = ["slot", "slot_lin", "slot_linsq", "s3", "adopted"];
const BLAB = ["Draft position alone", "+ production", "+ production squared", "+ age", "Adopted: + defenceman"];
add(P(`${T("buildAll")} builds the prospect model up one term at a time in each season. Within a season each row adds a term to the row above, except the adopted rows for D+4 and from D+5 on, which leave out draft position, and from D+5 on the age discount.`));
const BR = [];
G5.forEach((g) => { BSP.forEach((s, i) => { BR.push([i === 0 ? `**${SEAS[g]}**\n${BLAB[i]}` : BLAB[i], ...BROW.map(([k, , d]) => cc(PC[s][g][k], d, K25)), f3(PD.season_r2[s][g])]); }); });
add(TT("buildAll", "The prospect model built up one term at a time, by season"));
add(TABLE(["Season and model", "S", "P", "P²", "P × (age − 18)", "D × P", "R-squared"], BR, [2140, 1350, 1300, 1300, 1450, 1300, 800], [1, 2, 3, 4, 5, 6], new Set(), 15));
add(CAPTION("Each block is one season, each row one regression with the full set of season interactions and no intercept. S: star probability; P: production level; D: 1 for a defenceman. Coefficient (standard error, clustered by player) [two-sided p-value]; R-squared measured from zero; percent of the 2025-26 cap."));

// ---- every table and figure is referred to in the text before or at it --------------------------------------------
const body = TEXT.join("\n");
for (const k of [...TABS, ...Object.keys(APPX)]) if (!body.includes(`${T(k)}`)) throw new Error(`${T(k)} is never referred to`);
for (const k of FIGS) if (!body.includes(`${F(k)}`)) throw new Error(`${F(k)} is never referred to`);

const doc = new Document({
  creator: "Thomas Mihaljevic", title: "Valuing Prospects",
  styles: { default: { document: { run: { font: FONT, size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 28, bold: true, font: FONT, color: "1F1E1C" }, paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 23, bold: true, font: FONT, color: "2F6DB5" }, paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 1 } }] },
  numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: "bullet", text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1300, bottom: 1300, left: 1300, right: 1300 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "8A8984", font: FONT })] })] }) },
    children: kids }],
});
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUTFILE, buf);
  if (process.env.LINT_OUT) fs.writeFileSync(process.env.LINT_OUT, TEXT.join("\n\n"), "utf8");
  console.log(`${VERSION} wrote ${OUTFILE} (${(buf.length / 1024).toFixed(0)} KB, ${TEXT.join(" ").split(/\s+/).length} words)`);
  // the banned-pattern check (25_TESTS/doc_check.py) on the file just written; each hit to 30_OUTPUT/doc_check/
  const chkDir = path.join(ROOT, "30_OUTPUT", "doc_check");
  fs.mkdirSync(chkDir, { recursive: true });
  const chkOut = path.join(chkDir, path.basename(OUTFILE).replace(/\.docx$/i, ".txt"));
  const chk = require("child_process").spawnSync(process.env.PYTHON || "python",
    [path.join(__dirname, "doc_check.py"), "--quiet", "--out", chkOut, OUTFILE],
    { stdio: "inherit", env: Object.assign({}, process.env, { PYTHONIOENCODING: "utf-8" }) });
  if (chk.error || chk.status !== 0) console.log(`doc_check did not run: ${chk.error ? chk.error.message : "exit " + chk.status}`);
});
