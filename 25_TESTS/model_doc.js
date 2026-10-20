// model_doc.js v2.0 -- builds "Valuing Players, Draft Picks, and Prospects.docx" (40_DOCS/Supervisor_Drafts/).
//
// v2.0 (2026-10-19): the second draft, at the level of detail of "Valuing Draft Picks" and "Valuing Prospects"
// (Thomas, 2026-10-19: keep in mind their specificity; longer is fine; graphs and tables; for each decision, why it
// had to be made, the choices, why the adopted one and why not the others; explain the statistics, the formulas and
// the terms). Every formula written in full with its discount (CLAUDE.md, 2026-10-19). On today's model: the pick curve
// after the 2026-10-18/19 fixes, the prospect fits inside club control, the back-test's three rules as decided.
// v1.0 (2026-10-16): the first draft, 20 pages.
//
// NUMBERS: every computed figure comes from OUTPUT_DIR/model_doc/numbers.json (25_TESTS/model_doc_figures.py v2.0,
// every guard PASS). Recorded test results are constants in REC below, each with its source in the record.
//
// Run:  NODE_PATH=<folder with docx> node 25_TESTS/model_doc.js   (LINT_OUT=<file.md> writes the prose for the linter)

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType, HeadingLevel,
  BorderStyle, ShadingType, Footer, PageNumber, Math: OMath, MathRun, MathSuperScript, MathSubScript,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const FIG = path.join(ROOT, "30_OUTPUT", "model_doc");
const N = JSON.parse(fs.readFileSync(path.join(FIG, "numbers.json"), "utf8"));
const OUTFILE = process.env.DOC_OUT || path.join(ROOT, "40_DOCS", "Supervisor_Drafts", "Valuing Players, Draft Picks, and Prospects.docx");
const TEXT = [];

// ---- recorded test results (each from the record; date and script given) ---------------------------------------------
const REC = {
  // starting level (25_TESTS/starting_level_simple_test.py v1.1; level_games_weighting_test.py v1.0; development pages 2015-2021)
  startGames: { gw: 1.1506, plain: 1.1526, gwWhole: 1.3598, plainWhole: 1.3618, p1: 0.087, p2: 0.099 },
  startStep: { with: 1.1506, without: 1.1611, wWhole: 1.3598, woWhole: 1.3689 },
  fittedDecay: "47/32/21",
  // investigations A-C (aging_investigations_abc.py v1.0, laptop 2026-10-05; start / one to five seasons ahead / season WAR)
  base: [1.1506, 1.3598, 0.8093],
  A1: [1.1505, 1.3598, 0.8093], A1p: ["0.005", "0.002", "<0.001"],
  B1: [1.1505, 1.3678, 0.8120], B1under22: [1.8119, 1.7384],
  B2start: [1.1203, 1.1271],
  C: [["Replacement level, WAR 0 (adopted)", 1.1506, 1.3598, 0.8093],
      ["0.50 WAR per 82 below replacement", 1.1494, 1.3767, 0.8139],
      ["0.25 below replacement", 1.1499, 1.3670, 0.8113],
      ["0.25 above replacement", 1.1515, 1.3552, 0.8080],
      ["Players who came back later not filled in (adopted)", 1.1507, 1.3588, 0.8089],
      ["A departed season at his own games, not 82 (adopted)", 1.1506, 1.3596, 0.8092],
      ["No departed seasons filled in", 1.1509, 1.3612, 0.8092],
      ["Short next seasons filled in", 1.1505, 1.3671, 0.8123]],
  combined: [1.1506, 1.3587, 0.8088],
  // games share and chance of playing (games_and_playing_de.py v1.0; war_input_uniformity_test.py v1.0; laptop 2026-10-05)
  D: { buildShare: 0.2657, buildWar: 0.8088, logitShare: 0.2636, logitWar: 0.8108, sqShare: 0.2654, sqWar: 0.8078, sqP: [0.088, 0.009] },
  unif: { total: 0.8093, totalTerm: 0.8107, rate: 0.8108, rateTerm: 0.8111, pRate: 0.995, pTerm: 0.011 },
  E: { e1War: [0.8085, 0.8088], e1p: 0.011, e1ll: [0.4047, 0.4044], e2: { n: 884, seasons: 1561, played: 0.916, julyMean: 0.785, julyLL: 0.3309, signMean: 0.877, signLL: 0.2632 }, e3p: 0.87 },
  // the forecast against the earlier projection (revalidation on 2022-2025, 2026-10-05)
  conf: { x1: 0.8932, x0: 0.9724 },
  // the price line: Stage 3 against the forecast (xnpv1_price_line.py docstring); the 2026-10-14 log (start- vs signing-dated)
  spread: { fc: "0.180 + 0.674 × trailing", real: "0.163 + 0.710 × trailing" },
  ll: { startFree: 3958.3, signFree: 3950.7, startIn: 4587.5, signIn: 4591.1 },
  // price-line specification tests (price_line_spec_tests.py v1.0-v1.1, 2026-10-05, on that day's line, 2,296 contracts;
  // held-out root mean squared error of the cap hit, $M at the 2025-26 cap, five-fold player splits repeated 20 times)
  spec: [["The adopted price line", "-", "1.2809", "-"],
         ["A separate line for restricted free agents", "+7.9 (p = 0.0034)", "1.2787", "20 of 20"],
         ["A premium that varies by forecast group", "+18.5 (p < 0.001)", "1.2712", "20 of 20"],
         ["A higher premium below replacement level (one step)", "+16.0 (p < 0.001)", "1.2718", "20 of 20"],
         ["The premium times the forecast", "+5.5 (p = 0.0009)", "1.2755", "20 of 20"],
         ["A squared forecast term", "+4.1 (p = 0.0042)", "1.2809", "12 of 20"],
         ["A bend at one forecast win", "+1.7 (p = 0.064)", "1.2817", "2 of 20"],
         ["A separate line for 2022-23 to 2025-26", "+2.8 (p = 0.24)", "1.2818", "5 of 20"]],
  step: { below: 1.103, above: 0.821, perWinFrom: 1.668, perWinTo: 1.826, pGroup: 0.083 },
  // control seasons (DECISIONS D14(c); rfa_terminal_value docstring; open decision 1; 2026-10-13 adoption)
  d14: { intercept: 18, netRepl: 44, walk0: 21.3, n0: 1231, walk1: 27.0, n1: 2270, leave: 13.1 },
  arb: { pages: 811, total: 7817, median: 0.81, agree: 64.1, nFlag: 1656, later: 541, flag0: 92.4, flag0n: 225, stay: 99.5 },
  // goaltenders (contract_npv docstring)
  goalieKept: [2.084, 2.131], goalieKeptN: 645,
  // circularity: the July test of Game Value as a replacement (Circularity and Game Value.docx; investigation F)
};

// ---- formatting helpers (as v1.0) --------------------------------------------------------------------------------------
const FONT = "Calibri";
const fx = (x, d) => Number(x).toFixed(d);
const f1 = (x) => fx(x, 1), f2 = (x) => fx(x, 2), f3 = (x) => fx(x, 3), f4 = (x) => fx(x, 4);
const comma = (x) => Number(x).toLocaleString("en-US");
const money = (x) => (x < 0 ? `-$${f2(-x)}M` : `$${f2(x)}M`);
const mil = (x) => (x < 0 ? `-$${f2(-x)} million` : `$${f2(x)} million`);
const pfmt = (p) => (p === null || p === undefined || Number.isNaN(p) ? "–" : (p < 0.001 ? "<0.001" : f3(p)));
const pq = (p) => (p < 0.0005 ? "p < 0.001" : `p = ${p < 0.01 ? f4(p) : f3(p)}`);
const pr = (p) => (p < 0.0005 ? "<0.001" : (p < 0.01 ? f4(p) : f3(p)));        // a redraw p in a table
const z = (x, d) => (Math.abs(x) < 0.5 * 10 ** -d ? (0).toFixed(d) : Number(x).toFixed(d));
const pct = (x, d = 1) => `${fx(100 * x, d)}%`;
const cc = (t, d = 3, scale = 1) => (t ? `${z(t.b * scale, d)} (${t.se === null || Math.abs(t.se) < 1e-12 ? "–" : fx(t.se * scale, d)})\n[${t.se === null || Math.abs(t.se) < 1e-12 ? "–" : pfmt(t.p)}]` : "");
function erf(x) { const s = Math.sign(x); x = Math.abs(x); const t = 1 / (1 + 0.3275911 * x);
  return s * (1 - t * Math.exp(-x * x) * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))))); }
const p2 = (b, se) => 2 * (1 - 0.5 * (1 + erf(Math.abs(b / se) / Math.SQRT2)));   // two-sided normal p
const listAnd = (xs) => (xs.length < 3 ? xs.join(" and ") : `${xs.slice(0, -1).join(", ")}, and ${xs[xs.length - 1]}`);

function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), font: FONT, ...base }));
    const t = m[0];
    out.push(new TextRun({ text: t.replace(/\*/g, ""), font: FONT, ...base, bold: t.startsWith("**") || base.bold, italics: !t.startsWith("**") }));
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

function EQ(pieces) {
  const kids = pieces.map((x) => {
    if (!Array.isArray(x)) return new MathRun(x);
    if (x[0] === "^") return new MathSuperScript({ children: [new MathRun(x[1])], superScript: [new MathRun(x[2])] });
    return new MathSubScript({ children: [new MathRun(x[1])], subScript: [new MathRun(x[2])] });
  });
  TEXT.push(pieces.map((x) => (Array.isArray(x) ? `${x[1]}${x[0]}${x[2]}` : x)).join(""));
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 120 }, children: [new OMath({ children: kids })] });
}

// tables and figures numbered from one list each, so a reference written before its table is right
const TABS = ["terms", "stats", "start", "departures", "gs", "pp", "pl", "term", "spec", "control", "pac", "gv", "point",
  "shapes", "nested", "pickvals", "pstar", "fade", "prod", "forms", "age", "ageform", "adopted", "build2", "suzuki", "top10", "trade"];
const APPX = { gsH: "A1", ppH: "A2", buildAll: "B1", pickChoices: "C1", deceased: "C2" };
const FIGS = ["aging", "price", "pickcost", "picks", "pickdrafts", "arrival", "fade", "prospect", "trade"];
const tn = (k) => (APPX[k] ? APPX[k] : String(TABS.indexOf(k) + 1));
const T = (k) => `Table ${tn(k)}`;
const F = (k) => `Figure ${FIGS.indexOf(k) + 1}`;
for (const k of TABS) if (TABS.indexOf(k) < 0) throw new Error(k);
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
// the lowest number in each listed column, compared at the precision shown; each tie is bold
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
const H = N.heavy;
const CAP = H.cap, CAP25 = CAP["2025"], CAP18 = CAP["2018"], CAP25M = CAP25 / 1e6;
const M = (x) => x / 1e6;
const PAC = H.players["Max Pacioretty"], TAT = H.players["Tomas Tatar"];
const PL = H.price_line, PLF = PL.fits, LK = PL.locked;
const GS = H.games_share.by_h, PP = H.participation.by_h;
const CT = H.control, AG = H.aging;
const PK = N.picks, SH = PK.shapes, STAR = SH["star probability (adopted)"].terms.p_star;
const PR = N.prospects, SZ = PR.suzuki, TRD = N.trade, GV = N.gv, GO = N.goalie;
const SEAS = { "0": "D+1", "1": "D+2", "2": "D+3", "3": "D+4", "4+": "D+5 and later" };
const G5 = ["0", "1", "2", "3", "4+"];
const ARR = PR.arrival;
const cumA = (grp, upto) => { let s = 0; for (let i = 1; i <= upto; i++) s += (ARR[grp][`D+${i}`] || { share_of_all: 0 }).share_of_all; return 100 * s; };
const everA = (grp) => 100 * (1 - ARR[grp].never.share_of_all);
const perWin = (b) => b * CAP25M;
const gd = (pos, a) => AG.gdelta[`${pos}|${a}`];
const adoptedGS = GS["0"]["+ trailing WAR (adopted)"], adoptedPP = PP["0"]["+ contract status (adopted)"];
const ppKey = (h) => Object.keys(PP[h]).find((k) => k.includes("adopted"));
const pacS = PAC.seasons, tatS = TAT.seasons;
const sumPV = (s) => s.reduce((a, x) => a + x.pv_dollars, 0) / 1e6;
const bucketW = (b) => CT.qualify_p[b] * (CT.plays_given_q[b] === undefined ? 1 : CT.plays_given_q[b]);
const BUCKETS = [["star", "3 or more"], ["regular", "1 to 3"], ["fringe", "0 to 1"], ["negative", "below 0, or no forecast"]];
const LIN = PK.persistence;
const NL = Object.fromEntries(PR.nhle_look.map((r) => [r.arm, r]));
const AL = Object.fromEntries(PR.age_look.map((r) => [r.arm, r]));
const AF = Object.fromEntries(PR.age_forms.map((r) => [r.key, r]));
const FS = Object.fromEntries(PR.fade.scores.map((r) => [r.rule, r]));
const FC = PR.fade.curves;
const redrawP = (wins) => (2000 - wins) / 2000;       // "beats the base in `wins` of 2,000 redraws" as a one-sided p

const kids = [];
const add = (...xs) => xs.flat().forEach((x) => kids.push(x));
add(new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: "Valuing Players, Draft Picks, and Prospects", bold: true, size: 40, font: FONT })] }));

// =====================================================================================================================
// OPENING
// =====================================================================================================================
add(P("An NHL trade exchanges assets of different kinds: players under contract, draft picks, and prospects who have not yet reached the NHL. To judge whether a club received more than it gave, each asset has to be valued in one currency, as of the trade date. This document explains how each of the three kinds of asset is valued and how the three values are put on one scale. Each step says what it does and why; where a choice had to be made, it says what the options were, which was chosen, and why the others were not."));
add(P("One trade runs through the document. On September 10, 2018, the Montreal Canadiens traded Max Pacioretty to the Vegas Golden Knights for Tomas Tatar, Nick Suzuki, and a 2019 second-round pick. Pacioretty and Tatar were players under contract, Suzuki was a prospect drafted 13th overall in 2017, and the pick was Columbus's, which Vegas held. Each asset is valued in the section for its kind, and Section 8 adds them up."));
add(P("The sections follow the order in which a value is built. Section 1 defines the currency. Sections 2 to 4 value a player under contract: the forecast of his play, the price of a season, and the contract's value with the seasons his club controls after it. Section 5 checks that the measure of play is not circular. Sections 6 and 7 value draft picks and prospects, and Section 8 values the trade. Section 9 lists what the models do not do."));
add(P("Player production throughout is Patrick Bacon's wins above replacement (WAR). One provider is used for each player and each asset, so that every win is measured on one scale; a second provider's wins would differ in level and in what they credit. Contracts and their terms come from PuckPedia, and CapWages for contracts that ended before 2018-19. The trades come from a ledger collected from CapFriendly, scoring outside the NHL from Elite Prospects, the draft from the NHL's draft records, and the star probability for each draft position and the NHL equivalency factors from Bacon's draft and prospect models. Tables 1 and 2 define the terms this document uses."));
add(TT("terms", "Model terms"));
const GLOSS = [
  ["Surplus value", "The market price of the wins an asset delivers to its club, less what the club pays for them, summed over the seasons the club controls it and discounted 3% a year; \"surplus\" for short."],
  ["Cap hit", "A contract's charge against the salary cap in a season: its average annual value."],
  ["WAR", "Bacon's wins above replacement for a season: the wins a player added over a replacement-level player, one a club could sign or call up at the league minimum. WAR per 82 is the same scaled to 82 games."],
  ["Valuation season", "The season in which an asset is valued, starting July 1. A trade during a season is valued in that season; a trade after its last regular-season game, in the next one."],
  ["Valuation date", "The date an asset is valued at: for a traded asset, the trade date."],
  ["Forecast WAR if he plays", "The forecast of a player's WAR per 82 in a season, times his forecast games share."],
  ["Games share", "The share of his team's 82 games a player plays, if he plays at all."],
  ["Chance of playing", "The probability that a player plays at least one NHL game in a season."],
  ["Comparable players", "Players of the same position and age whose style, ice time, level, and trend were closest to his, each weighted by how close."],
  ["Price line", "The regression of cap hit on forecast WAR if he plays, position, and contract length: the market price of a season."],
  ["Term", "A contract's length in years. A season's price uses the term left at the valuation date."],
  ["Control seasons", "The seasons after a contract ends in restricted free agency, until the player can become an unrestricted free agent."],
  ["Qualifying offer", "The one-year offer, set by the collective bargaining agreement (CBA) from the player's prior salary, that keeps a restricted free agent's rights."],
  ["Arbitration price", "Once a player is eligible for salary arbitration, the higher of his qualifying offer and the price line's price of his forecast for that season."],
  ["End of club control", "The June 30 after a drafted player turns 27, or his seventh season of 40 or more NHL games (30 for a goaltender), whichever comes first (CBA Group 3)."],
  ["Draft position", "The overall number of a pick."],
  ["Star probability", "Bacon's probability that a player taken at a draft position becomes a star: career WAR per 82 of at least 1.8 for a forward or 1.23 for a defenceman."],
  ["Star value", "The surplus value of a pick, or a prospect in a given season, certain to become a star."],
  ["Prospect", "A drafted player the player model does not yet value: a skater with no NHL season of 10 or more games in the three before the valuation season, or a goaltender with no NHL game in the six before it."],
  ["D+n", "Seasons named from the draft: D0 is the season that ends with the draft, D+1 the season after it."],
  ["NHLe", "Bacon's NHL equivalency: the NHL points that one point in a given league and season is worth."],
  ["Production level", "A prospect's NHLe points per 82 games, weighted 50/30/20 over his three seasons before the valuation season."],
];
add(TABLE(["Term", "Meaning"], GLOSS, [2300, 7340], [], new Set(), 17, false));
add(CAPTION("Weights written 50/30/20 apply to the three seasons before the valuation season, the most recent first, and are rescaled over the seasons the player has, so a missing season is left out rather than counted as zero (two seasons are weighted 62.5/37.5)."));
add(TT("stats", "Statistical terms"));
const STATS = [
  ["Regression", "A fitted equation: an outcome as the sum of inputs, each multiplied by a coefficient chosen so that the fitted values come as close as possible to the outcomes (least squares: the smallest sum of squared misses)."],
  ["Coefficient", "What one more unit of an input adds to the outcome, the other inputs held fixed."],
  ["Intercept", "The fitted outcome when every input is zero. A regression \"through zero\" has none, so an asset whose inputs are all zero is worth zero."],
  ["Standard error", "How far a coefficient would typically move if the data were drawn again; about 95% of such draws fall within two standard errors."],
  ["Clustered standard errors", "Standard errors that allow the misses of one player, who appears in several rows, to be related, so his rows are not counted as independent evidence."],
  ["p-value", "In this document, a two-sided p-value: the chance of a coefficient at least this far from zero if its true value were zero. Statistically significant at the 5% level means p < 0.05."],
  ["Interaction term", "An input multiplied by an indicator for a group (a season since the draft, say), so the input's coefficient can differ by group."],
  ["Held-out error", "Each draft (or group of contracts) is predicted from a fit that leaves it out; the error is the root mean squared error of those predictions. It measures prediction on data the fit has not seen."],
  ["Root mean squared error", "The square root of the average squared miss: a typical miss, in the outcome's units."],
  ["Redraws, one-sided p", "To ask whether one version predicts better than another, the drafts are redrawn with replacement 2,000 times; the one-sided p is the share of redraws in which the version claimed better is not better. It is one-sided because the question has a direction."],
  ["R-squared", "The share of the outcome's variation the fitted values account for. Without an intercept it is measured from zero, not from the mean."],
  ["Censored (Tobit) regression", "A regression for an outcome with a floor: an outcome at the floor says only that the true value is at or below it (Tobin 1958)."],
  ["Logistic regression", "A regression for a yes-or-no outcome. It fits the log of the odds, log(p / (1 − p)), so every fitted probability lies between 0 and 1."],
];
add(TABLE(["Term", "Meaning"], STATS, [2300, 7340], [], new Set(), 17, false));
add(CAPTION("Each term is used in this sense throughout."));

// =====================================================================================================================
// 1. THE COMMON CURRENCY
// =====================================================================================================================
add(H1("1. The Common Currency"));
add(P("A club holds an asset for the seasons it controls it. In each of those seasons the asset delivers play, which has a market price, and costs the club something: a cap hit, an entry-level salary, or a qualifying offer. The asset's value to the club is what it delivers beyond what it costs. Under a salary cap this is the right measure, because a club that pays a player less than the market would charge for his wins keeps the difference in cap room, and cap room buys wins elsewhere. A player who costs exactly his market price adds nothing a club could not have bought on the open market."));
add(P("Each model writes value the same way: for each season k the club controls, counted from the valuation season (k = 0), the season's value V less its cost C, in that season's dollars, discounted 3% a year:"));
add(EQ(["surplus = Σ (", ["_", "V", "k"], " − ", ["_", "C", "k"], ") / ", ["^", "1.03", "k"]]));
add(P("For a player under contract, V is the market price of his forecast play, weighted by his chance of playing, and C his cap hit (Sections 2 to 4). For a drafted player, V is the market price of the wins he actually delivered and C what his club paid to keep him (Section 6). A prospect's value is the surplus such players went on to deliver from the season he is in (Section 7)."));
add(H2("Cap shares, cap growth, and discounting"));
add(P(`Prices are measured as shares of the salary cap, because the cap sets what a club can spend: a $5 million cap hit was 6.3% of the 2018-19 cap of $${f1(M(CAP18))} million and 5.2% of the 2025-26 cap of $${f1(CAP25M)} million. For a future season the model expects the cap to grow 3% a year from the valuation season's cap, so a season priced at a share s of the cap is worth s × cap × 1.03^k in that season's dollars. Dividing by 1.03^k returns it to s × cap: on the value side, cap growth and discounting cancel. A cap hit is fixed in dollars, so on the cost side only the discount acts. A $5 million cap hit four seasons out counts as $5 million / 1.03^4 = $4.44 million today; it takes a smaller share of a larger cap.`));
add(P(`A drafted player's career has already happened, so each of his seasons is in its own season's dollars, and the model knows the cap that season actually had. It divides each season by the cap's actual growth from 2025-26 instead of by 1.03^k, which states the career at the 2025-26 cap, written cap*:`));
add(EQ(["surplus = Σ (", ["_", "V", "s"], " − ", ["_", "C", "s"], ") × (cap* / ", ["_", "cap", "s"], ")"]));
add(P("This is the same discount, at the cap's actual growth rather than 3%, and again growth and discount cancel on the value side. A season's value and cost are then shares of that season's cap, and the career's surplus is the sum of its seasons' shares, stated in 2025-26 dollars."));
add(H2("Decision: one rate for cap growth and discounting"));
add(P("Future seasons have to be discounted at some rate, and the cap has to be projected at some rate. The options were: one rate for both (adopted, at 3%); a discount rate above cap growth, as a market interest rate would be; no discounting; or a rate that reflects how impatient clubs are."));
add(P("One rate for both was chosen because it makes a share of the cap mean the same thing in any season: a season's worth of play is worth the same share of the cap whenever it comes, and only a fixed-dollar cost becomes cheaper with time. A higher discount rate would make waiting for a prospect costly, and it would need a reason clubs value future cap room less than present cap room, which the model has no evidence for. No discounting would ignore that a fixed cap hit takes a smaller share of a growing cap. A rate for clubs' impatience was rejected for a different reason: whether clubs are impatient is one of the questions the trade study asks, so it cannot be built into the values it tests."));
add(P("The cost of this choice is that 3% is a planning assumption. The cap grew 3.4% a year from 2015-16 to 2019-20, 0.6% a year through 2023-24, and 7.6% a year from 2023-24 to 2026-27. The rate matters most for long contracts at a flat cap hit, where it sets how much cheaper the later seasons become: an eight-year contract at a flat cap hit equal to its first season's value gains $6.16 million at 3%, $9.71 million at 5%, and $13.77 million at 7.6%. The back-test will be run at 3%, 5%, and 7.6% to show whether its findings depend on the rate."));
add(H2("Decision: one cap at which to add values"));
add(P(`A player's value comes out of the player model at the cap of his valuation season (2018-19's $${f1(M(CAP18))} million for the trade in this document), while picks and prospects are stated at the 2025-26 cap. To add the assets on each side of a trade they have to be at one cap. The options were each trade's own valuation season, shares of the cap, or one cap for every trade. Every value is added at the 2025-26 cap: a player's value is multiplied by the 2025-26 cap over his valuation season's cap. This keeps every trade in one unit, so trades from different seasons can be compared and summed, and it changes the size of a value but never its sign or its order within a trade.`));
add(H2("What the three models share"));
add(P("The three models share the price of a win and the cost rules. Each season is priced on one price line, estimated from what clubs paid for players' forecast play (Section 3). Each season is costed by the same rules from the CBA: the entry-level salary while a player's first contract runs, then the qualifying offer, or the arbitration price once he is eligible for salary arbitration (Section 4). Because both are shared, a player, a pick, and a prospect are measured in the same currency and can be added together."));

// =====================================================================================================================
// 2. THE FORECAST
// =====================================================================================================================
add(H1("2. Players Under Contract: the Forecast"));
add(P("A contract commits a club to a cap hit for each of its seasons, and what the club receives is the player's play in seasons not yet played. For seasons k = 0, 1, 2, ... of his contract:"));
add(EQ(["value = Σ (", ["_", "p", "k"], " × ", ["_", "V", "k"], " − ", ["_", "C", "k"], ") / ", ["^", "1.03", "k"], "  +  value of the control seasons"]));
add(P("where p is his chance of playing the season, V the market price of his forecast play in it, and C his cap hit. This section builds the forecast behind p and V; Section 3 prices it, and Section 4 adds up the contract and the control seasons after it."));
add(P("For each season ahead, the forecast gives three things: his WAR per 82 games if he plays, his games share if he plays, and his chance of playing. His forecast WAR if he plays is the first times the second. Each part is estimated only from seasons completed before the valuation season, so it is refitted for each valuation season; where this document shows a fit, it is the one for 2025-26, the most recent, fitted on seasons through 2024-25. A season counts as evidence of a player's ability when he played 10 or more games in it, and WAR in the shortened 2019-20 and 2020-21 seasons is scaled to 82 games. Ages are taken on September 15 of the season's first year, the date the CBA uses."));
add(H2("The starting level"));
add(P("A single season of WAR is a noisy measure of a player's ability: a hot shooting season or an injury can move it a long way. The forecast therefore starts from his last three seasons and pulls them toward the level of players similar to him:"));
add(EQ(["starting level = 0.65 × own rate + 0.35 × comparable players' level + their change to the valuation season"]));
add(P("His own rate is his WAR per 82 games in the three seasons before the valuation season, counting seasons of 10 or more games, weighted 50/30/20. Each season's weight is also multiplied by its games, so a 20-game season counts for less than a full one. Comparable players' level, defined below, is measured at the age of his last counted season, and the last term adds their change in level from that age to the valuation season."));
const own = PAC.own_seasons;
add(P(`For Pacioretty at the trade, his three seasons before 2018-19 were ${listAnd(own.map((s) => `${f2(s.WAR_82)} WAR per 82 in ${s.syr}-${String(s.syr + 1).slice(2)} (${s.GP} games)`))}. His own rate is (0.5 × ${own[2].GP} × ${f2(own[2].WAR_82)} + 0.3 × ${own[1].GP} × ${f2(own[1].WAR_82)} + 0.2 × ${own[0].GP} × ${f2(own[0].WAR_82)}) / (0.5 × ${own[2].GP} + 0.3 × ${own[1].GP} + 0.2 × ${own[0].GP}) = ${f3(PAC.own_82)}. His comparable players' level at ${PAC.age_last} is ${f3(PAC.comparables_level)}, and their change from ${PAC.age_last} to ${PAC.age_last + PAC.last_lag} is ${f3(PAC.path[PAC.last_lag])}. His starting level is 0.65 × ${f3(PAC.own_82)} + 0.35 × ${f3(PAC.comparables_level)} − ${f3(Math.abs(PAC.path[PAC.last_lag]))} = ${f3(PAC.start)} WAR per 82. His poor 2017-18 season and his comparable players both pull him below his two earlier seasons.`));
add(H2("Decision: the starting level's settings"));
add(P(`The starting level needed four settings: how to weight his recent seasons, how to treat seasons with few games, how far to pull him toward similar players, and how to move him from his last season to the valuation season. Each was scored on the forecast's error (the root mean squared error of WAR per 82, on the valuation seasons 2015-16 to 2021-22) and decided by Thomas (${T("start")}).`));
add(TT("start", "The starting level's settings"));
add(TABLE(["Setting", "Adopted", "Alternatives", "Why the adopted setting", "Evidence"],
  [["Weights on his last seasons", "50/30/20 over three seasons", `Weights chosen from the data on each valuation date (${REC.fittedDecay}); 60/40 over two seasons; eight other three-season weightings`, "A fixed rule with no fitted parameter; the best of the simple weightings", "50/30/20 had the lowest error of nine simple three-season weightings"],
   ["Seasons with few games", "Each season's weight times its games", "Plain 50/30/20 on the three rates", "A 20-game season says less than a full one; the same rule for his comparable players' level", `Start ${REC.startGames.gw} against ${REC.startGames.plain}; one to five seasons ahead ${REC.startGames.gwWhole} against ${REC.startGames.plainWhole} (p = ${REC.startGames.p1} and ${REC.startGames.p2})`],
   ["Pull toward similar players", "65% his own rate, 35% his comparable players", "Other shares; a three-way blend with the league average", "The lowest error of the pulls tested; the three-way blend put no weight on the league average", "Best pull in the same test"],
   ["From his last season to the valuation season", "Add his comparable players' change over the gap", "No step: start at his last season's level", "A player a year older has aged a year", `Start ${REC.startStep.with} against ${REC.startStep.without}; one to five seasons ahead ${REC.startStep.wWhole} against ${REC.startStep.woWhole}`],
   ["Fewer than three seasons", "Rescale the weights over the seasons he has", "Count a missing season as zero", "A missing NHL season is not replacement-level play: it may be junior, the AHL, or an injury", "Missing as zero was put to Thomas and not chosen"],
   ["A counting season", "10 or more NHL games", "Any games", "A handful of games gives an unreliable rate", "The threshold used throughout the model"]],
  [1500, 1500, 2100, 2200, 2340], [], new Set(), 16));
add(CAPTION("Errors are root mean squared errors of WAR per 82 on the valuation seasons 2015-16 to 2021-22 (25_TESTS/starting_level_simple_test.py and level_games_weighting_test.py, 2026-10-04 and 2026-10-05). The p-values are one-sided, from 2,000 redraws of careers. The games weighting was not statistically significant at the 5% level on its own; it was chosen so that a player's own rate and his comparable players' level are measured the same way."));

add(H2("Comparable players"));
add(P("To find players similar to him, the model describes each player-season by four attributes: how his WAR divides among five components (even-strength offence, even-strength defence, power play, penalty kill, and shooting), his ice time per game, his level, and his trend. His level is his 50/30/20 WAR per 82 at that age, games-weighted as above, over seasons of 20 or more games; his trend is the change in his rate between his last two seasons. Each attribute is standardized within position (each measure minus its mean, divided by its standard deviation, so that minutes and wins are on one scale) and given equal weight, so the five style shares together count as one attribute. The candidates are players of the same position at the same age, in seasons before the valuation season. Each candidate's weight falls with his distance d from the player, the square root of the summed squared differences across the attributes:"));
add(EQ(["weight = exp(−", ["^", "d", "2"], " / 2", ["^", "h", "2"], ")"]));
add(P(`where h, the yardstick, is the median distance between two players of the same position (${f2(AG.yardstick.F)} for forwards and ${f2(AG.yardstick.D)} for defencemen in the 2025-26 fit). An exact match gets weight 1, a candidate one yardstick away exp(−0.5) = 0.61, and one two yardsticks away exp(−2) = 0.14. This is kernel weighting (Nadaraya 1964; Watson 1964): an average in which closer cases count more, with no fixed number of neighbours. Pacioretty's ${PAC.comparables.n_at_age} candidates at ${PAC.age_last} carry weights that sum to ${f1(PAC.comparables.weight_sum)}; his five closest were ${listAnd(PAC.comparables.top.map((c) => `${c.name} (${f2(c.weight)})`))}.`));
add(P("A few close matches, or many distant ones, could give an extreme average. The comparable players' level is therefore blended with the league average for the player's position and age, which counts as ten more comparable players, each with full weight:"));
add(EQ(["comparable players' level = (Σ ", ["_", "w", "i"], ["_", "L", "i"], " + 10 × league level) / (Σ ", ["_", "w", "i"], " + 10)"]));
add(P(`where w is each candidate's weight and L his level at that age. Pulling a noisy average toward a group mean in this way lowers its expected error (Efron and Morris 1975). For Pacioretty, his candidates' weighted level of ${f3(PAC.comparables.weighted_mean_level)} and the league level for forwards at ${PAC.age_last} of ${f3(PAC.comparables.league_level)} give ${f3(PAC.comparables_level)}; with weights summing to ${f1(PAC.comparables.weight_sum)}, the league average carries ${pct(10 / (PAC.comparables.weight_sum + 10))} of it.`));
add(H2("Decision: how comparable players are weighted"));
add(P(`Three settings govern the weights. The yardstick could be one median for all players or one for each position. One for each position was adopted: it lowered the forecast's error slightly, ${REC.A1[1]} against ${REC.base[1]} one to five seasons ahead at four decimals, but consistently (one-sided p = ${REC.A1p[0]} for the starting level, ${REC.A1p[1]} one to five seasons ahead, and ${REC.A1p[2]} for season WAR). Leaving a player's own other seasons out of the yardstick's sample was also tested; it changed no error at four decimals and was dropped.`));
add(P(`The weight of ten on the league average is a judgement call. Removing it (comparable players alone) left the starting level unchanged but made the forecast one to five seasons ahead worse, ${REC.B1[1]} against ${REC.base[1]} (one-sided p < 0.001 that the weight of ten is better), most for players under 22 (${REC.B1under22[0]} against ${REC.B1under22[1]}), whose comparable players are few. An earlier sweep of the weight from 0.01 to 50 moved the forecast's error by at most 0.16%. A version that gave players with very short histories a league average built from 10-game seasons improved their starting level (${REC.B2start[0]} against ${REC.B2start[1]}) and nothing after it, so it was not adopted. The weight of ten was kept.`));

add(H2("Aging"));
add(P("Players change with age, and how much depends on the player. The forecast walks the starting level forward one season at a time. Each season it adds his comparable players' average change in level from that age to the next, blended with the league-average change at weight ten as above. The same comparable players, chosen once at his last counted age, supply each change. Their changes are used, not their levels: whether similar players improved or declined at an age carries over to him, while his own level stays his own."));
add(P(`A player who leaves the league records no decline. If departures were left out, the average change at older ages would come only from players good enough to stay, and the forecast would understate aging. A player who leaves the NHL for good is therefore given one more season at replacement level (WAR 0), at his own last season's games, so his departure counts as a decline. In the 2025-26 fit, ${comma(AG.imputed)} departures enter this way among ${comma(AG.careers)} careers.`));
add(P(`On average a forward improves until 24 and declines after it, by about ${f2(-gd("F", 29))} WAR per 82 from 29 to 30 and ${f2(-gd("F", 34))} from 34 to 35 (${F("aging")}, left). Pacioretty's comparable players declined slightly faster than the league average, and his forecast falls from ${f2(pacS[0].rate_82)} WAR per 82 at 29 to ${f2(pacS[pacS.length - 1].rate_82)} at 33 (${F("aging")}, right).`));
add(FIGURE("aging", "fig_aging.png", "Aging",
  `Left: the league-average change in level from one age to the next, by position, in the 2025-26 fit, with departures entered at replacement level; each point is drawn at the age reached. Right: Max Pacioretty's forecast WAR per 82 at the trade, from his comparable players' changes (blue) and, for comparison, from the league-average changes for forwards (orange); grey points are his three seasons before the trade.`));
add(H2("Decision: changes added to the start"));
add(P("The aging changes could be added to the starting level in wins per 82, or applied as a percentage of it, as the model's earlier projection did. Adding was adopted. A percentage change needs rules for players near zero: a move from 0.10 to 0.30 WAR per 82 is a small gain in wins but a tripling as a percentage, and a percentage decline applied to a negative level moves it toward zero, an improvement. The earlier projection needed a cap, a floor, and a separate rule for negative levels to handle these cases. Added changes need none, because a change of 0.2 wins means the same thing at any level."));
add(H2("Decision: how departed players enter the aging curve"));
add(P(`The level given to a departed player's missing season had to be set, and three details decided. ${T("departures")} gives each version's error. A level 0.25 WAR per 82 above replacement scored better two or more seasons ahead and worse at the start; the sweep found no best level within the range tested, so the level would have been set by the edge of the range. Zero was kept because it is what replacement level means: what a club gets from the player it calls up in his place. A player who misses a season and comes back later is not a departure, since his return shows he was not finished, and a departed season counts his own last season's games rather than a full 82. Filling in no departures at all was a wash on season WAR and much worse for players 35 and older, the group it exists for.`));
add(TT("departures", "Departed players in the aging curve: each version's forecast error"));
add(TABLE(["Version", "Starting level", "One to five seasons ahead", "Season WAR"],
  REC.C.map((r) => [r[0], f4(r[1]), f4(r[2]), f4(r[3])]), [4440, 1700, 1800, 1700], [1, 2, 3], new Set(), 16));
add(CAPTION(`Root mean squared error on the valuation seasons 2015-16 to 2021-22, 40,510 player-seasons (aging_investigations_abc.py v1.0, 2026-10-05). Each row changes one setting against the first. The starting level and the rate one to five seasons ahead are in WAR per 82; season WAR combines the rate, the games share, and the chance of playing. Players who came back were filled in at zero before (one-sided p < 0.001 that leaving them out is better); the departed season at his own games, p = 0.033 one to five seasons ahead. With the yardstick for each position, the adopted versions together give ${REC.combined.join(", ")}.`));

add(H2("Games share"));
const gsSpecs = Object.keys(GS["0"]);
const GSROW = [["tr_gp_share", "Trailing games share"], ["is_D", "Defenceman"], ["exp_seasons", "NHL seasons since his debut"], ["age_c", "Age − 27"], ["age_c2", "(Age − 27)²"], ["tw_WAR", "Trailing WAR"], ["intercept", "Intercept"]];
const ageTurn = 27 - adoptedGS.terms.age_c.b / (2 * adoptedGS.terms.age_c2.b);
add(P("WAR accumulates with games, so the forecast needs the share of the 82 games he will play if he plays at all. A regression for each season ahead estimates it from his trailing games share, his trailing WAR, his position, his NHL seasons since his debut, and his age at the valuation season and its square. The two trailing measures are his 50/30/20 averages over seasons of 10 or more games, without the games weighting, because a games share already counts games:"));
add(EQ(["games share = a + ", ["_", "b", "1"], " × trailing games share + ", ["_", "b", "2"], " × defenceman + ", ["_", "b", "3"], " × seasons since debut + ", ["_", "b", "4"], " × (age − 27) + ", ["_", "b", "5"], " × ", ["^", "(age − 27)", "2"], " + ", ["_", "b", "6"], " × trailing WAR"]));
add(P(`Age enters less 27, near the peak, which changes no forecast and makes the intercept a 27-year-old's. Its square lets the effect of age bend: the share falls with age at a rate that changes, and the coefficients put the bottom of that curve at about ${Math.round(ageTurn)}. The forecast is capped at 1 and floored at 0.05. ${T("gs")} builds the regression for the valuation season up one term at a time, in the 2025-26 fit; Appendix A gives the adopted regression for each season ahead. The trailing games share carries most of the fit (R-squared ${f3(GS["0"]["games share"].r2)} alone, ${f3(adoptedGS.r2)} adopted). Each win of trailing WAR adds ${f1(100 * adoptedGS.terms.tw_WAR.b)} percentage points of games, about ${f1(82 * adoptedGS.terms.tw_WAR.b)} games: better players play more. With trailing WAR in the regression, position is no longer statistically significant at the 5% level (${pq(adoptedGS.terms.is_D.p)}).`));
const GSHEAD = { "games share": "Trailing games\nshare alone", "+ defence, experience": "+ defenceman,\nseasons since debut", "+ age, age squared": "+ age, age\nsquared", "+ trailing WAR (adopted)": "+ trailing WAR\n(adopted)" };
add(TT("gs", "Games share in the valuation season, built up one term at a time"));
add(TABLE(["Term", ...gsSpecs.map((s) => GSHEAD[s])],
  [...GSROW.map(([k, lab]) => [lab, ...gsSpecs.map((s) => cc(GS["0"][s].terms[k], 4))]),
   ["R-squared", ...gsSpecs.map((s) => f3(GS["0"][s].r2))]],
  [2140, 1875, 1875, 1875, 1875], [1, 2, 3, 4]));
add(CAPTION(`Least squares on ${comma(adoptedGS.n)} player-seasons by ${comma(adoptedGS.players)} players: each player's trailing inputs at a valuation season from 2008-09 to 2024-25, and his games share in that season, among seasons he played. Coefficient (standard error, clustered by player) [two-sided p-value]. The adopted column is the model's fit, coefficient for coefficient.`));
add(H2("Decision: a straight line with a curved age effect"));
add(P(`A games share lies between 0 and 1, and a straight line can predict outside that range, which is why the forecast is capped. Two alternatives were tested. The first was a fractional logit (Papke and Wooldridge 1996): a logistic curve fitted to the share, so that every prediction lies between 0 and 1. It fitted the share better (root mean squared error ${REC.D.logitShare} against ${REC.D.buildShare}) but made season WAR worse (${REC.D.logitWar} against ${REC.D.buildWar}), because it predicts worse where the forecast matters most, for regulars who play most of the season. The second, adding age squared to the straight line, improved both (${REC.D.sqShare} and ${REC.D.sqWar}; one-sided p = ${REC.D.sqP[0]} and ${REC.D.sqP[1]}) and was adopted. The cap binds on 0.1% to 0.5% of forecasts in most seasons ahead.`));
add(P(`The player's quality enters as his trailing WAR total, not his rate per 82. Both were tested: the total predicted season WAR better (${REC.unif.total} against ${REC.unif.rate}; one-sided p = ${REC.unif.pRate} that the rate is better), because the question here is whether and how much he plays, and a player's total already reflects how much he played. A term for trailing WAR above one win helped the share but cost season WAR (${REC.unif.total} without it against ${REC.unif.totalTerm} with it; p = ${REC.unif.pTerm}) and was dropped.`));

add(H2("Chance of playing"));
const uc = adoptedPP.terms.under_contract;
add(P("A contract pays its cap hit whether or not the player plays, but his value accrues only if he does. The chance he plays at least one NHL game in a season is a logistic regression for each season ahead. Its inputs are his age in that season and its square, his trailing WAR and games share, his seasons since his debut, his position, and whether he is under contract for that season on a deal signed by the valuation date:"));
add(EQ(["log( p / (1 − p) ) = a + ", ["_", "c", "1"], " × (age − 27) + ", ["_", "c", "2"], " × ", ["^", "(age − 27)", "2"], " + ", ["_", "c", "3"], " × trailing WAR + ", ["_", "c", "4"], " × trailing games share + ", ["_", "c", "5"], " × seasons since debut + ", ["_", "c", "6"], " × defenceman + ", ["_", "c", "7"], " × under contract + ", ["_", "c", "8"], " × no contract record"]));
add(P(`The left side is the log of the odds of playing; a coefficient is the change in those log odds for one more unit of its input, and e raised to a coefficient multiplies the odds. Contract status is visible only from 2018-19, when the contract records start, so an indicator, no contract record, marks the earlier seasons; without it they would read as seasons without a contract. ${T("pp")} builds the regression for the valuation season up one term at a time. Being under contract for the season multiplies the odds of playing by e^${f2(uc.b)} = ${f1(Math.exp(uc.b))} (${pq(uc.p)}), and each win of trailing WAR by ${f2(Math.exp(adoptedPP.terms.level.b))}. Contract status is read at the date of the valuation, which for a traded player is the trade date, so a deal signed by then is seen.`));
const ppSpecs = Object.keys(PP["0"]);
const PPROW = [["age", "Age − 27"], ["age_sq", "(Age − 27)²"], ["level", "Trailing WAR"], ["gp_share", "Trailing games share"], ["exp_seasons", "NHL seasons since his debut"], ["is_D", "Defenceman"], ["under_contract", "Under contract for the season"], ["contract_unknown", "No contract record (season before 2018-19)"], ["intercept", "Intercept"]];
add(TT("pp", "Chance of playing in the valuation season, built up one term at a time"));
add(TABLE(["Term", "Age alone", "+ trailing WAR, games\nshare, seasons since\ndebut, defenceman", "+ contract status\n(adopted)"],
  [...PPROW.map(([k, lab]) => [lab, ...ppSpecs.map((s) => cc(PP["0"][s].terms[k], 3))]),
   ["McFadden pseudo R-squared", ...ppSpecs.map((s) => f3(PP["0"][s].pseudo_r2))],
   ["Log-likelihood", ...ppSpecs.map((s) => comma(Math.round(PP["0"][s].loglik)))]],
  [2640, 2330, 2330, 2340], [1, 2, 3]));
add(CAPTION(`Logistic regression on ${comma(adoptedPP.n)} player-seasons by ${comma(adoptedPP.players)} players (valuation seasons 2008-09 to 2024-25), ${pct(adoptedPP.base)} of whom played. Coefficient on the log odds (standard error, clustered by player) [two-sided p-value]. McFadden's pseudo R-squared is one minus the fit's log-likelihood over that of a model with the intercept alone; higher is better. The model's own fit adds a negligible penalty (1e-4) against perfectly predicted outcomes; its coefficients differ from these by at most ${adoptedPP.gap_to_page_fit.toExponential(0)}.`));
add(H2("Decision: a chance of playing each season, read from contract status"));
add(P("The model's earlier projection lowered each season by a chain of yearly exit risks: a player who missed a season was treated as gone for good, and the chance of reaching a season was the product of the chances of surviving each season before it. That fails twice. Players come back after a missed season, which a chain that ends a career at the first absence cannot express. And it counted a departure twice, once in the exit chain and again in a production rate already lowered by players who left. The adopted forecast gives each season its own chance of playing, so a player can be absent one season and back the next, and multiplies the rate if he plays by it once."));
add(P(`Of the yes-or-no inputs, contract status moves the odds the most, and three questions about it were tested. The first was when to read it. Reading a contract's status at its signing rather than at July 1 of its first season matters for the 884 contracts signed after July 1. Read at July 1, a contract cannot see itself: their mean chance of playing was ${REC.E.e2.julyMean}, against the ${REC.E.e2.played} who actually played. Read at the signing, it was ${REC.E.e2.signMean}, and the log loss was ${REC.E.e2.signLL} against ${REC.E.e2.julyLL} (one-sided p < 0.001; log loss measures how far predicted probabilities sit from what happened, and lower is better). Reading at the signing was adopted. The second was the indicator for seasons before 2018-19: it improved season WAR (${REC.E.e1War[0]} against ${REC.E.e1War[1]}; p = ${REC.E.e1p}) and was adopted. The third was a contract effect that varies with the player's quality: it added nothing (p = ${REC.E.e3p}) and was not adopted.`));
add(P("The event is one NHL game or more, while a season counts as evidence of ability only at 10 games. The two questions differ: whether a past season is good evidence of a player's rate, and whether he is in the NHL at all in a future season. The forecast multiplies the chance of playing by the rate if he plays, so the two must describe the same event; any season with a game is a season he played."));
add(P("The regressions are fitted for each season ahead with at least 200 player-seasons of evidence: up to eight seasons ahead for the 2018-19 valuation season and twelve for 2025-26. Past that, the forecast continues the league-wide decline in expected WAR measured between the last two fitted seasons."));
add(H2("Decision: this forecast against the earlier projection"));
add(P(`The forecast described in this section replaced the model's earlier projection, which multiplied a two-season trailing total by a percentage aging path and lowered it by the exit chain. The replacement was decided on one scored run on the valuation seasons 2022-23 to 2025-26 under a rule declared before the run: the root mean squared error of season WAR was ${REC.conf.x1} against ${REC.conf.x0}, and the new forecast's error was lower (one-sided p < 0.001, from redraws of players). Those seasons had been examined by about thirty earlier versions of the model, so they are not a sealed holdout.`));

// =====================================================================================================================
// 3. PRICING A SEASON
// =====================================================================================================================
add(H1("3. Pricing a Season"));
add(P("The forecast is in wins. The price line converts it to dollars at the rate clubs pay. It is a regression of each contract's cap hit, as a share of the cap in its first season, on the player's forecast WAR if he plays in that season. It adds a slope for defencemen and a term for the contract's length in years:"));
add(EQ(["cap share = α + (β + ", ["_", "β", "D"], " × defenceman) × forecast WAR if he plays + γ × years of term"]));
add(P(`The sample is the ${comma(PL.n)} skater contracts past the entry level that started from 2018-19 to 2025-26, each with a forecast at its signing. They were signed by ${comma(PL.players)} players who had a season of 10 or more games in one of the two before. Of these contracts, ${comma(PL.censored)} are at the league minimum, which is a floor rather than a negotiated price: a player at the minimum might have been worth less, but no club can pay less. The regression therefore treats them as censored. For a contract above the minimum it asks how close the price line comes to the cap hit; for one at the minimum, only how likely the price line is to put the player at or below it (a Tobit regression; Tobin 1958). Treating minimum contracts as negotiated prices would pull the price line toward the minimum and understate what clubs pay per win.`));
const plSpecs = Object.keys(PLF);
const PLROW = [["intercept", "Intercept (α)"], ["per forecast win", "Per forecast win (β)"], ["defence addition per win", "Added per win for a defenceman (β_D)"], ["per year of term", "Per year of term (γ)"]];
add(TT("pl", "The price line, built up one term at a time"));
add(TABLE(["Term", "Forecast WAR alone", "+ defence slope\n(the term-free\nprice line)", "+ term\n(adopted)"],
  [...PLROW.map(([k, lab]) => [lab, ...plSpecs.map((s) => cc(PLF[s].terms[k], 3, CAP25M))]),
   ["Spread of the price (σ)", ...plSpecs.map((s) => f3(PLF[s].sigma * CAP25M))],
   ["Log-likelihood", ...plSpecs.map((s) => Number(PLF[s].loglik_share).toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 }))]],
  [2840, 2260, 2260, 2280], [1, 2, 3]));
add(CAPTION(`Censored (Tobit) regression on ${comma(PL.n)} contracts, ${comma(PL.censored)} of them at the league minimum, refitted on today's forecasts. Coefficients are shares of the cap, shown in millions of dollars at the 2025-26 cap (standard error, clustered by player) [two-sided p-value]; σ is the typical distance of a cap hit from the price line. Log-likelihood in cap-share units, on the same contracts in each column; higher is better. The model prices on the price line locked on October 14, 2026; refitted today its coefficients differ from the lock by at most ${(LK.gap_term_in).toExponential(1)} of the cap ($${comma(Math.round(LK.gap_term_in * CAP25))} at the 2025-26 cap), inside the lock's tolerance.`));
add(P(`At the 2025-26 cap, the locked price line prices a forecast win at ${mil(perWin(LK.term_in.beta))} for a forward and ${mil(perWin(LK.term_in.beta + LK.term_in.beta_d_add))} for a defenceman, and adds ${mil(perWin(LK.term_in.gamma_term))} a season for each year of term. A one-season forward forecast at one win is priced at (${f4(LK.term_in.alpha)} + ${f4(LK.term_in.beta)} + ${f4(LK.term_in.gamma_term)}) × $${f1(CAP25M)} million = ${mil(perWin(LK.term_in.alpha + LK.term_in.beta + LK.term_in.gamma_term))}. ${F("price")} shows the price line against the contracts it is fitted on.`));
add(FIGURE("price", "fig_price_line.png", "The price line",
  `Each point is one contract's cap hit, restated at the 2025-26 cap, against the forecast at its signing of the player's WAR if he plays in its first season. Lines: the adopted price line for one, three, and six years of term, floored at the league minimum.`));
add(H2("Decision: the forecast at the signing"));
add(P(`The price line could be fitted on three measures of each player: his trailing WAR, his forecast dated at the contract's first season, or his forecast dated at its signing. The model's earlier price line used trailing WAR. A price line fitted per trailing win cannot price forecast wins: the forecast is narrower than the trailing total (across players it runs ${REC.spread.fc}), so a price line fitted on the wider measure underprices each forecast win above the intercept, and good players look overpaid by construction. A price line fitted on the forecast prices the quantity it is applied to.`));
const SL = PL.signing_log.find((l) => l.startsWith("seasons between")) || "";
const before = (SL.match(/, 1: ([\d,]+)/) || [])[1];
const SD = PL.signing_log.find((l) => l.startsWith("start-dated (page")) || "";
const sampleN = (SD.match(/of ([\d,]+)/) || [])[1];
add(P(`Dating the forecast at the first season would let it read seasons played after the contract was signed. Of the ${sampleN} contracts in the price line's sample, ${before} were signed before the season preceding their first season had finished; a forecast dated at the start would read that season, which the club had not seen when it signed. Dating the forecast at the signing gives each contract the information its club had. In-sample the two fit about equally: without term the start-dated forecast fits slightly better (log-likelihood ${REC.ll.startFree} against ${REC.ll.signFree}), and with term, the adopted form, slightly worse (${REC.ll.startIn} against ${REC.ll.signIn}; both from the October 14 lock's fit). The choice therefore does not rest on fit: the signing-dated forecast was adopted because it reads only what was known.`));
add(H2("Decision: contract length in the price line"));
add(P(`Clubs pay more a season for a longer contract at the same forecast: they buy the security of the player for those years. ${T("term")} shows it. Without a term for length, the price line overprices one-year contracts by ${mil(PL.by_term[0].term_free - PL.by_term[0].observed)} on average and underprices eight-year contracts by ${mil(PL.by_term[7].observed - PL.by_term[7].term_free)}; with it, each length's mean is close. Adding term raises the log-likelihood by ${f1(PLF["wins + defence + term"].loglik_share - PLF["wins + defence"].loglik_share)} on the same contracts, and its coefficient is statistically significant at the 5% level (${pq(PLF["wins + defence + term"].terms["per year of term"].p)}). The price line without term is reported beside each value as a sensitivity.`));
add(TT("term", "Mean cap hit by contract length, observed and priced"));
add(TABLE(["Years of term", "Contracts", "Observed", "Price line without term", "Adopted price line"],
  PL.by_term.map((r) => [String(r.years), comma(r.n), money(r.observed), money(r.term_free), money(r.term_in)]),
  [1800, 1700, 2000, 2050, 2090], [1, 2, 3, 4]));
add(CAPTION("Mean cap hit of the contracts of each length, and the mean of each price line's expected cap hit for the same contracts, allowing for the league minimum; millions of dollars at the 2025-26 cap."));
add(P("Term does not mean more wins. When length was tested as a predictor of the player's later production, it had opposite signs on two measures (negative on Game Value in each of 18 versions of the test, positive on Bacon's WAR in each), and on either measure later production accounted for at most a sixth of the length premium. The premium prices security, not production."));
add(P("How term enters a season's price also had to be decided: the contract's original length at every valuation, the term left at the valuation date, or a term that shrinks season by season. The term left at the valuation date was adopted, the same for each remaining season, because the comparison is a replacement player with the same forecast signed on that date for the rest of the deal. A control season, bought one season at a time by a qualifying offer, is priced at one year of term, as is each season of a drafted player's career (Section 6)."));
add(H2("Decision: the price line's form"));
add(P(`Six other forms were tested against the adopted one on held-out contracts (${T("spec")}). A premium that falls with the player's quality predicted best, mostly through one step: a premium of $${f3(REC.step.below)} million a year for players forecast below replacement against $${f3(REC.step.above)} million for everyone else. It would also move the price of a forecast win from $${f3(REC.step.perWinFrom)} million to $${f3(REC.step.perWinTo)} million (on the price line of October 5, 2026). The flat premium was kept. The step's gain is small, 0.7% of held-out error (1.2718 against 1.2809), and it adds a term; the premium that varies by forecast group adds two more, which are not statistically significant against the step (p = ${f3(REC.step.pGroup)}). The premium's fall with quality is stated as a limitation. A separate line for restricted free agents predicted 0.17% better, mostly by pricing restricted defencemen higher, at the cost of four more terms; one price line serves both. A squared term and a bend fitted better in-sample only. A separate line for the last four seasons was not statistically significant (p = 0.24), so the price line is stable over the period.`));
add(TT("spec", "The price line against six alternatives"));
add(TABLE(["Version", "Log-likelihood gain (p)", "Held-out error", "Repeats with lower error"],
  REC.spec, [4200, 2000, 1600, 1840], [2, 3], new Set(), 16));
add(CAPTION("Tested on October 5, 2026, on that day's price line and 2,296 contracts (price_line_spec_tests.py v1.0-v1.1). Log-likelihood gain against the adopted price line, with its likelihood-ratio p-value. Held-out error: the root mean squared error of the expected cap hit, $M at the 2025-26 cap, with the contracts split by player into five groups, each predicted from a fit on the other four, the split repeated 20 times. The last column counts the repeats in which the version's error is lower than the adopted price line's."));
add(H2("The league-minimum floor"));
const mae = H.war_if_plays_mae;
add(P(`No player is paid less than the league minimum, so a season's price is the price line's price or the minimum, whichever is higher. The forecast is uncertain, and the floor cuts off only the bottom of its range: for a player near the minimum, the average price over the range of outcomes is above the price of the point forecast. Each season is therefore priced at the expected value of the higher of the two, with the price normally distributed around its point estimate μ. Its standard deviation σ is the forecast's mean absolute miss k seasons ahead (${f2(mae["0"])} WAR in the valuation season, rising to ${f2(mae["5"])} five seasons ahead) times 1.2533, converted to dollars at the season's price per win; for a normal distribution the standard deviation is the mean absolute deviation times √(π/2) = 1.2533. With F the league minimum and Φ and φ the standard normal distribution and density:`));
add(EQ(["V = F × Φ(z) + μ × (1 − Φ(z)) + σ × φ(z),   z = (F − μ) / σ"]));
add(P(`The first term is the floor times the chance the price falls below it; the second and third are the expected price when it does not. For a player far above the minimum, V equals the price line's price; Pacioretty's adjustment is $${comma(Math.round(pacS[0].uncertainty_correction))} in his first season.`));

// =====================================================================================================================
// 4. CONTRACT VALUE AND CONTROL SEASONS
// =====================================================================================================================
add(H1("4. Contract Value and Control Seasons"));
add(P("A contract's value adds its seasons and the control seasons after it. Written in full for a player valued in season t:"));
add(EQ(["value = Σ (", ["_", "p", "k"], " × ", ["_", "V", "k"], " − ", ["_", "C", "k"], ") / ", ["^", "1.03", "k"], "  +  Σ ", ["_", "W", "j"], " × (", ["_", "V", "j"], " − ", ["_", "C", "j"], ") / ", ["^", "1.03", "j"]]));
add(P("The first sum runs over the seasons k of his contracts; V_k is the floored price of his forecast at the cap expected for that season, cap_t × 1.03^k, so on the value side the growth and the discount cancel. The second sum runs over the control seasons j after the last contract, each weighted by W_j, the chance the club keeps him and he plays (below). The cap hit is subtracted whether or not he plays: an injured or buried player still counts against the cap, so the chance of playing multiplies the value only. Retirement can end a cap hit; that relief is not modelled, which errs toward a lower value. The contracts valued are the one he is playing and each extension signed on or before the valuation date; an extension signed later was not known at the valuation."));
add(H2("Control seasons"));
add(P("When a contract ends with the player a restricted free agent, his club keeps his rights until he can become an unrestricted free agent: it retains him by tendering a qualifying offer. Each control season adds its value less its cost, weighted by the chance that it happens:"));
add(BULLET("Value: his forecast WAR if he plays in that season, priced at one year of term, with the floor."));
add(BULLET("Cost: the qualifying offer, which the CBA sets from his prior salary; once he is eligible for arbitration, the higher of the qualifying offer and the price line's price of his arbitration WAR. Through the 2025 offseason the qualifying offer was 110% of a salary up to $660,000, 105% up to $1 million, and 100% above it, never above 120% of the cap hit for contracts starting from 2020-21 and never below the league minimum; the 2026 agreement's bands apply after that. The arbitration WAR is the forecast's own starting level rebuilt at that season, from the seasons before it, times the forecast games share. Each next qualifying offer is computed on what he was paid."));
add(BULLET(`Weight: the chance his club qualifies him times the chance he then plays, by his forecast quality at the decision (${T("control")}), measured on the qualify-or-walk decisions for skater contracts that ended from 2018-19 to 2024-25. The weights compound from season to season, starting from his chance of playing the contract's last season.`));
add(BULLET("Walking away: the club stops at the first control season whose surplus is negative, and later seasons count as zero."));
add(TT("control", "The weight on each control season"));
add(TABLE(["Forecast WAR if he plays", "Decisions", "Qualified", "Played, if qualified", "Weight"],
  BUCKETS.map(([b, lab]) => [lab, comma(CT.qualify_n[b]), pct(CT.qualify_p[b]), CT.plays_given_q[b] === undefined ? "–" : `${pct(CT.plays_given_q[b])} (of ${comma(CT.plays_given_q_n[b])})`, f3(bucketW(b))]),
  [2600, 1500, 1600, 2240, 1700], [1, 2, 3, 4]));
add(CAPTION("Decisions on skater contracts ending from 2018-19 to 2024-25 with the player a restricted free agent, by his forecast at the decision. Played, if qualified: the share of qualified players who played at least one NHL game the next season, among those who played the contract's last season. A player with no forecast enters the lowest group: a player who could not hold an NHL job is the one a club walks away from."));
add(H2("Decision: how a control season is weighted"));
add(P(`A control season happens only if the club qualifies the player and he then plays. Four ways of weighting it were considered. Assuming every season happens credited the model with control the clubs did not exercise: it predicted only ${REC.d14.intercept}% of the walk-aways observed. Keeping a season only when the player's forecast beats a replacement player's went too far the other way, zeroing ${REC.d14.netRepl}% of the players clubs kept. The observed qualifying rate for players of his quality was adopted first, since it is what clubs actually did. A qualified player still left the league ${REC.d14.leave}% of the time, so the chance he plays given that he was qualified was added. Reusing the forecast's chance of playing instead would count walk-aways twice, once in the qualifying rate and again in a chance of playing estimated on players who include them. The plays-given-qualified rate is measured only on players who played the contract's last season, so an absence in that season is charged once, through the chance of playing the weights compound from, and not again in the weight.`));
add(H2("Decision: the cost of a control season"));
add(P(`Until October 13, 2026, a control season cost the qualifying offer. Clubs pay more in practice: a player eligible for salary arbitration can push his pay toward market, and clubs paid first-round picks ${f1(Math.min(...PK.first_round.map((g) => g.cost_actual / g.cost_qo)))} to ${f1(Math.max(...PK.first_round.map((g) => g.cost_actual / g.cost_qo)))} times the qualifying-offer chain over their control seasons (Section 6). The options were the qualifying-offer chain, actual contracts, or a rule that prices the season at market once the player is eligible for arbitration. Actual contracts were rejected: they record what was negotiated years after the valuation, and long contracts also buy seasons after control ends. The arbitration price was adopted, for players and drafted players alike: the higher of the qualifying offer and the price line's price of his arbitration WAR. Surplus can remain in an arbitration season, but less of it. Adopting it lowered ${comma(REC.arb.pages)} of ${comma(REC.arb.total)} contract values (one for each contract and valuation season), by a median of $${f2(REC.arb.median)} million. The qualifying-offer chain alone is reported beside each value.`));
add(P(`Eligibility comes from PuckPedia's arbitration flag on the expiring contract: a player flagged eligible is eligible from his first control season, and one flagged not eligible from his second (${REC.arb.flag0}% of ${REC.arb.flag0n} players flagged not eligible were eligible a season later, and ${REC.arb.stay}% of eligible players stay eligible). The CBA's count of professional seasons (Section 12.1(a)) agreed with the flag for ${REC.arb.agree}% of ${comma(REC.arb.nFlag)} contracts and was later for ${REC.arb.later}, because the data hold no AHL games, so the flag was adopted. The flag is set at the contract's end, so a valuation dated earlier reads eligibility from a later date.`));
add(H2("Decision: walking away"));
add(P("Control is a right, not an obligation: a club qualifies a player while he is worth it and lets him go when he is not, and once it lets him go it cannot qualify him again later. The model therefore stops at the first control season whose surplus is negative. Counting every control season whatever its surplus would charge the club for seasons it would never pay for."));
add(H2("Max Pacioretty and Tomas Tatar"));
add(P(`Pacioretty's contract had one season left, 2018-19, at a cap hit of ${mil(M(pacS[0].cost_dollars))}. Vegas signed him to a four-year extension at ${mil(M(pacS[1].cost_dollars))} a season on the day of the trade, and the extension is part of the value because it was signed on or before the valuation date. ${T("pac")} values each season. Each season's price includes the term premium for the five years left: ${mil(M(pacS[0].term_premium_dollars))} of the ${mil(M(pacS[0].value_dollars))} in 2018-19, growing with the cap. The price falls short of the $7.00 million cap hit in each season of the extension, by more as he ages and his chance of playing falls.`));
add(TT("pac", "Max Pacioretty's contract, valued at the trade"));
add(TABLE(["Season", "Age", "WAR per 82", "Games share", "WAR if he plays", "Chance of playing", "Price", "Of which term", "Cap hit", "Discount", "Present value"],
  [...pacS.map((s) => [`${s.season_start}-${String(s.season_start + 1).slice(2)}`, String(29 + s.k), f2(s.rate_82), f2(s.gp_share), f2(s.projected_war), f2(s.p_play), money(M(s.value_dollars)), money(M(s.term_premium_dollars)), money(M(s.cost_dollars)), f3(s.discount), money(M(s.pv_dollars))]),
   ["Total", "", "", "", "", "", "", "", "", "", `**${money(sumPV(pacS))}**`]],
  [830, 480, 800, 780, 820, 860, 900, 880, 860, 760, 1000], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], new Set(), 16));
add(CAPTION(`Millions of dollars at the cap of the valuation season (2018-19, $${f1(M(CAP18))} million); the price uses the cap expected for each season, growing 3% a year. Price: the adopted price line's price of his WAR if he plays at five years of term, with the floor. Present value = (chance of playing × price − cap hit) × discount. He becomes an unrestricted free agent at the end, so there are no control seasons. On the price line without term, his value is ${mil(M(PAC.summary.npv_total_term_free))}.`));
add(P(`Tatar's contract had three seasons left at ${mil(M(tatS[0].cost_dollars))}. His forecast WAR if he plays is ${f2(tatS[0].projected_war)}, ${f2(tatS[1].projected_war)}, and ${f2(tatS[2].projected_war)}. Each season's price, ${listAnd(tatS.map((s) => mil(M(s.value_dollars))))}, is below his cap hit, and his value is ${mil(M(TAT.summary.npv_total))} at the 2018-19 cap (${mil(M(TAT.summary.npv_total_term_free))} on the price line without term).`));

add(H2("Goaltenders"));
add(P(`Goaltenders have a simpler model, because their WAR varies far more from season to season than a skater's. A goaltender's forecast is his 50/30/20 average of season WAR (62.5/37.5 with two seasons, the last alone with one), pulled 65% of the way to the league average of 2.19 WAR, and held flat for each remaining season. The 65% was chosen by cross-validation on held-out goaltenders: each goaltender's seasons were predicted from fits on other goaltenders (${comma(GO.lambda_n)} goaltender-seasons by ${GO.lambda_goalies} goaltenders), and the mean squared error was lowest at 0.65 (${Object.entries(GO.mse_near).map(([k, v]) => `${k}: ${f3(v)}`).join("; ")}). Goaltenders keep only 35% of their own record because a goaltender's WAR in one season says little about the next.`));
add(P(`No aging curve was fitted for goaltenders: the signal was judged too weak, and the birthdates needed were then missing for a third of them. The goaltender price line is an ordinary regression of cap share on the 50/30/20 WAR at the contract's start, over ${GO.n} standard-level goaltender contracts starting from 2015-16 (R-squared ${f2(GO.r2)}); at the 2025-26 cap it is ${mil(GO.alpha * CAP25M)} plus ${mil(GO.beta * CAP25M)} per WAR, with no term and no censoring. It is fitted on WAR before the pull toward the league average but prices the pulled forecast, the mismatch Section 3 removed for skaters. A goaltender's chance of playing each season comes from a chain of exit rates by quality and age, and each control season carries one weight for all goaltenders: ${f3(CT.goalie.qualify_p)} qualified × ${f3(CT.goalie.plays_given_q)} played = ${f3(CT.goalie.weight)}, from ${CT.goalie.n[0]} decisions.`));

// =====================================================================================================================
// 5. WAR AND CIRCULARITY
// =====================================================================================================================
add(H1("5. WAR and Circularity"));
add(P("A circularity risk comes with using one source of WAR. The price line is fitted on what clubs paid for players whose forecasts are built from WAR, and the values will be compared with outcomes measured in WAR, so agreement could reflect Bacon's model rather than play. To check that the forecast measures play, I compared it with Game Value, a measure built from the NHL's play-by-play and shift records with no Bacon input. Game Value credits each skater on the ice with an equal share of his team's expected goals for and against, adjusted for the score, plus the value of the penalties he draws and takes; its adjusted version (GV-adj) also separates a player from his linemates and opponents at five-on-five. Across full seasons, team Game Value explains 58.3% of the variation in team goal differential."));
add(P(`${T("gv")} compares each measure with the same season's Game Value, across ${comma(GV.n)} player-seasons by ${comma(GV.players)} players from 2017-18 to 2025-26. The forecast agrees with Game Value more closely than the trailing WAR it starts from (r = ${f3(GV.all.forecast[0])} against ${f3(GV.all.trailing[0])}), for forwards and defencemen, and one season further ahead (${f3(GV.next.forecast[0])} against ${f3(GV.next.trailing[0])}). The correlation of expected WAR is ${f3(GV.expected[0])} with contract status and ${f3(GV.no_contract[0])} without it, so the agreement does not come through clubs' contract decisions. Some agreement is expected regardless, since both measures describe the same games.`));
add(TT("gv", "Correlation of each measure with the same season's Game Value"));
const gvr = (lab, key, idx = 0) => [lab, ...["all", "F", "D", "next"].map((s) => (GV[s] && GV[s][key] ? f3(GV[s][key][idx]) : "–"))];
add(TABLE(["Measure", "All skaters", "Forwards", "Defencemen", "One season further"],
  [gvr("Trailing WAR, 60/40 over two seasons (the earlier model)", "trailing60"), gvr("Trailing WAR, 50/30/20", "trailing"),
   ["Starting level (per 82)", f3(GV.start[0]), "–", "–", "–"], gvr("Forecast WAR if he plays", "forecast"),
   ["Expected WAR", f3(GV.expected[0]), "–", "–", "–"], ["Expected WAR without contract status", f3(GV.no_contract[0]), "–", "–", "–"]],
  [4200, 1360, 1360, 1360, 1360], [1, 2, 3, 4], new Set(), 16));
add(CAPTION(`Pearson correlation with GV-adj, on ${comma(GV.n)} player-seasons (${comma(GV.n_next)} one season further). Measured on October 5, 2026 (gv_investigation_f.py), on the forecast before ages moved to September 15. In paired redraws of careers, the forecast's correlation is higher than the 60/40 total's (one-sided p < 0.001) on each Game Value version, for forwards, for defencemen, and one season further.`));
add(H2("Decision: Bacon's WAR, checked by Game Value"));
add(P("Game Value could have replaced Bacon's WAR as the model's measure of play. GV-adj was tested as a replacement and came closer to Bacon's results for forwards than for defencemen: play-by-play data record shots and goals well and the defensive plays that prevent a chance poorly. The comparison cannot say which measure values defence more accurately, so the model keeps Bacon's WAR and uses Game Value as the independent check above."));

// =====================================================================================================================
// 6. DRAFT PICKS
// =====================================================================================================================
add(H1("6. Draft Picks"));
const PS = PK.p_star;
const neverN = PK.routes["never played"];
add(P(`A draft pick has no contract and no player yet. It is a claim on whoever the club selects, so its value has to come from what past selections at the same draft position delivered. Two features of the draft make this hard. Outcomes are uneven: of the ${comma(PK.n)} players drafted from 2007 to 2017, ${comma(neverN)} played no NHL game while their club held their rights, and the ${PK.top5.n} with the most surplus, 5% of the players, delivered ${pct(PK.top5.share, 0)} of the total. And outcomes arrive slowly: a club holds a drafted player's rights for about nine seasons, so the drafts that can be measured completely are years older than the trades being priced.`));
add(H2("The approach"));
add(P(`Most of the surplus picks produce comes from the few players who become stars. Of the ${comma(PK.stars.skaters)} skaters drafted from 2007 to 2015, the ${PK.stars.stars} who became stars (${pct(PK.stars.share_players)}, by Bacon's definition below, with at least 200 NHL games) delivered ${pct(PK.stars.share_surplus)} of the surplus those picks returned. Among the first ten picks, stars were ${pct(PK.stars.top10_share_players)} of the players and delivered ${pct(PK.stars.top10_share_surplus)} of the surplus. The model therefore values a pick as a claim on a chance of a star:`));
add(EQ(["pick value = star value × star probability for the draft position"]));
add(P(`The star probability is the chance that a player taken at that draft position becomes a star. It comes from Patrick Bacon's draft model, the source of the WAR used throughout, which defines a star as a player whose career WAR per 82 games is at least 1.8 for a forward or 1.23 for a defenceman. The star value is the surplus a pick would be worth if its player were certain to become a star. It is estimated below at ${mil(STAR.b)} at the 2025-26 cap; the first overall pick, with a star probability of ${pct(PS["1"])}, is worth ${f3(PS["1"])} × ${mil(STAR.b)} = ${mil(STAR.b * PS["1"])}.`));
add(H2("What a drafted player delivered"));
add(P("To learn what a draft position returns, I price each player drafted from 2007 to 2017 the way the player model prices a contract, over the seasons his club held his rights: from his draft to the end of club control, with careers observed through 2025-26. Six drafted players who died before reaching the NHL, while their clubs still controlled them, are left out (Appendix C). The rules for each season are:"));
add(BULLET("Value: the market price of the wins he delivered, on the price line at one year of term, with the league-minimum floor; a goaltender's on the goaltender price line. The pick model learns from what happened, so it prices delivered WAR, not a forecast. WAR in the shortened 2012-13, 2019-20, and 2020-21 seasons is scaled to 82 games."));
add(BULLET("Cost: first the entry-level maximum for his draft class, counted from his first NHL season, for three, two, or one seasons by his age on September 15 of the year he signed (18 to 21, 22 to 23, 24 or older). Then a chain of one-year qualifying offers, and once he is eligible for arbitration, the higher of the qualifying offer and the price line's price of his arbitration WAR, as for players under contract. He becomes eligible after 4, 3, 2, or 1 seasons of 10 or more NHL games for a signing age of 20 or under, 21, 22 to 23, or 24 or older (CBA Section 12.1(a))."));
add(BULLET("A season without an NHL game is worth zero and costs zero, since a minor-league salary does not count against the cap. A season of fewer than 10 games is scaled by its games over 82, since a call-up counts against the cap only for his days on the roster."));
add(BULLET(`Rights: a player who first played for another club, without having signed with or been traded by the club that drafted him, is worth zero to the pick, since the drafting club let his rights lapse (${PK.routes.lapsed} players). One who signed his entry-level contract with the drafting club and was lost later, on waivers or by release, keeps his surplus (${PK.routes["signed by the drafting club"]} players): the club held him.`));
add(BULLET("Each season's value and cost are stated at the 2025-26 cap with the formula of Section 1, and summed. A career whose total is negative counts as negative."));
const PT = PK.point;
add(P(`${T("point")} prices Brayden Point, taken 79th in 2014 (star probability ${pct(PT.p_star)}). He spent two seasons in junior, three on his entry-level contract, one on a qualifying offer, and three priced at arbitration. His surplus is ${mil(PT.surplus)}; on the qualifying-offer chain alone it would be ${mil(PT.surplus_qo)}.`));
add(TT("point", "Brayden Point (2014, #79), from his draft to the end of club control"));
add(TABLE(["Season", "NHL games", "WAR per 82", "Contract charged", "Value", "Cost", "Surplus", "Cost on the qualifying-offer chain"],
  [["2014-15, 2015-16", "0", "", "Junior (Moose Jaw)", "0.00", "0.00", "0.00", "0.00"],
   ...PT.seasons.map((s) => [`${s.season}-${String(s.season + 1).slice(2)}`, String(s.gp), f2(s.war82), s.elc ? "Entry-level" : (s.arb ? `Arbitration (${f2(s.arb_war)} WAR)` : "Qualifying offer"), f2(s.value), f2(s.cost), f2(s.surplus), f2(s.cost_qo)]),
   ["Total", "", "", "", f2(PT.seasons.reduce((a, s) => a + s.value, 0)), f2(PT.seasons.reduce((a, s) => a + s.cost, 0)), `**${f2(PT.surplus)}**`, f2(PT.seasons.reduce((a, s) => a + s.cost_qo, 0))]],
  [1500, 900, 1000, 2000, 900, 900, 1000, 1400], [1, 2, 4, 5, 6, 7], new Set(), 16));
add(CAPTION("Millions of dollars at the 2025-26 cap. Value: his delivered WAR priced on the price line at one year of term. Arbitration: the price of his arbitration WAR (shown), the forecast's own starting level rebuilt at that season, when it exceeds the qualifying offer. Season WAR for 2019-20 and 2020-21 is scaled to 82 games. Club control ended after 2022-23."));
add(H2("Decision: the cost of keeping a drafted player"));
add(P(`How cost is charged once a drafted player is in the NHL moves pick values more than any other choice. The options were the qualifying-offer chain, the cost of holding a player's rights; actual contracts; and the arbitration price once he is eligible. The qualifying-offer chain understates what clubs pay. A star's club usually signs him to a long contract while it still holds his rights, and a player eligible for arbitration can push his pay toward market. ${F("pickcost")} compares the costs for first-round picks who played in the NHL. As a multiple of the qualifying-offer chain, clubs actually paid ${listAnd(PK.first_round.map((g) => `${f1(g.cost_actual / g.cost_qo)} times for picks ${g.lo} to ${g.hi}`))}.`));
add(P(`Actual contracts were not used as the cost. They bring hindsight into the cost side, since they record what was negotiated years after the draft, and many are long contracts that buy unrestricted seasons as well as the seasons of club control. The arbitration price was adopted on both sides of the trade study: it charges market prices from eligibility by a rule, without hindsight, and the same rule costs a player's control seasons (Section 4). It lowers the star value from ${mil(PK.qo_chain.star)} on the qualifying-offer chain to ${mil(STAR.b)}, and it still charges less than clubs paid: as a multiple of the qualifying-offer chain, it charges ${listAnd(PK.first_round.map((g) => `${f2(g.cost_arb / g.cost_qo)} times for picks ${g.lo} to ${g.hi}`))}. Picks may therefore still look more valuable relative to players than they are, which is stated as a limitation.`));
add(FIGURE("pickcost", "fig_pick_cost.png", "Value delivered and three measures of cost, first-round picks",
  `Average per first-round skater who played in the NHL for the club that drafted him (2007-2017 drafts), over the seasons his club held his rights, in millions of dollars at the 2025-26 cap. Cost actually paid uses each season's cap hit (PuckPedia from 2018-19, CapWages before).`));
add(H2("Decision: the shape of value across draft positions"));
const shp = (nm) => SH[nm];
const SHROWS = [["Straight line in draft position", "straight line in draft position"], ["Log of draft position", "log of draft position"],
  ["Log of draft position and its square", "log of draft position and its square"], ["Star value × star probability (adopted)", "star probability (adopted)"],
  ["Star probability and its square", "star probability and its square"], ["Star and NHL-player probabilities", "star and NHL-player probabilities"]];
add(P(`Value falls steeply over the first ten picks and is close to flat after the first round (${F("picks")}). Several shapes could describe that fall: a straight line in draft position, its logarithm, the logarithm and its square, or Bacon's star probability times a star value. Each was fitted on all 2,316 picks and scored on drafts it had not seen: each draft was predicted from a fit on the other ten, and the held-out error is the root mean squared error over all picks (${T("shapes")}).`));
const stLog2 = shp("log of draft position and its square");
add(P(`The adopted shape has the lowest held-out error with a single parameter. A straight line values the first pick at ${mil(shp("straight line in draft position").at["1"])} and the logarithm at ${mil(shp("log of draft position").at["1"])}, against the ${mil(PK.avg_at["1"])} first picks returned and the adopted ${mil(STAR.b * PS["1"])}. The logarithm with its square comes close, but it turns upward after pick ${stLog2.first_rise}, valuing the 200th pick above the 137th. Adding the square of the star probability, or Bacon's probability of a 200-game NHL player, does not predict better (one-sided p = ${f3(shp("star probability and its square").p_vs_adopted)} and ${f3(shp("star and NHL-player probabilities").p_vs_adopted)}); once the star probability is in, the NHL-player probability's coefficient is ${f2(shp("star and NHL-player probabilities").terms.p_nhler.b)} (standard error ${f2(shp("star and NHL-player probabilities").terms.p_nhler.se)}). Bacon's probability is fitted on largely the same drafts, so its agreement with our surplus is not independent confirmation; applied to our data, his definition marks 5.9% of the skaters drafted from 2007 to 2015 as stars, against the 5.3% his probabilities imply.`));
add(TT("shapes", "Six shapes of value across draft positions"));
add(TABLE(["Shape", "Parameters", "#1", "#10", "#32", "#64", "Held-out error", "One-sided p"],
  [...SHROWS.map(([lab, k]) => [lab, String(shp(k).params), f2(shp(k).at["1"]), f2(shp(k).at["10"]), f2(shp(k).at["32"]), f2(shp(k).at["64"]), f4(shp(k).held), shp(k).p_vs_adopted === null ? "-" : pr(shp(k).p_vs_adopted)]),
   ["Actual average of the eleven players taken", "", f2(PK.avg_at["1"]), f2(PK.avg_at["10"]), f2(PK.avg_at["32"]), f2(PK.avg_at["64"]), "", ""]],
  [2900, 950, 700, 700, 700, 700, 1100, 1000], [1, 2, 3, 4, 5, 6, 7], bestKeys(SHROWS.map(([, k]) => ["", "", "", "", "", "", f4(shp(k).held)]), [6], 4), 16));
add(CAPTION("Values in millions of dollars at the 2025-26 cap, from each shape's fit on all 2,316 picks. Held-out error: each draft predicted from a fit without it; root mean squared error over all picks, $M. One-sided p: the share of 2,000 redraws of the drafts in which the shape's held-out error is not lower than the adopted shape's; a small p would mean the shape predicts better. The lowest error is in bold. Each actual average rests on eleven players, so one draft moves it a great deal."));
add(FIGURE("picks", "fig_picks.png", "Draft position and surplus",
  "Left: Bacon's star probability by draft position (a logistic regression on pick number with a change of slope at pick 150). Right: the average surplus of the eleven players taken at each draft position (2007-2017), and three of the shapes in the table above. Millions of dollars at the 2025-26 cap."));
add(H2("The star value"));
add(P(`I regressed each drafted player's surplus on the star probability for his draft position, with no intercept, so a draft position with no chance of a star is worth zero:`));
add(EQ(["surplus = star value × star probability + error"]));
const DI = PK.draft_intercepts;
const diVals = Object.values(DI.values);
add(P(`The coefficient is the star value, ${mil(STAR.b)} (standard error ${f2(STAR.se)}). ${T("nested")} adds an intercept, then an intercept for each draft, then draft position with an intercept, then the NHL-player probability, each on the same 2,316 picks. None predicts left-out drafts better (one-sided p of ${f3(Math.min(shp("star probability and an intercept").p_vs_adopted, DI.p_vs_adopted, shp("star probability, draft position and an intercept").p_vs_adopted, shp("star and NHL-player probabilities").p_vs_adopted))} or more), and the star value moves by at most ${mil(Math.max(...[shp("star probability and an intercept").terms.p_star.b, DI.star.b, shp("star probability, draft position and an intercept").terms.p_star.b, shp("star and NHL-player probabilities").terms.p_star.b].map((b) => Math.abs(b - STAR.b))))}. The star value of ${mil(STAR.b)} is not the value of a star: it is the surplus of a pick whose star probability is 100%, which no draft position reaches, and it also carries the surplus of players who become regulars without becoming stars, which rises with the star probability.`));
add(TT("nested", "The star value, with each term added"));
const NROW = (lab, t) => [lab, t ? cc(t, 2) : ""];
const sI = shp("star probability and an intercept"), sP = shp("star probability, draft position and an intercept"), sN = shp("star and NHL-player probabilities");
add(TABLE(["Term", "Adopted", "+ an intercept", "+ an intercept\nfor each draft", "+ draft position\nand an intercept", "+ NHL-player\nprobability"],
  [["Star probability (the star value)", cc(STAR, 2), cc(sI.terms.p_star, 2), cc(DI.star, 2), cc(sP.terms.p_star, 2), cc(sN.terms.p_star, 2)],
   ["Intercept", "", cc(sI.terms.intercept, 3), `11, ${money(Math.min(...diVals))} to ${money(Math.max(...diVals))}\njointly zero: ${pq(DI.joint_zero.p)}`, cc(sP.terms.intercept, 3), ""],
   ["Draft position", "", "", "", cc(sP.terms.pick, 4), ""],
   ["NHL-player probability", "", "", "", "", cc(sN.terms.p_nhler, 2)],
   ["Root mean squared error, in sample", f3(SH["star probability (adopted)"].rmse_in), f3(sI.rmse_in), f3(DI.rmse_in), f3(sP.rmse_in), f3(sN.rmse_in)],
   ["Held-out error", f3(SH["star probability (adopted)"].held), f3(sI.held), f3(DI.held), f3(sP.held), f3(sN.held)],
   ["One-sided p, better than adopted", "-", pr(sI.p_vs_adopted), pr(DI.p_vs_adopted), pr(sP.p_vs_adopted), pr(sN.p_vs_adopted)]],
  [2360, 1460, 1460, 1460, 1460, 1460], [1, 2, 3, 4, 5], new Set(), 16));
add(CAPTION("Least squares on 2,316 drafted players, 2007-2017; surplus in millions of dollars at the 2025-26 cap. Coefficient (heteroskedasticity-robust standard error, which allows the size of the misses to differ across players) [two-sided p-value]. Held-out error and one-sided p as in the table of shapes; a left-out draft has no intercept of its own, so the draft-intercept version predicts it at the other drafts' average."));
add(H2("Decision: no intercept and no draft-year terms"));
add(P(`Two additions were considered and left out. A single intercept would give each pick, including a seventh-round pick with almost no chance of a star, a fixed amount of ${mil(sI.terms.intercept.b)}. It is not statistically significant at the 5% level (${pq(sI.terms.intercept.p)}), yet when it was measured it would have raised the value of all traded picks by 9.5% and of seventh-round picks by 111%, because a fixed amount is large next to their small star values.`));
add(P(`An intercept for each draft would let deep and shallow drafts differ in level. The draft intercepts are jointly statistically significant at the 5% level (${pq(DI.joint_zero.p)}): beyond what its star probability predicts, a pick in the best draft delivered ${mil(Math.max(...diVals))} and in the weakest ${mil(Math.min(...diVals))}. They are left out because a pick traded before its draft has no intercept of its own: it would have to be valued at the average draft's intercept, which is what the model did before with indicators that sum to zero, and those moved the star value by $0.004 million. Predicting a left-out draft at the average intercept is no better than the adopted model (one-sided p = ${f3(DI.p_vs_adopted)}). The differences between drafts are carried instead by the next decision.`));
add(H2("Decision: one star value for every draft"));
const per = PK.per_draft;
const lo = per.reduce((a, b) => (b.star < a.star ? b : a)), hi = per.reduce((a, b) => (b.star > a.star ? b : a));
add(P(`Fitted on each draft separately, the star value ranges from ${mil(lo.star)} for the ${lo.draft} draft to ${mil(hi.star)} for ${hi.draft}, and the differences are statistically significant (${pq(PK.equal_test.p)}; ${F("pickdrafts")}). Some drafts are deeper than others, so this is expected. What matters is whether the star value drifts over time, because a drift would make an average over eleven drafts wrong for any one trade. Fitted with a linear trend across draft years, the star value rises by ${mil(PK.trend.all.b)} a draft (${pq(PK.trend.all.p)}). That rise rests on two drafts. Without 2015 (Connor McDavid, Jack Eichel) and 2016 (Auston Matthews), the trend falls to ${mil(PK.trend.without_2015_2016.b)} a draft and is not statistically significant (${pq(PK.trend.without_2015_2016.p)}).`));
add(P(`The model therefore uses one star value for every draft, fitted on all eleven, which treats each club as expecting the same value from a given draft position each year and an exceptional draft as noise. A star value for each trade season, fitted only on drafts whose control had run out by then, was built first and retired: it rested the early trade seasons on two or three drafts, and the test behind it showed only that drafts differ, not that they drift. The 2015 and 2016 drafts finished after most of the trades studied, so the fit without them, ${mil(PK.sensitivity.star)}, is reported beside it as a sensitivity; it lowers each pick's value by ${pct(1 - PK.sensitivity.star / STAR.b, 0)}.`));
add(FIGURE("pickdrafts", "fig_pick_drafts.png", "The star value fitted on each draft",
  "Each dot is the star value fitted on one draft alone (all positions), with bars two standard errors either side. The solid line is the star value fitted on all eleven drafts and used by the model; the dashed line is the same fit without the 2015 and 2016 drafts. Millions of dollars at the 2025-26 cap."));
add(H2("The value of a pick"));
const PSK = ["1", "2", "5", "10", "13", "20", "32", "50", "64", "100", "150", "200"];
add(TT("pickvals", "The value of a pick at selected draft positions"));
add(TABLE(["Draft position", ...PSK],
  [["Star probability", ...PSK.map((k) => pct(PS[k]))], ["Value", ...PSK.map((k) => f2(STAR.b * PS[k]))], ["Without 2015 and 2016", ...PSK.map((k) => f2(PK.sensitivity.star * PS[k]))]],
  [1680, ...PSK.map(() => 663)], PSK.map((_, i) => i + 1), new Set(), 15));
add(CAPTION(`Value: the star value (${mil(STAR.b)}, or ${mil(PK.sensitivity.star)} without 2015 and 2016) times the star probability, in millions of dollars at the 2025-26 cap.`));
add(H2("Valuing a traded pick"));
const TPK = PK.trade_pick;
add(P("A pick is often traded before anyone knows its draft position, so the model assigns one in three ways, by what was known on the trade date:"));
add(BULLET(`A pick traded during its own draft takes its actual draft position (${PK.traded.methods["actual slot (traded during the draft)"]} of the ${comma(PK.traded.n)} traded picks).`));
add(BULLET(`A pick for the coming draft, traded once that season's regular season has started, takes the draft position implied by its original team's place in the standings on the trade date, worst first, by points percentage (${PK.traded.standings_n}). For ${PK.traded.within3} of them this lands within three places of the pick's actual draft position, and the median miss is ${f1(PK.traded.median_gap)}.`));
add(BULLET(`A pick traded before that season starts, or for a later draft, takes the average star probability of its round (${PK.traded.methods["round average (before the season's first game)"] + PK.traded.methods["round average (a later draft)"]}).`));
add(P(`The round average rests on how little a team's draft position says about its position a year or two later. Across the 2005 to 2026 drafts, a team's own first-round position correlates ${f2(LIN.corr1)} with its position in the next draft and ${f2(LIN.corr2)} with its position two drafts later, and moves a median of ${f1(LIN.median_move)} places in a year. The draft position is not purely random, so the round average gives up some information. Valued at the positions teams went on to pick, the next first-round pick of a team that just picked in the top five was worth ${mil(LIN.top5_later)} on average, and that of a team that just picked 25th or later ${mil(LIN.bottom_later)}, against the round average of ${mil(LIN.round_avg)}. The round average therefore undervalues a weak team's future first-round pick and overvalues a strong team's; it is kept for its simplicity, and the difference is stated as a limitation. The draft lottery and the reordering of playoff teams are not modelled, and a conditional pick is valued as if its condition were met.`));
add(P(`The 2019 second-round pick Montreal received was traded before the 2018-19 season began, so it takes the average star probability over round 2's draft positions, ${pct(TPK.star_chance, 2)}, and is worth ${f4(TPK.star_chance)} × ${mil(STAR.b)} = ${mil(TPK.value)}. It became the ${TPK.actual_slot}th pick.`));

// =====================================================================================================================
// 7. PROSPECTS
// =====================================================================================================================
add(H1("7. Prospects"));
add(P("A prospect is a drafted player the player model does not yet value: a skater with no NHL season of 10 or more games in the three before the valuation season, or a goaltender with no NHL game in the six before it. The six seasons match the goaltender forecast, which reads any NHL season in the three before and looks back three more when the last is missing. This boundary means no player is valued twice or by neither model."));
add(P(`A prospect is valued in the pick model's currency. The model learns from the 2,316 players drafted from 2007 to 2017, in each season from D+1 on in which a player was still a prospect and his club still controlled him. The outcome is his remaining surplus: the surplus he went on to deliver from that season to the end of club control, priced as in Section 6. A prospect traded between the draft and the start of D+1 is valued as in D+1.`));
add(H2("Draft position, and how its value fades"));
const A10 = "picks 1-10", A37 = "rounds 3-7", AALL = "all drafted players";
add(P(`At the draft, a pick is worth its draft position's star probability times the star value. A prospect starts with his pick's value; the question is how that value changes while he remains unproven. The answer depends on when drafted players reach the NHL. Of the ${comma(PK.n)} drafted players, ${f1(everA(AALL))}% played an NHL season of 10 or more games (a goaltender, an NHL game) before their club's control ended (${F("arrival")}). Of the 110 top-ten picks, ${f1(cumA(A10, 1))}% had reached the NHL by D+1, ${f1(cumA(A10, 2))}% by D+2, and ${f1(cumA(A10, 3))}% by D+3. Of the picks from rounds 3 to 7, ${f1(cumA(A37, 3))}% had reached it by D+3 and ${f1(cumA(A37, 4))}% by D+4, and ${f1(everA(A37))}% ever did. A top pick still a prospect in D+4 is unusual, and later picks who reach the NHL at all reach it later.`));
add(FIGURE("arrival", "fig_arrival.png", "When drafted players reach the NHL",
  "Drafted players of 2007 to 2017, without the six who died. Each line is the share of a draft group's players who had reached the NHL by each season; the gap above a line at D+9 is the share who never did. Reaching the NHL means a first NHL season of 10 or more games (for a goaltender, a first NHL game), the point at which the player model takes him; only seasons within club control are counted."));
add(P("I regressed each prospect's remaining surplus on the star probability for his draft position, interacted with an indicator for each season from D+1 to D+4 and one for D+5 onwards, with no intercept. The coefficient for each season is that season's star value: the surplus value if a prospect in that season were certain to become a star."));
add(EQ(["remaining surplus = star value for D+n × star probability + error"]));
const S_ = PR.star;
add(P(`For example, a #10 pick (star probability ${pct(PS["10"])}) who is still a prospect in D+3 is worth ${f3(PS["10"])} × ${mil(S_["2"].b)} = ${mil(PS["10"] * S_["2"].b)}. A prospect keeps most of his draft position's value through D+3 and loses most of it over the next two seasons (${T("pstar")}), because of who is left: by D+4, most top picks who will reach the NHL have done so. The prospects left are mostly later picks and top picks who missed, and among them draft position no longer separates those who will succeed from those who will not.`));
add(TT("pstar", "The star value for a player still a prospect, by season"));
add(TABLE(["Season", "Prospect-seasons", "Star value (s.e.)", "p-value", "#1 pick", "#13 pick", "#32 pick"],
  G5.map((g) => [g === "0" ? "D+1 (at the draft)" : SEAS[g], comma(S_[g].rows), `${money(S_[g].b)} (${f2(S_[g].se)})`, pfmt(p2(S_[g].b, S_[g].se)), money(S_[g].b * PS["1"]), money(S_[g].b * PS["13"]), money(S_[g].b * PS["32"])]),
  [2000, 1600, 1600, 900, 1100, 1100, 1100], [1, 2, 3, 4, 5, 6]));
add(CAPTION("Drafted players of 2007 to 2017 still prospects, within club control. Star value in millions of dollars at the 2025-26 cap; one regression with a full set of interaction terms, standard errors clustered by player, since one player appears in several seasons; two-sided p-values. From D+5 on the rows are prospect-seasons from D+5 to D+8 pooled. The pick columns multiply the star value by the star probability for the draft position."));
add(H2("Decision: a separate star value for each season"));
add(P(`The adopted regression gives each season its own star value from D+1 to D+4, and one shared value from D+5 on, where few prospects remain and little value is left. Three simpler alternatives were tested and rejected. Each restricts how the star value may change from one season to the next, and each was fitted on the same prospect-seasons and scored the same way (${T("fade")}, ${F("fade")}). The first is one value for all seasons: the draft-day value kept for as long as a player remains a prospect (fitted: ${mil(FC["no fade"][0])}). The second is a straight-line decline: a starting value plus a fixed change for each season since the draft (${mil(FC["straight line"][0])} in D+1, falling ${mil(FC["straight line"][0] - FC["straight line"][1])} a season). The third is the same percentage decline each season (${mil(FC["same percentage"][0])} in D+1, keeping ${pct(FC["same percentage"][1] / FC["same percentage"][0])} each season).`));
add(TT("fade", "Each alternative for the star value against the adopted one"));
const FR = [["A separate value for each season (adopted)", "separate", null], ["One value for all seasons", "no fade", "traded total: no fade"], ["Straight-line decline", "straight line", "traded total: straight line"], ["Same percentage decline each season", "same percentage", "traded total: same percentage"]];
const fadeRows = FR.map(([lab, k, tk]) => [lab, f4(FS[k].rmse_M), FS[k].redraws_adopted_lower === null || FS[k].redraws_adopted_lower === undefined || Number.isNaN(FS[k].redraws_adopted_lower) ? "-" : pr(redrawP(FS[k].redraws_adopted_lower)), f2(FC[k][4]), money(FS[tk || "traded total: separate"].total_M), String(FS[tk || "traded total: separate"].below_zero)]);
add(TABLE(["Alternative", "Held-out error", "One-sided p", "Star value, D+5", "196 traded prospects, draft position alone", "Values below zero"],
  fadeRows, [3200, 1300, 1100, 1200, 1700, 1100], [1, 2, 3, 4, 5], bestKeys(fadeRows, [1], 4), 16));
add(CAPTION(`Held-out error: each draft predicted from a fit without it; root mean squared error in millions of dollars of remaining surplus per prospect-season, over ${comma(FS.separate.rows)} prospect-seasons; the lowest is in bold. One-sided p: the share of 2,000 redraws of the drafts in which the adopted model's error is not lower than the alternative's. prospect_fade_rules.py, run on today's data.`));
add(P(`One value for all seasons predicts worse than a separate value for each season (${pq(redrawP(FS["no fade"].redraws_adopted_lower))}) and nearly doubles the traded prospects' value. The straight-line and same-percentage declines predict about as well (p = ${f3(redrawP(FS["straight line"].redraws_adopted_lower))} and ${f3(redrawP(FS["same percentage"].redraws_adopted_lower))}), so the choice does not rest on prediction. I chose a separate value for each season for two reasons. It imposes no shape on the decline, and the estimates hold through D+3 and then fall, which matches when top picks reach the NHL. And the straight-line decline keeps falling past zero: from D+8 it values a top pick below a late pick, and it values ${FS["traded total: straight line"].below_zero} of the traded prospects below zero. Equal steps from D+1 to D+4 are not rejected at the 5% level (p = ${f3(FS["equal steps, D+1 to D+4 (Wald)"].p)}), which is why the straight-line decline predicts about as well.`));
add(H2("Decision: the overlap with the fit is a stated limitation"));
add(P(`A prospect drafted from 2007 to 2017 is valued from a fit that contains his own outcome. Refitting without each prospect's own draft as the main value was rejected for two reasons: it would take eleven fits for each season, and the prospect values would no longer use the same star value as the draft picks traded beside them. His value with his own draft left out is reported beside it; for the traded prospects together it is ${mil(PR.traded.own_out)} against ${mil(PR.traded.tot_drafted)}.`));

add(H2("Production"));
add(P(`Draft position is one element of what predicts a prospect's value; how much he scores after the draft is another. A player who scores at a high rate in junior, college, or a European league is more likely to reach the NHL and to contribute when he does. Scoring in different leagues is put on one scale with Bacon's NHL equivalency (NHLe) factors. A league's factor is the number of NHL points that one point in that league and season is worth; Bacon estimates it from players who played full seasons in two leagues in consecutive years, adjusted for a year of development, on a rolling four-season window, so a league's factor changes over time. An OHL point was worth 0.136 NHL points in 2006-07 and 0.120 in 2025-26.`));
add(P(`A season's production is the player's points, from Elite Prospects, times his league-season's NHLe factor, per 82 games, counted for seasons of 10 or more games. His production level weights his three seasons before the valuation season 50/30/20, rescaled over the seasons he has, as each part of the model weights recent seasons. A prospect valued in D+1 is measured on D0, D-1, and D-2, the scoring scouts saw before the draft. A prospect with no counted season (${pct(PR.no_record_share)} of prospect-seasons) gets an indicator for having no record, so missing data is not read as zero scoring; ${PR.no_record_by_k["0"] + PR.no_record_by_k["4+"]} of the ${Object.values(PR.no_record_by_k).reduce((a, b) => a + b, 0)} are in D+1 (${PR.no_record_by_k["0"]}) or from D+5 on (${PR.no_record_by_k["4+"]}). The median production level rises from ${f1(PR.median_prod["0"])} NHLe points per 82 games in D+1 to ${f1(PR.median_prod["4+"])} from D+5 on. Goaltenders stay on draft position alone, since NHLe converts scoring.`));
add(P(`${T("prod")} scores each way of adding production, on the ${comma(PR.rows)} prospect-seasons of the ${comma(PR.players)} drafted skaters, against draft position alone.`));
const NLROWS = [["Draft position alone", "slot"], ["Linear production alone", "production"], ["Draft position + linear production", "slot+production"],
  ["Draft position + linear production, a separate rate for defencemen", "slot+production by position"], ["Draft position + linear and squared production", "slot+production curved"],
  ["Linear and squared production alone", "production curved"], ["Adopted: linear and squared production; draft position in D+1 to D+3 only", "chosen"]];
const base = NL.slot.rmse_M;
const prodRows = NLROWS.map(([lab, k]) => [lab, f4(NL[k].rmse_M), k === "slot" ? "-" : `${NL[k].rmse_M > base ? "+" : ""}${f2(100 * (NL[k].rmse_M / base - 1))}%`, f4(NL[k].rmse_k0), f4(NL[k].rmse_k1), f4(NL[k].rmse_k2), f4(NL[k].rmse_k3), f4(NL[k]["rmse_k4+"]), k === "slot" ? "-" : pr(redrawP(NL[k].redraws_beating_slot))]);
add(TT("prod", "Held-out error of each way of adding production, against draft position alone"));
add(TABLE(["Candidate", "Held-out error", "vs draft position alone", "D+1", "D+2", "D+3", "D+4", "D+5 and later", "One-sided p"],
  prodRows, [2700, 900, 900, 760, 760, 760, 760, 900, 820], [1, 2, 3, 4, 5, 6, 7, 8], bestKeys(prodRows, [1, 3, 4, 5, 6, 7], 4), 15));
add(CAPTION("Held-out error as in the star value's table, here within each season too; one-sided p: the share of redraws in which the candidate's error is not lower than draft position alone's. The best in each column is in bold. The error falls with the season because most prospects still unproven in D+5 or later deliver little or no NHL surplus; compare candidates within a column. prospect_nhle_look.py, run on today's data."));
add(H2("Decision: production adds to draft position"));
add(P(`Production alone predicts worse than draft position alone (one-sided p = ${f3(redrawP(NL.production.redraws_beating_slot))} that it is better), so production does not replace draft position at the draft. Added to draft position, linear production lowers the error in each season from D+1 to D+4, but the improvement is not statistically significant at the 5% level (p = ${f3(redrawP(NL["slot+production"].redraws_beating_slot))}). Linear and squared production added to draft position is (p = ${f3(redrawP(NL["slot+production curved"].redraws_beating_slot))}), and so is the adopted combination (p = ${f3(redrawP(NL.chosen.redraws_beating_slot))}).`));
add(H2("Decision: production enters with a squared term"));
const FM = PR.forms;
add(P(`With linear production, each additional NHLe point adds the same dollars. Adding production squared lets each point add more the higher a prospect already scores. It was added because most of a pick's surplus comes from the few players who become stars. Draft position captures part of this, since the first pick's star probability is about ten times the 32nd's. But every prospect at a draft position has the same star probability whatever he scores, and linear production then gives the highest scorers, the prospects most likely to become stars, the same dollars per point as everyone else. ${T("forms")} compares three forms of production within the adopted model.`));
add(TT("forms", "Three forms of production in the adopted model"));
const FMR = [["Linear production", "linear production"], ["Linear and squared production (adopted)", "adopted"], ["Production squared alone", "production squared alone"]];
const formRows = FMR.map(([lab, k]) => [lab, f4(FM[k].rmse), ...G5.map((g) => f4(FM[k].by_k[g])), k === "adopted" ? "-" : (k === "linear production" ? `adopted better: ${pr(FM[k].p_adopted_better)}` : `adopted better: ${pr(FM[k].p_adopted_better)}`), money(PR.forms_traded[k].total)]);
add(TABLE(["Form", "Held-out error", "D+1", "D+2", "D+3", "D+4", "D+5 and later", "Head to head (one-sided p)", `${PR.traded_skaters} traded skaters`],
  formRows, [2200, 900, 760, 760, 760, 760, 900, 1500, 1060], [1, 2, 3, 4, 5, 6, 8], bestKeys(formRows, [1, 2, 3, 4, 5, 6], 4), 15));
add(CAPTION("Each form keeps the adopted structure: draft position in D+1 to D+3, production discounted by age in D+1 to D+4 (below), and the no-record indicator. Held-out error as above, from the age test's procedure (its adopted error reproduced); head to head, p is the share of redraws in which the adopted form's error is not lower than the other form's. The last column is the traded drafted skaters' total value, $M at the 2025-26 cap."));
const AD = PR.adopted;
const turn = (g, age) => -(AD[g].terms.nhle82.b + AD[g].terms.prod_x_age18.b * (age - 18)) / (2 * AD[g].terms.nhle82_sq.b);
add(P(`Linear and squared production predicts better than linear production alone (one-sided p = ${f3(FM["linear production"].p_adopted_better)}). Production squared alone, without the linear term, predicts about as well (held-out error ${f4(FM["production squared alone"].rmse)} against ${f4(FM.adopted.rmse)}; p = ${f3(FM["production squared alone"].p_adopted_better)} that the adopted form is better, ${f3(FM["production squared alone"].p_better_than_adopted)} that squared alone is). It was not adopted because it would raise the traded skaters' value from ${mil(PR.forms_traded.adopted.total)} to ${mil(PR.forms_traded["production squared alone"].total)} without predicting better. With the squared term in, the linear coefficient is not the value of an extra point: an extra point adds the linear coefficient plus twice the squared coefficient times the player's production, so its value grows with production. In the adopted model, which also discounts each point for age (below), an extra point in D+2 for a player drafted at his first opportunity is worth less than nothing only below ${f1(turn("1", 19))} points, under the 25th percentile of ${f1(PR.pct_d2["25"])}. The linear coefficient sets where the value bottoms out; it is not evidence that a little scoring lowers a prospect's value.`));
add(H2("Decision: from D+4, production replaces draft position"));
const B = PR.build;
add(P(`Once production is in the model, draft position stops carrying information in D+4: its coefficient is ${mil(B["+ production squared"]["3"].terms.p_star.b)} (${pq(B["+ production squared"]["3"].terms.p_star.p)}). From D+5 on it is negative, ${mil(B["+ production squared"]["4+"].terms.p_star.b)} (${pq(B["+ production squared"]["4+"].terms.p_star.p)}), which would value a top pick below a later pick with the same production and makes no logical sense. The adopted model keeps draft position from D+1 to D+3 and uses production alone from D+4, which drops a parameter in each later season at no cost to prediction.`));
add(P(`A separate production rate for defencemen was also tested (${T("prod")}). It changes the held-out error by ${f2(100 * (NL["slot+production by position"].rmse_M / NL["slot+production"].rmse_M - 1))}% against one rate, and its improvement over draft position alone is less consistent (p = ${f3(redrawP(NL["slot+production by position"].redraws_beating_slot))} against ${f3(redrawP(NL["slot+production"].redraws_beating_slot))}). One rate is kept.`));
add(P("With production, the model values a prospect in season D+n as follows, where S is the star probability for his draft position, P his production level, and N is 1 when he has no production record. Each term is interacted with the season indicators, so the coefficients a, b, c, and d take a separate value in each season:"));
add(EQ(["D+1 to D+3:  remaining surplus = a × S + b × P + c × ", ["^", "P", "2"], " + d × N + error"]));
add(EQ(["D+4 and later:  remaining surplus = b × P + c × ", ["^", "P", "2"], " + d × N + error"]));
add(H2("Age"));
add(P("A player who scores at a given rate at 18 is commonly rated a better prospect than one who scores at the same rate at 20: the younger player is further from his peak. Age is the player's age on September 15 of the valuation season, the date the CBA uses. A player is first eligible for the draft in the year he is 18 by September 15, so in D+1 a player drafted at his first opportunity is 18 to 19, and one drafted a year later 19 to 20. Within a season's regression each prospect is the same number of seasons from his draft, so a prospect a year older also scored his points, and was drafted, a year older; across seasons, age and seasons since the draft move almost one for one, which is why age is compared only within a season."));
add(TT("age", "Each way of adding age, against the model without it"));
const ALR = [["Without age (the production model above)", "chosen"], ["Plus age: a flat amount per year", "+ age"], ["Plus age discounting production, each season", "+ age x production"], ["Plus both", "+ age and age x production"], ["Adopted: age discounting production, D+1 to D+4", "age x production, seasons 0-3"]];
const ageRows = ALR.map(([lab, k]) => [lab, f4(AL[k].rmse_M), k === "chosen" ? "-" : `${f2(100 * (AL[k].rmse_M / AL.chosen.rmse_M - 1))}%`, k === "chosen" ? "-" : pr(redrawP(AL[k].redraws_beating_chosen))]);
add(TABLE(["Candidate", "Held-out error", "vs without age", "One-sided p"], ageRows, [4900, 1500, 1600, 1640], [1, 2, 3], bestKeys(ageRows, [1], 4), 16));
add(CAPTION("Each candidate keeps the production model (draft position in D+1 to D+3, linear and squared production, the no-record indicator) and adds the age term shown; one-sided p compares it with the model without age. With both terms against the discount alone, p = 0.617. Held-out error as above; prospect_age_look.py, run on today's data."));
add(H2("Decision: age discounts production"));
add(P(`Two forms were tested. Age as a flat amount subtracts the same dollars for each year of age, whatever the player scores. Age discounting production makes each point worth less the older the player was when he scored it. Both improve on the model without age and are statistically significant at the 5% level (p = ${f4(redrawP(AL["+ age"].redraws_beating_chosen))} and ${f4(redrawP(AL["+ age x production"].redraws_beating_chosen))}), and the discount improves the held-out error more (${f2(100 * (AL["+ age x production"].rmse_M / AL.chosen.rmse_M - 1))}% against ${f2(100 * (AL["+ age"].rmse_M / AL.chosen.rmse_M - 1))}%). I chose the discount because it is the larger gain and it measures what age was included for: how much a player's scoring says about him given the age at which he scored. Both terms together are no better than the discount alone. From D+5 on the discount adds nothing, so it applies from D+1 to D+4.`));
add(P(`In D+2, each year of age lowers the value of each NHLe point by $${f3(-AD["1"].terms.prod_x_age18.b)} million (${pq(AD["1"].terms.prod_x_age18.p)}): of two prospects with 10 points, the one a year older, who scored them a year older, is worth ${mil(-10 * AD["1"].terms.prod_x_age18.b)} less. ${F("prospect")} shows the adopted model for a prospect drafted 13th, in D+2, at three ages.`));
add(H2("Decision: the discount on production alone"));
const AFR = [["Production × age (adopted)", "adopted"], ["Both production and its square discounted", "both"], ["Production squared × age, in place of production × age", "sq_only"], ["One discount on all of production", "share"], ["Age-adjusted points in both terms", "adjusted"]];
add(P(`The adopted term discounts linear production: a point is worth b + e × (age − 18) plus the squared term's share, and the squared term is not discounted. So a year of age costs a low scorer a larger share of his production's value than a high scorer. Four forms that reach the squared term were tested (${T("ageform")}). None predicts left-out drafts better at the 5% level (one-sided p from ${f3(Math.min(...AFR.slice(1).map(([, k]) => AF[k].p_vs_adopted)))} to ${f3(Math.max(...AFR.slice(1).map(([, k]) => AF[k].p_vs_adopted)))}), and they would move the cost of age from low scorers to high scorers. The discount on production alone was kept.`));
add(TT("ageform", "Forms of the age discount"));
const ageFormRows = AFR.map(([lab, k]) => [lab, f4(AF[k].rmse_M), f4(AF[k].rmse_D1_D4), k === "adopted" ? "-" : pr(AF[k].p_vs_adopted)]);
add(TABLE(["Form", "Held-out error", "D+1 to D+4", "One-sided p, better than adopted"], ageFormRows, [4900, 1500, 1500, 1740], [1, 2, 3], bestKeys(ageFormRows, [1, 2], 4), 16));
const AC_ = PR.age_cost;
const ac = (arm, s, pts) => AC_.find((r) => r.arm === arm && r.season === s && r.points_per_82 === pts);
add(CAPTION(`prospect_age_form_look.py (October 19, 2026, on today's rows); its own refit gives the adopted form ${f4(AF.adopted.rmse_M)}. What a year of age costs, D+1, as a share of production's value: adopted ${pct(ac("production x age (adopted)", "D+1", 10).share, 0)} at 10 points per 82 and ${pct(ac("production x age (adopted)", "D+1", 20).share, 0)} at 20; both terms discounted ${pct(ac("+ production squared x age", "D+1", 10).share, 0)} and ${pct(ac("+ production squared x age", "D+1", 20).share, 0)}.`));
add(H2("The adopted model"));
add(P("The adopted model values a prospect in season D+n as follows, where A is his age on September 15 of that season. The coefficient e is the age discount: the change in the value of each point of production for each year of age. Age enters less 18, so the age term is zero for an 18-year-old."));
add(EQ(["D+1 to D+3:  value = a × S + b × P + c × ", ["^", "P", "2"], " + d × N + e × P × (A − 18)"]));
add(EQ(["D+4:  value = b × P + c × ", ["^", "P", "2"], " + d × N + e × P × (A − 18)"]));
add(EQ(["D+5 and later:  value = b × P + c × ", ["^", "P", "2"], " + d × N"]));
add(P(`${T("adopted")} gives the regression for each season, and ${T("build2")} builds the D+2 regression up one term at a time; Appendix B does the same for each other season.`));
const BROW = [["p_star", "Star probability (a)"], ["nhle82", "Production (b)"], ["nhle82_sq", "Production squared (c)"], ["no_record", "No production record (d)"], ["prod_x_age18", "Production × (age − 18) (e)"]];
add(FIGURE("prospect", "fig_prospect.png", "A prospect drafted 13th, in D+2",
  `The adopted model's value against production level, at ages 19, 20, and 21 on September 15 of the valuation season, with Nick Suzuki at the trade. Vertical lines mark the 25th, 50th, 75th, and 90th percentiles of production level among prospects in D+2 with a record. Millions of dollars at the 2025-26 cap.`));
add(TT("adopted", "The adopted prospect model, by season"));
add(TABLE(["Term", ...G5.map((g) => SEAS[g])],
  [...BROW.map(([k, lab]) => [lab, ...G5.map((g) => cc(AD[g].terms[k], 3))]), ["Prospect-seasons", ...G5.map((g) => comma(AD[g].rows))], ["Players", ...G5.map((g) => comma(AD[g].players))], ["R-squared", ...G5.map((g) => f3(AD[g].r2))]],
  [2440, 1440, 1440, 1440, 1440, 1440], [1, 2, 3, 4, 5]));
add(CAPTION("Dependent variable: remaining surplus, $M at the 2025-26 cap. One regression with a full set of interaction terms and no intercept, drafted skaters 2007-2017; coefficient (standard error clustered by player) [two-sided p-value]; R-squared measured from zero. Production squared is in squared points (15 points enter as 225). A blank cell: the term is not in that season's model. From D+4 on, each prospect without a production record delivered nothing, so that coefficient is exactly zero, with no standard error. The low R-squared reflects how uneven outcomes are: most prospects deliver no NHL surplus."));
const B2 = PR.build;
const BHEAD = { "draft position alone": "(1) Draft position\nalone", "+ linear production": "(2) + production", "+ production squared": "(3) + production\nsquared", adopted: "(4) Adopted:\n+ age" };
add(TT("build2", "The D+2 regression built up one term at a time"));
add(TABLE(["Term", ...Object.keys(BHEAD).map((s) => BHEAD[s])],
  [...BROW.map(([k, lab]) => [lab, ...Object.keys(BHEAD).map((s) => cc(B2[s]["1"].terms[k], 3))]), ["R-squared", ...Object.keys(BHEAD).map((s) => f3(B2[s]["1"].r2))]],
  [2440, 1800, 1800, 1800, 1800], [1, 2, 3, 4]));
add(CAPTION(`${comma(B2.adopted["1"].rows)} skaters who were prospects in D+2; as the previous table. Column (2) also adds the no-record indicator. Adding linear production lowers the star value's coefficient; adding its square raises R-squared further; adding age makes the square carry the value of production.`));
add(H2("Nick Suzuki"));
add(P(`Suzuki was traded at the start of his D+2 season. His draft position's star probability is ${pct(SZ.inputs.p_star)}, his production level is ${f1(SZ.inputs.nhle82)} NHLe points per 82 games (above the 90th percentile in D+2, ${f1(PR.pct_d2["90"])}), and he was ${f1(SZ.age)} on September 15, 2018, a player drafted at his first opportunity. ${T("suzuki")} builds his value from the D+2 regression.`));
add(TT("suzuki", "Nick Suzuki's value, term by term"));
add(TABLE(["Term", "His input", "Coefficient (D+2)", "Contribution"],
  [["Star probability for his draft position", f3(SZ.inputs.p_star), f3(SZ.coefs.p_star), money(SZ.parts.p_star)],
   ["Production", f2(SZ.inputs.nhle82), f4(SZ.coefs.nhle82), money(SZ.parts.nhle82)],
   ["Production squared", f2(SZ.inputs.nhle82_sq), f4(SZ.coefs.nhle82_sq), money(SZ.parts.nhle82_sq)],
   ["No production record", "0", f3(SZ.coefs.no_record), money(0)],
   ["Production × (age − 18)", f2(SZ.inputs.prod_x_age18), f4(SZ.coefs.prod_x_age18), money(SZ.parts.prod_x_age18)],
   ["Value, adopted model", "", "", `**${money(SZ.value)}**`],
   ["Value on draft position alone", "", "", money(SZ.slot)],
   ["Value with his draft left out of the fit", "", "", money(SZ.own_out)]],
  [3500, 1800, 2000, 2340], [1, 2, 3]));
add(CAPTION("Millions of dollars at the 2025-26 cap. Contributions are input times coefficient and sum to the adopted value."));
add(P(`His scoring raises his value from ${mil(SZ.slot)} on his draft position to ${mil(SZ.value)}: his production and its square add ${mil(SZ.parts.nhle82 + SZ.parts.nhle82_sq)}, and the age discount takes back ${mil(-SZ.parts.prod_x_age18)}. He was among the youngest a D+2 prospect can be; a prospect a year older with his production would be worth ${mil(-SZ.coefs.prod_x_age18 * SZ.inputs.nhle82)} less.`));
add(H2("Goaltenders and undrafted players"));
add(P("NHLe converts scoring, which says nothing about a goaltender. Elite Prospects holds goaltenders' save percentages, but no factor translates a save percentage from one league to another, so a goaltender prospect is valued on draft position alone, with the star values above; a save-based measure is untested. Those star values pool skaters and goaltenders. When last measured (October 16, 2026), the star value from D+5 on, on draft position alone, was $2.01 million pooled, $0.16 million for skaters alone (p = 0.64), and $19.35 million for goaltenders alone: nearly all of it is goaltenders' signal. A separate goaltender star value is set aside for later work."));
add(P(`An undrafted player has no draft rights, so a club holds his NHL rights only through an NHL contract; one on a minor-league contract is worth nothing to an NHL club in this currency. An undrafted player on an NHL contract is valued with the same model, his star probability set to zero and his seasons counted from his first draft-eligible year. The model is fitted on drafted players, including many whose rights lapsed and who delivered nothing, while undrafted players on NHL contracts are players a club chose to sign, so it probably undervalues them.`));
add(H2("The traded prospects"));
const TR_ = PR.traded;
add(P(`From July 2017 to March 2022, clubs traded ${TR_.drafted} drafted prospects (${TR_.drafted_players} different players, as some were traded more than once) and ${TR_.undrafted} undrafted prospects on NHL contracts. The adopted model values the drafted prospects at ${mil(TR_.tot_drafted)} (${mil(TR_.slot_alone)} on draft position alone) and the undrafted at ${mil(TR_.tot_undrafted)}, the largest ${TR_.max_undrafted_name} at ${mil(TR_.max_undrafted)}. ${T("top10")} lists the ten most valuable. Of the drafted prospects, ${TR_.below_zero} are valued below zero, ${mil(TR_.below_zero_sum)} in total: prospects with that profile, a low scorer from a late draft position, delivered slightly negative surplus on average, because when such players reach the NHL their cost tends to exceed the value of the wins they deliver.`));
add(TT("top10", "The ten most valuable traded drafted prospects"));
add(TABLE(["Traded", "Player", "Drafted", "Season", "Production", "Age", "Draft position alone", "Adopted"],
  TR_.top10.map((t) => [t.date, t.name, `${t.draft} #${t.pick}`, t.season, f1(t.prod), f1(t.age), money(t.slot), money(t.value)]),
  [1100, 1900, 1100, 800, 1000, 700, 1500, 1100], [4, 5, 6, 7], new Set(), 16));
add(CAPTION("Production in NHLe points per 82 games; age on September 15 of the season of the trade; values in millions of dollars at the 2025-26 cap."));
add(H2("Decision: D+5 and later stay on production"));
add(P(`From D+5 on, neither production term is statistically significant at the 5% level, alone or jointly (chi-squared ${f2(PR.joint_late.chi2)} on 2 degrees of freedom, ${pq(PR.joint_late.p)}). The options were to keep the production terms there, to use draft position alone, or to value those prospects at zero. Production was kept: the model was specified before the test, it is the same form as in the earlier seasons with terms leaving as their evidence runs out, and it keeps late bloomers, whose scoring is the only sign of them. Little rides on it: the star value from D+5 on is ${mil(S_["4+"].b)}.`));

// =====================================================================================================================
// 8. THE TRADE ON ONE SCALE
// =====================================================================================================================
add(H1("8. The Trade on One Scale"));
const to25 = TRD.to_2025, A_ = TRD.assets, RET = TRD.retained;
add(P(`The player model states a player's value at the cap of his valuation season, $${f1(M(CAP18))} million in 2018-19. Pacioretty's and Tatar's values are restated at the 2025-26 cap, multiplied by ${f1(CAP25M)} / ${f1(M(CAP18))} = ${f3(to25)}, and the four values are added (${T("trade")}, ${F("trade")}).`));
add(TT("trade", "The trade, each asset at the trade date"));
add(TABLE(["Asset", "Received by", "Valued by", "At the 2018-19 cap", "At the 2025-26 cap"],
  [...A_.map((a) => [a.asset, a.to === "MTL" ? "Montreal" : "Vegas", a.kind === "player" ? "Player model (Sections 2-4)" : (a.kind === "pick" ? "Pick model (Section 6)" : "Prospect model (Section 7)"), a.value_page === undefined ? "" : money(a.value_page), money(a.value)]),
   ["Total received by Montreal", "", "", "", `**${money(TRD.MTL)}**`], ["Total received by Vegas", "", "", "", `**${money(TRD.VGK)}**`]],
  [2500, 1300, 2300, 1700, 1840], [3, 4]));
add(CAPTION("Surplus value in millions of dollars. Pacioretty's value includes the four-year extension he signed with Vegas on the day of the trade. Retained salary is not in these values (below)."));
add(FIGURE("trade", "fig_trade.png", "The trade on one scale", "Each asset's surplus value at the trade date, in millions of dollars at the 2025-26 cap, by the club that received it."));
add(P(`At the trade date, both players carried contracts priced above their forecast play, so each club took on negative surplus value. Vegas received Pacioretty with the extension it chose to sign, worth ${mil(A_[0].value)}. Montreal gave up only the 2018-19 season of his old contract, worth ${mil(TRD.pacioretty_old_contract.value)}, and received ${mil(TRD.MTL)}: Tatar's ${mil(A_[1].value)}, partly offset by Suzuki's ${mil(A_[2].value)} and the pick's ${mil(A_[3].value)}.`));
add(H2("Decision: retained salary"));
add(P(`A club trading a player can keep part of his cap hit. The options were to charge the acquiring club the full cap hit, as the player model did, or to charge it only the part it carries and charge the retained part to the club that kept it. The second was decided for the back-test: a retained share is a real cost to the club that kept it and a real relief to the club that received the player, and charging it to the acquirer would misstate both sides. The retaining club pays the retained share of each remaining season of the contract being played, discounted like the contract; extensions and control seasons are not retained.`));
const mtlRet = A_[1].value + RET["Tomas Tatar"].pv_2025 + A_[2].value + A_[3].value - RET["Max Pacioretty"].pv_2025;
const vgkRet = A_[0].value + RET["Max Pacioretty"].pv_2025 - RET["Tomas Tatar"].pv_2025;
add(P(`In this trade Montreal kept $450,000 of Pacioretty's 2018-19 cap hit, ${mil(RET["Max Pacioretty"].pv_2025)} at the 2025-26 cap, and Vegas kept $500,000 of Tatar's in each of his three seasons, ${mil(RET["Tomas Tatar"].pv_2025)}. Under the rule, Montreal's side becomes ${mil(mtlRet)} and Vegas's ${mil(vgkRet)}. The rule is built and awaits adoption. Built as it stands, it reads the retained amount from the trade ledger's fields, which record Montreal's retention but not Vegas's: Tatar's appears only in the text of his row. Of the 87 traded players whose row text shows a retention, 15 have no retained amount in the fields.`));
add(H2("Decision: trades during the season"));
add(P("A player traded during the regular season has already played part of it for the club that traded him. The options were to count the whole season for the acquiring club, as the player model did, or to count only the part left. The part left was decided for the back-test, on both value and cap hit: the regular-season days left on the trade date, the trade day counted, over the season's days. The season's last day is the schedule's as published before the season, not the last game played; 2019-20's pause in March 2020 was not known before it happened, and using it would be look-ahead. A prospect keeps the full season, since his value is the surplus to the end of club control, of which the valuation season carries about 2%. This trade was made before opening night, on October 3, 2018, so the whole season was left."));
add(H2("Open: an extension signed at the trade"));
add(P(`Pacioretty's value includes the extension Vegas signed with him on the day of the trade, because it was signed on or before the valuation date. That is what Vegas acquired, but it is not what Montreal gave up, which was one season worth ${mil(TRD.pacioretty_old_contract.value)}. How the back-test counts an extension signed at a trade, on the acquiring side, the trading side, or neither, is not yet decided.`));

// =====================================================================================================================
// 9. LIMITS
// =====================================================================================================================
add(H1("9. What the Models Do Not Do"));
add(BULLET("Fitted on later seasons. The star values for picks and prospects are fitted on the 2007-2017 drafts, whose careers run past many of the trades valued, so a club at the trade could not have known them; a 2007-2017 draftee is also inside the regression that values him. The price line is fitted on contracts that started from 2018-19 to 2025-26, the control-season weights on decisions about contracts that ended from 2018-19 to 2024-25, the goaltender exit table on departures from 2018-19 to 2025-26, and the NHLe factors are one 2026 download of a table re-estimated with later seasons. Each runs past many of the trades it prices. The player forecast alone reads only seasons before the valuation season."));
add(BULLET("One price of a win. One price line prices each season of each valuation; the length premium is flat although it falls with quality, and restricted free agents are priced on the same line as unrestricted ones."));
add(BULLET("Cost of control. The arbitration price still charges first-round picks less than clubs paid them, so picks may look more valuable relative to players than they are."));
add(BULLET("Goaltenders. The forecast is flat, the goaltender price line is fitted on WAR before the pull toward the league average but prices the pulled forecast, and goaltender prospects share one star value with skaters."));
add(BULLET("Undrafted prospects. Only those on NHL contracts are valued, on a model fitted on drafted players, which assumes an undrafted player converts production as a drafted one does."));
add(BULLET("Arbitration eligibility. PuckPedia's flag is set at the contract's end, so a valuation dated earlier reads eligibility from a later date."));
add(BULLET("The trade side. Retained salary, the season left on an in-season trade, and conditional picks are decided or flagged for the back-test but not yet in the values; the draft lottery is not modelled; future picks are valued at their round's average."));

// =====================================================================================================================
// REFERENCES
// =====================================================================================================================
add(H1("References"));
add(P("Efron, B., and C. Morris. 1975. \"Data Analysis Using Stein's Estimator and Its Generalizations.\" *Journal of the American Statistical Association* 70 (350): 311-319."));
add(P("Nadaraya, E. A. 1964. \"On Estimating Regression.\" *Theory of Probability and Its Applications* 9 (1): 141-142."));
add(P("Papke, L. E., and J. M. Wooldridge. 1996. \"Econometric Methods for Fractional Response Variables with an Application to 401(k) Plan Participation Rates.\" *Journal of Applied Econometrics* 11 (6): 619-632."));
add(P("Tobin, J. 1958. \"Estimation of Relationships for Limited Dependent Variables.\" *Econometrica* 26 (1): 24-36."));
add(P("Watson, G. S. 1964. \"Smooth Regression Analysis.\" *Sankhyā, Series A* 26 (4): 359-372."));

// =====================================================================================================================
// APPENDICES
// =====================================================================================================================
add(H1("Appendix A. Games Share and Chance of Playing, Each Season Ahead"));
add(P(`The adopted regressions of ${T("gs")} and ${T("pp")} are fitted separately for each season ahead, in the 2025-26 fit. Tables A1 and A2 give each, from the valuation season (0) to five seasons ahead. The trailing games share matters less the further ahead the season, and age more.`));
const HS = ["0", "1", "2", "3", "4", "5"];
const gsA = (h) => GS[h]["+ trailing WAR (adopted)"];
add(TT("gsH", "Games share, adopted regression, by seasons ahead"));
add(TABLE(["Term", ...HS],
  [...GSROW.map(([k, lab]) => [lab, ...HS.map((h) => cc(gsA(h).terms[k], 4))]), ["R-squared", ...HS.map((h) => f3(gsA(h).r2))], ["Player-seasons", ...HS.map((h) => comma(gsA(h).n))]],
  [2140, 1250, 1250, 1250, 1250, 1250, 1250], [1, 2, 3, 4, 5, 6], new Set(), 15));
add(CAPTION("Least squares; coefficient (standard error, clustered by player) [two-sided p-value]."));
const ppA = (h) => PP[h][ppKey(h)];
add(TT("ppH", "Chance of playing, adopted regression, by seasons ahead"));
add(TABLE(["Term", ...HS],
  [...PPROW.map(([k, lab]) => [lab, ...HS.map((h) => cc(ppA(h).terms[k], 3))]), ["McFadden pseudo R-squared", ...HS.map((h) => f3(ppA(h).pseudo_r2))], ["Player-seasons", ...HS.map((h) => comma(ppA(h).n))]],
  [2140, 1250, 1250, 1250, 1250, 1250, 1250], [1, 2, 3, 4, 5, 6], new Set(), 15));
add(CAPTION("Logistic regression on the log odds; coefficient (standard error, clustered by player) [two-sided p-value]."));

add(H1("Appendix B. The Prospect Model Built Up, Each Season"));
add(P(`${T("build2")} builds the prospect model up one term at a time in D+2. Table B1 does the same for each season. Within a season each row adds a term to the row above, except the adopted rows for D+4 and from D+5 on, which leave out draft position, and from D+5 on the age discount.`));
const BR = [];
const ADLAB = { "3": "Adopted: production, its square, and age; no draft position", "4+": "Adopted: production and its square only" };
G5.forEach((g) => {
  Object.keys(BHEAD).forEach((s) => {
    const sp = B2[s][g];
    const lab = s === "adopted" && ADLAB[g] ? ADLAB[g] : BHEAD[s].replace("\n", " ").replace(/^\(\d\) /, "");
    BR.push([s === "draft position alone" ? `**${SEAS[g]}**\n${lab}` : lab, ...BROW.map(([k]) => cc(sp.terms[k], 3)), f3(sp.r2)]);
  });
});
add(TT("buildAll", "The prospect model built up one term at a time, by season"));
add(TABLE(["Season and model", "S", "P", "P²", "N", "P × (age − 18)", "R-squared"], BR, [2140, 1350, 1300, 1300, 1300, 1450, 800], [1, 2, 3, 4, 5, 6], new Set(), 15));
add(CAPTION("Each block is one season, each row one regression with the full set of season interactions and no intercept. S: star probability; P: production level; N: no production record. Coefficient (standard error, clustered by player) [two-sided p-value]; R-squared measured from zero."));

add(H1("Appendix C. The Pick Model: Other Choices"));
add(P("Each row gives a choice made in building the pick model, why it was made, and what the alternative would have done. Where an effect was measured before the arbitration cost was adopted, it is a percentage of the star value then and is marked so."));
const CH = [
  ["End of club control", "Unrestricted free agency under CBA Section 10.1(a): 27 as of June 30, or seven seasons of 40 or more games (30 for a goaltender); games played stand in for roster games", "The pick secures the player only until he can sign with any club", "PuckPedia's projected free-agency year agrees with this rule for 1,151 of the 1,183 drafted players it covers"],
  ["Price before regression", "Each drafted player's seasons are priced, then his surplus is regressed on the star probability", "Regressing WAR on draft position and pricing the prediction treats each player at a position as the average one and blurs the stars, who carry a pick's value", "-"],
  ["Length of each season's contract", "Each season priced at one year of term", "An entry-level or qualifying-offer season buys no security beyond that season", "Pricing entry-level seasons at the contract's remaining length would add about $2.6 million to a player who plays all three"],
  ["Brief call-ups", "A season under 10 NHL games has its value and cost scaled by games over 82", "A call-up's cap hit counts only for his days on the roster", "Counting each as a full season would lower the mean pick from $1.68 million to $1.50 million (qualifying-offer chain)"],
  ["Entry-level slides", "Not modelled; the entry-level contract runs by calendar from his first NHL season", "The CBA lets an 18- or 19-year-old's contract slide a year when he plays under 10 NHL games, but modelling it changes little", "Each pick's value moves by under 0.5% (qualifying-offer chain)"],
  ["Careers that lost money", "Counted as negative", "A player who holds a roster spot while delivering less than his cost was a loss to his club", "Flooring each career at zero would raise each pick's value by 4.1% (qualifying-offer chain)"],
  ["Rights that lapsed", `Zero (${PK.routes.lapsed} players); kept when he signed his entry-level contract with the drafting club (${PK.routes["signed by the drafting club"]})`, "Surplus a club never held cannot belong to its pick; a club that signed him held him", "The lapsed players held 2.2% of drafted skaters' surplus (qualifying-offer chain)"],
  ["Goaltenders", "Pooled with skaters, priced on the goaltender price line", "At a trade, nobody knows whether a pick will become a goaltender", "Goaltenders' value does not follow draft position (Holtby #93, Saros #99, Shesterkin #118); a separate goaltender star value would put a first-overall goaltender near $63 million (qualifying-offer chain)"],
  ["Drafted players who died", "Left out of every fit (Table C2)", "They never had the chance to deliver; left in, each counts as a prospect worth zero after his death", "Leaving them out moved the star value from $18.03 million to $18.04 million"],
  ["The 2017 draft's last season", "Kept", "The data end with 2025-26, which cuts 29 of the 217 players' control by one season", "Scoring each draft left out already refits without 2017"],
  ["CBA Group 6", "Not modelled", "Players 25 or older with three professional seasons and under 80 NHL games become free agents early; few drafted players qualify", "At its upper bound it lowers the star value by 0.37%"],
];
add(TT("pickChoices", "Other choices in the pick model"));
add(TABLE(["Choice", "What the model does", "Why", "What the alternative would do"], CH, [1500, 2800, 2700, 2640], [], new Set(), 15, false));
add(CAPTION("Effects marked \"qualifying-offer chain\" were measured on October 9, 2026, before the arbitration cost; the others on the model of their date."));
const DEC = [["Alexei Cherepanov", "2007, #17", "New York Rangers", "October 13, 2008"], ["Mickey Renaud", "2007, #143", "Calgary Flames", "February 18, 2008"],
  ["Bryan Rufenach", "2007, #208", "Detroit Red Wings", "June 4, 2012"], ["Scott Winkler", "2008, #89", "Dallas Stars", "June 12, 2013"],
  ["Kristians Pelss", "2010, #181", "Edmonton Oilers", "June 11, 2013"], ["Daniil Sobchenko", "2011, #166", "San Jose Sharks", "September 7, 2011"]];
add(TT("deceased", "Drafted players left out of every fit"));
add(TABLE(["Player", "Drafted", "Club", "Died"], DEC, [2600, 1500, 2700, 2400]));
add(CAPTION("Drafted players of 2007 to 2017 who never played an NHL season and died before their club's control would have ended (deceased_draftees.py, from Wikipedia's list of ice hockey players who died during their careers)."));

const doc = new Document({
  creator: "Thomas Mihaljevic", title: "Valuing Players, Draft Picks, and Prospects",
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
