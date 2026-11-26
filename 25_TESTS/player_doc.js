// player_doc.js v1.0 -- builds "Valuing Players.docx" (40_DOCS/), the first of the four write-up chunks (WORK_QUEUE 0a).
//
// v1.0 (2026-11-25; Thomas: "Agreed, build it", on the outline agreed in session 2026-11-25). The player sections of
// "Valuing Players, Draft Picks, and Prospects" v5.0 (model_doc.js v5.0) made into a document of their own:
//   - Thomas's 55 paragraph edits to his copy of v5.0 (committed 1026401) carried in word for word, except where one of
//     his own comments on the same passage asks for a rewrite, and except four typing slips (each listed in the session
//     log 2026-11-25): "wseason" (his comment 16 marks it "error"), "defined as forward" (a forward), "Entry draft
//     results comes" (dropped with the draft sources), and "the players cap hit" (the player's);
//   - his 101 comments worked through (those on the player sections), under the writing-style skill v2.0: no forward
//     references, no script names or run dates, "compared with" for figures, RMSE (out-of-sample where the seasons were
//     not used), "regression", "dummy variable", "interaction term", "bandwidth", "year-over-year change", no first
//     person, no colons joining sentences;
//   - every tested choice re-measured on today's model (25_TESTS/model_choices_current.py v1.0, price_line_spec_tests.py
//     v1.2, the goaltender tests) and read from OUTPUT_DIR/player_doc/numbers.json (25_TESTS/player_doc_figures.py v1.0);
//     the model's own figures from OUTPUT_DIR/model_doc/numbers.json (model_doc_figures.py v4.3, refreshed 2026-11-25);
//   - the order changed so nothing is argued before it is introduced: the own rate, then comparable players, then the
//     starting level that blends them, then aging.
// v1.3 (2026-11-27; Thomas): Section 6 retitled "Limitations of the Player Model", his edit to his copy (552a8b7).
// v1.2 (2026-11-26; Thomas: "Yes, implement it", on the list agreed that day). His 25 edits to v1.1 (committed 8010f1f)
// carried in, except where the list corrects one: the comparables' age in Aging kept to the code's rule (his most recent
// counted season, skater_forecast.py age_last); "therefore 20 was chosen" cut (any NHL game next season is playing on); the
// control season's value restored; the arbitration reason the code's (the rebuilt start lags a rising forecast); the price
// line named; the games share's age curve turns at 36; the minus signs on the Pacioretty extension (computed, as before).
// His comments: the forecast's test table split into one table per step, the prose they repeat cut; the event sentence his
// rewrite; the significance sentence cut; the Game Value table two rows, every cell filled; the price-line alternatives
// and the floor shortened. From an outside review: Section 4's restated opening cut, a lead-in to the traded-player rules,
// goaltender errors as RMSE, Figure 2's axis label (model_doc_figures.py).
// v1.1 (2026-11-25; Thomas: "Yes, build it", on the shorter structure put to him that day). His three edits to v1.0
// (committed 56bc2cd) carried in; his two comments answered (the one-sided p-value defined in two sentences, no mention
// of bootstrap resamples). The xNPV formula once, in full, in Section 1; the glossary table cut, each term defined where
// it first appears; the three discounting subsections made one; the forecast's four test tables made one ("fc"), with
// each step's text giving its conclusion and the figure that matters; the price line's two test tables made one; the
// control seasons in one pass (value, cost, weight, walking away); the terms rule and its table moved to Appendix A; the
// Game Value check made the last step of the forecast; each repeated rule said once. Dropped as unsupported: "most for
// players under 22" (comparable players alone raise the RMSE as much for players 22 to 34).
// Two figures are not re-measured and are flagged in the session log: the control-season rules' 18% and 44% and the
// 13.1% exit after qualifying (DECISIONS D14(c), measured on an earlier price line), and the arbitration flag's checks.
//
// Run:  NODE_PATH=<folder with docx> node 25_TESTS/player_doc.js   (DOC_OUT=<file> to write elsewhere; LINT_OUT=<file.md>)

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType, HeadingLevel,
  BorderStyle, ShadingType, Footer, PageNumber, Math: OMath, MathRun, MathSuperScript, MathSubScript,
  MathFraction, MathSum, MathRoundBrackets,
} = require("docx");

const VERSION = "player_doc.js v1.3";
const ROOT = path.resolve(__dirname, "..");
const FIG = path.join(ROOT, "30_OUTPUT", "model_doc");
const N = JSON.parse(fs.readFileSync(path.join(FIG, "numbers.json"), "utf8"));
const N2 = JSON.parse(fs.readFileSync(path.join(ROOT, "30_OUTPUT", "player_doc", "numbers.json"), "utf8"));
if (!String(N2.script).startsWith("player_doc_figures.py v1.")) throw new Error(`player_doc numbers from ${N2.script}`);
const OUTFILE = process.env.DOC_OUT || path.join(ROOT, "40_DOCS", "Valuing Players.docx");
const TEXT = [];

// ---- formatting helpers (as model_doc.js v5.0) ---------------------------------------------------------------------------
const FONT = "Calibri";
const fx = (x, d) => Number(x).toFixed(d);
const f1 = (x) => fx(x, 1), f2 = (x) => fx(x, 2), f3 = (x) => fx(x, 3), f4 = (x) => fx(x, 4);
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
const TABS = ["ownT", "comps", "compT", "startT", "depT", "gs", "pp", "gsT", "gv", "pl", "term", "spec", "control", "pac"];
const APPX = { gsH: "A1", ppH: "A2", terms_ns: "A3" };
const FIGS = ["aging", "price"];
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
const H = N.heavy;
const CAP = H.cap, CAP25 = CAP["2025"], CAP18 = CAP["2018"], CAP25M = CAP25 / 1e6;
const M = (x) => x / 1e6;
const money = (x) => shareOf(x, CAP25M);                 // x in $M at the 2025-26 cap
const mil = (x) => `${shareOf(x, CAP25M)} of the cap`;
const money18 = (x) => shareOf(x, CAP18 / 1e6);           // x in $M at the 2018-19 cap
const PAC = H.players["Max Pacioretty"], TAT = H.players["Tomas Tatar"];
const PL = H.price_line, PLF = PL.fits, LK = PL.locked;
const GS = H.games_share.by_h, PP = H.participation.by_h;
const CT = H.control, AG = H.aging;
const GV = N.gv, GO = N.goalie, TRD = N.trade;
const perWin = (b) => b * CAP25M;
const gd = (pos, a) => AG.gdelta[`${pos}|${a}`];
const adoptedGS = GS["0"]["+ trailing WAR (adopted)"], adoptedPP = PP["0"]["+ contract status (adopted)"];
const ppKey = (h) => Object.keys(PP[h]).find((k) => k.includes("adopted"));
const pacS = PAC.seasons, tatS = TAT.seasons;
const sumPV = (s) => s.reduce((a, x) => a + x.pv_dollars, 0) / 1e6;
const NQ = Object.values(CT.plays_given_q_n).reduce((a, b) => a + b, 0);
const LEFT_Q = Object.keys(CT.plays_given_q).reduce((a, b) => a + CT.plays_given_q_n[b] * (1 - CT.plays_given_q[b]), 0) / NQ;
const bucketW = (b) => CT.qualify_p[b] * (CT.plays_given_q[b] === undefined ? 1 : CT.plays_given_q[b]);
const BUCKETS = [["star", "3 or more"], ["regular", "1 to 3"], ["fringe", "0 to 1"], ["negative", "below 0, or no forecast"]];
const CH = N2.choices, BASE = CH.base;
const AU = Object.fromEntries(N.audit.all.map((r) => [r.version, r]));
const AUC = Object.fromEntries(N.audit.common.map((r) => [r.version, r]));
const R1 = AU["R1 no games weighting"], R2 = AU["R2 counting season at 5 games"], R3 = AUC["R3 counting season at 20 games"], B0c = AUC.base;
for (const [k, v] of [["start", 1.1506], ["whole", 1.3569], ["war", 0.8054]]) {
  if (f4(BASE[k]) !== f4(v) || f4(AU.base[k]) !== f4(v)) throw new Error(`the build's ${k} is not ${v}`);
}
// p of a comparison: that the adopted model's error is not lower; a dagger marks a version with the lower RMSE, and
// its p is then that the version's error is not lower
const pB = (r, k) => (r[`p_build_better_${k}`] <= 0.5 ? pr(r[`p_build_better_${k}`]) : `${pr(r[`p_version_better_${k}`])}†`);
const G2 = N2.goalie, SP = N2.spec, E2 = N2.e2, A82 = N2.all82, W64 = N2.w6040, AB = N2.age_bands, DROP = N2.dropped;

const kids = [];
const add = (...xs) => xs.flat().forEach((x) => kids.push(x));
add(new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: "Valuing Players", bold: true, size: 40, font: FONT })] }));

// =====================================================================================================================
// OPENING (Thomas's edits to v5.0's first two paragraphs, the second sentence of the first changed for this document)
// =====================================================================================================================
add(P("An NHL trade exchanges assets of different kinds: players under contract, draft picks, and prospects who have not yet reached the NHL. To judge whether a club received more value than it gave, each asset has to be valued in one currency, as of the trade date. The following sections explain how a player under contract is valued in that currency."));
add(P("One real-life trade is used as an example throughout to demonstrate how the model values real assets. On September 10, 2018, the Montreal Canadiens traded Max Pacioretty to the Vegas Golden Knights for Tomas Tatar, Nick Suzuki, and a 2019 second-round pick. Pacioretty and Tatar were players under contract, Suzuki was a prospect drafted 13th overall in 2017, and the draft pick originally belonged to Columbus, which Vegas acquired from a previous transaction. This document values Pacioretty and Tatar."));
add(H2("The data and their sources"));
add(P("Performance is measured throughout by wins above replacement (WAR): the wins a player added to his team in a season, compared with what a replacement-level player would have added in the same minutes. A replacement-level player is a hypothetical player a club can sign or call up at about the league minimum at any time. In the WAR metric used here, this player is defined as a forward outside his team's top 13 in ice time or a defenceman outside its top 7. WAR suits this model because it is built from components that describe each part of a player's game, and is stated in wins, which is the on ice result which clubs ultimately buy with their money."));
add(P("The WAR statistic comes from Patrick Bacon, a data scientist who has published hockey models as TopDownHockey since late 2020 and co-founded HockeyStats.com, where his WAR, NHL equivalency, and draft models are published with their methods. His WAR is built from the NHL's play-by-play and shift records in six parts: even-strength offence and defence, power-play offence, penalty-kill defence, penalties drawn and taken, and shooting. The even-strength and special-teams parts come from a weighted ridge regression that estimates each player's effect on his team's expected goals for and against while separating him from his teammates and opponents (regularized adjusted plus-minus). Shooting is goals scored above expected goals, and goals are converted to wins at about five goals a win, recalculated each season."));
add(P("Three things make it a credible source for this model. Its method is published in full (hockeystats.com/methodology/war). At the team level, WAR explains 82% of the variation in standings points per 82 games from 2007-08 to 2020-21, according to Bacon's own published results. It is free, public, and available for each NHL skater and goaltender season from 2007-08 on, so each traded player can be valued. Bacon also openly states the limitations of the model. He writes that it \"places too much emphasis on shooting and not enough on play-driving,\" and that forwards who make dangerous passes are probably underrated by it."));
add(P("Contracts and cap hits come from PuckPedia, a salary-cap database that records each NHL contract's terms, its cap hit by season, its clauses, and its arbitration eligibility; it has been one of the main public sources of NHL contract data since CapFriendly was acquired by the Washington Capitals and closed in 2024. The trades from July 2017 to March 2022, with their assets and retained salary, come from CapFriendly's trade records, collected before it closed using the Internet Archive, and trades from June 2022 to March 2026 from PuckPedia's trade records. Cap hits of contracts that ended before 2018-19, which PuckPedia's export does not hold, come from CapWages, a second public cap database. Long-term injured reserve comes from Spotrac's injured-reserve log, a public record of each season's injured players and their reserve status. Players' ages and games come from the NHL's own records, and the game log data behind Game Value, the independent measure, from the NHL's play-by-play and shift data."));

// =====================================================================================================================
// 1. EXPECTED NET PRESENT VALUE (the formula once, in full; each later section supplies one part of it)
// =====================================================================================================================
add(H1("1. Expected Net Present Value"));
add(P("A club holds an asset only for a finite period of time, either determined by contract length or determined through the NHL's collective bargaining agreement (CBA). A player under contract delivers performance in each of those seasons, and the market price of that performance is what clubs would pay for it in the free agency market for players. In each season the club also pays the player's cap hit, the cost of his contract against the salary cap (its average annual value), whether that contract is an entry-level contract, a qualifying offer, or a negotiated deal. The asset's value to the club is the expected net present value (xNPV) of what it delivers beyond what it costs."));
add(P("Under a salary cap, extracting proper value out of assets is critical, because a club that pays a player less than the market would charge for his performance keeps the difference, and cap space can buy additional wins through investing it in more players."));
add(P("Expected net present value is defined as follows, counted from the valuation season (k = 0):"));
add(EQ(["xNPV = ", ["sum", "k", [["/", [SUB("p", "k"), SUB("V", "k"), " − ", SUB("C", "k")], DISC("k")]]], " + ", ["sum", "j", [["/", [SUB("W", "j"), ["()", [SUB("V", "j"), " − ", SUB("C", "j")]]], DISC("j")]]]]));
add(P("The valuation season is the season in which the asset is valued, starting July 1. A trade during a season is valued in that season, and a trade after its last regular-season game in the following one. The first sum runs over the seasons k of the player's contract. V_{k} is the projected market price of the performance he delivers in season k and C_{k} is his cap hit, both in that season's dollars, and p_{k} is his chance of playing in it, the probability that he plays at least one NHL game; each season is discounted by dividing by 1.03^{k}, 3% for each season ahead. The chance of playing multiplies the value side only, because a contract costs its cap hit whether or not the player plays, and an injured player or a player buried in the AHL still counts against the cap. The second sum is the terminal value, the xNPV of the control seasons j after his contract ends, the seasons in which his club keeps his rights as a restricted free agent; each is weighted by W_{j}, the chance that the club keeps him and he plays."));
add(H2("Cap growth and discounting"));
add(P(`Prices are measured as shares of the salary cap, because the salary cap limits how much or little a club can spend. The salary cap also grows each season, but a signed contract's value does not. For example, a $5 million cap hit was 6.3% of the 2018-19 cap of $${f1(M(CAP18))} million and 5.2% of the 2025-26 cap of $${f1(CAP25M)} million. The cap is projected to grow 3% a year from the valuation season's cap, so a season priced at a share s of the cap is worth s × cap × 1.03^{k} in that season's dollars. Discounting, done by dividing by 1.03^{k}, returns it to s × cap. On the value side, therefore, cap growth and discounting cancel. They cancel exactly for a price above the league minimum; a season priced at the minimum follows the league minimum's published schedule, so there they cancel only approximately. A cap hit is in fixed dollars, so on the cost side discounting is present. For example, a $5 million cap hit four seasons out counts as $5 million / 1.03^{4} = $4.44 million today, because it takes a smaller share of a larger cap. Every value in this document is therefore stated as a share of the salary cap.`));
add(P("One rate for both, 3%, was adopted because it makes a share of the cap mean the same in any season. A season's worth of performance is worth the same share of the cap whenever it comes, and only a fixed-dollar cost becomes cheaper with time. Three alternatives were considered and rejected. A discount rate above cap growth would need evidence that clubs value future cap room less than present cap room, which the data do not provide. No discounting would ignore that a fixed cap hit takes a smaller share of a growing cap. A rate that reflects how impatient clubs are was rejected because whether clubs are impatient is one of the questions the trade study is built to answer, so it cannot be built into the values it tests."));
add(P("The choice of 3% is an assumption. The cap grew 3.4% a year from 2015-16 to 2019-20, 0.6% a year through 2023-24, and 7.6% a year from 2023-24 to 2026-27. The rate matters most for long contracts at a flat cap hit, where it sets how much cheaper the later seasons become."));

// =====================================================================================================================
// 2. FORECASTING PERFORMANCE (each step with its formula, Pacioretty's number, and its test's conclusion; the test
//    results in one table at the end; the Game Value check as the last step)
// =====================================================================================================================
add(H1("2. Forecasting Performance"));
add(P("The forecast has three parts for each season k: his WAR per 82, r_{k}, his WAR scaled to 82 games; his games share, g_{k}, the share of his team's 82 games he plays in a season in which he plays at least one; and his chance of playing, p_{k}. His forecasted WAR is w_{k} = r_{k} × g_{k}, and V_{k} is the price of w_{k}. Each part is re-estimated for every valuation season using only seasons completed before it. The regressions shown in this document are those estimated for 2025-26, on seasons through 2024-25. A season counts as evidence of a player's ability when he played 10 or more games in it, and WAR in the 2019-20 and 2020-21 seasons, shortened due to Covid-19, is scaled to 82 games. A player's age in a season is his age on September 15 of that season, the date the CBA uses to set a player's age for a season."));
add(P(`The forecast's accuracy is measured on the valuation seasons 2015-16 to 2021-22: each player's forecast at each valuation season, estimated only on seasons before it, is compared with what he delivered in the valuation season and the five seasons after it (${comma(N.audit.rows_all)} player-seasons by 1,609 players). The measure is the out-of-sample root mean squared error (RMSE), the square root of the average squared difference between forecast and outcome, in the outcome's units; lower is better, and out-of-sample means that the seasons compared were not used in the estimation. It is taken at three points: the starting level and the forecast one to five seasons ahead, in WAR per 82, and season WAR, the chance of playing × WAR per 82 × games share compared with his WAR in the season, in wins. Season WAR is the quantity that is priced. Each choice below is compared with versions of the adopted model that change one setting, on the same player-seasons, in a table at the end of each step.`));
add(P("Each comparison reports a one-sided p-value, the probability of the adopted model's RMSE being at least this much lower than the other version's if the two forecast equally well. Below 0.05, the adopted model is statistically significantly better at the 5% level. Where a version has the lower RMSE, its p-value is instead that of the version being better, marked with a dagger (†)."));

// ---- each step's tested versions: one table at the end of the step, the adopted model on top ----------------------
// p of one measure, or a dash where the version leaves that measure unchanged
const pT = (r, k, col, base = BASE) => (Math.abs(r[col] - base[col]) < 1e-12 ? "–" : pB(r, k));
const fcRow = (lab, r, base = BASE) => [lab, f4(r.start), f4(r.whole), f4(r.war), pT(r, "start_sq", "start", base), pT(r, "whole_sq", "whole", base), pT(r, "war", "war", base)];
function TESTS(key, title, rows, first = false, ages = false) {
  rows.forEach((r) => { if (r.slice(1).some((c) => c === undefined || String(c).includes("NaN"))) throw new Error(`${key} row ${r[0]}`); });
  let head = ["Version", "Starting level", "One to five seasons ahead", "Season WAR", "p, starting level", "p, one to five ahead", "p, season WAR"];
  let body = [["Adopted", f4(BASE.start), f4(BASE.whole), f4(BASE.war), "-", "-", "-"], ...rows];
  let widths = [3360, 1000, 1080, 1000, 1060, 1080, 1060];
  if (ages) {   // the 35-and-over column: each row's key is its label in DEPK
    head = [...head.slice(0, 4), "One to five ahead, aged 35 and over", ...head.slice(4)];
    body = body.map((r) => { const ab = AB[DEPK[r[0]]]; if (!ab) throw new Error(`age band ${r[0]}`); return [...r.slice(0, 4), f4(ab[2]), ...r.slice(4)]; });
    widths = [2560, 960, 1020, 960, 1100, 1000, 1020, 1000];
  }
  add(TT(key, title));
  add(TABLE(head, body, widths, widths.map((_, i) => i).slice(1), new Set(), 15));
  add(CAPTION(first
    ? `Out-of-sample RMSE on the valuation seasons 2015-16 to 2021-22: the starting level and one to five seasons ahead in WAR per 82, season WAR in wins; all ${comma(N.audit.rows_all)} player-seasons unless a row says otherwise. Each row changes one setting of the adopted model. p: one-sided p-value that the adopted model's RMSE is not lower than the version's; † marks a version with the lower RMSE, whose p-value is then that its RMSE is not lower; – where the version leaves the measure unchanged.`
    : `Out-of-sample RMSE, as in ${T("ownT")}${ages ? `; aged 35 and over at the valuation season, ${comma(N2.age_band_n[2])} seasons played one to five seasons ahead` : ""}. Each row changes one setting of the adopted model; p and †: as in ${T("ownT")}.`));
}

add(H2("His own rate"));
add(P(`A single season of WAR is a noisy measure of a player's ability. A hot shooting season or an injury can influence it greatly. A skater's WAR in one season has a correlation of only ${f3(G2.s_r)} with his WAR in the next, across ${comma(G2.s_pairs)} pairs of consecutive seasons of 20 or more games. To account for the large variability of performance year over year, the forecast starts from his three most recent seasons:`));
add(EQ(["own rate = ", ["/", ["0.5", SUB("G", "1"), SUB("r", "1"), " + 0.3", SUB("G", "2"), SUB("r", "2"), " + 0.2", SUB("G", "3"), SUB("r", "3")], ["0.5", SUB("G", "1"), " + 0.3", SUB("G", "2"), " + 0.2", SUB("G", "3")]]]));
add(P("The player's own rate is comprised of r_{1}, his WAR per 82 games in the most recent season before the valuation season and G_{1}, his total games played in that season, r_{2} and G_{2} are the same for the season before that, and r_{3} and G_{3} for the one before that; only seasons of 10 or more games count. Each season's 50/30/20 weight is multiplied by its games, so a 20-game season counts for less than a full one. Players with fewer than three seasons have the weights rescaled over the seasons they have (62.5/37.5 for two), rather than a missing season counted as zero. A missing NHL season is not replacement-level performance, since it may have been spent in junior, in the AHL, or injured."));
const own = PAC.own_seasons;
add(P(`For Pacioretty at the trade, his three seasons before 2018-19 were ${listAnd(own.map((s) => `${f2(s.WAR_82)} WAR per 82 in ${s.syr}-${String(s.syr + 1).slice(2)} (${s.GP} games)`))}. His own rate is (0.5 × ${own[2].GP} × ${f2(own[2].WAR_82)} + 0.3 × ${own[1].GP} × ${f2(own[1].WAR_82)} + 0.2 × ${own[0].GP} × ${f2(own[0].WAR_82)}) / (0.5 × ${own[2].GP} + 0.3 × ${own[1].GP} + 0.2 × ${own[0].GP}) = ${f3(PAC.own_82)} WAR per 82.`));
const WROWS = ["33/33/33", "40/35/25", "40/40/20", "50/25/25", "50/35/15", "60/25/15", "60/30/10", "70/20/10"];
const Wn = WROWS.map((w) => [w, CH[`W ${w}`]]);
const w64 = W64["W 60/40 over two seasons"], w64b = W64.base;
// the claims below, checked on the figures they rest on
if (!Wn.every(([, r]) => r.start > BASE.start && r.war > BASE.war)) throw new Error("50/30/20 is not lowest at the start and on season WAR");
if (!["start", "whole", "war"].every((k) => w64[k] > w64b[k])) throw new Error("60/40 over two is not worse on all three measures");
const W4 = CH["W 40/35/25"];
add(P(`Among nine fixed weightings of the three seasons, 50/30/20 gives the lowest RMSE at the starting level and on season WAR; 40/35/25 is slightly lower one to five seasons ahead, a difference that is not statistically significant (p = ${f3(W4.p_version_better_whole_sq)}). Fixed weights also need nothing estimated from the data. The games weighting lowers the RMSE of season WAR, because a 20-game season says less about a player's ability than a full one (${T("ownT")}).`));
add(P(`Ten games, the line the CBA draws for a season of an entry-level contract, decides which seasons count. A line of 5 games gives a lower RMSE of season WAR (${pq(R2.p_version_better_war)}) but was not adopted, because the same line decides which players the player model values and which are prospects valued by the prospect model. A line of 20 games gives a higher RMSE, a difference that is not statistically significant (p = ${f3(R3.p_build_better_war)}).`));
TESTS("ownT", "His own rate: each version's out-of-sample RMSE", [
  ...Wn.map(([w, r]) => fcRow(`Weights ${w}`, r)),
  fcRow(`Weights 60/40 over two seasons (on its ${comma(W64.rows)} player-seasons; adopted ${f4(w64b.start)}, ${f4(w64b.whole)}, ${f4(w64b.war)})`, w64, w64b),
  fcRow("No games weighting", R1),
  fcRow("A played season at 5 or more games", R2),
  fcRow(`A played season at 20 or more games (on its ${comma(N.audit.rows_common)} player-seasons; adopted ${f4(B0c.start)}, ${f4(B0c.whole)}, ${f4(B0c.war)})`, R3, B0c)], true);

add(H2("Comparable players"));
add(P(`A player's own seasons are few and noisy, so the forecast also draws on players who resembled him at the same age, and on what they went on to do. Each player-season is described by four attributes: how his WAR divides among five components (even-strength offence, even-strength defence, power play, penalty kill, and shooting), his ice time per game, his level, and his year-over-year change. His level is his 50/30/20 WAR per 82 at that age, games-weighted as above, over seasons of 20 or more games; his year-over-year change is the change in his WAR per 82 from the season before. Each attribute is standardized within position (each measure minus its mean, divided by its standard deviation, so that minutes and wins are on one scale) and given equal weight, so the five style shares together share a quarter of the weight and the remaining attributes share a quarter each. The candidates are other players of the same position at the same age, in seasons before the valuation season. Each candidate's weight falls with his distance d from the player, the square root of the summed squared differences across the attributes:`));
add(EQ(["weight = exp", ["()", ["−", ["/", [["^", "d", "2"]], ["2", ["^", "h", "2"]]]]]]));
add(P(`Here h, the bandwidth, is the median distance between two player-seasons of the same position (${f2(AG.yardstick.F)} for forwards and ${f2(AG.yardstick.D)} for defencemen in the 2025-26 estimation). An exact match gets weight 1, a candidate one bandwidth away exp(−0.5) = 0.61, and one two bandwidths away exp(−2) = 0.14. This is kernel weighting (Nadaraya 1964; Watson 1964), an average in which closer cases count more, with no fixed number of neighbours. Pacioretty's ${PAC.comparables.n_at_age} candidates at ${PAC.age_last} carry weights that sum to ${f1(PAC.comparables.weight_sum)}; ${T("comps")} lists his five closest.`));
add(TT("comps", `Max Pacioretty's five closest comparable players at ${PAC.age_last}`));
add(TABLE(["Player", "Weight", `Level at ${PAC.age_last} (WAR per 82)`],
  PAC.comparables.top.map((c) => [c.name, f2(c.weight), f3(c.level)]), [4000, 2500, 3100], [1, 2]));
add(CAPTION(`Weight: exp(−d² / 2h²), 1 for an exact match. Level: each comparable player's 50/30/20 WAR per 82 at that age, games-weighted. Of Pacioretty's ${PAC.comparables.n_at_age} candidates.`));
add(P("The player's own season at that age is also in the pool, and it would be an exact match with weight 1. He is therefore left out of his own comparable players; otherwise his own level would enter the comparable players' level as well as his own rate, and be counted twice."));
add(P("A small or poorly matched group of comparable players could produce an extreme estimate on its own. To guard against that, the comparable players' average is mixed with the league average for the same position and age, which counts as ten extra comparable players, each an exact match:"));
add(EQ(["comparable players' level = ", ["/", [["sum", "i", [SUB("w", "i"), SUB("L", "i")]], " + 10 × league level"], [["sum", "i", [SUB("w", "i")]], " + 10"]]]));
add(P(`Here w_{i} is candidate i's weight and L_{i} is his level at that age. When the comparable players are many and close, their weights sum well above ten and they dominate; when they are few or distant, the league average takes over. Pulling a noisy average toward a group mean in this way lowers its expected error (Efron and Morris 1975). For Pacioretty, his candidates' weighted level of ${f3(PAC.comparables.weighted_mean_level)} and the league level for forwards at ${PAC.age_last} of ${f3(PAC.comparables.league_level)} give ${f3(PAC.comparables_level)}; with weights summing to ${f1(PAC.comparables.weight_sum)}, the league average makes up ${pct(10 / (PAC.comparables.weight_sum + 10))} of it.`));
const BKV = ["0.01", "1", "5", "20", "50"].map((k) => CH[`BK league weight ${k}`]);
const bkMax = Math.max(...BKV.flatMap((r) => ["start", "whole", "war"].map((k) => Math.abs(r[k] / BASE[k] - 1))));
const B1 = CH["B1 comparable players alone"], A1 = CH["A1 one yardstick for all players"], A2 = CH["A2 yardstick without self-pairs"];
if (!["start", "whole", "war"].every((k) => Math.abs(A1[k] - BASE[k]) < 0.00015 && f4(A2[k]) === f4(BASE[k]))) throw new Error("bandwidth claims");
add(P(`Ten is a judgement call. Any weight from 0.01 to 50 changes no out-of-sample RMSE by more than ${pct(bkMax, 2)}, while removing the league average altogether, from the comparable players' level and from their changes with age, raises the RMSE one to five seasons ahead (${T("compT")}). One bandwidth for all players, instead of separate numbers by position, and leaving pairs of two seasons by the same player out of the median distance each change no RMSE by more than 0.0001, but both are statistically significantly worse.`));
TESTS("compT", "Comparable players: each version's out-of-sample RMSE", [
  fcRow("One bandwidth for all players", A1),
  fcRow("Bandwidth without pairs of one player's seasons", A2),
  fcRow("Comparable players alone (no league weight)", B1),
  ...["0.01", "1", "5", "20", "50"].map((k) => fcRow(`League weight ${k} instead of 10`, CH[`BK league weight ${k}`]))]);

add(H2("The starting level"));
add(P("His own rate and his comparable players' level are blended into a starting level, his forecasted WAR per 82 in the valuation season:"));
add(EQ(["starting level = 0.65 × own rate + 0.35 × comparable players' level + aging"]));
add(P("The comparable players are chosen at the age he was in his most recent season of 10 or more games, and their level is measured at that age. A player whose most recent such season came before the season just completed has aged since then, so aging is the comparable players' average change in level from that age to his age in the valuation season."));
add(P(`For Pacioretty, his comparable players' level at ${PAC.age_last} is ${f3(PAC.comparables_level)}, and their change from ${PAC.age_last} to ${PAC.age_last + PAC.last_lag} is ${f3(PAC.path[PAC.last_lag])}. Therefore, his starting level is 0.65 × ${f3(PAC.own_82)} + 0.35 × ${f3(PAC.comparables_level)} − ${f3(Math.abs(PAC.path[PAC.last_lag]))} = ${f3(PAC.start)} WAR per 82. His poor 2017-18 season and his comparable players both pull his level below his two earlier seasons.`));
const KR = ["45", "55", "60", "70", "75"].map((k) => [k, CH[`K own ${k}%`]]);
const NS = CH["NS no step to the valuation season"];
if (!["start", "whole", "war"].every((k) => NS[k] > BASE[k])) throw new Error("no aging is not worse at all three points");
add(P(`Among shares of his own rate from 30% to 100% in steps of 5%, 65% gives the lowest RMSE at the starting level; on season WAR, 70% is slightly lower, a difference that is not statistically significant (${T("startT")}). The starting level is aged to the valuation season because a player a year older has aged a year; leaving that step out raises the RMSE at each of the three points.`));
TESTS("startT", "The starting level: each version's out-of-sample RMSE", [
  ...KR.map(([k, r]) => fcRow(`Share of his own rate ${k}%`, r)),
  fcRow("No aging to the valuation season", NS)]);

add(H2("Aging"));
add(P("Players change with age, and how much depends on the player. The starting level is carried forward one season at a time. At each age forward, the same pool of comparable players, chosen at the age of his most recent counted season, provides its average change in performance from one age to the next, blended with the league-average change at a weight of ten as above. The average change in WAR per 82 is then added to or subtracted from his starting level. Holding the pool fixed keeps each step tied to real players at the same age; choosing a new pool each year would match historical players to a version of him that the forecast itself produced the year before."));
add(P(`A player who leaves the league records no decline. If departures were left out, the average change at older ages would come only from players good enough to stay, and the forecast would understate aging. A player who leaves the NHL for good is therefore given one more season at replacement level (0 WAR), at his own most recent season's games total, so his departure counts as a decline. In the 2025-26 estimation, ${comma(AG.imputed)} departures enter this way among ${comma(AG.careers)} careers.`));
add(P(`On average a forward improves until 24 and declines after it, by about ${f2(-gd("F", 29))} WAR per 82 from 29 to 30 and ${f2(-gd("F", 34))} from 34 to 35 (${F("aging")}, left). Pacioretty's comparable players declined slightly faster than the league average, and his forecast falls from ${f2(PAC.forecast_path[0].rate_82)} WAR per 82 at 29 to ${f2(PAC.forecast_path[4].rate_82)} at 33 (${F("aging")}, right).`));
add(FIGURE("aging", "fig_aging.png", "Aging",
  `Left: the league-average change in level from one age to the next, by position, in the 2025-26 estimation, with departures entered at replacement level; each point is drawn at the age reached. Right: Max Pacioretty's forecasted WAR per 82 at the trade, from his comparable players' changes (blue) and, for comparison, from the league-average changes for forwards (orange); grey points are his three seasons before the trade.`));
const C25 = CH["C1 departed season at +0.25 WAR per 82"], C2_ = CH["C2 players who came back filled in"], C6 = CH["C6 departed season at 82 games"];
const C4 = CH["C4 no departed seasons filled in"], C3 = CH["C3 short next seasons filled in"];
add(P(`Three details of the departure rule were tested. The first is the level given to the departed season, zero, which was kept on principle as replacement level performance is what a club expects to get from the player it calls up in his place. The second decision is who counts as departed. A player who misses a season but plays again later did not leave for good, and counting his absence as a departure raises the RMSE one to five seasons ahead (${pq(C2_.p_build_better_whole_sq)}), as does counting a next season of 1 to 19 games as one (${pq(C3.p_build_better_whole_sq)}). The third is the games the departed season counts, which was decided to be his own most recent season's games played total, so the departure of a player already playing part-time is not weighted as a full season. The data do not distinguish this from a full 82 games (p = ${f3(C6.p_build_better_whole_sq)}). Leaving departures out altogether raises the RMSE of season WAR (p = ${f3(C4.p_build_better_war)}) and, for players 35 and over, the group the rule exists for, the RMSE one to five seasons ahead (${T("depT")}).`));
const DEPK = { Adopted: "base", "Departed season at -0.50 WAR per 82": "C1 departed season at -0.50 WAR per 82", "Departed season at -0.25 WAR per 82": "C1 departed season at -0.25 WAR per 82",
  "Departed season at +0.25 WAR per 82": "C1 departed season at +0.25 WAR per 82", "Players who came back counted as departures": "C2 players who came back filled in",
  "Next seasons of 1 to 19 games counted as departures": "C3 short next seasons filled in", "Departed season at 82 games": "C6 departed season at 82 games", "No departures counted": "C4 no departed seasons filled in" };
TESTS("depT", "Departures: each version's out-of-sample RMSE", [
  ...["-0.50", "-0.25", "+0.25"].map((v) => fcRow(`Departed season at ${v} WAR per 82`, CH[`C1 departed season at ${v} WAR per 82`])),
  fcRow("Players who came back counted as departures", C2_),
  fcRow("Next seasons of 1 to 19 games counted as departures", C3),
  fcRow("Departed season at 82 games", C6),
  fcRow("No departures counted", C4)], false, true);

add(H2("Games share"));
const gsSpecs = Object.keys(GS["0"]);
const GSROW = [["tr_gp_share", "Trailing games share"], ["exp_seasons", "NHL seasons since his debut"], ["age_c", "Age − 27.22"], ["age_c2", "(Age − 27.22)²"], ["tw_WAR", "Trailing WAR"], ["intercept", "Intercept"]];
const ageTurn = 27.22 - adoptedGS.terms.age_c.b / (2 * adoptedGS.terms.age_c2.b);
add(P("WAR accumulates with games, so the model needs to forecast the share of the 82 games he will play. A regression for each season ahead estimates that number from his 50/30/20 trailing games share, his 50/30/20 trailing WAR, his NHL seasons since his debut, and his age at the valuation season and its square. The two trailing measures are his 50/30/20 averages over seasons of 10 or more games, without the games weighting, because a games share already counts games:"));
add(EQ(["g = a + ", SUB("b", "1"), "G + ", SUB("b", "2"), "E + ", SUB("b", "3"), "A + ", SUB("b", "4"), ["^", "A", "2"], " + ", SUB("b", "5"), "W"]));
add(P(`Here g is his games share, G is his trailing games share, E is his NHL seasons since his debut, A is his age less 27.22, and W is his trailing WAR. Age enters less 27.22, the average age of the player-seasons in the 2025-26 estimation. Centring the age variable makes the intercept the games share of a player of average age. With its square, the effect of age changes as he ages; the share falls with age at a slowing rate and bottoms out at about ${Math.round(ageTurn)}. The forecast is capped at 1 and floored at 0. ${T("gs")} builds the regression for the valuation season up one term at a time.`));
const GSHEAD = { "games share": "Trailing games\nshare alone", "+ seasons since debut": "+ seasons since\ndebut", "+ age, age squared": "+ age, age\nsquared", "+ trailing WAR (adopted)": "+ trailing WAR\n(adopted)" };
add(TT("gs", "The games-share regression in the valuation season, built up one term at a time"));
add(TABLE(["Term", ...gsSpecs.map((s) => GSHEAD[s])],
  [...GSROW.map(([k, lab]) => [lab, ...gsSpecs.map((s) => cc(GS["0"][s].terms[k], 4))]),
   ["R-squared", ...gsSpecs.map((s) => f3(GS["0"][s].r2))]],
  [2140, 1875, 1875, 1875, 1875], [1, 2, 3, 4]));
add(CAPTION(`Least squares on ${comma(adoptedGS.n)} player-seasons by ${comma(adoptedGS.players)} players: each player's trailing inputs at a valuation season from 2008-09 to 2024-25, and his games share in that season, among seasons he played. Coefficient (standard error, clustered by player) [two-sided p-value]. R-squared: the share of the variation in the games share that the regression accounts for. The adopted column is the model's regression, coefficient for coefficient.`));
const D1 = CH["D1 games share as a fractional logit"], D2 = CH["D2 games share without age squared"];
const U1 = CH["U1 quality as rate per 82 (share and playing)"], U2 = CH["U2 games share + total above one win"], E3 = CH["E3 contract x quality"];
add(P(`Five alternatives were tested and rejected (${T("gsT")}). Assuming that every player plays all 82 games, with no games-share regression, raises the RMSE of season WAR. A fractional logit (Papke and Wooldridge 1996), a logistic curve fitted to the share so that every prediction lies between 0 and 1, predicts the games share better but season WAR worse, because it predicts worse for regulars who play most of the season, where the forecast matters most. Season WAR is also worse without age squared and with the inclusion of a term for trailing WAR above one win. It is worse, too, with WAR per 82 in place of his trailing WAR total, because the question is how much he plays, and that total already reflects how much he played.`));

add(H2("Chance of playing"));
const uc = adoptedPP.terms.under_contract;
add(P("The chance that he plays at least one NHL game in a season is a logistic regression for each season ahead. Its inputs are his age in that season, his trailing WAR and games share, his position, and whether he is under contract for that season as of the valuation date:"));
add(EQ(["log", ["()", [["/", ["p"], ["1 − p"]]]], " = a + ", SUB("c", "1"), "A + ", SUB("c", "2"), "W + ", SUB("c", "3"), "G + ", SUB("c", "4"), "D + ", SUB("c", "5"), "K + ", SUB("c", "6"), "U"]));
add(P(`Here p is his chance of playing in the season; A, W, and G are as in the games share. Three are dummy variables, each 1 or 0: D is 1 for a defenceman, K is 1 when he is under contract for the season, and U is 1 for a season with no contract record. The left side is the log of the odds of playing, p / (1 − p). Each coefficient is the change in the log odds for one more unit of its input, so e raised to it is the factor by which that unit multiplies the odds; being under contract for the season, for example, multiplies the odds of playing by e^{${f2(uc.b)}} = ${f1(Math.exp(uc.b))} (${pq(uc.p)}). Contract status is visible only from 2018-19, when the contract records start, so U marks the earlier seasons; without it, those seasons would read as seasons without a contract. ${T("pp")} builds the regression for the valuation season up one term at a time.`));
const ppSpecs = Object.keys(PP["0"]);
const PPROW = [["age", "Age − 27.22"], ["level", "Trailing WAR"], ["gp_share", "Trailing games share"], ["is_D", "Defenceman (D)"], ["under_contract", "Under contract for the season (K)"], ["contract_unknown", "No contract record, a season before 2018-19 (U)"], ["intercept", "Intercept"]];
add(TT("pp", "The chance-of-playing regression in the valuation season, built up one term at a time"));
add(TABLE(["Term", "Age alone", "+ trailing WAR, games\nshare, defenceman", "+ contract status\n(adopted)"],
  [...PPROW.map(([k, lab]) => [lab, ...ppSpecs.map((s) => cc(PP["0"][s].terms[k], 3))]),
   ["McFadden pseudo R-squared", ...ppSpecs.map((s) => f3(PP["0"][s].pseudo_r2))],
   ["Log-likelihood", ...ppSpecs.map((s) => comma(Math.round(PP["0"][s].loglik)))]],
  [2640, 2330, 2330, 2340], [1, 2, 3]));
add(CAPTION(`Logistic regression on ${comma(adoptedPP.n)} player-seasons by ${comma(adoptedPP.players)} players (valuation seasons 2008-09 to 2024-25), ${pct(adoptedPP.base)} of whom played. Coefficient on the log odds (standard error, clustered by player) [two-sided p-value]. McFadden's pseudo R-squared is one minus the regression's log-likelihood over that of a model with the intercept alone; higher is better. The model's own regression adds a negligible penalty (1e-4) against perfectly predicted outcomes; its coefficients differ from these by at most ${adoptedPP.gap_to_page_fit.toExponential(0)}.`));
add(P("Each season ahead has its own chance of playing, so a player can be absent one season and back the next. The event is at least one NHL game, because the games-share regression predicts how many games the player will play conditional on his playing in the season. Whether a past season is good evidence of his ability is a different question, which is why that line is 10 games."));
add(P(`Contract status moves the odds of playing the most of the dummy variables, so it is read on the valuation date itself rather than on July 1 of the valuation season. Read on July 1, the regression cannot see a contract signed later that summer.`));
if (f4(E3.war) !== f4(BASE.war)) throw new Error("the interaction term moves season WAR");
const P3 = AU["P3 no no-contract-record marker"];
add(P(`The regressions are estimated for each season ahead with at least 200 player-seasons of evidence: up to eight seasons ahead for the 2018-19 valuation season and twelve for 2025-26. Past that, the league-wide decline in expected WAR between the last two estimated seasons is continued. Appendix A gives each regression for each season ahead.`));

// ---- the games share's and the chance of playing's tested versions ---------------------------------------------------
add(TT("gsT", "The games share and the chance of playing: each version's out-of-sample RMSE"));
const gsfRows = [["Adopted", f4(BASE.share), f4(BASE.war), f4(BASE.logloss), "-", "-"],
  ["Every player plays all 82 games", "–", f4(A82.war), f4(BASE.logloss), "–", pr(A82.p_build_better)],
  ...[["Games share as a fractional logit", D1], ["Games share without age squared", D2], ["Games share with a term for trailing WAR above one win", U2],
      ["Quality read as rate per 82 (games share and chance of playing)", U1], ["Chance of playing with an interaction term, under contract × trailing WAR", E3]]
    .map(([lab, r]) => [lab, f4(r.share), f4(r.war), f4(r.logloss), pT(r, "share_sq", "share"), pT(r, "war", "war")])];
add(TABLE(["Version", "Games share", "Season WAR", "Log loss, chance of playing", "p, games share", "p, season WAR"], gsfRows,
  [3760, 1050, 1050, 1300, 1150, 1250], [1, 2, 3, 4, 5], new Set(), 15));
add(CAPTION(`Out-of-sample RMSE: the games share in share of 82 games, in seasons he appeared in; season WAR in wins. Log loss measures how far the forecast chances of playing sit from what happened; lower is better. The version with every player at 82 games has no games-share forecast. p and †: as in ${T("ownT")}; – where the version leaves the measure unchanged.`));

add(H2("Checking the forecast with Game Value"));
add(P("The forecast and the price of a season are both built from Bacon's WAR, and the trade study compares values with outcomes measured in WAR. Agreement could therefore reflect the quirks of Bacon's model rather than performance on the ice. To check that the forecast measures performance, it is compared with Game Value, a measure built from the NHL's play-by-play and shift records with no input from Bacon's WAR model. Game Value gives each skater on the ice an equal share of his team's expected goals for and against, adjusted for score-state (tied, leading, trailing), plus the value of the penalties he draws and takes; in its adjusted version (GV-adj), a player is also separated from his linemates and opponents at five-on-five. Across full seasons, team Game Value explains 58.3% of the variation in team goal differential."));
add(P(`A forecast that only repeated the errors in Bacon's WAR would have no higher a correlation with Game Value than the trailing WAR it is built from. Instead, its correlation is higher. Across ${comma(GV.n)} player-seasons by ${comma(GV.players)} players from 2017-18 to 2025-26, the forecast has a correlation of ${f3(GV.all.forecast[0])} with the same season's Game Value, compared with ${f3(GV.all.trailing[0])} for his trailing WAR, and the gap holds for forwards, for defencemen, and one season further ahead (${T("gv")}). Some agreement is expected regardless, since both measures describe the same games.`));
add(TT("gv", "Correlation of each measure with the same season's Game Value"));
const gvr = (lab, key, idx = 0) => [lab, ...["all", "F", "D", "next"].map((s) => (GV[s] && GV[s][key] ? f3(GV[s][key][idx]) : "–"))];
add(TABLE(["Measure", "All skaters", "Forwards", "Defencemen", "One season further"],
  [gvr("Trailing WAR, 50/30/20", "trailing"), gvr("Forecasted WAR", "forecast")],
  [4200, 1360, 1360, 1360, 1360], [1, 2, 3, 4], new Set(), 16));
add(CAPTION(`Pearson correlation with GV-adj, on ${comma(GV.n)} player-seasons (${comma(GV.n_next)} one season further).`));

// =====================================================================================================================
// 3. PRICING A SEASON
// =====================================================================================================================
add(H1("3. Pricing a Season"));
add(P("Now that the player model can forecast wins provided by a player and how the player performs over time, that forecasted performance must be converted into a market rate that teams pay for that performance level. To do so, each contract's cap hit, as a share of the cap in its first season, is regressed on the forecast of the player's WAR in that first season. This regression, the price line, adds an interaction term for defencemen and a term for the contract's length in years:"));
add(EQ(["cap share = α + ", ["()", ["β + ", SUB("β", "D"), "D"]], "w + γT"]));
add(P(`Here w is the player's forecasted WAR in the contract's first season, D is a dummy variable equal to 1 for a defenceman, and T is the contract's length in years, its term. The interaction term β_{D}D gives defencemen their own price per forecasted win. The sample is the ${comma(PL.n)} skater contracts past the entry level that started from 2018-19 to 2025-26, each with a forecast at its signing. They were signed by ${comma(PL.players)} players who had a season of 10 or more games in one of the two before. Of these contracts, ${comma(PL.censored)} are at the league minimum, which is a floor rather than a negotiated price. A player at the minimum might have been worth less, but clubs were not allowed to pay less. They are therefore treated as censored in the regression (a Tobit regression; Tobin 1958). A contract above the minimum tells the regression its exact price; a contract at the minimum tells it only that the player's price was at or below the minimum, and enters through the probability of that. Treating minimum contracts as negotiated prices would pull the price line toward the minimum and understate what clubs pay per win. ${T("pl")} builds the price line up one term at a time.`));
const plSpecs = Object.keys(PLF);
const PLROW = [["intercept", "Intercept (α)"], ["per forecast win", "Per forecasted win (β)"], ["defence addition per win", "Added per win for a defenceman (β_{D})"], ["per year of term", "Per year of term (γ)"]];
add(TT("pl", "The price line, built up one term at a time"));
add(TABLE(["Term", "Forecasted WAR alone", "+ defenceman interaction\n(the term-free\nprice line)", "+ term\n(adopted)"],
  [...PLROW.map(([k, lab]) => [lab, ...plSpecs.map((s) => cc(PLF[s].terms[k], 3, 100))]),
   ["Spread of the price (σ)", ...plSpecs.map((s) => f3(PLF[s].sigma * 100))],
   ["Log-likelihood", ...plSpecs.map((s) => Number(PLF[s].loglik_share).toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 }))]],
  [2840, 2260, 2260, 2280], [1, 2, 3]));
add(CAPTION(`Censored (Tobit) regression on ${comma(PL.n)} contracts, ${comma(PL.censored)} of them at the league minimum. Coefficients are shares of the cap, shown in percent (standard error, clustered by player) [two-sided p-value]; σ is the typical distance of a cap hit from the price line. Log-likelihood in cap-share units, on the same contracts in each column; higher is better. Re-estimated, the adopted line's coefficients equal those the model prices on to within ${(Math.max(LK.gap_term_in, 1e-12)).toExponential(0)} of the cap.`));
const tl = LK.term_in;
add(P("Written with its estimates, in shares of the cap, the adopted price line is:"));
add(EQ([`cap share = ${f4(tl.alpha)} + `, ["()", [`${f4(tl.beta)} + ${f4(tl.beta_d_add)}D`]], `w + ${f4(tl.gamma_term)}T`]));
add(P(`${F("price")} shows the price line with the contracts it is estimated on.`));
add(FIGURE("price", "fig_price_line.png", "The price line",
  `Each point is one contract's cap hit, restated at the 2025-26 cap, plotted on the forecast at its signing of the player's WAR in its first season. Lines: the adopted price line for one, three, and six years of term, floored at the league minimum.`));
add(H2("The forecast used to estimate the price line"));
const SL = PL.signing_log.find((l) => l.startsWith("seasons between")) || "";
const beforeN = (SL.match(/, 1: ([\d,]+)/) || [])[1];
const sampleN = ((PL.signing_log.find((l) => l.startsWith("signing-dated")) || "").match(/of ([\d,]+)/) || [])[1];
const noFc = ((PL.signing_log.find((l) => l.startsWith("left out, no forecast")) || "").match(/: ([\d,]+)/) || [])[1];
if (Number(String(sampleN).replace(/,/g, "")) - Number(String(noFc).replace(/,/g, "")) !== PL.n) throw new Error("candidate contracts less those without a forecast at signing must equal the regression's");
add(P(`A club signing a player prices what it expects him to produce, so the price line is estimated on the forecast, dated at the contract's signing, of the player's performance in the first season of the new contract. The forecast uses only the seasons the club had seen when it agreed to the deal. Of the ${sampleN} candidate contracts, ${beforeN} were signed mid-season before the new contract's first season, an extension signed in January for example. ${noFc} have no forecast at their signing and are left out, which leaves the ${comma(PL.n)} contracts of the regression.`));
const TA = (v, t) => N.term_avg.find((r) => r.version === v && r.term === t);
const TA0 = TA("first season (today)", true), TA1 = TA("term average (main)", true), TA2 = TA("term average, expected", true);
if (Math.abs(TA0.loglik - PLF["wins + defence + term"].loglik_share) > 0.05 || Math.abs(TA0.rmse_M - SP.locked_rmse_M) > 1e-4) throw new Error("the first-season row is not the adopted price line");
add(P(`A club signing a long contract might instead price the performance it expects over every season of it. The average forecast over the contract's term, alone and times the chance of playing each season, fits the cap hits worse and has a higher out-of-sample RMSE (${T("spec")}). On it, the premium per year of term grows, from ${mil(TA0.gamma_term * CAP25M)} to ${mil(TA1.gamma_term * CAP25M)} a season, because long contracts go to players whose forecasts decline over the term. If clubs paid more for long contracts because of performance expected later in the deal, the premium would shrink once that performance was in the forecast, so the premium pays for something other than future performance.`));
add(H2("Contract length"));
add(P(`Clubs pay more per season for a longer contract at the same forecast: they buy the security of the player for those years. Without a term for length, the price line overprices one-year contracts by ${mil(PL.by_term[0].term_free - PL.by_term[0].observed)} on average and underprices eight-year contracts by ${mil(PL.by_term[7].observed - PL.by_term[7].term_free)}; with it, each length's mean is close (${T("term")}). Adding term raises the log-likelihood by ${f1(PLF["wins + defence + term"].loglik_share - PLF["wins + defence"].loglik_share)} on the same contracts, and its coefficient is statistically significant at the 5% level (${pq(PLF["wins + defence + term"].terms["per year of term"].p)}). The price line without term is reported beside each value as a sensitivity.`));
add(TT("term", "Mean cap hit by contract length, observed and priced"));
add(TABLE(["Years of term", "Contracts", "Observed", "Price line without term", "Adopted price line"],
  PL.by_term.map((r) => [String(r.years), comma(r.n), money(r.observed), money(r.term_free), money(r.term_in)]),
  [1800, 1700, 2000, 2050, 2090], [1, 2, 3, 4]));
add(CAPTION("Mean cap hit of the contracts of each length, and the mean of each price line's expected cap hit for the same contracts, allowing for the league minimum; percent of the 2025-26 cap."));
add(P("A season is priced at the term left at the valuation date, the same for each remaining season, because the comparison is a replacement player with the same forecast signed that day for the rest of the deal."));
add(H2("Other forms of the price line"));
const V = SP.variants, stepV = V["one step: premium below replacement"], rfaV = V["separate RFA line"];
const gain = (r) => 100 * (1 - r.rmse_M / SP.locked_rmse_M);
add(P(`Seven other forms of the price line were tested and rejected on the out-of-sample RMSE of the expected cap hit (${T("spec")}). A premium per year of term that falls with the player's quality predicted best, mostly through one step, ${mil(stepV ? SP.step_below_M : 0)} a year for players forecast below replacement level compared with ${mil(SP.step_above_M)} for everyone else. The flat premium was kept, because the step lowers the out-of-sample RMSE by only ${f1(gain(stepV))}% and adds a term. A separate line for restricted free agents predicted ${f2(gain(rfaV))}% better at the cost of four more terms. A separate line for the four most recent seasons was not statistically significant (p = ${f2(V["separate 2022-2025 line"].p)}), which does not show that prices were stable.`));
add(TT("spec", "The price line and its alternatives"));
const SPR = [["One step: a separate premium below replacement level", "one step: premium below replacement"], ["Premium by forecast group", "length premium by forecast group"],
  ["Premium times the forecast", "length x forecast (one term)"], ["A separate line for restricted free agents", "separate RFA line"], ["A squared forecast term", "quadratic in the forecast"],
  ["A bend at one forecasted win", "bend at one forecast win"], ["A separate line for 2022-23 to 2025-26", "separate 2022-2025 line"]];
const spRows = [["Adopted price line", "-", money(SP.locked_rmse_M), "-"],
  ...SPR.map(([lab, k]) => [lab, `+${f1(V[k].gain)} (${pq(V[k].p)})`, money(V[k].rmse_M), `${V[k].beats} of 20`]),
  ...[["Average forecast over the term", TA1], ["Average forecast over the term × chance of playing", TA2]].map(([lab, r]) => [lab, f1(r.loglik - TA0.loglik), money(r.rmse_M), `${r.rmse_beats_first} of 20`])];
add(TABLE(["Version", "Log-likelihood gain (p)", "Out-of-sample RMSE (% of the cap)", "Repeats with lower RMSE"], spRows, [4200, 2000, 1600, 1840], [2, 3], bestKeys(spRows, [2], 2), 16));
add(CAPTION(`The ${comma(SP.n)} contracts of the adopted price line. Log-likelihood gain over the adopted price line, with its likelihood-ratio p-value; the two versions on the average over the term are not nested in the adopted price line and have none. Out-of-sample RMSE of the expected cap hit, percent of the 2025-26 cap, with the contracts split by player into five groups, each predicted from a regression on the other four, the split repeated 20 times. The last column counts the repeats in which the version's RMSE is lower than the adopted price line's. Bold: the lowest RMSE.`));
add(H2("The league-minimum floor"));
const mae = H.war_if_plays_mae;
add(P(`No player is paid less than the league minimum, so a season's price is the higher of the price line's price and the minimum. Because the forecast is uncertain, for a player near the minimum the average of that higher figure over the range of outcomes is above the forecasted price, so each season is priced at its expected value. The price is taken as normally distributed around the price line's price μ, with standard deviation σ equal to the forecast's mean absolute error that many seasons ahead (${f2(mae["0"])} WAR in the valuation season, rising to ${f2(mae["5"])} five seasons ahead) times √(π/2) = 1.2533, the normal distribution's ratio of the two, converted to a share of the cap at the season's price per win. With F the league minimum and Φ and φ the standard normal distribution and density:`));
add(EQ(["V = FΦ(z) + μ", ["()", ["1 − Φ(z)"]], " + σφ(z),     z = ", ["/", ["F − μ"], ["σ"]]]));
add(P(`The first term is the floor times the chance the price falls below it; the second and third are the expected price when it does not. For a player far above the minimum, V equals the price line's price; Pacioretty's adjustment is ${fx(100 * pacS[0].uncertainty_correction / CAP18, 4)}% of the 2018-19 cap in his first season.`));

// =====================================================================================================================
// 4. CONTRACT VALUE AND THE TERMINAL VALUE (control seasons in one pass: value, cost, weight, walking away)
// =====================================================================================================================
add(H1("4. Contract Value and the Terminal Value"));
add(P(`The contracts valued are the one he is playing and each extension signed on or before the valuation date, since an extension signed later was not known at the valuation. The one exception to charging the full cap hit is a player who is on long-term injured reserve (LTIR) on the trade date, as recorded in Spotrac's injured-reserve log. A club may exceed the cap by an LTIR player's cap hit, so for such a player the cap hit is charged only in the share of each season he is forecast to play. The rule applies to 22 of the 490 traded-player valuations from 2018-19 on.`));
add(H2("Control seasons"));
add(P("When a contract ends with the player a restricted free agent, his club keeps his rights until he can become an unrestricted free agent, by tendering a qualifying offer, a one-year offer whose cost the CBA sets from his prior salary. Each control season adds its value less its cost, weighted by the chance that it happens. Its value is his forecasted WAR in that season, priced at one year of term because a control season is bought one season at a time, and floored at the league minimum."));
add(H2("The cost of a control season"));
add(P("Before he is eligible for salary arbitration, a control season costs the qualifying offer. Each player's next qualifying offer is computed on what he was paid the season before. Through the 2025 offseason the qualifying offer was 110% of a salary up to $660,000, 105% up to $1 million, and 100% above it, never above 120% of the cap hit for contracts starting from 2020-21 and never below the league minimum. From the 2026 offseason, updated bands of the 2026 collective bargaining agreement apply."));
add(P("A player eligible for arbitration can push his pay toward his market price, so from arbitration eligibility onwards a control season costs the higher of the qualifying offer and the expected price of his WAR using the same method described above. An arbitrator sets a player's pay from his recent seasons, so that WAR is his starting level rebuilt at the arbitration season, from the three seasons before it, times that season's forecasted games share. A season before the valuation date enters as he played it, and a season after it as the forecast has it, so nothing after the valuation date is read. Because the rebuilt starting level reads the three seasons before, it lags behind a forecast that is still rising, so an arbitration season can still be worth more than it costs, though never by more than the same season at the qualifying offer alone."));
add(P("A player becomes eligible for arbitration after a set number of professional seasons, which depends on his age when he signed his first contract (CBA Article 12.1(a)). Eligibility is taken from PuckPedia, which marks each expiring contract with whether the player is eligible. A player marked eligible is treated as eligible from his first control season, and one marked not eligible from his second: 92.4% of the 225 players marked not eligible were eligible a season later, and 99.5% of eligible players stay eligible. Counting each player's professional seasons from NHL game records was tested as an alternative and rejected. That count agreed with PuckPedia's mark for only 64.1% of 1,656 contracts and put eligibility later for 541 of them, because the game records include no AHL games, which count toward eligibility."));
add(H2("The weight on a control season"));
add(P(`A control season happens only if the club qualifies the player and he then plays. Its weight is therefore the share of players of his forecasted quality whom clubs qualified, measured on the qualify-or-walk decisions for skater contracts that ended from 2018-19 to 2024-25, times the share of those qualified who then played (${T("control")}). The weights compound from season to season, starting from his chance of playing the contract's final season. Two simpler rules were considered and rejected: keeping every control season until the price of his forecast fell below its cost, and keeping a season only when his forecast was above replacement level. Each replaces clubs' recorded decisions with a rule that clubs' decisions do not follow in the observed data.`));
add(TT("control", "The weight on each control season"));
add(TABLE(["Forecasted WAR", "Decisions", "Qualified", "Played, if qualified", "Weight"],
  BUCKETS.map(([b, lab]) => [lab, comma(CT.qualify_n[b]), pct(CT.qualify_p[b]), CT.plays_given_q[b] === undefined ? "–" : `${pct(CT.plays_given_q[b])} (of ${comma(CT.plays_given_q_n[b])})`, f3(bucketW(b))]),
  [2600, 1500, 1600, 2240, 1700], [1, 2, 3, 4]));
add(CAPTION("Decisions on skater contracts ending from 2018-19 to 2024-25 with the player a restricted free agent, by his forecast at the decision. Played, if qualified: the share of qualified players who played at least one NHL game the next season, among those who played the contract's final season. A player with no forecast enters the lowest group, since a player who could not hold an NHL job is the one a club walks away from."));
add(P(`A qualified player still did not play the next season ${pct(LEFT_Q)} of the time (${comma(NQ)} qualified players who played the contract's final season), so the chance he plays given that he was qualified is multiplied in. Reusing the forecast's chance of playing instead would count walk-aways twice, once in the qualifying rate and again in a chance of playing estimated on players who include them. The plays-given-qualified rate is measured only on players who played the contract's final season, so an absence in that season is charged once, through the chance of playing the weights compound from, and not again in the weight.`));
add(H2("Walking away"));
add(P("Control is a right, not an obligation. A club qualifies a player while he is worth it and lets him go when he is not, and once it lets him go it cannot qualify him again later. The terminal value therefore ends at the first control season whose net value, its value less its cost, is negative. Counting every control season whatever its net value would charge the club for seasons it would never pay for."));
add(H2("Rules for a traded player"));
const A_ = TRD.assets, to25 = TRD.to_2025;
add(P(`Three rules apply when the player is traded. A club trading a player can retain part of his cap hit. The acquiring club is charged only the part it carries, and the retained part is charged to the club that kept it. A retained share is a real cost to the club that kept it and a real relief to the club that received the player, and charging it to the acquirer would misstate both sides. The retaining club pays the retained share of each remaining season of the contract being played, discounted like the contract; extensions and control seasons are not retained.`));
add(P("A player traded during the regular season has already played part of it for the club that traded him, so the acquiring club is credited, on value and on cap hit alike, only with the regular-season days left on the trade date, the trade day counted, over the season's days. The season's last day is the schedule's as published before the season, not the last game played; 2019-20's pause in March 2020 was not known before it happened, and using it would draw on information from after the valuation date."));
add(P(`A contract signed on the trade date is left out of a traded player's value, and out of his chance of playing. The records date a contract by the day, not the hour, so a contract signed on the trade date cannot be shown to come before the trade, and what the trading club gave up was the contract the player was on. This is a dating convention, and it does not say the clubs knew nothing of the new contract. The rule applies to 15 contracts in the trades valued, each signed with the acquiring club: eight extensions and seven restricted free agents who signed the day they were traded, who are valued as rights. Vegas signed Pacioretty to a four-year extension on the day of the trade; with it, his value would have been ${mil(M(PAC.npv_with_extension) * to25)} instead of ${mil(A_[0].value)}.`));
add(H2("Max Pacioretty and Tomas Tatar"));
const carried = (x, P_) => x.cost_dollars * (x.contract_id === P_.seasons[0].contract_id ? 1 - P_.retained_pct : 1);
add(P(`Values in this example are shares of the 2018-19 cap of $${f1(M(CAP18))} million, the cap in force in the season of the trade, against which both players' cap hits were paid. Pacioretty's contract had one season left, 2018-19, at a cap hit of ${money18(M(pacS[0].cost_dollars))}, of which Montreal retained ${pct(PAC.retained_pct, 0)} in the trade, so Vegas carries ${money18(M(carried(pacS[0], PAC)))}. At one year of term his performance is priced at ${money18(M(pacS[0].value_dollars))}, of which ${money18(M(pacS[0].term_premium_dollars))} is the term premium; with a ${pct(pacS[0].p_play, 0)} chance of playing, that is ${money18(M(pacS[0].p_play * pacS[0].value_dollars))}, compared with the ${money18(M(carried(pacS[0], PAC)))} Vegas carries.`));
add(P(`Tatar's contract had three seasons left at ${money18(M(tatS[0].cost_dollars))}, of which Vegas retained ${pct(TAT.retained_pct, 1)}, so Montreal carries ${money18(M(carried(tatS[0], TAT)))} a season. Each season's price is below the cap hit Montreal carries, and his value is ${money18(M(TAT.summary.npv_total))} (${money18(M(TAT.summary.npv_total_term_free))} on the price line without term). ${T("pac")} values both contracts.`));
add(TT("pac", "Max Pacioretty's and Tomas Tatar's contracts, valued at the trade"));
const ageAt = (P_, x) => P_.age_last + P_.last_lag + x.k;
const pacRow = (P_, x, nm) => [nm, `${x.season_start}-${String(x.season_start + 1).slice(2)}`, String(ageAt(P_, x)), f2(x.rate_82), f2(x.gp_share), f2(x.projected_war), f2(x.p_play), money18(M(x.value_dollars)), money18(M(x.term_premium_dollars)), money18(M(x.cost_dollars)), money18(M(carried(x, P_))), money18(M(x.pv_dollars))];
add(TABLE(["Player", "Season", "Age", "WAR per 82", "Games share", "Forecasted WAR", "Chance of playing", "Price", "Of which term", "Cap hit", "Carried by the acquirer", "Present value"],
  [...pacS.map((x) => pacRow(PAC, x, "Pacioretty")), ["Pacioretty, total", "", "", "", "", "", "", "", "", "", "", `**${money18(sumPV(pacS))}**`],
   ...tatS.map((x) => pacRow(TAT, x, "Tatar")), ["Tatar, total", "", "", "", "", "", "", "", "", "", "", `**${money18(sumPV(tatS))}**`]],
  [960, 700, 430, 700, 700, 760, 760, 800, 800, 790, 860, 900], [2, 3, 4, 5, 6, 7, 8, 9, 10, 11], new Set(), 15));
add(CAPTION(`Percent of the 2018-19 cap ($${f1(M(CAP18))} million). Age on September 15. Price: the adopted price line's price of his forecasted WAR at the term left, with the floor. Present value = (chance of playing × price − cap hit carried) / 1.03^{k}, k counted from 2018-19. Pacioretty became an unrestricted free agent at the end of the season, so he has no terminal value; on the price line without term his value is ${money18(M(PAC.summary.npv_total_term_free))}.`));

// =====================================================================================================================
// 5. GOALTENDERS
// =====================================================================================================================
add(H1("5. Goaltenders"));
add(P(`A goaltender's WAR carries over from one season to the next far less than a skater's. Across consecutive seasons of 20 or more games, a goaltender's WAR in one season has a correlation of ${f3(G2.g_r)} with his WAR in the next (${comma(G2.g_pairs)} pairs by ${G2.g_goalies} goaltenders), compared with ${f3(G2.s_r)} for skaters, and his 50/30/20 average of the three seasons before has a correlation of ${f3(G2.g_trail)} with the next season, compared with ${f3(G2.s_trail)} for skaters. A goaltender's own record therefore says much less about his next season, and his forecast keeps less of it.`));
add(P(`A goaltender's forecast is his 50/30/20 average of season WAR, keeping 35% of it and pulling 65% toward the league average of 2.19 WAR, plus an age term. The 35% was chosen by cross-validation. Each goaltender's seasons were predicted from regressions on other goaltenders (${comma(G2.cv_n)} goaltender-seasons of 20 or more games by ${G2.cv_goalies} goaltenders), and the out-of-sample RMSE of season WAR, the square root of the mean squared error across the cross-validation folds, was lowest at 35% (${f4(Math.sqrt(G2.pull_mse))} wins, compared with ${f4(Math.sqrt(G2.pull_30))} at 30% and ${f4(Math.sqrt(G2.pull_40))} at 40%). Every season counts, whatever its games; counting only seasons of 10 or more games, as for skaters, raised the out-of-sample RMSE (${f4(Math.sqrt(G2.gp10))} compared with ${f4(Math.sqrt(G2.gp10_base))} on the same seasons).`));
add(P(`The age term is a straight line in age, estimated on the forecast's errors in goaltender-seasons before the valuation season. It lowers the forecast by about ${f2(-G2.slope)} WAR for each year of age (${pq(G2.slope_p)} in sample) and lowers the out-of-sample RMSE of season WAR by ${f2(100 * (1 - Math.sqrt(G2.age_lin / G2.age_base)))}% (${f4(Math.sqrt(G2.age_lin))} compared with ${f4(Math.sqrt(G2.age_base))}; p = ${f3(G2.age_lin_p)}). Adding age squared lowered it by a further ${f2(100 * (Math.sqrt(G2.age_lin / G2.age_base) - Math.sqrt(G2.age_quad / G2.age_base)))}%, a gain that was not compared with the straight line by a test of its own, so the simpler straight line was kept. The term is applied at his age in each season, so a goaltender's forecast declines as he ages.`));
add(P(`A goaltender's chance of playing each season is a logistic regression for each season ahead on his age, his forecast, and his games share in the most recent season, as for skaters but without contract status. Age squared was not statistically significant in any season ahead (p from ${f3(G2.sq_p_min)} to ${f3(G2.sq_p_max)}) and is not in the model. On the valuation seasons 2015-16 to 2021-22 the mean forecast chance is ${f3(G2.fc0)}, compared with ${f3(G2.played0)} who played in the valuation season, and ${f3(G2.fc5)} compared with ${f3(G2.played5)} five seasons ahead.`));
const GOC = N.goalie;
add(P(`The goaltender price line has the skater line's form: cap share regressed on the forecast dated at the signing, censored at the league minimum, with a term for contract length, estimated on ${GOC.n} standard-level goaltender contracts starting from 2015-16 to 2025-26 (${GOC.at_min} at the minimum). Written with its estimates, in shares of the cap:`));
add(EQ([`cap share = ${f4(GOC.alpha)} + ${f4(GOC.beta)}w + ${f4(GOC.gamma)}T`]));
add(P(`At the 2025-26 cap, that is ${mil(GOC.alpha * CAP25M)} plus ${mil(GOC.beta * CAP25M)} per forecasted WAR plus ${mil(GOC.gamma * CAP25M)} a season per year of term. The line is estimated on the goaltender's pulled trailing record alone, without the age term, because clubs' pay follows the record. Estimated on the forecast with the age term, the price line's out-of-sample RMSE rises from ${money(G2.line_flat_M)} to ${money(G2.line_aged_M)} of the cap a contract, in all 20 repeats. Each season of a goaltender's contract is then priced on his forecast with the age term, so an older goaltender's value reflects the decline that his age predicts, which clubs' pay does not.`));
add(P(`Each control season has one weight for all goaltenders: ${pct(G2.ctl_q)} of goaltenders were qualified and ${pct(G2.ctl_play)} of those played, a weight of ${f3(G2.ctl_q)} × ${f3(G2.ctl_play)} = ${f3(G2.ctl_w)}, from ${G2.ctl_n} decisions. One weight serves all because the qualifying rates do not differ by forecasted quality (chi-squared test, p = ${f3(G2.ctl_p)}).`));

// =====================================================================================================================
// 6. LIMITS (each said once, here only)
// =====================================================================================================================
add(H1("6. Limitations of the Player Model"));
add(BULLET("Estimated on later seasons. The price line is estimated on contracts that started from 2018-19 to 2025-26, the goaltender price line on contracts that started from 2015-16 to 2025-26, and the control-season weights on decisions about contracts that ended from 2018-19 to 2024-25; each runs past many of the trades it prices. The forecast alone uses only seasons before the valuation season, but the WAR it reads is the current release of Bacon's WAR, and no archived copy shows each season's figures as they stood at the time of a trade."));
add(BULLET("Arbitration eligibility. PuckPedia's eligibility mark is recorded when a contract ends, so a valuation dated earlier reads a mark recorded later."));
add(BULLET("Form within a season. Each asset is valued once a season, on seasons completed before it, so a player's form in the season of an in-season trade is not used."));
add(BULLET("The best players. The forecast runs low for the best players: those with a trailing 50/30/20 WAR of 3 or more were forecast 0.39 WAR a season below what they delivered over the next five seasons (95% interval 0.05 to 0.70; valuation seasons 2015-16 to 2021-22, 889 forecasts of 73 players). Most of it is five players, Connor McDavid, Nathan MacKinnon, Sidney Crosby, Auston Matthews, and Leon Draisaitl; without them the shortfall is 0.11 WAR and not statistically significant at the 5% level."));
add(BULLET(`Long contracts. Players on seven- and eight-year contracts delivered more than their forecast, by ${money(0.60)} to ${mil(0.75)} a season in the contract's first three seasons (0.33 to 0.42 WAR). Each extra year of term predicts 9% to 20% of the term premium in out-performance, so the premium mostly buys length, but part of it is quality the forecast misses.`));
add(BULLET("Players with one or two seasons. A player's starting level rests on the counted seasons he has, rescaled, so for a player with one or two NHL seasons it rests on less evidence than for one with three."));
add(BULLET("One price of a win. One price line prices each season of each valuation; the length premium is flat although it falls with quality, and restricted free agents are priced on the same line as unrestricted ones."));
add(BULLET("Retirement. A retirement that ends a cap hit early is not modelled, which errs toward a lower value."));

// =====================================================================================================================
// REFERENCES AND APPENDIX (the per-season regressions and the significance rule)
// =====================================================================================================================
add(H1("References"));
add(P("Efron, B., and C. Morris. 1975. \"Data Analysis Using Stein's Estimator and Its Generalizations.\" *Journal of the American Statistical Association* 70 (350): 311-319."));
add(P("Nadaraya, E. A. 1964. \"On Estimating Regression.\" *Theory of Probability and Its Applications* 9 (1): 141-142."));
add(P("Papke, L. E., and J. M. Wooldridge. 1996. \"Econometric Methods for Fractional Response Variables with an Application to 401(k) Plan Participation Rates.\" *Journal of Applied Econometrics* 11 (6): 619-632."));
add(P("Tobin, J. 1958. \"Estimation of Relationships for Limited Dependent Variables.\" *Econometrica* 26 (1): 24-36."));
add(P("Watson, G. S. 1964. \"Smooth Regression Analysis.\" *Sankhyā, Series A* 26 (4): 359-372."));

add(H1("Appendix A. The Games-Share and Chance-of-Playing Regressions"));
add(P(`The adopted regressions of ${T("gs")} and ${T("pp")} are estimated separately for each season ahead, in the 2025-26 estimation. ${T("gsH")} and ${T("ppH")} give each, from the valuation season (0) to five seasons ahead. The trailing games share matters less the further ahead the season, and age more.`));
const HS = ["0", "1", "2", "3", "4", "5"];
const gsA = (h) => GS[h]["+ trailing WAR (adopted)"];
add(TT("gsH", "The games-share regression, by seasons ahead"));
add(TABLE(["Term", ...HS],
  [...GSROW.map(([k, lab]) => [lab, ...HS.map((h) => cc(gsA(h).terms[k], 4))]), ["R-squared", ...HS.map((h) => f3(gsA(h).r2))], ["Player-seasons", ...HS.map((h) => comma(gsA(h).n))]],
  [2140, 1250, 1250, 1250, 1250, 1250, 1250], [1, 2, 3, 4, 5, 6], new Set(), 15));
add(CAPTION("Least squares; coefficient (standard error, clustered by player) [two-sided p-value]."));
const ppA = (h) => PP[h][ppKey(h)];
add(TT("ppH", "The chance-of-playing regression, by seasons ahead"));
add(TABLE(["Term", ...HS],
  [...PPROW.map(([k, lab]) => [lab, ...HS.map((h) => cc(ppA(h).terms[k], 3))]), ["McFadden pseudo R-squared", ...HS.map((h) => f3(ppA(h).pseudo_r2))], ["Player-seasons", ...HS.map((h) => comma(ppA(h).n))]],
  [2140, 1250, 1250, 1250, 1250, 1250, 1250], [1, 2, 3, 4, 5, 6], new Set(), 15));
add(CAPTION("Logistic regression on the log odds; coefficient (standard error, clustered by player) [two-sided p-value]."));
const INS = N.audit.insample;
const fails = (m, t) => { const x = INS.filter((r) => r.model === m && r.term === t); return { n: x.length, f: x.filter((r) => r.p > 0.05).map((r) => r.h) }; };
const fmtH = (hs) => (hs.length ? listAnd(hs.map((h) => `+${h}`)) : "none");
const TNS = [["Trailing games share", "games share", "tr_gp_share"], ["NHL seasons since his debut", "games share", "exp_seasons"], ["Age − 27.22", "games share", "age_c"], ["(Age − 27.22)²", "games share", "age_c2"], ["Trailing WAR", "games share", "tw_WAR"],
  ["Age − 27.22", "chance of playing", "age"], ["Trailing WAR", "chance of playing", "level"], ["Trailing games share", "chance of playing", "gp_share"], ["Defenceman", "chance of playing", "is_D"], ["Under contract", "chance of playing", "under_contract"], ["No contract record", "chance of playing", "contract_unknown"], ["Intercept", "chance of playing", "intercept"]];
const tnsRows = TNS.map(([lab, m, t]) => { const x = fails(m, t); if (!x.n) throw new Error(`${m} ${t}`); return [lab, m === "games share" ? "Games share" : "Chance of playing", `${x.f.length} of ${x.n}`, fmtH(x.f)]; });
const cu = fails("chance of playing", "contract_unknown");
const dGS = DROP.is_D, dAS = DROP.age_sq, dES = DROP.exp_seasons;
add(P(`Every term in the two regressions was checked by one rule. A term is not included if it is not statistically significant at the 5% level and dropping it does not worsen the forecast on the valuation seasons 2015-16 to 2021-22; a term that fails on its p-value but improves the forecast is kept only with the reason stated. Each season ahead keeps the same terms, so a term is judged across all seasons ahead together. Three terms failed and are not in the model. A defenceman dummy variable in the games share was not statistically significant in ${dGS.fail} of its ${dGS.n} seasons ahead (p from ${f3(dGS.p_min)} to ${f3(dGS.p_max)}), and age squared and seasons since debut in the chance of playing in ${dAS.fail} and ${dES.fail} of ${dAS.n} respectively; dropping the three together lowered the forecast's RMSE of season WAR (p < 0.001).`));
add(P(`The terms that remain are shown in ${T("terms_ns")}. Their failures all come six or more seasons ahead, where each regression rests on the fewest player-seasons, except the no-contract-record dummy variable, which is not statistically significant in ${cu.f.length} of ${cu.n} seasons ahead but is kept because dropping it makes season WAR worse (${pq(P3.p_build_better_war)}).`));
add(TT("terms_ns", "The adopted regressions' terms: seasons ahead in which each is not statistically significant"));
add(TABLE(["Term", "Regression", "Seasons ahead with p > 0.05", "Which seasons ahead"], tnsRows, [3200, 2000, 2000, 2440], [2], new Set(), 15));
add(CAPTION("The 2025-26 regressions, every season ahead estimated (+0 is the valuation season); two-sided p-values, standard errors clustered by player. The no-contract-record dummy variable enters only the seasons ahead whose training seasons include some before 2018-19."));

// ---- every table and figure is referred to in the text before or at it --------------------------------------------
const body = TEXT.join("\n");
for (const k of [...TABS, ...Object.keys(APPX)]) if (!body.includes(`${T(k)}`)) throw new Error(`${T(k)} is never referred to`);

const doc = new Document({
  creator: "Thomas Mihaljevic", title: "Valuing Players",
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
