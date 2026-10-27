// prospect_model_doc.js v4.3 -- builds "Valuing Prospects.docx" (40_DOCS/Supervisor_Drafts/).
//
// v4.3 (2026-10-27, session 2026-10-27; Thomas: "Apply cuts 1 to 19 and the 2,316 fix"): the before-age coefficient table
// cut (it is column (3) of the build-up tables); no adjusted R-squared columns; Table 3's candidate (5) cut and the
// candidates renumbered; Table 7 without the undrafted column; Table 8 without the Drafts row; the #10 example, the top-ten
// counts, the D+4 coefficients, the no-record detail, the significance list under Table 8, restatements and a date
// line cut; "Production squared alone" and the own-outcome note folded into their neighbours; the six left out of
// 2,322 said in one clause.
// v4.2 (2026-10-27, session 2026-10-27): Thomas's Word edits of v4.1 (his copy of 13:52, commit 43b4ecb) carried in: the
// deceased-draftee paragraph cut; "therefore", "busts", "Done as in the player model"; the production paragraph's
// weighting, counts and medians cut; the age paragraphs shortened; why linear production stays as one paragraph, its
// table cut; appendix titles shortened. His two comments: the same percentage decline tested (delta-method Wald, numbers
// v4.1); "his draft" made "the season he was drafted (D0)".
// v4.1 (2026-10-27, session 2026-10-27): shorter (Thomas: "overall it's gotten too big"): the pooled-terms section and
// the table of discounted-points forms cut (two sentences remain), the Defencemen section trimmed, sentences that only
// restate totals cut. Thomas's four Word edits of v4.0 (his copy of 13:06) carried in: the remaining-NPV formula and its
// paragraph cut; the fit-measures paragraph cut; his definitions paragraph for S, I and theta; the pick curve's
// defenceman paragraph cut. Held-out error is now defined in Table 2's caption.
// v4.0 (2026-10-27, session 2026-10-27): on prospect_values.py v1.13 (defenceman x production in every season, Thomas
// 2026-10-24) and numbers.json v4.0. The supervisor meeting of 2026-10-23's document items: R-squared, statistical
// significance (Wald tests of the added terms) and economic significance (dollars on the traded prospects and a worked
// prospect) as the fit measures, held-out error a supplementary column; each regression's equation in full each time a
// term is added (Word equations); the defenceman test in the meeting's words, now a section of its own (Section 4) with
// the pick curve's position test reported as tested; the age-form and pooled-terms tests reported. Thomas's 2026-10-22
// rule: xNPV for a value, NPV for a played career, remaining NPV for a prospect's outcome, net value for a season; no
// "surplus". Thomas's Word edits of v3.0 (his copy of 2026-10-22, commit acc5d67) carried in: the table of deceased
// draftees and its caption cut (the paragraph's pointer to it too), Figure 1's caption without "without the six in Table
// 1", every script citation cut, the age coefficient named d, the top-ten table cut. Tables and figures are numbered
// from one list each, so each reference follows the table it names (v3.0's appendix captions pointed at old numbers).
// v3.0 (2026-10-22): on the model after 2026-10-21. v2.x (2026-10-15 to 2026-10-21): Thomas's five rounds of notes
// (40_DOCS/Valuing_Prospects_Feedback.md). Earlier versions are in git.
//
// NUMBERS: every computed figure comes from OUTPUT_DIR/prospect_doc/numbers.json (prospect_doc_figures.py v4.0).
// Recorded figures copied from the records, each with its source:
//   post-season trades on the next page: 23 prospects, -$3.51M          25_TESTS/next_page_moves.py (session 2026-10-14)
//   the no-record indicator's test (p by season, joint p, held-out)      prospect_term_check.py v1.0 (2026-10-21)
//   NHLe method                                                         hockeystats.com/draft/guide (read 2026-10-15)
//
// Run:  NODE_PATH=<folder with docx> node 25_TESTS/prospect_model_doc.js   (LINT_OUT=<file.md> writes the prose)

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType, HeadingLevel,
  BorderStyle, ShadingType, Footer, PageNumber, Math: OMath, MathRun, MathSuperScript, MathSubScript, MathFraction,
  MathSum, MathRoundBrackets,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const FIG = path.join(ROOT, "30_OUTPUT", "prospect_doc");
const N = JSON.parse(fs.readFileSync(path.join(FIG, "numbers.json"), "utf8"));
if (!N.script.startsWith("prospect_doc_figures.py v4.")) throw new Error(`numbers.json is from ${N.script}`);
const OUTFILE = process.env.DOC_OUT || path.join(ROOT, "40_DOCS", "Supervisor_Drafts", "Valuing Prospects.docx");
const TEXT = [];

// ---- formatting helpers ---------------------------------------------------------------------------------
const FONT = "Calibri";
const f1 = (x) => Number(x).toFixed(1);
const f2 = (x) => Number(x).toFixed(2);
const f3 = (x) => Number(x).toFixed(3);
const f4 = (x) => Number(x).toFixed(4);
const comma = (x) => Number(x).toLocaleString("en-US");
const money = (x) => (x < 0 ? `-$${f2(-x)}M` : `$${f2(x)}M`);
const mil = (x) => (x < 0 ? `-$${f2(-x)} million` : `$${f2(x)} million`);
const pfmt = (p) => (p === null || p === undefined || Number.isNaN(p) ? "–" : (p < 0.001 ? "<0.001" : f3(p)));
const pt = (p) => (p < 0.0005 ? "<0.001" : (p < 0.01 ? f4(p) : f3(p)));          // a test's p in a table
const pq = (p) => (p < 0.0005 ? "p < 0.001" : `p = ${p < 0.01 ? f4(p) : f3(p)}`);   // a p-value in prose
const z3 = (x, d = 3) => (Math.abs(x) < 0.5 * 10 ** -d ? (0).toFixed(d) : Number(x).toFixed(d));
const coefCell = (t, d = 3) => (t ? `${z3(t.b, d)} (${Number(t.se).toFixed(d)}) [${pfmt(t.p)}]` : "-");
const sig = (p) => p < 0.05;
const listAnd = (xs) => (xs.length < 3 ? xs.join(" and ") : `${xs.slice(0, -1).join(", ")}, and ${xs[xs.length - 1]}`);
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const longDate = (s) => { const [y, m, d] = s.split("-").map(Number); return `${MONTHS[m - 1]} ${d}, ${y}`; };

function runs(text, base = {}) {
  const out = [];
  // **bold**, *italic* (never opened inside a word), _{sub}, ^{super}
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
const TITLE = (text) => { TEXT.push(text); return new Paragraph({ spacing: { before: 180, after: 60 }, keepNext: true, children: runs(text, { size: 20, bold: true }) }); };
const BULLET = (text) => { TEXT.push(`- ${text}`); return new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: runs(text), spacing: { before: 20, after: 60, line: 276 } }); };

// Word equations (as model_doc.js v4.2): a piece is a string, or ["_", base, sub], ["^", base, super], ["/", [num],
// [den]] (a stacked fraction), ["sum", index, [body]] (a sum over the index), or ["()", [inside]]
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
const SQ = (b) => ["^", b, "2"];

// tables and figures numbered from one list each, so a reference written before its table is right
const TABS = ["star", "fade", "prod", "settings", "age", "def", "adopted", "build2", "suzuki", "versions"];
const APPX = { b0: "B1", b2: "B2", b3: "B3", b4: "B4", ageforms: "B5" };
const FIGS = ["arrival", "fade", "nhle", "production", "age", "traded"];
const tn = (k) => { if (APPX[k]) return APPX[k]; const i = TABS.indexOf(k); if (i < 0) throw new Error(`table ${k}`); return String(i + 1); };
const T = (k) => `Table ${tn(k)}`;
const F = (k) => { const i = FIGS.indexOf(k); if (i < 0) throw new Error(`figure ${k}`); return `Figure ${i + 1}`; };
const TT = (k, title) => TITLE(`${T(k)}. ${title}`);

function FIGURE(key, file, title, caption, width = 540) {
  const b = fs.readFileSync(path.join(FIG, file));
  const w = b.readUInt32BE(16), h = b.readUInt32BE(20);
  return [TITLE(`${F(key)}. ${title}`), new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true,
    children: [new ImageRun({ type: "png", data: b, transformation: { width, height: Math.round(width * h / w) } })] }), CAPTION(caption)];
}
const border = { style: BorderStyle.SINGLE, size: 4, color: "C9C8C3" };
const borders = { top: border, bottom: border, left: border, right: border };
// bold: a set of "row,col" keys to bold (the best number in a column)
function TABLE(header, rows, widths, numeric = [], bold = new Set(), shade = []) {
  const cell = (text, i, j, head, keep) => new TableCell({
    borders, width: { size: widths[i], type: WidthType.DXA },
    shading: head ? { fill: "EFEEEA", type: ShadingType.CLEAR, color: "auto" } : (shade.includes(j) ? { fill: "F4F1E6", type: ShadingType.CLEAR, color: "auto" } : undefined),
    margins: { top: 40, bottom: 40, left: 80, right: 80 },
    children: [new Paragraph({ keepNext: keep, alignment: numeric.includes(i) ? AlignmentType.RIGHT : AlignmentType.LEFT,
      children: runs(String(text), { size: 17, bold: !!head || bold.has(`${j},${i}`) }) })],
  });
  if (rows.some((r) => r.length !== header.length)) throw new Error(`a row of "${header[0]}" has the wrong number of cells`);
  return new Table({ width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: header.map((t, i) => cell(t, i, -1, true, true)) }),
      ...rows.map((r, j) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, i, j, false, j < rows.length - 1)) }))] });
}
// the best number in each listed column (highest, or lowest when low[c]), as bold keys; every tie at the precision shown
function bestKeys(values, cols, dp = {}, low = {}) {
  const keys = new Set();
  cols.forEach((c) => {
    const d = dp[c] === undefined ? 4 : dp[c];
    const shown = values.map((r) => (r[c] === null || r[c] === undefined ? null : Number(Number(r[c]).toFixed(d))));
    const ok = shown.filter((x) => x !== null);
    if (!ok.length) return;
    const best = low[c] ? Math.min(...ok) : Math.max(...ok);
    shown.forEach((x, j) => { if (x === best) keys.add(`${j},${c}`); });
  });
  return keys;
}

// ---- numbers ---------------------------------------------------------------------------------------------
const S1 = N.step1, PS = N.p_star, TR = N.traded, W = N.worked, FS = N.fade_scores, FR = N.fade_r2, TS = N.tests;
const M = N.models, MT = N.model_traded, C = N.coefs, E = N.econ;
const k = (g) => S1.find((r) => r.k === g);
const ARR = N.arrival;
const cum = (grp, upto) => { let s = 0; for (let i = 1; i <= upto; i++) s += ARR[grp].share_all[`D+${i}`] || 0; return 100 * s; };
const G = ["0", "1", "2", "3", "4+"];
const SEAS = { "0": "D+1", "1": "D+2", "2": "D+3", "3": "D+4", "4+": "D+5 and later" };
const maxP = (name, col, gs) => Math.max(...gs.map((g) => C[name][g][col].p));
const drafted = (nm) => MT[nm].drafted;
const kids = [];
const add = (...xs) => xs.flat().forEach((x) => kids.push(x));
// a model row for a comparison table: coefficients, R-squared, adjusted, test, traded drafted, held-out
const mrow = (label, nm, test) => [label, comma(M[nm].n_coef), f4(M[nm].r2), test, f2(drafted(nm)), f4(M[nm].rmse)];
const MHEAD = ["Model", "Coefficients", "R-squared", "Test of the added terms (p)", `${TR.drafted} traded drafted prospects ($M)`, "Held-out error ($M)"];
const MW = [3800, 1050, 1000, 1900, 1400, 1100];
const mbold = (names) => bestKeys(names.map((nm) => [null, null, M[nm].r2]), [2]);

add(new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: "Valuing Prospects", bold: true, size: 40, font: FONT })] }));

// ---- opening ----------------------------------------------------------------------------------------------
add(P("A prospect is a player the player model does not yet value. For a skater, that is a player with no NHL season of 10 or more games in the three seasons before the valuation date. For a goaltender, it is a player with no NHL game in the six seasons before it. The goaltender forecast uses any NHL season in the three before and looks back three more when the most recent is missing."));
add(P("A prospect is valued in the same currency as a draft pick and a contract: the expected net present value (xNPV) of his remaining NHL seasons until his club's control ends. Control ends when he becomes an unrestricted free agent under the collective agreement, at 27 or after seven seasons on an NHL roster. Each season counts the market price of the wins he delivers, less what the club pays to keep him. That cost is the entry-level salary, then the qualifying offer, or the arbitration price once he is eligible. A season outside the NHL counts as zero."));
add(P(`The prospect model is fitted on ${comma(k("0").players)} of the ${comma(k("0").players + 6)} players drafted from 2007 to 2017; the other six died before reaching the NHL. Seasons are named from the draft: D0 is the draft season, which ends with the draft, and D+1 is the season after it, and so on. The outcome is each player's remaining NPV, measured in each season from D+1 on in which he was still a prospect and his club still controlled him. A prospect traded between the draft and the start of D+1 is valued as in D+1.`));

// ---- 1. draft position -------------------------------------------------------------------------------------------
add(H1("1. Draft Position and How Its Value Fades"));
add(P("At the draft, a pick is worth its draft position's star probability times the star value. A prospect starts with his pick's value. The question is how that value changes while he remains unproven."));
const A10 = ARR["picks 1-10"], A37 = ARR["rounds 3-7"], AALL = ARR["all drafted players"];
add(P(`The answer depends on when drafted players reach the NHL. Of the ${comma(AALL.n)} drafted players, ${comma(AALL.n_arrived)} (${f1(100 * AALL.n_arrived / AALL.n)}%) played an NHL season of 10 or more games (a goaltender, an NHL game) before their club's control ended; the other ${comma(AALL.n - AALL.n_arrived)} never did. How many arrive, and when, depends on where they were drafted (${F("arrival")}). Of the ${A10.n} top-ten picks, ${f1(cum("picks 1-10", 1))}% had reached the NHL by D+1, ${f1(cum("picks 1-10", 2))}% by D+2 and ${f1(cum("picks 1-10", 3))}% by D+3, and ${A10.n_arrived} reached it in the end. Of the ${comma(A37.n)} picks from rounds 3 to 7, ${f1(cum("rounds 3-7", 3))}% had reached it by D+3 and ${f1(cum("rounds 3-7", 4))}% by D+4, and only ${f1(100 * A37.n_arrived / A37.n)}% ever did. A top pick who is still a prospect in D+4 is therefore unusual, and later picks who reach the NHL at all reach it later.`));
add(FIGURE("arrival", "fig_arrival.png", "When drafted players reach the NHL",
  "Drafted players of 2007 to 2017. Each line is the share of a draft group's players who had reached the NHL by each season; the rest of the group, the gap above the line at D+9, never did. Reaching the NHL means a first NHL season of 10 or more games (for a goaltender, a first NHL game), the point at which the player model takes him; only seasons within club control are seen. Every draft is observed through at least D+9."));
add(P("To measure how the value of draft position changes, I regressed each prospect's remaining NPV on the star probability for his draft position, interacted with an indicator for each season from D+1 to D+4 and one for D+5 onwards, using every season in which a drafted player was still a prospect and still under his club's control. The coefficient for each season is that season's star value, which is what a prospect still unproven in that season would be worth if he were certain to become a star. As in the draft pick curve, the regression has no intercept, so a draft position with no star probability is worth zero:"));
add(EQ([SUB("remaining NPV", "it"), " = ", ["sum", "n", [SUB("θ", "n"), SUB("I", "nt"), SUB("S", "i")]], " + ", SUB("ε", "it")]));
add(P("In this equation, S_{i} is the star probability for player i’s draft position, which is the chance that a player taken there becomes a star. It comes from Patrick Bacon’s draft model, the same source as the draft pick curve. I_{nt} is a set of five dummy variables, one for each season group: D+1, D+2, D+3, D+4, and D+5 or later. Each dummy equals 1 when the prospect-season falls in its group and 0 otherwise. Interacting it with S_{i} gives the star probability a separate coefficient θ_{n} in each group, so θ_{n} is the star value for that group."));
add(TT("star", "The star value for a player still a prospect, by season"));
add(TABLE(["Season", "Prospects", "Star value (s.e.)", "p-value", "R-squared", "#1 pick", "#10 pick", "#32 pick", "Top-10 picks still prospects"],
  S1.map((r) => [r.k === "0" ? "D+1 (from the draft)" : SEAS[r.k], r.k === "4+" ? `${comma(r.players)} (${comma(r.rows)} prospect-seasons)` : comma(r.players),
    `${money(r.star)} (${f2(r.se)})`, pfmt(r.p), f3(N.star_r2_by_k[r.k]), money(r.pick1), money(r.pick10), money(r.pick32), comma(r.top10)]),
  [1450, 1450, 1250, 750, 850, 850, 850, 850, 1000], [1, 2, 3, 4, 5, 6, 7, 8]));
add(CAPTION(`Drafted players 2007-2017 still prospects in each season (D+1 is the season after the draft). Star value in millions of dollars at the 2025-26 cap; standard errors clustered by player, since one player appears in several seasons; two-sided p-values. R-squared within each season, measured from zero. The pick columns multiply the star value by Bacon's star probability (${f1(100 * PS["1"])}%, ${f1(100 * PS["10"])}% and ${f1(100 * PS["32"])}%).`));
add(P(`A prospect keeps most of his draft position's value through D+3 (${mil(k("1").star)} in D+2 and ${mil(k("2").star)} in D+3) and loses most of it over the next two seasons (${mil(k("3").star)} in D+4 and ${mil(k("4+").star)} from D+5 on). Each estimate is statistically significant at the ${Math.max(...S1.map((r) => r.p)) < 0.01 ? "1%" : "5%"} level. The value falls sharply after D+3 because of who is left. By D+4, nearly every top pick who will reach the NHL has done so, therefore the prospects still unproven are mostly later picks and the top picks who were busts. Among the prospects left, draft position no longer separates the players who will succeed from those who will not.`));

add(H2("A separate star value for each season"));
add(P(`The adopted regression gives each season its own star value from D+1 to D+4, and one shared value from D+5 on, where few prospects remain and little value is left. Three simpler alternatives were tested and rejected. Each restricts how the star value may change from one season to the next, and each was fitted on the same ${comma(N.fade_rows)} prospect-seasons (${F("fade")}, ${T("fade")}):`));
add(BULLET(`One value for every season, the draft-day value kept for as long as a player remains a prospect (fitted: ${mil(N.fade_curve["no fade"][0])}).`));
add(BULLET(`A straight-line decline: the star value equals a starting value plus a fixed change for each season since the draft. Fitted: ${mil(N.fade_curve["straight line"][0])} in D+1, falling ${mil(N.fade_curve["straight line"][0] - N.fade_curve["straight line"][1])} a season.`));
add(BULLET(`The same percentage decline each season: the value keeps a fixed share of itself each season. Fitted: ${mil(N.fade_curve["same percentage"][0])} in D+1, keeping ${f1(100 * N.fade_curve["same percentage"][1] / N.fade_curve["same percentage"][0])}% each season.`));
add(FIGURE("fade", "fig_star_value.png", "The star value by season, and three rejected alternatives",
  `Orange: each rejected alternative, fitted on the same prospect-seasons. Blue: the adopted star values (${T("star")}) with 95% intervals; from D+5 on, one shared value drawn as a line with its interval as a band. Millions of dollars at the 2025-26 cap.`));
const fadeRows = [["A separate value for each season (adopted: a full set of interaction terms)", "separate", "-"],
  ["One value for every season", "no fade", pt(N.fade_wald_one.p)],
  ["Straight-line decline (one interaction term)", "straight line", `${f3(N.fade_wald_steps.p)} (equal drops, D+1 to D+4)`],
  ["Same percentage decline each season", "same percentage", `${f3(N.fade_wald_ratio.p)} (equal shares, D+1 to D+4)`]];
add(TT("fade", "Each alternative for the star value against the adopted one"));
add(TABLE(["Alternative", "Coefficients", "R-squared", "Test against the adopted model (p)", "Star value, D+5 ($M)", `${TR.drafted} traded prospects, draft position alone ($M)`, "Values below zero", "Held-out error ($M)"],
  fadeRows.map(([lab, r, t]) => [lab, comma(FR[r].params), f4(FR[r].r2), t, f2(N.fade_curve[r][4]), f2(FS[r].total), comma(FS[r].below_zero), f4(FS[r].rmse)]),
  [2800, 950, 950, 1650, 950, 1350, 900, 950], [1, 2, 4, 5, 6, 7],
  bestKeys(fadeRows.map(([, r]) => [null, null, FR[r].r2]), [2])));
add(CAPTION(`R-squared measured from zero over the ${comma(N.fade_rows)} prospect-seasons; the highest is in bold. The test against the adopted model is a Wald test in the adopted regression, standard errors clustered by player: for one value for every season, that the five star values are equal; for the straight line, that the star value falls by the same amount from D+1 to D+2, D+2 to D+3, and D+3 to D+4; for the same percentage decline, that it keeps the same share of itself over those three steps (a non-linear restriction, tested by the delta method). Held-out error: each of the 11 drafts is predicted from a fit on the other ten, and the error is the root mean squared error in millions of dollars of remaining NPV per prospect-season; lower is better.`));
add(P(`One value for every season is rejected: the star values are not equal across seasons (Wald ${pq(N.fade_wald_one.p)}). Neither the straight-line decline (p = ${f3(N.fade_wald_steps.p)}) nor the same percentage decline (p = ${f3(N.fade_wald_ratio.p)}) is rejected at the 5% level. I chose a separate value for each season for two reasons. First, it imposes no shape on the decline, and the estimates hold through D+3 and then fall, which matches when top picks reach the NHL (${F("arrival")}). Second, the straight-line decline keeps falling past zero: from D+8 it values a top pick below a late pick, which makes no logical sense, and it values ${FS["straight line"].below_zero} of the ${TR.drafted} traded prospects below zero. A prospect drafted from 2007 to 2017 is valued from a fit that contains his own outcome, so that prospects and the draft picks traded beside them use the same star value.`));

// ---- 2. production ------------------------------------------------------------------------------------------
add(H1("2. Production Adjusted to NHL Terms"));
add(P("Draft position is one element of what predicts a prospect's value. A prospect's own scoring helps as well, because a player who scores at a high rate in junior, college, or a European league is more likely to reach the NHL and more likely to contribute when he does. Done as in the player model, a prospect's production level is a weighted average of his three previous seasons. For example, a prospect valued in D+1 is measured on his draft season (D0) and the two before it (D-1 and D-2), which is the scoring scouts saw before the draft."));
const LG = (lg) => N.leagues.find((r) => r.league === lg);
add(P(`Scoring in different leagues is put on one scale with Patrick Bacon's NHL equivalency (NHLe) factors. A league's factor is the number of NHL points that one point in that league and season is worth. Bacon estimates each factor from players who played full seasons in two leagues in consecutive years, adjusted for a year of development, and re-estimates the factors on a rolling four-season window, so a league's factor changes over time (hockeystats.com/draft/guide). ${F("nhle")} shows the ten leagues that the 2007-2017 draftees played in most in their draft season, which together hold ${f1(100 * N.leagues_share_top10)}% of those draft seasons. For example, an OHL point was worth ${f3(LG("ohl").nhle_2006)} NHL points in 2006-07 and ${f3(LG("ohl").nhle_2025)} in 2025-26.`));
add(FIGURE("nhle", "fig_nhle.png", "NHLe factors over time for the leagues most draftees came from",
  "Bacon's NHLe factor for each league and season (NHL points per point scored in the league). Leagues are the ten in which the most 2007-2017 draftees played their draft season, by games played; the count of draftees is in the legend. The OHL is drawn thicker. Linear axis."));
const NR = N.prod_rows.no_record_by_k;
const nrMid = NR["1"] + NR["2"] + NR["3"];
add(P(`A season's production is the player's points, sourced from Elite Prospects, times his league-season's NHLe factor, per 82 games, counted for seasons of 10 or more games. A prospect with no eligible season (${f1(100 * N.prod_rows.no_record_share)}% of prospect-seasons) has a production level of zero, so he is valued on his draft position alone where it is in the model. Goaltenders stay on draft position alone (${T("settings")}), so the models from here on are fitted on the ${comma(N.prod_rows.rows)} prospect-seasons of ${comma(N.prod_rows.players)} drafted skaters.`));
const prodRows = [
  ["(1) Draft position alone", "slot", "-"],
  ["(2) Linear production alone", "lin_alone", "-"],
  ["(3) Draft position + linear production", "slot_lin", `vs (1): ${pt(TS.lin_vs_slot.p)}`],
  ["(4) Draft position + linear and squared production", "slot_linsq", `vs (3): ${pt(TS.sq_given_lin.p)}`],
  ["(5) As (4), draft position in D+1 to D+3 only", "s2", `vs (4), without draft position in D+4 and later: ${pt(TS.slot_late.p)}`],
  ["(6) As (5), production squared alone", "s2_sq_alone", `vs (5), without linear production: ${pt(TS.lin_s2.p)}`]];
add(TT("prod", "Production added to draft position: each candidate's fit"));
add(TABLE(MHEAD.map((h, i) => (i === 0 ? "Candidate" : h)), prodRows.map(([lab, nm, t]) => mrow(lab, nm, t)), MW, [1, 2, 4, 5], mbold(prodRows.map((r) => r[1]))));
add(CAPTION(`Each candidate is one regression with the full set of interaction terms (each term its own coefficient in each season, D+1 to D+4 and D+5 and later), fitted on the same ${comma(N.prod_rows.rows)} prospect-seasons of ${comma(N.prod_rows.players)} drafted skaters, 2007-2017, before age (Section 3) and the defenceman term (Section 4). R-squared measured from zero; the highest is in bold. Test of the added terms: Wald test, standard errors clustered by player, that the coefficients named are zero in every season where they appear; for (5) and (6), the test of the terms dropped. Traded drafted prospects: goaltenders on draft position alone, $M at the 2025-26 cap. Held-out error as in ${T("fade")}.`));
add(H2("Production added to draft position"));
add(P(`Linear production alone accounts for less of remaining NPV than draft position alone (R-squared ${f4(M.lin_alone.r2)} against ${f4(M.slot.r2)}), so production does not replace draft position at the draft. Added to draft position, production is statistically significant: linear production with ${pq(TS.lin_vs_slot.p)}, and linear and squared production together with ${pq(TS.prod_vs_slot.p)}.`));
const cu1 = C.slot_linsq["1"], st1 = C.slot_lin["1"];
const qa = cu1.Q.b, qb = cu1.P.b - st1.P.b, qc = (cu1.S.b - st1.S.b) * N.fig_production.p20;
const crossAt = (-qb + Math.sqrt(qb * qb - 4 * qa * qc)) / (2 * qa);
const turn1 = -cu1.P.b / (2 * cu1.Q.b);
add(H2("Production squared"));
add(P(`With linear production, each additional NHLe point adds the same dollars. With the production squared term, each point adds more the higher a prospect already scores. I added it because most of a pick's value comes from the few players who become stars. Draft position already captures part of this: the star probability for the first pick is ${f1(100 * PS["1"])}%, about ${Math.round(PS["1"] / PS["32"])} times the ${f1(100 * PS["32"])}% for the 32nd. But every prospect taken at the same draft position has the same star probability, whatever he scores. Linear production then gives the highest scorers at a draft position, the prospects most likely to become stars, the same dollars per point as every other prospect; with the squared term, their value rises faster.`));
add(P(`The squared term is statistically significant over linear production (${pq(TS.sq_given_lin.p)}) and raises R-squared from ${f4(M.slot_lin.r2)} to ${f4(M.slot_linsq.r2)} (${F("production")}). Production squared alone, without linear production (candidate (6)), is rejected: dropping linear production is statistically significant (${pq(TS.lin_s2.p)}). Once age enters, this test depends on where age is measured from, which Section 4 takes up.`));
add(FIGURE("production", "fig_production.png", "A #20 pick in D+2: xNPV against production, before age",
  `xNPV in millions of dollars at the 2025-26 cap for a #20 pick (star probability ${f1(100 * N.fig_production.p20)}%) in D+2, from candidates (1), (3) and (4) of ${T("prod")}. Production is NHLe points per 82 games, weighted 50/30/20 over the three seasons before the valuation season. Vertical lines mark the 25th, 50th, 75th and 90th percentiles of production among prospects in D+2 (${f1(N.prod_pct_k1["25"])}, ${f1(N.prod_pct_k1["50"])}, ${f1(N.prod_pct_k1["75"])} and ${f1(N.prod_pct_k1["90"])} points).`));
add(P(`Up to ${f1(crossAt)} points (above the 75th percentile), the line with the squared term sits below the linear one, by at most ${mil(N.fig_production.gap_max)}, and it dips slightly before it rises. The dip comes from the negative linear coefficient: in D+2 an extra point adds ${f3(cu1.P.b)} + 2 × ${f4(cu1.Q.b)} × production million dollars, which is positive above ${f1(turn1)} points, below the 25th percentile of ${f1(N.prod_pct_k1["25"])}. The negative coefficient sets where the value bottoms out; it is not evidence that a little scoring lowers a prospect's value.`));
add(H2("Production in place of draft position from D+4"));
add(P(`Once production is in the model, draft position stops carrying information in D+4: its coefficients in D+4 and from D+5 on are together not statistically significant (p = ${f3(TS.slot_late.p)}; column (3) of ${T("build2")} and Appendix B). Once a prospect's production is known, his draft position adds nothing to his value from D+4 on. The adopted model keeps draft position from D+1 to D+3 and uses production alone from D+4, which leaves R-squared at ${f4(M.s2.r2)} against ${f4(M.slot_linsq.r2)} (candidate (5) of ${T("prod")}).`));
add(P("With production, the model values a prospect as follows, where P_{it} is his production level in NHLe points per 82 games in season t and the other symbols are as in Section 1. Each term is multiplied by the indicator for each season (a full set of interaction terms), so the coefficients a_{n}, b_{n} and c_{n} take a separate value in each season: a_{n} is the value of the star probability, and b_{n} and c_{n} together give the value of production. Draft position is out from D+4, so a_{4} = a_{5} = 0."));
add(EQ([SUB("remaining NPV", "it"), " = ", ["sum", "n", [SUB("I", "nt"), ["()", [SUB("a", "n"), SUB("S", "i"), " + ", SUB("b", "n"), SUB("P", "it"), " + ", SUB("c", "n"), ["^", SUB("P", "it"), "2"]]]]], " + ", SUB("ε", "it")]));
add(TT("settings", "The production measure's settings"));
add(TABLE(["Setting", "Adopted", "Alternative", "Why"], [
  ["A counting season", "10 or more games", "Any games", "The same threshold the player model uses for an NHL season; a handful of games gives an unreliable scoring rate."],
  ["Weighting of recent seasons", "50/30/20 over the three seasons before, rescaled over those he has", "Other weights", "The weighting each part of the model uses for recent seasons."],
  ["2012-13 (no NHLe factor; lockout season)", "The mean of the league's 2011-12 and 2013-14 factors", "Leave 2012-13 out", "Keeps a full season of scoring for the 2011-2013 drafts."],
  ["Goaltenders", "Draft position alone", "A save-based measure (not tested)", "NHLe converts scoring, which says nothing about a goaltender. Elite Prospects holds goaltenders' save percentages, but no factor translates a save percentage from one league to another; a save-based measure is untested."],
  ["No production record", "Production level zero: valued on draft position alone where it is in the model", "An indicator for having no record", "Its significance rests on a single prospect-season (the paragraph after this table)"],
], [1900, 2100, 1700, 3600]));
add(P(`Each setting is applied identically to each candidate in ${T("prod")}. An indicator for having no production record was tested and dropped: its statistical significance rests on a single prospect-season in D+3, and no traded prospect's value changed.`));

// ---- 3. age ------------------------------------------------------------------------------------------------
add(H1("3. Age"));
add(P("A player who scores at a given rate at 18 is commonly rated a better prospect than one who scores at the same rate at 20. This section tests whether the data agree. Age is the player's age on September 15 of the valuation season, the date the collective agreement uses. A player is first eligible for the draft in the year he is 18 by September 15, so in D+1 a player drafted at his first opportunity is 18 to 19, and one drafted a year later is 19 to 20."));
add(P(`Within a season's regression each prospect is the same number of seasons from the season he was drafted (D0), so a prospect a year older now also scored his points, and was drafted, a year older; age cannot be confused with time since the draft there. Across all seasons the two move almost one for one (correlation ${f3(N.age_corr.age_vs_k)}), which is why age enters each season with its own coefficient.`));
const ageRows = [
  ["(5) Section 2 model: draft position in D+1 to D+3, linear and squared production", "s2", "-"],
  ["(7) Plus age as a flat amount, D+1 to D+4", "s3_flat", `vs (5): ${pt(TS.flat.p)}`],
  ["(8) Plus age discounting production, D+1 to D+4 (adopted)", "s3", `vs (5): ${pt(TS.disc.p)}`],
  ["(9) Plus both", "s3_both", `vs (8), the flat amount: ${pt(TS.flat_given_disc.p)}`],
  ["(10) As (8), the discount from D+5 on as well", "s3_age_late", `vs (8): ${pt(TS.age_late.p)}`]];
add(TT("age", "Each age candidate added to the Section 2 model (draft position + linear and squared production)"));
add(TABLE(MHEAD.map((h, i) => (i === 0 ? "Candidate" : h)), ageRows.map(([lab, nm, t]) => mrow(lab, nm, t)), MW, [1, 2, 4, 5], mbold(ageRows.map((r) => r[1]))));
add(CAPTION(`As ${T("prod")}, on the same prospect-seasons; candidate (5) is the model of Section 2. Age is his age on September 15 of the valuation season, less 18.`));
add(H2("Age as a discount on production"));
const d2 = C.s3["1"].A.b;
add(P(`Two forms were tested. Age as a flat amount subtracts the same dollars for each year of age, whatever the player scores. Age discounting production makes each point of production worth less the older the player was when he scored it by a fixed amount. In D+2 that amount is $${f3(-d2)} million (${T("ageforms")}), so of two prospects with 10 points, the one who is a year older is worth ${mil(-10 * d2)} less. The flat amount costs a D+2 prospect ${mil(-C.s3_flat["1"].F.b)} a year whatever he scores.`));
add(P(`Each form is statistically significant on its own (${pq(TS.flat.p)} for the flat amount, ${pq(TS.disc.p)} for the discount). With both in the model, the discount stays statistically significant (${pq(TS.disc_given_flat.p)}) and the flat amount does not (p = ${f3(TS.flat_given_disc.p)}), so the discount is adopted. It also better measures what age was included to account for, which is how much a player's scoring says about him given his age.`));
add(P(`From D+5 on, the discount is not statistically significant (p = ${f3(TS.age_late.p)}; candidate (10)), so the adopted model applies it from D+1 to D+4 only, where it is statistically significant in each season (p ≤ ${f3(maxP("s3", "A", ["0", "1", "2", "3"]))}, ${T("ageforms")}).`));
add(FIGURE("age", "fig_age.png", "A #20 pick in D+2: the age discount",
  `xNPV in millions of dollars at the 2025-26 cap under candidate (8) for a #20 pick in D+2 with a production record, at three ages on September 15 of his D+2 season. A player drafted at his first opportunity is 19 to 20 then. Percentile lines as in ${F("production")}.`));
const DF = N.disc_forms;
add(P(`Applying the discount to the points themselves, so that a point scored a year older counts as a fraction of a point, was tested in four forms and rejected. The closest, age-adjusted points, fits slightly better in the sample (R-squared ${f4(DF.adj_disc.r2)} against ${f4(DF.adopted.r2)}), but it is not nested in the adopted model, so neither can be tested against the other, and its held-out error is not lower by a statistically significant amount (p = ${f2(N.disc_p_heldout)}).`));
add(P("With age, the model values a prospect as follows, where A_{it} is his age on September 15 of season t and the other symbols are as in Section 2. The coefficient d_{n} is the age discount in season D+n: the change in the value of each point of production for each year of age. Age enters less 18, so the age term is zero for an 18-year-old. The discount is out from D+5, so d_{5} = 0."));
add(EQ([SUB("remaining NPV", "it"), " = ", ["sum", "n", [SUB("I", "nt"), ["()", [SUB("a", "n"), SUB("S", "i"), " + ", SUB("b", "n"), SUB("P", "it"), " + ", SUB("c", "n"), ["^", SUB("P", "it"), "2"], " + ", SUB("d", "n"), SUB("P", "it"), ["()", [SUB("A", "it"), " - 18"]]]]]], " + ", SUB("ε", "it")]));

// ---- 4. defencemen ----------------------------------------------------------------------------------------
add(H1("4. Defencemen"));
const MP = N.prod_median_pos, DM = N.def_moved;
add(P(`Defencemen score less than forwards: among prospects with a production record in D+2, the median defenceman scores ${f1(MP["1"].D)} NHLe points per 82 games and the median forward ${f1(MP["1"].F)}. To test whether a defenceman's point is worth a different amount, a separate regression was run using a defenceman dummy interacted with production: D_{i} is 1 for a defenceman and 0 for a forward, and D_{i} × P_{it} enters in each season with its own coefficient f_{n}. Of the ${comma(N.prod_rows.players)} drafted skaters in the fit, ${comma(N.prod_rows.defencemen)} are defencemen.`));
const defRows = [
  ["(8) Section 3 model", "s3", "-"],
  ["(11) Plus defenceman × production (adopted)", "adopted", `vs (8): ${pt(TS.def.p)}`],
  ["(12) As (11), plus defenceman × production squared", "adopted_dq", `vs (11): ${pt(TS.dq.p)}`],
  ["(13) As (11), plus defenceman × star probability, D+1 to D+3", "adopted_ds", `vs (11): ${pt(TS.ds.p)}`]];
add(TT("def", "Defenceman terms added to the Section 3 model"));
add(TABLE(MHEAD, defRows.map(([lab, nm, t]) => mrow(lab, nm, t)), MW, [1, 2, 4, 5], mbold(defRows.map((r) => r[1]))));
add(CAPTION(`As ${T("prod")}, on the same prospect-seasons.`));
add(P(`The defenceman term is statistically significant (${pq(TS.def.p)}) and positive in each season. A #20 pick in D+2 who is 19.5 and scores 20 points is worth ${mil(E.fwd_20_k1)} as a forward and ${mil(E.def_20_k1_value)} as a defenceman. Defenceman × production squared (p = ${f3(TS.dq.p)}) and a separate star value for defencemen (p = ${f3(TS.ds.p)}) are not statistically significant given it.`));
const PD = N.pick_def;
add(H2("The adopted model"));
add(P("With the defenceman term, the adopted model values a prospect as follows, where D_{i} is 1 for a defenceman and the other symbols are as in Section 3:"));
add(EQ([SUB("remaining NPV", "it"), " = ", ["sum", "n", [SUB("I", "nt"), ["()", [SUB("a", "n"), SUB("S", "i"), " + ", SUB("b", "n"), SUB("P", "it"), " + ", SUB("c", "n"), ["^", SUB("P", "it"), "2"], " + ", SUB("d", "n"), SUB("P", "it"), ["()", [SUB("A", "it"), " - 18"]], " + ", SUB("f", "n"), SUB("D", "i"), SUB("P", "it")]]]], " + ", SUB("ε", "it")]));
add(P("Draft position is out from D+4 (a_{4} = a_{5} = 0) and the age discount from D+5 (d_{5} = 0)."));
const t9 = [["Star probability for his draft position (a)", "S", 3], ["Production (b)", "P", 3], ["Production squared (c)", "Q", 4],
  ["Production × (age − 18) (d)", "A", 3], ["Defenceman × production (f)", "D", 3]];
const AC_ = N.adopted_counts;
add(TT("adopted", "The adopted model: regression by season"));
add(TABLE(["Term", ...G.map((g) => SEAS[g])], [
  ...t9.map(([lab, c, d]) => [lab, ...G.map((g) => coefCell(C.adopted[g][c], d))]),
  ["Prospect-seasons", ...G.map((g) => comma(AC_[g].rows))], ["Players", ...G.map((g) => comma(AC_[g].players))],
  ["R-squared", ...G.map((g) => f3(N.season_r2.adopted[g]))]],
  [2600, 1350, 1350, 1350, 1350, 1350], [1, 2, 3, 4, 5]));
add(CAPTION(`Dependent variable: remaining NPV in millions of dollars at the 2025-26 cap. Each cell gives the coefficient, its standard error clustered by player in parentheses and its two-sided p-value in brackets. The table is one regression with the full set of interaction terms: each column holds that season's coefficients. Production squared is in squared points (15 points enter as 225); age is on September 15 of the valuation season. R-squared within each season, measured from zero; over all ${comma(N.prod_rows.rows)} prospect-seasons it is ${f4(M.adopted.r2)}. The low R-squared reflects how uneven outcomes are: most prospects deliver no NHL value.`));
const nsD = G.filter((g) => !sig(C.adopted[g].D.p)).map((g) => SEAS[g]);
const sigQ = G.filter((g) => sig(C.adopted[g].Q.p)).map((g) => SEAS[g]);
add(P(`The defenceman term is statistically significant in ${listAnd(G.filter((g) => sig(C.adopted[g].D.p)).map((g) => SEAS[g]))}, not in ${nsD.join(" or ")}; it is kept in each season because the five together are statistically significant (p = ${f3(TS.def.p)}). Linear production is not statistically significant in any season; the next two subsections say why it stays, and why production stays from D+5 on.`));
add(P(`${T("build2")} shows the D+2 regression built up one term at a time, in the order of this document: draft position alone, then production, then its square, then age, then the defenceman term. Each column adds one term to the column before it, on the same prospect-seasons; Appendix B gives the same table for each other season.`));
const BSPEC = ["slot", "slot_lin", "slot_linsq", "s3", "adopted"];
const BT = (g) => TABLE(["Term", "(1) Draft position alone", "(2) + production", "(3) + production squared", "(4) + age", "(5) Adopted: + defenceman"], [
  ...t9.map(([lab, c, d]) => [lab, ...BSPEC.map((s) => coefCell(C[s][g][c], d))]),
  ["Prospect-seasons", ...BSPEC.map(() => comma(AC_[g].rows))], ["R-squared", ...BSPEC.map((s) => f3(N.season_r2[s][g]))]],
  [2400, 1350, 1350, 1350, 1350, 1400], [1, 2, 3, 4, 5]);
add(TT("build2", "The D+2 regression built up one term at a time"));
add(BT("1"));
add(CAPTION(`As ${T("adopted")}. Column (5) is the adopted D+2 regression (${T("adopted")}); columns (1) to (3) are candidates (1), (3) and (4) of ${T("prod")}, and column (4) candidate (8) of ${T("age")}.`));
add(H2("Why linear production stays"));
const LZ = TS.lin_zero;
add(P(`Linear production's coefficient b is not statistically significant at the 5% level in any season (${T("adopted")}). It stays because its p-value is not the test of whether it belongs. With production × (age − 18) in the model, b is the linear value of a point for a prospect who is exactly 18 on September 15, and each year older adds d. Measuring age from another starting age changes b and its p-value but no value, because the change in b offsets the change in the age term. The test that b is zero in every season gives p = ${f3(LZ["18"].p)} with age measured from 18, ${pq(LZ["19"].p)} from 19 and ${pq(LZ["20"].p)} from 20, on the same fitted values. Dropping b would set a point's linear value to zero at whichever starting age is chosen, so the values would depend on a choice the data give no way to make.`));
add(H2("Production from D+5 on"));
const C5 = C.adopted["4+"];
add(P(`From D+5 on, linear production is not statistically significant at the 5% level (p = ${f3(C5.P.p)}), production squared ${sig(C5.Q.p) ? `is, narrowly (p = ${f3(C5.Q.p)})` : `is not (p = ${f3(C5.Q.p)})`}, and the two together are not (p = ${f3(TS.late_prod.p)}). Dropping them would value every prospect from D+5 on at zero, drafted or undrafted. Production was kept for two reasons. Dropping it would set each late prospect's value to exactly zero, which predicts left-out drafts slightly worse, not better. And a late prospect's scoring is the only evidence of his progress: without it, a prospect in D+6 scoring at the top of the AHL and one who has stopped scoring would be valued the same.`));
add(H2("A worked prospect"));
add(P(`Nick Suzuki was traded to the Montreal Canadiens on September 10th, 2018, at the start of his D+2 season, a year after he was drafted 13th overall in 2017 by the Vegas Golden Knights. The star probability for his draft position is ${f1(100 * W.inputs.S)}%, his production level is ${f1(W.prod)} NHLe points per 82 games (above the 90th percentile in D+2, ${f1(N.prod_pct_k1["90"])}), he was ${f1(W.age)} on September 15, 2018, a player drafted at his first opportunity, and he is a forward. ${T("suzuki")} builds his value from the D+2 regression.`));
if (W.name !== "Nick Suzuki" || W.k !== 1) throw new Error(`the worked prospect is now ${W.name}: rewrite the paragraph`);
const parts = [["Star probability for his draft position", "S", (x) => f3(x)], ["Production", "P", (x) => f2(x)], ["Production squared", "Q", (x) => f2(x)],
  ["Production × (age − 18)", "A", (x) => f2(x)], ["Defenceman × production", "D", (x) => f2(x)]];
add(TT("suzuki", "Nick Suzuki's xNPV, term by term"));
add(TABLE(["Term", "His input", "Coefficient (D+2)", "Contribution"], [
  ...parts.map(([lab, c, fm]) => [lab, fm(W.inputs[c]), c === "Q" ? f4(W.coefs[c]) : f3(W.coefs[c]), money(W.parts[c])]),
  ["xNPV, adopted model", "", "", money(W.value)], ["xNPV, Section 3 model (before the defenceman term)", "", "", money(W.s3)],
  ["xNPV, Section 2 model (before age)", "", "", money(W.no_age)],
  ["xNPV on draft position alone (Section 1)", "", "", money(W.slot)], ["xNPV with his draft left out of the fit", "", "", money(W.own_out)]],
  [3600, 1400, 1600, 1500], [1, 2, 3], new Set(), [5]));
add(CAPTION(`Millions of dollars at the 2025-26 cap. Contributions are input times coefficient and sum to the adopted xNPV. His production of ${f2(W.prod)} enters squared as ${f2(W.prod)}² = ${f2(W.inputs.Q)}; his age less 18 is ${f2(W.age - 18)}; as a forward, his defenceman input is zero. The production and squared terms are read together: his ${f2(W.prod)} points add ${money(W.parts.P)} + ${money(W.parts.Q)} = ${money(W.parts.P + W.parts.Q)}.`));
add(P(`His scoring raises his xNPV from ${mil(W.slot)} on his draft position to ${mil(W.value)}. The model without age values him at ${mil(W.no_age)} and the model with age at ${mil(W.s3)}, so age adds ${mil(W.s3 - W.no_age)}: Suzuki is among the youngest a D+2 prospect can be, and each point is discounted by the age at which it was scored. The defenceman term lowers his value by ${mil(W.s3 - W.value)}: once a defenceman's points are valued apart, a forward's point is worth a little less than the average point was.`));

// ---- 5. the traded prospects ----------------------------------------------------------------------------
add(H1("5. The Traded Prospects"));
add(P(`From July 2017 to March 2022, clubs traded ${TR.drafted} drafted prospects (${TR.drafted_players} different players, as some were traded more than once) and ${TR.undrafted} undrafted prospects. The adopted model values them at ${mil(TR.tot_all)}: ${mil(TR.tot_main)} for the drafted prospects and ${mil(TR.tot_undrafted)} for the undrafted. ${T("versions")} values the same ${TR.drafted} drafted prospects under each model built above, so each step's effect can be read in dollars on the same assets.`));
add(TT("versions", `The ${TR.drafted} traded drafted prospects under each model`));
const vers = [["Draft position alone, draft-day value however long ago (no fade)", TR.slot_no_fade], ["Draft position alone, star value by season (Section 1)", TR.tot_slot],
  ["(3) Draft position + linear production, draft position in each season", drafted("slot_lin")], ["(4) Draft position + linear and squared production, draft position in each season", drafted("slot_linsq")],
  ["(5) Linear and squared production, draft position in D+1 to D+3 only (Section 2)", drafted("s2")], 
  ["(8) Plus age discounting production, D+1 to D+4 (Section 3)", drafted("s3")],
  ["(11) Adopted: plus defenceman × production (Section 4)", TR.tot_main], ["Adopted, each prospect's draft left out of the fit", TR.tot_own_out]];
add(TABLE(["Model", "Total xNPV", "vs adopted"], vers.map(([lab, v]) => [lab, money(v), Math.abs(v - TR.tot_main) < 1e-9 ? "-" : money(v - TR.tot_main)]),
  [5600, 1700, 1700], [1, 2], new Set(), [vers.findIndex(([lab]) => lab.includes("Adopted: plus"))]));
add(CAPTION(`Millions of dollars at the 2025-26 cap; ${TR.skaters_priced} skaters priced under each model and ${TR.others_on_slot} goaltenders on draft position alone in each. Each model applies its fit on all drafts 2007-2017 to each prospect at the season of his trade; the numbers in parentheses are the candidates of ${T("prod")}, ${T("age")} and ${T("def")}.`));
add(P(`Production, age and position change many prospects' values. Moving from draft position alone to the adopted model moves ${TR.moved_025} of the ${TR.drafted} values by $0.25 million or more and leaves ${TR.top20_same_slot} of the 20 most valuable prospects in the top 20 (rank correlation ${f3(TR.rank)}).`));
add(P(`A value can be below zero. Of the ${TR.drafted} drafted prospects, ${TR.neg_drafted} are valued below zero, ${mil(TR.neg_drafted_sum)} in total; of all ${TR.drafted + TR.undrafted} prospects valued, ${TR.neg_all} are, the lowest at ${mil(TR.neg_min)}. A value below zero means that prospects with that profile, a low scorer from a late draft position, delivered a slightly negative NPV on average in the data: when such players reach the NHL, their cost tends to exceed the value of the wins they deliver. Negative careers count, as in the draft pick curve.`));
add(FIGURE("traded", "fig_traded.png", "Production raises some prospects well above their draft position's value and lowers others",
  `Each point is one of the ${TR.drafted} traded drafted prospects, valued on draft position alone (horizontal) and on the adopted model (vertical), in millions of dollars at the 2025-26 cap. Points above the dashed line gained value from production, age and position. Colour shows the prospect's season at the trade.`, 440));
add(H2("Undrafted prospects"));
add(P(`An undrafted player has no draft rights, so a club holds his NHL rights only through an NHL contract; an undrafted player on a minor-league contract is worth nothing to an NHL club in this currency. The ${TR.undrafted} undrafted prospects on NHL contracts are valued by the same model with the star probability set to zero, with seasons counted from the first draft at which they were eligible. They total ${mil(TR.tot_undrafted)}; the largest is ${TR.max_undrafted_name} at ${mil(TR.max_undrafted)}.`));
if (TR.undrafted_k_min < 4) throw new Error("an undrafted prospect is valued before D+5: rewrite the paragraph");
add(P("Each was in D+5 or later at his trade, where draft position is not in the model, so setting his star probability to zero changes none of their values. Two limitations remain. First, the model is fitted on drafted players only, including many whose rights lapsed and who delivered nothing, while undrafted prospects on NHL contracts are players a club chose to sign; their values are therefore probably too low. The contract records begin in 2018-19, so the drafted prospects of 2007-2017 under NHL contracts cannot be separated out. Second, with no age term from D+5 on, an undrafted 22-year-old and a 25-year-old with the same scoring receive the same value."));

// ---- appendices ----------------------------------------------------------------------------------------------
add(H1("Appendix A. Decisions Not Covered Above"));
add(TABLE(["Decision", "Adopted", "Alternative", "Why", "Effect"], [
  ["Currency", "Remaining NPV to the end of the club's control", "Entry-level years only", "A club controls a drafted player to 27 or seven roster seasons, long after his entry-level contract; one scale with picks and contracts", "Not measured; the entry-level years alone omit the control years"],
  ["Who is a prospect", "The player model's entry point (no 10+ game season in three; goaltenders no game in six)", "Any NHL game sends him to the player model", "No player is valued twice or by neither model", "The alternative would change the player model's forecast"],
  ["Undrafted prospects", "On NHL contracts only", "All undrafted players", "Only an NHL contract gives a club NHL rights", `${TR.undrafted} assets, ${money(TR.tot_undrafted)}`],
  ["Trades after the regular season", "Valued at the next season", "The season just ended", "The season's games are played and its data complete at the trade", "23 traded prospects move, -$3.51M in total"],
], [1500, 2100, 1600, 2300, 1800]));
add(H1("Appendix B. The Regressions Built Up One Term at a Time"));
for (const [key, g] of [["b0", "0"], ["b2", "2"], ["b3", "3"], ["b4", "4+"]]) {
  add(TT(key, `The ${SEAS[g]} regression`));
  add(BT(g));
  add(CAPTION(g === "3" || g === "4+"
    ? `As ${T("build2")}. In the adopted model draft position is out from D+4${g === "4+" ? ", and age is out from D+5" : ""}, so columns (4) and (5) drop ${g === "4+" ? "both" : "draft position"}.`
    : `As ${T("build2")}.`));
}
const formsB = [["Flat: per year of age", "s3_flat", "F"], ["Discount: production × (age − 18)", "s3", "A"],
  ["Both: per year of age", "s3_both", "F"], ["Both: production × (age − 18)", "s3_both", "A"]];
add(TT("ageforms", "The age terms in each tested form"));
add(TABLE(["Form and term", ...G.slice(0, 4).map((g) => SEAS[g])],
  formsB.map(([lab, nm, c]) => [lab, ...G.slice(0, 4).map((g) => coefCell(C[nm][g][c]))]),
  [3300, 1500, 1500, 1500, 1500], [1, 2, 3, 4]));
add(CAPTION(`Candidates (7), (8) and (9) of ${T("age")}. Coefficients in millions of dollars per year of age (flat) or per NHLe point per year of age (discount), standard errors clustered by player in parentheses and two-sided p-values in brackets; each form is one regression with the full set of interaction terms and the production terms of Section 2. Age is his age on September 15 of the valuation season, less 18.`));

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
  console.log(`wrote ${OUTFILE} (${(buf.length / 1024).toFixed(0)} KB)`);
});
