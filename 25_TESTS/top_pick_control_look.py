"""
top_pick_control_look.py -- what control over a top pick actually costs.

WHY (MODEL_DIRECTIVES.md directive 6; meeting 2026-10-09)
-------------------------------------------------------------------
The pick curve charges every drafted player the entry-level maximum, then a
chain of one-year qualifying offers (about $1M a season). For a top pick that
becomes a star this is too cheap: a star's club usually pays entry-level
bonuses and signs him long before his control runs out. The meeting agreed to
look at what control over a top pick is actually worth in the data: the top
10, with the top 15 as the test (Thomas). Picks 16-32 are shown beside them, so
we can tell whether any gap is special to the top. REPORT ONLY.

WHAT IT DOES
  1. PRICES each first-round skater (picks 1-32, classes 2007-2017) season by
     season exactly as pick_regression_first_look.py v1.1 does, and asserts that
     every pick's total equals that file's (reproduction guard).
  2. REPLACES the modelled cost of each NHL season in his window with his ACTUAL
     cap hit that season, from his CapWages page (contract tables by season,
     entry-level bonuses included). Value, the window, the zero for a season
     outside the NHL and the scaling of seasons under 10 games are unchanged.
     A season with no CapWages cap hit keeps the modelled cost (counted).
  3. REPORTS by pick range: coverage, modelled against actual cost, surplus both
     ways, and the pick curve's scale (surplus = b x Bacon's star chance, through
     zero, year indicators) refitted with actual costs for picks 1-10, then 1-15.

SOURCES
  * CapWages pages: the cached 10_SOURCE/capwages_cache/ (read only), and pages
    fetched now into OUTPUT_DIR/capwages_top_picks/ for first-round NHL players
    the cache lacks (capwages.com/players/<first-last>, the slug rule of
    capspace_capwages_compare.to_slug; 1.5 s between requests; user agent from
    .env SCRAPER_USER_AGENT). A page is used ONLY if its "Drafted" line names the
    same draft year and overall pick as the player (namesakes are refused).
  * WHICH CAP HIT (v1.1): from 2018-19 on, PuckPedia's (OUTPUT_DIR/
    contract_season_spine.csv, pp_cap_hit by NHL id and season), the project's
    contract source; CapWages before that, or where PuckPedia has none. A CapWages
    cap hit above that season's ceiling is refused as corrupt (v1.0 read Hampus
    Lindholm's 2017-22 seasons as $2,834,135,994, "3778.8%" of the cap; the same
    rows' average annual value is $5,205,556) and the season keeps its modelled
    cost (counted). Cap hit means CapWages' "Cap Hit" column: base salary and
    signing bonus, NOT entry-level performance bonuses (shown apart; they reach
    the cap only when earned, which the pages do not show).
  * CROSS-CHECK: where both sources have a season, the two cap hits are compared.

Run from the repo root:  python 25_TESTS/top_pick_control_look.py
"""

import html as htmlmod
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

SCRIPT_VERSION = "top_pick_control_look.py v1.1 (2026-10-09)"
load_dotenv()
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_CODE"))
import skater_forward_projection as sfp          # noqa: E402
import rfa_terminal_value as rtv                 # noqa: E402

SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])
CACHE_OLD = SOURCE_DIR / "capwages_cache"
CACHE_NEW = OUTPUT_DIR / "capwages_top_picks"
UA = os.environ.get("SCRAPER_USER_AGENT", "xnpv-model/1.0 (academic research)")
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
F = {"linkage": OUTPUT_DIR / "draft_pick_linkage.csv", "windows": OUTPUT_DIR / "draft_window_count.csv",
     "WAR": SOURCE_DIR / "WAR.csv", "first_look": OUTPUT_DIR / "pick_first_look_players.csv",
     "fl_log": OUTPUT_DIR / "pick_first_look_log.txt", "bacon": SOURCE_DIR / "draft_slot_baseline.csv",
     "pp_seasons": OUTPUT_DIR / "contract_season_spine.csv"}
for k, p in F.items():
    log(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")
assert F["fl_log"].read_text(encoding="utf-8").startswith("pick_regression_first_look.py v1.1")

# ---- pricing constants: identical to pick_regression_first_look.py v1.1 -------------
ALPHA, BETA_F, BETA_D, GAMMA, LINE = sfp.price_constants()
CAP = {2007: 50.3e6, 2008: 56.7e6, 2009: 56.8e6, 2010: 59.4e6, 2011: 64.3e6, 2012: 60.0e6, 2013: 64.3e6,
       2014: 69.0e6, **{y: sfp.CAP_CEILING[y] for y in range(2015, 2026)}}
LMIN = {2007: 475_000, 2008: 475_000, 2009: 500_000, 2010: 500_000, 2011: 525_000, 2012: 525_000,
        2013: 550_000, 2014: 550_000, **{y: sfp.league_min_path(y) for y in range(2015, 2026)}}
ELC_MAX = {**{y: 875_000 for y in (2007, 2008)}, **{y: 900_000 for y in (2009, 2010)},
           **{y: 925_000 for y in range(2011, 2018)}}
SHORT = {2012: 82 / 48, 2019: 82 / 70, 2020: 82 / 56}
CAP_NOW, CAMEO_GP, LAST_START = sfp.CAP_CEILING[2025], 10, 2025


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


def to_slug(name):
    """capspace_capwages_compare.to_slug: first-last lowercase ASCII."""
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    n = re.sub(r"[^A-Za-z\- ]", "", n).strip().lower()
    return re.sub(r"\s+", "-", n)


def page_text(raw):
    return htmlmod.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw)))


def drafted(txt):
    m = re.search(r"Drafted\s*:\s*(\d{4})\s+Rd\s+\d+\s+\(#(\d+)\)", txt)
    return (int(m.group(1)), int(m.group(2))) if m else None


def cap_hits(txt):
    """Season -> cap hit from the contract tables: 'YYYY-YY <clause> $cap  pct% $aav ...'.
    Returns (dict, number of seasons listed with two different cap hits)."""
    out, clash = {}, 0
    for s, cap in re.findall(r"(\d{4})-\d{2} \S+ \$([\d,]+) [\d.]+% \$[\d,]+", txt):
        y, v = int(s), float(cap.replace(",", ""))
        if y in out and out[y] != v:
            clash += 1
            continue                                  # keep the first listed (the contract table order)
        out.setdefault(y, v)
    return out, clash


# index the cached pages by (draft year, overall pick)
pages = {}
for d_ in (CACHE_OLD, CACHE_NEW):
    if d_.exists():
        for f in d_.glob("*.html"):
            t = page_text(f.read_text(encoding="utf-8", errors="ignore"))
            k = drafted(t)
            if k:
                pages.setdefault(k, (f, t))
log(f"  CapWages pages with a draft line: {len(pages):,}")

# ---- the first-round skaters, priced as the first look prices them --------------------
link = pd.read_csv(F["linkage"], parse_dates=["birthDate"])
win = pd.read_csv(F["windows"])
fl = pd.read_csv(F["first_look"])
p = link[link["draftYear"].between(2007, 2017) & ~link["is_goalie"].astype(bool)].merge(
    win[["draftYear", "overall", "end_g3"]], left_on=["draftYear", "overallPickNumber"],
    right_on=["draftYear", "overall"], validate="one_to_one")
p = p[p["end_g3"].notna() & (p["link_status"] != "excluded_merged_name")]
p = p.merge(fl[["draftYear", "pick", "surplus"]], left_on=["draftYear", "overallPickNumber"],
            right_on=["draftYear", "pick"], validate="one_to_one")   # all picks: the curve refit needs them

war = pd.read_csv(F["WAR"], usecols=["Player", "Season", "GP", "WAR"])
war["name_n"] = war["Player"].map(norm)
war["start"] = war["Season"].map(lambda s: 2000 + int(str(s)[:2]))
war = war.groupby(["name_n", "start"])[["GP", "WAR"]].sum()


def seasons_of(row):
    if pd.isna(row["war_names"]):
        return pd.DataFrame(columns=["GP", "WAR"])
    parts = [war.loc[n] for n in {norm(x) for x in str(row["war_names"]).split("|")}
             if n in war.index.get_level_values(0)]
    if not parts:
        return pd.DataFrame(columns=["GP", "WAR"])
    s = pd.concat(parts).groupby(level=0).sum()
    return s[s.index >= row["draftYear"]]


def season_rows(row):
    """One row per season priced, with the first look's value and modelled cost (cap shares)."""
    s = seasons_of(row)
    beta = BETA_D if row["position"] == "D" else BETA_F
    last = min(int(row["end_g3"]) - 1, LAST_START)
    played = s[(s["GP"] > 0) & (s.index <= last)]
    if played.empty:
        return []
    first = int(played.index.min())
    age = (pd.Timestamp(first, 9, 15) - row["birthDate"]).days / 365.25 if pd.notna(row["birthDate"]) else 19
    n_elc = 3 if int(age) <= 21 else 2 if int(age) <= 23 else 1
    elc_done, prior, out = 0, None, []
    for y in range(int(row["draftYear"]), last + 1):
        gp = float(s.loc[y, "GP"]) if y in s.index else 0.0
        wins = float(s.loc[y, "WAR"]) * SHORT.get(y, 1.0) if y in s.index else 0.0
        in_elc = elc_done < n_elc and gp > 0
        if not in_elc and elc_done >= n_elc:
            prior = rtv.qualifying_offer(prior or ELC_MAX[row["draftYear"]], prior or ELC_MAX[row["draftYear"]],
                                         y, False)
        if gp == 0:
            continue
        scale = gp / 82 if gp < CAMEO_GP else 1.0
        value = max(ALPHA + beta * wins + GAMMA * 1, LMIN[y] / CAP[y]) * scale
        cost = (ELC_MAX[row["draftYear"]] if in_elc else prior) / CAP[y] * scale
        out.append({"season": y, "gp": gp, "in_elc": in_elc, "scale": scale, "value": value,
                    "cost_model": cost, "model_cost_$": (ELC_MAX[row["draftYear"]] if in_elc else prior)})
        if in_elc and gp >= CAMEO_GP:
            elc_done += 1
    return out


# ---- fetch missing CapWages pages for first-round NHL players -----------------------------
CACHE_NEW.mkdir(exist_ok=True)
sess, fetched, refused = requests.Session(), 0, []
first_round = p[p["overallPickNumber"] <= 32]
for r in first_round.itertuples():
    key = (r.draftYear, r.overallPickNumber)
    if key in pages or not season_rows(r._asdict()):
        continue
    slug = to_slug(r.playerName)
    f = CACHE_NEW / f"{slug}.html"
    if not f.exists():
        try:
            resp = sess.get(f"https://capwages.com/players/{slug}", headers={"User-Agent": UA}, timeout=20)
        except requests.RequestException as e:
            refused.append(f"{r.draftYear}#{r.overallPickNumber} {r.playerName}: {type(e).__name__}")
            continue
        time.sleep(1.5)
        if resp.status_code != 200:
            refused.append(f"{r.draftYear}#{r.overallPickNumber} {r.playerName}: HTTP {resp.status_code}")
            continue
        f.write_text(resp.text, encoding="utf-8")
        fetched += 1
    t = page_text(f.read_text(encoding="utf-8", errors="ignore"))
    if drafted(t) != key:                             # GUARD: a namesake's page is refused
        refused.append(f"{r.draftYear}#{r.overallPickNumber} {r.playerName}: page drafted {drafted(t)}")
        continue
    pages[key] = (f, t)
log(f"  fetched {fetched} pages into {CACHE_NEW}; not usable: {len(refused)}")
for x in refused:
    log(f"     {x}")

# ---- price every pick both ways ------------------------------------------------------------
pp = pd.read_csv(F["pp_seasons"], usecols=["nhl_id", "season_start", "pp_cap_hit"]).dropna()
pp = pp.groupby(["nhl_id", "season_start"])["pp_cap_hit"].max().to_dict()
rows, xcheck, clashes, corrupt = [], [], 0, []
src = {"PuckPedia": 0, "CapWages": 0, "modelled (no cap hit)": 0}
for r in p.itertuples():
    d = r._asdict()
    sr = season_rows(d)
    total_model = sum(x["value"] - x["cost_model"] for x in sr) * CAP_NOW
    assert abs(total_model - r.surplus) < 1.0, (r.playerName, total_model, r.surplus)   # reproduction guard
    have_page = (r.draftYear, r.overallPickNumber) in pages
    caps, c = cap_hits(pages[(r.draftYear, r.overallPickNumber)][1]) if have_page else ({}, 0)
    clashes += c
    cost_act, n_act = 0.0, 0
    for x in sr:
        y = x["season"]
        cw = caps.get(y)
        if cw is not None and cw > CAP[y]:
            corrupt.append(f"{r.draftYear}#{r.overallPickNumber} {r.playerName} {y}: ${cw:,.0f}")
            cw = None                                 # GUARD: a cap hit above the ceiling is not a cap hit
        pv = pp.get((int(r.playerId), y)) if (pd.notna(r.playerId) and y >= 2018) else None
        if cw is not None and pv is not None:
            xcheck.append((cw, pv))
        act = pv if pv is not None else cw            # PuckPedia first from 2018-19, else CapWages
        if act is not None:
            cost_act += act / CAP[y] * x["scale"]
            n_act += 1
            src[("PuckPedia" if pv is not None else "CapWages")] += 1
        else:
            cost_act += x["cost_model"]
            src["modelled (no cap hit)"] += 1
    value = sum(x["value"] for x in sr)
    rows.append({"draftYear": r.draftYear, "pick": r.overallPickNumber, "player": r.playerName,
                 "nhl_seasons": len(sr), "seasons_actual": n_act, "page": have_page,
                 "value_$M": value * CAP_NOW / 1e6,
                 "cost_model_$M": sum(x["cost_model"] for x in sr) * CAP_NOW / 1e6,
                 "cost_actual_$M": cost_act * CAP_NOW / 1e6,
                 "surplus_model_$M": r.surplus / 1e6,
                 "surplus_actual_$M": (value - cost_act) * CAP_NOW / 1e6})
t = pd.DataFrame(rows)
log(f"  reproduction guard: every pick's modelled surplus equals the first look's ({len(t):,} picks)")
log(f"  seasons with two different cap hits on one page (first kept): {clashes}")
log(f"  CapWages cap hits refused as above the ceiling: {len(corrupt)}" + (": " + "; ".join(corrupt[:8]) if corrupt else ""))
log(f"  cost source, NHL seasons of all picks: {src}")
xc = np.array(xcheck)
if len(xc):
    gap = np.abs(xc[:, 0] - xc[:, 1])
    log(f"  CROSS-CHECK CapWages vs PuckPedia, 2018-19 on: {len(xc)} player-seasons; within $1,000: "
        f"{int((gap <= 1000).sum())}; within 10%: {int((gap <= 0.1 * xc[:, 1]).sum())}; "
        f"largest gaps: {', '.join(f'${a:,.0f} vs ${b:,.0f}' for a, b in xc[np.argsort(-gap)[:4]])}")

# ---- results by pick range -------------------------------------------------------------------
log("\nFIRST ROUND, NHL players (2025-26 dollars, $M a pick, over each player's control window)")
out = []
for lo, hi in ((1, 10), (11, 15), (16, 32)):
    g = t[t["pick"].between(lo, hi) & (t["nhl_seasons"] > 0)]
    out.append({"picks": f"{lo}-{hi}", "NHL players": len(g), "with a page": int(g["page"].sum()),
                "NHL seasons": int(g["nhl_seasons"].sum()), "seasons with actual cap hit": int(g["seasons_actual"].sum()),
                "value": g["value_$M"].mean(), "cost modelled": g["cost_model_$M"].mean(),
                "cost actual": g["cost_actual_$M"].mean(), "surplus modelled": g["surplus_model_$M"].mean(),
                "surplus actual": g["surplus_actual_$M"].mean()})
log(pd.DataFrame(out).round(2).to_string(index=False))

top = t[t["pick"] <= 15].assign(gap=lambda x: x["cost_actual_$M"] - x["cost_model_$M"]).nlargest(12, "gap")
log("\nlargest gaps, actual minus modelled cost ($M):")
log(top[["draftYear", "pick", "player", "nhl_seasons", "seasons_actual", "value_$M", "cost_model_$M",
         "cost_actual_$M"]].round(2).to_string(index=False))

# ---- the curve's scale, refitted -------------------------------------------------------------
bacon = pd.read_csv(F["bacon"]).set_index("draft_pick")["p_star"]
allp = fl.merge(t[["draftYear", "pick", "surplus_actual_$M"]], on=["draftYear", "pick"], how="left")
allp["p_star"] = allp["pick"].map(bacon)
CL = sorted(allp["draftYear"].unique())


def scale_b(y):
    X = np.zeros((len(allp), len(CL) - 1))
    for j, c in enumerate(CL[:-1]):
        X[:, j] = (allp["draftYear"].values == c)
    X[allp["draftYear"].values == CL[-1], :] = -1
    b, *_ = np.linalg.lstsq(np.column_stack([allp["p_star"].values, X]), y, rcond=None)
    return b[0]


base = scale_b(allp["surplus"].values / 1e6)
log(f"\nPICK CURVE SCALE ($M per 100% star chance; through zero, year indicators): adopted {base:.2f}")
for hi in (10, 15):
    y = np.where(allp["pick"] <= hi, allp["surplus_actual_$M"], allp["surplus"] / 1e6)
    b = scale_b(y)
    vals = ", ".join(f"#{k} ${b * bacon[k]:.2f}M (was ${base * bacon[k]:.2f}M)" for k in (1, 5, 10, 15, 20, 32))
    log(f"  actual costs for picks 1-{hi}: {b:.2f} ({100 * (b / base - 1):+.1f}%); {vals}")

t.to_csv(OUTPUT_DIR / "top_pick_control_look.csv", index=False)
(OUTPUT_DIR / "top_pick_control_look_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote top_pick_control_look.csv and its log in {OUTPUT_DIR}")
