// prospect_model_doc.js v2.6 -- builds "Valuing Prospects.docx" (40_DOCS/Supervisor_Drafts/).
//
// v2.6 (2026-10-21, session 2026-10-21; Thomas: "ensure it is still describing the model as it is written"): on the
// model after 2026-10-20 (prospect_values.py v1.11: fit rows inside club control; the pick curve and contract fixes of
// 2026-10-18 to 2026-10-20). Three sentences now follow the numbers instead of asserting a verdict: linear production's
// significance against draft position alone (p = 0.053 today, 0.025 at v2.5), and draft position from D+5 (no longer
// negative: +$0.07M, p = 0.944) in the text and Table 6's note. The fit rows are said to be inside club control; the
// deceased draftees' effect is dated (measured 2026-10-16). No wording of Thomas's changed otherwise.
// v2.5 (2026-10-16, session 2026-10-16b): no intercept and no draft-year terms in the pick curve and the prospect
// model (Thomas); Section 1's method, its equation and Table 6's note say so; Table 1's note re-measured.
// v2.4 (2026-10-16, session 2026-10-16b): Thomas's 14 concision edits (13 as proposed, the D+5 paragraph after
// Table 9 cut entirely), his two comments on Section 1 (the star value in his words; the draft-year effects and
// the regression equation shown), his Oxford comma.
// v2.3 (2026-10-16, session 2026-10-16b): Table 6's note corrected (draft position is significant, negative, from D+5
// on); "rule" -> "alternative" in Figure 2's title, Table 3's title, header and caption (Thomas: "go with alternatives").
// v2.2 (2026-10-16, session 2026-10-16): Thomas's 10 notes on v2.1's document and his own edits carried over (the date
// line, the call-up sentence, the Table 1 pointer and the leave-one-draft-out figures cut; the production intro in his
// words; "Bacon," out of the citation and the SHL example cut; "which makes no logical sense"; the D+1 age range cut).
// The regression IS the full set of interaction terms (prospect_values.py v1.8, numbers.json v2.2: one stacked
// regression, errors clustered by player); Section 1's method in his phrasing ("I regressed ..."); the simpler fade
// rules called tested and rejected; ties in bold; "statistically significant" for "reliable"; the D+5-and-later terms
// tested jointly; Table 8's baseline named as the Section 2 model.
// v2.1 (2026-10-15, session 2026-10-15c): Thomas's 13 notes on v2.0's document, and his two edits carried over (the
// deceased-draftee paragraph shortened; "The measure." label dropped). "Draft position" for "slot" throughout; "NHLe"
// after it is introduced; "root mean squared error"; the production forms named by their terms (linear production;
// linear and squared production; production squared alone), never "the curve"; the season fits presented as one
// regression with a full set of interaction terms; age reported as his age on September 15 of the valuation season
// (option A: the same values, numbers.json v2.1 refits it), and the age wording says he scored it at that age; the
// age-centring argument cut from the squared-alone paragraph; arrival figure as shares of all picks; the star value
// figure as three panels; the no-record counts by season (2007 holds only 17 of D+1's 88, so its short record stays
// with the uncertainty sentence).
// v2.0 (2026-10-15, session 2026-10-15b): THE SOURCE OF THE .docx AGAIN. Rebuilt from Thomas's own edited Word file (his
// wording is carried over where nothing changed) with his 20 notes applied, the decisions of that session (age fully
// adopted with no age-removed version; age centred at 18; production squared not divided by 10; the full curve kept;
// drafted players who died before reaching the NHL left out of every fit and listed), and the tests the notes called for
// (nhl_arrival_timing.py, prospect_fade_rules.py, prospect_curve_vs_line.py, prospect_production_form.py,
// prospect_age_correlation.py). Reader-facing: names no reader. The v1.x builder and the hand-edited file are in git.
//
// NUMBERS: every computed figure comes from OUTPUT_DIR/prospect_doc/numbers.json (prospect_doc_figures.py v2.0, on
// prospect_values.py v1.7 and the tests above). Recorded figures copied from the records, each with its source:
//   post-season trades on the next page: 23 prospects, -$3.51M          25_TESTS/next_page_moves.py (session 2026-10-14)
//   NHLe method                                                         hockeystats.com/draft/guide (read 2026-10-15)
//
// Run:  NODE_PATH=<folder with docx> node 25_TESTS/prospect_model_doc.js   (LINT_OUT=<file.md> writes the prose)

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType, HeadingLevel,
  BorderStyle, ShadingType, Footer, PageNumber, Math: OMath, MathRun, MathSuperScript,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const FIG = path.join(ROOT, "30_OUTPUT", "prospect_doc");
const N = JSON.parse(fs.readFileSync(path.join(FIG, "numbers.json"), "utf8"));
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
const pfmt = (p) => (p === null || Number.isNaN(p) ? "–" : (p < 0.001 ? "<0.001" : f3(p)));   // v2.5: "–" when there is no p-value
const pone = (p) => (p < 0.0005 ? "<0.001" : (p < 0.01 ? f4(p) : f3(p)));
const pq = (p) => (p < 0.0005 ? "p < 0.001" : `p = ${p < 0.01 ? f4(p) : f3(p)}`);   // a p-value in prose
const z3 = (x, d = 3) => (Math.abs(x) < 0.5 * 10 ** -d ? (0).toFixed(d) : Number(x).toFixed(d));
const pct = (x) => `${x > 0 ? "+" : ""}${f2(x)}%`;
const coefCell = (t, d = 3) => (t ? `${z3(t.b, d)} (${Number(t.se).toFixed(d)}) [${pfmt(t.p)}]` : "-");

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
const FORMULA = (text) => { TEXT.push(text); return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 140 }, children: [new TextRun({ text, font: FONT, italics: true, size: 23 })] }); };
const CAPTION = (text) => { TEXT.push(text); return new Paragraph({ spacing: { before: 40, after: 220 }, children: runs(text, { size: 18, color: "52514E" }) }); };
const TITLE = (text) => new Paragraph({ spacing: { before: 180, after: 60 }, keepNext: true, children: runs(text, { size: 20, bold: true }) });
const BULLET = (text) => { TEXT.push(`- ${text}`); return new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: runs(text), spacing: { before: 20, after: 60, line: 276 } }); };

// Word equations: a list of pieces, each a string (an ordinary run) or ["P", "2"] (a superscript)
function EQ(label, pieces) {
  const kids = pieces.map((x) => (Array.isArray(x)
    ? new MathSuperScript({ children: [new MathRun(x[0])], superScript: [new MathRun(x[1])] })
    : new MathRun(x)));
  TEXT.push(`${label}: ${pieces.map((x) => (Array.isArray(x) ? `${x[0]}^${x[1]}` : x)).join("")}`);
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 100 },
    children: [...(label ? [new TextRun({ text: `${label}:   `, font: FONT, italics: true })] : []), new OMath({ children: kids })] });
}

function FIGURE(file, title, caption, width = 540) {
  const b = fs.readFileSync(path.join(FIG, file));
  const w = b.readUInt32BE(16), h = b.readUInt32BE(20);
  return [TITLE(title), new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true,
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
  return new Table({ width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: header.map((t, i) => cell(t, i, -1, true, true)) }),
      ...rows.map((r, j) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, i, j, false, j < rows.length - 1)) }))] });
}
// the best (lowest) number in each listed column, as bold keys; v2.2: compared at the precision shown (dp[c], default
// 4 decimals), and every row that ties the best at that precision is bold (Thomas: "If there are ties ... bold each")
function bestKeys(values, cols, dp = {}) {
  const keys = new Set();
  cols.forEach((c) => {
    const d = dp[c] === undefined ? 4 : dp[c];
    const shown = values.map((r) => (r[c] === null || r[c] === undefined ? null : Number(Number(r[c]).toFixed(d))));
    const ok = shown.filter((x) => x !== null);
    if (!ok.length) return;
    const best = Math.min(...ok);
    shown.forEach((x, j) => { if (x === best) keys.add(`${j},${c}`); });
  });
  return keys;
}

// ---- numbers ---------------------------------------------------------------------------------------------
const S1 = N.step1, PS = N.p_star, TR = N.traded, ALT = N.alt_totals, W = N.worked, FS = N.fade_scores;
const k = (g) => S1.find((r) => r.k === g);
const PA = Object.fromEntries(N.prod_arms.map((a) => [a.arm, a]));
const AA = Object.fromEntries(N.age_arms.map((a) => [a.arm, a]));
const FA = N.forms["all drafts"], F07 = N.forms["2007 out"];
const AD = Object.fromEntries(N.adopted.map((t) => [t.k, t]));
const B = N.build;
const PC = (g, arm) => N.prod_coefs.find((r) => r.k_group === g && r.arm === arm);
const AC = (g, arm) => N.age_coefs.find((r) => r.k_group === g && r.arm === arm);
const ARR = N.arrival;
// the share of ALL the group's players who had reached the NHL by season D+upto, in percent
const cum = (grp, upto) => { let s = 0; for (let i = 1; i <= upto; i++) s += ARR[grp].share_all[`D+${i}`] || 0; return 100 * s; };
const G = ["0", "1", "2", "3", "4+"];
const SEAS = { "0": "D+1", "1": "D+2", "2": "D+3", "3": "D+4", "4+": "D+5 and later" };
const pctVs = (x, base) => 100 * (x / base - 1);
const goalieTot = TR.tot_main - N.forms_traded.curved.drafted;
const sqTot = N.forms_traded["squared alone"].drafted + goalieTot;
const TEAMS = { "Alexei Cherepanov": "New York Rangers", "Mickey Renaud": "Calgary Flames", "Bryan Rufenach": "Detroit Red Wings",
  "Scott Winkler": "Dallas Stars", "Kristians Pelss": "Edmonton Oilers", "Daniil Sobchenko": "San Jose Sharks" };
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const longDate = (s) => { const [y, m, d] = s.split("-").map(Number); return `${MONTHS[m - 1]} ${d}, ${y}`; };

const kids = [];
const add = (...xs) => xs.flat().forEach((x) => kids.push(x));
add(new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: "Valuing Prospects", bold: true, size: 40, font: FONT })] }));

// ---- opening ----------------------------------------------------------------------------------------------
add(P("A prospect is a player the player model does not yet value. For a skater, that is a player with no NHL season of 10 or more games in the three seasons before the valuation date. For a goaltender, it is a player with no NHL game in the six seasons before it. The goaltender forecast uses any NHL season in the three before and looks back three more when the last is missing."));
add(P("A prospect is valued in the same currency as a draft pick and a contract: the surplus of his remaining NHL seasons until his club's control ends. Control ends when he becomes an unrestricted free agent under the collective agreement, at 27 or after seven seasons on an NHL roster. Each season counts the market price of the wins he delivers, less what the club pays to keep him. That cost is the entry-level salary, then the qualifying offer, or the arbitration price once he is eligible. A season outside the NHL counts as zero."));
add(P(`The model learns from ${comma(k("0").players)} of the ${comma(k("0").players + N.excluded.length)} players drafted from 2007 to 2017 whose careers are long enough to observe. Seasons are named from the draft: D0 is the draft season, which ends with the draft, and D+1 is the season after it, and so on. The outcome is each player's remaining surplus, measured in each season from D+1 on in which he was still a prospect and his club still controlled him. Remaining surplus is the surplus he went on to deliver from that season to the end of his club's control. A prospect traded between the draft and the start of D+1 is valued as in D+1.`));
add(P(`Six drafted players of 2007 to 2017 died before reaching the NHL, while their clubs still controlled them (Table 1). They are left out of every fit in this document and of the draft pick curve. Left in, each would count as a prospect with zero surplus in each season after his death.`));
add(TITLE("Table 1. Drafted players left out of every fit"));
add(TABLE(["Player", "Drafted", "Club", "Died"],
  N.excluded.map((e) => [e.name, `${e.draft}, #${e.pick}`, TEAMS[e.name], longDate(e.died)]),
  [2600, 1500, 2600, 2400], []));
add(CAPTION("Drafted players of 2007 to 2017 who never played an NHL season and died before their club's control would have ended, from Wikipedia's list of ice hockey players who died during their careers, each matched to the draft records by draft year and overall pick. Leaving them out moved the star value at the draft from $18.03 million to $18.04 million when it was measured (October 16, 2026)."));

// ---- 1. draft position -------------------------------------------------------------------------------------------
add(H1("1. Draft Position and How Its Value Fades"));
add(P("At the draft, a pick is worth its draft position's star probability times the star value. A prospect starts with his pick's value. The question is how that value changes while he remains unproven."));
const A10 = ARR["picks 1-10"], A37 = ARR["rounds 3-7"], AALL = ARR["all drafted players"];
add(P(`The answer depends on when drafted players reach the NHL. Of the ${comma(AALL.n)} drafted players, ${comma(AALL.n_arrived)} (${f1(100 * AALL.n_arrived / AALL.n)}%) played an NHL season of 10 or more games (a goaltender, an NHL game) before their club's control ended; the other ${comma(AALL.n - AALL.n_arrived)} never did. How many arrive, and when, depends on where they were drafted (Figure 1). Of the ${A10.n} top-ten picks, ${f1(cum("picks 1-10", 1))}% had reached the NHL by D+1, ${f1(cum("picks 1-10", 2))}% by D+2 and ${f1(cum("picks 1-10", 3))}% by D+3, and ${A10.n_arrived} reached it in the end. Of the ${comma(A37.n)} picks from rounds 3 to 7, ${f1(cum("rounds 3-7", 3))}% had reached it by D+3 and ${f1(cum("rounds 3-7", 4))}% by D+4, and only ${f1(100 * A37.n_arrived / A37.n)}% ever did. A top pick who is still a prospect in D+4 is therefore unusual, and later picks who reach the NHL at all reach it later.`));
add(FIGURE("fig_arrival.png", "Figure 1. When drafted players reach the NHL",
  `Drafted players of 2007 to 2017, without the six in Table 1. Each line is the share of a draft group's players who had reached the NHL by each season; the rest of the group, the gap above the line at D+9, never did. Reaching the NHL means a first NHL season of 10 or more games (for a goaltender, a first NHL game), the point at which the player model takes him; only seasons within club control are seen. Every draft is observed through at least D+9.`));
add(P("To measure how the value of draft position changes, I regressed each prospect's remaining surplus on the star probability for his draft position, interacted with an indicator for each season from D+1 to D+4 and one for D+5 onwards, using every season in which a drafted player was still a prospect and still under his club's control. The coefficient for each season is that season's star value, which is what a prospect still unproven in that season would be worth if he were certain to become a star. As in the draft pick curve, the regression has no intercept, so a draft position with no star probability is worth zero."));
add(FORMULA("remaining surplus  =  star value for D+n  ×  star probability  +  error"));
add(P("A prospect still unproven in season D+n is therefore valued as:"));
add(FORMULA("value in season D+n  =  star probability for his draft position  ×  star value for season D+n"));
add(P(`For example, a #10 pick (star probability ${f1(100 * PS["10"])}%) who is still a prospect in D+3 is worth ${f3(PS["10"])} × ${mil(k("2").star)} = ${mil(PS["10"] * k("2").star)}.`));
add(TITLE("Table 2. The star value for a player still a prospect, by season"));
add(TABLE(["Season", "Prospects", "Star value (s.e.)", "p-value", "#1 pick", "#10 pick", "#32 pick", "Top-10 picks still prospects"],
  S1.map((r) => [r.k === "0" ? "D+1 (from the draft)" : SEAS[r.k], r.k === "4+" ? `${comma(r.players)} (${comma(r.rows)} prospect-seasons)` : comma(r.players),
    `${money(r.star)} (${f2(r.se)})`, pfmt(r.p), money(r.pick1), money(r.pick10), money(r.pick32), comma(r.top10)]),
  [1500, 1500, 1300, 800, 900, 900, 900, 1000], [1, 2, 3, 4, 5, 6, 7]));
add(CAPTION(`Drafted players 2007-2017 still prospects in each season (D+1 is the season after the draft). Star value in millions of dollars at the 2025-26 cap; standard errors clustered by player, since one player appears in several seasons; two-sided p-values. The pick columns multiply the star value by Bacon's star probability (${f1(100 * PS["1"])}%, ${f1(100 * PS["10"])}% and ${f1(100 * PS["32"])}%).`));
add(P(`A prospect keeps most of his draft position's value through D+3 (${mil(k("1").star)} in D+2 and ${mil(k("2").star)} in D+3) and loses most of it over the next two seasons (${mil(k("3").star)} in D+4 and ${mil(k("4+").star)} from D+5 on). Each estimate is statistically significant at the ${Math.max(...S1.map((r) => r.p)) < 0.01 ? "1%" : "5%"} level; the largest p-value is ${f3(k("4+").p)}, from D+5 on. The value falls sharply after D+3 because of who is left. By D+4, nearly each top pick who will reach the NHL has done so, so the prospects still unproven are mostly later picks and the top picks who missed: of the 110 top-ten picks of 2007-2017, ${k("2").top10} were still prospects in D+3 and ${k("3").top10} in D+4. Among the prospects left, draft position no longer separates the players who will succeed from those who will not.`));

add(H2("Decision: a full set of interaction terms"));
add(P("The adopted regression gives each season its own star value from D+1 to D+4, and one shared value from D+5 on, where few prospects remain and little value is left. Three simpler alternatives were tested and rejected. Each restricts how the star value may change from one season to the next, and each was fitted on the same prospect-seasons and scored the same way (Figure 2, Table 3):"));
add(BULLET(`One value for every season, the draft-day value kept for as long as a player remains a prospect (fitted: ${mil(N.fade_curve["no fade"][0])}).`));
add(BULLET(`A straight-line decline: the star value equals a starting value plus a fixed change for each season since the draft. This is one regression with a single interaction term, star probability × seasons since the draft. Fitted: ${mil(N.fade_curve["straight line"][0])} in D+1, falling ${mil(N.fade_curve["straight line"][0] - N.fade_curve["straight line"][1])} a season.`));
add(BULLET(`The same percentage decline each season: the value keeps a fixed share of itself each season. Fitted: ${mil(N.fade_curve["same percentage"][0])} in D+1, keeping ${f1(100 * N.fade_curve["same percentage"][1] / N.fade_curve["same percentage"][0])}% each season.`));
add(FIGURE("fig_star_value.png", "Figure 2. The star value by season, and three rejected alternatives",
  "Orange: each rejected alternative, fitted on the same prospect-seasons. Blue: the adopted star values (Table 2) with 95% intervals; from D+5 on, one shared value drawn as a line with its interval as a band. Millions of dollars at the 2025-26 cap."));
const fadeRows = [["A separate value for each season (adopted: a full set of interaction terms)", "separate"], ["One value for every season", "no fade"],
  ["Straight-line decline (one interaction term)", "straight line"], ["Same percentage decline each season", "same percentage"]];
add(TITLE("Table 3. Each alternative for the star value against the adopted one"));
add(TABLE(["Alternative", "Held-out error ($M)", "One-sided p", "Star value, D+5 ($M)", "197 traded prospects, draft position alone ($M)", "Values below zero"],
  fadeRows.map(([lab, r]) => [lab, f4(FS[r].rmse), FS[r].p === null ? "-" : pone(FS[r].p), f2(N.fade_curve[r][4]), f2(FS[r].total), comma(FS[r].below_zero)]),
  [2900, 1300, 1100, 1200, 1700, 1000], [1, 2, 3, 4, 5], bestKeys(fadeRows.map(([, r]) => [null, FS[r].rmse]), [1])));
add(CAPTION(`Held-out error: each draft is predicted from a fit without it, and the error is the root mean squared error in millions of dollars of remaining surplus per prospect-season, over ${comma(N.fade_rows)} prospect-seasons; lower is better, and the lowest is in bold. One-sided p: the 11 drafts are redrawn with replacement 2,000 times, and p is the share of redraws in which the adopted model's total squared error is not lower than the alternative's. It is one-sided because the question is directional: is the adopted model better?`));
add(P(`One value for every season predicts worse than a separate value for each season (${pq(FS["no fade"].p)}). The straight-line and same-percentage declines predict about as well (p = ${f3(FS["straight line"].p)} and ${f3(FS["same percentage"].p)}), so the choice does not rest on prediction. I chose a separate value for each season for two reasons. First, it imposes no shape on the decline, and the estimates hold through D+3 and then fall, which matches when top picks reach the NHL (Figure 1). Second, the straight-line decline keeps falling past zero: from D+8 it values a top pick below a late pick, and it values ${FS["straight line"].below_zero} of the 197 traded prospects below zero.`));
add(H2("Decision: the overlap with the fit is a stated limitation"));
add(P(`A prospect drafted from 2007 to 2017 is valued from a fit that contains his own outcome. Refitting without each prospect's own draft as the main value was rejected for two reasons. It would take eleven fits for each season, and the prospect values would no longer use the same star value as the draft picks traded beside them.`));

// ---- 2. production ------------------------------------------------------------------------------------------
add(H1("2. Production Adjusted to NHL Terms"));
add(P("Draft position is one element of what predicts a prospect's value. A prospect's own scoring helps as well, because a player who scores at a high rate in junior, college, or a European league is more likely to reach the NHL and more likely to contribute when he does. Like the player model, when calculating a player's current production level, the model takes a weighted average of his previous three seasons. For example, a prospect valued in D+1 is measured on his draft season (D0) and the two before it (D-1 and D-2), which is the scoring scouts saw before the draft."));
const LG = (lg) => N.leagues.find((r) => r.league === lg);
add(P(`Scoring in different leagues is put on one scale with Patrick Bacon's NHL equivalency (NHLe) factors. A league's factor is the number of NHL points that one point in that league and season is worth. Bacon estimates each factor from players who played full seasons in two leagues in consecutive years, adjusted for a year of development, and re-estimates the factors on a rolling four-season window, so a league's factor changes over time (hockeystats.com/draft/guide). Figure 3 shows the ten leagues that the 2007-2017 draftees played in most in their draft season, which together hold ${f1(100 * N.leagues_share_top10)}% of those draft seasons. For example, an OHL point was worth ${f3(LG("ohl").nhle_2006)} NHL points in 2006-07 and ${f3(LG("ohl").nhle_2025)} in 2025-26.`));
add(FIGURE("fig_nhle.png", "Figure 3. NHLe factors over time for the leagues most draftees came from",
  "Bacon's NHLe factor for each league and season (NHL points per point scored in the league). Leagues are the ten in which the most 2007-2017 draftees played their draft season, by games played; the count of draftees is in the legend. The OHL is drawn thicker. Linear axis."));
const NR = N.prod_rows.no_record_by_k;
const nrMid = NR["1"] + NR["2"] + NR["3"];
add(P(`A season's production is the player's points, sourced from Elite Prospects, times his league-season's NHLe factor, per 82 games, counted for seasons of 10 or more games. His production level weights his three seasons before the valuation season 50/30/20, most recent first, rescaled over the seasons he has. A prospect with no eligible season (${f1(100 * N.prod_rows.no_record_share)}% of prospect-seasons) gets an indicator for having no record, so missing data is not read as zero scoring. Almost all are in D+1 (${NR["0"]}) or from D+5 on (${NR["4+"]}); only ${nrMid} fall in D+2 to D+4, so the indicator's coefficient there rests on very few players. The median production level rises from ${f1(N.prod_median_by_k["0"])} NHLe points per 82 games in D+1 to ${f1(N.prod_median_by_k["4+"])} from D+5 on.`));
const prodRows = [["Draft position alone", "slot"], ["Linear production alone", "production"], ["Draft position + linear production", "slot+production"],
  ["Draft position + linear production, separate rate for defencemen", "slot+production by position"], ["Draft position + linear and squared production", "slot+production curved"],
  ["Linear and squared production alone", "production curved"], ["Adopted: linear and squared production; draft position in D+1 to D+3 only", "chosen"]];
const prodVals = prodRows.map(([, a]) => [null, PA[a].rmse, PA[a].pct, ...PA[a].by_k, PA[a].p === null ? null : PA[a].p]);
add(TITLE("Table 4. Held-out error of each production candidate against draft position alone"));
add(TABLE(["Candidate", "Held-out error, all seasons", "vs draft position alone", "D+1", "D+2", "D+3", "D+4", "D+5 and later", "One-sided p"],
  prodRows.map(([lab, a]) => [lab, f4(PA[a].rmse), a === "slot" ? "-" : pct(PA[a].pct), ...PA[a].by_k.map(f4), PA[a].p === null ? "-" : pone(PA[a].p)]),
  [2300, 1000, 850, 800, 800, 800, 800, 850, 800], [1, 2, 3, 4, 5, 6, 7, 8], bestKeys(prodVals, [1, 2, 3, 4, 5, 6, 7, 8], { 2: 2 })));
add(CAPTION(`Held-out error and one-sided p as in Table 3, here against draft position alone, over the ${comma(N.prod_rows.rows)} prospect-seasons of ${comma(N.prod_rows.players)} drafted skaters, 2007-2017 (goaltenders stay on draft position alone); the best in each column is in bold. The season columns are the error within each season. The error falls with the season because most prospects still unproven in D+5 or later deliver little or no NHL surplus. Compare candidates within a column.`));
add(H2("Decision: production adds to draft position"));
add(P(`Linear production alone predicts worse than draft position alone (${pct(PA.production.pct)} in held-out error; one-sided p = ${f3(PA.production.p)}), so production does not replace draft position at the draft. Added to draft position, production lowers the error in each season. ${PA["slot+production"].p < 0.05 ? `The improvement is statistically significant at the 5% level both for linear production (p = ${f3(PA["slot+production"].p)}) and for linear and squared production (p = ${f3(PA["slot+production curved"].p)}).` : `The improvement is statistically significant at the 5% level for linear and squared production (p = ${f3(PA["slot+production curved"].p)}), but not for linear production (p = ${f3(PA["slot+production"].p)}).`} Undrafted prospects, who have no draft position, use the adopted model with the star probability set to zero (Section 4).`));
add(H2("Decision: production enters with a squared term"));
add(P(`With linear production, each additional NHLe point adds the same dollars. Adding the production squared term lets each point add more the higher a prospect already scores. I added it because most of a pick's surplus comes from the few players who become stars. Draft position already captures part of this: the star probability for the first pick is ${f1(100 * PS["1"])}%, about ${Math.round(PS["1"] / PS["32"])} times the ${f1(100 * PS["32"])}% for the 32nd. But every prospect taken at the same draft position has the same star probability, whatever he scores. Linear production then gives the highest scorers at a draft position, the prospects most likely to become stars, the same dollars per point as every other prospect; the squared term lets their value rise faster.`));
const cvl = N.curve_vs_line;
add(P(`Linear and squared production has the lower held-out error in each season (Table 4) and improves on draft position alone by ${f2(-PA["slot+production curved"].pct)}%, against ${f2(-PA["slot+production"].pct)}% for linear production. Compared directly with linear production, adding the squared term is better with one-sided p = ${f3(cvl["1"].p)} with draft position in each season, and p = ${f3(cvl["3"].p)} in the adopted model with age (Table 5). The production squared term is statistically significant in each season from D+1 to D+4 of the adopted model (${Math.max(...["0", "1", "2", "3"].map((g) => AD[g].terms.nhle82_sq.p)) < 0.001 ? "p < 0.001" : `p ≤ ${f3(Math.max(...["0", "1", "2", "3"].map((g) => AD[g].terms.nhle82_sq.p)))}`}, Table 9). Most of the uncertainty comes from the 2007 draft. Elite Prospects scoring and the NHLe factors begin in 2006-07, so a 2007 draftee's D+1 production rests on his draft season alone, against up to three seasons for later drafts. Without the 2007 draft, linear and squared production beats linear production with ${pq(F07.pairs["curved vs straight"])}.`));
const formRows = [["Linear production", "straight"], ["Linear and squared production (adopted)", "curved"], ["Production squared alone", "squared alone"]];
add(TITLE("Table 5. Three forms of production in the adopted model"));
add(TABLE(["Form", "Held-out error", "D+1", "D+2", "D+3", "D+4", "D+5 and later", "vs draft position alone (p)", "Head to head (p)", "197 traded ($M)"],
  formRows.map(([lab, f]) => [lab, f4(FA.rmse[f]), ...FA.by_k[f].map(f4), pone(FA.pairs[`${f} vs slot alone`]),
    f === "straight" ? "-" : (f === "curved" ? `vs linear ${pone(FA.pairs["curved vs straight"])}` : `vs linear and squared ${f3(FA.pairs["squared alone vs curved"])}`),
    f2(f === "curved" ? TR.tot_main : N.forms_traded[f].drafted + goalieTot)]),
  [1700, 850, 750, 750, 750, 750, 850, 1000, 1300, 950], [1, 2, 3, 4, 5, 6, 7, 9],
  bestKeys(formRows.map(([, f]) => [null, FA.rmse[f], ...FA.by_k[f]]), [1, 2, 3, 4, 5, 6])));
add(CAPTION(`Each form keeps the adopted structure: draft position in D+1 to D+3, production discounted by age in D+1 to D+4 (Section 3), and the no-record indicator. Held-out error and one-sided p as in Table 4; head to head, p is the share of redraws in which the named form is not lower than the other. The last column is the total for the 197 traded drafted prospects, goaltenders on draft position alone.`));
add(P(`Production squared alone, without the linear production term, predicts about as well as the regression with both the linear and the squared production terms (held-out error ${f4(FA.rmse["squared alone"])} against ${f4(FA.rmse.curved)}; the regression with both terms is better with one-sided p = ${f3(FA.pairs["curved vs squared alone"])}, which is not statistically significant). It was not adopted because it would raise the 197 traded prospects' value from ${mil(TR.tot_main)} to ${mil(sqTot)} without predicting better.`));
add(FIGURE("fig_production.png", "Figure 4. A #20 pick in D+2: value against production, before age",
  `Value in millions of dollars at the 2025-26 cap for a #20 pick (star probability ${f1(100 * N.fig_production.p20)}%) in D+2, from each candidate's fit on all drafts, without the age term of Section 3. Production is NHLe points per 82 games, weighted 50/30/20 over the three seasons before the valuation season. Vertical lines mark the 25th, 50th, 75th and 90th percentiles of production among prospects in D+2 (${f1(N.prod_pct_k1["25"])}, ${f1(N.prod_pct_k1["50"])}, ${f1(N.prod_pct_k1["75"])} and ${f1(N.prod_pct_k1["90"])} points).`));
const cu1 = PC("1", "slot+production curved");
const st1 = PC("1", "slot+production");
const qa = cu1.nhle82_sq, qb = cu1.nhle82 - st1.nhle82, qc = (cu1.p_star - st1.p_star) * N.fig_production.p20;
const crossAt = (-qb + Math.sqrt(qb * qb - 4 * qa * qc)) / (2 * qa);
const turn1 = -cu1.nhle82 / (2 * cu1.nhle82_sq);
add(P(`Up to ${f1(crossAt)} points (above the 75th percentile), the line with the squared term sits below the linear one, by at most ${mil(N.fig_production.gap_max)}, and it dips slightly before it rises. The dip comes from the negative linear coefficient, which, with the squared term in the model, is not the value of an extra point: in D+2 an extra point adds ${f3(cu1.nhle82)} + 2 × ${f4(cu1.nhle82_sq)} × production million dollars, which is positive above ${f1(turn1)} points, below the 25th percentile of ${f1(N.prod_pct_k1["25"])}. The negative coefficient sets where the value bottoms out; it is not evidence that a little scoring lowers a prospect's value.`));
add(H2("Decision: from D+4, production replaces draft position"));
const sl = N.slot_late;
add(P(`Once production is in the model, draft position stops carrying information in D+4 (Table 6). Its coefficient is ${mil(sl["3"].b)} (standard error ${f2(sl["3"].se)}, p = ${f3(sl["3"].p)}) in D+4 and ${mil(sl["4+"].b)} (standard error ${f2(sl["4+"].se)}, p = ${f3(sl["4+"].p)}) from D+5 on. ${sl["4+"].b < 0 && sl["4+"].p < 0.05 ? "A negative weight on draft position would value a top pick below a later pick with the same production, which makes no logical sense." : "Neither is statistically significant at the 5% level: once a prospect's production is known, his draft position adds nothing to his value from D+4 on."} The adopted model keeps draft position from D+1 to D+3 and uses production alone from D+4. This drops one parameter in each later season at no cost: the held-out error is ${f4(PA.chosen.rmse)} against ${f4(PA["slot+production curved"].rmse)} with draft position kept throughout.`));
const t6terms = [["Star probability for his draft position", "p_star"], ["Production (NHLe points per 82)", "nhle82"], ["Production squared", "nhle82_sq"], ["No production record", "no_record"]];
add(TITLE("Table 6. Draft position and linear and squared production in each season, before age"));
add(TABLE(["Term", ...G.map((g) => SEAS[g])],
  [...t6terms.map(([lab, c]) => [lab, ...G.map((g) => { const r = PC(g, "slot+production curved"); const d = c === "nhle82_sq" ? 4 : 3;
    return `${Number(r[c]).toFixed(d)} (${Number(r[`${c}_se`]).toFixed(d)}) [${pfmt(erfcP(r[c], r[`${c}_se`]))}]`; })])],
  [2600, 1350, 1350, 1350, 1350, 1350], [1, 2, 3, 4, 5]));
add(CAPTION(`Dependent variable: remaining surplus in millions of dollars at the 2025-26 cap. Each cell gives the coefficient, its standard error clustered by player in parentheses and its two-sided p-value in brackets. The table is one regression with the full set of interaction terms: each column holds that season's coefficients. Draft position's coefficient is statistically significant at the 5% level from D+1 to D+3, not in D+4, and ${sl["4+"].b < 0 && sl["4+"].p < 0.05 ? "negative and statistically significant from D+5 on" : "not from D+5 on"} (the paragraph before this table). From D+5 on, neither production term is statistically significant at the 5% level on its own.`));
add(H2("Decision: one production rate for forwards and defencemen"));
add(P(`A separate production rate for defencemen was tested. It changes the held-out error by ${pct(pctVs(PA["slot+production by position"].rmse, PA["slot+production"].rmse))} against linear production with one rate, and its improvement over draft position alone is less consistent across drafts (one-sided p = ${f3(PA["slot+production by position"].p)} against ${f3(PA["slot+production"].p)}). One rate is kept.`));
add(P("With production, the model values a prospect in season D+n as follows, where S is the star probability for his draft position, P is his production level in NHLe points per 82 games, and N is 1 when he has no production record and 0 otherwise. As in Section 1, each term is multiplied by an indicator for each season (a full set of interaction terms), so the coefficients a, b, c and d take a separate value in each season: a is the value of the star probability, b and c together give the value of production, and d is the value of having no record."));
add(EQ("D+1 to D+3", ["value = a × S + b × P + c × ", ["P", "2"], " + d × N"]));
add(EQ("D+4 and later", ["value = b × P + c × ", ["P", "2"], " + d × N"]));
add(TITLE("Table 7. The production measure's settings"));
add(TABLE(["Setting", "Adopted", "Alternative", "Why"], [
  ["A counting season", "10 or more games", "Any games", "The same threshold the player model uses for an NHL season; a handful of games gives an unreliable scoring rate."],
  ["Weighting of recent seasons", "50/30/20 over the three seasons before, rescaled over those he has", "Other weights", "The weighting each part of the model uses for recent seasons."],
  ["2012-13 (no NHLe factor; lockout season)", "The mean of the league's 2011-12 and 2013-14 factors", "Leave 2012-13 out", "Keeps a full season of scoring for the 2011-2013 drafts."],
  ["Goaltenders", "Draft position alone", "A save-based measure (not tested)", "NHLe converts scoring, which says nothing about a goaltender. Elite Prospects holds goaltenders' save percentages, but no factor translates a save percentage from one league to another; a save-based measure is untested."],
  ["No production record", "An indicator, 0 or 1", "Read as zero scoring", "Missing data (an unlisted league) is not evidence of poor play."],
], [1900, 2100, 1700, 3600]));
// v2.5: with no draft-year terms the no-record coefficient is what prospects without a record went on to deliver in
// that season; from D+4 on each of them delivered nothing, so it is exactly zero there, with no p-value. The wording
// below rests on that and on D+3 holding one such prospect-season: GUARD, the build stops if either changes.
const nrP = N.adopted.map((t) => t.terms.no_record.p);
if (!(nrP[3] === null && nrP[4] === null && NR["2"] === 1 && nrP[0] >= 0.05 && nrP[1] >= 0.05)) throw new Error("no-record wording no longer matches Table 9");
add(P(`Each setting is applied identically to each candidate in Table 4. The no-record indicator gives a prospect without a record what such prospects went on to deliver in his season. It is not statistically significant at the 5% level in D+1 or D+2 (p = ${f3(nrP[0])} and ${f3(nrP[1])}, Table 9), and in D+3 it rests on a single prospect-season. From D+4 on it is exactly zero, with no p-value, because none of the ${NR["3"] + NR["4+"]} prospect-seasons without a record in those seasons delivered any surplus. It is kept so that missing data is not read as zero scoring.`));

// ---- 3. age ------------------------------------------------------------------------------------------------
add(H1("3. Age"));
add(P(`A player who scores at a given rate at 18 is commonly rated a better prospect than one who scores at the same rate at 20. This section tests whether the data agree. Age is the player's age on September 15 of the valuation season, the date the collective agreement uses. A player is first eligible for the draft in the year he is 18 by September 15, so in D+1 a player drafted at his first opportunity is 18 to 19, and one drafted a year later is 19 to 20.`));
add(P(`Within a season's regression each prospect is the same number of seasons from his draft, so a prospect a year older now also scored his points, and was drafted, a year older; age cannot be confused with time since the draft there. Across all seasons the two move almost one for one (correlation ${f3(N.age_corr.age_vs_k)}), which is why age is compared only within a season.`));
const ageRows = [["Draft position + linear and squared production, without age (Section 2)", "chosen"], ["Plus age: a flat amount per year", "+ age"],
  ["Plus age discounting production, each season", "+ age x production"], ["Plus both", "+ age and age x production"],
  ["Adopted: age discounting production, D+1 to D+4", "age x production, seasons 0-3"]];
add(TITLE("Table 8. Each age candidate against the adopted model of Section 2 (draft position + linear and squared production), on the same prospect-seasons"));
add(TABLE(["Candidate", "Held-out error", "vs Section 2 model", "vs draft position alone", "One-sided p"],
  ageRows.map(([lab, a]) => [lab, f4(AA[a].rmse), a === "chosen" ? "-" : pct(AA[a].pct), pct(AA[a].pct_vs_slot), AA[a].p === null ? "-" : pone(AA[a].p)]),
  [3700, 1300, 1700, 1300, 1300], [1, 2, 3, 4], bestKeys(ageRows.map(([, a]) => [null, AA[a].rmse, AA[a].pct, AA[a].pct_vs_slot]), [1, 2, 3], { 2: 2, 3: 2 })));
add(CAPTION(`Held-out error as in Table 4. Each candidate keeps the adopted model of Section 2 (draft position in D+1 to D+3, linear and squared production, the no-record indicator) and adds the age term shown; its one-sided p-value compares it with that model. With both terms, the comparison against the age discount alone gives p = ${f3(N.age_both_vs_discount_p)}.`));
add(H2("Decision: age discounts production"));
const d2disc = AD["1"].terms.prod_x_age.b;
add(P(`Two forms were tested. Age as a flat amount subtracts the same dollars for each year of age, whatever the player scores. Age discounting production makes each point of production worth less the older the player was when he scored it: each year of age lowers the value of each point by a fixed amount. In D+2 that amount is $${f3(-d2disc)} million (Table 9), so of two prospects with 10 points, the one who is a year older, and so scored them a year older, is worth ${mil(-10 * d2disc)} less. Both forms are statistically significant improvements (one-sided p = ${f3(AA["+ age"].p)} and ${pone(AA["+ age x production"].p)}), and the discount improves held-out error more (${pct(AA["+ age x production"].pct)} against ${pct(AA["+ age"].pct)}). I chose the discount because it is the larger gain and it measures what age was included for, which is how much a player's scoring says about him given his age. Using both terms is worse than the discount alone (${pct(AA["+ age and age x production"].pct)} against ${pct(AA["+ age x production"].pct)}; p = ${f3(N.age_both_vs_discount_p)} that it is better). The flat term also changes sign once the discount is in (Table B5), which shows the two terms measure the same thing.`));
add(P(`From D+5 on, age adds nothing (held-out error ${f4(AA["+ age x production"].by_k[4])} with the discount against ${f4(AA.chosen.by_k[4])} without), so the adopted model applies the discount from D+1 to D+4 only, where it is statistically significant in each season (p ≤ ${f3(Math.max(...N.adopted.filter((t) => t.terms.prod_x_age).map((t) => t.terms.prod_x_age.p)))}, Table 9).`));
add(FIGURE("fig_age.png", "Figure 5. A #20 pick in D+2: the age discount",
  `Value in millions of dollars at the 2025-26 cap under the adopted model for a #20 pick in D+2 with a production record, at three ages on September 15 of his D+2 season. A player drafted at his first opportunity is 19 to 20 then. Percentile lines as in Figure 4.`));
add(P("The adopted model values a prospect in season D+n as follows, where A is his age on September 15 of that season and the other symbols are as in Section 2. The coefficient e is the age discount: the change in the value of each point of production for each year of age. Age enters less 18, so the age term is zero for an 18-year-old."));
add(EQ("D+1 to D+3", ["value = a × S + b × P + c × ", ["P", "2"], " + d × N + e × P × (A − 18)"]));
add(EQ("D+4", ["value = b × P + c × ", ["P", "2"], " + d × N + e × P × (A − 18)"]));
add(EQ("D+5 and later", ["value = b × P + c × ", ["P", "2"], " + d × N"]));
const t9 = [["Star probability for his draft position (a)", "p_star", 3], ["Production (b)", "nhle82", 3], ["Production squared (c)", "nhle82_sq", 4],
  ["No production record (d)", "no_record", 3], ["Production × (age − 18) (e)", "prod_x_age", 3]];
add(TITLE("Table 9. The adopted model: regression by season"));
add(TABLE(["Term", ...G.map((g) => SEAS[g])], [
  ...t9.map(([lab, c, d]) => [lab, ...G.map((g) => coefCell(AD[g].terms[c], d))]),
  ["Prospect-seasons", ...G.map((g) => comma(AD[g].rows))], ["Players", ...G.map((g) => comma(AD[g].players))],
  ["Drafts", ...G.map((g) => comma(AD[g].drafts))], ["R-squared", ...G.map((g) => f3(AD[g].r2))]],
  [2600, 1350, 1350, 1350, 1350, 1350], [1, 2, 3, 4, 5]));
add(CAPTION("As Table 6. Production squared is in squared points (15 points enter as 225); age is on September 15 of the valuation season. The low R-squared reflects how uneven outcomes are: most prospects deliver no NHL surplus."));
const BT = (g) => {
  const specs = ["slot alone", "slot + production", "slot + production + squared", "adopted"];
  const cell = (s, c, d) => coefCell(B[g][s].terms[c], d);
  return TABLE(["Term", "(1) Draft position alone", "(2) + production", "(3) + production squared", "(4) Adopted: + age"], [
    ...t9.map(([lab, c, d]) => [lab, ...specs.map((s) => cell(s, c, d))]),
    ["Prospect-seasons", ...specs.map((s) => comma(B[g][s].rows))], ["R-squared", ...specs.map((s) => f3(B[g][s].r2))]],
    [2700, 1650, 1650, 1650, 1700], [1, 2, 3, 4]);
};
add(P("Table 10 shows the D+2 regression built up one term at a time, in the order of this document: draft position alone, then production, then its square, then age. Each column adds one term to the column before it, on the same prospect-seasons; Appendix B gives the same table for each other season."));
add(TITLE("Table 10. The D+2 regression built up one term at a time"));
add(BT("1"));
add(CAPTION("As Table 9. Column (2) also adds the no-record indicator. Column (4) is the adopted D+2 regression (Table 9)."));

add(H2("A worked prospect"));
add(P(`Nick Suzuki was traded to the Montreal Canadiens on September 10th, 2018, at the start of his D+2 season, a year after he was drafted 13th overall in 2017 by the Vegas Golden Knights. The star probability for his draft position is ${f1(100 * W.inputs.p_star)}%, his production level is ${f1(W.prod)} NHLe points per 82 games (above the 90th percentile in D+2, ${f1(N.prod_pct_k1["90"])}), and he was ${f1(W.age)} on September 15, 2018, a player drafted at his first opportunity. Table 11 builds his value from the D+2 regression.`));
const parts = [["Star probability for his draft position", "p_star", (x) => f3(x)], ["Production", "nhle82", (x) => f2(x)], ["Production squared", "nhle82_sq", (x) => f2(x)],
  ["No production record", "no_record", (x) => f2(x)], ["Production × (age − 18)", "prod_x_age", (x) => f2(x)]];
add(TITLE("Table 11. Nick Suzuki's value, term by term"));
add(TABLE(["Term", "His input", "Coefficient (D+2)", "Contribution"], [
  ...parts.map(([lab, c, fm]) => [lab, fm(W.inputs[c]), c === "nhle82_sq" ? f4(W.coefs[c]) : f3(W.coefs[c]), money(W.parts[c])]),
  ["Value, adopted model", "", "", money(W.value)], ["Value, production model without age (Section 2)", "", "", money(W.no_age)],
  ["Value on draft position alone (Section 1)", "", "", money(W.slot)], ["Value with his draft left out of the fit", "", "", money(W.own_out)]],
  [3600, 1400, 1600, 1500], [1, 2, 3], new Set(), [5]));
add(CAPTION(`Millions of dollars at the 2025-26 cap. Contributions are input times coefficient and sum to the adopted value. His production of ${f2(W.prod)} enters squared as ${f2(W.prod)}² = ${f2(W.inputs.nhle82_sq)}; his age less 18 is ${f2(W.age - 18)}. The production and squared terms are read together: his ${f2(W.prod)} points add ${money(W.parts.nhle82)} + ${money(W.parts.nhle82_sq)} = ${money(W.parts.nhle82 + W.parts.nhle82_sq)}.`));
add(P(`His scoring raises his value from ${mil(W.slot)} on his draft position to ${mil(W.value)}. The production model without age values him at ${mil(W.no_age)}, so age adds ${mil(W.value - W.no_age)}. Age adds value because Suzuki is among the youngest a D+2 prospect can be, and the model discounts each point by the age at which it was scored.`));

// ---- 4. the traded prospects ----------------------------------------------------------------------------
add(H1("4. The Traded Prospects"));
add(P(`From July 2017 to March 2022, clubs traded ${TR.drafted} drafted prospects (${TR.drafted_players} different players, as some were traded more than once) and ${TR.undrafted} undrafted prospects. The adopted model values them at ${mil(TR.tot_all)}: ${mil(TR.tot_main)} for the drafted prospects and ${mil(TR.tot_undrafted)} for the undrafted. Table 12 values the same ${TR.drafted} drafted prospects under each alternative considered above, so each decision's effect can be read in dollars on the same assets.`));
add(TITLE(`Table 12. The ${TR.drafted} traded drafted prospects under each version`));
const vers = [["Draft position alone, draft-day value however long ago (no fade)", ALT.slot_no_fade], ["Draft position alone, star value by season (Section 1)", ALT.slot_by_season],
  ["Draft position + linear production, draft position in each season", ALT.straight_slot_throughout], ["Draft position + linear and squared production, draft position in each season", ALT.curved_slot_throughout],
  ["Linear and squared production, draft position in D+1 to D+3 only, before age (Section 2)", ALT.curved_slot_early_no_age], ["Plus age as a flat amount", ALT.age_flat],
  ["Plus age as a flat amount and discounting production", ALT.age_both], ["Adopted: plus age discounting production, D+1 to D+4", ALT.adopted],
  ["Adopted, each prospect's draft left out of the fit", ALT.own_draft_out]];
add(TABLE(["Version", "Total value", "vs adopted"], vers.map(([lab, v]) => [lab, money(v), Math.abs(v - ALT.adopted) < 1e-9 ? "-" : money(v - ALT.adopted)]),
  [5600, 1700, 1700], [1, 2], new Set(), [7]));
add(CAPTION(`Millions of dollars at the 2025-26 cap; ${ALT.skaters_priced} skaters priced under each version and ${ALT.others_on_slot} goaltenders on draft position alone in each. Each version applies its fit on all drafts 2007-2017 to each prospect at the season of his trade.`));
add(P(`Production and age change many prospects' values. Moving from draft position alone to the adopted model moves ${TR.moved_025} of the ${TR.drafted} values by $0.25 million or more and leaves ${TR.top20_same_slot} of the 20 most valuable prospects in the top 20 (rank correlation ${f3(TR.rank)}).`));
add(P(`A value can be below zero. Of the ${TR.drafted} drafted prospects, ${TR.neg_drafted} are valued below zero, ${mil(TR.neg_drafted_sum)} in total; of all ${TR.drafted + TR.undrafted} prospects valued, ${TR.neg_all} are, the lowest at ${mil(TR.neg_min)}. A value below zero means that prospects with that profile, a low scorer from a late draft position, delivered slightly negative surplus on average in the data: when such players reach the NHL, their cost tends to exceed the value of the wins they deliver. Negative careers count, as in the draft pick curve.`));
add(FIGURE("fig_traded.png", "Figure 6. Production raises some prospects well above their draft position's value and lowers others",
  `Each point is one of the ${TR.drafted} traded drafted prospects, valued on draft position alone (horizontal) and on the adopted model (vertical), in millions of dollars at the 2025-26 cap. Points above the dashed line gained value from production and age. Colour shows the prospect's season at the trade.`, 440));
add(TITLE("Table 13. The ten most valuable traded drafted prospects"));
add(TABLE(["Traded", "Player", "Drafted", "Season", "Production", "Age", "Draft position alone", "Adopted"],
  TR.top10.map((r) => [r.date, r.name, `${r.draft} #${r.pick}`, r.k >= 4 ? `D+${r.k + 1}` : SEAS[String(r.k)], r.prod === null ? "-" : f1(r.prod),
    r.age === null ? "-" : f1(r.age), money(r.slot), money(r.main)]),
  [1150, 1900, 1100, 750, 1050, 1150, 1000, 1000], [4, 5, 6, 7]));
add(CAPTION("Production in NHLe points per 82 games; age on September 15 of the season of the trade; values in millions of dollars at the 2025-26 cap. Nikita Gusev, a 2012 draftee playing in the KHL, has the highest production level in the data from D+5 on, and his own career is in the fit that values him."));

add(H2("Undrafted prospects"));
add(P(`An undrafted player has no draft rights, so a club holds his NHL rights only through an NHL contract; an undrafted player on a minor-league contract is worth nothing to an NHL club in this currency. The ${TR.undrafted} undrafted prospects on NHL contracts are valued by the same model with the star probability set to zero, with seasons counted from the first draft at which they were eligible. They total ${mil(TR.tot_undrafted)}; the largest is ${TR.max_undrafted_name} at ${mil(TR.max_undrafted)}.`));
add(P(`Each was in D+5 or later at his trade, where draft position is not in the model, so setting his star probability to zero changes none of their values. Two limitations remain. First, the model learns from drafted players only, including many whose rights lapsed and who delivered nothing, while undrafted prospects on NHL contracts are players a club chose to sign; the model, therefore, probably undervalues them. The contract records begin in 2018-19, so the drafted prospects of 2007-2017 under NHL contracts cannot be separated out. Second, with no age term from D+5 on, an undrafted 22-year-old and a 25-year-old with the same scoring receive the same value.`));

// ---- appendices ----------------------------------------------------------------------------------------------
add(H1("Appendix A. Decisions Not Covered Above"));
add(TABLE(["Decision", "Adopted", "Alternative", "Why", "Effect"], [
  ["Currency", "Remaining surplus to the end of the club's control", "Entry-level years only", "A club controls a drafted player to 27 or seven roster seasons, long after his entry-level contract; one scale with picks and contracts", "Not measured; the entry-level years alone omit the control years"],
  ["Who is a prospect", "The player model's entry point (no 10+ game season in three; goaltenders no game in six)", "Any NHL game sends him to the player model", "No player is valued twice or by neither model", "The alternative would change the player model's forecast"],
  ["Undrafted prospects", "On NHL contracts only", "All undrafted players", "Only an NHL contract gives a club NHL rights", `${TR.undrafted} assets, ${money(TR.tot_undrafted)}`],
  ["Trades after the regular season", "Valued at the next season", "The season just ended", "The season's games are played and its data complete at the trade", "23 traded prospects move, -$3.51M in total (recorded October 14, 2026)"],
], [1500, 2100, 1600, 2300, 1800]));
add(H1("Appendix B. The Regressions Built Up One Term at a Time"));
let bt = 1;
for (const g of ["0", "2", "3", "4+"]) {
  add(TITLE(`Table B${bt}. The ${SEAS[g]} regression built up one term at a time`));
  add(BT(g));
  add(CAPTION(g === "3" || g === "4+"
    ? `As Table 10. In the adopted model draft position is out from D+4${g === "4+" ? ", and age is out from D+5" : ""}, so column (4) drops ${g === "4+" ? "both" : "draft position"}.`
    : "As Table 10."));
  bt += 1;
}
const formsB = [["Flat: per year of age", "+ age", "past_elig"], ["Discount: production × age", "+ age x production", "prod_x_age"],
  ["Both: per year of age", "+ age and age x production", "past_elig"], ["Both: production × age", "+ age and age x production", "prod_x_age"]];
add(TITLE(`Table B${bt}. The age terms in each tested form`));
add(TABLE(["Form and term", ...G.map((g) => SEAS[g])],
  formsB.map(([lab, arm, c]) => [lab, ...G.map((g) => { const r = AC(g, arm); return coefCell({ b: r[c], se: r[`${c}_se`], p: erfcP(r[c], r[`${c}_se`]) }); })]),
  [2900, 1300, 1300, 1300, 1300, 1300], [1, 2, 3, 4, 5]));
add(CAPTION("Coefficients in millions of dollars per year of age (flat) or per NHLe point per year of age (discount), standard errors clustered by player in parentheses and two-sided p-values in brackets; each form is one regression with the full set of interaction terms and the production terms of Section 2. These candidates were fitted with age measured as years past first eligibility (his age less 18, less the seasons since his draft). Measuring age from 18 instead leaves the discount alone unchanged, as in Table 9; the forms with the flat term would be different fits, because the regression has no constant term to absorb the difference."));

function erfcP(b, se) {
  if (!(se > 1e-12)) return null;                       // v2.5: no p-value when the standard error is zero
  const x = Math.abs(b / se) / Math.SQRT2, t = 1 / (1 + 0.3275911 * x);
  return t * Math.exp(-x * x) * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))));
}

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
