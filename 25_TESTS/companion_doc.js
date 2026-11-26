// companion_doc.js v1.0 -- builds "Figures and Regression Results.docx" (40_DOCS/), the companion read beside the four
// write-up chunks (WORK_QUEUE 0c).
//
// v1.0 (2026-11-27; Thomas: "Build it", on the outline agreed that day: one file for the four chunks; the chunks keep
// their tables and figures, and the companion repeats them under the same numbers, then gives each regression the
// chunks report only in their text with its full output).
//   - Each chunk's tables and figures are the chunk builder's own objects (player_doc.js, pick_doc.js, prospect_doc.js,
//     findings_doc.js, each required as a module: its hook collects every titled table or figure with its caption), so a
//     number in the companion cannot differ from the one in its chunk. GUARD: each chunk gives as many titled blocks as
//     it numbers tables and figures.
//   - The regressions in full (Tables R1 to R6) read OUTPUT_DIR/companion/numbers.json (companion_figures.py v1.0, which
//     guards each against the figure the model uses) and model_doc/numbers.json (the star value on each draft).
//
// Run:  NODE_PATH=<folder with docx> node 25_TESTS/companion_doc.js   (DOC_OUT=<file> to write elsewhere)

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType, HeadingLevel,
  BorderStyle, ShadingType, Footer, PageNumber,
} = require("docx");

const VERSION = "companion_doc.js v1.0";
const ROOT = path.resolve(__dirname, "..");
const C = JSON.parse(fs.readFileSync(path.join(ROOT, "30_OUTPUT", "companion", "numbers.json"), "utf8"));
if (!String(C.script).startsWith("companion_figures.py v1.")) throw new Error(`companion numbers from ${C.script}`);
const MD = JSON.parse(fs.readFileSync(path.join(ROOT, "30_OUTPUT", "model_doc", "numbers.json"), "utf8"));
const OUTFILE = process.env.DOC_OUT || path.join(ROOT, "40_DOCS", "Figures and Regression Results.docx");

// ---- the four chunks, each builder's titled tables and figures ----------------------------------------------------------
const CHUNKS = ["player_doc", "pick_doc", "prospect_doc", "findings_doc"].map((b) => {
  const m = require(path.join(__dirname, `${b}.js`));
  const starts = m.blocks.filter((x) => x.__cap === "start").length;
  if (starts !== m.n) throw new Error(`${b}: ${starts} titled tables and figures collected, ${m.n} numbered`);
  console.log(`  ${m.VERSION}: ${starts} tables and figures`);
  return m;
});

// ---- formatting, as the chunks ---------------------------------------------------------------------------------------------
const FONT = "Calibri";
const TEXT = [];
const fx = (x, d) => Number(x).toFixed(d);
const f2 = (x) => fx(x, 2), f3 = (x) => fx(x, 3);
const comma = (x) => Number(x).toLocaleString("en-US");
const pfmt = (p) => (p < 0.001 ? "<0.001" : f3(p));
const z = (x, d) => (Math.abs(x) < 0.5 * 10 ** -d ? (0).toFixed(d) : Number(x).toFixed(d));
const cc = (t, d = 3, scale = 1) => `${z(t.b * scale, d)} (${fx(t.se * scale, d)})\n[${pfmt(t.p)}]`;
function erf(x) { const s = Math.sign(x); x = Math.abs(x); const t = 1 / (1 + 0.3275911 * x);
  return s * (1 - t * Math.exp(-x * x) * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))))); }
const p2 = (b, se) => 2 * (1 - 0.5 * (1 + erf(Math.abs(b / se) / Math.SQRT2)));
const run = (text, base = {}) => new TextRun({ text, font: FONT, ...base });
const P = (text) => { TEXT.push(text); return new Paragraph({ children: [run(text)], spacing: { before: 60, after: 120, line: 276 } }); };
const H1 = (text) => { TEXT.push(text); return new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, keepNext: true, children: [run(text)] }); };
const H2 = (text) => { TEXT.push(text); return new Paragraph({ heading: HeadingLevel.HEADING_2, keepNext: true, children: [run(text)] }); };
const CAPTION = (text) => { TEXT.push(text); return new Paragraph({ spacing: { before: 40, after: 220 }, children: [run(text, { size: 18, color: "52514E" })] }); };
const TITLE = (text) => { TEXT.push(text); return new Paragraph({ spacing: { before: 180, after: 60 }, keepNext: true, children: [run(text, { size: 20, bold: true })] }); };
const border = { style: BorderStyle.SINGLE, size: 4, color: "C9C8C3" };
const borders = { top: border, bottom: border, left: border, right: border };
function TABLE(header, rows, widths, numeric = [], size = 16) {
  const tot = widths.reduce((a, b) => a + b, 0);
  if (tot > 9660) throw new Error(`table too wide: ${tot}`);
  rows.forEach((r) => { if (r.length !== header.length) throw new Error(`row of ${r.length} cells under ${header.length} headers: ${r[0]}`); });
  const cell = (text, i, head, kp) => new TableCell({
    borders, width: { size: widths[i], type: WidthType.DXA },
    shading: head ? { fill: "EFEEEA", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 40, bottom: 40, left: 70, right: 70 },
    children: String(text).split("\n").map((line) => new Paragraph({ keepNext: kp,
      alignment: numeric.includes(i) ? AlignmentType.RIGHT : AlignmentType.LEFT, children: [run(line, { size, bold: !!head })] })),
  });
  rows.forEach((r) => r.slice(1).forEach((c) => { if (String(c).includes("NaN") || String(c).includes("undefined")) throw new Error(`cell ${c} in ${r[0]}`); }));
  return new Table({ width: { size: tot, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: header.map((t, i) => cell(t, i, true, true)) }),
      ...rows.map((r, j) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, i, false, j < rows.length - 1)) }))] });
}
const CAP25M = MD.heavy.cap["2025"] / 1e6;
const K25 = 100 / CAP25M;                     // $M at the 2025-26 cap -> percent of it

const kids = [];
const add = (...xs) => xs.flat().forEach((x) => kids.push(x));
add(new Paragraph({ spacing: { after: 40 }, children: [run("Figures and Regression Results", { bold: true, size: 40 })] }));
add(P("This document collects the tables and figures of Valuing Players, Valuing Draft Picks, Valuing Prospects, and Findings, each under the number it carries in its own document, so that they can be read beside the text. After each document's tables and figures come the regressions that the document reports only in its text, each with its full output: coefficients, standard errors, p-values, the number of observations, and a measure of fit. These are numbered R1 to R6."));
add(P("Values are in percent of the 2025-26 salary cap of $95.5 million unless a table states otherwise. In the regression tables, each cell gives the coefficient, its standard error in parentheses, and its two-sided p-value in square brackets."));

let R = 0;
const RT = (title) => TITLE(`Table R${++R}. ${title}`);
const section = (i, full = true) => {
  const m = CHUNKS[i];
  add(H1(m.title));
  if (!full) add(P(`Every regression in ${m.title} is shown in full in its own tables.`));
  add(H2("Tables and figures"), m.blocks);
  if (full) add(H2("Regressions in full"));
};

// ---- Valuing Players: the three goaltender regressions ------------------------------------------------------------------
section(0);
const GA = C.g_age;
add(RT("The goaltender age term"));
add(TABLE(["Term", "Coefficient"], [
  ["Intercept", cc(GA.terms.intercept, 3)], [`Age − ${f2(GA.centre)}`, cc(GA.terms.age_c, 3)],
  ["R-squared", f3(GA.r2)], ["Goaltender-seasons", comma(GA.n)], ["Goaltenders", comma(GA.goalies)]], [4200, 2400], [1]));
add(CAPTION(`Least squares on goaltender-seasons of 20 or more games before 2025-26. The dependent variable is the forecast error before the age term: season WAR less the forecast that keeps 35% of the goaltender's 50/30/20 average and takes 65% from the league average of 2.19 WAR. Age is his age on September 15 of the season, centred at ${f2(GA.centre)}. Standard errors clustered by goaltender. The age term adds the intercept and the age coefficient times his centred age to the forecast in each season.`));

const GPL = C.g_play;
const hs = Object.keys(GPL).sort((a, b) => Number(a) - Number(b));
add(RT("The goaltender chance-of-playing regression, by seasons ahead"));
add(TABLE(["Seasons ahead", "Intercept", `Age − ${f2(GA.centre)}`, "Forecasted WAR\nbefore the age term", "Games share,\nmost recent season", "McFadden\npseudo R-squared", "Goaltender-\nseasons"],
  hs.map((h) => { const g = GPL[h]; return [h === "0" ? "+0 (valuation season)" : `+${h}`, cc(g.terms.intercept, 3), cc(g.terms.age_c, 3), cc(g.terms.fc, 3), cc(g.terms.gs, 3), f3(g.pseudo_r2), comma(g.n)]; }),
  [1700, 1300, 1300, 1400, 1400, 1260, 1100], [1, 2, 3, 4, 5, 6]));
// the terms (the intercept aside) with p above 0.05, and in which seasons ahead: stated, never shown in silence
const ns = [["age_c", "age"], ["fc", "forecasted WAR"], ["gs", "games share"]].map(([k, lab]) => [lab, hs.filter((h) => GPL[h].terms[k].p > 0.05)]).filter(([, x]) => x.length);
const nsText = ns.map(([lab, x]) => `${lab} at ${x.length === 1 ? `+${x[0]}` : `+${x[0]} to +${x[x.length - 1]}`}`);
ns.forEach(([lab, x]) => { if (Number(x[x.length - 1]) - Number(x[0]) !== x.length - 1 || x[x.length - 1] !== hs[hs.length - 1]) throw new Error(`${lab}: its seasons ahead with p > 0.05 are not one run to the last: rewrite the caption`); });
add(CAPTION(`Logistic regression for each season ahead, on the log odds that the goaltender plays at least one NHL game in that season. Age is his age in that season, centred at ${f2(GA.centre)}. The rows are every valuation season from 2008-09 whose season ahead was complete before 2025-26. Standard errors clustered by goaltender. Every season ahead keeps the same terms; the intercept aside, the terms not statistically significant at the 5% level are ${nsText.join(" and ")}, the seasons ahead estimated on the fewest goaltender-seasons. Beyond +${hs[hs.length - 1]}, the +${hs[hs.length - 1]} regression is used, with his age moving on.`));

const GL = C.g_line;
add(RT("The goaltender price line"));
add(TABLE(["Term", "Coefficient (percent of the cap)"], [
  ["Intercept", cc(GL.terms.intercept, 3, 100)], ["Forecasted WAR at the signing", cc(GL.terms["per forecast win"], 3, 100)],
  ["Years of term", cc(GL.terms["per year of term"], 3, 100)], ["Spread of the price (σ)", f3(GL.sigma * 100)],
  ["Log-likelihood", GL.loglik_share.toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 })],
  ["Contracts", comma(GL.n)], ["Goaltenders", comma(GL.goalies)]], [4200, 2800], [1]));
add(CAPTION(`Censored (Tobit) regression of cap share on ${comma(GL.n)} standard-level goaltender contracts starting from 2015-16 to 2025-26, ${comma(GL.censored)} of them at the league minimum. The forecast is the goaltender's forecasted WAR dated at the signing, before the age term. Coefficients are shares of the cap, shown in percent. Standard errors clustered by goaltender. σ is the typical distance of a cap hit from the price line; the log-likelihood is in cap-share units.`));

// ---- Valuing Draft Picks: the star value on each draft, and its trend ---------------------------------------------------
section(1);
const PK = MD.picks;
add(RT("The star value estimated on each draft"));
add(TABLE(["Draft", "Star value", "Drafted players"],
  PK.per_draft.map((r) => [String(r.draft), cc({ b: r.star, se: r.se, p: p2(r.star, r.se) }, 2, K25), comma(r.n)]),
  [1600, 2400, 1800], [1, 2]));
add(CAPTION(`Least squares through zero of NPV over club control on the star probability, on each draft's players alone, with heteroskedasticity-robust standard errors. The test that the eleven star values are equal gives χ² = ${fx(PK.equal_test.chi2, 1)} with ${PK.equal_test.df} degrees of freedom (p = ${PK.equal_test.p < 0.01 ? fx(PK.equal_test.p, 4) : f3(PK.equal_test.p)}).`));
const TR = C.trend;
add(RT("The linear trend in the star value across draft years"));
add(TABLE(["Term", "All drafts", "Without 2015 and 2016"], [
  ["Star probability (the star value for the 2012 draft)", cc(TR.all.terms.p_star, 2, K25), cc(TR.without_2015_2016.terms.p_star, 2, K25)],
  ["Star probability × (draft year − 2012)", cc(TR.all.terms.p_trend, 2, K25), cc(TR.without_2015_2016.terms.p_trend, 2, K25)],
  ["Drafted players", comma(TR.all.n), comma(TR.without_2015_2016.n)], ["Drafts", String(TR.all.drafts), String(TR.without_2015_2016.drafts)]],
  [4600, 2200, 2200], [1, 2]));
add(CAPTION("Least squares through zero of NPV over club control on the star probability and its interaction term with the draft year less 2012. The first coefficient is the star value for the 2012 draft and the second its change from one draft to the next. Heteroskedasticity-robust standard errors."));

// ---- Valuing Prospects: every regression is in its tables ------------------------------------------------------------------
section(2, false);

// ---- Findings: Section 2's regression with its standard errors ------------------------------------------------------------
section(3);
const S2 = C.s2_cluster;
add(RT("Realized NPV regressed on trade-day xNPV"));
add(TABLE(["", "Realized NPV, WAR", "Realized NPV, Game Value"], [
  ["Trade-day xNPV", cc(S2.war, 3), cc(S2.gv, 3)],
  ["Standard error, not clustered", f3(S2.war.se_plain), f3(S2.gv.se_plain)],
  ["Club sides", comma(S2.war.n), comma(S2.gv.n)], ["Trades", comma(S2.war.trades), comma(S2.gv.trades)]],
  [3600, 2400, 2400], [1, 2]));
add(CAPTION("Least squares through zero of each club's realized NPV on its trade-day xNPV, for trades from July 1, 2017 to March 28, 2022. The slope is the one in Table 2. Standard errors clustered by trade, because one club's net value in a trade is the other club's loss. A trade among three clubs gives three club sides."));
if (R !== 6) throw new Error(`${R} regression tables, the introduction says six`);

const doc = new Document({
  creator: "Thomas Mihaljevic", title: "Figures and Regression Results",
  styles: { default: { document: { run: { font: FONT, size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 28, bold: true, font: FONT, color: "1F1E1C" }, paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 23, bold: true, font: FONT, color: "2F6DB5" }, paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 1 } }] },
  sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1300, bottom: 1300, left: 1300, right: 1300 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "8A8984", font: FONT })] })] }) },
    children: kids }],
});
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUTFILE, buf);
  console.log(`${VERSION} wrote ${OUTFILE} (${(buf.length / 1024).toFixed(0)} KB)`);
  const chkDir = path.join(ROOT, "30_OUTPUT", "doc_check");
  fs.mkdirSync(chkDir, { recursive: true });
  const chkOut = path.join(chkDir, path.basename(OUTFILE).replace(/\.docx$/i, ".txt"));
  const chk = require("child_process").spawnSync(process.env.PYTHON || "python",
    [path.join(__dirname, "doc_check.py"), "--quiet", "--out", chkOut, OUTFILE],
    { stdio: "inherit", env: Object.assign({}, process.env, { PYTHONIOENCODING: "utf-8" }) });
  if (chk.error || chk.status !== 0) console.log(`doc_check did not run: ${chk.error ? chk.error.message : "exit " + chk.status}`);
});
