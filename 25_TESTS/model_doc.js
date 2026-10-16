// model_doc.js v1.0 -- builds "Valuing Players, Draft Picks, and Prospects.docx" (40_DOCS/Supervisor_Drafts/).
//
// v1.0 (2026-10-16): the three valuation models on one scale, for Thomas and his supervisor (a full write-up of the
// approach, every regression with its formula and a table that adds terms one at a time). One trade runs through it:
// Montreal and Vegas, 2018-09-10 (Pacioretty for Tatar, Suzuki and a 2019 second-round pick).
//
// NUMBERS: every computed figure comes from OUTPUT_DIR/model_doc/numbers.json (25_TESTS/model_doc_figures.py v1.0,
// whose guards tie each figure to the output it must reproduce). Recorded figures copied from the records, with their
// sources, are listed here:
//   50/30/20 the best of nine three-season weightings; 65/35 the best pull     25_TESTS/starting_level_simple_test.py v1.1
//                                                                              (MODEL_DIRECTIVES directive 1)
//   comparable players alone worse 1-5 seasons ahead in 2,000 of 2,000         aging_investigations_abc.py v1.0
//     career resamples (the league average's weight of ten kept)               (MODEL_DIRECTIVES investigation B)
//   contract length does not predict later production                          July Stage 2 (MODEL_DIRECTIVES directive 4)
//   CBA rules (entry-level length 9.1(b), arbitration 12.1(a), Group 3 10.1(a)) pick_curve.py v1.7 docstring and constants
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

// ---- formatting helpers (as prospect_model_doc.js) ----------------------------------------------------------------
const FONT = "Calibri";
const fx = (x, d) => Number(x).toFixed(d);
const f1 = (x) => fx(x, 1), f2 = (x) => fx(x, 2), f3 = (x) => fx(x, 3), f4 = (x) => fx(x, 4);
const comma = (x) => Number(x).toLocaleString("en-US");
const money = (x) => (x < 0 ? `-$${f2(-x)}M` : `$${f2(x)}M`);
const mil = (x) => (x < 0 ? `-$${f2(-x)} million` : `$${f2(x)} million`);
const pfmt = (p) => (p === null || p === undefined || Number.isNaN(p) ? "–" : (p < 0.001 ? "<0.001" : f3(p)));
const pq = (p) => (p < 0.0005 ? "p < 0.001" : `p = ${p < 0.01 ? f4(p) : f3(p)}`);
const z = (x, d) => (Math.abs(x) < 0.5 * 10 ** -d ? (0).toFixed(d) : Number(x).toFixed(d));
const pct = (x, d = 1) => `${fx(100 * x, d)}%`;
// a coefficient as "b (se)" on one line and "[p]" on the next
const cc = (t, d = 3, scale = 1) => (t ? `${z(t.b * scale, d)} (${t.se === null || Math.abs(t.se) < 1e-12 ? "–" : fx(t.se * scale, d)})\n[${pfmt(t.p)}]` : "");

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

// Word equations: pieces are strings (ordinary runs), ["^", base, sup] or ["_", base, sub]
function EQ(pieces) {
  const kids = pieces.map((x) => {
    if (!Array.isArray(x)) return new MathRun(x);
    if (x[0] === "^") return new MathSuperScript({ children: [new MathRun(x[1])], superScript: [new MathRun(x[2])] });
    return new MathSubScript({ children: [new MathRun(x[1])], subScript: [new MathRun(x[2])] });
  });
  TEXT.push(pieces.map((x) => (Array.isArray(x) ? `${x[1]}${x[0]}${x[2]}` : x)).join(""));
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 120 }, children: [new OMath({ children: kids })] });
}

function FIGURE(file, title, caption, width = 600) {
  const b = fs.readFileSync(path.join(FIG, file));
  const w = b.readUInt32BE(16), h = b.readUInt32BE(20);
  return [TITLE(title), new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true,
    children: [new ImageRun({ type: "png", data: b, transformation: { width, height: Math.round(width * h / w) } })] }), CAPTION(caption)];
}
const border = { style: BorderStyle.SINGLE, size: 4, color: "C9C8C3" };
const borders = { top: border, bottom: border, left: border, right: border };
// a cell's text may hold "\n": each line its own paragraph; bold: a set of "row,col" keys
function TABLE(header, rows, widths, numeric = [], bold = new Set(), size = 17, keep = true) {
  const cell = (text, i, j, head, keep) => new TableCell({
    borders, width: { size: widths[i], type: WidthType.DXA },
    shading: head ? { fill: "EFEEEA", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 40, bottom: 40, left: 70, right: 70 },
    children: String(text).split("\n").map((line) => new Paragraph({ keepNext: keep,
      alignment: numeric.includes(i) && !head ? AlignmentType.RIGHT : (numeric.includes(i) ? AlignmentType.RIGHT : AlignmentType.LEFT),
      children: runs(line, { size, bold: !!head || bold.has(`${j},${i}`) }) })),
  });
  return new Table({ width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: header.map((t, i) => cell(t, i, -1, true, true)) }),
      ...rows.map((r, j) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, i, j, false, keep && j < rows.length - 1)) }))] });
}

// ---- numbers -------------------------------------------------------------------------------------------------------
const H = N.heavy;
const CAP = H.cap, CAP25 = CAP["2025"], CAP18 = CAP["2018"];
const PAC = H.players["Max Pacioretty"], TAT = H.players["Tomas Tatar"];
const PL = H.price_line, PLF = PL.fits, TI = PLF["wins + defence + term"].terms;
const GS = H.games_share.by_h, PP = H.participation.by_h;
const CT = H.control, AG = H.aging;
const PK = N.picks, PKF = PK.fits, STAR = PKF["through zero (adopted)"].star;
const PR = N.prospects, S1 = PR.step1, W = PR.worked, TRD = N.trade, TPK = N.trade_pick;
const GV = N.gv, GO = N.goalie;
const k1 = (g) => S1.find((r) => r.k === g);
const SEAS = { "0": "D+1", "1": "D+2", "2": "D+3", "3": "D+4", "4+": "D+5 and later" };
const G5 = ["0", "1", "2", "3", "4+"];
const ARR = PR.arrival;
const cum = (grp, upto) => { let s = 0; for (let i = 1; i <= upto; i++) s += ARR[grp].share_all[`D+${i}`] || 0; return 100 * s; };
const CAP25M = CAP25 / 1e6;                                        // the 2025-26 cap in $M
const perWin = (b) => b * CAP25M;                                  // a cap share at the 2025-26 cap, $M
const M = (x) => x / 1e6;
const to25 = TRD.to_2025;
const gd = (pos, a) => AG.gdelta[`${pos}|${a}`];
const adoptedGS = GS["0"]["+ trailing WAR (adopted)"], adoptedPP = PP["0"]["+ contract status (adopted)"];
const ppKey = (h) => Object.keys(PP[h]).find((k) => k.includes("adopted"));
const pacS = PAC.seasons, tatS = TAT.seasons;
const sumPV = (s) => s.reduce((a, x) => a + x.pv_dollars, 0) / 1e6;
const bucketW = (b) => CT.qualify_p[b] * (CT.plays_given_q[b] === undefined ? 1 : CT.plays_given_q[b]);
const BUCKETS = [["star", "3 or more"], ["regular", "1 to 3"], ["fringe", "0 to 1"], ["negative", "below 0, or no forecast"]];

const kids = [];
const add = (...xs) => xs.flat().forEach((x) => kids.push(x));
add(new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: "Valuing Players, Draft Picks, and Prospects", bold: true, size: 40, font: FONT })] }));

// =====================================================================================================================
// OPENING
// =====================================================================================================================
add(P("An NHL trade exchanges assets of different kinds: players under contract, draft picks, and prospects who have not yet reached the NHL. To judge whether a club received more than it gave, each asset has to be valued in one currency, as of the trade date. This document explains how each kind of asset is valued, and how the three values are put on one scale."));
add(P(`The currency is surplus value: the market price of the wins an asset is expected to deliver to its club, less what the club will pay for them, summed over the seasons the club controls the asset. Under a salary cap, a club gains from a player only when it pays him less than the market would charge for the same wins, since the cap room it saves buys wins elsewhere. Value and cost are measured as shares of each season's salary cap. The model assumes the cap grows 3% a year and discounts future seasons at 3% a year; the two cancel, so a sum of cap shares can be stated in dollars at one cap. Each value in this document is in millions of dollars at the 2025-26 cap of $${f1(M(CAP25))} million, unless it says otherwise.`));
add(P("The three models share two parts. The first is one price line, which converts wins to dollars at the rate clubs pay for them; it is estimated from contracts in Section 1. The second is one set of cost rules from the collective bargaining agreement (CBA): an entry-level salary, then a qualifying offer, or an arbitration price once the player is eligible for salary arbitration. Because these parts are shared, the values of a player, a pick, and a prospect can be added together on each side of a trade."));
add(P("One trade runs through the document. On September 10, 2018, the Montreal Canadiens traded Max Pacioretty to the Vegas Golden Knights for Tomas Tatar, Nick Suzuki, and a 2019 second-round pick. Pacioretty and Tatar were players under contract, Suzuki was a prospect drafted 13th overall in 2017, and the pick was Columbus's, which Vegas held. Each asset is valued in the section for its kind, and Section 4 adds them up."));
add(P("Player production throughout is Patrick Bacon's wins above replacement (WAR); one source puts each asset's wins on one scale. Contracts come from PuckPedia, the trades from a ledger collected from CapFriendly, scoring outside the NHL from Elite Prospects, and the star probability for each draft position and the NHL equivalency factors from Bacon's draft and prospect models."));
add(TITLE("Table 1. Terms used in this document"));
const GLOSS = [
  ["Surplus value", "The market price of the wins an asset delivers to its club, less what the club pays, summed over the seasons the club controls it, discounted 3% a year; \"surplus\" for short."],
  ["WAR", "Bacon's wins above replacement for a season. WAR per 82 is the same scaled to 82 games."],
  ["Valuation date", "The date an asset is valued at: for a traded asset, the trade date."],
  ["Valuation season", "The season in which an asset is valued, starting July 1. A trade during a season is valued in that season; a trade after its last regular-season game, in the next one."],
  ["Forecast WAR if he plays", "The forecast of a player's WAR per 82 in a season, times his forecast games share."],
  ["Games share", "The share of his team's 82 games a player plays, if he plays at all."],
  ["Chance of playing", "The probability that a player plays at least one NHL game in a season."],
  ["Comparable players", "Players of the same position and age whose style, ice time, level, and trend were closest to his, weighted by closeness."],
  ["Price line", "The regression of cap hit on forecast WAR if he plays, position, and contract length: the market price of a season."],
  ["Term", "A contract's length in years. A season's price uses the term left at the valuation date."],
  ["Control seasons", "The seasons after a contract ends in restricted free agency, until the player is eligible for unrestricted free agency."],
  ["Qualifying offer", "The one-year offer, set by the CBA from his prior salary, that keeps a restricted free agent's rights."],
  ["Arbitration price", "Once a player is eligible for salary arbitration, the higher of his qualifying offer and the price line's price of his forecast for that season, built from the seasons before it."],
  ["End of club control", "The June 30 after a drafted player turns 27, or his seventh season of 40 or more NHL games (30 for a goaltender), whichever comes first (CBA Group 3)."],
  ["Draft position", "The overall number of a pick."],
  ["Star probability", "Bacon's probability that a player taken at a draft position becomes a star: career WAR per 82 of at least 1.8 for a forward or 1.23 for a defenceman."],
  ["Star value", "The surplus value of a pick, or a prospect, certain to become a star."],
  ["Prospect", "A drafted player the player model does not yet value: a skater with no NHL season of 10 or more games in the three before the valuation season, or a goaltender with no NHL game in the six before it."],
  ["D+n", "Seasons named from the draft: D0 is the season that ends with the draft, D+1 the season after it."],
  ["NHLe", "Bacon's NHL equivalency: the NHL points one point in a given league and season is worth."],
  ["Production level", "A prospect's NHLe points per 82 games, weighted 50/30/20 over his three seasons before the valuation season."],
];
add(TABLE(["Term", "Meaning"], GLOSS, [2300, 7340], [], new Set(), 17, false));
add(CAPTION("Each term has this meaning wherever it appears. Weights written 50/30/20 apply to the three seasons before the valuation season, the most recent first, and are rescaled over the seasons the player has, so a missing season is left out rather than counted as zero."));

// =====================================================================================================================
// 1. PLAYERS UNDER CONTRACT
// =====================================================================================================================
add(H1("1. Players Under Contract"));
add(P("A contract commits a club to a cap hit for each of its seasons, and what the club receives is the player's play in seasons not yet played. The player model therefore forecasts each remaining season, prices it, and subtracts the cap hit. For seasons k = 0, 1, 2, ... of his contract, where k = 0 is the valuation season:"));
add(EQ(["value = Σ (", ["_", "p", "k"], " × ", ["_", "V", "k"], " − ", ["_", "C", "k"], ") / ", ["^", "1.03", "k"], "  +  value of the control seasons"]));
add(P("where p is his chance of playing the season, V is the market price of his forecast play in it, and C is his cap hit. The cap hit is subtracted whether or not he plays, since an injured or buried player still counts against the cap. The contract valued is the one he is playing, together with each extension signed on or before the valuation date. The rest of this section builds p and V, then the control seasons. Each part of the forecast is estimated only from seasons completed before the valuation season, so it is refitted for each valuation season. Where this document shows a fit, it is the one for 2025-26, the most recent, fitted on seasons through 2024-25."));

add(P("For each season ahead, the model forecasts three things: his WAR per 82 games if he plays, his games share if he plays, and his chance of playing. His forecast WAR if he plays is the first times the second."));
add(H2("The starting level"));
add(P("A single season of WAR is a noisy measure of a player's ability: a hot shooting season or an injury can move it a long way. The forecast therefore starts from his last three seasons and pulls them toward the level of players similar to him:"));
add(EQ(["starting level = 0.65 × own rate + 0.35 × comparable players' level + their change to the valuation season"]));
add(P("His own rate is his WAR per 82 games in the three seasons before the valuation season, counting seasons of 10 or more games, weighted 50/30/20. Each season's weight is also multiplied by its games, so a 20-game season counts for less than a full one. Comparable players' level, defined below, is measured at the age of his last counted season. The last term adds their change in level from that age to the valuation season. Each weighting had the lowest error of those tested on the valuation seasons 2015-16 to 2021-22: 50/30/20 among nine three-season weightings, and 65/35 among pulls toward comparable players."));
const own = PAC.own_seasons;
add(P(`For Pacioretty at the trade, his three seasons before 2018-19 were ${own.map((s) => `${f2(s.WAR_82)} WAR per 82 in ${s.syr}-${String(s.syr + 1).slice(2)} (${s.GP} games)`).join(", ").replace(/, ([^,]*)$/, ", and $1")}. His own rate is ${f3(PAC.own_82)}. His comparable players' level at ${PAC.age_last} is ${f3(PAC.comparables_level)}, and their change from ${PAC.age_last} to ${PAC.age_last + PAC.last_lag} is ${f3(PAC.path[PAC.last_lag])}. His starting level is 0.65 × ${f3(PAC.own_82)} + 0.35 × ${f3(PAC.comparables_level)} ${PAC.path[PAC.last_lag] < 0 ? "−" : "+"} ${f3(Math.abs(PAC.path[PAC.last_lag]))} = ${f3(PAC.start)} WAR per 82: his poor 2017-18 season and his comparable players both pull him below his own two earlier seasons.`));

add(H2("Comparable players"));
add(P("To find players similar to him, the model describes each player-season by four attributes: how his WAR divides among five components (even-strength offence, even-strength defence, power play, penalty kill, and shooting), his ice time per game, his level, and his trend. His level is his 50/30/20 WAR per 82 at that age, games-weighted as above, over seasons of 20 or more games; his trend is the change in his rate between his last two seasons. Each attribute is standardized within position and given equal weight, so the five style shares together count as one attribute. The candidates are players of the same position at the same age, in seasons before the valuation season. Each candidate's weight falls with his distance d from the player:"));
add(EQ(["weight = exp(−", ["^", "d", "2"], " / 2", ["^", "h", "2"], ")"]));
add(P(`where h, the yardstick, is the median distance between two players of the same position (${f2(AG.yardstick.F)} for forwards and ${f2(AG.yardstick.D)} for defencemen in the 2025-26 fit). A candidate one yardstick away gets weight exp(−0.5) = 0.61, against 1 for an exact match, so the weighting is broad. This is kernel weighting (Nadaraya 1964; Watson 1964). Pacioretty's ${PAC.comparables.n_at_age} candidates at ${PAC.age_last} carry weights that sum to ${f1(PAC.comparables.weight_sum)}; his five closest were ${PAC.comparables.top.map((c) => `${c.name} (${f2(c.weight)})`).join(", ").replace(/, ([^,]*)$/, ", and $1")}.`));
add(P("A few close matches, or many distant ones, could give an extreme average. The comparable players' level is therefore blended with the league average for the player's position and age, which counts as ten more comparable players, each with full weight. Pulling a noisy average toward a group mean in this way lowers its expected error (Efron and Morris 1975):"));
add(EQ(["comparable players' level = (Σ ", ["_", "w", "i"], ["_", "L", "i"], " + 10 × league level) / (Σ ", ["_", "w", "i"], " + 10)"]));
add(P(`For Pacioretty, his candidates' weighted level of ${f3(PAC.comparables.weighted_mean_level)} and the league level for forwards at ${PAC.age_last} of ${f3(PAC.comparables.league_level)} give ${f3(PAC.comparables_level)}; with weights summing to ${f1(PAC.comparables.weight_sum)}, the league average carries ${pct(10 / (PAC.comparables.weight_sum + 10))} of it. The weight of ten is a judgement call. Removing the league average leaves the starting level's error unchanged, but the forecast one to five seasons ahead becomes statistically significantly worse (p < 0.001, resampling careers), most for players under 22, so it was kept.`));

add(H2("Aging"));
add(P("Players change with age, and how much depends on the player. The forecast walks the starting level forward one season at a time. Each season it adds his comparable players' average change in level from that age to the next, blended with the league-average change at weight ten as above. The same comparable players, chosen once at his last counted age, supply each change. Their changes are used, not their levels: whether his comparable players improved or declined at an age carries over to him, while his own level stays his own."));
add(P(`A player who leaves the league records no decline. If departures were left out, the average change at older ages would come only from players good enough to stay, and the forecast would understate aging. A player who leaves the NHL for good is therefore given one more season at replacement level (WAR 0), at his own last season's games, so his departure counts as a decline. In the 2025-26 fit, ${comma(AG.imputed)} departures enter this way among ${comma(AG.careers)} careers.`));
add(P(`On average a forward improves until 24 and declines after it, by about ${f2(-gd("F", 29))} WAR per 82 from 29 to 30 and ${f2(-gd("F", 34))} from 34 to 35 (Figure 1, left). Pacioretty's comparable players declined slightly faster than the league average, and his forecast falls from ${f2(pacS[0].rate_82)} WAR per 82 at 29 to ${f2(pacS[pacS.length - 1].rate_82)} at 33 (Figure 1, right).`));
add(FIGURE("fig_aging.png", "Figure 1. Aging",
  `Left: the league-average change in level from one age to the next, by position, in the 2025-26 fit, with departures entered at replacement level; each point is drawn at the age reached. Right: Max Pacioretty's forecast WAR per 82 at the trade, from his comparable players' changes (blue) and, for comparison, from the league-average changes for forwards in the same fit (orange); grey points are his three seasons before the trade. The level is games-weighted 50/30/20 WAR per 82.`));

add(H2("Games share"));
const gsSpecs = Object.keys(GS["0"]);
const GSROW = [["tr_gp_share", "Trailing games share"], ["is_D", "Defenceman"], ["exp_seasons", "NHL seasons since his debut"], ["age_c", "Age − 27"], ["age_c2", "(Age − 27)²"], ["tw_WAR", "Trailing WAR"], ["intercept", "Intercept"]];
const ageTurn = 27 - adoptedGS.terms.age_c.b / (2 * adoptedGS.terms.age_c2.b);
add(P("WAR accumulates with games, so the forecast needs the share of the 82 games he will play if he plays at all. A regression for each season ahead estimates it from his trailing games share and trailing WAR (each his 50/30/20 average over seasons of 10 or more games), his position, his NHL seasons since his debut, and his age at the valuation season and its square:"));
add(EQ(["games share = a + ", ["_", "b", "1"], " × trailing games share + ", ["_", "b", "2"], " × defenceman + ", ["_", "b", "3"], " × seasons since debut + ", ["_", "b", "4"], " × (age − 27) + ", ["_", "b", "5"], " × ", ["^", "(age − 27)", "2"], " + ", ["_", "b", "6"], " × trailing WAR"]));
add(P(`The forecast is capped at 1 and floored at 0.05. Table 2 builds up, one term at a time, the regression for the valuation season itself in the 2025-26 fit; Appendix A gives the adopted regression for each season ahead. The trailing games share carries most of the fit. Each win of trailing WAR adds ${f1(100 * adoptedGS.terms.tw_WAR.b)} percentage points of games, about ${f1(82 * adoptedGS.terms.tw_WAR.b)} games, and the share falls with age until about ${Math.round(ageTurn)}. With trailing WAR in the regression, position is no longer statistically significant at the 5% level (${pq(adoptedGS.terms.is_D.p)}).`));
add(TITLE("Table 2. Games share in the valuation season, built up one term at a time"));
const GSHEAD = { "games share": "Trailing games\nshare alone", "+ defence, experience": "+ defenceman,\nseasons since debut", "+ age, age squared": "+ age, age\nsquared", "+ trailing WAR (adopted)": "+ trailing WAR\n(adopted)" };
add(TABLE(["Term", ...gsSpecs.map((s) => GSHEAD[s])],
  [...GSROW.map(([k, lab]) => [lab, ...gsSpecs.map((s) => cc(GS["0"][s].terms[k], 4))]),
   ["R²", ...gsSpecs.map((s) => f3(GS["0"][s].r2))]],
  [2140, 1875, 1875, 1875, 1875], [1, 2, 3, 4]));
add(CAPTION(`Ordinary least squares on ${comma(adoptedGS.n)} player-seasons by ${comma(adoptedGS.players)} players: each player's 50/30/20 inputs at a valuation season from 2008-09 to 2024-25, and his games share in that season, among seasons he played. Coefficient (standard error, clustered by player) [two-sided p-value]. The adopted column is the model's fit, coefficient for coefficient.`));

add(H2("Chance of playing"));
const uc = adoptedPP.terms.under_contract;
add(P("A contract pays its cap hit whether or not the player plays, but his value accrues only if he does. The chance he plays at least one NHL game in a season is a logistic regression for each season ahead. Its inputs are his age in that season and its square, his trailing WAR and games share, his seasons since his debut, his position, and whether he is under contract for that season on a deal signed by the valuation date:"));
add(EQ(["log( p / (1 − p) ) = a + ", ["_", "c", "1"], " × (age − 27) + ", ["_", "c", "2"], " × ", ["^", "(age − 27)", "2"], " + ", ["_", "c", "3"], " × trailing WAR + ", ["_", "c", "4"], " × trailing games share + ", ["_", "c", "5"], " × seasons since debut + ", ["_", "c", "6"], " × defenceman + ", ["_", "c", "7"], " × under contract + ", ["_", "c", "8"], " × before 2018-19"]));
add(P(`Contract status is visible only from 2018-19, when the contract records begin; an indicator marks the earlier seasons, so they are not read as seasons without a contract. Table 3 builds the regression for the valuation season up one term at a time. Being under contract for the season multiplies the odds of playing by ${f1(Math.exp(uc.b))} (${pq(uc.p)}). Contract status is read at the date of the valuation, which for a traded player is the trade date, so a deal signed by then is seen.`));
const ppSpecs = Object.keys(PP["0"]);
const PPROW = [["age", "Age − 27"], ["age_sq", "(Age − 27)²"], ["level", "Trailing WAR"], ["gp_share", "Trailing games share"], ["exp_seasons", "NHL seasons since his debut"], ["is_D", "Defenceman"], ["under_contract", "Under contract for the season"], ["contract_unknown", "Season before 2018-19"], ["intercept", "Intercept"]];
add(TITLE("Table 3. Chance of playing in the valuation season, built up one term at a time"));
add(TABLE(["Term", "Age alone", "+ trailing WAR, games\nshare, seasons since\ndebut, defenceman", "+ contract status\n(adopted)"],
  [...PPROW.map(([k, lab]) => [lab, ...ppSpecs.map((s) => cc(PP["0"][s].terms[k], 3))]),
   ["McFadden pseudo-R²", ...ppSpecs.map((s) => f3(PP["0"][s].pseudo_r2))],
   ["Log-likelihood", ...ppSpecs.map((s) => comma(Math.round(PP["0"][s].loglik)))]],
  [2640, 2330, 2330, 2340], [1, 2, 3]));
add(CAPTION(`Logistic regression on ${comma(adoptedPP.n)} player-seasons by ${comma(adoptedPP.players)} players (valuation seasons 2008-09 to 2024-25), ${pct(adoptedPP.base)} of whom played. Coefficient on the log-odds (standard error, clustered by player) [two-sided p-value]. The model's own fit adds a negligible penalty (1e-4) against perfectly predicted outcomes; its coefficients differ from these by at most ${adoptedPP.gap_to_page_fit.toExponential(0)}.`));
add(P("Both regressions are fitted for each season ahead with at least 200 player-seasons of evidence: up to eight seasons ahead for the 2018-19 valuation season and twelve for 2025-26. Past that, the forecast continues the league-wide decline in expected WAR measured between the last two fitted seasons."));

add(H2("The price of a season"));
add(P(`The forecast is in wins. The price line converts it to dollars at the rate clubs pay. It is a regression of each contract's cap hit, as a share of the cap in its first season, on the player's forecast WAR if he plays in that season. It adds a slope for defencemen and a term for the contract's length in years:`));
add(EQ(["cap share = α + (β + ", ["_", "β", "D"], " × defenceman) × forecast WAR if he plays + γ × years of term"]));
add(P(`The sample is the ${comma(PL.n)} skater contracts past the entry level that started from 2018-19 to 2025-26, each with a forecast at its signing. They were signed by ${comma(PL.players)} players who had a season of 10 or more games in one of the two before. Each contract's forecast is dated at its signing: it reads only seasons completed when the contract was signed, as the club's information did, and it is the same quantity the price line later prices. Of these contracts, ${comma(PL.censored)} are at the league minimum, which is a floor rather than a negotiated price. The regression treats them as censored (a Tobit regression; Tobin 1958): a minimum contract says only that the player's price was at or below the minimum.`));
const plSpecs = Object.keys(PLF);
const PLROW = [["intercept", "Intercept (α)"], ["per forecast win", "Per forecast win (β)"], ["defence addition per win", "Added per win for a defenceman (β_D)"], ["per year of term", "Per year of term (γ)"]];
add(TITLE("Table 4. The price line, built up one term at a time"));
add(TABLE(["Term", "Forecast WAR alone", "+ defence slope\n(the term-free\nprice line)", "+ term\n(adopted)"],
  [...PLROW.map(([k, lab]) => [lab, ...plSpecs.map((s) => cc(PLF[s].terms[k], 3, CAP25M))]),
   ["Spread of the price (σ)", ...plSpecs.map((s) => f3(PLF[s].sigma * CAP25M))],
   ["Log-likelihood", ...plSpecs.map((s) => comma(f1(PLF[s].loglik_share)))]],
  [2840, 2260, 2260, 2280], [1, 2, 3]));
add(CAPTION(`Censored (Tobit) regression on ${comma(PL.n)} contracts, ${comma(PL.censored)} of them at the league minimum. Coefficients are shares of the cap, shown here in millions of dollars at the 2025-26 cap (standard error, clustered by player) [two-sided p-value]. Log-likelihood in cap-share units, on the same contracts in each column.`));
add(P(`At the 2025-26 cap, the adopted price line prices a forecast win at ${mil(perWin(TI["per forecast win"].b))} for a forward and ${mil(perWin(TI["per forecast win"].b + TI["defence addition per win"].b))} for a defenceman, and adds ${mil(perWin(TI["per year of term"].b))} a season for each year of term. Term is statistically significant at the 5% level (${pq(TI["per year of term"].p)}), and adding it raises the log-likelihood by ${f1(PLF["wins + defence + term"].loglik_share - PLF["wins + defence"].loglik_share)} on the same contracts. Clubs pay more a season for a longer deal at the same forecast (Table 5): they buy the security of the player for those years. Without term, the price line overprices one-year deals by ${mil(PL.by_term[0].term_free - PL.by_term[0].observed)} on average and underprices eight-year deals by ${mil(PL.by_term[7].observed - PL.by_term[7].term_free)}. An earlier test found that contract length does not predict later production, so the term coefficient prices security, not wins. The term-free price line, the middle column of Table 4, is reported beside each value as a sensitivity.`));
add(TITLE("Table 5. Mean cap hit by contract length, observed and priced"));
add(TABLE(["Years of term", "Contracts", "Observed", "Term-free price line", "Adopted price line"],
  PL.by_term.map((r) => [String(r.years), comma(r.n), money(r.observed), money(r.term_free), money(r.term_in)]),
  [1800, 1700, 2000, 2050, 2090], [1, 2, 3, 4]));
add(CAPTION("Mean cap hit of the contracts of each length, and the mean of each price line's expected cap hit for the same contracts (allowing for the league minimum), in millions of dollars at the 2025-26 cap."));
add(P("Each season of a contract is priced at the term left at the valuation date, the same for each remaining season: the comparison is a replacement player with the same forecast signed on that date for the rest of the deal. A control season is priced at one year of term, since it is bought one season at a time."));
add(FIGURE("fig_price_line.png", "Figure 2. The price line",
  `Each point is one contract's cap hit, restated at the 2025-26 cap, against the forecast at its signing of the player's WAR if he plays in its first season. Lines: the adopted price line for one, three, and six years of term, floored at the league minimum.`));

add(H2("The league-minimum floor"));
const mae = H.war_if_plays_mae;
add(P(`No player is paid less than the league minimum, so a season's price is the price line's price or the minimum, whichever is higher. The forecast is uncertain, and the floor cuts off only the bottom of its range: for a player near the minimum, the average price over the range of outcomes is above the price of the point forecast. Each season is therefore priced at the expected value of the higher of the two, with the price normally distributed around its point estimate μ. Its standard deviation σ is the forecast's mean absolute miss k seasons ahead (${f2(mae["0"])} WAR in the valuation season, rising to ${f2(mae["5"])} five seasons ahead) times 1.2533, converted to dollars at the season's price per win; the factor 1.2533 turns a mean absolute miss into a standard deviation for a normal distribution:`));
add(EQ(["V = F × Φ(z) + μ × (1 − Φ(z)) + σ × φ(z),   z = (F − μ) / σ"]));
add(P("where F is the league minimum and Φ and φ are the standard normal distribution and density. For a player far above the minimum, V equals the price line's price."));

add(H2("Control seasons"));
add(P("When a contract ends with the player a restricted free agent, his club keeps his rights until he is eligible for unrestricted free agency: it retains him by tendering a qualifying offer. Each control season adds its value less its cost, weighted by the chance that it happens:"));
add(BULLET("Value: his forecast WAR if he plays in that season, priced at one year of term, with the floor."));
add(BULLET("Cost: the qualifying offer, which the CBA sets from his prior salary; once he is eligible for arbitration, the higher of the qualifying offer and the price line's price of his arbitration WAR. The arbitration WAR is the forecast's own starting level rebuilt at that season, from the seasons before it, times the forecast games share. Eligibility comes from PuckPedia's arbitration flag on the contract, and each next qualifying offer is computed on what he was paid."));
add(BULLET("Weight: the chance his club qualifies him times the chance he then plays, by his forecast quality at the decision (Table 6), measured on the qualify-or-walk decisions for skater contracts that ended from 2018-19 to 2024-25. The weights compound from season to season, starting from his chance of playing the contract's last season."));
add(BULLET("Walking away: the club stops at the first control season whose surplus is negative, and later seasons count as zero, since a club that declines to qualify a player loses his rights."));
add(TITLE("Table 6. The weight on each control season"));
add(TABLE(["Forecast WAR if he plays", "Decisions", "Qualified", "Played, if qualified", "Weight"],
  BUCKETS.map(([b, lab]) => [lab, comma(CT.qualify_n[b]), pct(CT.qualify_p[b]), CT.plays_given_q[b] === undefined ? "–" : `${pct(CT.plays_given_q[b])} (of ${comma(CT.plays_given_q_n[b])})`, f3(bucketW(b))]),
  [2600, 1500, 1600, 2240, 1700], [1, 2, 3, 4]));
add(CAPTION("Decisions on skater contracts ending from 2018-19 to 2024-25 with the player a restricted free agent, by his forecast at the decision. Played, if qualified: the share of qualified players who played at least one NHL game the next season, among those who played the contract's last season."));

add(H2("Max Pacioretty and Tomas Tatar"));
add(P(`Pacioretty's contract had one season left, 2018-19, at a cap hit of ${mil(M(pacS[0].cost_dollars))}. Vegas signed him to a four-year extension at ${mil(M(pacS[1].cost_dollars))} a season on the day of the trade, and the extension is part of the value because it was signed on or before the valuation date. Table 7 values each season. Each season's price includes the term premium for the five years left: ${mil(M(pacS[0].term_premium_dollars))} of the ${mil(M(pacS[0].value_dollars))} in 2018-19, growing with the cap. The price falls short of the $7.00 million cap hit in each season of the extension, by more as he ages and his chance of playing falls.`));
add(TITLE("Table 7. Max Pacioretty's contract, valued at the trade"));
add(TABLE(["Season", "Age", "WAR per 82", "Games share", "WAR if he plays", "Chance of playing", "Price", "Of which term", "Cap hit", "Discount", "Present value"],
  [...pacS.map((s) => [`${s.season_start}-${String(s.season_start + 1).slice(2)}`, String(29 + s.k), f2(s.rate_82), f2(s.gp_share), f2(s.projected_war), f2(s.p_play), money(M(s.value_dollars)), money(M(s.term_premium_dollars)), money(M(s.cost_dollars)), f3(s.discount), money(M(s.pv_dollars))]),
   ["Total", "", "", "", "", "", "", "", "", "", `**${money(sumPV(pacS))}**`]],
  [830, 480, 800, 780, 820, 860, 900, 880, 860, 760, 1000], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], new Set(), 16));
add(CAPTION(`Millions of dollars at the cap of the valuation season (2018-19, $${f1(M(CAP18))} million); the price uses the cap expected for each season, growing 3% a year. Price: the adopted price line's price of his WAR if he plays at five years of term, with the floor. Present value = (chance of playing × price − cap hit) × discount. He reaches unrestricted free agency at the end, so there are no control seasons. On the term-free price line his value is ${mil(M(PAC.summary.npv_total_term_free))}.`));
add(P(`Tatar's contract had three seasons left at ${mil(M(tatS[0].cost_dollars))}. His forecast WAR if he plays is ${f2(tatS[0].projected_war)}, ${f2(tatS[1].projected_war)}, and ${f2(tatS[2].projected_war)}. Each season's price, ${tatS.map((s) => mil(M(s.value_dollars))).join(", ").replace(/, ([^,]*)$/, ", and $1")}, is below his cap hit, and his value is ${mil(M(TAT.summary.npv_total))} at the 2018-19 cap (${mil(M(TAT.summary.npv_total_term_free))} on the term-free price line).`));

add(H2("Goaltenders"));
add(P(`Goaltenders have a simpler model. A goaltender's forecast is his 50/30/20 average of season WAR (62.5/37.5 with two seasons, the last alone with one), pulled 65% of the way to the league average of 2.19 WAR, and held flat for each remaining season. The 65% was chosen by cross-validation on held-out goaltenders, with ${comma(GO.lambda_n)} goaltender-seasons by ${GO.lambda_goalies} goaltenders. The goaltender price line is an ordinary regression of cap share on that 50/30/20 WAR at the contract's start, over ${GO.n} standard-level goaltender contracts starting from 2015-16 (R² = ${f2(GO.r2)}). At the 2025-26 cap it is ${mil(GO.alpha * CAP25M)} plus ${mil(GO.beta * CAP25M)} per WAR, with no term. It is fitted on WAR before the pull toward the league average but prices the pulled forecast, a mismatch the skater price line was re-fitted to remove. A goaltender's chance of playing each season comes from a table of exit rates by quality and age, and each control season carries one weight for all goaltenders, ${f3(CT.goalie.qualify_p)} × ${f3(CT.goalie.plays_given_q)} = ${f3(CT.goalie.weight)}, from ${CT.goalie.n[0]} decisions.`));

add(H2("WAR and circularity"));
add(P("A circularity risk comes with using one source of WAR. The price line is fitted on what clubs paid for players whose forecasts are built from WAR, and the values will be compared with outcomes measured in WAR. Agreement could then reflect Bacon's model rather than play. To check that the forecast measures play, I compared it with Game Value, a measure built from the NHL's play-by-play and shift records with no Bacon input. Game Value credits each skater on the ice with an equal share of his team's expected goals for and against, adjusted for the score, plus the value of the penalties he draws and takes. Its adjusted version (GV-adj) also separates a player from his linemates and opponents at five-on-five."));
add(P(`Across ${comma(GV.n)} player-seasons by ${comma(GV.players)} players from 2017-18 to 2025-26, the forecast WAR if he plays correlates with the same season's GV-adj at r = ${f3(GV.all.forecast[0])}, against ${f3(GV.all.trailing[0])} for his trailing WAR. The forecast's correlation is ${f3(GV.F.forecast[0])} for forwards and ${f3(GV.D.forecast[0])} for defencemen, and ${f3(GV.next.forecast[0])} one season further ahead, against ${f3(GV.next.trailing[0])} (${comma(GV.n_next)} player-seasons). The correlation of expected WAR is ${f3(GV.expected[0])} with contract status and ${f3(GV.no_contract[0])} without it, so none of the agreement comes through clubs' contract decisions. The forecast agrees more closely with an independent measure than his trailing WAR does, which supports it as a measure of play. Some agreement is expected regardless, since both measures describe the same games. These correlations were measured on ${GV.log_date === "2026-10-05" ? "October 5, 2026" : GV.log_date}, before ages were moved to September 15.`));

// =====================================================================================================================
// 2. DRAFT PICKS
// =====================================================================================================================
add(H1("2. Draft Picks"));
add(P("A draft pick's value depends on a player who has not yet been chosen, or who is years from the NHL. The pick model values a draft position by what players taken there delivered in the past. That is the surplus each player drafted from 2007 to 2017 gave his club up to the end of its control, priced on the price line and cost rules of Section 1."));
add(H2("What a drafted player delivered"));
add(P(`For each of the ${comma(PK.n)} players drafted from 2007 to 2017, the model sums the surplus of each NHL season from the draft to the end of club control, with careers observed through 2025-26. Six drafted players who died before reaching the NHL, while their clubs still controlled them, are left out. The rules for each season are:`));
add(BULLET("Value: his actual WAR priced on the price line at one year of term, with the league-minimum floor; a goaltender's on the goaltender price line. The pick model learns from what happened, so it prices delivered WAR, not a forecast. WAR in the shortened 2012-13, 2019-20, and 2020-21 seasons is scaled to 82 games."));
add(BULLET("Cost: the entry-level maximum for his draft class for three, two, or one seasons, by his age on September 15 of the year he signed (18 to 21, 22 to 23, 24 or older), counted from his first NHL season. After that, a chain of one-year qualifying offers; once he is eligible for arbitration, the higher of the qualifying offer and the price line's price of his arbitration WAR, as for players under contract. He is eligible after 4, 3, 2, or 1 seasons of 10 or more NHL games for a signing age of 20 or under, 21, 22 to 23, or 24 or older."));
add(BULLET("A season without an NHL game is worth zero and costs zero; a season of fewer than 10 games is scaled by its games over 82."));
add(BULLET(`A player who first played for another club, without having been traded, is worth zero to the pick, since the drafting club let his rights lapse (${PK.lapsed} players).`));
add(BULLET("Each season's surplus is a share of that season's cap. The shares are summed and stated at the 2025-26 cap, which is the same as discounting at 3% when the cap grows 3%."));
add(P(`Of the ${comma(PK.n)} players, ${comma(PK.played)} played an NHL game. The mean surplus is ${mil(PK.mean_surplus)} a pick, but most of it comes from a few players: the ${PK.concentration.top5_n} with the most surplus, 5% of the players, delivered ${pct(PK.concentration.top5_share, 0)} of the total, and ${pct(PK.share_zero)} of players delivered exactly zero.`));

add(H2("The star value"));
add(P("A pick's surplus comes mostly from a few players, so the model takes the shape of value across draft positions from Bacon's star probability: his probability that a player taken at each draft position becomes a star, a logistic regression on pick number with a change of slope at pick 150 (Figure 3, left). When the pick model was built, it predicted drafted players' surplus better than a straight line in draft position or its logarithm. Only its scale is fitted here. The star value is the surplus value of a pick certain to become a star. I regressed each drafted player's surplus on the star probability for his draft position, with no intercept, so a draft position with no chance of a star is worth zero:"));
add(EQ(["surplus = star value × star probability + error"]));
add(P(`A pick is then worth the star value times its star probability. The star value is ${mil(STAR.b)} (standard error ${f2(STAR.se)}). Table 8 adds an intercept, then an intercept for each draft. The single intercept is not statistically significant at the 5% level (${pq(PKF["one intercept"].intercept.p)}). The draft intercepts are jointly statistically significant at the 5% level (${pq(PKF["an intercept for each draft"].joint_zero.p)}): a draft's intercept, the surplus a pick in it delivered beyond what its star probability predicts, runs from ${mil(PKF["an intercept for each draft"].range[0])} to ${mil(PKF["an intercept for each draft"].range[1])}. They are left out because a pick traded before its draft has no intercept of its own, and with them the star value changes from ${mil(STAR.b)} to ${mil(PKF["an intercept for each draft"].star.b)}. Leaving out the 2015 and 2016 drafts, the two that carry the only trend across drafts, gives ${mil(PK.sensitivity.star)}, reported as a sensitivity.`));
add(TITLE("Table 8. The star value, built up one term at a time"));
const pk3 = PKF["an intercept for each draft"];
add(TABLE(["Term", "Star probability\n(adopted)", "+ one intercept", "+ an intercept\nfor each draft"],
  [["Star value", cc(STAR, 2), cc(PKF["one intercept"].star, 2), cc(pk3.star, 2)],
   ["Intercept", "", cc(PKF["one intercept"].intercept, 3), `11 intercepts, ${money(pk3.range[0])} to ${money(pk3.range[1])}\njointly zero: ${pq(pk3.joint_zero.p)}`],
   ["Root mean squared error", f3(PKF["through zero (adopted)"].rmse), f3(PKF["one intercept"].rmse), f3(pk3.rmse)]],
  [2400, 2400, 2400, 2440], [1, 2, 3]));
add(CAPTION(`Ordinary least squares on ${comma(PK.n)} players drafted from 2007 to 2017; surplus in millions of dollars at the 2025-26 cap. Coefficient (robust standard error) [two-sided p-value].`));
const PS = PK.p_star;
add(FIGURE("fig_picks.png", "Figure 3. Draft position and surplus",
  `Left: Bacon's star probability by draft position. Right: the mean surplus delivered by players drafted in each group of draft positions from 2007 to 2017 (grey, with 95% intervals), and the model's mean value for the same picks (orange). Millions of dollars at the 2025-26 cap.`));
add(TITLE("Table 9. The value of a pick at selected draft positions"));
const PSK = ["1", "5", "10", "13", "20", "32", "50", "64", "100", "150", "200"];
add(TABLE(["Draft position", ...PSK],
  [["Star probability", ...PSK.map((k) => pct(PS[k]))], ["Value", ...PSK.map((k) => money(STAR.b * PS[k]))]],
  [1680, ...PSK.map(() => 723)], PSK.map((_, i) => i + 1), new Set(), 16));
add(CAPTION("Value: the star value times the star probability, in millions of dollars at the 2025-26 cap."));

add(H2("Valuing a traded pick"));
add(P("A traded pick is valued at the trade date by what was known then about its draft position:"));
add(BULLET("A pick in the next draft, traded once that draft's regular season has started: the draft position its original team's place in the standings gives on the trade date, worst first, by points percentage."));
add(BULLET("A pick in the next draft traded before that season's first game, or a pick in a later draft: the average star probability over its round's draft positions."));
add(BULLET("A pick traded during its own draft: its actual draft position."));
add(P(`The lottery and the reordering of playoff teams are not modelled, and conditional picks are valued as if their conditions were met. The 2019 second-round pick Montreal received was traded before the 2018-19 season began, so it is valued at the average star probability over round 2's draft positions, ${pct(TPK.star_chance, 2)}, times the star value: ${mil(TPK.value_M)}.`));

// =====================================================================================================================
// 3. PROSPECTS
// =====================================================================================================================
add(H1("3. Prospects"));
add(P("A prospect is a drafted player the player model does not yet value: a skater with no NHL season of 10 or more games in the three before the valuation season, or a goaltender with no NHL game in the six before it. A prospect is valued in the pick model's currency. The outcome the prospect model learns from is his remaining surplus: the surplus a 2007-2017 draftee went on to deliver from a season in which he was still a prospect to the end of club control, as the pick model prices it."));
add(H2("Draft position, and how its value fades"));
add(P("I regressed each prospect's remaining surplus on the star probability for his draft position, interacted with an indicator for each season from D+1 to D+4 and one for D+5 onwards, with no intercept. The data are each season in which a 2007-2017 draftee was still a prospect. The coefficient for each season is that season's star value: the surplus value if a prospect in that season were certain to become a star."));
add(EQ(["remaining surplus = star value for D+n × star probability + error"]));
add(TITLE("Table 10. The star value for a player still a prospect, by season"));
add(TABLE(["Season", "Prospects", "Star value (s.e.)", "p-value", "#1 pick", "#13 pick", "#32 pick"],
  S1.map((r) => [r.k === "0" ? "D+1 (at the draft)" : SEAS[r.k], r.k === "4+" ? `${comma(r.players)} (${comma(r.rows)} prospect-seasons)` : comma(r.players), `${money(r.star)} (${f2(r.se)})`, pfmt(r.p), money(r.pick1), money(r.star * PR.p_star["13"]), money(r.pick32)]),
  [1800, 2100, 1500, 900, 1110, 1110, 1120], [1, 2, 3, 4, 5, 6]));
add(CAPTION("Drafted players of 2007 to 2017 still prospects in each season. Star value in millions of dollars at the 2025-26 cap; standard errors clustered by player, since one player appears in several seasons; two-sided p-values. The pick columns multiply the star value by the star probability for the draft position."));
add(P(`A prospect keeps most of his draft position's value through D+3 and loses most of it over the next two seasons, because of who is left. Of the 110 top-ten picks of 2007 to 2017, ${f1(cum("picks 1-10", 1))}% had reached the NHL by D+1 and ${f1(cum("picks 1-10", 3))}% by D+3. Of the ${comma(ARR["rounds 3-7"].n)} picks from rounds 3 to 7, ${f1(cum("rounds 3-7", 3))}% had reached it by D+3, and ${f1(100 * ARR["rounds 3-7"].n_arrived / ARR["rounds 3-7"].n)}% ever did. By D+4, most top picks who will reach the NHL have done so. The prospects left are mostly later picks and top picks who missed, and draft position no longer separates those who will succeed from those who will not.`));

add(H2("Production"));
const B1 = PR.build["1"];
add(P("Draft position is one element of what predicts a prospect's value; how much he scores after the draft is another. A season's production is his points, from Elite Prospects, times his league-season's NHLe factor, per 82 games, for seasons of 10 or more games. His production level weights his three seasons before the valuation season 50/30/20; a prospect with no such season gets an indicator instead. Production enters with its square, so each point adds more the more he already scores, because most surplus comes from the few prospects who become stars:"));
add(EQ(["remaining surplus = a × S + b × P + c × ", ["^", "P", "2"], " + d × N + error"]));
add(P(`where S is the star probability for his draft position, P is his production level, and N is 1 when he has no production record; each coefficient takes a separate value for each season, as above. Table 11 builds the regression up in D+2, the season Suzuki was in at the trade, and Appendix B does the same for each season. In D+2, adding linear production lowers the star value from ${mil(B1["slot alone"].terms.p_star.b)} to ${mil(B1["slot + production"].terms.p_star.b)}, and adding its square raises R² from ${f3(B1["slot + production"].r2)} to ${f3(B1["slot + production + squared"].r2)}. The squared term is statistically significant at the 5% level in each season through D+4.`));
const BROW = [["p_star", "Star probability (S)"], ["nhle82", "Production level (P)"], ["nhle82_sq", "Production level squared (P²)"], ["no_record", "No production record (N)"], ["prod_x_age", "P × (age − 18)"]];
const bSpecs = Object.keys(B1);
const BHEAD = { "slot alone": "Draft position\nalone", "slot + production": "+ linear\nproduction", "slot + production + squared": "+ production\nsquared", adopted: "+ age discount\n(adopted)" };
add(TITLE("Table 11. A prospect in D+2, built up one term at a time"));
add(TABLE(["Term", ...bSpecs.map((s) => BHEAD[s])],
  [...BROW.map(([k, lab]) => [lab, ...bSpecs.map((s) => cc(B1[s].terms[k], 3))]),
   ["R² (no intercept)", ...bSpecs.map((s) => f3(B1[s].r2))]],
  [2440, 1800, 1800, 1800, 1800], [1, 2, 3, 4]));
add(CAPTION(`${comma(B1.adopted.rows)} skaters drafted from 2007 to 2017 who were prospects in D+2; remaining surplus in millions of dollars at the 2025-26 cap. Each column is one regression with the full set of season interactions, shown for D+2; coefficient (standard error, clustered by player) [two-sided p-value].`));
add(P(`In D+4, once production is known, draft position is not statistically significant at the 5% level (${pq(PR.build["3"]["slot + production + squared"].terms.p_star.p)}), so it is left out from D+4 on. From D+5 on its coefficient is negative (${pq(PR.build["4+"]["slot + production + squared"].terms.p_star.p)}), which makes no logical sense for a draft position, and it stays out. From D+5 on, neither production term is statistically significant at the 5% level, alone or jointly (${pq(PR.joint_late.production.p)}). Production is kept there, since the model was specified before that test and keeps the same form as in the earlier seasons.`));

add(H2("Age"));
const AD1 = PR.adopted.find((t) => t.k === "1").terms;
add(P(`The same production is worth less from an older prospect: a 20-year-old scoring at a given NHLe rate is closer to his peak than an 18-year-old scoring at the same rate. From D+1 to D+4, production is discounted by his age on September 15 of the valuation season, less 18. The adopted model is:`));
add(EQ(["remaining surplus = a × S + b × P + c × ", ["^", "P", "2"], " + d × N + e × P × (A − 18) + error"]));
add(P(`where A is his age. In D+2, each year of age lowers the value of each NHLe point by $${f3(-AD1.prod_x_age.b)} million (${pq(AD1.prod_x_age.p)}). Figure 4 shows the adopted model for a prospect drafted 13th, in D+2, at three ages; Table 12 gives it for each season.`));
add(FIGURE("fig_prospect.png", "Figure 4. A prospect drafted 13th, in D+2",
  `The adopted model's value against production level, at ages 19, 20, and 21 on September 15 of the valuation season, with Nick Suzuki at the trade. Vertical lines mark the 25th, 50th, 75th, and 90th percentiles of production level among prospects in D+2. Millions of dollars at the 2025-26 cap.`));
add(TITLE("Table 12. The adopted prospect model, by season"));
const ADP = Object.fromEntries(PR.adopted.map((t) => [t.k, t]));
add(TABLE(["Term", ...G5.map((g) => SEAS[g])],
  [...BROW.map(([k, lab]) => [lab, ...G5.map((g) => cc(ADP[g].terms[k], 3))]),
   ["Prospect-seasons", ...G5.map((g) => comma(ADP[g].rows))]],
  [2440, 1440, 1440, 1440, 1440, 1440], [1, 2, 3, 4, 5]));
add(CAPTION("One regression with the full set of season interactions, no intercept; remaining surplus in millions of dollars at the 2025-26 cap. Coefficient (standard error, clustered by player) [two-sided p-value]. A blank cell: the term is not in that season's model. From D+4 on, each prospect without a production record delivered nothing, so that coefficient is exactly zero, with no standard error."));

add(H2("Nick Suzuki"));
const WP = W.parts;
add(P(`Suzuki was traded at the start of his D+2 season. His draft position's star probability is ${pct(W.inputs.p_star)}, his production level is ${f1(W.prod)} NHLe points per 82 games (above the 90th percentile in D+2, ${f1(PR.prod_pct_k1["90"])}), and he was ${f1(W.age)} on September 15, 2018. Table 13 adds up his value.`));
add(TITLE("Table 13. Nick Suzuki's value at the trade"));
add(TABLE(["Term", "His input", "Coefficient", "Contribution"],
  [["Star probability", f3(W.inputs.p_star), f3(W.coefs.p_star), money(WP.p_star)],
   ["Production level", f2(W.inputs.nhle82), f4(W.coefs.nhle82), money(WP.nhle82)],
   ["Production level squared", f1(W.inputs.nhle82_sq), f4(W.coefs.nhle82_sq), money(WP.nhle82_sq)],
   ["No production record", "0", f3(W.coefs.no_record), money(0)],
   ["P × (age − 18)", f2(W.inputs.prod_x_age), f4(W.coefs.prod_x_age), money(WP.prod_x_age)],
   ["Value", "", "", `**${money(W.value)}**`]],
  [3000, 2200, 2200, 2240], [1, 2, 3]));
add(CAPTION("Millions of dollars at the 2025-26 cap. The coefficients are Table 12's D+2 column."));
add(P(`On draft position alone he would be worth ${mil(W.slot)}; his production and age add ${mil(W.value - W.slot)}. Suzuki was drafted in 2017, so his own draft is inside the regression that values him; fitted without the 2017 draft, his value is ${mil(W.own_out)}.`));

add(H2("Goaltenders and undrafted players"));
add(P(`NHLe converts scoring, which says nothing about a goaltender, so a goaltender prospect is valued on draft position alone, with Table 10's star values. An undrafted player is valued only once he holds an NHL contract, which gives a club his rights. He is valued with the same model, his star probability set to zero and his seasons counted from his first draft-eligible year. Of the prospects traded from July 2017 to March 2022, the ${comma(PR.traded.drafted)} drafted prospects (${comma(PR.traded.drafted_players)} different players, as some were traded more than once) are worth ${mil(PR.traded.tot_main)} in total, and the ${PR.traded.undrafted_skaters_valued} undrafted skaters on NHL contracts ${mil(PR.traded.tot_undrafted)}.`));

// =====================================================================================================================
// 4. THE TRADE
// =====================================================================================================================
add(H1("4. The Trade on One Scale"));
add(P(`The player model states a player's value at the cap of his valuation season, $${f1(M(CAP18))} million in 2018-19. To add the four assets, Pacioretty's and Tatar's values are restated at the 2025-26 cap, multiplied by ${f1(M(CAP25))} / ${f1(M(CAP18))} = ${f3(to25)}, which changes their size but not their sign or order (Table 14).`));
const A_ = TRD.assets;
add(TITLE("Table 14. The trade, each asset at the trade date"));
add(TABLE(["Asset", "Received by", "Valued by", "At the 2018-19 cap", "At the 2025-26 cap"],
  [...A_.map((a) => [a.asset, a.to === "MTL" ? "Montreal" : "Vegas", a.kind === "player" ? "Player model" : (a.kind === "pick" ? "Pick model" : "Prospect model"), a.value_page === undefined ? "" : money(a.value_page), money(a.value)]),
   ["Total received by Montreal", "", "", "", `**${money(TRD.MTL)}**`], ["Total received by Vegas", "", "", "", `**${money(TRD.VGK)}**`]],
  [2700, 1400, 1700, 1900, 1940], [3, 4]));
add(CAPTION("Surplus value in millions of dollars. Pacioretty's value includes the four-year extension he signed with Vegas on the day of the trade."));
add(FIGURE("fig_trade.png", "Figure 5. The trade on one scale", "Each asset's surplus value at the trade date, in millions of dollars at the 2025-26 cap, by the club that received it."));
add(P(`At the trade date, both players carried contracts priced above their forecast play, so each club took on negative surplus value. Vegas received Pacioretty with the extension it chose to sign, worth ${mil(TRD.assets[0].value)}. Montreal gave up only the 2018-19 season of his old contract, worth ${mil(TRD.pacioretty_old_contract.value)}, and received ${mil(TRD.MTL)}: Tatar's ${mil(TRD.assets[1].value)}, partly offset by Suzuki and the pick. Salary retained in the trade is not yet in these values: Montreal kept $450,000 of Pacioretty's 2018-19 cap hit, and Vegas kept $500,000 of Tatar's in each of his three seasons.`));

// =====================================================================================================================
// 5. LIMITS
// =====================================================================================================================
add(H1("5. What the Models Do Not Do"));
add(BULLET("Fitted on completed careers. The star values for picks and prospects are fitted on the 2007-2017 drafts, whose careers run past many of the trades valued, so a club at the trade could not have known them. A 2007-2017 draftee is also inside the regression that values him; his value with his own draft left out is reported beside it."));
add(BULLET("Fitted on later contracts. The price line is fitted on contracts that started from 2018-19 to 2025-26, and the control-season weights on decisions about contracts that ended from 2018-19 to 2024-25. Both samples run past many of the trades they price, and one price line prices each season of each valuation."));
add(BULLET("Retained salary and conditional picks. Neither is yet in the values: a retained share of a cap hit moves cost from one club to the other, and a conditional pick is valued as if its conditions were met."));
add(BULLET("Goaltenders. The forecast is flat, and the price line is fitted on WAR before the pull toward the league average but prices the pulled forecast. The exit table is fitted on departures from 2018-19 to 2025-26, after many of the valuations it is used in. Goaltender prospects share one star value with skaters."));
add(BULLET("Undrafted prospects. Only those on NHL contracts are valued, on a model fitted on drafted players, which assumes an undrafted player converts production as a drafted one does."));
add(BULLET("Arbitration eligibility. PuckPedia's flag is set at the contract's end, so a valuation dated earlier reads eligibility as of a later date."));

// =====================================================================================================================
// REFERENCES AND APPENDICES
// =====================================================================================================================
add(H1("References"));
add(P("Efron, B., and C. Morris. 1975. \"Data Analysis Using Stein's Estimator and Its Generalizations.\" *Journal of the American Statistical Association* 70 (350): 311-319."));
add(P("Nadaraya, E. A. 1964. \"On Estimating Regression.\" *Theory of Probability and Its Applications* 9 (1): 141-142."));
add(P("Tobin, J. 1958. \"Estimation of Relationships for Limited Dependent Variables.\" *Econometrica* 26 (1): 24-36."));
add(P("Watson, G. S. 1964. \"Smooth Regression Analysis.\" *Sankhyā, Series A* 26 (4): 359-372."));

add(H1("Appendix A. Games Share and Chance of Playing, Each Season Ahead"));
add(P("The adopted regressions of Tables 2 and 3 are fitted separately for each season ahead, on the fit for the 2025-26 valuation season. Tables A1 and A2 give each, from the valuation season (0) to five seasons ahead."));
const HS = ["0", "1", "2", "3", "4", "5"];
const gsA = (h) => GS[h]["+ trailing WAR (adopted)"];
add(TITLE("Table A1. Games share, adopted regression, by seasons ahead"));
add(TABLE(["Term", ...HS],
  [...GSROW.map(([k, lab]) => [lab, ...HS.map((h) => cc(gsA(h).terms[k], 4))]), ["R²", ...HS.map((h) => f3(gsA(h).r2))], ["Player-seasons", ...HS.map((h) => comma(gsA(h).n))]],
  [2140, 1250, 1250, 1250, 1250, 1250, 1250], [1, 2, 3, 4, 5, 6], new Set(), 15));
add(CAPTION("Ordinary least squares; coefficient (standard error, clustered by player) [two-sided p-value]."));
const ppA = (h) => PP[h][ppKey(h)];
add(TITLE("Table A2. Chance of playing, adopted regression, by seasons ahead"));
add(TABLE(["Term", ...HS],
  [...PPROW.map(([k, lab]) => [lab, ...HS.map((h) => cc(ppA(h).terms[k], 3))]), ["McFadden pseudo-R²", ...HS.map((h) => f3(ppA(h).pseudo_r2))], ["Player-seasons", ...HS.map((h) => comma(ppA(h).n))]],
  [2140, 1250, 1250, 1250, 1250, 1250, 1250], [1, 2, 3, 4, 5, 6], new Set(), 15));
add(CAPTION("Logistic regression on the log-odds; coefficient (standard error, clustered by player) [two-sided p-value]."));

add(H1("Appendix B. The Prospect Model Built Up, Each Season"));
add(P("Table 11 builds the prospect model up one term at a time in D+2. Table B1 does the same for each season. Within a season, each row adds one term to the row above, except the adopted rows for D+4 and from D+5 on, which leave out draft position, and from D+5 on the age discount."));
const BR = [];
G5.forEach((g) => {
  Object.keys(PR.build[g]).forEach((s) => {
    const sp = PR.build[g][s];
    const ADLAB = { "3": "Adopted: production, its square, and age; no draft position", "4+": "Adopted: production and its square only" };
    const lab = s === "adopted" && ADLAB[g] ? ADLAB[g] : BHEAD[s].replace("\n", " ");
    BR.push([s === "slot alone" ? `**${SEAS[g]}**\n${lab}` : lab, ...BROW.map(([k]) => cc(sp.terms[k], 3)), f3(sp.r2)]);
  });
});
add(TITLE("Table B1. The prospect model built up one term at a time, by season"));
add(TABLE(["Season and model", "S", "P", "P²", "N", "P × (age − 18)", "R²"], BR, [2140, 1350, 1300, 1300, 1300, 1450, 800], [1, 2, 3, 4, 5, 6], new Set(), 15));
add(CAPTION("Each block is one season, each row one regression with the full set of season interactions and no intercept. S: star probability; P: production level; N: no production record. Coefficient (standard error, clustered by player) [two-sided p-value]; R² measured without an intercept."));

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
