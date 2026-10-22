// model_doc.js v4.1 -- builds "Valuing Players, Draft Picks, and Prospects.docx" (40_DOCS/Supervisor_Drafts/).
//
// v4.1 (2026-10-22): one phrase, as "Valuing Prospects" v3.0: the change in b offsets the change in the age term
// (v4.0: "b absorbs the difference", a personified part of the model).
// v4.0 (2026-10-22): Thomas's second round of notes on v3 (40_DOCS/Valuing_Players_Feedback.md, Round 2: 39 comments and
// his 15 text edits, carried verbatim). No earlier version of the model is described; every number names its measure;
// terms not statistically significant are dropped or their reason stated; tables for comparisons. On the model after
// 2026-10-21: the forecast audit (games share without the defenceman term, floored at 0; chance of playing without age
// squared and seasons since debut; age centred at 27.22), the re-locked price line, the whole-term pricing test, the
// goaltender rebuild, the prospect model without the no-record indicator, the 50th pick as the worked drafted player.
// v3.0 (2026-10-21): Thomas's first round of notes on v2 (40_DOCS/Valuing_Players_Feedback.md): Section 1 in general
// terms, its detail moved to where it is used; the sources introduced with what they are; no "Decision:" headings;
// performance, not play; forecasted; the terminal value; no personified model parts; nothing used before it is
// introduced (the forms of production after age). On the model as it runs after 2026-10-20: a contract signed on the
// trade date left out, retained salary and the season left adopted, each club's side as received less given up.
// v2.0 (2026-10-19): the second draft, at the level of detail of "Valuing Draft Picks" and "Valuing Prospects"
// (Thomas, 2026-10-19: keep in mind their specificity; longer is fine; graphs and tables; for each decision, why it
// had to be made, the choices, why the adopted one and why not the others; explain the statistics, the formulas and
// the terms). Every formula written in full with its discount (CLAUDE.md, 2026-10-19). On today's model: the pick curve
// after the 2026-10-18/19 fixes, the prospect fits inside club control, the back-test's three rules as decided.
// v1.0 (2026-10-16): the first draft, 20 pages.
//
// NUMBERS: every computed figure comes from OUTPUT_DIR/model_doc/numbers.json (25_TESTS/model_doc_figures.py v4.0,
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
  // starting_level_simple_test.py v1.1 (2026-10-04): the starting level's root mean squared error of WAR per 82, pulled form
  weights: { best: "50/30/20", n: 9, rmse: 1.1708, next: [["50/35/15", 1.1710], ["60/25/15", 1.1711], ["60/30/10", 1.1714]] },
  pull: { shares: [[0.45, 1.1676], [0.55, 1.1545], [0.65, 1.1502], [0.75, 1.1549]], threeWay: "0.65 / 0.35 / 0.00" },
  startStep: { with: 1.1506, without: 1.1611, wWhole: 1.3598, woWhole: 1.3689 },
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
  // the price line, start- against signing-dated (xnpv1_price_line.py v2.3 on skater_forecast v2.4, 2026-10-21)
  ll: { startFree: 3986.6, signFree: 3982.5, startIn: 4624.7, signIn: 4628.7 },
  // goaltenders (25_TESTS/goalie_review.py v1.0, goalie_play_spec.py v1.0, goalie_line_check.py v1.0, 2026-10-21)
  gPersist: { g: [0.209, 0.123, 0.291, 776, 152], s: [0.586, 0.558, 0.612, 10049, 1815], gRate: 0.113, sRate: 0.575, gTrail: 0.234, sTrail: 0.627 },
  gAge: { base: 7.3294, lin: 7.2070, linP: 0.022, quad: 7.1933, quadP: 0.023, slope: -0.0954, n: 928, goalies: 183 },
  gPull: { kept: 0.35, mse: 7.3294, at30: 7.3488, at40: 7.3302, gp10: [7.5670, 7.5476], target: 2.318 },
  gLine: { asRuns: 1.962, bias: 0.519, flat: 1.119, aged: 1.273, agedBeta: 1.274, agedGamma: 0.914 },
  gPlay: { rows: 3307, played0: 0.818, played5: 0.430, fc0: 0.815, fc5: 0.413, ll: 0.4850, llNoSq: 0.4845, sqP: [0.370, 0.981] },
  gControl: { p: 0.519 },
  // the whole-term pricing test (term_average_price_line.py v1.0, 2026-10-21): log-likelihood, held-out error ($M)
  // the 10-game counting season and the games weighting (forecast_term_audit.py v1.2): read from numbers.json
  // price-line specification tests (price_line_spec_tests.py v1.0-v1.1, 2026-10-05, on that day's line, 2,296 contracts;
  // held-out root mean squared error of the cap hit, $M at the 2025-26 cap, five-fold player splits repeated 20 times)
  spec: [["The adopted price line", "-", "1.2809", "-"],
         ["A separate line for restricted free agents", "+7.9 (p = 0.0034)", "1.2787", "20 of 20"],
         ["A premium that varies by forecast group", "+18.5 (p < 0.001)", "1.2712", "20 of 20"],
         ["A higher premium below replacement level (one step)", "+16.0 (p < 0.001)", "1.2718", "20 of 20"],
         ["The premium times the forecast", "+5.5 (p = 0.0009)", "1.2755", "20 of 20"],
         ["A squared forecast term", "+4.1 (p = 0.0042)", "1.2809", "12 of 20"],
         ["A bend at one forecasted win", "+1.7 (p = 0.064)", "1.2817", "2 of 20"],
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
const TABS = ["terms", "start", "comps", "departures", "gs", "gsform", "pp", "drops", "pl", "termavg", "term", "spec", "control", "pac", "goalie", "gv", "point",
  "shapes", "nested", "pickvals", "pstar", "fade", "prod", "age", "ageform", "forms", "adopted", "build2", "suzuki", "top10", "trade", "sides"];
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
add(P("An NHL trade exchanges assets of different kinds: players under contract, draft picks, and prospects who have not yet reached the NHL. To judge whether a club received more than it gave, each asset has to be valued in one currency, as of the trade date. This document explains how each of the three kinds of asset is valued and are put on a comparable scale. Each step says what it does and why; where a choice had to be made, it says what the options were, which was chosen, and why the others were not."));
add(P("One real-life trade is used as an example throughout this document to demonstrate how the model values real assets. On September 10, 2018, the Montreal Canadiens traded Max Pacioretty to the Vegas Golden Knights for Tomas Tatar, Nick Suzuki, and a 2019 second-round pick. Pacioretty and Tatar were players under contract, Suzuki was a prospect drafted 13th overall in 2017, and the draft pick originally belonged to Columbus, which Vegas acquired from a previous transaction."));
add(H2("The data and their sources"));
add(P("Performance is measured throughout by wins above replacement (WAR): the wins a player added to his team in a season, compared with what a replacement-level player would have added in the same minutes. A replacement-level player is one a club can sign or call up at about the league minimum at any time; in the WAR metric used here, a forward outside his team's top 13 in ice time or a defenceman outside its top 7. WAR suits this model because it states each part of a player's game, at each position, in wins, the unit a club buys with cap room."));
add(P("The WAR comes from Patrick Bacon, a data scientist who has published hockey models as TopDownHockey since late 2020 and co-founded HockeyStats.com, where his WAR, NHL equivalency, and draft models are published with their methods. His WAR is built from the NHL's play-by-play and shift records in six parts: even-strength offence and defence, power-play offence, penalty-kill defence, penalties drawn and taken, and shooting. The even-strength and special-teams parts come from a weighted ridge regression that estimates each player's effect on his team's expected goals for and against while separating him from his teammates and opponents (regularized adjusted plus-minus). Shooting is goals scored above expected goals, and goals are converted to wins at about five goals a win, set each season."));
add(P("Three things make it a credible source for this model. Its method is published in full (hockeystats.com/methodology/war). At the team level, WAR accounts for 82% of the variation in standings points, by Bacon's own validation. And it is free, public, and available for each NHL skater and goaltender season from 2007-08 on, so each traded player can be valued and the values can be reproduced. Bacon also states its limits: it probably weights shooting too heavily against driving play, and it may miss part of a passer's value. Section 5 checks the forecast against a measure built without it."));
add(P("Bacon also supplies the two inputs that come from outside the NHL: the NHL equivalency factors that put a prospect's scoring in other leagues on one scale (Section 7), and the star probability for each draft position (Section 6)."));
add(P("Contracts, cap hits, and the trade ledger come from PuckPedia, a salary-cap database that records each NHL contract's terms, its cap hit by season, its clauses and arbitration eligibility, and each trade's assets and retained salary; it has been one of the main public sources of NHL contract data since CapFriendly closed in 2024. Cap hits of contracts that ended before 2018-19, which PuckPedia's export does not hold, come from CapWages, a second public cap database. Scoring outside the NHL comes from Elite Prospects, the largest public database of player statistics across junior, college, and professional leagues worldwide. Long-term injured reserve comes from Spotrac's injured-reserve log, a public record of each season's injured players and their reserve status. The draft comes from the NHL's own draft records, and the records behind Game Value, the independent measure of Section 5, from the NHL's play-by-play and shift data. Table 1 defines the terms this document uses."));
add(TT("terms", "Model terms"));
const GLOSS = [
  ["Surplus value", "The market price of the performance an asset delivers to its club, less what the club pays for it, summed over the seasons the club controls the asset and discounted 3% a year; \"surplus\" for short."],
  ["Cap hit", "A contract's charge against the salary cap in a season: its average annual value."],
  ["WAR", "Bacon's wins above replacement for a season: the wins a player added over a replacement-level player in the same minutes. WAR per 82 is the same scaled to 82 games."],
  ["Valuation season", "The season in which an asset is valued, starting July 1. A trade during a season is valued in that season; a trade after its last regular-season game, in the next one."],
  ["Valuation date", "The date an asset is valued at: for a traded asset, the trade date."],
  ["Forecasted WAR if he plays", "The forecast of a player's WAR per 82 in a season, times his forecasted games share."],
  ["Games share", "The share of his team's 82 games a player plays, if he plays at all."],
  ["Chance of playing", "The probability that a player plays at least one NHL game in a season."],
  ["Comparable players", "Players of the same position and age whose style, ice time, level, and trend were closest to his, each weighted by how close."],
  ["Root mean squared error", "A forecast's typical miss: the square root of the average squared difference between forecast and outcome, in the outcome's units (WAR per 82, wins, or dollars); lower is better."],
  ["One-sided p (redraws)", "The share of 2,000 redraws, with replacement, of whole careers (or drafts) in which one version's summed error is not lower than another's: how often the data could reverse the comparison. Below 0.05, the difference is statistically significant at the 5% level."],
  ["Price line", "The regression of cap hit on forecasted WAR if he plays, position, and contract length: the market price of a season."],
  ["Term", "A contract's length in years. A season's price uses the term left at the valuation date."],
  ["Control seasons", "The seasons after a contract ends in restricted free agency, until the player can become an unrestricted free agent."],
  ["Terminal value", "The value of the control seasons: the surplus of the seasons the club controls after the contract ends."],
  ["Qualifying offer", "The one-year offer, set by the collective bargaining agreement (CBA) from the player's prior salary, that keeps a restricted free agent's rights."],
  ["Arbitration price", "Once a player is eligible for salary arbitration, the higher of his qualifying offer and the price line's price of his forecasted performance for that season."],
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

// =====================================================================================================================
// 1. THE COMMON CURRENCY
// =====================================================================================================================
add(H1("1. Surplus Value"));
add(P("A club holds an asset only for a finite period of time, either determined by contract length or determined through the NHL's CBA. A player under contract delivers performance in each of those seasons, and the market price of that performance is what clubs pay for it in the market for players. A draft pick or a prospect delivers nothing until its player reaches the NHL; its value is the performance its player is expected to deliver once he does. In each season the club also pays the player's cap hit, the charge his contract makes against the salary cap, whether that contract is an entry-level contract, a qualifying offer, or a negotiated deal. The asset's value to the club is the surplus value it delivers beyond what it costs."));
add(P("Under a salary cap ensuring that extracting proper value out of assets is critical, because a club that pays a player less than the market would charge for his performance keeps the difference in cap space, and cap space can buy additional wins through investing it in more players. A player who costs exactly his market price adds nothing a club could not have bought on the open market."));
add(P("Surplus value is defined as follows, summed over the seasons the club controls the asset, counted from the valuation season (k = 0):"));
add(EQ(["surplus = Σ (", ["_", "V", "k"], " − ", ["_", "C", "k"], ") / ", ["^", "1.03", "k"]]));
add(P("V_k is the market price of the performance delivered in season k, and C_k is the cap hit paid for it, both in that season's dollars; dividing by 1.03^k discounts season k at 3% a year. The models differ in how V and C are obtained: for a player under contract, from a forecast of his performance (Sections 2 to 4); for a pick or a prospect, from what drafted players went on to deliver (Sections 6 and 7)."));
add(H2("Cap growth and discounting"));
add(P(`Prices are measured as shares of the salary cap, because the cap sets what a club can spend: a $5 million cap hit was 6.3% of the 2018-19 cap of $${f1(M(CAP18))} million and 5.2% of the 2025-26 cap of $${f1(CAP25M)} million. The cap is projected to grow 3% a year from the valuation season's cap, so a season priced at a share s of the cap is worth s × cap × 1.03^k in that season's dollars. Discounting, done by dividing by 1.03^k returns it to s × cap: on the value side, cap growth and discounting cancel. A cap hit is in fixed dollars, so on the cost side discounting is present: a $5 million cap hit four seasons out counts as $5 million / 1.03^4 = $4.44 million today, because it takes a smaller share of a larger cap.`));
add(H2("The discount rate"));
add(P("Future seasons have to be discounted at some rate, and salary cap growth has to be projected at some rate. The options were one rate for both (adopted, at 3%); a discount rate above cap growth; no discounting; or a rate that reflects how impatient clubs are."));
add(P("One rate for both was adopted because it makes a share of the cap mean the same in any season: a season's worth of performance is worth the same share of the cap whenever it comes, and only a fixed-dollar cost becomes cheaper with time. A higher discount rate would make waiting for a prospect costly, and it would need evidence that clubs value future cap room less than present cap room, which the data do not provide. No discounting would ignore that a fixed cap hit takes a smaller share of a growing cap. A rate for clubs' impatience was rejected for a different reason: whether clubs are impatient is one of the questions the trade study is built to answer, so it cannot be built into the values it tests."));
add(P("The cost of this choice is that 3% is a planning assumption. The cap grew 3.4% a year from 2015-16 to 2019-20, 0.6% a year through 2023-24, and 7.6% a year from 2023-24 to 2026-27. The rate matters most for long contracts at a flat cap hit, where it sets how much cheaper the later seasons become: an eight-year contract at a flat cap hit equal to its first season's value gains $6.16 million at 3%, $9.71 million at 5%, and $13.77 million at 7.6%."));
add(H2("What the three models share"));
add(P("The three models share the price of a win and the cost rules. Each season is priced on one price line, estimated from what clubs paid for players' forecasted performance (Section 3), and costed by the same rules from the collective bargaining agreement (CBA; Section 4). Because both are shared, a player, a pick, and a prospect are measured in the same currency and can be added together."));

// =====================================================================================================================
// 2. THE FORECAST
// =====================================================================================================================
add(H1("2. Players Under Contract: Forecasting Performance"));
add(P("A contract commits a club to a cap hit for each of its seasons, and what the club receives is the player's performance in seasons not yet played. For seasons k = 0, 1, 2, ... of his contract:"));
add(EQ(["value = Σ (", ["_", "p", "k"], " × ", ["_", "V", "k"], " − ", ["_", "C", "k"], ") / ", ["^", "1.03", "k"], "  +  terminal value"]));
add(P("Here p_k is his chance of playing in season k, V_k is the market price of his forecasted performance in that season if he plays, and C_k is his cap hit. The terminal value is the value of the seasons his club controls after the contract ends (Section 4). This section builds the forecast behind p and V; Section 3 prices it, and Section 4 adds up the contract and the terminal value."));
add(P("The forecast has three parts for each season ahead k: his WAR per 82 games if he plays, r_k; his games share if he plays, g_k; and his chance of playing, p_k. His forecasted WAR if he plays is w_k = r_k × g_k, and V_k is the price of w_k. Each part is re-estimated for every valuation season using only seasons completed before it. The fits shown in this document are those for 2025-26, estimated on seasons through 2024-25. A season counts as evidence of a player's ability when he played 10 or more games in it, and WAR in the shortened 2019-20 and 2020-21 seasons is scaled to 82 games. Ages are taken on September 15 of the season's first year, the date the CBA uses."));
add(H2("The starting level"));
add(P("A single season of WAR is a noisy measure of a player's ability: a hot shooting season or an injury can influence it greatly. The forecast's starting level is therefore his three most recent seasons, pulled toward the level of players similar to him:"));
add(EQ(["starting level = 0.65 × own rate + 0.35 × comparable players' level + aging"]));
add(EQ(["own rate = (0.5 × ", ["_", "G", "1"], " × ", ["_", "r", "1"], " + 0.3 × ", ["_", "G", "2"], " × ", ["_", "r", "2"], " + 0.2 × ", ["_", "G", "3"], " × ", ["_", "r", "3"], ") / (0.5 × ", ["_", "G", "1"], " + 0.3 × ", ["_", "G", "2"], " + 0.2 × ", ["_", "G", "3"], ")"]));
add(P("In the own rate, r_1 is his WAR per 82 games in the most recent season before the valuation season and G_1 his games in it, r_2 and G_2 the season before that, and r_3 and G_3 the one before that; only seasons of 10 or more games count, and a missing season drops out of both sums. Each season's 50/30/20 weight is multiplied by its games, so a 20-game season counts for less than a full one. Comparable players' level, defined below, is measured at the age of his most recent counted season. Aging is the comparable players' change in level from that age to the valuation season."));
const own = PAC.own_seasons;
add(P(`For Pacioretty at the trade, his three seasons before 2018-19 were ${listAnd(own.map((s) => `${f2(s.WAR_82)} WAR per 82 in ${s.syr}-${String(s.syr + 1).slice(2)} (${s.GP} games)`))}. His own rate is (0.5 × ${own[2].GP} × ${f2(own[2].WAR_82)} + 0.3 × ${own[1].GP} × ${f2(own[1].WAR_82)} + 0.2 × ${own[0].GP} × ${f2(own[0].WAR_82)}) / (0.5 × ${own[2].GP} + 0.3 × ${own[1].GP} + 0.2 × ${own[0].GP}) = ${f3(PAC.own_82)}. His comparable players' level at ${PAC.age_last} is ${f3(PAC.comparables_level)}, and their change from ${PAC.age_last} to ${PAC.age_last + PAC.last_lag} is ${f3(PAC.path[PAC.last_lag])}. Therefore, his starting level is 0.65 × ${f3(PAC.own_82)} + 0.35 × ${f3(PAC.comparables_level)} − ${f3(Math.abs(PAC.path[PAC.last_lag]))} = ${f3(PAC.start)} WAR per 82. His poor 2017-18 season and his comparable players both pull him below his two earlier seasons.`));
add(H2("The starting level's decisions"));
const AU = Object.fromEntries(N.audit.all.map((r) => [r.version, r]));
const AUC = Object.fromEntries(N.audit.common.map((r) => [r.version, r]));
const R1 = AU["R1 no games weighting"], R2 = AU["R2 counting season at 5 games"], R3 = AUC["R3 counting season at 20 games"], B0 = AU.base, B0c = AUC.base;
add(P(`The starting level required five decisions: how to weight his recent seasons, how to treat seasons with few games, how far to pull him toward similar players, how to move him from his most recent season to the valuation season, and how many games make a season count. Each decision was evaluated using the forecast's error: the root mean squared error of WAR per 82 against what he went on to deliver, on the valuation seasons 2015-16 to 2021-22 (${T("start")}).`));
add(TT("start", "The starting level's decisions"));
add(TABLE(["Decision", "Adopted", "Alternatives", "Why the adopted one", "Evidence (root mean squared error)"],
  [["Weights on his recent seasons", "50/30/20 over three seasons", "60/40 over two seasons; eight other fixed three-season weightings", `Of the ${REC.weights.n} three-season weightings tested, 50/30/20 had the lowest error, and fixed weights need nothing estimated from the data`, `Starting level, WAR per 82: 50/30/20 ${f4(REC.weights.rmse)}; next best ${REC.weights.next.map(([w, e]) => `${w} ${f4(e)}`).join(", ")}`],
   ["Seasons with few games", "Each season's weight times its games", "Plain 50/30/20 on the three rates, the same on both sides of the blend", "A 20-game season says less than a full one, and the forecast is significantly more accurate with the games weighting", `Starting level ${f4(B0.start)} against ${f4(R1.start)}; one to five seasons ahead ${f4(B0.whole)} against ${f4(R1.whole)} (WAR per 82); season WAR ${f4(B0.war)} against ${f4(R1.war)} wins (p = ${f3(R1.p_build_better_war)})`],
   ["Pull toward similar players", "Keep 65% of his own rate, 35% his comparable players", "Other shares; a three-way blend adding the league average", "The share with the lowest error; the three-way blend put no weight on the league average", `Starting level, WAR per 82, by share kept: ${REC.pull.shares.map(([k, e]) => `${Math.round(100 * k)}% ${f4(e)}`).join(", ")}; best three-way blend ${REC.pull.threeWay}`],
   ["From his most recent season to the valuation season", "Add his comparable players' change over the gap", "No step: start at his most recent season's level", "A player a year older has aged a year", `Starting level, WAR per 82: ${f4(REC.startStep.with)} against ${f4(REC.startStep.without)}; one to five seasons ahead ${f4(REC.startStep.wWhole)} against ${f4(REC.startStep.woWhole)}`],
   ["Fewer than three seasons", "Rescale the weights over the seasons he has", "Count a missing season as zero", "A missing NHL season is not replacement-level performance: it may be junior, the AHL, or an injury", "Not scored: a design choice"],
   ["A counting season", "10 or more NHL games", "5 or 20 games", "Ten games is the line the CBA draws for a season of an entry-level contract; 20 forecasts worse, and 5 would move players whose recent seasons were all shorter than 10 games out of the prospect model, a change not tested", `Season WAR, wins: 10 games ${f4(B0.war)}, 5 games ${f4(R2.war)} (p = ${f3(R2.p_version_better_war)}); on the rows 20 games can forecast, 10 games ${f4(B0c.war)}, 20 games ${f4(R3.war)} (p = ${f3(R3.p_build_better_war)})`]],
  [1450, 1500, 1800, 2400, 2490], [], new Set(), 15));
add(CAPTION(`Root mean squared error of the forecast against what the player went on to deliver, valuation seasons 2015-16 to 2021-22: the starting level and one to five seasons ahead in WAR per 82, season WAR (the chance of playing × WAR per 82 × games share against his season's WAR) in wins. The weights, the pull, and the step were measured on October 4 and 5, 2026 (starting_level_simple_test.py, aging_investigations_abc.py), each against its own baseline that day; the games weighting and the counting season on October 21, 2026, on the model as it now runs (forecast_term_audit.py, ${comma(N.audit.rows_all)} player-seasons; ${comma(N.audit.rows_common)} for 20 games, which cannot forecast the rest). p is one-sided, from 2,000 redraws of careers: the share of redraws in which the comparison is reversed.`));

add(H2("Comparable players"));
add(P(`To find players similar to him, each player-season is described by four attributes: how his WAR divides among five components (even-strength offence, even-strength defence, power play, penalty kill, and shooting), his ice time per game, his level, and his trend. His level is his 50/30/20 WAR per 82 at that age, games-weighted as above, over seasons of 20 or more games; his trend is the change in his rate between his two most recent seasons. Each attribute is standardized within position (each measure minus its mean, divided by its standard deviation, so that minutes and wins are on one scale) and given equal weight, so the five style shares together share a quarter of the weight and the remaining attributes share a quarter each. The candidates are other players of the same position at the same age, in seasons before the valuation season. Each candidate's weight falls with his distance d from the player, the square root of the summed squared differences across the attributes:`));
add(EQ(["weight = exp(−", ["^", "d", "2"], " / 2", ["^", "h", "2"], ")"]));
add(P(`where h, the yardstick, is the median distance between two players of the same position (${f2(AG.yardstick.F)} for forwards and ${f2(AG.yardstick.D)} for defencemen in the 2025-26 fit). An exact match gets weight 1, a candidate one yardstick away exp(−0.5) = 0.61, and one two yardsticks away exp(−2) = 0.14. This is kernel weighting (Nadaraya 1964; Watson 1964): an average in which closer cases count more, with no fixed number of neighbours. Pacioretty's ${PAC.comparables.n_at_age} candidates at ${PAC.age_last} carry weights that sum to ${f1(PAC.comparables.weight_sum)}; ${T("comps")} lists his five closest.`));
add(TT("comps", `Max Pacioretty's five closest comparable players at ${PAC.age_last}`));
add(TABLE(["Player", "Weight", `Level at ${PAC.age_last} (WAR per 82)`],
  PAC.comparables.top.map((c) => [c.name, f2(c.weight), f3(c.level)]), [4000, 2500, 3100], [1, 2]));
add(CAPTION(`Weight: exp(−d² / 2h²), 1 for an exact match. Level: each comparable player's 50/30/20 WAR per 82 at that age, games-weighted. Of Pacioretty's ${PAC.comparables.n_at_age} candidates.`));
add(P("A few close matches, or many distant ones, could give an extreme average. The league average for the player's position and age is therefore included alongside the comparable players with a weight of 10:"));
add(EQ(["comparable players' level = (Σ ", ["_", "w", "i"], ["_", "L", "i"], " + 10 × league level) / (Σ ", ["_", "w", "i"], " + 10)"]));
add(P(`where w is each candidate's weight and L his level at that age. Pulling a noisy average toward a group mean in this way lowers its expected error (Efron and Morris 1975). For Pacioretty, his candidates' weighted level of ${f3(PAC.comparables.weighted_mean_level)} and the league level for forwards at ${PAC.age_last} of ${f3(PAC.comparables.league_level)} give ${f3(PAC.comparables_level)}; with weights summing to ${f1(PAC.comparables.weight_sum)}, the league average makes up ${pct(10 / (PAC.comparables.weight_sum + 10))} of it.`));
add(H2("Weighting comparable players"));
add(P(`Three settings govern the weights. The yardstick could be one median for all players or one for each position. One for each position was adopted: measured on October 5, 2026, it lowered the forecast's error by less than 0.0001 WAR per 82 (${REC.base[1]} one to five seasons ahead for both, at four decimals), but it was lower in nearly every redraw of careers, the players resampled 2,000 times with replacement (one-sided p = ${REC.A1p[0]} for the starting level, ${REC.A1p[1]} one to five seasons ahead, and ${REC.A1p[2]} for season WAR). The yardstick is the median distance between pairs of player-seasons; whether pairs of two seasons by the same player should count toward that median was also tested, and it changed no error at four decimals, so it was dropped. A player is never one of his own comparable players.`));
add(P(`The weight of ten on the league average is a judgement call. Removing it (comparable players alone) left the starting level unchanged but made the forecast one to five seasons ahead worse, a root mean squared error of ${REC.B1[1]} WAR per 82 against ${REC.base[1]} (one-sided p < 0.001 that the weight of ten is better), most for players under 22 (${REC.B1under22[0]} against ${REC.B1under22[1]}), whose comparable players are few. An earlier sweep of the weight from 0.01 to 50 moved the forecast's error by at most 0.16%. `));

add(H2("Aging"));
add(P("Players change with age, and how much depends on the player. The starting level is carried forward one season at a time. At each age step, the same pool of comparable players, chosen at his most recent counted age, provides its average change in performance from one age to the next, blended with the league-average change at a weight of ten as above. The change in WAR per 82 is used, not the comparable players' level itself, and those average changes are added to or subtracted from his starting level."));
add(P(`A player who leaves the league records no decline. If departures were left out, the average change at older ages would come only from players good enough to stay, and the forecast would understate aging. A player who leaves the NHL for good is therefore given one more season at replacement level (WAR 0), at his own most recent season's games, so his departure counts as a decline. In the 2025-26 fit, ${comma(AG.imputed)} departures enter this way among ${comma(AG.careers)} careers.`));
add(P(`On average a forward improves until 24 and declines after it, by about ${f2(-gd("F", 29))} WAR per 82 from 29 to 30 and ${f2(-gd("F", 34))} from 34 to 35 (${F("aging")}, left). Pacioretty's comparable players declined slightly faster than the league average, and his forecast falls from ${f2(PAC.forecast_path[0].rate_82)} WAR per 82 at 29 to ${f2(PAC.forecast_path[4].rate_82)} at 33 (${F("aging")}, right).`));
add(FIGURE("aging", "fig_aging.png", "Aging",
  `Left: the league-average change in level from one age to the next, by position, in the 2025-26 fit, with departures entered at replacement level; each point is drawn at the age reached. Right: Max Pacioretty's forecasted WAR per 82 at the trade, from his comparable players' changes (blue) and, for comparison, from the league-average changes for forwards (orange); grey points are his three seasons before the trade.`));
add(H2("Departed players in the aging curve"));
add(P(`The level given to a departed player's missing season had to be set, and three details decided. ${T("departures")} gives each version's error. Three levels other than replacement were tested: 0.50 and 0.25 WAR per 82 below it, and 0.25 above it. The level 0.25 above replacement gave a lower error one to five seasons ahead and on season WAR, and a higher error at the start. The error was still falling at the highest level tested, so the test does not identify a best level. Zero was kept on principle rather than on the data: replacement level is what a club gets from the player it calls up in his place. A player who misses a season and comes back later is not a departure, since his return shows he was not finished, and a departed season counts his own most recent season's games rather than a full 82. Filling in no departures at all was a wash on season WAR and much worse for players 35 and older, the group it exists for.`));
add(TT("departures", "Departed players in the aging curve: each version's forecast error"));
add(TABLE(["Version", "Starting level", "One to five seasons ahead", "Season WAR"],
  REC.C.map((r) => [r[0], f4(r[1]), f4(r[2]), f4(r[3])]), [4440, 1700, 1800, 1700], [1, 2, 3], new Set(), 16));
add(CAPTION(`Root mean squared error on the valuation seasons 2015-16 to 2021-22, 40,510 player-seasons, measured October 5, 2026 (aging_investigations_abc.py v1.0) on the model of that day. Each row changes one setting against the first. The starting level and the rate one to five seasons ahead are in WAR per 82; season WAR, in wins, combines the rate, the games share, and the chance of playing. Players who came back were filled in at zero before (one-sided p < 0.001 that leaving them out is better); the departed season at his own games, p = 0.033 one to five seasons ahead.`));

add(H2("Games share"));
const gsSpecs = Object.keys(GS["0"]);
const GSROW = [["tr_gp_share", "Trailing games share"], ["exp_seasons", "NHL seasons since his debut"], ["age_c", "Age − 27.22"], ["age_c2", "(Age − 27.22)²"], ["tw_WAR", "Trailing WAR"], ["intercept", "Intercept"]];
const ageTurn = 27.22 - adoptedGS.terms.age_c.b / (2 * adoptedGS.terms.age_c2.b);
add(P("WAR accumulates with games, so the forecast needs the share of the 82 games he will play if he plays at all. A regression for each season ahead estimates it from his trailing games share, his trailing WAR, his NHL seasons since his debut, and his age at the valuation season and its square. The two trailing measures are his 50/30/20 averages over seasons of 10 or more games, without the games weighting, because a games share already counts games:"));
add(EQ(["games share = a + ", ["_", "b", "1"], " × trailing games share + ", ["_", "b", "2"], " × seasons since debut + ", ["_", "b", "3"], " × (age − 27.22) + ", ["_", "b", "4"], " × ", ["^", "(age − 27.22)", "2"], " + ", ["_", "b", "5"], " × trailing WAR"]));
const DROP_GS = N.audit.insample.filter((r) => r.model === "games share" && r.term === "is_D");
add(P(`Age enters less 27.22, the average age of the player-seasons in the 2025-26 fit. Centring changes no forecast: it makes the intercept the games share of a player of average age. With its square, the effect of age can bend: the share falls with age at a rate that changes, and the bottom of that curve falls at about ${Math.round(ageTurn)}. The forecast is capped at 1 and floored at 0, the limits of a share; on the valuation seasons 2015-16 to 2021-22, ${comma(N.audit.above_cap)} of ${comma(N.audit.shares)} forecasts (${pct(N.audit.above_cap / N.audit.shares)}) reach the cap and none falls below 0.05. ${T("gs")} builds the regression for the valuation season up one term at a time, in the 2025-26 fit; Appendix A gives the adopted regression for each season ahead. The trailing games share accounts for most of the fit (R-squared ${f3(GS["0"]["games share"].r2)} alone, ${f3(adoptedGS.r2)} adopted). Each win of trailing WAR adds ${f1(100 * adoptedGS.terms.tw_WAR.b)} percentage points of games, about ${f1(82 * adoptedGS.terms.tw_WAR.b)} games: better players play more. Position is not in the regression: beside trailing WAR, a defenceman term was not statistically significant at the 5% level in any of the ${DROP_GS.length} seasons ahead fitted (p from ${f3(Math.min(...DROP_GS.map((r) => r.p)))} to ${f3(Math.max(...DROP_GS.map((r) => r.p)))}), and dropping it left the forecast's error unchanged (${T("drops")}).`));
const GSHEAD = { "games share": "Trailing games\nshare alone", "+ seasons since debut": "+ seasons since\ndebut", "+ age, age squared": "+ age, age\nsquared", "+ trailing WAR (adopted)": "+ trailing WAR\n(adopted)" };
add(TT("gs", "Games share in the valuation season, built up one term at a time"));
add(TABLE(["Term", ...gsSpecs.map((s) => GSHEAD[s])],
  [...GSROW.map(([k, lab]) => [lab, ...gsSpecs.map((s) => cc(GS["0"][s].terms[k], 4))]),
   ["R-squared", ...gsSpecs.map((s) => f3(GS["0"][s].r2))]],
  [2140, 1875, 1875, 1875, 1875], [1, 2, 3, 4]));
add(CAPTION(`Least squares on ${comma(adoptedGS.n)} player-seasons by ${comma(adoptedGS.players)} players: each player's trailing inputs at a valuation season from 2008-09 to 2024-25, and his games share in that season, among seasons he played. Coefficient (standard error, clustered by player) [two-sided p-value]. The adopted column is the model's fit, coefficient for coefficient.`));
add(H2("The form of the games-share regression"));
add(P(`A games share lies between 0 and 1, and a straight line can predict outside that range, which is why the forecast is capped. ${T("gsform")} sets out the alternatives tested. A fractional logit (Papke and Wooldridge 1996), a logistic curve fitted to the share so that every prediction lies between 0 and 1, fitted the share better but made season WAR worse, because it predicts worse where the forecast matters most, for regulars who play most of the season. Adding age squared to the straight line improved both and was adopted. The player's quality enters as his trailing WAR total rather than his rate per 82, because the question is whether and how much he plays, and his total already reflects how much he played; a term for trailing WAR above one win helped the share but cost season WAR.`));
add(TT("gsform", "The form of the games-share regression: each version's error"));
add(TABLE(["Test", "Version", "Games share", "Season WAR", "One-sided p"],
  [["Form", "Straight line (the baseline that day)", f4(REC.D.buildShare), f4(REC.D.buildWar), "-"],
   ["", "Fractional logit", f4(REC.D.logitShare), f4(REC.D.logitWar), "-"],
   ["", "Straight line + age squared (adopted)", f4(REC.D.sqShare), f4(REC.D.sqWar), `${REC.D.sqP[0]} / ${REC.D.sqP[1]}`],
   ["Quality", "Trailing WAR total (adopted)", "", f4(REC.unif.total), "-"],
   ["", "Trailing WAR rate per 82", "", f4(REC.unif.rate), `${REC.unif.pRate} (rate better)`],
   ["", "Total + a term for trailing WAR above one win", "", f4(REC.unif.totalTerm), `${REC.unif.pTerm} (without it better)`]],
  [1100, 3700, 1400, 1500, 1940], [2, 3], new Set(), 16));
add(CAPTION("Root mean squared error on the valuation seasons 2015-16 to 2021-22, measured October 5, 2026 (games_and_playing_de.py, war_input_uniformity_test.py), each test against its own baseline that day: games share in share of 82 games, season WAR in wins. One-sided p from 2,000 redraws of careers that the adopted version is better (games share / season WAR), unless the cell says otherwise."));

add(H2("Chance of playing"));
const uc = adoptedPP.terms.under_contract;
add(P("A contract costs its cap hit whether or not the player plays, but his value accrues only if he does. The chance he plays at least one NHL game in a season is a logistic regression for each season ahead. Its inputs are his age in that season, his trailing WAR and games share, his position, and whether he is under contract for that season on a deal signed by the valuation date:"));
add(EQ(["log( p / (1 − p) ) = a + ", ["_", "c", "1"], " × (age − 27.22) + ", ["_", "c", "2"], " × trailing WAR + ", ["_", "c", "3"], " × trailing games share + ", ["_", "c", "4"], " × defenceman + ", ["_", "c", "5"], " × under contract + ", ["_", "c", "6"], " × no contract record"]));
add(P(`The left side is the log of the odds of playing; a coefficient is the change in those log odds for one more unit of its input, and e raised to a coefficient multiplies the odds. Contract status is visible only from 2018-19, when the contract records start, so an indicator, no contract record, marks the earlier seasons; without it they would read as seasons without a contract. ${T("pp")} builds the regression for the valuation season up one term at a time. Being under contract for the season multiplies the odds of playing by e^${f2(uc.b)} = ${f1(Math.exp(uc.b))} (${pq(uc.p)}), and each win of trailing WAR by ${f2(Math.exp(adoptedPP.terms.level.b))}. Contract status is read at the valuation date. For a traded player, a contract signed on the trade date itself is left out, as it is from the contract's value (Section 8).`));
const ppSpecs = Object.keys(PP["0"]);
const PPROW = [["age", "Age − 27.22"], ["level", "Trailing WAR"], ["gp_share", "Trailing games share"], ["is_D", "Defenceman"], ["under_contract", "Under contract for the season"], ["contract_unknown", "No contract record (season before 2018-19)"], ["intercept", "Intercept"]];
add(TT("pp", "Chance of playing in the valuation season, built up one term at a time"));
add(TABLE(["Term", "Age alone", "+ trailing WAR, games\nshare, defenceman", "+ contract status\n(adopted)"],
  [...PPROW.map(([k, lab]) => [lab, ...ppSpecs.map((s) => cc(PP["0"][s].terms[k], 3))]),
   ["McFadden pseudo R-squared", ...ppSpecs.map((s) => f3(PP["0"][s].pseudo_r2))],
   ["Log-likelihood", ...ppSpecs.map((s) => comma(Math.round(PP["0"][s].loglik)))]],
  [2640, 2330, 2330, 2340], [1, 2, 3]));
add(CAPTION(`Logistic regression on ${comma(adoptedPP.n)} player-seasons by ${comma(adoptedPP.players)} players (valuation seasons 2008-09 to 2024-25), ${pct(adoptedPP.base)} of whom played. Coefficient on the log odds (standard error, clustered by player) [two-sided p-value]. McFadden's pseudo R-squared is one minus the fit's log-likelihood over that of a model with the intercept alone; higher is better. The model's own fit adds a negligible penalty (1e-4) against perfectly predicted outcomes; its coefficients differ from these by at most ${adoptedPP.gap_to_page_fit.toExponential(0)}.`));
add(P("Each season ahead has its own chance of playing, so a player can be absent one season and back the next, and the rate if he plays is multiplied by that season's chance once. The event is one NHL game or more, while a season counts as evidence of ability only at 10 games. The two questions differ: whether a past season is good evidence of a player's rate, and whether he is in the NHL at all in a future season. The chance of playing is multiplied by the rate if he plays, so the two must describe the same event; any season with a game is a season he played."));
add(P(`Of the yes-or-no inputs, contract status moves the odds the most, and two questions about it were tested. The first was when to read it. Reading a contract's status at its signing rather than at July 1 of its first season matters for the 884 contracts signed after July 1. Read at July 1, a contract signed later in the summer is not yet in the data: their mean chance of playing was ${REC.E.e2.julyMean}, against the ${REC.E.e2.played} who actually played. Read at the signing, it was ${REC.E.e2.signMean}, and the log loss was ${REC.E.e2.signLL} against ${REC.E.e2.julyLL} (one-sided p < 0.001; log loss measures how far predicted probabilities sit from what happened, and lower is better). Reading at the signing was adopted. The second was a contract effect that varies with the player's quality: it added nothing (p = ${REC.E.e3p}) and was not adopted.`));
add(P("The regressions are fitted for each season ahead with at least 200 player-seasons of evidence: up to eight seasons ahead for the 2018-19 valuation season and twelve for 2025-26. Past that, the league-wide decline in expected WAR between the last two fitted seasons is continued."));
add(H2("Terms that are not statistically significant"));
const failN = (model, term) => { const x = N.audit.insample.filter((r) => r.model === model && r.term === term); return [x.filter((r) => r.p > 0.05).length, x.length]; };
const fr = (model, term) => { const [a, b] = failN(model, term); return `${a} of ${b}`; };
add(P(`Every term in the games-share and chance-of-playing regressions was checked by one rule, set before any result was seen: a term goes if it is not statistically significant at the 5% level and dropping it does not worsen the forecast on the valuation seasons 2015-16 to 2021-22; terms that fail are tested together as well as one at a time; a term that fails on its p-value but improves the forecast is kept only with the reason stated. ${T("drops")} gives the result. The defenceman term in the games share and two terms in the chance of playing, age squared and seasons since debut, failed in most seasons ahead, and dropping all three together lowered the error of season WAR from ${f4(B0.war)} to ${f4(AU["S1 G1+P1+P2"].war)} wins (${pq(AU["S1 G1+P1+P2"].p_version_better_war)}); they were dropped. The no-contract-record indicator is not statistically significant in ${fr("chance of playing", "contract_unknown")} seasons ahead, but dropping it made season WAR worse (${pq(AU["P3 no no-contract-record marker"].p_build_better_war)}), so it was kept.`));
add(TT("drops", "Terms checked for statistical significance, and the forecast without each"));
const DR = [["Defenceman (games share)", "games share", "is_D", "G1 no defenceman", "Dropped"],
  ["Age squared (chance of playing)", "chance of playing", "age_sq", "P1 no age squared", "Dropped"],
  ["Seasons since debut (chance of playing)", "chance of playing", "exp_seasons", "P2 no seasons since debut", "Dropped"],
  ["The three together", null, null, "S1 G1+P1+P2", "Dropped"],
  ["No contract record (chance of playing)", "chance of playing", "contract_unknown", "P3 no no-contract-record marker", "Kept: dropping it worsens the forecast"],
  ["The games-share floor at 0.05, against 0", null, null, "G2 floor at 0", "Floor at 0: it never binds"]];
add(TABLE(["Term", "Seasons ahead with p > 0.05", "Season WAR without it", "p, better without", "p, worse without", "Decision"],
  DR.map(([lab, m, t, v, dec]) => [lab, m ? fr(m, t) : "-", f4(AU[v].war), f3(AU[v].p_version_better_war), f3(AU[v].p_build_better_war), dec]),
  [2700, 1300, 1200, 1100, 1100, 2240], [1, 2, 3, 4], new Set(), 15));
add(CAPTION(`In sample: the 2025-26 fit, every season ahead fitted, two-sided p, errors clustered by player. Season WAR: root mean squared error in wins on ${comma(N.audit.rows_all)} player-seasons, valuation seasons 2015-16 to 2021-22, against ${f4(B0.war)} with every term (forecast_term_audit.py, October 21, 2026). The two p columns are one-sided, from 2,000 redraws of careers: the share of redraws in which the version without the term is not better, and in which it is not worse.`));

// =====================================================================================================================
// 3. PRICING A SEASON
// =====================================================================================================================
add(H1("3. Pricing a Season"));
add(P("The forecast is in wins. The price line converts it to dollars at the rate clubs pay. It is a regression of each contract's cap hit, as a share of the cap in its first season, on the player's forecasted WAR if he plays in that season. It adds a slope for defencemen and a term for the contract's length in years:"));
add(EQ(["cap share = α + (β + ", ["_", "β", "D"], " × defenceman) × forecasted WAR if he plays + γ × years of term"]));
add(P(`The sample is the ${comma(PL.n)} skater contracts past the entry level that started from 2018-19 to 2025-26, each with a forecast at its signing. They were signed by ${comma(PL.players)} players who had a season of 10 or more games in one of the two before. Of these contracts, ${comma(PL.censored)} are at the league minimum, which is a floor rather than a negotiated price: a player at the minimum might have been worth less, but no club can pay less. They are therefore treated as censored in the regression. A contract above the minimum enters the fit through how close the price line comes to its cap hit; a contract at the minimum enters only through how likely the price line is to put the player at or below it (a Tobit regression; Tobin 1958). Treating minimum contracts as negotiated prices would pull the price line toward the minimum and understate what clubs pay per win.`));
const plSpecs = Object.keys(PLF);
const PLROW = [["intercept", "Intercept (α)"], ["per forecast win", "Per forecasted win (β)"], ["defence addition per win", "Added per win for a defenceman (β_D)"], ["per year of term", "Per year of term (γ)"]];
add(TT("pl", "The price line, built up one term at a time"));
add(TABLE(["Term", "Forecasted WAR alone", "+ defence slope\n(the term-free\nprice line)", "+ term\n(adopted)"],
  [...PLROW.map(([k, lab]) => [lab, ...plSpecs.map((s) => cc(PLF[s].terms[k], 3, CAP25M))]),
   ["Spread of the price (σ)", ...plSpecs.map((s) => f3(PLF[s].sigma * CAP25M))],
   ["Log-likelihood", ...plSpecs.map((s) => Number(PLF[s].loglik_share).toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 }))]],
  [2840, 2260, 2260, 2280], [1, 2, 3]));
add(CAPTION(`Censored (Tobit) regression on ${comma(PL.n)} contracts, ${comma(PL.censored)} of them at the league minimum. Coefficients are shares of the cap, shown in millions of dollars at the 2025-26 cap (standard error, clustered by player) [two-sided p-value]; σ is the typical distance of a cap hit from the price line. Log-likelihood in cap-share units, on the same contracts in each column; higher is better. The model prices on the price line locked on October 21, 2026; refitted, its coefficients equal the lock's to within ${(Math.max(LK.gap_term_in, 1e-12)).toExponential(0)} of the cap.`));
add(P(`At the 2025-26 cap, the price line prices a forecasted win at ${mil(perWin(LK.term_in.beta))} for a forward and ${mil(perWin(LK.term_in.beta + LK.term_in.beta_d_add))} for a defenceman, and adds ${mil(perWin(LK.term_in.gamma_term))} a season for each year of term. A one-year contract for a forward forecast at one win is priced at (${f4(LK.term_in.alpha)} + ${f4(LK.term_in.beta)} + ${f4(LK.term_in.gamma_term)}) × $${f1(CAP25M)} million = ${mil(perWin(LK.term_in.alpha + LK.term_in.beta + LK.term_in.gamma_term))}. ${F("price")} shows the price line against the contracts it is fitted on.`));
add(FIGURE("price", "fig_price_line.png", "The price line",
  `Each point is one contract's cap hit, restated at the 2025-26 cap, against the forecast at its signing of the player's WAR if he plays in its first season. Lines: the adopted price line for one, three, and six years of term, floored at the league minimum.`));
add(H2("The forecast the price line reads"));
const SL = PL.signing_log.find((l) => l.startsWith("seasons between")) || "";
const before = (SL.match(/, 1: ([\d,]+)/) || [])[1];
const SD = PL.signing_log.find((l) => l.startsWith("start-dated (page")) || "";
const sampleN = (SD.match(/of ([\d,]+)/) || [])[1];
add(P(`A club signing a player prices what it expects him to produce, so the price line is fitted on the forecast, the same measure it is applied to, dated at the contract's signing: the forecast uses only the seasons the club had seen when it agreed to the deal. Of the ${sampleN} contracts in the sample, ${before} were signed before the season preceding their first season had finished; a forecast dated at the first season would include that season. In-sample the two datings fit about equally (log-likelihood ${REC.ll.signIn} at the signing against ${REC.ll.startIn} at the first season, with term), so the choice rests on using only what was known.`));
const TA = (v, t) => N.term_avg.find((r) => r.version === v && r.term === t);
const TA0 = TA("first season (today)", true), TA1 = TA("term average (main)", true), TA2 = TA("term average, expected", true);
add(P(`The price line is fitted on the forecast of the contract's first season. A club signing a long contract might instead price the performance it expects over every season of it, so the average forecast over the contract's term was tested in its place, as was that average times the chance of playing each season (${T("termavg")}). Both fit the cap hits worse in sample and predict them worse for players left out of the fit, in each of 20 repeats. The term premium rises rather than falls on the averages, because long contracts go to players forecast to decline, so the premium is not paying for later performance. The first season's forecast was kept.`));
add(TT("termavg", "The price line on the first season's forecast and on the average over the term"));
add(TABLE(["Forecast the price line reads", "Per forecasted win", "Per year of term", "Log-likelihood", "Held-out error", "Repeats with lower error"],
  [["First season (adopted)", TA0, null], ["Average over the term, if he plays", TA1, TA0], ["Average over the term × chance of playing", TA2, TA0]].map(([lab, r, b]) =>
    [lab, mil(r.beta * CAP25M), mil(r.gamma_term * CAP25M), Number(r.loglik).toFixed(1), money(r.rmse_M), b ? `${r.rmse_beats_first} of 20` : "-"]),
  [3200, 1350, 1250, 1250, 1250, 1340], [1, 2, 3, 4, 5], new Set(), 16));
add(CAPTION(`The same ${comma(PL.n)} contracts and censored regression, with term; per win for forwards, at the 2025-26 cap. Held-out error: root mean squared error of the expected cap hit, $M at the 2025-26 cap, with the players split into five groups, each predicted from a fit on the other four, the split repeated 20 times; the last column counts the repeats in which the version's error is lower than the first season's (term_average_price_line.py, October 21, 2026). Each season's price is linear in the forecast, so pricing each season on its own forecast adds up to pricing the term's average.`));
add(H2("Contract length"));
add(P(`Clubs pay more a season for a longer contract at the same forecast: they buy the security of the player for those years. ${T("term")} shows it. Without a term for length, the price line overprices one-year contracts by ${mil(PL.by_term[0].term_free - PL.by_term[0].observed)} on average and underprices eight-year contracts by ${mil(PL.by_term[7].observed - PL.by_term[7].term_free)}; with it, each length's mean is close. Adding term raises the log-likelihood by ${f1(PLF["wins + defence + term"].loglik_share - PLF["wins + defence"].loglik_share)} on the same contracts, and its coefficient is statistically significant at the 5% level (${pq(PLF["wins + defence + term"].terms["per year of term"].p)}). The price line without term is reported beside each value as a sensitivity.`));
add(TT("term", "Mean cap hit by contract length, observed and priced"));
add(TABLE(["Years of term", "Contracts", "Observed", "Price line without term", "Adopted price line"],
  PL.by_term.map((r) => [String(r.years), comma(r.n), money(r.observed), money(r.term_free), money(r.term_in)]),
  [1800, 1700, 2000, 2050, 2090], [1, 2, 3, 4]));
add(CAPTION("Mean cap hit of the contracts of each length, and the mean of each price line's expected cap hit for the same contracts, allowing for the league minimum; millions of dollars at the 2025-26 cap."));
add(P("The premium buys security, not more wins: tested as a predictor of a player's later production, contract length accounted for at most a sixth of the premium, with opposite signs on Bacon's WAR and on Game Value. A season is priced at the term left at the valuation date, the same for each remaining season, because the comparison is a replacement player with the same forecast signed that day for the rest of the deal. A control season, bought one season at a time, is priced at one year of term, as is each season of a drafted player's career (Section 6)."));
add(H2("Other forms of the price line"));
add(P(`Six other forms were tested against the adopted one on held-out contracts (${T("spec")}). A premium that falls with the player's quality predicted best, mostly through one step: a premium of $${f3(REC.step.below)} million a year for players forecast below replacement against $${f3(REC.step.above)} million for everyone else. The flat premium was kept. The step's gain is small, 0.7% of held-out error (1.2718 against 1.2809, in $M), and it adds a term; the premium that varies by forecast group adds two more, which are not statistically significant against the step (p = ${f3(REC.step.pGroup)}). The premium's fall with quality is stated as a limitation. A separate line for restricted free agents predicted 0.17% better, mostly by pricing restricted defencemen higher, at the cost of four more terms; one price line serves both. A squared term and a bend fitted better in-sample only. A separate line for the last four seasons was not statistically significant (p = 0.24), so the price line is stable over the period.`));
add(TT("spec", "The price line against six alternatives"));
add(TABLE(["Version", "Log-likelihood gain (p)", "Held-out error ($M)", "Repeats with lower error"],
  REC.spec, [4200, 2000, 1600, 1840], [2, 3], new Set(), 16));
add(CAPTION("Tested on October 5, 2026, on that day's price line and 2,296 contracts (price_line_spec_tests.py v1.0-v1.1). Log-likelihood gain against the adopted price line, with its likelihood-ratio p-value. Held-out error: the root mean squared error of the expected cap hit, $M at the 2025-26 cap, with the contracts split by player into five groups, each predicted from a fit on the other four, the split repeated 20 times. The last column counts the repeats in which the version's error is lower than the adopted price line's."));
add(H2("The league-minimum floor"));
const mae = H.war_if_plays_mae;
add(P(`No player is paid less than the league minimum, so a season's price is the price line's price or the minimum, whichever is higher. The forecast is uncertain, and the floor removes only the bottom of its range: for a player near the minimum, the average price over the range of outcomes is above the price of the point forecast. Each season is therefore priced at the expected value of the higher of the two, with the price normally distributed around its point estimate μ. Its standard deviation σ is the forecast's mean absolute miss k seasons ahead (${f2(mae["0"])} WAR in the valuation season, rising to ${f2(mae["5"])} five seasons ahead) times 1.2533, converted to dollars at the season's price per win; for a normal distribution the standard deviation is the mean absolute deviation times √(π/2) = 1.2533. With F the league minimum and Φ and φ the standard normal distribution and density:`));
add(EQ(["V = F × Φ(z) + μ × (1 − Φ(z)) + σ × φ(z),   z = (F − μ) / σ"]));
add(P(`The first term is the floor times the chance the price falls below it; the second and third are the expected price when it does not. For a player far above the minimum, V equals the price line's price; Pacioretty's adjustment is $${comma(Math.round(pacS[0].uncertainty_correction))} in his first season.`));

// =====================================================================================================================
// 4. CONTRACT VALUE AND CONTROL SEASONS
// =====================================================================================================================
add(H1("4. Contract Value and the Terminal Value"));
add(P("A contract's value is the sum of it’s remaining seasons and the terminal value, the value of the control seasons after it. Written in full for a player valued in season t:"));
add(EQ(["value = Σ (", ["_", "p", "k"], " × ", ["_", "V", "k"], " − ", ["_", "C", "k"], ") / ", ["^", "1.03", "k"], "  +  Σ ", ["_", "W", "j"], " × (", ["_", "V", "j"], " − ", ["_", "C", "j"], ") / ", ["^", "1.03", "j"]]));
add(P("The first sum runs over the seasons k of his contracts; V_k is the floored price of his forecast at the cap expected for that season, cap_t × 1.03^k, so on the value side the growth and the discount cancel. The second sum runs over the control seasons j after the last contract, each weighted by W_j, the chance the club keeps him and he plays (below). The cap hit is subtracted whether or not he plays: an injured or buried player still counts against the cap, so the chance of playing multiplies the value only. The one exception is a player on long-term injured reserve (LTIR) when traded, read from Spotrac's injured-reserve log: a club may exceed the cap by an LTIR player's cap hit, so his cost is charged only in the share of each season he is forecast to play. Retirement can end a cap hit; that relief is not modelled, which errs toward a lower value. The contracts valued are the one he is playing and each extension signed on or before the valuation date; an extension signed later was not known at the valuation, and for a traded player a contract signed on the trade date itself counts as signed after it (Section 8). Each season's cap hit is from PuckPedia, and a contract later bought out is valued at its full signed term until the buyout is known, at the opening of free agency after his most recent season played."));
add(H2("Control seasons"));
add(P("When a contract ends with the player a restricted free agent, his club keeps his rights until he can become an unrestricted free agent: it retains him by tendering a qualifying offer. Each control season adds its value less its cost, weighted by the chance that it happens:"));
add(BULLET("Value: his forecasted WAR if he plays in that season, priced at one year of term, with the floor."));
add(BULLET("Cost: the qualifying offer, which the CBA sets from his prior salary; once he is eligible for arbitration, the higher of the qualifying offer and the price line's price of his arbitration years WAR. Through the 2025 offseason the qualifying offer was 110% of a salary up to $660,000, 105% up to $1 million, and 100% above it, never above 120% of the cap hit for contracts starting from 2020-21 and never below the league minimum; the 2026 agreement's bands apply after that. The arbitration WAR is the forecast's own starting level rebuilt at that season, from the seasons before it, times the forecasted games share. Each next qualifying offer is computed on what he was paid."));
add(BULLET(`Weight: the chance his club qualifies him times the chance he then plays, by his forecasted quality at the decision (${T("control")}), measured on the qualify-or-walk decisions for skater contracts that ended from 2018-19 to 2024-25. The weights compound from season to season, starting from his chance of playing the contract's last season.`));
add(BULLET("Walking away: the terminal value ends at the first control season whose surplus is negative, and later seasons count as zero. PuckPedia marks some expiring contracts \"UFA no QO\", where the club declined to qualify the player; that mark is used only from the opening of free agency after the contract ends, when the decision is known, and before then the walk-away rule prices the choice."));
add(TT("control", "The weight on each control season"));
add(TABLE(["Forecasted WAR if he plays", "Decisions", "Qualified", "Played, if qualified", "Weight"],
  BUCKETS.map(([b, lab]) => [lab, comma(CT.qualify_n[b]), pct(CT.qualify_p[b]), CT.plays_given_q[b] === undefined ? "–" : `${pct(CT.plays_given_q[b])} (of ${comma(CT.plays_given_q_n[b])})`, f3(bucketW(b))]),
  [2600, 1500, 1600, 2240, 1700], [1, 2, 3, 4]));
add(CAPTION("Decisions on skater contracts ending from 2018-19 to 2024-25 with the player a restricted free agent, by his forecast at the decision. Played, if qualified: the share of qualified players who played at least one NHL game the next season, among those who played the contract's last season. A player with no forecast enters the lowest group: a player who could not hold an NHL job is the one a club walks away from."));
add(H2("Weighting a control season"));
add(P(`A control season happens only if the club qualifies the player and he then plays. Four ways of weighting it were considered. Assuming every season happens gives clubs control they did not exercise: that rule predicted only ${REC.d14.intercept}% of the walk-aways observed. Keeping a season only when the player's forecast beats a replacement player's went too far the other way, zeroing ${REC.d14.netRepl}% of the players clubs kept. The observed qualifying rate for players of his quality was adopted, since it is what clubs actually did. A qualified player still left the league ${REC.d14.leave}% of the time, so the chance he plays given that he was qualified is multiplied in. Reusing the forecast's chance of playing instead would count walk-aways twice, once in the qualifying rate and again in a chance of playing estimated on players who include them. The plays-given-qualified rate is measured only on players who played the contract's last season, so an absence in that season is charged once, through the chance of playing the weights compound from, and not again in the weight.`));
add(H2("The cost of a control season"));
add(P("A player eligible for salary arbitration can push his pay toward his market price, so from eligibility a control season costs the higher of the qualifying offer and the price line's price of his arbitration WAR; before it, the qualifying offer. The same rule costs a drafted player's control seasons (Section 6). Actual contracts were not used as the cost: they record what was negotiated years after the valuation, and long contracts also buy seasons after control ends. Surplus can remain in an arbitration season, but less of it."));
add(P(`Eligibility comes from PuckPedia's arbitration flag on the expiring contract: a player flagged eligible is eligible from his first control season, and one flagged not eligible from his second (${REC.arb.flag0}% of ${REC.arb.flag0n} players flagged not eligible were eligible a season later, and ${REC.arb.stay}% of eligible players stay eligible). The CBA's count of professional seasons (Section 12.1(a)) agreed with the flag for ${REC.arb.agree}% of ${comma(REC.arb.nFlag)} contracts and was later for ${REC.arb.later}, because the data hold no AHL games, so the flag was adopted. The flag is set at the contract's end, so a valuation dated earlier uses eligibility recorded at a later date.`));
add(H2("Walking away"));
add(P("Control is a right, not an obligation: a club qualifies a player while he is worth it and lets him go when he is not, and once it lets him go it cannot qualify him again later. The terminal value therefore ends at the first control season whose surplus is negative. Counting every control season whatever its surplus would charge the club for seasons it would never pay for."));
add(H2("Max Pacioretty and Tomas Tatar"));
const carried = (x, P_) => x.cost_dollars * (x.contract_id === P_.seasons[0].contract_id ? 1 - P_.retained_pct : 1);
add(P(`Pacioretty's contract had one season left, 2018-19, at a cap hit of ${mil(M(pacS[0].cost_dollars))}, of which Montreal retained ${pct(PAC.retained_pct, 0)} in the trade, so Vegas carries ${mil(M(carried(pacS[0], PAC)))}. Vegas also signed him to a four-year extension at $7.00 million a season on the day of the trade; a contract signed on the trade date is left out of a traded player's value and of his chance of playing (Section 8), so his value is the one season. At one year of term his performance is priced at ${mil(M(pacS[0].value_dollars))}, of which ${mil(M(pacS[0].term_premium_dollars))} is the term premium; with a ${pct(pacS[0].p_play, 0)} chance of playing, that is ${mil(M(pacS[0].p_play * pacS[0].value_dollars))} against the ${mil(M(carried(pacS[0], PAC)))} Vegas carries. Had the extension counted, his value would have been ${mil(M(PAC.npv_with_extension))}: the price falls short of the $7.00 million cap hit in each of its seasons, by more as he ages and his chance of playing falls.`));
add(P(`Tatar's contract had three seasons left at ${mil(M(tatS[0].cost_dollars))}, of which Vegas retained ${pct(TAT.retained_pct, 1)}, so Montreal carries ${mil(M(carried(tatS[0], TAT)))} a season. Each season's price is below the cap hit Montreal carries, and his value is ${mil(M(TAT.summary.npv_total))} at the 2018-19 cap (${mil(M(TAT.summary.npv_total_term_free))} on the price line without term). ${T("pac")} values both contracts.`));
add(TT("pac", "Max Pacioretty's and Tomas Tatar's contracts, valued at the trade"));
const ageAt = (P_, x) => P_.age_last + P_.last_lag + x.k;
const pacRow = (P_, x, nm) => [nm, `${x.season_start}-${String(x.season_start + 1).slice(2)}`, String(ageAt(P_, x)), f2(x.rate_82), f2(x.gp_share), f2(x.projected_war), f2(x.p_play), money(M(x.value_dollars)), money(M(x.term_premium_dollars)), money(M(x.cost_dollars)), money(M(carried(x, P_))), money(M(x.pv_dollars))];
add(TABLE(["Player", "Season", "Age", "WAR per 82", "Games share", "WAR if he plays", "Chance of playing", "Price", "Of which term", "Cap hit", "Carried by the acquirer", "Present value"],
  [...pacS.map((x) => pacRow(PAC, x, "Pacioretty")), ["Pacioretty, total", "", "", "", "", "", "", "", "", "", "", `**${money(sumPV(pacS))}**`],
   ...tatS.map((x) => pacRow(TAT, x, "Tatar")), ["Tatar, total", "", "", "", "", "", "", "", "", "", "", `**${money(sumPV(tatS))}**`]],
  [960, 700, 430, 700, 700, 760, 760, 800, 800, 790, 860, 900], [2, 3, 4, 5, 6, 7, 8, 9, 10, 11], new Set(), 15));
add(CAPTION(`Millions of dollars at the cap of the valuation season (2018-19, $${f1(M(CAP18))} million). Age on September 15. Price: the adopted price line's price of his WAR if he plays at the term left, with the floor. Present value = (chance of playing × price − cap hit carried) / 1.03^k, k counted from 2018-19. Pacioretty became an unrestricted free agent at the end of the season, so he has no terminal value; on the price line without term his value is ${mil(M(PAC.summary.npv_total_term_free))}.`));

add(H2("Goaltenders"));
const GOW = REC.gPersist;
add(P(`A goaltender's WAR varies far more from season to season than a skater's (${T("goalie")}). Across consecutive seasons of 20 or more games, a goaltender's WAR in one season correlates ${f3(GOW.g[0])} with his WAR in the next (95% interval ${f3(GOW.g[1])} to ${f3(GOW.g[2])}, ${comma(GOW.g[3])} pairs by ${GOW.g[4]} goaltenders), against ${f3(GOW.s[0])} for skaters (${f3(GOW.s[1])} to ${f3(GOW.s[2])}, ${comma(GOW.s[3])} pairs); per game, ${f3(GOW.gRate)} against ${f3(GOW.sRate)}. The 50/30/20 average of the three seasons before correlates ${f3(GOW.gTrail)} with the next season for goaltenders and ${f3(GOW.sTrail)} for skaters. A goaltender's own record therefore says much less about his next season, and his forecast keeps less of it.`));
add(P(`A goaltender's forecast is his 50/30/20 average of season WAR (62.5/37.5 with two seasons, the most recent alone with one), keeping 35% of it and pulling 65% toward the league average of 2.19 WAR, plus an age term. The 35% was chosen by cross-validation on held-out goaltenders: each goaltender's seasons were predicted from fits on other goaltenders (${comma(REC.gAge.n)} goaltender-seasons of 20 or more games by ${REC.gAge.goalies} goaltenders), and the mean squared error of season WAR was lowest at 35% (${f4(REC.gPull.mse)}, against ${f4(REC.gPull.at30)} at 30% and ${f4(REC.gPull.at40)} at 40%). Counting only seasons of 10 or more games, as for skaters, made it worse (${f4(REC.gPull.gp10[0])} against ${f4(REC.gPull.gp10[1])} on the same seasons), so every season counts.`));
add(P(`Ages are complete for goaltenders, from the NHL's records, and the age term is a straight line in age fitted on the forecast's errors in goaltender-seasons before the valuation season. It lowers the forecast by about ${f2(-REC.gAge.slope)} WAR for each year of age (p < 0.001 in sample) and lowers the held-out error of season WAR by ${f2(100 * (1 - REC.gAge.lin / REC.gAge.base))}% (${f4(REC.gAge.lin)} against ${f4(REC.gAge.base)}; one-sided p = ${f3(REC.gAge.linP)}). Adding age squared lowered it a further ${f2(100 * (REC.gAge.lin - REC.gAge.quad) / REC.gAge.base)}%, and the straight line was kept. The term is applied at his age in each season, so a goaltender's forecast declines as he ages.`));
add(P(`A goaltender's chance of playing each season is a logistic regression for each season ahead on his age, his forecast, and his games share in the most recent season, fitted on seasons before the valuation season, as for skaters but without contract status. Age squared was tested and dropped: it was not statistically significant in any season ahead (p from ${f3(REC.gPlay.sqP[0])} to ${f3(REC.gPlay.sqP[1])}), and the log loss was ${f4(REC.gPlay.llNoSq)} without it against ${f4(REC.gPlay.ll)} with it. On the valuation seasons 2015-16 to 2021-22 the chance is well calibrated: ${f3(REC.gPlay.fc0)} forecast against ${f3(REC.gPlay.played0)} who played in the valuation season, and ${f3(REC.gPlay.fc5)} against ${f3(REC.gPlay.played5)} five seasons ahead.`));
const GO_ = N.goalie;
add(P(`The goaltender price line has the skater line's form: cap share on the forecast dated at the signing, censored at the league minimum, with a term for contract length, fitted on ${GO_.n} standard-level goaltender contracts starting from 2015-16 to 2025-26 (${GO_.at_min} at the minimum). At the 2025-26 cap it is ${mil(GO_.alpha * CAP25M)} plus ${mil(GO_.beta * CAP25M)} per forecasted WAR plus ${mil(GO_.gamma * CAP25M)} a season per year of term. It is fitted on the goaltender's forecast before the age term: what clubs pay follows his record, and fitted on the forecast with the age term the line predicts cap hits worse (held-out error ${money(REC.gLine.aged)} against ${money(REC.gLine.flat)} a contract, in each of 20 repeats). Each season is then priced on the forecast with the age term, so a contract for an older goaltender is valued on the decline clubs do not price. Each control season has one weight for all goaltenders, ${f3(CT.goalie.qualify_p)} qualified × ${f3(CT.goalie.plays_given_q)} played = ${f3(CT.goalie.weight)}, from ${CT.goalie.n[0]} decisions: the qualifying rates do not differ by forecasted quality (p = ${f3(REC.gControl.p)}).`));
add(TT("goalie", "Goaltenders and skaters, and the goaltender model's choices"));
add(TABLE(["Measure or choice", "Result"],
  [["Season WAR, correlation with the next season", `Goaltenders ${f3(GOW.g[0])}, skaters ${f3(GOW.s[0])}`],
   ["WAR per game, correlation with the next season", `Goaltenders ${f3(GOW.gRate)}, skaters ${f3(GOW.sRate)}`],
   ["Share of his own record kept", `35%: mean squared error ${f4(REC.gPull.mse)} (30%: ${f4(REC.gPull.at30)}; 40%: ${f4(REC.gPull.at40)})`],
   ["Age term", `−${f2(-REC.gAge.slope)} WAR a year; held out ${f4(REC.gAge.lin)} against ${f4(REC.gAge.base)} (p = ${f3(REC.gAge.linP)})`],
   ["Chance of playing", `Forecast ${f3(REC.gPlay.fc0)} / ${f3(REC.gPlay.fc5)} against ${f3(REC.gPlay.played0)} / ${f3(REC.gPlay.played5)} played (now / five seasons ahead)`],
   ["Price line fitted on the forecast", `Without the age term ${money(REC.gLine.flat)}, with it ${money(REC.gLine.aged)} held-out error a contract`]],
  [3700, 5940], [], new Set(), 16));
add(CAPTION("Goaltender-seasons of 20 or more games, 2007-08 to 2025-26; mean squared errors of season WAR on goaltenders left out of the fit, 6 seeds × 5 folds split by goaltender; the chance of playing on the valuation seasons 2015-16 to 2021-22 (goalie_review.py, goalie_play_spec.py, goalie_line_check.py, October 21, 2026)."));

// =====================================================================================================================
// 5. WAR AND CIRCULARITY
// =====================================================================================================================
add(H1("5. WAR and Circularity"));
add(P("Using one source of WAR carries a risk of circularity. The price line is fitted on what clubs paid for players whose forecasts are built from WAR, and the values will be compared with outcomes measured in WAR, so agreement could reflect Bacon's model rather than performance. To check that the forecast measures performance, I compared it with Game Value, a measure built from the NHL's play-by-play and shift records with no input from Bacon’s WAR model. Game Value gives each skater on the ice an equal share of his team's expected goals for and against, adjusted for score-state (tied, leading, trailing), plus the value of the penalties he draws and takes; in its adjusted version (GV-adj), a player is also separated from his linemates and opponents at five-on-five. Across full seasons, team Game Value explains 58.3% of the variation in team goal differential."));
add(P(`${T("gv")} compares each measure with the same season's Game Value, across ${comma(GV.n)} player-seasons by ${comma(GV.players)} players from 2017-18 to 2025-26. The forecast is more closely correlated with Game Value than the trailing WAR it is built from (r = ${f3(GV.all.forecast[0])} against ${f3(GV.all.trailing[0])}), for forwards and defencemen, and one season further ahead (${f3(GV.next.forecast[0])} against ${f3(GV.next.trailing[0])}). The correlation of expected WAR is ${f3(GV.expected[0])} with contract status and ${f3(GV.no_contract[0])} without it, so the agreement does not come through clubs' contract decisions. Some agreement is expected regardless, since both measures describe the same games.`));
add(TT("gv", "Correlation of each measure with the same season's Game Value"));
const gvr = (lab, key, idx = 0) => [lab, ...["all", "F", "D", "next"].map((s) => (GV[s] && GV[s][key] ? f3(GV[s][key][idx]) : "–"))];
add(TABLE(["Measure", "All skaters", "Forwards", "Defencemen", "One season further"],
  [gvr("Trailing WAR, 50/30/20", "trailing"),
   ["Starting level (per 82)", f3(GV.start[0]), "–", "–", "–"], gvr("Forecasted WAR if he plays", "forecast"),
   ["Expected WAR", f3(GV.expected[0]), "–", "–", "–"], ["Expected WAR without contract status", f3(GV.no_contract[0]), "–", "–", "–"]],
  [4200, 1360, 1360, 1360, 1360], [1, 2, 3, 4], new Set(), 16));
add(CAPTION(`Pearson correlation with GV-adj, on ${comma(GV.n)} player-seasons (${comma(GV.n_next)} one season further). Measured on October 5, 2026 (gv_investigation_f.py), on the forecast of that day.`));

// =====================================================================================================================
// 6. DRAFT PICKS
// =====================================================================================================================
add(H1("6. Draft Picks"));
const PS = PK.p_star;
const neverN = PK.routes["never played"];
add(P(`A draft pick has no contract and no player yet. It is a claim on whoever the club selects, so its value has to come from what past selections at the same draft position delivered. Two features of the draft make this hard. Outcomes are uneven: of the ${comma(PK.n)} players drafted from 2007 to 2017, ${comma(neverN)} played no NHL game while their club held their rights, and the ${PK.top5.n} with the most surplus, 5% of the players, delivered ${pct(PK.top5.share, 0)} of the total. And outcomes arrive slowly: a club holds a drafted player's rights for about nine seasons, so the drafts that can be measured completely are years older than the trades being priced.`));
add(H2("The approach"));
add(P(`Most of the surplus picks produce comes from the few players who become stars. Of the ${comma(PK.stars.skaters)} skaters drafted from 2007 to 2015, the ${PK.stars.stars} who became stars (${pct(PK.stars.share_players)}, by Bacon's definition below, with at least 200 NHL games) delivered ${pct(PK.stars.share_surplus)} of the surplus those picks returned. Among the first ten picks, stars were ${pct(PK.stars.top10_share_players)} of the players and delivered ${pct(PK.stars.top10_share_surplus)} of the surplus. A pick is therefore valued as a claim on a chance of a star:`));
add(EQ(["pick value = star value × star probability for the draft position"]));
add(P(`The star probability is the chance that a player taken at that draft position becomes a star. It comes from Patrick Bacon's draft model, the source of the WAR used throughout, which defines a star as a player whose career WAR per 82 games is at least 1.8 for a forward or 1.23 for a defenceman. The star value is the surplus a pick would be worth if its player were certain to become a star. It is estimated below at ${mil(STAR.b)} at the 2025-26 cap; the first overall pick, with a star probability of ${pct(PS["1"])}, is worth ${f3(PS["1"])} × ${mil(STAR.b)} = ${mil(STAR.b * PS["1"])}.`));
add(H2("What a drafted player delivered"));
add(P("To learn what a draft position returns, I price each player drafted from 2007 to 2017 the way the player model prices a contract, over the seasons his club held his rights: from his draft to the end of club control, with careers observed through 2025-26. Six drafted players who died before reaching the NHL, while their clubs still controlled them, are left out (Appendix C). The rules for each season are:"));
add(BULLET("Value: the market price of the performance he delivered (his WAR), on the price line at one year of term, with the league-minimum floor; a goaltender's on the goaltender price line. The pick model is fitted on what happened, so delivered WAR is priced, not a forecast. WAR in the shortened 2012-13, 2019-20, and 2020-21 seasons is scaled to 82 games."));
add(BULLET("Cost: first the entry-level maximum for his draft class, counted from his first NHL season, for three, two, or one seasons by his age on September 15 of the year he signed (18 to 21, 22 to 23, 24 or older). Then a chain of one-year qualifying offers, and once he is eligible for arbitration, the higher of the qualifying offer and the price line's price of his arbitration WAR, as for players under contract. He becomes eligible after 4, 3, 2, or 1 seasons of 10 or more NHL games for a signing age of 20 or under, 21, 22 to 23, or 24 or older (CBA Section 12.1(a))."));
add(BULLET("A season without an NHL game is worth zero and costs zero, since a minor-league salary does not count against the cap. A season of fewer than 10 games is scaled by its games over 82, since a call-up counts against the cap only for his days on the roster."));
add(BULLET(`Rights: a player who first played for another club, without having signed with or been traded by the club that drafted him, is worth zero to the pick, since the drafting club let his rights lapse (${PK.routes.lapsed} players). One who signed his entry-level contract with the drafting club and was lost later, on waivers or by release, keeps his surplus (${PK.routes["signed by the drafting club"]} players): the club held him.`));
add(BULLET("A career whose total is negative counts as negative."));
add(P("A drafted player's seasons have already been played, so each season's value and cost are in that season's dollars, and each season's cap is known. Instead of discounting at 3%, each season is restated at the 2025-26 cap, written cap*, by multiplying it by cap* over that season's cap:"));
add(EQ(["surplus = Σ (", ["_", "V", "s"], " − ", ["_", "C", "s"], ") × (cap* / ", ["_", "cap", "s"], ")"]));
add(P("This is the discount of Section 1 at the cap's actual growth rather than 3%. On the value side, cap growth and this discount cancel, as in Section 1: a season's value and cost become shares of that season's cap, and the career's surplus is the sum of those shares, stated in 2025-26 dollars."));
const PT = PK.point;
const played_ = PT.seasons.filter((x) => x.gp > 0), unplayed_ = PT.seasons.filter((x) => x.gp <= 0);
add(P(`${T("point")} prices ${PT.name}, taken ${PT.pick}th in ${PT.draft} (star probability ${pct(PT.p_star)}), the draft position of the 2019 pick Montreal received in the example trade. He played ${played_.length} NHL seasons within club control; his surplus over them is ${mil(PT.surplus)}.`));
add(TT("point", `${PT.name} (${PT.draft}, #${PT.pick}), from his draft to the end of club control`));
add(TABLE(["Season", "NHL games", "WAR per 82", "Contract charged", "Value", "Cost", "Surplus"],
  [...PT.seasons.map((x) => [`${x.season}-${String(x.season + 1).slice(2)}`, String(x.gp), x.gp > 0 ? f2(x.war82) : "", x.gp <= 0 ? "Not in the NHL" : (x.elc ? "Entry-level" : (x.arb ? `Arbitration (${f2(x.arb_war)} WAR)` : "Qualifying offer")), f2(x.value), f2(x.cost), f2(x.surplus)]),
   ["Total", "", "", "", f2(PT.seasons.reduce((a, x) => a + x.value, 0)), f2(PT.seasons.reduce((a, x) => a + x.cost, 0)), `**${f2(PT.surplus)}**`]],
  [1500, 1100, 1200, 2400, 1100, 1100, 1240], [1, 2, 4, 5, 6], new Set(), 16));
add(CAPTION(`Millions of dollars at the 2025-26 cap. Value: his delivered WAR priced on the price line at one year of term. Arbitration: the price of his arbitration WAR (shown), the forecast's own starting level rebuilt at that season, when it exceeds the qualifying offer. Season WAR for 2019-20 and 2020-21 is scaled to 82 games. Club control ended after ${PT.window_end}-${String(PT.window_end + 1).slice(2)}. Of the two 50th picks of 2007-2017 named for this example, he played the more NHL games (${PT.nhl_games[PT.name]}).`));
add(H2("The cost of keeping a drafted player"));
add(P(`How cost is charged once a drafted player is in the NHL moves pick values more than any other choice. The options were what clubs actually paid, or a rule: the entry-level contract, then the qualifying offer, then from arbitration eligibility the higher of the qualifying offer and the price line's price of his arbitration WAR. A star's club usually signs him to a long contract while it still holds his rights, and a player eligible for arbitration can push his pay toward market, so a rule has to price eligibility at market to come near what clubs pay. The arbitration rule was adopted, the same rule that costs a player's control seasons (Section 4). Actual contracts were not used: they bring hindsight into the cost side, since they record what was negotiated years after the draft, and many are long contracts that buy unrestricted seasons as well as the seasons of club control.`));
add(P(`The rule's cost is still below what clubs paid first-round picks (${F("pickcost")}): ${listAnd(PK.first_round.map((g) => `${pct(g.cost_arb / g.cost_actual, 0)} of it for picks ${g.lo} to ${g.hi}`))}. Picks may therefore still look more valuable relative to players than they are, which is stated as a limitation.`));
add(FIGURE("pickcost", "fig_pick_cost.png", "Value delivered and two measures of cost, first-round picks",
  `Average per first-round skater who played in the NHL for the club that drafted him (2007-2017 drafts), over the seasons his club held his rights, in millions of dollars at the 2025-26 cap: the value of the performance he delivered, his cost under the adopted rule, and what clubs actually paid (each season's cap hit; PuckPedia from 2018-19, CapWages before).`));
add(H2("The shape of value across draft positions"));
const shp = (nm) => SH[nm];
const SHROWS = [["Straight line in draft position", "straight line in draft position"], ["Log of draft position", "log of draft position"],
  ["Log of draft position and its square", "log of draft position and its square"], ["Star value × star probability (adopted)", "star probability (adopted)"],
  ["Star probability and its square", "star probability and its square"], ["Star and NHL-player probabilities", "star and NHL-player probabilities"]];
add(P(`Value falls steeply over the first ten picks and is close to flat after the first round (${F("picks")}). Several shapes could describe that fall: a straight line in draft position, its logarithm, the logarithm and its square, or Bacon's star probability times a star value. Each was fitted on all 2,316 picks and scored on drafts left out of its fit: each draft was predicted from a fit on the other ten, and the held-out error is the root mean squared error over all picks (${T("shapes")}).`));
const stLog2 = shp("log of draft position and its square");
add(P(`The adopted shape has the lowest held-out error with a single parameter. A straight line values the first pick at ${mil(shp("straight line in draft position").at["1"])} and the logarithm at ${mil(shp("log of draft position").at["1"])}, against the ${mil(PK.avg_at["1"])} first picks returned and the adopted ${mil(STAR.b * PS["1"])}. The logarithm with its square comes close, but it turns upward after pick ${stLog2.first_rise}, valuing the 200th pick above the 137th. Adding the square of the star probability, or Bacon's probability of a 200-game NHL player, does not predict better (one-sided p = ${f3(shp("star probability and its square").p_vs_adopted)} and ${f3(shp("star and NHL-player probabilities").p_vs_adopted)}); once the star probability is in, the NHL-player probability's coefficient is ${f2(shp("star and NHL-player probabilities").terms.p_nhler.b)} (standard error ${f2(shp("star and NHL-player probabilities").terms.p_nhler.se)}). Bacon's probability is fitted on largely the same drafts, so its agreement with our surplus is not independent confirmation; applied to our data, his definition marks 5.9% of the skaters drafted from 2007 to 2015 as stars, against the 5.3% his probabilities imply.`));
add(TT("shapes", "Six shapes of value across draft positions"));
add(TABLE(["Shape", "Parameters", "#1", "#10", "#32", "#64", "Held-out error", "One-sided p"],
  [...SHROWS.map(([lab, k]) => [lab, String(shp(k).params), f2(shp(k).at["1"]), f2(shp(k).at["10"]), f2(shp(k).at["32"]), f2(shp(k).at["64"]), f4(shp(k).held), shp(k).p_vs_adopted === null ? "-" : pr(shp(k).p_vs_adopted)]),
   ["Actual average of the eleven players taken", "", f2(PK.avg_at["1"]), f2(PK.avg_at["10"]), f2(PK.avg_at["32"]), f2(PK.avg_at["64"]), "", ""]],
  [2900, 950, 700, 700, 700, 700, 1100, 1000], [1, 2, 3, 4, 5, 6, 7], bestKeys(SHROWS.map(([, k]) => ["", "", "", "", "", "", f4(shp(k).held)]), [6], 4), 16));
add(CAPTION("Values in millions of dollars at the 2025-26 cap, from each shape's fit on all 2,316 picks. Held-out error: each draft predicted from a fit without it; root mean squared error over all picks, $M. One-sided p: the share of 2,000 redraws of the drafts in which the shape's held-out error is not lower than the adopted shape's; a small p would mean the shape predicts better. The lowest error is in bold. Each actual average rests on eleven players, so a single draft changes it a great deal."));
add(FIGURE("picks", "fig_picks.png", "Draft position and surplus",
  "Left: Bacon's star probability by draft position (a logistic regression on pick number with a change of slope at pick 150). Right: the average surplus of the eleven players taken at each draft position (2007-2017), and three of the shapes in the table above. Millions of dollars at the 2025-26 cap."));
add(H2("The star value"));
add(P(`I regressed each drafted player's surplus on the star probability for his draft position, with no intercept, so a draft position with no chance of a star is worth zero:`));
add(EQ(["surplus = star value × star probability + error"]));
const DI = PK.draft_intercepts;
const diVals = Object.values(DI.values);
add(P(`The coefficient is the star value, ${mil(STAR.b)} (standard error ${f2(STAR.se)}). ${T("nested")} adds an intercept, then an intercept for each draft, then draft position with an intercept, then the NHL-player probability, each on the same 2,316 picks. None predicts left-out drafts better (one-sided p of ${f3(Math.min(shp("star probability and an intercept").p_vs_adopted, DI.p_vs_adopted, shp("star probability, draft position and an intercept").p_vs_adopted, shp("star and NHL-player probabilities").p_vs_adopted))} or more), and the star value moves by at most ${mil(Math.max(...[shp("star probability and an intercept").terms.p_star.b, DI.star.b, shp("star probability, draft position and an intercept").terms.p_star.b, shp("star and NHL-player probabilities").terms.p_star.b].map((b) => Math.abs(b - STAR.b))))}. The star value of ${mil(STAR.b)} is not the value of a star: it is the surplus of a pick whose star probability is 100%, which no draft position reaches, and it also includes the surplus of players who become regulars without becoming stars, which rises with the star probability.`));
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
add(H2("No intercept and no draft-year terms"));
add(P(`Two additions were considered and left out. A single intercept would give each pick, including a seventh-round pick with almost no chance of a star, a fixed amount of ${mil(sI.terms.intercept.b)}. It is not statistically significant at the 5% level (${pq(sI.terms.intercept.p)}), yet when it was measured it would have raised the value of all traded picks by 9.5% and of seventh-round picks by 111%, because a fixed amount is large next to their small star values.`));
add(P(`An intercept for each draft would let deep and shallow drafts differ in level. The draft intercepts are jointly statistically significant at the 5% level (${pq(DI.joint_zero.p)}): beyond what its star probability predicts, a pick in the best draft delivered ${mil(Math.max(...diVals))} and in the weakest ${mil(Math.min(...diVals))}. They are left out because a pick traded before its draft has no intercept of its own: it would have to be valued at the average draft's intercept. Predicting a left-out draft at the average intercept is no better than the adopted model (one-sided p = ${f3(DI.p_vs_adopted)}). The differences between drafts are carried instead by the next decision.`));
add(H2("One star value for every draft"));
const per = PK.per_draft;
const lo = per.reduce((a, b) => (b.star < a.star ? b : a)), hi = per.reduce((a, b) => (b.star > a.star ? b : a));
add(P(`Fitted on each draft separately, the star value ranges from ${mil(lo.star)} for the ${lo.draft} draft to ${mil(hi.star)} for ${hi.draft}, and the differences are statistically significant (${pq(PK.equal_test.p)}; ${F("pickdrafts")}). Some drafts are deeper than others, so this is expected. What matters is whether the star value drifts over time, because a drift would make an average over eleven drafts wrong for any one trade. Fitted with a linear trend across draft years, the star value rises by ${mil(PK.trend.all.b)} a draft (${pq(PK.trend.all.p)}). That rise rests on two drafts. Without 2015 (Connor McDavid, Jack Eichel) and 2016 (Auston Matthews), the trend falls to ${mil(PK.trend.without_2015_2016.b)} a draft and is not statistically significant (${pq(PK.trend.without_2015_2016.p)}).`));
add(P(`The model therefore uses one star value for every draft, fitted on all eleven, so each club is taken to expect the same value from a given draft position each year and an exceptional draft as noise. A star value for each trade season, fitted only on drafts whose control had run out by then, would rest the early trade seasons on two or three drafts. The 2015 and 2016 drafts finished after most of the trades studied, so the fit without them, ${mil(PK.sensitivity.star)}, is reported beside it as a sensitivity; it lowers each pick's value by ${pct(1 - PK.sensitivity.star / STAR.b, 0)}.`));
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
add(P("A pick is often traded before anyone knows its draft position, so one is assigned in three ways, by what was known on the trade date:"));
add(BULLET(`A pick traded during its own draft is given its actual draft position (${PK.traded.methods["actual slot (traded during the draft)"]} of the ${comma(PK.traded.n)} traded picks).`));
add(BULLET(`A pick for the coming draft, traded once that season's regular season has started, is given the draft position implied by its original team's place in the standings on the trade date, worst first, by points percentage (${PK.traded.standings_n}). For ${PK.traded.within3} of them this lands within three places of the pick's actual draft position, and the median miss is ${f1(PK.traded.median_gap)}.`));
add(BULLET(`A pick traded before that season starts, or for a later draft, is given the average star probability of its round (${PK.traded.methods["round average (before the season's first game)"] + PK.traded.methods["round average (a later draft)"]}).`));
add(P(`The round average is used because a team's draft position says little about its position a year or two later. Across the 2005 to 2026 drafts, a team's own first-round position correlates ${f2(LIN.corr1)} with its position in the next draft and ${f2(LIN.corr2)} with its position two drafts later, and moves a median of ${f1(LIN.median_move)} places in a year. The draft position is not purely random, so the round average loses some information. Valued at the positions teams went on to pick, the next first-round pick of a team that just picked in the top five was worth ${mil(LIN.top5_later)} on average, and that of a team that just picked 25th or later ${mil(LIN.bottom_later)}, against the round average of ${mil(LIN.round_avg)}. The round average therefore undervalues a weak team's future first-round pick and overvalues a strong team's; it is kept for its simplicity, and the difference is stated as a limitation. The draft lottery and the reordering of playoff teams are not modelled, and a conditional pick is valued as if its condition were met.`));
add(P(`The 2019 second-round pick Montreal received was traded before the 2018-19 season began, so it is given the average star probability over round 2's draft positions, ${pct(TPK.star_chance, 2)}, and is worth ${f4(TPK.star_chance)} × ${mil(STAR.b)} = ${mil(TPK.value)}. It became the ${TPK.actual_slot}th pick.`));

// =====================================================================================================================
// 7. PROSPECTS
// =====================================================================================================================
add(H1("7. Prospects"));
add(P("A prospect is a drafted player the player model does not yet value: a skater with no NHL season of 10 or more games in the three before the valuation season, or a goaltender with no NHL game in the six before it. The six seasons match the goaltender forecast, which uses any NHL season in the three before and the three before those when the last is missing. This boundary means no player is valued twice or by neither model at a given valuation date."));
add(P(`The prospect model is fitted on the 2,316 players drafted from 2007 to 2017, in each season from D+1 on in which a player was still a prospect and his club still controlled him. The outcome is his remaining surplus: the surplus he went on to deliver from that season to the end of club control, priced as in Section 6. A prospect traded between the draft and the start of D+1 is valued as in D+1.`));
add(H2("Draft position, and how its value fades"));
const A10 = "picks 1-10", A37 = "rounds 3-7", AALL = "all drafted players";
add(P(`At the draft, a pick is worth its draft position's star probability times the star value. A prospect starts with his pick's value; the question is how that value changes while he remains unproven. The answer depends on when drafted players reach the NHL. Of the ${comma(PK.n)} drafted players, ${f1(everA(AALL))}% played an NHL season of 10 or more games (a goaltender, an NHL game) before their club's control ended (${F("arrival")}). Of the 110 top-ten picks, ${f1(cumA(A10, 1))}% had reached the NHL by D+1, ${f1(cumA(A10, 2))}% by D+2, and ${f1(cumA(A10, 3))}% by D+3. Of the picks from rounds 3 to 7, ${f1(cumA(A37, 3))}% had reached it by D+3 and ${f1(cumA(A37, 4))}% by D+4, and ${f1(everA(A37))}% ever did. A top pick still a prospect in D+4 is unusual, and later picks who reach the NHL at all reach it later.`));
add(FIGURE("arrival", "fig_arrival.png", "When drafted players reach the NHL",
  "Drafted players of 2007 to 2017, without the six who died. Each line is the share of a draft group's players who had reached the NHL by each season; the gap above a line at D+9 is the share who never did. Reaching the NHL means a first NHL season of 10 or more games (for a goaltender, a first NHL game), the point at which he is valued by the player model; only seasons within club control are counted."));
add(P("I regressed each prospect's remaining surplus on the star probability for his draft position, interacted with an indicator for each season from D+1 to D+4 and one for D+5 onwards, with no intercept. The coefficient for each season is that season's star value: the surplus value if a prospect in that season were certain to become a star."));
add(EQ(["remaining surplus = star value for D+n × star probability + error"]));
const S_ = PR.star;
add(P(`For example, a #10 pick (star probability ${pct(PS["10"])}) who is still a prospect in D+3 is worth ${f3(PS["10"])} × ${mil(S_["2"].b)} = ${mil(PS["10"] * S_["2"].b)}. A prospect keeps most of his draft position's value through D+3 and loses most of it over the next two seasons (${T("pstar")}), because of who is left: by D+4, most top picks who will reach the NHL have done so. The prospects left are mostly later picks and top picks who missed, and among them draft position no longer distinguishes those who will succeed from those who will not.`));
add(TT("pstar", "The star value for a player still a prospect, by season"));
add(TABLE(["Season", "Prospect-seasons", "Star value (s.e.)", "p-value", "#1 pick", "#13 pick", "#32 pick"],
  G5.map((g) => [g === "0" ? "D+1 (at the draft)" : SEAS[g], comma(S_[g].rows), `${money(S_[g].b)} (${f2(S_[g].se)})`, pfmt(p2(S_[g].b, S_[g].se)), money(S_[g].b * PS["1"]), money(S_[g].b * PS["13"]), money(S_[g].b * PS["32"])]),
  [2000, 1600, 1600, 900, 1100, 1100, 1100], [1, 2, 3, 4, 5, 6]));
add(CAPTION("Drafted players of 2007 to 2017 still prospects, within club control. Star value in millions of dollars at the 2025-26 cap; one regression with a full set of interaction terms, standard errors clustered by player, since one player appears in several seasons; two-sided p-values. From D+5 on the rows are prospect-seasons from D+5 to D+8 pooled. The pick columns multiply the star value by the star probability for the draft position."));
add(H2("A separate star value for each season"));
add(P(`In the adopted regression each season from D+1 to D+4 has its own star value, and the seasons from D+5 on, where few prospects remain and little value is left, share one. Three simpler alternatives were tested and rejected. Each restricts how the star value may change from one season to the next, and each was fitted on the same prospect-seasons and scored the same way (${T("fade")}, ${F("fade")}). The first is one value for all seasons: the draft-day value kept for as long as a player remains a prospect (fitted: ${mil(FC["no fade"][0])}). The second is a straight-line decline: a starting value plus a fixed change for each season since the draft (${mil(FC["straight line"][0])} in D+1, falling ${mil(FC["straight line"][0] - FC["straight line"][1])} a season). The third is the same percentage decline each season (${mil(FC["same percentage"][0])} in D+1, keeping ${pct(FC["same percentage"][1] / FC["same percentage"][0])} each season).`));
add(FIGURE("fade", "fig_star_fade.png", "The star value by season, and three rejected alternatives",
  "Orange: each rejected alternative, fitted on the same prospect-seasons. Blue: the adopted star values with 95% intervals; from D+5 on, one shared value. Millions of dollars at the 2025-26 cap."));
add(TT("fade", "Each alternative for the star value against the adopted one"));
const FR = [["A separate value for each season (adopted)", "separate", null], ["One value for all seasons", "no fade", "traded total: no fade"], ["Straight-line decline", "straight line", "traded total: straight line"], ["Same percentage decline each season", "same percentage", "traded total: same percentage"]];
const fadeRows = FR.map(([lab, k, tk]) => [lab, f4(FS[k].rmse_M), FS[k].redraws_adopted_lower === null || FS[k].redraws_adopted_lower === undefined || Number.isNaN(FS[k].redraws_adopted_lower) ? "-" : pr(redrawP(FS[k].redraws_adopted_lower)), f2(FC[k][4]), money(FS[tk || "traded total: separate"].total_M), String(FS[tk || "traded total: separate"].below_zero)]);
add(TABLE(["Alternative", "Held-out error", "One-sided p", "Star value, D+5", "196 traded prospects, draft position alone", "Values below zero"],
  fadeRows, [3200, 1300, 1100, 1200, 1700, 1100], [1, 2, 3, 4, 5], bestKeys(fadeRows, [1], 4), 16));
add(CAPTION(`Held-out error: each draft predicted from a fit without it; root mean squared error in millions of dollars of remaining surplus per prospect-season, over ${comma(FS.separate.rows)} prospect-seasons; the lowest is in bold. One-sided p: the share of 2,000 redraws of the drafts in which the adopted model's error is not lower than the alternative's. prospect_fade_rules.py, run on today's data.`));
add(P(`One value for all seasons predicts worse than a separate value for each season (${pq(redrawP(FS["no fade"].redraws_adopted_lower))}) and nearly doubles the traded prospects' value. The straight-line and same-percentage declines predict about as well (p = ${f3(redrawP(FS["straight line"].redraws_adopted_lower))} and ${f3(redrawP(FS["same percentage"].redraws_adopted_lower))}), so the choice does not rest on prediction. I chose a separate value for each season for two reasons. It assumes no shape for the decline, and the estimates hold through D+3 and then fall, which matches when top picks reach the NHL. And the straight-line decline falls past zero: from D+8 a top pick is valued below a late pick, and it puts ${FS["traded total: straight line"].below_zero} of the traded prospects below zero. Equal steps from D+1 to D+4 are not rejected at the 5% level (p = ${f3(FS["equal steps, D+1 to D+4 (Wald)"].p)}), which is why the straight-line decline predicts about as well.`));
add(H2("A prospect's own outcome in the fit"));
add(P(`A prospect drafted from 2007 to 2017 is valued from a fit that contains his own outcome. Refitting without each prospect's own draft as the main value was rejected for two reasons: it would take eleven fits for each season, and the prospect values would no longer use the same star value as the draft picks traded beside them. His value with his own draft left out is reported beside it; for the traded prospects together it is ${mil(PR.traded.own_out)} against ${mil(PR.traded.tot_drafted)}.`));

add(H2("Production"));
add(P(`Draft position is one element of what predicts a prospect's value; how much he scores after the draft is another. A player who scores at a high rate in junior, college, or a European league is more likely to reach the NHL and to contribute when he does. Scoring in different leagues is put on one scale with Bacon's NHL equivalency (NHLe) factors. A league's factor is the number of NHL points that one point in that league and season is worth; Bacon estimates it from players who played full seasons in two different leagues in consecutive years, adjusted for a year of development, on a rolling four-season window, so a league's factor changes over time. An OHL point was worth 0.136 NHL points in 2006-07 and 0.120 in 2025-26.`));
add(P(`A season's production is the player's points, from Elite Prospects, times his league-season's NHLe factor, per 82 games, counted for seasons of 10 or more games. His production level weights his three seasons before the valuation season 50/30/20, rescaled over the seasons he has, as each part of the model weights recent seasons. A prospect valued in D+1 is measured on D0, D-1, and D-2, the scoring scouts saw before the draft. A prospect with no counted season (${pct(PR.no_record_share)} of prospect-seasons; ${PR.no_record_by_k["0"] + PR.no_record_by_k["4+"]} of the ${Object.values(PR.no_record_by_k).reduce((a, b) => a + b, 0)} in D+1 or from D+5 on) has a production level of zero, so he is valued on his draft position alone where it is in the model. An indicator for having no record was tested and dropped: it was not statistically significant at the 5% level in D+1 or D+2 (p = 0.053 and 0.067), its D+3 coefficient rests on a single prospect-season, from D+4 it is exactly zero, and without it the held-out error is unchanged. The median production level rises from ${f1(PR.median_prod["0"])} NHLe points per 82 games in D+1 to ${f1(PR.median_prod["4+"])} from D+5 on. Goaltenders stay on draft position alone, since NHLe converts only skater scoring and says nothing of goaltender performance.`));
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
add(H2("Production added to draft position"));
add(P(`Production alone predicts worse than draft position alone (one-sided p = ${f3(redrawP(NL.production.redraws_beating_slot))} that it is better), so production does not replace draft position at the draft. Added to draft position, linear production lowers the error in each season from D+1 to D+4, but the improvement is not statistically significant at the 5% level (p = ${f3(redrawP(NL["slot+production"].redraws_beating_slot))}). Linear and squared production added to draft position is (p = ${f3(redrawP(NL["slot+production curved"].redraws_beating_slot))}), and so is the adopted combination (p = ${f3(redrawP(NL.chosen.redraws_beating_slot))}).`));
add(H2("Production squared"));
const FM = PR.forms;
add(P(`With linear production, each additional NHLe point adds the same dollars. With production squared, each point adds more the higher a prospect already scores. It was added because most of a pick's surplus comes from the few players who become stars. Draft position accounts for part of this, since the first pick's star probability is about ten times the 32nd's. But every prospect at a draft position has the same star probability whatever he scores, and linear production then gives the highest scorers, the prospects most likely to become stars, the same dollars per point as everyone else. The squared term is compared with other forms of production within the full model once age has been added.`));
const AD = PR.adopted;
const turn = (g, age) => -(AD[g].terms.nhle82.b + AD[g].terms.prod_x_age18.b * (age - 18)) / (2 * AD[g].terms.nhle82_sq.b);
add(H2("Production in place of draft position from D+4"));
const B = PR.build;
add(P(`Once production is in the model, draft position stops carrying information in D+4: its coefficient is ${mil(B["+ production squared"]["3"].terms.p_star.b)} (${pq(B["+ production squared"]["3"].terms.p_star.p)}). ${B["+ production squared"]["4+"].terms.p_star.b < 0 ? `From D+5 on it is negative, ${mil(B["+ production squared"]["4+"].terms.p_star.b)} (${pq(B["+ production squared"]["4+"].terms.p_star.p)}), which would value a top pick below a later pick with the same production and makes no logical sense.` : `From D+5 on it is ${mil(B["+ production squared"]["4+"].terms.p_star.b)}, indistinguishable from zero (${pq(B["+ production squared"]["4+"].terms.p_star.p)}).`} In the adopted model draft position is kept from D+1 to D+3, and production alone is used from D+4.`));
add(P(`A separate production rate for defencemen was also tested (${T("prod")}). It changes the held-out error by ${f2(100 * (NL["slot+production by position"].rmse_M / NL["slot+production"].rmse_M - 1))}% against one rate, and its improvement over draft position alone is less consistent (p = ${f3(redrawP(NL["slot+production by position"].redraws_beating_slot))} against ${f3(redrawP(NL["slot+production"].redraws_beating_slot))}). One rate is kept.`));
add(P("With production, the model values a prospect in season D+n as follows, where S is the star probability for his draft position and P his production level. Each term is interacted with the season indicators, so the coefficients a, b, and c take a separate value in each season:"));
add(EQ(["D+1 to D+3:  remaining surplus = a × S + b × P + c × ", ["^", "P", "2"], " + error"]));
add(EQ(["D+4 and later:  remaining surplus = b × P + c × ", ["^", "P", "2"], " + error"]));
add(H2("Age"));
add(P("A player who scores at a given rate at 18 is commonly rated a better prospect than one who scores at the same rate at 20: the younger player is further from his peak. Age is the player's age on September 15 of the valuation season, the date the CBA uses. A player is first eligible for the draft in the year he is 18 by September 15, so in D+1 a player drafted at his first opportunity is 18 to 19, and one drafted a year later 19 to 20. Within a season's regression each prospect is the same number of seasons from his draft, so a prospect a year older also scored his points, and was drafted, a year older; across seasons, age and seasons since the draft move almost one for one, which is why age is compared only within a season."));
add(TT("age", "Each way of adding age, against the model without it"));
const ALR = [["Without age (the production model above)", "chosen"], ["Plus age: a flat amount per year", "+ age"], ["Plus age discounting production, each season", "+ age x production"], ["Plus both", "+ age and age x production"], ["Adopted: age discounting production, D+1 to D+4", "age x production, seasons 0-3"]];
const ageRows = ALR.map(([lab, k]) => [lab, f4(AL[k].rmse_M), k === "chosen" ? "-" : `${f2(100 * (AL[k].rmse_M / AL.chosen.rmse_M - 1))}%`, k === "chosen" ? "-" : pr(redrawP(AL[k].redraws_beating_chosen))]);
add(TABLE(["Candidate", "Held-out error", "vs without age", "One-sided p"], ageRows, [4900, 1500, 1600, 1640], [1, 2, 3], bestKeys(ageRows, [1], 4), 16));
add(CAPTION("Each candidate keeps the production model (draft position in D+1 to D+3, linear and squared production) and adds the age term shown; one-sided p compares it with the model without age. With both terms against the discount alone, p = 0.617. Held-out error as above; prospect_age_look.py, run on today's data."));
add(H2("Age as a discount on production"));
add(P(`Two forms were tested. Age as a flat amount subtracts the same dollars for each year of age, whatever the player scores. Age discounting production makes each point worth less the older the player was when he scored it. Both improve on the model without age and are statistically significant at the 5% level (p = ${f4(redrawP(AL["+ age"].redraws_beating_chosen))} and ${f4(redrawP(AL["+ age x production"].redraws_beating_chosen))}), and the discount improves the held-out error more (${f2(100 * (AL["+ age x production"].rmse_M / AL.chosen.rmse_M - 1))}% against ${f2(100 * (AL["+ age"].rmse_M / AL.chosen.rmse_M - 1))}%). I chose the discount because it is the larger gain and it measures what age was included for: how much a player's scoring says about him given the age at which he scored. Both terms together are no better than the discount alone. From D+5 on the discount adds nothing, so it applies from D+1 to D+4.`));
add(P(`In D+2, each year of age lowers the value of each NHLe point by $${f3(-AD["1"].terms.prod_x_age18.b)} million (${pq(AD["1"].terms.prod_x_age18.p)}): of two prospects with 10 points, the one a year older, who scored them a year older, is worth ${mil(-10 * AD["1"].terms.prod_x_age18.b)} less. ${F("prospect")} shows the adopted model for a prospect drafted 13th, in D+2, at three ages.`));
add(H2("Which production terms age discounts"));
const AFR = [["Production × age (adopted)", "adopted"], ["Both production and its square discounted", "both"], ["Production squared × age, in place of production × age", "sq_only"], ["One discount on all of production", "share"], ["Age-adjusted points in both terms", "adjusted"]];
add(P(`The adopted term discounts linear production: a point is worth b + e × (age − 18) plus the squared term's share, and the squared term is not discounted. So a year of age costs a low scorer a larger share of his production's value than a high scorer. Four forms that reach the squared term were tested (${T("ageform")}). None predicts left-out drafts better at the 5% level (one-sided p from ${f3(Math.min(...AFR.slice(1).map(([, k]) => AF[k].p_vs_adopted)))} to ${f3(Math.max(...AFR.slice(1).map(([, k]) => AF[k].p_vs_adopted)))}), and they would move the cost of age from low scorers to high scorers. The discount on linear production alone was kept.`));
add(TT("ageform", "Forms of the age discount"));
const ageFormRows = AFR.map(([lab, k]) => [lab, f4(AF[k].rmse_M), f4(AF[k].rmse_D1_D4), k === "adopted" ? "-" : pr(AF[k].p_vs_adopted)]);
add(TABLE(["Form", "Held-out error", "D+1 to D+4", "One-sided p, better than adopted"], ageFormRows, [4900, 1500, 1500, 1740], [1, 2, 3], bestKeys(ageFormRows, [1, 2], 4), 16));
const AC_ = PR.age_cost;
const ac = (arm, s, pts) => AC_.find((r) => r.arm === arm && r.season === s && r.points_per_82 === pts);
add(CAPTION(`prospect_age_form_look.py (October 19, 2026, on today's rows); its own refit gives the adopted form ${f4(AF.adopted.rmse_M)}. What a year of age costs, D+1, as a share of production's value: adopted ${pct(ac("production x age (adopted)", "D+1", 10).share, 0)} at 10 points per 82 and ${pct(ac("production x age (adopted)", "D+1", 20).share, 0)} at 20; both terms discounted ${pct(ac("+ production squared x age", "D+1", 10).share, 0)} and ${pct(ac("+ production squared x age", "D+1", 20).share, 0)}.`));
add(H2("Three forms of production in the full model"));
add(P(`With age in the model, ${T("forms")} compares three forms of production: linear production, linear and squared production (adopted), and production squared alone.`));
add(TT("forms", "Three forms of production in the adopted model"));
const FMR = [["Linear production", "linear production"], ["Linear and squared production (adopted)", "adopted"], ["Production squared alone", "production squared alone"]];
const formRows = FMR.map(([lab, k]) => [lab, f4(FM[k].rmse), ...G5.map((g) => f4(FM[k].by_k[g])), k === "adopted" ? "-" : (k === "linear production" ? `adopted better: ${pr(FM[k].p_adopted_better)}` : `adopted better: ${pr(FM[k].p_adopted_better)}`), money(PR.forms_traded[k].total)]);
add(TABLE(["Form", "Held-out error", "D+1", "D+2", "D+3", "D+4", "D+5 and later", "Head to head (one-sided p)", `${PR.traded_skaters} traded skaters`],
  formRows, [2200, 900, 760, 760, 760, 760, 900, 1500, 1060], [1, 2, 3, 4, 5, 6, 8], bestKeys(formRows, [1, 2, 3, 4, 5, 6], 4), 15));
add(CAPTION("Each form keeps the adopted structure: draft position in D+1 to D+3 and production discounted by age in D+1 to D+4. Held-out error as above, from the age test's procedure (its adopted error reproduced); head to head, p is the share of redraws in which the adopted form's error is not lower than the other form's. The last column is the traded drafted skaters' total value, $M at the 2025-26 cap."));
add(P(`Linear and squared production predicts better than linear production alone (one-sided p = ${f3(FM["linear production"].p_adopted_better)}). Production squared alone, without the linear term, predicts about as well (held-out error ${f4(FM["production squared alone"].rmse)} against ${f4(FM.adopted.rmse)}; p = ${f3(FM["production squared alone"].p_adopted_better)} that the adopted form is better, ${f3(FM["production squared alone"].p_better_than_adopted)} that squared alone is). It was not adopted because it would raise the traded skaters' value from ${mil(PR.forms_traded.adopted.total)} to ${mil(PR.forms_traded["production squared alone"].total)} without predicting better. With the squared term in, the linear coefficient is not the value of an extra point: an extra point adds the linear coefficient plus twice the squared coefficient times the player's production, so its value grows with production. In the adopted model, with its age discount, an extra point in D+2 for a player drafted at his first opportunity is worth less than nothing only below ${f1(turn("1", 19))} points, under the 25th percentile of ${f1(PR.pct_d2["25"])}. The linear coefficient determines where the value is lowest; it is not evidence that a little scoring lowers a prospect's value.`));
add(P(`Linear production's coefficient is not statistically significant at the 5% level in any season of the adopted model (${T("adopted")}), and it stays: its p-value is not the test of whether it belongs. With production × (age − 18) in the model, b is the linear value of a point for a prospect who is exactly 18 on September 15, and each year older adds e. Measuring age from another starting age changes b and its p-value but no value, because the change in b offsets the change in the age term: the test that b is zero in every season gives p = 0.062 with age measured from 18, 0.006 from 19, and 0.0003 from 20, on the same fitted values. Without linear production, a point's linear value would be forced to zero at whichever age is chosen, so that choice would set the values: the traded drafted prospects would be worth between $75.34 million and $88.09 million as the starting age moves from 18 to 21, against ${mil(PR.traded.tot_drafted)} in the adopted model, and none of those versions predicts left-out drafts better (prospect_linear_drop_centre.py v1.1, October 22, 2026). The adopted form is the only one whose values do not depend on where age is measured from.`));
add(H2("The adopted model"));
add(P("The adopted model values a prospect in season D+n as follows, where A is his age on September 15 of that season. The coefficient e is the age discount: the change in the value of each point of production for each year of age. Age enters less 18, so the age term is zero for an 18-year-old."));
add(EQ(["D+1 to D+3:  value = a × S + b × P + c × ", ["^", "P", "2"], " + e × P × (A − 18)"]));
add(EQ(["D+4:  value = b × P + c × ", ["^", "P", "2"], " + e × P × (A − 18)"]));
add(EQ(["D+5 and later:  value = b × P + c × ", ["^", "P", "2"]]));
add(P(`${T("adopted")} gives the regression for each season, and ${T("build2")} builds the D+2 regression up one term at a time; Appendix B does the same for each other season.`));
const BROW = [["p_star", "Star probability (a)"], ["nhle82", "Production (b)"], ["nhle82_sq", "Production squared (c)"], ["prod_x_age18", "Production × (age − 18) (e)"]];
add(FIGURE("prospect", "fig_prospect.png", "A prospect drafted 13th, in D+2",
  `The adopted model's value against production level, at ages 19, 20, and 21 on September 15 of the valuation season, with Nick Suzuki at the trade. Vertical lines mark the 25th, 50th, 75th, and 90th percentiles of production level among prospects in D+2 with a record. Millions of dollars at the 2025-26 cap.`));
add(TT("adopted", "The adopted prospect model, by season"));
add(TABLE(["Term", ...G5.map((g) => SEAS[g])],
  [...BROW.map(([k, lab]) => [lab, ...G5.map((g) => cc(AD[g].terms[k], 3))]), ["Prospect-seasons", ...G5.map((g) => comma(AD[g].rows))], ["Players", ...G5.map((g) => comma(AD[g].players))], ["R-squared", ...G5.map((g) => f3(AD[g].r2))]],
  [2440, 1440, 1440, 1440, 1440, 1440], [1, 2, 3, 4, 5]));
add(CAPTION("Dependent variable: remaining surplus, $M at the 2025-26 cap. One regression with a full set of interaction terms and no intercept, drafted skaters 2007-2017; coefficient (standard error clustered by player) [two-sided p-value]; R-squared measured from zero. Production squared is in squared points (15 points enter as 225). A blank cell: the term is not in that season's model. The low R-squared reflects how uneven outcomes are: most prospects deliver no NHL surplus."));
const B2 = PR.build;
const BHEAD = { "draft position alone": "(1) Draft position\nalone", "+ linear production": "(2) + production", "+ production squared": "(3) + production\nsquared", adopted: "(4) Adopted:\n+ age" };
add(TT("build2", "The D+2 regression built up one term at a time"));
add(TABLE(["Term", ...Object.keys(BHEAD).map((s) => BHEAD[s])],
  [...BROW.map(([k, lab]) => [lab, ...Object.keys(BHEAD).map((s) => cc(B2[s]["1"].terms[k], 3))]), ["R-squared", ...Object.keys(BHEAD).map((s) => f3(B2[s]["1"].r2))]],
  [2440, 1800, 1800, 1800, 1800], [1, 2, 3, 4]));
add(CAPTION(`${comma(B2.adopted["1"].rows)} skaters who were prospects in D+2; as the previous table. Adding linear production lowers the star value's coefficient; adding its square raises R-squared further; adding age makes the square carry the value of production.`));
add(H2("Nick Suzuki"));
add(P(`Suzuki was traded at the start of his D+2 season. His draft position's star probability is ${pct(SZ.inputs.p_star)}, his production level is ${f1(SZ.inputs.nhle82)} NHLe points per 82 games (above the 90th percentile in D+2, ${f1(PR.pct_d2["90"])}), and he was ${f1(SZ.age)} on September 15, 2018, a player drafted at his first opportunity. ${T("suzuki")} builds his value from the D+2 regression.`));
add(TT("suzuki", "Nick Suzuki's value, term by term"));
add(TABLE(["Term", "His input", "Coefficient (D+2)", "Contribution"],
  [["Star probability for his draft position", f3(SZ.inputs.p_star), f3(SZ.coefs.p_star), money(SZ.parts.p_star)],
   ["Production", f2(SZ.inputs.nhle82), f4(SZ.coefs.nhle82), money(SZ.parts.nhle82)],
   ["Production squared", f2(SZ.inputs.nhle82_sq), f4(SZ.coefs.nhle82_sq), money(SZ.parts.nhle82_sq)],
   ["Production × (age − 18)", f2(SZ.inputs.prod_x_age18), f4(SZ.coefs.prod_x_age18), money(SZ.parts.prod_x_age18)],
   ["Value, adopted model", "", "", `**${money(SZ.value)}**`],
   ["Value on draft position alone", "", "", money(SZ.slot)],
   ["Value with his draft left out of the fit", "", "", money(SZ.own_out)]],
  [3500, 1800, 2000, 2340], [1, 2, 3]));
add(CAPTION("Millions of dollars at the 2025-26 cap. Contributions are input times coefficient and sum to the adopted value."));
add(P(`His scoring raises his value from ${mil(SZ.slot)} on his draft position to ${mil(SZ.value)}: his production and its square add ${mil(SZ.parts.nhle82 + SZ.parts.nhle82_sq)}, and ${mil(-SZ.parts.prod_x_age18)} is subtracted for his age. He was among the youngest a D+2 prospect can be; a prospect a year older with his production would be worth ${mil(-SZ.coefs.prod_x_age18 * SZ.inputs.nhle82)} less.`));
add(H2("Goaltenders and undrafted players"));
add(P("NHLe converts scoring, which does not measure a goaltender. Elite Prospects holds goaltenders' save percentages, but no factor translates a save percentage from one league to another, so a goaltender prospect is valued on draft position alone, with the star values above; a save-based measure is untested. Those star values pool skaters and goaltenders. When last measured (October 16, 2026), the star value from D+5 on, on draft position alone, was $2.01 million pooled, $0.16 million for skaters alone (p = 0.64), and $19.35 million for goaltenders alone: nearly all of it is goaltenders' signal. A separate goaltender star value is set aside for later work."));
add(P(`An undrafted player has no draft rights, so a club holds his NHL rights only through an NHL contract; one on a minor-league contract is worth nothing to an NHL club in this currency. An undrafted player on an NHL contract is valued with the same model, his star probability set to zero and his seasons counted from his first draft-eligible year. The model is fitted on drafted players, including many whose rights lapsed and who delivered nothing, while undrafted players on NHL contracts are players a club chose to sign, so it probably undervalues them.`));
add(H2("The traded prospects"));
const TR_ = PR.traded;
add(P(`From July 2017 to March 2022, clubs traded ${TR_.drafted} drafted prospects (${TR_.drafted_players} different players, as some were traded more than once) and ${TR_.undrafted} undrafted prospects on NHL contracts. The adopted model values the drafted prospects at ${mil(TR_.tot_drafted)} (${mil(TR_.slot_alone)} on draft position alone) and the undrafted at ${mil(TR_.tot_undrafted)}, the largest ${TR_.max_undrafted_name} at ${mil(TR_.max_undrafted)}. ${T("top10")} lists the ten most valuable. Of the drafted prospects, ${TR_.below_zero} are valued below zero, ${mil(TR_.below_zero_sum)} in total: prospects with that profile, a low scorer from a late draft position, delivered slightly negative surplus on average, because when such players reach the NHL their cost tends to exceed the value of the wins they deliver.`));
add(TT("top10", "The ten most valuable traded drafted prospects"));
add(TABLE(["Traded", "Player", "Drafted", "Season", "Production", "Age", "Draft position alone", "Adopted"],
  TR_.top10.map((t) => [t.date, t.name, `${t.draft} #${t.pick}`, t.season, f1(t.prod), f1(t.age), money(t.slot), money(t.value)]),
  [1100, 1900, 1100, 800, 1000, 700, 1500, 1100], [4, 5, 6, 7], new Set(), 16));
add(CAPTION("Production in NHLe points per 82 games; age on September 15 of the season of the trade; values in millions of dollars at the 2025-26 cap."));
add(H2("Production from D+5 on"));
add(P(`From D+5 on, neither production term is statistically significant at the 5% level, alone or jointly (chi-squared ${f2(PR.joint_late.chi2)} on 2 degrees of freedom, ${pq(PR.joint_late.p)}). Dropping them would value every prospect from D+5 on at zero, drafted or undrafted: the traded drafted prospects would fall from ${mil(PR.traded.tot_drafted)} to $58.13 million and the ${PR.traded.undrafted} undrafted prospects, all valued from D+5 on, from ${mil(PR.traded.tot_undrafted)} to zero. The held-out error from D+5 on would rise (0.7621 against 0.7567, $M a prospect-season), though not by a statistically significant amount (one-sided p = 0.27; prospect_term_check.py v1.1, October 22, 2026). Production was kept: valuing every late prospect at zero is a stronger claim than the data support, and late bloomers, whose scoring is the only sign of them, keep a value.`));

// =====================================================================================================================
// 8. THE TRADE ON ONE SCALE
// =====================================================================================================================
add(H1("8. The Trade on One Scale"));
const to25 = TRD.to_2025, A_ = TRD.assets, RET = TRD.retained, SD_ = TRD.sides;
add(P("Sections 2 to 7 value each asset at the trade date. Four rules turn those values into each club's side of a trade: one cap at which to add them, who pays retained salary, how much of the season is left on an in-season trade, and what to do with a contract signed on the trade date. Each was decided with options, set out below, and the Pacioretty trade is then added up under them."));
add(H2("Adding values at one cap"));
add(P(`A player's value comes out of the player model at the cap of his valuation season ($${f1(M(CAP18))} million in 2018-19), while picks and prospects are stated at the 2025-26 cap, because their values come from careers restated at it (Section 6). To add the assets of a trade they have to be at one cap. The options were each trade's own valuation season, shares of the cap, or one cap for every trade. One cap for every trade, the 2025-26 cap, was adopted: a player's value is multiplied by the 2025-26 cap over his valuation season's cap, ${f1(CAP25M)} / ${f1(M(CAP18))} = ${f3(to25)} for 2018-19. Each trade's own cap would leave trades from different seasons in different units, so they could not be compared or summed. One cap changes the size of a value but never its sign or its order within a trade.`));
add(H2("Retained salary"));
add(P(`A club trading a player can keep part of his cap hit. The options were to charge the acquiring club the full cap hit, or to charge it only the part it carries and charge the retained part to the club that kept it. The second was adopted: a retained share is a real cost to the club that kept it and a real relief to the club that received the player, and charging it to the acquirer would misstate both sides. The retaining club pays the retained share of each remaining season of the contract being played, discounted like the contract; extensions and control seasons are not retained. The retained amounts come from PuckPedia's trade ledger: 72 from its retained-salary fields and 15 recorded only in the text of the asset's row, Tatar's among them. In this trade Montreal kept $450,000 (${pct(RET["Max Pacioretty"].share, 0)}) of Pacioretty's 2018-19 cap hit, ${mil(RET["Max Pacioretty"].pv_2025)} at the 2025-26 cap, and Vegas kept $500,000 (${pct(RET["Tomas Tatar"].share, 1)}) of Tatar's in each of his three seasons, ${mil(RET["Tomas Tatar"].pv_2025)}.`));
add(H2("Trades during the season"));
add(P("A player traded during the regular season has already played part of it for the club that traded him. The options were to count the whole season for the acquiring club or to count only the part left. The part left was adopted, on both value and cap hit: the regular-season days left on the trade date, the trade day counted, over the season's days. The season's last day is the schedule's as published before the season, not the last game played; 2019-20's pause in March 2020 was not known before it happened, and using it would be look-ahead. A prospect keeps the full season, since his value is the surplus to the end of club control, of which the valuation season accounts for about 2%. This trade was made before opening night, on October 3, 2018, so the whole season was left."));
add(H2("A contract signed on the trade date"));
add(P(`Vegas signed Pacioretty to a four-year extension on the day of the trade. The options were to count a contract signed on the trade date in the acquirer's value, as the model first did, or to leave it out. Leaving it out was adopted: the contract did not exist when Vegas acquired him, and what Montreal gave up was one season of his old contract. A contract signed on the trade date therefore counts as signed after it. The rule applies to 15 contracts in the trades valued, each signed with the acquiring club: eight extensions (Pacioretty, Mark Stone, Jean-Gabriel Pageau, Justin Faulk, Seth Jones, Nick Jensen, Kyle Turris, and Darcy Kuemper) and seven restricted free agents who signed the day they were traded, who are valued as rights. With the extension, Pacioretty's value would have been ${mil(M(PAC.npv_with_extension) * to25)} at the 2025-26 cap instead of ${mil(A_[0].value)}.`));
add(H2("The trade"));
add(P(`${T("trade")} gives each asset two values at the 2025-26 cap: its value to the club that received it, which carries the cap hit less any retained part, and its value to the club that traded it, before the trade, when that club paid the whole cap hit. The retained part is the difference between them. A club's side adds what it received, with any retained salary it pays, and subtracts what it gave up (${T("sides")}, ${F("trade")}). Read this way, a retained share moves value from the retaining club to the acquirer once, and the two clubs' sides sum to zero.`));
add(TT("trade", "The trade, each asset at the trade date"));
const before_ = (a) => a.value - ((RET[a.asset] && RET[a.asset].pv_2025) || 0);
add(TABLE(["Asset", "Traded by", "Received by", "Valued by", "Value to the receiving club", "Retained part, paid by the trading club", "Value to the trading club before the trade"],
  A_.map((a) => [a.asset, a.to === "MTL" ? "Vegas" : "Montreal", a.to === "MTL" ? "Montreal" : "Vegas", a.kind === "player" ? "Player model (Sections 2-4)" : (a.kind === "pick" ? "Pick model (Section 6)" : "Prospect model (Section 7)"), money(a.value), RET[a.asset] ? money(-RET[a.asset].pv_2025) : "", money(before_(a))]),
  [1900, 1000, 1000, 1700, 1300, 1400, 1340], [4, 5, 6], new Set(), 16));
add(CAPTION("Surplus value in millions of dollars at the 2025-26 cap. Pacioretty's and Tatar's values are their player-model values at the 2018-19 cap times 1.201; the retained part is a cost to the club that kept it."));
add(TT("sides", "Each club's side of the trade"));
const side = (c) => SD_[c];
add(TABLE(["Club", "Received", "Given up", "Net: received less given up"],
  [["Montreal", money(side("MTL").received_M), money(side("MTL").given_M), `**${money(side("MTL").net_M)}**`],
   ["Vegas", money(side("VGK").received_M), money(side("VGK").given_M), `**${money(side("VGK").net_M)}**`]],
  [2600, 2300, 2300, 2440], [1, 2, 3], new Set(), 17));
add(CAPTION("Millions of dollars at the 2025-26 cap. Received: the assets each club received, at their value to it, and the retained salary it pays. Given up: the assets it traded, at their value to it before the trade."));
add(FIGURE("trade", "fig_trade.png", "The trade on one scale", "Each club's side of the trade at the trade date, in millions of dollars at the 2025-26 cap: what it received, what it gave up, and the difference."));
add(P(`Montreal received Tatar (${mil(A_[1].value)}), Suzuki (${mil(A_[2].value)}), and the pick (${mil(A_[3].value)}), and kept paying ${mil(RET["Max Pacioretty"].pv_2025)} of Pacioretty's cap hit: ${mil(side("MTL").received_M)} in all. It gave up one season of Pacioretty, worth ${mil(side("MTL").given_M)} to it at his full cap hit. Its side is ${mil(side("MTL").received_M)} less ${mil(side("MTL").given_M)}, ${mil(side("MTL").net_M)}, and Vegas's is the reverse, ${mil(side("VGK").net_M)}. At the trade date both players carried contracts priced above their forecasted performance, so each club took on negative surplus value in a player. Montreal took on more of it: Tatar's three seasons and the retained part of Pacioretty's cap hit cost it ${mil(-(A_[1].value - RET["Max Pacioretty"].pv_2025))}, against the ${mil(-side("MTL").given_M)} it shed with Pacioretty's season. Suzuki and the pick, worth ${mil(A_[2].value + A_[3].value)} together, more than covered the difference.`));

// =====================================================================================================================
// 9. LIMITS
// =====================================================================================================================
add(H1("9. What the Models Do Not Do"));
add(BULLET("Fitted on later seasons. The star values for picks and prospects are fitted on the 2007-2017 drafts, whose careers run past many of the trades valued, so a club at the trade could not have known them; a 2007-2017 draftee is also inside the regression that values him. The price line is fitted on contracts that started from 2018-19 to 2025-26, the goaltender price line on contracts that started from 2015-16 to 2025-26, the control-season weights on decisions about contracts that ended from 2018-19 to 2024-25, and the NHLe factors are one 2026 download of a table re-estimated with later seasons. Each runs past many of the trades it prices. The player forecast alone uses only seasons before the valuation season."));
add(BULLET("One price of a win. One price line prices each season of each valuation; the length premium is flat although it falls with quality, and restricted free agents are priced on the same line as unrestricted ones."));
add(BULLET("Cost of control. The arbitration price still sets a lower cost for first-round picks than clubs paid them, so picks may look more valuable relative to players than they are."));
add(BULLET("Goaltenders. The goaltender price line is fitted on the forecast before its age term and applied to the forecast with it, because clubs' pay follows the record; goaltender prospects share one star value with skaters."));
add(BULLET("Undrafted prospects. Only those on NHL contracts are valued, on a model fitted on drafted players, so an undrafted player is assumed to convert production as a drafted one does."));
add(BULLET("Arbitration eligibility. PuckPedia's flag is set at the contract's end, so a valuation dated earlier uses eligibility recorded at a later date."));
add(BULLET("The trade side. A conditional pick is valued as if its condition were met; the draft lottery and the reordering of playoff teams are not modelled; a pick for a later draft is valued at its round's average."));

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
