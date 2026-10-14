// control_cost_note_doc.js v1.1 (2026-10-14) -- builds "Arbitration Cost Update.docx" (40_DOCS/Supervisor_Drafts/).
// v1.1 (Thomas, 2026-10-14: "new figures"): every figure from the final run of the day (September 15 ages,
// the re-locked price line, the forecast-based market price, signing-year ages); sources: pick_curve_log.txt v1.5,
// traded_pick_values_log.txt, arbitration_player_compare.py v1.1, pick_lookup.py regression,
// pick_class_overlap_check.py, the 2026-10-14 session log. The 'before' column is the qualifying-offer chain.
//
// A short bullet note (Thomas, 2026-10-14: "a short bullet point document that describes that changes were made to
// the draft model and to the player pricing side of the player model and the checks that were done"). Reader-facing:
// names no reader. Figures copied from the recorded runs:
//   star values, eligible seasons, first-round cost ratios   30_OUTPUT/pick_curve_log.txt (pick_curve.py v1.4)
//   pick values at slots                                      13.42 / 31.66 x draft_slot_baseline.csv p_star
//   traded picks $704.8M -> $298.8M                           traded_pick_values_log.txt; 2026-10-13b session log
//   actual pay 3.2x / 2.1-2.3x                                top_pick_control_look.py v1.1 (8.44 vs 27.04; 7.03 vs 16.43;
//                                                             5.88 vs 12.20)
//   contract valuations, top-20 lists                         arbitration_player_compare.py v1.1 (run 2026-10-14)
//   PuckPedia flag persistence 92.4% of 225                   2026-10-13b session log
//   reproduction within $2e-9; refresh 10 of 10               2026-10-13b session log
//   Game Value check                                          pick_star_gv_check.py v1.0
//   regression with a constant                                pick_lookup.py regression (run 2026-10-14)
//   draft overlap, leave one draft out                        pick_class_overlap_check.py v1.0
//
// Run:  NODE_PATH=<folder with docx> node 25_TESTS/control_cost_note_doc.js
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType,
  BorderStyle, LevelFormat,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const OUTFILE = path.join(ROOT, "40_DOCS", "Supervisor_Drafts", "Arbitration Cost Update.docx");
const FONT = "Calibri";

const P = (text, opts = {}) => new Paragraph({ spacing: { after: 100 }, ...opts,
  children: [new TextRun({ text, font: FONT, size: 22, ...(opts.run || {}) })] });
const H = (text) => new Paragraph({ spacing: { before: 220, after: 100 }, keepNext: true,
  children: [new TextRun({ text, font: FONT, size: 26, bold: true })] });
const B = (text, level = 0) => new Paragraph({ numbering: { reference: "bul", level }, spacing: { after: 60 },
  children: [new TextRun({ text, font: FONT, size: 22 })] });

const border = { style: BorderStyle.SINGLE, size: 4, color: "999999" };
const cell = (t, bold = false, w = 2340) => new TableCell({
  width: { size: w, type: WidthType.DXA }, borders: { top: border, bottom: border, left: border, right: border },
  margins: { top: 40, bottom: 40, left: 100, right: 100 },
  children: [new Paragraph({ alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: t, font: FONT, size: 20, bold })] })] });
const slots = [[1, "23.85", "13.48"], [2, "18.82", "10.63"], [5, "11.37", "6.43"], [10, "6.76", "3.82"],
               [20, "3.69", "2.08"], [32, "2.37", "1.34"], [64, "1.20", "0.68"], [100, "0.76", "0.43"]];
const table = new Table({
  width: { size: 7020, type: WidthType.DXA }, columnWidths: [2340, 2340, 2340],
  rows: [new TableRow({ tableHeader: true, children: [cell("Draft slot", true), cell("Qualifying-offer chain ($M)", true),
                                                       cell("Market price rule ($M)", true)] }),
         ...slots.map(([s, a, b]) => new TableRow({ children: [cell(String(s)), cell(a), cell(b)] }))],
});

const doc = new Document({
  numbering: { config: [{ reference: "bul", levels: [
    { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 360, hanging: 260 } } } },
    { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 720, hanging: 260 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 },
                          margin: { top: 1080, bottom: 1080, left: 1200, right: 1200 } } },
    children: [
      new Paragraph({ spacing: { after: 160 }, children: [new TextRun({ text: "Arbitration Cost Update",
        font: FONT, size: 34, bold: true })] }),
      P("Changes to the cost of control seasons in the draft pick model and the player model, and the checks run on them. Dollar figures are at the 2025-26 salary cap."),

      H("1. What Changed"),
      B("Control seasons are the restricted free agent seasons after a player's entry-level contract, while his team holds his rights. Both models used to cost each control season as a one-year qualifying offer, each offer computed on the one before."),
      B("Now, once a player is eligible for salary arbitration, a control season costs the higher of the qualifying offer and the market price of his production. The market price is the contract line's price for the model's own estimate of his level going into that season: his last three seasons' rate per 82 games, weighted 50/30/20 with the most recent first and by games played, pulled 35% toward comparable players, times his expected share of games. It uses only seasons before that one. Before eligibility, the qualifying offer still applies."),
      B("The reason: the qualifying-offer chain charged far less than teams paid. For first-round picks who played, actual cap hits over the control seasons were 3.2 times the chain's cost for picks 1-10 and 2.1 to 2.3 times for picks 11-32. Part of that gap is long contracts that also buy free-agent seasons."),
      B("The same rule applies to drafted players and to players under contract, so a pick and a player are costed the same way."),
      B("Eligibility follows the CBA (Section 12.1). A player needs four years of professional experience if he first signed at 18-20, three at 21, two at 22-23 and one at 24 or older, with age taken on September 15 of the year he first signed. For drafted players the signing year comes from PuckPedia and CapWages contract records (1,092 of the 1,157 who played); his first NHL season stands in for the other 65."),
      B("For drafted players the years are counted from the data, a year being a season of 10 or more NHL games. The data holds no AHL games, so eligibility comes later than in fact and the cost is understated.", 1),
      B("For players under contract the model uses PuckPedia's arbitration-eligibility flag on the contract.", 1),
      B("Every age in the model is now read on September 15 of the season's first year, the date the CBA uses, instead of February 1 of its second year. The price line was re-estimated on the new ages: $1.673 million per forecast win for forwards (from $1.668 million), $2.043 million for defencemen (from $2.012 million)."),

      H("2. Draft Picks"),
      B("The star value, which is the surplus a pick would be worth if its player were certain to become a star, is $18.03 million (standard error 1.73) against $31.90 million under the qualifying-offer chain. Without the 2015 and 2016 drafts it is $15.68 million against $27.82 million."),
      B("Of the 2,658 control seasons drafted players played, 1,488 were priced at the market price and 1,103 of those cost more than the qualifying offer. For first-round picks who played, the cost of control seasons is now 1.61 times the chain's for picks 1-10 and 1.34 times for picks 11-32. It remains below what teams actually paid."),
      B("A pick's value is the star value times Bacon's probability that the pick becomes a star:"),
      table,
      P(""),
      B("The 634 picks traded from July 2017 to March 2022 are worth $401.3 million in total, against $710.1 million under the qualifying-offer chain."),

      H("3. Player Contracts"),
      B("856 of the 7,817 contract valuations in the panel (seasons 2018-19 to 2026-27) are lower than under the qualifying-offer chain, and none are higher. These are 856 of the 882 valuations that carry control-season value. The median fall is $0.81 million and the largest is $15.66 million."),
      B("The players affected are young players with control seasons still ahead. On the 2025-26 list, Matvei Michkov is valued at $12.82 million against $21.47 million under the chain, Macklin Celebrini at $12.03 million against $19.83 million and Marco Kasper at $9.63 million against $16.30 million."),
      B("16 of the top 20 contracts on the 2024-25 list and 17 of 20 on the 2025-26 list stay in the top 20. Players on long contracts with no control seasons left are not affected."),

      H("4. Checks"),
      B("The full rebuild passed each of its 10 steps, including the dashboard's check that each re-priced valuation is within $1 of the panel. The qualifying-offer chain is still priced beside every value."),
      B("The market price rebuilds the model's starting estimate at each control season. At the season the model itself starts from, the rebuild was checked to equal the model's estimate (to nine decimal places) for every player priced."),
      B("Eligibility counted from the CBA agrees with PuckPedia's flag on 64.1% of the 1,656 skater contracts that ended in restricted free agency from 2018-19 to 2024-25. The count is later for 540 contracts, mostly because the data holds no AHL games, and earlier for 54. That is why contracts use the flag."),
      B("Where PuckPedia marks a player not yet eligible when his contract ends, the model makes him eligible from his second control season. Of the 225 such players who then signed a one-year restricted contract, 92.4% were eligible at its end."),
      B("Bacon's star probability was checked against a rating built without his WAR model, the Game Value metric. On the 2013-2019 drafts (1,337 skater picks), the share of Game Value stars is within two standard errors of the share of WAR stars in each of 9 ranges of draft slots: 5.5% against 6.1% overall, and Bacon's 5.3%. Adding the log of the pick number beside his probability adds nothing (p = 0.42)."),
      B("Fitting the star value with a constant gives $17.70 million (standard error 2.02) against $18.03 million without one. The constant is $0.07 million a pick at an average draft (p = 0.44)."),
      B("Each change was scored on its own, on the same drafts: the arbitration rule with the earlier market price (the last three seasons' WAR, 50/30/20) gives $13.53 million; reading ages in the signing year alone, $13.82 million; the model-based market price alone, $17.75 million; both, $18.03 million."),
      B("None of the 634 traded picks is for a draft inside the drafts the star value is fitted on (2007-2017). Each is for a draft from 2018 to 2025, so no traded pick's value contains its own outcome. Leaving one draft out of the fit moves the star value between $16.59 million (without 2015) and $19.37 million (without 2012)."),
    ],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUTFILE, buf);
  console.log(`wrote ${OUTFILE}`);
});
