"""
control_cost_figure.py v1.2 -- the control-cost bar chart for "Arbitration Cost Update" (Figure 1).

WHY (Thomas, 2026-10-15, a note on the Arbitration Cost Update): "In the previous Valuing Draft Picks document you
had a bar graph showing the difference between surplus value, what the model costed players at, and what teams
paid. Bring that back here." That graph (pick_summary_figures.py v1.2, Figure 3) read top_pick_control_look.py v1.1,
which prices on the qualifying-offer chain and the price line of 2026-10-09. This script redraws it on the CURRENT
pick curve (pick_curve.py v1.5: September 15 ages, the re-locked price line, the market price rule) and adds the
market price rule's cost as a fourth bar, beside the chain it replaced. REPORT ONLY: it changes no model file.

WHAT IT DRAWS, by draft slot band (picks 1-10, 11-15, 16-32; the old figure's bands), the average per first-round
skater of the 2007-2017 drafts who played an NHL game in his window (pick_curve_players.csv nhl_seasons > 0,
is_goalie false; as the old figure, no filter on how his rights were held), summed over the seasons his club
controlled him (entry-level and restricted free agent seasons alike; pick_curve_seasons.csv holds only seasons with
NHL games, each scaled by games_scale for under 10 games):
  * value delivered          value_share     (the market price of his wins)
  * cost, qualifying offers  cost_qo_share   (the chain the model used until 2026-10-13)
  * cost, market price rule  cost_share      (the adopted cost)
  * cost actually paid       his cap hit that season / that season's cap x games_scale, read as
                             top_pick_control_look.py v1.1 reads it: PuckPedia (contract_season_spine.csv,
                             pp_cap_hit, the larger if two rows) from 2018-19 by NHL id, else his CapWages page
                             (the cached pages; a page only if its "Drafted" line names the same draft year and
                             pick); a cap hit above that season's cap is refused as corrupt. A season with no cap
                             hit keeps the market price rule's cost (counted, and stated in the caption).
  Each share x the 2025-26 cap, in $M.

GUARD: the sums by pick_curve.py's own groups (picks 1-10 and 11-32; routes "same team" and "traded first";
goalies included, as its log) must equal the "first-round picks who played" lines of pick_curve_log.txt to the
$0.1M it prints, so the figure and the 1.61x / 1.34x in the note come from one run.

DOCUMENT: with --doc PATH (default 40_DOCS/Supervisor_Drafts/Arbitration Cost Update.docx) the figure goes into
the Word file in place of the paragraph "[Figure 1 is inserted here by 25_TESTS/control_cost_figure.py]", and the
caption's {{...}} counts are filled. Run again after the figure is in, it replaces the image (word/media/
control_cost.png) and leaves the text alone. Standard library only for the Word step (zipfile).

v1.1: stops plainly when the pick curve output predates v1.5. v1.2 (Thomas's first laptop run): the temporary
Word file is closed before it is swapped in (v1.1 left it open, and Windows refused the move); a re-run refreshes the
caption's counts; the cap-hit coverage is printed by band with the CapWages folders read, and the figure stays out of
the note when over 10% of seasons have no cap hit (--allow-gaps overrides).

OUTPUTS: OUTPUT_DIR/control_cost_figure/control_cost.png, control_cost_bands.csv, control_cost_figure_log.txt.
Run from the repo root:  python 25_TESTS/control_cost_figure.py      (after pick_curve.py; needs matplotlib)
"""

import argparse
import html as htmlmod
import os
import re
import struct
import sys
import zipfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                   # noqa: E402
import numpy as np                                # noqa: E402
import pandas as pd                               # noqa: E402
from dotenv import load_dotenv                    # noqa: E402

SCRIPT_VERSION = "control_cost_figure.py v1.2 (2026-10-15)"
load_dotenv()
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_CODE"))
import skater_forward_projection as sfp          # noqa: E402

SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])
OUT = OUTPUT_DIR / "control_cost_figure"
CAP_NOW = sfp.CAP_CEILING[2025]                   # every dollar figure at the 2025-26 cap, as pick_curve.py
BANDS = ((1, 10), (11, 15), (16, 32))             # the old figure's bands
PLACEHOLDER = "[Figure 1 is inserted here by 25_TESTS/control_cost_figure.py]"
MEDIA = "word/media/control_cost.png"
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


# ---- CapWages pages (as top_pick_control_look.py v1.1) ------------------------------------------------------
def page_text(raw):
    return htmlmod.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw)))


def drafted(txt):
    m = re.search(r"Drafted\s*:\s*(\d{4})\s+Rd\s+\d+\s+\(#(\d+)\)", txt)
    return (int(m.group(1)), int(m.group(2))) if m else None


def cap_hits(txt):
    """Season -> cap hit from the contract tables ('YYYY-YY <clause> $cap pct% $aav'); the first listed wins."""
    out = {}
    for s, cap in re.findall(r"(\d{4})-\d{2} \S+ \$([\d,]+) [\d.]+% \$[\d,]+", txt):
        out.setdefault(int(s), float(cap.replace(",", "")))
    return out


# ---- the Word step: one inline picture in place of the placeholder paragraph --------------------------------
def drawing_xml(rid, cx, cy):
    return (f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
            f'<wp:docPr id="9101" name="Control cost"/><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            f'<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr>'
            f'<pic:cNvPr id="9101" name="control_cost.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill>'
            f'<a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr>'
            f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/>'
            f'</a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>')


# the caption's counts: a {{TOKEN}} on the first insertion, the previous run's number on a re-run (v1.2)
CAPTION_RX = {"N_PLAYERS": r"2007-2017 drafts \((\{\{N_PLAYERS\}\}|[\d,]+) players\)",
              "NO_CAP_HIT": r"before; (\{\{NO_CAP_HIT\}\}|[\d,]+) of ",
              "SEASONS": r" of (\{\{SEASONS\}\}|[\d,]+) seasons with no cap hit"}


def put_in_doc(doc, png, fills):
    doc = Path(doc)
    with zipfile.ZipFile(doc) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    xml = parts["word/document.xml"].decode("utf-8")
    if MEDIA in parts:                                       # already inserted: replace the picture and the counts
        parts[MEDIA] = png.read_bytes()
        how = "picture and caption counts replaced"
    else:
        m = re.search(r"<w:p\b(?:(?!<w:p\b).)*?" + re.escape(PLACEHOLDER) + r".*?</w:p>", xml, flags=re.S)
        assert m, f"placeholder paragraph not found in {doc}"
        rels = parts["word/_rels/document.xml.rels"].decode("utf-8")
        rid = "rIdControlCost"
        assert rid not in rels
        rels = rels.replace("</Relationships>", f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/'
                            f'officeDocument/2006/relationships/image" Target="media/control_cost.png"/></Relationships>')
        w, h = struct.unpack(">II", png.read_bytes()[16:24])  # PNG header: width, height
        cx = int(6.0 * 914400)                                # six inches wide
        para = ('<w:p><w:pPr><w:keepNext/><w:spacing w:before="60" w:after="60"/><w:jc w:val="center"/></w:pPr>'
                + drawing_xml(rid, cx, int(cx * h / w)) + "</w:p>")
        xml = xml[:m.start()] + para + xml[m.end():]
        ct = parts["[Content_Types].xml"].decode("utf-8")
        if 'Extension="png"' not in ct:
            ct = ct.replace("</Types>", '<Default Extension="png" ContentType="image/png"/></Types>')
        parts.update({"word/_rels/document.xml.rels": rels.encode("utf-8"), "[Content_Types].xml": ct.encode("utf-8"),
                      MEDIA: png.read_bytes()})
        how = "figure and caption counts inserted"
    for k, v in fills.items():
        rx = CAPTION_RX[k]
        assert len(re.findall(rx, xml)) == 1, f"caption count {k} not found once in {doc}"
        xml = re.sub(rx, lambda mm: mm.group(0).replace(mm.group(1), v), xml)
    parts["word/document.xml"] = xml.encode("utf-8")
    # v1.2: write a closed temporary file beside the note, then swap it in (v1.1 left its temp file open, and
    # Windows refused the move). If Word holds the note, say so and leave the note as it was.
    tmp = doc.with_name(doc.name + ".tmp")
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", parts.pop("[Content_Types].xml"))   # first, as Word writes it
            for n, b in parts.items():
                z.writestr(n, b)
        os.replace(tmp, doc)
    except PermissionError:
        sys.exit(f"STOP: Windows would not replace {doc}. Close it in Word and run again; the note is unchanged.")
    finally:
        if tmp.exists():
            tmp.unlink()
    return how


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", default=str(ROOT / "40_DOCS" / "Supervisor_Drafts" / "Arbitration Cost Update.docx"))
    ap.add_argument("--no-doc", action="store_true", help="draw the figure only")
    ap.add_argument("--allow-gaps", action="store_true", help="insert even with over 10%% of seasons lacking a cap hit")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    log(SCRIPT_VERSION)
    F = {"seasons": OUTPUT_DIR / "pick_curve_seasons.csv", "players": OUTPUT_DIR / "pick_curve_players.csv",
         "curve_log": OUTPUT_DIR / "pick_curve_log.txt", "pp_seasons": OUTPUT_DIR / "contract_season_spine.csv"}
    for k, p in F.items():
        log(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")
    curve_log = F["curve_log"].read_text(encoding="utf-8")
    log(f"  pick curve: {curve_log.splitlines()[0]}")
    # GUARD (v1.1): the note's figures come from pick_curve.py v1.5 (2026-10-14); an older run has no chain column
    m = re.match(r"pick_curve\.py v(\d+)\.(\d+)", curve_log)
    if not m or (int(m.group(1)), int(m.group(2))) < (1, 5):
        sys.exit("STOP: 30_OUTPUT's pick curve is older than v1.5 (the version the note quotes). Run, from the repo "
                 "root:\n  python 20_CODE/elc_signing_dates.py\n  python 20_CODE/pick_curve.py\nthen check its log's "
                 "first line says v1.5 and the star value is 18.03, and run this script again.")

    se = pd.read_csv(F["seasons"])
    missing = {"value_share", "cost_share", "cost_qo_share", "games_scale", "cap"} - set(se.columns)
    assert not missing, f"pick_curve_seasons.csv lacks {sorted(missing)}: re-run pick_curve.py"
    pl = pd.read_csv(F["players"])
    se = se.merge(pl[["draftYear", "pick", "player", "playerId", "is_goalie", "route", "nhl_seasons"]],
                  on=["draftYear", "pick"], how="left", validate="many_to_one")
    assert se["route"].notna().all()

    # ---- GUARD: pick_curve.py's own first-round sums ---------------------------------------------------------
    fr = se[se["route"].isin(["same team", "traded first"])]
    for lo, hi in ((1, 10), (11, 32)):
        g = fr[fr["pick"].between(lo, hi)]
        v, c, cq = (g[k].sum() * CAP_NOW / 1e6 for k in ("value_share", "cost_share", "cost_qo_share"))
        m = re.search(rf"picks {lo}-{hi}: value delivered ([\d,.]+); cost ([\d,.]+) \(([\d.]+)x the qualifying-offer "
                      rf"chain's ([\d,.]+)\)", curve_log)
        assert m, f"pick_curve_log.txt has no line for picks {lo}-{hi}"
        lv, lc, _, lq = (float(x.replace(",", "")) for x in m.groups())
        assert abs(v - lv) < 0.06 and abs(c - lc) < 0.06 and abs(cq - lq) < 0.06, (lo, hi, v, c, cq, m.group(0))
        log(f"  guard: picks {lo}-{hi} value {v:,.1f}, cost {c:,.1f} ({c / cq:.2f}x the chain's {cq:,.1f}) "
            f"equal pick_curve_log.txt (PASS)")

    # ---- actual cap hits, season by season ----------------------------------------------------------------
    pages = {}
    for d_ in (SOURCE_DIR / "capwages_cache", OUTPUT_DIR / "capwages_top_picks"):
        if d_.exists():
            for f in sorted(d_.glob("*.html")):
                t = page_text(f.read_text(encoding="utf-8", errors="ignore"))
                k = drafted(t)
                if k:
                    pages.setdefault(k, cap_hits(t))
    log(f"  CapWages pages with a draft line: {len(pages):,}")
    pp = pd.read_csv(F["pp_seasons"], usecols=["nhl_id", "season_start", "pp_cap_hit"]).dropna()
    pp = pp.groupby(["nhl_id", "season_start"])["pp_cap_hit"].max().to_dict()

    fig_rows = se[(se["pick"] <= 32) & ~se["is_goalie"].astype(bool) & (se["nhl_seasons"] > 0)].copy()
    acts, src, corrupt = [], [], 0
    for r in fig_rows.itertuples():
        pv = pp.get((int(r.playerId), int(r.season))) if (pd.notna(r.playerId) and r.season >= 2018) else None
        cw = pages.get((int(r.draftYear), int(r.pick)), {}).get(int(r.season))
        if cw is not None and cw > r.cap:
            cw, corrupt = None, corrupt + 1                 # GUARD: a cap hit above the ceiling is not a cap hit
        act = pv if pv is not None else cw
        if act is None:
            acts.append(r.cost_share)
            src.append("market price rule (no cap hit)")
        else:
            acts.append(act / r.cap * r.games_scale)
            src.append("PuckPedia" if pv is not None else "CapWages")
    fig_rows["cost_actual_share"], fig_rows["actual_source"] = acts, src
    counts = fig_rows["actual_source"].value_counts()
    log(f"  seasons priced: {len(fig_rows):,}; cap hit from " + ", ".join(f"{k} {v:,}" for k, v in counts.items())
        + f"; CapWages cap hits above the ceiling refused: {corrupt}")

    per = fig_rows.groupby(["draftYear", "pick"])[["value_share", "cost_qo_share", "cost_share",
                                                    "cost_actual_share"]].sum() * CAP_NOW / 1e6
    per = per.reset_index()
    rows = []
    for lo, hi in BANDS:
        g = per[per["pick"].between(lo, hi)]
        rows.append({"band": f"Picks {lo}-{hi}", "players": len(g), "value": g["value_share"].mean(),
                     "cost_qo_chain": g["cost_qo_share"].mean(), "cost_market_rule": g["cost_share"].mean(),
                     "cost_actual": g["cost_actual_share"].mean()})
    cc = pd.DataFrame(rows)
    cc["market_rule_x_chain"] = cc["cost_market_rule"] / cc["cost_qo_chain"]
    cc["actual_x_chain"] = cc["cost_actual"] / cc["cost_qo_chain"]
    cc["actual_x_market_rule"] = cc["cost_actual"] / cc["cost_market_rule"]
    log("\nAVERAGE PER FIRST-ROUND SKATER WHO PLAYED, over his club's control ($M at the 2025-26 cap)")
    log(cc.round(2).to_string(index=False))
    cc.to_csv(OUT / "control_cost_bands.csv", index=False)

    # cross-check (information only): the old look's actual cost per player, where it has the player
    old = OUTPUT_DIR / "top_pick_control_look.csv"
    if old.exists():
        o = pd.read_csv(old)[["draftYear", "pick", "cost_actual_$M"]].merge(per, on=["draftYear", "pick"])
        gap = (o["cost_actual_$M"] - o["cost_actual_share"]).abs()
        log(f"  cross-check with top_pick_control_look.csv: {int((gap < 0.05).sum())} of {len(o)} players' actual "
            f"cost within $0.05M (windows and ages moved on 2026-10-14, so some differ)")

    # ---- the figure (pick_summary_figures.py's palette and style) ------------------------------------------
    BLUE, GRAY, AQUA, ORANGE, INK2 = "#2a78d6", "#8a8984", "#1baf7a", "#eb6834", "#52514e"
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": "#c9c8c3",
                         "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                         "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#ecebe8",
                         "grid.linewidth": 0.6, "axes.axisbelow": True, "figure.dpi": 200, "savefig.bbox": "tight",
                         "legend.frameon": False})
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    x = np.arange(len(cc))
    bars = (("value", BLUE, "Value delivered"), ("cost_qo_chain", GRAY, "Cost charged: qualifying-offer chain (before)"),
            ("cost_market_rule", AQUA, "Cost charged: market price rule (now)"),
            ("cost_actual", ORANGE, "Cost actually paid (cap hits)"))
    for i, (col, colour, lab) in enumerate(bars):
        xs = x + (i - 1.5) * 0.2
        ax.bar(xs, cc[col], width=0.19, color=colour, label=lab)
        for xx, vv in zip(xs, cc[col]):
            ax.text(xx, vv + 0.25, f"{vv:.1f}", ha="center", va="bottom", fontsize=6.5, color=INK2)
    ax.set_xticks(x, [f"{b}\n({n} NHL players)" for b, n in zip(cc["band"], cc["players"])])
    ax.set_ylabel("$M per player, while his club controls him")
    ax.set_ylim(0, cc[["value", "cost_qo_chain", "cost_market_rule", "cost_actual"]].max().max() * 1.12)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, fontsize=7.5)   # above the bars, never on them
    png = OUT / "control_cost.png"
    fig.savefig(png)
    plt.close(fig)
    log(f"\n  wrote {png}")

    nh = int((fig_rows["actual_source"] == "market price rule (no cap hit)").sum())
    for lo, hi in BANDS:                                     # v1.2: coverage of the "actually paid" bar, by band
        g = fig_rows[fig_rows["pick"].between(lo, hi)]
        gap = int((g["actual_source"] == "market price rule (no cap hit)").sum())
        log(f"  picks {lo}-{hi}: {gap:,} of {len(g):,} seasons without a cap hit ({gap / len(g):.0%})")
    for d_ in (SOURCE_DIR / "capwages_cache", OUTPUT_DIR / "capwages_top_picks"):
        n = len(list(d_.glob("*.html"))) if d_.exists() else 0
        log(f"  CapWages folder {d_}: {'present' if d_.exists() else 'MISSING'}, {n:,} pages")
    # GUARD (v1.2): a season without a cap hit takes the model's cost, which pulls the "actually paid" bar toward the
    # model's; over 10% of seasons and the bar is not what clubs paid, so the figure stays out of the note
    if not a.no_doc and nh > 0.10 * len(fig_rows) and not a.allow_gaps:
        (OUT / "control_cost_figure_log.txt").write_text("\n".join(LOG), encoding="utf-8")
        sys.exit(f"STOP: {nh:,} of {len(fig_rows):,} seasons ({nh / len(fig_rows):.0%}) have no cap hit, so the 'cost "
                 f"actually paid' bar is mostly the model's own cost. The note was not changed. Check the CapWages folder counts "
                 f"above against the folders top_pick_control_look.py read on 2026-10-09.")
    if not a.no_doc:
        how = put_in_doc(a.doc, png, {"N_PLAYERS": f"{int(cc['players'].sum()):,}", "NO_CAP_HIT": f"{nh:,}",
                                      "SEASONS": f"{len(fig_rows):,}"})
        log(f"  {a.doc}: {how}")
    (OUT / "control_cost_figure_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
