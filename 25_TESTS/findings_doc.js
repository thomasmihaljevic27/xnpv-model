// findings_doc.js v4.0 -- builds "Findings.docx" (40_DOCS/), fully worded, in the format of "Valuing Players, Draft Picks,
// and Prospects" (model_doc.js v5.0): numbered title-case sections, sentence-case subsections, the regressions as Word
// equations, numbered tables with captions, the full regressions in an appendix.
//
// v4.0 (2026-11-25, session 2026-11-25; Thomas: "turn the Findings doc into a fully worded one of the same format. Ensure
// consistency in terminology per prior meetings with Karl and my personal writing style"). The plan he agreed: the five
// take-aways (the models predict trades; clauses, ages 28 to 31 and defencemen; the former top-10 pick as exploratory; about
// 40% of a contract's value; how far the evidence reaches); "trade-day xNPV" and "realized NPV" for the two values;
// "difference variables" for the +1 / -1 / 0 terms; every value a share of the 2025-26 cap ("Both documents"); the four
// wordings agreed 2026-11-24 (the finding rule's grammar, the cap-dump sentence's verb, the cap hit over the seasons of
// the contract, "0 if neither or both"); the cap-dump note in the discussion (Thomas, 2026-11-18). Every figure is read from
// OUTPUT_DIR/findings_doc/numbers.json (25_TESTS/findings_numbers.py v1.0), never typed. The text he wrote in the point-form
// versions (v3.2-v3.14: the defenceman bullet, the two-stage passage, the clause reading) is kept in substance and in his
// words where a sentence survives the change of form. Previous body: git show HEAD~1:25_TESTS/findings_doc.js (v3.14).
//
// Run:  NODE_PATH=<folder with docx> node 25_TESTS/findings_doc.js   (LINT_OUT=<file.md> writes the prose for the linter)

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType, HeadingLevel,
  BorderStyle, ShadingType, Footer, PageNumber, Math: OMath, MathRun, MathSubScript, MathSum,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const N = JSON.parse(fs.readFileSync(path.join(ROOT, "30_OUTPUT", "findings_doc", "numbers.json"), "utf8"));
const OUTFILE = process.env.DOC_OUT || path.join(ROOT, "40_DOCS", "Findings.docx");   // 2026-11-24: renamed by Thomas
const VERSION = "findings_doc.js v4.0";
const TEXT = [];

// ---- formatting (as model_doc.js) ------------------------------------------------------------------------------------
const FONT = "Calibri";
const fx = (x, d) => Number(x).toFixed(d);
const f2 = (x) => fx(x, 2), f3 = (x) => fx(x, 3);
const comma = (x) => Number(x).toLocaleString("en-US");
const CAP25M = 95.5;
const K25 = 100 / CAP25M;                                 // $M at the 2025-26 cap -> percent of it
const sg = (x, d = 2) => `${x < 0 ? "-" : "+"}${fx(Math.abs(x), d)}`;
const sh = (x, d = 2) => `${x < 0 ? "-" : ""}${fx(Math.abs(x * K25), d)}%`;          // a $M value as a share, "1.69%"
const shc = (x, d = 2) => `${sh(x, d)} of the cap`;
const pq = (p) => (p < 0.0005 ? "p < 0.001" : `p = ${p < 0.01 ? fx(p, 3) : fx(p, 3)}`);
const pv = (p) => (p < 0.0005 ? "<0.001" : fx(p, 3));
const pct = (x, d = 1) => `${fx(100 * x, d)}%`;
const ci = (lo, hi, k = K25) => `[${sg(lo * k)}, ${sg(hi * k)}]`;
// a coefficient cell: share of the cap (standard error) [p]
const cc = (t) => `${sg(t[0] * K25)} (${f2(t[1] * K25)})\n[${pv(t[2])}]`;

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
  const L = (x) => (Array.isArray(x) && !["_", "sum"].includes(x[0]) ? x : [x]);
  return pieces.map((x) => {
    if (!Array.isArray(x)) return new MathRun(x);
    if (x[0] === "_") return new MathSubScript({ children: mathKids(L(x[1])), subScript: mathKids(L(x[2])) });
    if (x[0] === "sum") return new MathSum({ children: mathKids(x[2]), subScript: mathKids(L(x[1])) });
    throw new Error(`EQ piece ${x[0]}`);
  });
}
function mathText(pieces) {
  const L = (x) => (Array.isArray(x) && !["_", "sum"].includes(x[0]) ? x : [x]);
  return pieces.map((x) => (!Array.isArray(x) ? x : (x[0] === "_" ? `${mathText(L(x[1]))}_${mathText(L(x[2]))}` : `Σ_${mathText(L(x[1]))} ${mathText(x[2])}`))).join("");
}
const EQ = (pieces) => { TEXT.push(mathText(pieces)); return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 100, after: 140 }, children: [new OMath({ children: mathKids(pieces) })] }); };
const SUB = (b, i) => ["_", b, i];

const TABS = ["s2", "find", "rep", "other", "top10", "types", "price", "A1", "A2", "A3"];
const APPX = { A1: "A1", A2: "A2", A3: "A3" };
const tn = (k) => (APPX[k] ? APPX[k] : String(TABS.indexOf(k) + 1));
const T = (k) => `Table ${tn(k)}`;
const TT = (k, title) => TITLE(`${T(k)}. ${title}`);
const border = { style: BorderStyle.SINGLE, size: 4, color: "C9C8C3" };
const borders = { top: border, bottom: border, left: border, right: border };
function TABLE(header, rows, widths, numeric = [], size = 16) {
  const tot = widths.reduce((a, b) => a + b, 0);
  if (tot > 9660) throw new Error(`table too wide: ${tot}`);
  const cell = (text, i, head, kp) => new TableCell({
    borders, width: { size: widths[i], type: WidthType.DXA },
    shading: head ? { fill: "EFEEEA", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 40, bottom: 40, left: 70, right: 70 },
    children: String(text).split("\n").map((line) => new Paragraph({ keepNext: kp,
      alignment: numeric.includes(i) ? AlignmentType.RIGHT : AlignmentType.LEFT, children: runs(line, { size, bold: !!head }) })),
  });
  return new Table({ width: { size: tot, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: header.map((t, i) => cell(t, i, true, true)) }),
      ...rows.map((r, j) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, i, false, j < rows.length - 1)) }))] });
}

// ---- numbers -------------------------------------------------------------------------------------------------------------
const S2 = N.s2, R = N.reg, MR = "main player rule", AR = "any player rule";
const O = ["trade-day grade", "realized value, WAR", "realized value, Game Value", "realized value, seasons played"];
const r_ = (rule, col, o = 0) => R[rule][col][O[o]];
const REP = N.replication, T10 = N.top10, S4 = N.s4;
const isFinding = (rule, col) => { const a = r_(rule, col, 0), b = r_(rule, col, 1); return a[2] < 0.05 && b[2] < 0.05 && Math.sign(a[0]) === Math.sign(b[0]); };
for (const [rule, col] of [[MR, "main_clause"], [AR, "any_clause"], [MR, "age28"], [MR, "defence"]]) if (!isFinding(rule, col)) throw new Error(`${rule} ${col} is no longer a finding: rewrite Section 3`);
for (const [rule, col] of [[AR, "any_age28"], [AR, "any_defence"], [MR, "top15"], [AR, "any_top15"], [MR, "goalie"], [MR, "age32"]]) if (isFinding(rule, col)) throw new Error(`${rule} ${col} is now a finding: rewrite Section 3`);
const reduce = (mc, ac) => O.map((_, i) => 1 - r_(AR, ac, i)[0] / r_(MR, mc, i)[0]);
const rangePct = (xs) => `${Math.round(100 * Math.min(...xs))}% to ${Math.round(100 * Math.max(...xs))}%`;

const kids = [];
const add = (...xs) => xs.flat().forEach((x) => kids.push(x));
add(new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: "Findings", bold: true, size: 40, font: FONT })] }));

// =====================================================================================================================
// OPENING
// =====================================================================================================================
add(P(`This document tests whether NHL clubs misprice some kinds of trades. Each asset in a trade, a player under contract, a draft pick, or a prospect, is valued on the trade date by the models of "Valuing Players, Draft Picks, and Prospects", using only what was known that day. What each asset then delivered is valued at the same prices. If the market prices assets correctly, no kind of trade should leave the clubs that make it behind on both counts. The findings are the characteristics on which clubs came out behind on both.`));
add(P(`Every value is stated as a share of the 2025-26 salary cap of $${fx(CAP25M, 1)} million, so 1% of the cap is $${fx(CAP25M / 100, 3)} million. A value at an earlier season's cap is restated at the 2025-26 cap first, so trades from different seasons are in one unit.`));

// =====================================================================================================================
// 1. HOW A FINDING IS MADE
// =====================================================================================================================
add(H1("1. How a Finding Is Made"));
add(H2("The trades"));
add(P(`The sample is the ${comma(N.trades_s2)} trades made from July 1, 2017 to March 28, 2022 with every asset valued. The window was declared before any result was computed. It ends four seasons before the most recent season played, so the assets traded in it have had at least four seasons to deliver. The trades after it, to March 2026, are used to test whether a result holds in trades it was not found on.`));
add(H2("Trade-day xNPV"));
add(P(`On the trade date each asset is valued by the player, pick, or prospect model, and that value is its expected net present value (xNPV). A club's trade-day xNPV is the xNPV of what it received less the xNPV of what it gave up:`));
add(EQ(["trade-day xNPV = ", ["sum", "a ∈ received", [SUB("xNPV", "a")]], " − ", ["sum", "a ∈ given", [SUB("xNPV", "a")]]]));
add(P(`A positive value means the club received more than it gave up, at the models' prices; a negative value means it paid too much. Every value lost by one club is gained by the other, so the two clubs' trade-day xNPV always sum to zero.`));
add(H2("Realized NPV"));
add(P(`Each asset is then followed after the trade, whoever holds it later, and what it delivered is valued at the same prices: its WAR in each season through 2025-26 priced on the price line, less what it cost: a player's cap hit, or a drafted player's cost under the CBA's rules. A pick is followed to the player drafted with it. A club's realized net present value (realized NPV) is what its assets delivered less what the assets it gave up delivered. Seasons from 2026-27 on have not been played, so a contract that runs past 2025-26, or a pick or prospect who has not yet reached the NHL, is valued again for those seasons by the same models at the 2026-27 valuation season, with everything through 2025-26 known. That re-valuation is ${pct(N.revalued_share)} of the size of the clubs' realized NPV in the regressions below.`));
add(H2("Two ways to assign a characteristic"));
add(P(`A characteristic of the player a club received, such as his age, can be assigned in two ways. Under the main player rule, a club has the characteristic when the player it received with the highest cap hit has it. Under the any player rule, a club has it when any player it received has it. Of the clubs in the regressions, ${N.clubs_two_plus} received two or more players, so the two rules differ only for those; the any player rule is a check on the main player rule. A characteristic of the trade itself, such as buying at the trade deadline, is the same under both rules.`));
add(H2("The regression"));
add(P(`Each characteristic is entered as a difference variable: the first club's yes-or-no for it less the other club's. It is 1 if the first club received a player with the characteristic, −1 if it sent one away, and 0 if neither club received one or both did. For a measured characteristic, such as a player's recent production, it is the amount the first club received less the amount it sent away. The first club's trade-day xNPV, or its realized NPV, is regressed on the difference variables:`));
add(EQ([SUB("y", "i"), " = ", ["sum", "j", [SUB("β", "j"), SUB("x", "ij")]], " + ", SUB("ε", "i")]));
add(P(`Here y_{i} is the first club's value in trade i, the club first in alphabetical order, and x_{ij} is difference variable j. Each coefficient β_{j} is how much a club gains, as a share of the cap, from receiving rather than sending a player with characteristic j, with the others held constant. There is no constant, because one club's gain is the other's loss: the second club's values are the exact mirror image of the first's, so which club comes first changes no estimate. Each trade enters once. Standard errors are robust, which allows the size of the misses to differ from trade to trade. The regressions use the ${comma(N.reg_n)} two-team trades; the trades among three clubs are left out.`));
add(P("The regression holds 23 difference variables. Twelve describe the player received: aged 28 to 31 and aged 32 or over, each against 27 or under; a defenceman and a goaltender, each against a forward; a no-trade or no-move clause; signed as an unrestricted free agent; two seasons left on his contract and three or more, each against one; a former top-15 draft pick; his recent production, his WAR weighted 50/30/20 over his three most recent seasons; how far that production exceeds the models' forecast for the season of the trade; and his share of games played in the most recent season. Under the any player rule the last three are averages over the players received, weighted by cap hit. Ten describe the trade: the club sold a player for just picks and prospects; it was higher in the standings and traded in the 14 days before the deadline, or earlier in the season; it received a rental (a player in the final season of his contract, due to become an unrestricted free agent, traded during the season); it retained salary; it received one asset for two or more; it was paid to take on a contract to clear cap for another team; a new general manager sold a contract signed by his predecessor; it received a restricted free agent in his final contract season; it received only picks in rounds 6 and 7. The last marks whether the club received a player at all, since a club that received none has every player characteristic at 0."));
add(H2("What counts as a finding"));
add(P(`A characteristic is a finding when its coefficient is statistically significant at the 5% level in both the trade-day xNPV regression and the realized NPV regression, with the same sign. The trade-day regression shows what clubs paid against the models' value; the realized regression shows whether the assets bore the models out. A characteristic significant on trade day alone could be the models' error rather than the market's; one significant in realized NPV alone could be luck after the trade.`));
add(P(`Each finding is then checked two ways. Realized NPV is recomputed with Game Value in place of WAR, a measure of each skater's share of his team's expected goals built with no input from the WAR model, so that a result does not rest on one measure of performance being compared with itself. And it is recomputed on the seasons played through 2025-26 alone, with nothing re-valued, so that a result does not rest on the models' view of seasons not yet played.`));

// =====================================================================================================================
// 2. THE MODELS PREDICT HOW TRADES TURN OUT
// =====================================================================================================================
add(H1("2. The Models Predict How Trades Turn Out"));
add(P(`Before asking what clubs misprice, the models have to be shown to price trades well. ${T("s2")} compares each club's trade-day xNPV with its realized NPV. The club the models favoured on trade day came out ahead in ${pct(S2.war.fav[0])} of the ${comma(S2.war.n)} trades, against the 50% a coin would give (p = ${f3(S2.war.fav[3])}). The slope of realized NPV on trade-day xNPV is ${f3(S2.war.slope[0])}: about three-quarters of the gap the models predicted on trade day shows up in realized NPV. Measured with Game Value instead of WAR, the slope is ${f3(S2.gv.slope[0])}, so the result does not depend on the measure of performance.`));
add(TT("s2", "Trade-day xNPV against realized NPV"));
add(TABLE(["", "Realized NPV, WAR", "Realized NPV, Game Value", "Fully played-out trades, WAR"],
  [["Favoured club came out ahead", `${pct(S2.war.fav[0])} [${pct(S2.war.fav[1])}, ${pct(S2.war.fav[2])}]`, `${pct(S2.gv.fav[0])} [${pct(S2.gv.fav[1])}, ${pct(S2.gv.fav[2])}]`, `${pct(S2.played_out.fav_nz[0])} [${pct(S2.played_out.fav_nz[1])}, ${pct(S2.played_out.fav_nz[2])}]`],
   ["Slope of realized NPV on trade-day xNPV", `${f3(S2.war.slope[0])} [${f3(S2.war.slope[1])}, ${f3(S2.war.slope[2])}]`, `${f3(S2.gv.slope[0])} [${f3(S2.gv.slope[1])}, ${f3(S2.gv.slope[2])}]`, `${f3(S2.played_out.slope[0])} [${f3(S2.played_out.slope[1])}, ${f3(S2.played_out.slope[2])}]`],
   ["R-squared", f3(S2.r2), "", ""],
   ["Trades", comma(S2.war.n), comma(S2.gv.n), comma(S2.played_out.n)]],
  [3400, 2050, 2050, 2050], [1, 2, 3]));
add(CAPTION(`Trades from July 1, 2017 to March 28, 2022. 95% confidence intervals from 2,000 resamples of trades, in square brackets. Fully played-out trades: those in which every asset has reached the NHL and no season is re-valued; the share leaves out the sides whose realized NPV is exactly zero.`));
add(P(`The fully played-out trades are a check on the re-valued seasons, and they are not a fair sample of trades: a trade qualifies only if every pick and prospect in it has reached the NHL, so it is mostly player-for-player trades. In the ${S2.played_out.n} such trades the favoured club came out ahead in ${pct(S2.played_out.fav_nz[0])} of those decided, and the slope is ${f3(S2.played_out.slope[0])}, with a wide interval.`));
const AS = S2.assets;
add(P(`By kind of asset, realized NPV less trade-day xNPV is ${sh(AS.players[0])} of the cap a player ${ci(AS.players[1], AS.players[2])} over ${comma(AS.players[4])} players and ${sh(AS.prospects[0])} a prospect ${ci(AS.prospects[1], AS.prospects[2])} over ${comma(AS.prospects[4])}, neither statistically significant; and ${sh(AS.picks[0])} a pick ${ci(AS.picks[1], AS.picks[2])} over ${comma(AS.picks[4])}, statistically significant at the 5% level (p = ${f3(AS.picks[3])}). Picks delivered less than the pick model forecast; the pick model's limits are set out in "Valuing Players, Draft Picks, and Prospects".`));

// =====================================================================================================================
// 3. WHAT CLUBS OVERPAY FOR
// =====================================================================================================================
add(H1("3. What Clubs Overpay For"));
add(P(`${T("find")} gives the characteristics that are findings. A player with a no-trade or no-move clause is a finding under both rules. A player aged 28 to 31 and a defenceman are findings under the main player rule. In each case the coefficient is negative: the club that received such a player came out behind, on trade day and in realized NPV, and further behind in realized NPV.`));
add(TT("find", "The findings: the club that received the player"));
const FROW = [["A player with a no-trade or no-move clause", MR, "main_clause"], ["", AR, "any_clause"], ["A player aged 28 to 31", MR, "age28"], ["", AR, "any_age28"], ["A defenceman", MR, "defence"], ["", AR, "any_defence"]];
add(TABLE(["Club received", "Rule", "Trade-day xNPV", "Realized NPV, WAR", "Realized NPV, Game Value", "Realized NPV, seasons played"],
  FROW.map(([lab, rule, col]) => [lab, rule === MR ? "Main player" : "Any player", ...O.map((o) => cc(R[rule][col][o]))]),
  [2600, 1100, 1480, 1480, 1480, 1480], [2, 3, 4, 5]));
add(CAPTION(`Coefficients of the regression in Section 1, as a share of the 2025-26 cap (robust standard error) [two-sided p-value], ${comma(N.reg_n)} two-team trades from July 2017 to March 2022, every other characteristic held constant. Negative: the club that received the player came out behind. The full regressions are in Tables A1 and A2.`));
add(H2("Players with a no-trade or no-move clause"));
const CP = N.clause_profile, CH = N.clause_cap_held;
add(P(`A club that received a player with a clause came out ${sh(-r_(MR, "main_clause", 0)[0])} of the cap behind on trade day and ${sh(-r_(MR, "main_clause", 1)[0])} behind in realized NPV under the main player rule, and the result holds on Game Value and on the seasons played. A clause is not bad value in itself. It is negotiated by a player who has earned the leverage to ask for it, usually as an unrestricted free agent, so the players who carry one are established veterans: ${fx(CP.age[0], 1)} years old on average against ${fx(CP.age[1], 1)} for other main players, with career WAR of ${fx(CP["career WAR"][0], 1)} against ${fx(CP["career WAR"][1], 1)}. One reading is that clubs pay for the reputation such a player has built, and that his performance after the trade falls short of it.`));
add(P(`A player with a clause also costs more, a cap hit of $${fx(CP["cap hit, $M"][0], 2)} million a season on average against $${fx(CP["cap hit, $M"][1], 2)} million, so the finding could be the cap hit in disguise. With the main player's cap hit held constant, the trade-day overpay is no longer statistically significant (p = ${f3(CH.net_M[2])}), which suggests it is largely Section 4's finding that clubs under-price contract cost. The realized loss remains (${shc(CH.out_net_M[0])}, ${pq(CH.out_net_M[2])}), and holding the player's reputation constant, through his career WAR and his best season, or leaving out the trades that cleared cap, changes neither result.`));
add(H2("Players aged 28 to 31"));
add(P(`A club that received a main player aged 28 to 31 came out ${sh(-r_(MR, "age28", 0)[0])} of the cap behind on trade day and ${sh(-r_(MR, "age28", 1)[0])} in realized NPV, against a player 27 or under. Clubs know that players decline with age; what they may do less well is predict which players will decline and how quickly. A player aged 32 or over is not a finding (${pq(r_(MR, "age32", 1)[2])} in realized NPV). One reading is that the players still in the league at 32 are those who have shown they age well, so a club acquiring one is less uncertain about the seasons ahead than a club acquiring a player of 29.`));
add(H2("Defencemen"));
add(P(`A club that received a main player who is a defenceman came out ${sh(-r_(MR, "defence", 0)[0])} of the cap behind on trade day and ${sh(-r_(MR, "defence", 1)[0])} in realized NPV, against a forward. This is not because defencemen fell short of their forecasts. Traded defencemen met them across games played, ice time, and each component of WAR (${sg(N.def_war[0])} WAR a season [${sg(N.def_war[1])}, ${sg(N.def_war[2])}]), and the clubs acquiring a defenceman finished where their trade-day xNPV predicted (realized NPV less trade-day xNPV of ${shc(N.def_side[0])} ${ci(N.def_side[1], N.def_side[2])}). The larger realized coefficient is partly a matter of comparison: the regression measures defencemen against forwards, and clubs acquiring forwards beat their trade-day xNPV (${N.fwd_side[0] > 0 ? "+" : ""}${shc(N.fwd_side[0])} ${ci(N.fwd_side[1], N.fwd_side[2])}). Clubs paid more for defencemen than for forwards of the same forecasted value.`));
add(H2("Why the rules may differ"));
add(P(`Under the any player rule a cheaper second player who is 28 to 31, or a defenceman, puts his club in the group, so the effects are smaller than under the main player rule: by ${rangePct(reduce("age28", "any_age28"))} for age and ${rangePct(reduce("defence", "any_defence"))} for defencemen across the four measures. Smaller players in a deal, who may be included to meet the cap, dilute the effect. Under the any player rule, age 28 to 31 is not statistically significant (p = ${f3(r_(AR, "any_age28", 0)[2])} on trade day and ${f3(r_(AR, "any_age28", 1)[2])} in realized NPV), and for defencemen the trade-day coefficient is not (p = ${f3(r_(AR, "any_defence", 0)[2])}).`));
add(H2("The trades after March 2022"));
const rp = (k, o) => REP[k][O[o]];
add(P(`The same regression on the ${comma(N.replication_n)} two-team trades from June 2022 to March 2026 tests whether the findings hold in trades they were not found on (${T("rep")}). These trades' realized NPV is mostly re-valuation, since they have had at most four seasons to play out, so trade-day xNPV is the firmer measure for them. Age 28 to 31 holds on both. The clause holds on trade day under both rules but not in realized NPV. The defenceman does not hold.`));
add(TT("rep", "The findings on the trades after March 2022"));
add(TABLE(["Club received", "Rule", "Trade-day xNPV", "Realized NPV, WAR"],
  [["A player with a clause", "Main player", "main player rule|main_clause"], ["", "Any player", "any player rule|any_clause"], ["A player aged 28 to 31", "Main player", "main player rule|age28"], ["A defenceman", "Main player", "main player rule|defence"]]
    .map(([lab, rule, k]) => [lab, rule, `${sh(rp(k, 0)[0])}\n[${pv(rp(k, 0)[1])}]`, `${sh(rp(k, 1)[0])}\n[${pv(rp(k, 1)[1])}]`]),
  [3200, 1500, 2250, 2250], [2, 3]));
add(CAPTION(`The regression of Section 1 on ${comma(N.replication_n)} two-team trades from June 10, 2022 to March 13, 2026; share of the 2025-26 cap [two-sided p-value].`));
add(H2("Other characteristics"));
const sig = (t) => t[2] < 0.05;
const classify = (rows, rule) => {
  const g = { td: [], gv: [], none: [] };
  rows.forEach(([lab, col]) => { const x = R[rule][col];
    if (sig(x[O[0]]) && sig(x[O[1]])) throw new Error(`${col} meets the finding rule: rewrite`);
    if (sig(x[O[0]])) g.td.push(lab); else if (sig(x[O[1]])) throw new Error(`${col} significant in realized NPV alone: add a sentence`);
    else if (sig(x[O[2]])) g.gv.push(lab); else g.none.push(lab); });
  return g; };
const lc = (s_) => s_.charAt(0).toLowerCase() + s_.slice(1);
const listAnd = (xs) => (xs.length < 3 ? xs.join(" and ") : `${xs.slice(0, -1).join(", ")}, and ${xs[xs.length - 1]}`);
const OCLR = [["A goaltender", "goalie"], ["A former top-15 pick", "top15"], ["A player aged 32 or over", "age32"], ["A player with two seasons left", "left2"], ["A player with three or more seasons left", "left3"],
  ["Recent production", "trailing_war"], ["Production above the forecast", "rep_gap"], ["The games share", "gp_share_last"]];
const OCL = classify(OCLR, MR);
OCLR.forEach(([lab, col]) => { const x = R[MR][col][O[0]]; if (x[2] < 0.05 && x[0] > 0) throw new Error(`${col}: a positive trade-day coefficient; the "paid more" sentence is wrong`); });
add(P(`${T("other")} gives the other characteristics of the player received, under the main player rule. None is a finding. ${listAnd(OCL.td.map((x, i) => (i ? lc(x) : x)))} ${OCL.td.length > 1 ? "are" : "is"} statistically significant on trade day but not in realized NPV: clubs paid more than the models' value for ${OCL.td.length > 1 ? "them" : "it"}, and the outcomes do not show the price to have been wrong. ${listAnd(OCL.gv.map((x, i) => (i ? lc(x) : x)))} ${OCL.gv.length > 1 ? "are" : "is"} statistically significant on Game Value alone, and ${listAnd(OCL.none.map(lc))} in none of the three measures.`));
add(TT("other", "Other characteristics of the player received, main player rule"));
const OROW = [["A goaltender", "goalie"], ["A former top-15 pick", "top15"], ["A player aged 32 or over", "age32"], ["A player with two seasons left", "left2"], ["A player with three or more seasons left", "left3"],
  ["Recent production, each WAR a season", "trailing_war"], ["Production above the forecast, each WAR", "rep_gap"], ["Games share in the most recent season, all against none", "gp_share_last"]];
add(TABLE(["Club received", "Trade-day xNPV", "Realized NPV, WAR", "Realized NPV, Game Value"],
  OROW.map(([lab, col]) => [lab, ...O.slice(0, 3).map((o) => cc(R[MR][col][o]))]), [3800, 1950, 1950, 1950], [1, 2, 3]));
add(CAPTION(`As ${T("find")}. Recent production is WAR weighted 50/30/20 over the three most recent seasons. The any player rule gives the same conclusions (Table A2).`));
add(H2("The former top-10 pick, an exploratory result"));
const t10 = (rule, w, o) => T10[rule][w][O[o]];
add(P(`A former top-15 pick comes close to a finding: it is statistically significant on trade day and not in realized NPV (p = ${f3(r_(MR, "top15", 1)[2])}). A narrower group was then tried, a former top-10 pick in place of the top-15. This was tested only because the top-15 fell short, so it is a search among specifications, and it is reported as exploratory rather than as a finding. In the 2017-22 trades it meets the finding rule under both rules (${T("top10")}): a club that received a former top-10 pick came out ${sh(-t10(MR, "2017-22", 0)[0])} of the cap behind on trade day and ${sh(-t10(MR, "2017-22", 1)[0])} in realized NPV under the main player rule. It is not statistically significant on Game Value (p = ${f3(t10(MR, "2017-22", 2)[2])} under the main player rule and ${f3(t10(AR, "2017-22", 2)[2])} under the any player rule). In the trades after March 2022 it has the same sign at about half the size, statistically significant in realized NPV but not on trade day, the firmer measure for those trades.`));
add(TT("top10", "A former top-10 pick in place of the former top-15 pick"));
add(TABLE(["Trades", "Rule", "Trade-day xNPV", "Realized NPV, WAR", "Realized NPV, Game Value"],
  [["July 2017 to March 2022", MR, "2017-22"], ["", AR, "2017-22"], ["June 2022 to March 2026", MR, "after 2022"], ["", AR, "after 2022"]]
    .map(([lab, rule, w]) => [lab, rule === MR ? "Main player" : "Any player", ...O.slice(0, 3).map((o, i) => cc(T10[rule][w][O[i]]))]),
  [2400, 1300, 1950, 1950, 1950], [2, 3, 4]));
add(CAPTION(`The regression of Section 1 with a former top-10 pick in place of the former top-15 pick, every other term unchanged; ${comma(N.reg_n)} and ${comma(N.top10_n_after)} two-team trades. As ${T("find")}.`));
add(H2("Types of trade"));
const TCL = classify([["Selling a player for just picks and prospects", "t_futures"], ["Buying at the deadline", "t_deadline_buyer"], ["Buying earlier in the season", "t_other_buyer"], ["Receiving a rental", "t_rental"], ["Retaining salary", "m_retained"],
  ["Receiving one asset for two or more", "t_single"], ["Being paid to take on a contract to clear cap", "t_dump"], ["A new general manager selling his predecessor's contract", "t_newgm"], ["Receiving a restricted free agent in his final contract season", "m_rfa"], ["Receiving only picks in rounds 6 and 7", "t_late"]], MR);
add(P(`${T("types")} gives the characteristics of the trade itself. None is a finding. ${listAnd(TCL.td.map((x, i) => (i ? lc(x) : x)))} ${TCL.td.length > 1 ? "are" : "is"} statistically significant on trade day alone: a price clubs agreed to that the outcomes do not show to have been wrong. Being paid to take on a contract is the cap dump of Section 4.`));
add(TT("types", "Types of trade, main player rule"));
const TROW = [["Sold a player for just picks and prospects", "t_futures"], ["Higher in the standings, 14 days before the deadline", "t_deadline_buyer"], ["Higher in the standings, earlier in the season", "t_other_buyer"],
  ["Received a rental", "t_rental"], ["Retained salary", "m_retained"], ["Received one asset for two or more", "t_single"], ["Was paid to take on a contract to clear cap", "t_dump"],
  ["A new general manager sold his predecessor's contract", "t_newgm"], ["Received a restricted free agent in his final contract season", "m_rfa"], ["Received only picks in rounds 6 and 7", "t_late"]];
add(TABLE(["The club", "Trade-day xNPV", "Realized NPV, WAR"], TROW.map(([lab, col]) => [lab, ...O.slice(0, 2).map((o) => cc(R[MR][col][o]))]), [4800, 2400, 2400], [1, 2]));
add(CAPTION(`As ${T("find")}.`));
add(H2("No change over time"));
const TR = N.trend;
add(P(`The gap between what clubs paid and the models' value did not change over the period. From 2017-18 to 2021-22 the size of the clubs' trade-day xNPV changed by ${sh(TR["trade-day grade"][0], 3)} of the cap a season (standard error ${fx(TR["trade-day grade"][1] * K25, 3)}, p = ${f3(TR["trade-day grade"][2])}), and that of their realized NPV by ${sh(TR["realized value, WAR"][0], 3)} (standard error ${fx(TR["realized value, WAR"][1] * K25, 3)}, p = ${f3(TR["realized value, WAR"][2])}). Neither is statistically significant, which does not show that pricing was stable, only that no change was detected.`));

// =====================================================================================================================
// 4. CLUBS PRICE ONLY ABOUT 40% OF A CONTRACT'S VALUE
// =====================================================================================================================
add(H1("4. Clubs Price Only About 40% of a Contract's Value"));
add(P(`A contract has two parts: the value of the player's forecasted performance over the rest of team control, and the present value of his cap hit over the seasons of his contract. A club acquiring a player should pay for the first and be paid for the second. The price a club paid for its main player is the xNPV of everything it gave up less the xNPV of everything else it received. That price is regressed on the two parts:`));
add(EQ([SUB("price", "i"), " = a + b × ", SUB("performance value", "i"), " + c × ", SUB("cap cost", "i"), " + ", SUB("ε", "i")]));
add(P(`In a market that priced contracts fully, b would be 1 and c would be −1: a club would pay $1 more for each $1 of performance value and $1 less for each $1 of cap cost. This section uses every trade to March 2026, ${comma(S4.forecast.n)} clubs, since it needs only the price paid on trade day, with standard errors clustered by trade.`));
add(P(`The performance value is the models' estimate, and an estimate contains error. Clubs do not price that error, so regressing the price on the estimate pulls the slope toward zero and makes the market look less responsive than it is. Two-stage least squares separates the models' error from the market's response. In the first stage, the models' performance value is regressed on what the contract delivered in the seasons played through 2025-26, which keeps only the part of the forecast that on-ice performance bore out. In the second stage, the price is regressed on that part of the forecast and on the cap cost. If the models' error were the reason for a low slope, this correction would bring it close to 1.`));
add(TT("price", "How much the price paid for a player moves with each part of his contract"));
add(TABLE(["Performance value measured by", "Per $1 of performance value", "Per $1 of cap cost"],
  [["The models' forecast on trade day", S4.forecast], ["What the contract delivered in the seasons played", S4.played], ["The forecast, corrected for its error (two-stage least squares)", S4.iv]]
    .map(([lab, s]) => [lab, `${sg(s.perf[0])} (${f2(s.perf[1])})\n[${pv(s.perf[2])}]`, `${sg(s.cost[0])} (${f2(s.cost[1])})\n[${pv(s.cost[2] === null ? 2 * (1 - 0.5 * (1 + erf(Math.abs(s.cost[0] / s.cost[1]) / Math.SQRT2))) : s.cost[2])}]`]),
  [4600, 2500, 2500], [1, 2]));
add(CAPTION(`${comma(S4.forecast.n)} clubs, every trade from July 2017 to March 2026; coefficient (standard error, clustered by trade) [two-sided p-value]. The first stage of the two-stage fit has a coefficient of ${f2(S4.iv.first[0])} (t = ${fx(S4.iv.first[1], 1)}); the full fits are in Table A3.`));
add(P(`Corrected for the models' error, the slope rises only to ${f2(S4.iv.perf[0])}, and its 95% interval (${f2(S4.iv.perf_ci[0])} to ${f2(S4.iv.perf_ci[1])}) excludes 1: clubs pay about 40 cents for each dollar of a contract's performance value, and are paid about ${Math.round(-100 * S4.iv.cost[0])} cents for each dollar of its cap cost. A contract worth 1% of the cap more than another commands about 0.4% of the cap more in return.`));
add(H2("Clubs selling players for picks and prospects"));
const SE_ = N.sellers, SCH = N.sellers_cap_held;
add(P(`This is why clubs that sold a player for just picks and prospects came out ahead. In the 2017-22 trades their trade-day xNPV averaged ${shc(SE_.priced[0])} (standard error ${f2(SE_.priced[1] * K25)}) and their realized NPV ${shc(SE_.outcome[0])} (${f2(SE_.outcome[1] * K25)}). With the cap hit of the player sold held constant, the gain is gone: ${sh(SCH.net_M[0])} on trade day (${pq(SCH.net_M[2])}) and ${sh(SCH.out_net_M[0])} in realized NPV (${pq(SCH.out_net_M[2])}). The gain came from shedding the contract, which the buyer did not discount enough, and not from taking picks and prospects.`));
add(H2("Cap dumps"));
const CS_ = N.cap_space_price, DU = N.dumps;
add(P(`Cap dumps follow the same pattern. In ${CS_[0]} trades from 2017-22, a club sent a player with a cap hit of $2.5 million or more along with a pick or prospect and took back no player with a cap hit of $1 million or more. The club clearing the cap attached picks and prospects worth ${pct(CS_[1])} of the cap space it cleared (95% interval ${pct(CS_[2])} to ${pct(CS_[3])}), and the club taking the contract came out behind in realized NPV, by ${shc(-DU.outcome[0])} on average ${ci(DU.outcome[2], DU.outcome[3])}.`));

// =====================================================================================================================
// 5. DISCUSSION
// =====================================================================================================================
add(H1("5. Discussion"));
add(H2("Taking on a contract can still be the right move"));
add(P(`A club paid to take on a contract came out behind, but the transaction can still be rational. A club must spend to the salary cap floor, and cap space left unused buys nothing. Being paid to take on money, when the alternative is not to spend that cap space at all, is still a gain. What the result shows is that such clubs extract less than they could. Negotiating position may explain it: a club that would otherwise leave cap space unused has less leverage, because its alternative is not a deal with another club but spending nothing, or because the CBA requires it to spend the money.`));
add(H2("What the findings have in common"));
add(P(`One reading connects the three findings: in each, clubs paid for something the models' forecast does not price. For a player with a clause it may be the reputation he has built; for a player aged 28 to 31, a record from his best seasons that clubs may not tell will last; for a defenceman, his position. In each case the outcomes side with the models. These are readings of the results, not tests of them: the data do not separate reputation, age, or position from what a club knows about a player that the models do not.`));
add(P(`Defencemen may be priced higher because good ones are scarcer. A team dresses six defencemen and twelve forwards, so a club short of a top-four defenceman has fewer places to find one. In WAR a defenceman's win counts the same as a forward's; the price line already prices a defenceman's forecasted win above a forward's, and clubs paid more still.`));
add(H2("What is not mispriced"));
add(P(`Most characteristics and most types of trade are not findings: rentals, deadline buying, retained salary, restricted free agents, late picks, and a new general manager selling his predecessor's contracts. Nor did any type of trade turn out better or worse than its price predicted: comparing each club's realized NPV with what its trade-day xNPV predicted, across ${N.groups_n} groups, under both rules and on both WAR and Game Value, the smallest p-value is ${f3(N.smallest_c_p)}. A result that is not statistically significant is not evidence that the market prices that kind of trade correctly; it means only that these trades do not show that it does not.`));

// =====================================================================================================================
// 6. LIMITATIONS
// =====================================================================================================================
add(H1("6. Limitations"));
add(BULLET(`Realized NPV is partly forecasted. Seasons from 2026-27 on are re-valued by the models, ${pct(N.revalued_share)} of the size of realized NPV in the regressions, mostly picks and prospects who have not yet reached the NHL and contracts that run past 2025-26. The seasons-played check removes them.`));
add(BULLET("Regular-season performance only. A rental's value to a contender in the playoffs is outside the currency."));
add(BULLET("One price of a win for both values. Trade-day xNPV and realized NPV convert wins on the same price line. Game Value replaces the measure of performance, not the price."));
add(BULLET(`Game Value is weaker on defence. It correlates with the models' forecast at r = ${f3(N.gv_r.F)} for forwards and ${f3(N.gv_r.D)} for defencemen, so the Game Value check is weaker for the defenceman finding.`));
add(BULLET("Traded assets only. Only trades that were made are observed, and a club knows things about its own players that the models do not. A characteristic clubs misprice may be one on which they trade only when they know more."));
add(BULLET("League-average value. Each asset is valued at the league's price, not at what it is worth to a particular club: a contender's need for a defenceman, or a rebuilding club's use for cap space, is not valued."));
add(BULLET("The cost of a clause is not measured. A no-trade or no-move clause limits where a player can be traded, and some trades may have been forced by it; neither the clause's own cost nor the trades it forced are separated from the finding."));
add(BULLET(`Conditional picks are valued as if their condition were met (${N.conditional_trades} trades).`));
add(BULLET("The former top-10 pick was found by searching among specifications after the top-15 fell short, so its p-values overstate the evidence for it."));

// =====================================================================================================================
// APPENDIX
// =====================================================================================================================
add(H1("Appendix. Full Regression Results"));
const AROW = [["Aged 28 to 31", "age28", "any_age28"], ["Aged 32 or over", "age32", "any_age32"], ["Defenceman", "defence", "any_defence"], ["Goaltender", "goalie", "any_goalie"],
  ["No-trade or no-move clause", "main_clause", "any_clause"], ["Signed as an unrestricted free agent", "ufa", "any_ufa"], ["Two seasons left", "left2", "any_left2"], ["Three or more seasons left", "left3", "any_left3"],
  ["Former top-15 draft pick", "top15", "any_top15"], ["Recent production, each WAR", "trailing_war", "avg_war"], ["Production above the forecast, each WAR", "rep_gap", "avg_gap"], ["Games share, all games against none", "gp_share_last", "avg_gs"],
  ["Sold a player for just picks and prospects", "t_futures", "t_futures"], ["Higher in the standings, 14 days before the deadline", "t_deadline_buyer", "t_deadline_buyer"], ["Higher in the standings, earlier in the season", "t_other_buyer", "t_other_buyer"],
  ["Received a rental", "t_rental", "a_rental"], ["Retained salary", "m_retained", "t_retained"], ["Received one asset for two or more", "t_single", "t_single"], ["Was paid to take on a contract to clear cap", "t_dump", "t_dump"],
  ["A new general manager sold his predecessor's contract", "t_newgm", "a_newgm"], ["Received a restricted free agent in his final contract season", "m_rfa", "a_rfa"], ["Received only picks in rounds 6 and 7", "t_late", "t_late"], ["Received a player at all", "recv", "recv"]];
for (const [key, rule, ci_] of [["A1", MR, 1], ["A2", AR, 2]]) {
  add(TT(key, `The regression of Section 1, ${rule}`));
  add(TABLE(["Difference variable", "Trade-day xNPV", "Realized NPV, WAR", "Realized NPV, Game Value", "Realized NPV, seasons played"],
    [...AROW.map((r) => [r[0], ...O.map((o) => (R[rule][r[ci_]] ? cc(R[rule][r[ci_]][o]) : "–"))]), ["Trades", ...O.map(() => comma(N.reg_n))]],
    [3200, 1600, 1600, 1600, 1600], [1, 2, 3, 4], 15));
  add(CAPTION("Share of the 2025-26 cap (robust standard error) [two-sided p-value]; no constant; one row a trade."));
}
add(TT("A3", "The price paid for the main player"));
add(TABLE(["Fit", "Performance value", "Cap cost", "Clubs"],
  [["Price on the models' forecast", S4.forecast], ["Price on what the seasons played delivered", S4.played], ["Price, two-stage least squares", S4.iv]]
    .map(([lab, s]) => [lab, `${sg(s.perf[0])} (${f2(s.perf[1])})\n[${pv(s.perf[2])}]`, `${sg(s.cost[0])} (${f2(s.cost[1])})`, comma(s.n)]),
  [4200, 1900, 1900, 1600], [1, 2, 3]));
add(CAPTION(`Coefficient (standard error, clustered by trade) [two-sided p-value]; each fit has a constant. The two-stage fit's instrument is what the contract delivered in the seasons played; its first stage has a coefficient of ${f2(S4.iv.first[0])} (t = ${fx(S4.iv.first[1], 1)}).`));

function erf(x) { const s = Math.sign(x); x = Math.abs(x); const t = 1 / (1 + 0.3275911 * x);
  return s * (1 - t * Math.exp(-x * x) * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))))); }

const doc = new Document({
  creator: "Thomas Mihaljevic", title: "Findings",
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
  console.log(`${VERSION} wrote ${OUTFILE} (${(buf.length / 1024).toFixed(0)} KB)`);
  // 2026-11-25: the banned-pattern check (25_TESTS/doc_check.py) runs on every build; the count table
  // prints here, each hit with its paragraph goes to 30_OUTPUT/doc_check/. It lists, it never edits or stops.
  const chkDir = path.join(ROOT, "30_OUTPUT", "doc_check");
  fs.mkdirSync(chkDir, { recursive: true });
  const chkOut = path.join(chkDir, path.basename(OUTFILE).replace(/\.docx$/i, ".txt"));
  const chk = require("child_process").spawnSync(process.env.PYTHON || "python",
    [path.join(__dirname, "doc_check.py"), "--quiet", "--out", chkOut, OUTFILE],
    { stdio: "inherit", env: Object.assign({}, process.env, { PYTHONIOENCODING: "utf-8" }) });
  if (chk.error || chk.status !== 0) console.log(`doc_check did not run: ${chk.error ? chk.error.message : "exit " + chk.status}`);
});
