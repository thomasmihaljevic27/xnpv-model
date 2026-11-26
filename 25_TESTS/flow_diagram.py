"""
flow_diagram.py -- the method on one page: how a trade is valued and tested (40_DOCS/Method_Flow.pdf and .png).

ASKED (Karl, meeting of 2026-11-23: "we had that flow diagram ... now that we're done ... you can make a better one";
Thomas, 2026-11-27: "Agreed, build it", on the layout agreed that day). It replaces the three-column chart of the
September plain-language overview, whose steps (surplus value, the exit risk, an average per draft position, a prospect's
odds times payoff, the ratio test) the model no longer takes.

WHAT IT SHOWS, top to bottom: the data, each box naming the part it feeds; the three valuation documents as columns, each
step in the order the document gives it, with the player model's price line and cost rules feeding the pick and prospect
columns; the trade on one scale; the findings as a chain. Model boxes carry no coefficients, so the page does not go stale
when a figure moves; the findings' headline figures are read from OUTPUT_DIR/findings_doc/numbers.json (findings_numbers.py)
and guarded against the findings document's.

GUARDS: each box's height is set from its measured text (word wrap on measured widths, Arial); after drawing, the script
stops if any line of text falls outside its box, if two boxes overlap, or if the columns run into the trade box.

Run from the repo root:  python 25_TESTS/flow_diagram.py
"""

import json
import os
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch    # noqa: E402
from matplotlib.font_manager import FontProperties                 # noqa: E402
from dotenv import load_dotenv                                     # noqa: E402

SCRIPT_VERSION = "flow_diagram.py v1.0 (2026-11-27)"
load_dotenv(".env")
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ["OUTPUT_DIR"])
print(SCRIPT_VERSION)

N = json.loads((OUT / "findings_doc" / "numbers.json").read_text(encoding="utf-8"))
FAV = 100 * N["s2"]["war"]["fav"][0]
SLOPE = N["s2"]["war"]["slope"][0]
IV = N["s4"]["iv"]["perf"][0]
assert abs(FAV - 57.1) < 0.05 and abs(SLOPE - 0.749) < 0.0005 and abs(IV - 0.39) < 0.005, (FAV, SLOPE, IV)   # the document's

INK, MUTED, LINE = "#1F1E1C", "#55534E", "#8A8984"
BLUE, ORANGE, GREEN, PURPLE = "#2F6DB5", "#D9692B", "#23955F", "#6B4FA0"
LIGHT = {BLUE: "#E8F0FA", ORANGE: "#FBEDE4", GREEN: "#E5F4EC", PURPLE: "#EFEAF7", INK: "#F4F3EF"}
plt.rcParams.update({"font.family": "Arial", "font.size": 7})

W, H = 11.0, 8.5
fig = plt.figure(figsize=(W, H))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")
RND = fig.canvas.get_renderer()
TS, BS = 7.3, 6.4                    # title and body sizes, points
PADX, PADT, GAPT, PADB = 0.12, 0.065, 0.03, 0.07
PLACED = []                          # (text artist, box rectangle) for the containment guard
BOXES = []                           # every box, for the overlap guard


def width_in(s, size, bold):
    fp = FontProperties(family="Arial", size=size, weight="bold" if bold else "normal")
    return RND.get_text_width_height_descent(s, fp, ismath=False)[0] / fig.dpi


def wrap(text, w, size, bold=False):
    """Greedy word wrap on measured widths, so no line runs past the box."""
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and width_in(trial, size, bold) > w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return "\n".join(lines + [cur])


def height_of(s, size, bold):
    t = ax.text(0, 0, s, fontsize=size, fontweight="bold" if bold else "normal", va="top", linespacing=1.2)
    h = t.get_window_extent(RND).height / fig.dpi
    t.remove()
    return h


def lay(title, body, w, ts=TS, bs=BS):
    t = wrap(title, w - 2 * PADX - 0.1, ts, True)       # 0.1 in spare: the PNG renders text a little wider than measured
    b = wrap(body, w - 2 * PADX - 0.1, bs) if body else ""
    th = height_of(t, ts, True)
    h = PADT + th + (GAPT + height_of(b, bs, False) if b else 0) + PADB
    return t, b, th, h


def box(x, top, w, title, body="", color=INK, fill=None, bold_box=False, h=None, ts=TS, bs=BS):
    """Draw a box from its top edge down; its height fits its text unless h is given. Returns the bottom edge."""
    t, b, th, need = lay(title, body, w, ts, bs)
    h = max(h or 0, need)
    y = top - h
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.05",
                                linewidth=1.3 if bold_box else 0.7, edgecolor=color if bold_box else LINE,
                                facecolor=fill or "white", zorder=2))
    ax.add_patch(FancyBboxPatch((x, y), 0.045, h, boxstyle="square,pad=0", linewidth=0, facecolor=color, zorder=3))
    rect = (x, y, w, h)
    PLACED.append((ax.text(x + PADX, top - PADT, t, ha="left", va="top", fontsize=ts, fontweight="bold", color=INK,
                           zorder=4, linespacing=1.2), rect))
    if b:
        PLACED.append((ax.text(x + PADX, top - PADT - th - GAPT, b, ha="left", va="top", fontsize=bs, color=MUTED,
                               zorder=4, linespacing=1.2), rect))
    BOXES.append(rect)
    return y


def arrow(x0, y0, x1, y1, color=LINE, ls="-", lw=0.9):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=8, color=color, lw=lw,
                                 linestyle=ls, shrinkA=0, shrinkB=0, zorder=1))


def header(x, top, w, title, sub, color, h=0.38):
    ax.add_patch(FancyBboxPatch((x, top - h), w, h, boxstyle="round,pad=0,rounding_size=0.05", linewidth=0, facecolor=color, zorder=2))
    ax.text(x + PADX, top - 0.12, title, ha="left", va="center", fontsize=9, fontweight="bold", color="white", zorder=3)
    ax.text(x + PADX, top - 0.29, sub, ha="left", va="center", fontsize=6.4, color="white", zorder=3)
    return top - h


X0, X1 = 0.4, W - 0.4

# ---- title ---------------------------------------------------------------------------------------------------------------
ax.text(X0, 8.15, "How a Trade Is Valued and Tested", fontsize=15, fontweight="bold", color=INK, va="center")
ax.text(X0, 7.9, "Every value is an expected or realized net present value, stated as a share of the 2025-26 salary cap. "
        "Every valuation uses only what was known on the trade date.", fontsize=7.6, color=MUTED, va="center")

# ---- the data --------------------------------------------------------------------------------------------------------
DATA = [("Wins above replacement (WAR)", "Patrick Bacon. Players; drafted players' seasons", BLUE),
        ("Contracts and cap hits", "PuckPedia, CapWages. Players; drafted players' costs", BLUE),
        ("Draft records and star probabilities", "The NHL; Bacon's draft model. Picks and prospects", ORANGE),
        ("Scoring outside the NHL", "Elite Prospects, put on one scale by Bacon's NHLe factors. Prospects", GREEN),
        ("The trade ledger", "CapFriendly to March 2022, PuckPedia to March 2026. Trades", PURPLE),
        ("Game Value", "The NHL's play-by-play and shift records, no input from WAR. Checks", INK)]
dg = 0.12
dw = (X1 - X0 - 5 * dg) / 6
dtop = 7.62
ax.text(X0, dtop + 0.1, "DATA", fontsize=6.6, fontweight="bold", color=LINE, va="center")
dh = max(lay(t, b, dw, 6.9, 6.1)[3] for t, b, _ in DATA)
for i, (t, b, c) in enumerate(DATA):
    dbot = box(X0 + i * (dw + dg), dtop, dw, t, b, color=c, fill=LIGHT.get(c), h=dh, ts=6.9, bs=6.1)

# ---- the three valuation columns: the player column is wider, having twice the steps -------------------------------------
G = 0.5                                       # gap between columns, holding the price-line connectors
cwP = 4.1
cwO = (X1 - X0 - cwP - 2 * G) / 2
cx, cws = [X0, X0 + cwP + G, X0 + cwP + G + cwO + G], [cwP, cwO, cwO]
htop = dbot - 0.2
for x, w, (t, sub, c) in zip(cx, cws, [("Players", "Valuing Players", BLUE), ("Draft picks", "Valuing Draft Picks", ORANGE),
                                       ("Prospects", "Valuing Prospects", GREEN)]):
    hbot = header(x, htop, w, t, sub, c)
VG = 0.12                                     # vertical gap between steps, holding an arrow


def column(x, w, steps, color, out_title, out_body):
    top, rects = hbot - 0.09, []
    for t, b in steps:
        bot = box(x, top, w, t, b, color=color)
        rects.append((top, bot))
        arrow(x + w / 2, bot, x + w / 2, bot - VG)
        top = bot - VG
    bot = box(x, top, w, out_title, out_body, color=color, fill=LIGHT[color], bold_box=True)
    return rects, bot


P = [("Own rate", "His WAR per 82 over his three most recent seasons, weighted 50/30/20, each weight times its games"),
     ("Comparable players and the starting level", "Players of his position and age most like him, weighted by similarity and mixed with the league average; blended 65% own rate, 35% comparable players"),
     ("Aging", "The starting level carried forward by his comparable players' changes from one age to the next"),
     ("Games share and chance of playing", "A regression for each season ahead; forecasted WAR is WAR per 82 times games share"),
     ("The price line", "A Tobit regression of cap hit on forecasted WAR, a defenceman interaction and contract length; each season priced, floored at the league minimum"),
     ("Contract value and the terminal value", "Each season's chance of playing times its price, less its cap hit, discounted 3% a year; plus the terminal value, the control seasons after the contract, each costing the qualifying offer or, from arbitration eligibility, the higher of it and his expected price")]
prects, pend = column(cx[0], cwP, P, BLUE, "Player xNPV", "Goaltenders: their own forecast and price line")
K = [("Drafted players' NPV over club control", "Each player drafted 2007-2017, priced from his draft to the end of club control on the player model's price line and costs"),
     ("The star value", "That NPV regressed, through zero, on the star probability for his draft position"),
     ("A traded pick's draft position", "Known when traded during its draft; from the standings once its season has started; otherwise its round's average star probability")]
krects, kend = column(cx[1], cwO, K, ORANGE, "Pick xNPV", "Star value times the star probability for its draft position")
R = [("Remaining NPV", "What each drafted prospect went on to deliver from that season to the end of club control, priced as for a drafted player"),
     ("The prospect model", "A regression for each season after the draft on draft position (D+1 to D+3), NHLe production and its square, an age discount on production (D+1 to D+4), and defenceman times production"),
     ("Goaltenders and undrafted players", "Goaltenders on draft position alone; an undrafted player on an NHL contract with a star probability of zero")]
rrects, rend = column(cx[2], cwO, R, GREEN, "Prospect xNPV", "From his draft position, production, age and position")

# the one currency: the player model's price line and costs price the drafted players behind the pick and prospect models
dash = (0, (3, 2))
ptop, pbot = prects[4]
y0, gx = (ptop + pbot) / 2, cx[0] + cwP + G / 2
ktop, kbot = krects[0]
y1 = ktop - 0.5 * min(ktop - kbot, rrects[0][0] - rrects[0][1])
ax.plot([cx[0] + cwP, gx, gx], [y0, y0, y1], color=BLUE, lw=1.0, ls=dash, zorder=1)
arrow(gx, y1, cx[1], y1, color=BLUE, ls=dash, lw=1.0)
ax.text(gx - 0.09, (y0 + y1) / 2, "price line and costs", rotation=90, fontsize=6.2, color=BLUE, ha="center", va="center", style="italic")
gx2 = cx[1] + cwO + G / 2
arrow(cx[1] + cwO, y1, cx[2], y1, color=BLUE, ls=dash, lw=1.0)
ax.text(gx2, y1 - 0.08, "priced\nthe same\nway", fontsize=6.0, color=BLUE, ha="center", va="top", style="italic")

# ---- the findings, from the foot of the page up ----------------------------------------------------------------------------
F = [("Realized NPV", "What each asset then delivered: the seasons played through 2025-26, priced at the same prices, plus the seasons from 2026-27 re-valued by the models", INK, None, False),
     ("The models predict trades", f"The club favoured on trade day came out ahead in {FAV:.1f}% of trades; the slope of realized NPV on trade-day xNPV is {SLOPE:.3f}", INK, None, False),
     ("The regression", "Each club's trade-day xNPV, and its realized NPV, on 23 difference variables (what it received less what it sent), under the main player and the any player rule", INK, None, False),
     ("What counts as a finding", "Statistically significant at the 5% level on both, with the same sign; then checked on Game Value, on the seasons played alone, and out of the regression sample", INK, None, False),
     ("What clubs overpay for", "A player with a contract clause, a player aged 28 to 31, and a defenceman", PURPLE, LIGHT[PURPLE], True),
     ("Clubs price about 40% of a contract", f"Two-stage least squares: about {100 * IV:.0f} cents per dollar of a contract's performance value", PURPLE, LIGHT[PURPLE], True)]
fg = 0.16
fw = (X1 - X0 - 5 * fg) / 6
fh = max(lay(t, b, fw)[3] for t, b, *_ in F)
fbot = 0.45
ftop = fbot + fh
fx = [X0 + i * (fw + fg) for i in range(6)]
for i, (t, b, c, fill, bold) in enumerate(F):
    box(fx[i], ftop, fw, t, b, color=c, fill=fill, bold_box=bold, h=fh)
    if 0 < i < 5:
        arrow(fx[i] - fg, fbot + fh / 2, fx[i], fbot + fh / 2)
ax.text(X0, ftop + 0.1, "FINDINGS", fontsize=6.6, fontweight="bold", color=LINE, va="center")
ax.text(X0, 0.24, "Sources and methods: Valuing Players, Valuing Draft Picks, Valuing Prospects, and Findings. "
        "Game Value is used only to check results that rest on WAR.", fontsize=6.3, color=LINE, va="center")

# ---- the trade on one scale, between the columns and the findings -----------------------------------------------------------
TT = "The trade on one scale (Valuing Prospects)"
TB = ("Each club's trade-day xNPV: the xNPV of what it received less what it gave up. Retained salary is charged to the club "
      "that kept it; an in-season trade counts the days left; a contract signed on the trade date is left out.")
tbot = ftop + 0.4
ttop = tbot + lay(TT, TB, X1 - X0)[3]
box(X0, ttop, X1 - X0, TT, TB, color=PURPLE, fill=LIGHT[PURPLE], bold_box=True)
assert min(pend, kend, rend) - ttop >= 0.15, ("the columns run into the trade box", min(pend, kend, rend), ttop)
for x, w, yend in zip(cx, cws, (pend, kend, rend)):
    arrow(x + w / 2, yend, x + w / 2, ttop, color=LINE)
arrow(fx[0] + fw / 2, tbot, fx[0] + fw / 2, ftop, color=LINE, ls=(0, (2, 2)))
ax.text(fx[0] + fw / 2 + 0.06, (tbot + ftop) / 2, "each asset followed", fontsize=6.0, color=MUTED, ha="left", va="center", style="italic")
arrow(fx[1] + fw / 2, tbot, fx[1] + fw / 2, ftop, color=PURPLE)
ax.text(fx[1] + fw / 2 + 0.06, (tbot + ftop) / 2, "trade-day xNPV", fontsize=6.0, color=PURPLE, ha="left", va="center", style="italic")

# ---- guards: every line of text inside its box, and no two boxes overlapping ---------------------------------------------------
fig.canvas.draw()
inv = ax.transData.inverted()
for t, (x, y, w, h) in PLACED:
    (a0, b0), (a1, b1) = inv.transform(t.get_window_extent(RND).get_points())
    assert a0 >= x and a1 <= x + w - 0.04 and b0 >= y + 0.02 and b1 <= y + h, ("text outside its box", t.get_text()[:40], (a0, b0, a1, b1), (x, y, w, h))
for i, (x, y, w, h) in enumerate(BOXES):
    for (x2, y2, w2, h2) in BOXES[i + 1:]:
        assert x + w <= x2 or x2 + w2 <= x or y + h <= y2 or y2 + h2 <= y, ("boxes overlap", (x, y), (x2, y2))
print(f"  guards: {len(PLACED)} text blocks inside their {len(BOXES)} boxes; no boxes overlap; "
      f"columns end {min(pend, kend, rend) - ttop:.2f} in above the trade box")

outdir = ROOT / "40_DOCS"
fig.savefig(outdir / "Method_Flow.pdf")
fig.savefig(outdir / "Method_Flow.png", dpi=200)
print(f"wrote {outdir / 'Method_Flow.pdf'} and .png")
