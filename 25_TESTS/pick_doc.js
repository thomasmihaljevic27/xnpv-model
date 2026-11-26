// pick_doc.js v1.0 -- builds "Valuing Draft Picks.docx" (40_DOCS/), the second of the four write-up chunks (WORK_QUEUE 0a).
//
// v1.0 (2026-11-26; Thomas: "Agreed, re-run those two and build it", on the outline agreed that day). Section 6 and
// Appendix C of "Valuing Players, Draft Picks, and Prospects" v5.0 (model_doc.js v5.0) made into a document of their own,
// built the way "Valuing Players" v1.2 is (25_TESTS/player_doc.js): no glossary, each term defined where it first appears,
// the NPV formula in full, the p-value defined as there, the choices table at the end of the step it belongs to, each
// limit said once, under the writing-style skill v2.0.
//   - Thomas's comments on v5.0's pick sections (his copy, commit 1026401): 81 (define a pick by what it is), 82-84 and 91
//     (subjects, no "And", "determined by"), 85 ("depending on"), 86 (the rights rule rewritten), 87 (negative NPV moved
//     to the choices table), 88 (the 200-game probability a separate one Bacon publishes), 89 ("NPV over club control",
//     not "career NPV", here and in the figure), 90 (the defenceman star value removed), 92 (the example pick's place in
//     its round). His two edits ("total value", "by points percentage") carried in.
//   - Figures: OUTPUT_DIR/model_doc/numbers.json (model_doc_figures.py v4.5, the pick curve as it runs) and
//     OUTPUT_DIR/pick_doc/numbers.json (pick_doc_figures.py v1.0: entry-level seasons at the term left and CBA Group 6
//     re-run on today's model, the deceased, the intercept's effect on traded picks, Bacon's implied star share, the
//     example pick's place); the choices table's other effects from pick_choices_current.csv.
//
// Run:  NODE_PATH=<folder with docx> node 25_TESTS/pick_doc.js   (DOC_OUT=<file> to write elsewhere; LINT_OUT=<file.md>)

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType, HeadingLevel,
  BorderStyle, ShadingType, Footer, PageNumber, Math: OMath, MathRun, MathSuperScript, MathSubScript,
  MathFraction, MathSum, MathRoundBrackets,
} = require("docx");

const VERSION = "pick_doc.js v1.0";
const ROOT = path.resolve(__dirname, "..");
const FIG = path.join(ROOT, "30_OUTPUT", "model_doc");
const N = JSON.parse(fs.readFileSync(path.join(FIG, "numbers.json"), "utf8"));
const N3 = JSON.parse(fs.readFileSync(path.join(ROOT, "30_OUTPUT", "pick_doc", "numbers.json"), "utf8"));
if (!String(N3.script).startsWith("pick_doc_figures.py v1.")) throw new Error(`pick_doc numbers from ${N3.script}`);
if (!String(N.script).startsWith("model_doc_figures.py v4.5")) throw new Error(`model_doc numbers from ${N.script}`);
const OUTFILE = process.env.DOC_OUT || path.join(ROOT, "40_DOCS", "Valuing Draft Picks.docx");
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
const TABS = ["sissons", "choices", "shapes", "nested", "pickvals", "methods"];
const APPX = { deceased: "A1" };
const FIGS = ["pickcost", "picks", "pickdrafts"];
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
const CAP = H.cap, CAP25 = CAP["2025"], CAP25M = CAP25 / 1e6;
const money = (x) => shareOf(x, CAP25M);                 // x in $M at the 2025-26 cap
const mil = (x) => `${shareOf(x, CAP25M)} of the cap`;
const K25 = 100 / CAP25M;                                 // $M at the 2025-26 cap -> percent of it
const PK = N.picks, SH = PK.shapes, STAR = SH["star probability (adopted)"].terms.p_star;
const PS = PK.p_star, LIN = PK.persistence, TPK = PK.trade_pick, PT = PK.point;
const shp = (nm) => { if (!SH[nm]) throw new Error(`shape ${nm}`); return SH[nm]; };
// the choices table's effects on the pick model as it runs (pick_choices_current.py)
const PCH = Object.fromEntries(fs.readFileSync(path.join(ROOT, "30_OUTPUT", "pick_choices_current.csv"), "utf8").replace(/\r/g, "").trim()
  .split("\n").map((l, i, a) => (i ? Object.fromEntries(l.split(",").map((v, j) => [a[0].split(",")[j], v])) : null)).slice(1).map((r) => [r.choice, r]));
if (Math.abs(N3.deceased.out_M - STAR.b) > 1e-9) throw new Error("pick_doc numbers are not on this pick curve");

const kids = [];
const add = (...xs) => xs.flat().forEach((x) => kids.push(x));
add(new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: "Valuing Draft Picks", bold: true, size: 40, font: FONT })] }));

// =====================================================================================================================
// OPENING AND DATA
// =====================================================================================================================
add(P("A club that trades a draft pick gives up the player it would have selected with it, often before anyone knows who that player is or where the pick will fall. This document values a draft pick in the same currency as a player under contract: its expected net present value (xNPV), stated as a share of the 2025-26 salary cap of $95.5 million. The price of a season's performance and the cost of keeping a player are those of the player model, set out in Valuing Players, applied to drafted players."));
add(P(`The example used throughout is the 2019 second-round pick that the Montreal Canadiens received from the Vegas Golden Knights on September 10, 2018, with Tomas Tatar and Nick Suzuki, for Max Pacioretty. The pick originally belonged to Columbus. It was traded before the 2018-19 season began and became the ${TPK.actual_slot}th pick of the 2019 draft.`));
add(H2("The data and their sources"));
add(P("The chance that a player taken at a given draft position becomes a star comes from the draft model of Patrick Bacon, the data scientist whose wins above replacement (WAR) measure performance throughout the player model, published with its method on HockeyStats.com. For each draft position, the model gives two probabilities from a logistic regression on pick number with a change of slope at pick 150: that the player becomes a star, defined as a career WAR per 82 games of at least 1.8 for a forward or 1.23 for a defenceman, and, as a separate probability, that he plays 200 NHL games. Taking the probabilities from the same source as the WAR keeps one definition of performance across players and picks."));
add(P("Each draft's selections, with every draft position, club, and player, come from the NHL's own draft records. Each drafted player's seasons are measured by Bacon's WAR. Entry-level signing dates come from PuckPedia and CapWages, two public salary-cap databases, and the cap hits clubs paid drafted players from PuckPedia from 2018-19 and CapWages before. Traded picks come from the trade ledger: CapFriendly's trade records from July 2017 to March 2022, collected using the Internet Archive after it closed, and PuckPedia's from June 2022 to March 2026. The standings on each trade date are computed from the NHL's game results."));

// =====================================================================================================================
// 1. THE VALUE OF A PICK
// =====================================================================================================================
add(H1("1. The Value of a Pick"));
add(P(`A draft pick is a claim on the player a club selects with it, so its value has to come from what earlier selections at the same draft position delivered. Two features of the draft make that hard. Outcomes are uneven: of the ${comma(PK.n)} players drafted from 2007 to 2017, ${comma(PK.routes["never played"])} played no NHL game while their club held their rights, and the ${PK.top5.n} with the highest net present value (NPV) over club control, 5% of the players, delivered ${pct(PK.top5.share, 0)} of the total value. Outcomes also arrive slowly. A club holds a drafted player's rights for about nine seasons, so the drafts that can be measured completely are years older than the trades being valued.`));
add(P(`Most of the value that picks produce comes from the few players who become stars. Of the ${comma(PK.stars.skaters)} skaters drafted from 2007 to 2015, the ${PK.stars.stars} who became stars, ${pct(PK.stars.share_players)}, delivered ${pct(PK.stars.share_surplus)} of the NPV those picks returned; a star here meets Bacon's definition and played at least 200 NHL games. Among the first ten picks, stars were ${pct(PK.stars.top10_share_players)} of the players and delivered ${pct(PK.stars.top10_share_surplus)} of it. A pick is therefore valued as a claim on a chance of a star:`));
add(EQ(["pick xNPV = star value × star probability"]));
add(P(`The star probability is Bacon's probability that a player taken at the pick's draft position becomes a star. The star value is the value of a pick per unit of star probability, which is what a pick would be worth at a star probability of 100%. No draft position comes near that, so the star value is an extrapolation. It measures more than the stars, because the number of players who become regulars without becoming stars also rises with the star probability. The star value is estimated at ${mil(STAR.b)}, so the first overall pick, with a star probability of ${pct(PS["1"])}, is worth ${f3(PS["1"])} × ${money(STAR.b)} = ${mil(STAR.b * PS["1"])}.`));

// =====================================================================================================================
// 2. WHAT A DRAFTED PLAYER DELIVERED
// =====================================================================================================================
add(H1("2. What a Drafted Player Delivered"));
add(P("To learn what a draft position returns, each player drafted from 2007 to 2017 is priced the way the player model prices a contract, over the seasons his club controlled him: from his draft to the end of club control, with seasons observed through 2025-26. Club control ends when he can become an unrestricted free agent under CBA Section 10.1(a), at 27 as of June 30 or after seven seasons of 40 or more NHL games (30 for a goaltender). The rules for each season are as follows."));
add(BULLET("Value. The market price of the performance he delivered, his WAR, on the price line at one year of term, floored at the league minimum; a goaltender's is priced on the goaltender price line. The seasons have been played, so delivered WAR is priced rather than a forecast. WAR in the shortened 2012-13, 2019-20, and 2020-21 seasons is scaled to 82 games."));
add(BULLET("Cost. The entry-level maximum for his draft class from his first NHL season, for three, two, or one seasons depending on his age on September 15 of the year he signed (18 to 21, 22 to 23, 24 or older). After it, a one-year qualifying offer each season, and once he is eligible for arbitration, the higher of the qualifying offer and the price line's price of his arbitration WAR, as for a player under contract. He becomes eligible after 4, 3, 2, or 1 seasons of 10 or more NHL games for a signing age of 20 or under, 21, 22 to 23, or 24 or older (CBA Section 12.1(a))."));
add(BULLET("Seasons outside the NHL. A season without an NHL game is worth zero and costs zero, because a minor-league salary does not count against the cap. A season of fewer than 10 games is scaled by its games over 82, because a call-up counts against the cap only for his days on the roster."));
add(BULLET(`Rights. A player belongs to the pick only while the drafting club held him. If the drafting club let his rights lapse, so that he first played for another club without being signed or traded by it, he is worth zero to the pick (${PK.routes.lapsed} players). If he signed his entry-level contract with the drafting club and was later lost on waivers or released, he counts (${PK.routes["signed by the drafting club"]} players), because the club held him.`));
add(P("The seasons have already been played, so each season's value and cost are in that season's dollars and each season's cap is known. Each season is restated at the 2025-26 cap, cap*, by multiplying it by cap* over that season's cap:"));
add(EQ(["NPV = ", ["sum", "s", [["()", [SUB("V", "s"), " − ", SUB("C", "s")]], " × ", ["/", ["cap*"], [SUB("cap", "s")]]]]]));
add(P("Here V_{s} and C_{s} are season s's value and cost in that season's dollars, and cap_{s} is that season's cap. This is the player model's discount at the cap's actual growth rather than at 3%. On the value side, cap growth and the discount cancel, so each season's value and cost become shares of that season's cap, and the NPV is the sum of those shares, stated at the 2025-26 cap. The seasons have been played, so this is a net present value rather than an expected one, and the pick's xNPV is estimated from these NPVs."));
const played_ = PT.seasons.filter((x) => x.gp > 0);
add(P(`${T("sissons")} prices ${PT.name}, taken ${PT.pick}th in ${PT.draft} (star probability ${pct(PT.p_star)}), the draft position the example pick became. He played ${played_.length} NHL seasons within club control, and his NPV over them is ${mil(PT.surplus)}.`));
add(TT("sissons", `${PT.name} (${PT.draft}, #${PT.pick}), from his draft to the end of club control`));
add(TABLE(["Season", "NHL games", "Season WAR", "Contract charged", "Value", "Cost", "Net value"],
  [...PT.seasons.map((x) => [`${x.season}-${String(x.season + 1).slice(2)}`, String(x.gp), x.gp > 0 ? f2(x.war82) : "", x.gp <= 0 ? "Not in the NHL" : (x.elc ? "Entry-level" : (x.arb ? `Arbitration (${f2(x.arb_war)} WAR)` : "Qualifying offer")), f2(x.value * K25), f2(x.cost * K25), f2(x.surplus * K25)]),
   ["Total", "", "", "", f2(PT.seasons.reduce((a, x) => a + x.value, 0) * K25), f2(PT.seasons.reduce((a, x) => a + x.cost, 0) * K25), `**${f2(PT.surplus * K25)}**`]],
  [1500, 1100, 1200, 2400, 1100, 1100, 1240], [1, 2, 4, 5, 6], new Set(), 16));
add(CAPTION(`Percent of the 2025-26 cap. Value: his delivered WAR priced on the price line at one year of term. Arbitration: the price of his arbitration WAR (shown), his starting level rebuilt at that season, when it exceeds the qualifying offer. Season WAR: the WAR he delivered in the season, with the shortened 2019-20 and 2020-21 seasons scaled to 82 league games (by 82/70 and 82/56). His final season within club control was ${PT.window_end - 1}-${String(PT.window_end).slice(2)}.`));

add(H2("The cost of keeping a drafted player"));
const qoPct = PK.qo_chain.star / CAP25M * 100;
add(P(`How a drafted player's seasons are costed moves pick values more than any other choice. What clubs paid is not used, because it records contracts negotiated years after the draft, many of which also buy unrestricted seasons. The rule that costs a control season in the player model is used instead. A player eligible for arbitration can push his pay toward his market price, so from eligibility each season costs the higher of the qualifying offer and the price of his arbitration WAR. Costing every control season at the qualifying offer alone would raise the star value from ${money(STAR.b)} to ${f2(qoPct)}% of the cap.`));
add(P(`Even so, the rule's cost is below what clubs paid first-round picks (${F("pickcost")}): ${listAnd(PK.first_round.map((g, i) => `${pct(g.cost_arb / g.cost_actual, 0)}${i ? "" : " of what clubs paid"} for picks ${g.lo} to ${g.hi}`))}.`));
add(FIGURE("pickcost", "fig_pick_cost.png", "Value delivered and two measures of cost, first-round picks",
  `Average per first-round skater who played in the NHL for the club that drafted him (2007-2017 drafts), over the seasons his club held his rights, as a percentage of the 2025-26 cap: the value of the performance he delivered, his cost under the adopted rule, and what clubs paid (each season's cap hit; PuckPedia from 2018-19, CapWages before).`));

add(H2("Other choices in pricing a drafted player"));
const pch = PCH;
const g = (k, f) => { if (!pch[k] || pch[k][f] === undefined) throw new Error(`choice ${k} ${f}`); return Number(pch[k][f]); };
const E = N3.elc, G6 = N3.group6, DC = N3.deceased;
add(P(`Each remaining choice in pricing a drafted player is listed in ${T("choices")}, with what the alternative would have done.`));
const CHS = [
  ["End of club control", "Unrestricted free agency under CBA Section 10.1(a); games played stand in for roster games", "The pick secures the player only until he can sign with any club", `PuckPedia's projected free-agency year agrees with this rule for ${comma(N3.ufa_check.agree)} of the ${comma(N3.ufa_check.n)} drafted players it covers`],
  ["Price before regression", "Each drafted player's seasons are priced, then his NPV over club control is regressed on the star probability", "Regressing WAR on draft position and pricing the prediction treats each player at a position as the average one and blurs the stars, who carry a pick's value", "-"],
  ["Length of each season's contract", "Each season priced at one year of term", "An entry-level or qualifying-offer season buys no security beyond that season", `Pricing entry-level seasons at the term left on the deal would add up to ${money(E.max_pct * CAP25M / 100)} of the cap to a player who plays all three seasons of a three-year deal (${money(E.mean_pct * CAP25M / 100)} on average for the ${comma(E.players)} who did) and raise the star value by ${f0(E.pct)}%, to ${mil(E.star_M)}`],
  ["Brief call-ups", "A season under 10 NHL games has its value and cost scaled by games over 82", "A call-up's cap hit counts only for his days on the roster", `Counting each as a full season would lower the star value by ${f1(-g("brief call-ups", "pct"))}%, to ${mil(g("brief call-ups", "star_M"))}`],
  ["Entry-level slides", "Not modelled; the entry-level contract runs by calendar from his first NHL season", "The CBA lets an 18- or 19-year-old's contract slide a year when he plays under 10 NHL games, and modelling it changes little", `Modelled approximately, slides raise the star value by ${f2(g("entry-level slides", "pct"))}%; ${g("entry-level slides", "players").toFixed(0)} players have a season that would slide`],
  ["NPV below zero", "Counted as negative", "A player who holds a roster spot while delivering less than his cost was a loss to his club", `Flooring each NPV at zero would raise each pick's value by ${f1(g("floored at zero", "pct"))}% (${comma(g("floored at zero", "negative"))} are negative)`],
  ["Rights that lapsed", `Zero (${PK.routes.lapsed} players); kept when he signed his entry-level contract with the drafting club (${PK.routes["signed by the drafting club"]})`, "Value a club never held cannot belong to its pick; a club that signed him held him", `The lapsed players held ${pct(g("lapsed rights", "share_positive"))} of drafted skaters' positive NPV`],
  ["Goaltenders", "Pooled with skaters, priced on the goaltender price line", "At a trade, nobody knows whether a pick will become a goaltender", `Goaltenders' value does not follow draft position (Holtby #93, Saros #99, Shesterkin #118); a separate goaltender star value (${mil(g("goaltender star value", "star_M"))}) would put a first-overall goaltender near ${mil(g("goaltender star value", "first_pick_M"))}`],
  ["Drafted players who died", `Left out of every regression (${T("deceased")})`, "They never had the chance to deliver; left in, each counts as a pick worth zero", `Leaving them in would move the star value from ${mil(DC.out_M)} to ${mil(DC.in_M)}`],
  ["The 2017 draft's final season", "Kept", `The data end with 2025-26, which cuts ${N3.d2017.past} of the ${N3.d2017.picks} players' control by one season`, "Scoring each draft out of sample already refits without 2017"],
  ["CBA Group 6", "Not modelled", "Players 25 or older with three professional seasons and under 80 NHL games become free agents early; few drafted players qualify", `At its upper bound it lowers the star value by ${f2(-G6.pct)}%`],
];
add(TT("choices", "Other choices in pricing a drafted player"));
add(TABLE(["Choice", "What the model does", "Why", "What the alternative would do"], CHS, [1500, 2800, 2700, 2640], [], new Set(), 15, false));
add(CAPTION(`Each effect is measured on the pick model as it runs, against the star value of ${mil(STAR.b)}. Slides are modelled approximately, by moving one later season to the entry-level cost for each season that would slide. Group 6 at its upper bound applies it at 25 to every player under the games ceiling, as if each had three professional seasons.`));

// =====================================================================================================================
// 3. ESTIMATING THE STAR VALUE
// =====================================================================================================================
add(H1("3. Estimating the Star Value"));
add(H2("The shape of value across draft positions"));
const SHROWS = [["Straight line in draft position", "straight line in draft position"], ["Log of draft position", "log of draft position"],
  ["Log of draft position and its square", "log of draft position and its square"], ["Star value × star probability (adopted)", "star probability (adopted)"],
  ["Star probability and its square", "star probability and its square"], ["Star and 200-game probabilities", "star and NHL-player probabilities"]];
const ADO = shp("star probability (adopted)");
SHROWS.forEach(([, k]) => { if (k !== "star probability (adopted)" && !(shp(k).held > ADO.held)) throw new Error(`shape ${k} is not worse out of sample`); });
add(P(`Value falls steeply over the first ten picks and is close to flat after the first round (${F("picks")}). Six shapes could describe that fall: a straight line in draft position, its logarithm, the logarithm and its square, Bacon's star probability times a star value, the star probability and its square, and the star probability with Bacon's probability of a 200-game NHL player. Each was estimated on all ${comma(PK.n)} picks and scored out of sample. Each draft was predicted from a regression on the other ten, and the out-of-sample root mean squared error (RMSE), the square root of the average squared miss, is taken over all picks (${T("shapes")}). Each comparison reports a one-sided p-value, the probability of the adopted shape's RMSE being at least this much lower than the other shape's if the two predicted equally well; below 0.05, the adopted shape is statistically significantly better at the 5% level.`));
const stLog2 = shp("log of draft position and its square"), sN = shp("star and NHL-player probabilities");
add(P(`The adopted shape has the lowest out-of-sample RMSE, with a single parameter. A straight line values the first pick at ${mil(shp("straight line in draft position").at["1"])} and the logarithm at ${mil(shp("log of draft position").at["1"])}, compared with the ${mil(PK.avg_at["1"])} that first picks returned and the adopted ${mil(STAR.b * PS["1"])}. The logarithm with its square comes close, but it turns upward after pick ${stLog2.first_rise}, valuing the 200th pick above the 137th. Adding the square of the star probability, or Bacon's separate probability of a 200-game NHL player, adds nothing statistically significant (p = ${f3(shp("star probability and its square").terms.p_star_sq.p)} and ${f3(sN.terms.p_nhler.p)}).`));
add(P(`Bacon's probabilities are estimated on largely the same drafts, so their agreement with these values is not independent confirmation. Applied to these data, his definition marks ${pct(PK.stars.share_players)} of the skaters drafted from 2007 to 2015 as stars, compared with the ${pct(N3.bacon_implied)} his probabilities imply.`));
add(TT("shapes", "Six shapes of value across draft positions"));
const pShape = (k) => (shp(k).p_vs_adopted === null ? "-" : pr(1 - shp(k).p_vs_adopted));
add(TABLE(["Shape", "Parameters", "#1", "#10", "#32", "#64", "Out-of-sample RMSE", "p"],
  [...SHROWS.map(([lab, k]) => [lab, String(shp(k).params), f2(shp(k).at["1"] * K25), f2(shp(k).at["10"] * K25), f2(shp(k).at["32"] * K25), f2(shp(k).at["64"] * K25), f4(shp(k).held * K25), pShape(k)]),
   ["Average of the eleven players taken", "", f2(PK.avg_at["1"] * K25), f2(PK.avg_at["10"] * K25), f2(PK.avg_at["32"] * K25), f2(PK.avg_at["64"] * K25), "", ""]],
  [2900, 950, 700, 700, 700, 700, 1100, 1000], [1, 2, 3, 4, 5, 6, 7], bestKeys(SHROWS.map(([, k]) => ["", "", "", "", "", "", f4(shp(k).held * K25)]), [6], 4), 16));
add(CAPTION("Values in percent of the 2025-26 cap, from each shape's regression on all picks. Out-of-sample RMSE: each draft predicted from a regression without it, over all picks, in percent of the cap; the lowest is in bold. p: one-sided p-value that the adopted shape's RMSE is not lower than the shape's. Each average rests on eleven players, so a single draft changes it a great deal."));
add(FIGURE("picks", "fig_picks.png", "Draft position and NPV over club control",
  "Left: Bacon's star probability by draft position (a logistic regression on pick number with a change of slope at pick 150). Right: the average NPV over club control of the eleven players taken at each draft position (2007-2017), and three of the shapes. Percent of the 2025-26 cap."));

add(H2("The star value"));
add(P("Each drafted player's NPV over club control is regressed on the star probability for his draft position, with no intercept, so a draft position with no chance of a star is worth zero:"));
add(EQ(["NPV over club control = star value × star probability + error"]));
const DI = PK.draft_intercepts, diVals = Object.values(DI.values);
const sI = shp("star probability and an intercept"), sP = shp("star probability, draft position and an intercept");
const moveMax = Math.max(...[sI.terms.p_star.b, DI.star.b, sP.terms.p_star.b, sN.terms.p_star.b].map((b) => Math.abs(b - STAR.b)));
add(P(`The coefficient is the star value, ${mil(STAR.b)} (standard error ${f2(STAR.se * K25)} percentage points). ${T("nested")} adds an intercept, then an intercept for each draft, then draft position with an intercept, then the 200-game probability, each on the same ${comma(PK.n)} picks. Only the intercepts for each draft are statistically significant at the 5% level (jointly ${pq(DI.joint_zero.p)}), and no addition moves the star value by more than ${mil(moveMax)}.`));
add(TT("nested", "The star value, with each term added"));
add(TABLE(["Term", "Adopted", "+ an intercept", "+ an intercept\nfor each draft", "+ draft position\nand an intercept", "+ 200-game\nprobability"],
  [["Star probability (the star value)", cc(STAR, 2, K25), cc(sI.terms.p_star, 2, K25), cc(DI.star, 2, K25), cc(sP.terms.p_star, 2, K25), cc(sN.terms.p_star, 2, K25)],
   ["Intercept", "", cc(sI.terms.intercept, 3, K25), `11, ${money(Math.min(...diVals))} to ${money(Math.max(...diVals))}\njointly zero: ${pq(DI.joint_zero.p)}`, cc(sP.terms.intercept, 3, K25), ""],
   ["Draft position", "", "", "", cc(sP.terms.pick, 4, K25), ""],
   ["200-game probability", "", "", "", "", cc(sN.terms.p_nhler, 2, K25)]],
  [2360, 1460, 1460, 1460, 1460, 1460], [1, 2, 3, 4, 5], new Set(), 16));
add(CAPTION(`Least squares on ${comma(PK.n)} drafted players, 2007-2017; NPV over club control in percent of the 2025-26 cap. Coefficient (heteroskedasticity-robust standard error, which allows the size of the misses to differ across players) [two-sided p-value].`));
add(P(`A single intercept would give each pick, including a seventh-round pick with almost no chance of a star, a fixed amount of ${mil(sI.terms.intercept.b)}. It is not statistically significant at the 5% level (${pq(sI.terms.intercept.p)}), yet it would raise the value of all traded picks by ${f1(N3.intercept.all_pct)}% and of seventh-round picks by ${f0(N3.intercept.r7_pct)}%, because a fixed amount is large next to their small star probabilities. An intercept for each draft would let deep and shallow drafts differ in level: beyond what its star probability predicts, a pick in the best draft delivered ${mil(Math.max(...diVals))} and in the weakest ${mil(Math.min(...diVals))}. These intercepts are left out because a pick traded before its draft has no intercept of its own and would have to be valued at the average draft's.`));

add(H2("One star value for every draft"));
const per = PK.per_draft;
const lo = per.reduce((a, b) => (b.star < a.star ? b : a)), hi = per.reduce((a, b) => (b.star > a.star ? b : a));
add(P(`Estimated on each draft separately, the star value ranges from ${mil(lo.star)} for the ${lo.draft} draft to ${mil(hi.star)} for ${hi.draft}, and the differences are statistically significant (${pq(PK.equal_test.p)}; ${F("pickdrafts")}). Some drafts are deeper than others, so differences are expected. A drift over time would matter more, because it would make an average over eleven drafts wrong for any one trade. With a linear trend across draft years, the star value rises by ${mil(PK.trend.all.b)} a draft (${pq(PK.trend.all.p)}). That rise rests on two drafts. Without 2015 (Connor McDavid, Jack Eichel) and 2016 (Auston Matthews), the trend falls to ${mil(PK.trend.without_2015_2016.b)} a draft and is not statistically significant (${pq(PK.trend.without_2015_2016.p)}).`));
add(P(`The model therefore uses one star value for every draft, estimated on all eleven, so a club is taken to expect the same value from a given draft position each year and an exceptional draft is treated as noise. A star value for each trade season, estimated only on drafts whose control had run out by then, would rest the early trade seasons on two or three drafts. The 2015 and 2016 drafts finished after most of the trades studied, so the star value without them, ${mil(PK.sensitivity.star)}, is reported beside each value as a sensitivity; it lowers each pick's value by ${pct(1 - PK.sensitivity.star / STAR.b, 0)}.`));
add(FIGURE("pickdrafts", "fig_pick_drafts.png", "The star value estimated on each draft",
  "Each dot is the star value estimated on one draft alone (all positions), with bars two standard errors either side. The solid line is the star value estimated on all eleven drafts and used by the model; the dashed line is the same regression without the 2015 and 2016 drafts. Percent of the 2025-26 cap."));
add(H2("The value of a pick"));
const PSK = ["1", "2", "5", "10", "13", "20", "32", "50", "64", "100", "150", "200"];
add(P(`${T("pickvals")} gives the resulting value at selected draft positions.`));
add(TT("pickvals", "The value of a pick at selected draft positions"));
add(TABLE(["Draft position", ...PSK],
  [["Star probability", ...PSK.map((k) => pct(PS[k]))], ["Value", ...PSK.map((k) => f2(STAR.b * PS[k] * K25))], ["Without 2015 and 2016", ...PSK.map((k) => f2(PK.sensitivity.star * PS[k] * K25))]],
  [1680, ...PSK.map(() => 663)], PSK.map((_, i) => i + 1), new Set(), 15));
add(CAPTION(`Value: the star value (${mil(STAR.b)}, or ${mil(PK.sensitivity.star)} without 2015 and 2016) times the star probability, in percent of the 2025-26 cap.`));

// =====================================================================================================================
// 4. VALUING A TRADED PICK
// =====================================================================================================================
add(H1("4. Valuing a Traded Pick"));
const M_ = PK.traded.methods;
const nRound = M_["round average (before the season's first game)"] + M_["round average (a later draft)"];
if (M_["actual slot (traded during the draft)"] + M_["slot on the trade date"] + nRound !== PK.traded.n) throw new Error("traded pick methods do not add up");
add(P(`A pick is often traded before its draft position is known, so its position is determined by what was known on the trade date, in one of three ways (${T("methods")}).`));
add(TT("methods", "How a traded pick's draft position is determined"));
add(TABLE(["When the pick was traded", "Picks", "Draft position used"],
  [["During its own draft", comma(M_["actual slot (traded during the draft)"]), "Its actual draft position"],
   ["For the coming draft, once that season's regular season had started", comma(M_["slot on the trade date"]), `The position its original team's place in the standings on the trade date gives, by points percentage; within three places of the actual position for ${PK.traded.within3}, with a median miss of ${f1(PK.traded.median_gap)} places`],
   ["Before that season started, or for a later draft", comma(nRound), "The average star probability of its round"]],
  [3200, 900, 5500], [1], new Set(), 16, false));
add(CAPTION(`The ${comma(PK.traded.n)} picks traded from July 2017 to March 2022.`));
add(P(`The round average is used because a team's draft position says little about its position a year or two later. Across the 2005 to 2026 drafts, a team's own first-round position has a correlation of ${f2(LIN.corr1)} with its position in the next draft and ${f2(LIN.corr2)} with its position two drafts later, and it moves a median of ${f1(LIN.median_move)} places in a year. The position is not purely random, so the round average loses some information. Valued at the positions teams went on to pick, the next first-round pick of a team that had just picked in the top five was worth ${mil(LIN.top5_later)} on average, and that of a team that had just picked 25th or later ${mil(LIN.bottom_later)}, compared with the round average of ${mil(LIN.round_avg)}. The round average is kept for its simplicity.`));
add(P("A pick for a later draft is not discounted further for the years until its draft. Its value is a share of the cap, and the player model projects the cap to grow 3% a year and discounts 3% a year, so the two cancel."));
const EX = N3.example;
add(P(`The 2019 second-round pick Montreal received was traded before the 2018-19 season began, so it is given the average star probability over round 2's draft positions, picks ${EX.first} to ${EX.last} of a 31-team draft. That average, ${pct(TPK.star_chance, 2)}, is the star probability of about the ${EX.pick_nearest_avg}th pick, and the pick is worth ${f4(TPK.star_chance)} × ${money(STAR.b)} = ${mil(TPK.value)}. It became the ${TPK.actual_slot}th pick, three places after the middle of the round; at that position its star probability is ${pct(EX.p_at_50, 2)} and its value ${mil(EX.value_at_50_M)}.`));
if (TPK.actual_slot - EX.middle !== 3) throw new Error("the example pick's place in its round");

// =====================================================================================================================
// 5. LIMITS
// =====================================================================================================================
add(H1("5. What the Pick Model Does Not Do"));
add(BULLET("Estimated on later drafts. The star value is estimated on the 2007-2017 drafts, whose seasons run past many of the trades valued, so a club at the trade could not have known it, and a 2007-2017 draftee is inside the regression that values him. Bacon's probabilities are estimated on largely the same drafts."));
add(BULLET(`Cost of control. The arbitration rule still charges first-round picks less than clubs paid them, ${pct(PK.first_round[0].cost_arb / PK.first_round[0].cost_actual, 0)} to ${pct(PK.first_round[PK.first_round.length - 1].cost_arb / PK.first_round[PK.first_round.length - 1].cost_actual, 0)} of what clubs paid, so picks may look more valuable relative to players than they are.`));
add(BULLET("The round average. A pick traded before its season starts is valued at its round's average, which undervalues a weak team's future first-round pick and overvalues a strong team's."));
add(BULLET("The lottery and conditions. The draft lottery and the reordering of playoff teams are not modelled, and a conditional pick is valued as if its condition were met."));
add(BULLET("Goaltenders. Goaltenders share the skaters' star value, because a pick's position does not reveal whether it will become a goaltender."));
add(BULLET("Arbitration eligibility. Eligibility is counted from NHL games, and the game records hold no AHL games, so eligibility comes later than in fact and the cost of control is understated."));

// =====================================================================================================================
// APPENDIX
// =====================================================================================================================
add(H1("Appendix A. Drafted Players Left Out"));
const DEC = [["Alexei Cherepanov", "2007, #17", "New York Rangers", "October 13, 2008"], ["Mickey Renaud", "2007, #143", "Calgary Flames", "February 18, 2008"],
  ["Bryan Rufenach", "2007, #208", "Detroit Red Wings", "June 4, 2012"], ["Scott Winkler", "2008, #89", "Dallas Stars", "June 12, 2013"],
  ["Kristians Pelss", "2010, #181", "Edmonton Oilers", "June 11, 2013"], ["Daniil Sobchenko", "2011, #166", "San Jose Sharks", "September 7, 2011"]];
if (DEC.length !== DC.n) throw new Error("the deceased count");
add(P(`${T("deceased")} lists the ${DC.n} drafted players of 2007 to 2017 who never played an NHL season and died before their club's control would have ended.`));
add(TT("deceased", "Drafted players left out of every regression"));
add(TABLE(["Player", "Drafted", "Club", "Died"], DEC, [2600, 1500, 2700, 2400]));
add(CAPTION("From Wikipedia's list of ice hockey players who died during their careers."));

// ---- every table and figure is referred to in the text before or at it --------------------------------------------
const body = TEXT.join("\n");
for (const k of [...TABS, ...Object.keys(APPX)]) if (!body.includes(`${T(k)}`)) throw new Error(`${T(k)} is never referred to`);
for (const k of FIGS) if (!body.includes(`${F(k)}`)) throw new Error(`${F(k)} is never referred to`);

const doc = new Document({
  creator: "Thomas Mihaljevic", title: "Valuing Draft Picks",
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
