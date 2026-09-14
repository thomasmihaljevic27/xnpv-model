"""
=============================================================================
 player_dashboard.py   v1.1                        Viewer tool (2026-09-13)
=============================================================================
 v1.1 (2026-09-13): the 2026-27 page, and extensions from their signing
 date. A page is valued as of July 1 of its season (contract_npv v1.4
 includes every extension signed by then). An extension signed LATER in
 the season changes what the team holds from that day, so the page gets
 an in-season variant valued with as_of = the signing date, stored under
 the page's "v" list with its "from" date. The template shows the latest
 variant already signed on the selected date. Both the base page and
 every variant pass guard (b); guard (a) applies to the base page, which
 is the one the panel stores.
=============================================================================
 WHAT THIS PRODUCES (plain English)
 ----------------------------------
 One self-contained HTML page, 30_OUTPUT/player_dashboard.html, that opens
 in any browser with no server and no internet connection. Pick a player
 and a date; the page shows:

   * the player's xNPV across every valuation page he has (a step line),
   * the Bacon WAR seasons underneath it, with the seasons the selected
     page actually reads highlighted,
   * bio, draft position, contract history and trade history,
   * the season-by-season build-up of the selected page's xNPV
     (projected WAR, value, cost, survival, discount, present value).

 Clicking a contract or a trade jumps the date to the signing / trade date
 and shows the valuation the model could make with the information
 available on that day.

 CONFIDENTIALITY (read this)
 ---------------------------
 The page EMBEDS PuckPedia contract and trade data, which is confidential
 vendor data. It is written to 30_OUTPUT/, which is gitignored. Do not
 commit it, upload it, publish it, or send it anywhere. This script holds
 no data itself and is safe to commit.

 WHERE THE xNPV LINE COMES FROM
 ------------------------------
 contract_npv_panel.csv -- the validation panel. For every league-year t0
 from 2018 to 2026, the panel values every contract active that season
 using only information available before it. Each "page" is therefore a
 clean ex-ante valuation; the sequence of pages is a diagnostic of how the
 model's view updates, NOT a back-test input (see contract_npv_panel.py).

 THE DATE RULE (the model's clock ticks once per season)
 -------------------------------------------------------
 A page for season t0 reads trailing seasons only (t0-1 / t0-2 for skaters;
 the 50/30/20 cascade over t0-1..t0-3 for goalies). All of those seasons
 are complete by July 1 of t0. So a date d uses:

     page = d.year      if d is on or after July 1
     page = d.year - 1  otherwise

 i.e. the latest page whose inputs were all known on d. Within that page,
 the variant in force is the latest one whose extension was signed on or
 before d (v1.1). A February trade
 therefore uses the page built at the start of that season, which ignores
 the half-season already played. That is conservative (no look-ahead) and
 is a documented gap: mid-season proration is Phase 4a-ii, not built.

 REPRODUCTION GUARD
 ------------------
 The panel stores totals only. To show the per-season build-up, this
 script re-runs the SAME engine (contract_npv.NPVEngine.npv) for every
 page and refuses to write the page unless
   (a) the engine's npv_total matches the panel's within $1, and
   (b) the per-season present values sum to that total within $1.
 If (a) fails, the panel is stale relative to the code: re-run
 contract_npv_panel.py first.

 USAGE (from the repo root):   python 20_CODE/player_dashboard.py
 Then open 30_OUTPUT/player_dashboard.html in a browser.
=============================================================================
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

# The engine is imported, never re-implemented, so the breakdown shown in
# the page can never drift from the panel's pricing.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from contract_npv import NPVEngine                      # noqa: E402
from skater_forward_projection import norm_name, page_date   # noqa: E402

SCRIPT_VERSION = "player_dashboard.py v1.1 (2026-09-13)"

load_dotenv()
SOURCE_DIR = Path(os.environ["SOURCE_DIR"])
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
CODE_DIR = Path(__file__).resolve().parent

F_PANEL      = OUTPUT_DIR / "contract_npv_panel.csv"
F_LEVEL      = OUTPUT_DIR / "contract_level_spine.csv"
F_DRAFT      = OUTPUT_DIR / "draft_pick_linkage.csv"
F_WAR_AGE    = OUTPUT_DIR / "WAR_with_age.csv"
F_GOALIE_WAR = SOURCE_DIR / "Goalies_WAR.csv"
F_PP_CONTRACTS = Path(os.environ["PUCKPEDIA_CONTRACTS_XLSX"])
F_PP_TRADES    = Path(os.environ["PUCKPEDIA_TRADES_XLSX"])
F_TEMPLATE   = CODE_DIR / "player_dashboard_template.html"
OUT_HTML     = OUTPUT_DIR / "player_dashboard.html"

GUARD_TOL = 1.0          # dollars; the guard tolerance for (a) and (b)
PLACEHOLDER = "/*__XNPV_DATA__*/null"


def log(msg=""):
    print(msg)


def clean(v):
    """NaN / numpy scalars -> JSON-safe Python values."""
    if v is None:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, pd.Timestamp):
        return None if pd.isna(v) else v.strftime("%Y-%m-%d")
    if isinstance(v, str):
        return v
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v


def rint(v):
    v = clean(v)
    return None if v is None else int(round(v))


def rnd(v, n):
    v = clean(v)
    return None if v is None else round(v, n)


# ---------------------------------------------------------------------------
# 1. Valuation pages: panel totals + engine re-run for the per-season detail
# ---------------------------------------------------------------------------
def build_pages():
    panel = pd.read_csv(F_PANEL)
    log(f"panel rows: {len(panel):,}  players: {panel['player_id'].nunique():,}")

    # Duplicate player-season pages: two contract_ids valuing the same player
    # in the same season (retention-split legs / duplicate contract records).
    # They are only safe to collapse if they carry the same value -- guard it.
    grp = panel.groupby(["player_id", "valuation_season"])["npv_total"]
    spread = grp.max() - grp.min()
    if (spread > GUARD_TOL).any():
        bad = spread[spread > GUARD_TOL]
        raise SystemExit(f"GUARD FAILED: {len(bad)} player-season pages carry "
                         f"conflicting values, cannot collapse:\n{bad.head()}")
    n_dup = int((grp.size() > 1).sum())
    pages_df = (panel.sort_values("contract_id")
                .drop_duplicates(["player_id", "valuation_season"]))
    log(f"duplicate player-season pages collapsed (identical values): {n_dup}")

    eng = NPVEngine()

    def page_dict(d, s, r):
        """One valuation page (or in-season variant) as the template reads it."""
        # guard (b): the rows shown in the breakdown add up to the total
        if abs(d["pv_dollars"].sum() - s["npv_total"]) > GUARD_TOL:
            raise SystemExit(f"GUARD FAILED: {r.full_name} {int(r.valuation_season)} "
                             f"(as of {s['as_of']}): detail rows do not sum to npv_total.")
        first = d[d["row_type"] == "contract"].iloc[0]
        # the contract the ENGINE is playing out on this page (skater and
        # goalie branches both carry contract_id on every contract row)
        cid = int(first["contract_id"])
        rows = [[int(x.season_start), int(x.k),
                 # C = contract being played, E = signed extension (v1.1),
                 # T = RFA control year at the qualifying offer
                 ("T" if x.row_type != "contract"
                  else "C" if int(x.contract_id) == cid else "E"),
                 rnd(x.projected_war, 3), rint(x.value_dollars),
                 rint(x.cost_dollars), rnd(x.survival, 4),
                 rnd(x.discount, 4), rint(x.pv_dollars)]
                for x in d.itertuples(index=False)]
        return {
            "npv": rint(s["npv_total"]),
            "c": rint(s["npv_contract"]),
            "t": rint(s["npv_terminal"]),
            "path": s.get("path", ""),
            "rem": int(s["n_contract_seasons"]),     # includes extension seasons
            "elc": bool(r.is_elc_season),
            "cid": cid,
            "ext": [int(c) for c in s["chain"][1:]],  # extensions included
            "age": rint(first.get("age_at_valuation")),     # skaters only
            "anchor": rnd(first.get("anchor_war"), 3),      # skaters only
            "src": clean(first.get("anchor_source")),       # skaters only
            "rows": rows,
        }

    # v1.1 in-season variants: which of a player's later contracts were
    # signed inside a page's window, i.e. after July 1 of t0 and before
    # July 1 of t0+1. Keyed on contract_id; first season from both spines.
    cols = ["player_id", "contract_id", "season_start"]
    spine_all = pd.concat([eng.sp.spine[cols], eng.gp_spine[cols]])
    first_season = spine_all.groupby("contract_id")["season_start"].min()
    contracts_of = spine_all.groupby("player_id")["contract_id"].unique()
    signed = eng.sp.signed

    pages, n_var = {}, 0
    for r in pages_df.itertuples(index=False):
        pid, t0 = int(r.player_id), int(r.valuation_season)
        d, s = eng.npv(pid, t0)                  # as of July 1 of t0
        # guard (a): the engine still prices this page the way the panel did
        if s.get("status") != "ok":
            raise SystemExit(f"GUARD FAILED: panel page {r.full_name} {t0} "
                             f"is no longer priced ({s.get('status')}). "
                             "Re-run contract_npv_panel.py.")
        if abs(s["npv_total"] - r.npv_total) > GUARD_TOL:
            raise SystemExit(f"GUARD FAILED: {r.full_name} {t0}: engine "
                             f"{s['npv_total']:,.0f} vs panel {r.npv_total:,.0f}."
                             " The panel is stale -- re-run contract_npv_panel.py.")
        base = page_dict(d, s, r)

        lo, hi = page_date(t0), page_date(t0 + 1)
        dates = sorted({signed[int(c)] for c in contracts_of.get(pid, [])
                        if first_season[c] > t0
                        and pd.notna(signed.get(int(c), pd.NaT))
                        and lo < signed[int(c)] < hi})
        chain_prev, variants = s["chain"], []
        for dt in dates:
            dv, sv_ = eng.npv(pid, t0, as_of=dt)
            # a signing that does not extend the chain (e.g. a contract that
            # starts after a gap) leaves the page unchanged: no variant
            if sv_.get("status") != "ok" or sv_["chain"] == chain_prev:
                continue
            pv = page_dict(dv, sv_, r)
            pv["from"] = dt.date().isoformat()
            variants.append(pv)
            chain_prev = sv_["chain"]
        if variants:
            base["v"] = variants
            n_var += len(variants)
        pages.setdefault(pid, {})[t0] = base
    log(f"pages re-run through the engine and matched the panel: "
        f"{sum(len(v) for v in pages.values()):,}")
    log(f"in-season extension variants added: {n_var:,}")
    names = (pages_df.drop_duplicates("player_id")
             .set_index("player_id")[["full_name", "position"]])
    return pages, names, n_dup


# ---------------------------------------------------------------------------
# 2. Bio + contracts (PuckPedia export joined to the contract-level spine)
# ---------------------------------------------------------------------------
def build_bio_contracts(pids):
    pp = pd.read_excel(F_PP_CONTRACTS)
    ls = pd.read_csv(F_LEVEL)

    # contract_id is the join key; the export is one row per contract
    assert pp["contract_id"].is_unique, "PuckPedia export: duplicate contract_id"
    pp["signing_date"] = pd.to_datetime(pp["signing_date"], errors="coerce")

    # start_season_year comes from the SPINE, not the export's `season`
    # column: PuckPedia stores the first season for completed contracts and
    # the last season for active long deals (the true_start_year correction).
    c = ls.merge(pp[["contract_id", "signing_date", "signing_status",
                     "contract_level", "value", "short_code.1"]],
                 on="contract_id", how="left")
    c = c[c["player_id"].isin(pids)]

    contracts, team_now = {}, {}
    for pid, g in c.sort_values("start_season_year").groupby("player_id"):
        lst = []
        for r in g.itertuples(index=False):
            lst.append({
                "id": int(r.contract_id),
                "start": rint(r.start_season_year),
                "len": rint(r.pp_length),
                "cap": rint(r.pp_cap_hit),
                "aav": rint(r.pp_aav),
                "value": rint(r.value),
                "signed": clean(r.signing_date),
                "sstatus": clean(r.signing_status),
                "level": clean(r.contract_level),
                "expiry": clean(r.pp_expiry),
                "clause": clean(r.clause_most_restr_type),
                "team": None,     # filled from short_code.1 just below
            })
        # itertuples renames the dotted column "short_code.1", so read the
        # team codes off the frame directly, in the same row order
        teams = g["short_code.1"].tolist()
        for item, tm in zip(lst, teams):
            item["team"] = clean(tm)
        contracts[int(pid)] = lst
        team_now[int(pid)] = clean(teams[-1])

    bio = {}
    first = pp.sort_values("contract_id").drop_duplicates("player_id").set_index("player_id")
    nhl_ids = ls.drop_duplicates("player_id").set_index("player_id")["nhl_id"]
    for pid in pids:
        if pid not in first.index:
            continue
        r = first.loc[pid]
        bio[int(pid)] = {
            "first": clean(r["first_name"]), "last": clean(r["last_name"]),
            "pos": clean(r["position"]), "born": clean(pd.to_datetime(r["birthdate"], errors="coerce")),
            "height": rint(r["height"]), "weight": rint(r["weight"]),
            "shoots": clean(r["shoots"]), "city": clean(r["city.1"]),
            "state": clean(r["state_province"]), "country": clean(r["country"]),
            "jersey": rint(r["jersey_number"]), "ufa": rint(r["ufa_year"]),
            "draft_year": rint(r["draft_year"]),
            "team": team_now.get(int(pid)),
            "nhl_id": rint(nhl_ids.get(pid)),
        }
    log(f"bio rows: {len(bio):,}  players with contracts: {len(contracts):,}")
    return bio, contracts


# ---------------------------------------------------------------------------
# 3. Draft position (NHL Records linkage, keyed on NHL id)
# ---------------------------------------------------------------------------
def build_draft(bio):
    dl = pd.read_csv(F_DRAFT)
    dl = dl[dl["playerId"].notna()]
    by_nhl = {}
    for r in dl.itertuples(index=False):
        by_nhl.setdefault(int(r.playerId), []).append({
            "year": int(r.draftYear), "round": int(r.roundNumber),
            "overall": int(r.overallPickNumber), "team": clean(r.triCode)})
    out = {pid: by_nhl[b["nhl_id"]] for pid, b in bio.items()
           if b.get("nhl_id") in by_nhl}
    log(f"players linked to a draft record (2005-2026 linkage): {len(out):,}")
    return out


# ---------------------------------------------------------------------------
# 4. WAR history (display only -- same provider, Bacon, as every input)
# ---------------------------------------------------------------------------
def season_start(s):
    # "16-17" -> 2016. WAR.csv starts in 2007-08, so no 1900s seasons occur.
    return 2000 + int(str(s)[:2])


def build_war(names):
    war = {}
    # Skaters: WAR_with_age carries the PuckPedia player_id from age_join.py.
    # Team-halves of a traded season are summed (same rule as item 1.5).
    w = pd.read_csv(F_WAR_AGE)
    w["ss"] = w["Season"].map(season_start)
    w["nk"] = w["Player"].map(norm_name)
    by_id = (w[w["player_id"].notna()]
             .groupby(["player_id", "ss"])[["WAR", "GP"]].sum().reset_index())
    for r in by_id.itertuples(index=False):
        pid = int(r.player_id)
        if pid in names.index:
            war.setdefault(pid, {})[int(r.ss)] = [round(r.WAR, 3), int(r.GP)]
    # Fallback for panel skaters with no id-matched WAR: cleaned-name match,
    # accepted only where the name is unique among panel players.
    pn = names.assign(nk=names["full_name"].map(norm_name))
    uniq = pn[~pn["nk"].duplicated(keep=False)]
    nk_to_pid = {nk: int(pid) for pid, nk in uniq["nk"].items()}
    by_nk = w.groupby(["nk", "ss"])[["WAR", "GP"]].sum().reset_index()
    n_fallback = 0
    for r in by_nk.itertuples(index=False):
        pid = nk_to_pid.get(r.nk)
        if pid is None or pid in war and int(r.ss) in war[pid]:
            continue
        if names.loc[pid, "position"] != "skater":
            continue
        if pid in war and war[pid].get("_src") != "name":
            continue          # id-matched player: never mix in name matches
        war.setdefault(pid, {"_src": "name"})[int(r.ss)] = [round(r.WAR, 3), int(r.GP)]
        n_fallback += 1

    # Goalies: Goalies_WAR has names only -- match on the cleaned name, with
    # the same uniqueness rule, exactly as the goalie engine keys on nname.
    gw = pd.read_csv(F_GOALIE_WAR)
    gw["ss"] = gw["Season"].map(season_start)
    gw["nk"] = gw["Goalie"].map(norm_name)
    gg = gw.groupby(["nk", "ss"])[["WAR", "GP"]].sum().reset_index()
    for r in gg.itertuples(index=False):
        pid = nk_to_pid.get(r.nk)
        if pid is None or names.loc[pid, "position"] != "goalie":
            continue
        war.setdefault(pid, {"_src": "name"})[int(r.ss)] = [round(r.WAR, 3), int(r.GP)]

    out = {}
    for pid, d in war.items():
        src = d.pop("_src", "id")
        out[pid] = {"src": src, "s": {str(k): v for k, v in sorted(d.items())}}
    log(f"players with a WAR history: {len(out):,} "
        f"(skater name-fallback season rows: {n_fallback:,})")
    return out


# ---------------------------------------------------------------------------
# 5. Trades (PuckPedia trades export)
# ---------------------------------------------------------------------------
def build_trades(pids):
    t = pd.read_excel(F_PP_TRADES)
    t["date"] = pd.to_datetime(t["trade_date"], format="%m/%d/%Y", errors="coerce")
    # A multi-team trade is several trade_ids sharing one linked_trade_id
    # (e.g. the 2020-02-24 Lehner three-way: trade_ids 254/256/257, link 4).
    t["g"] = np.where(t["linked_trade_id"].notna(),
                      "L" + t["linked_trade_id"].fillna(0).astype(int).astype(str),
                      "T" + t["trade_id"].astype(int).astype(str))

    groups, legs = {}, {}
    for g, gg in t.groupby("g"):
        assets = []
        seen = set()
        for r in gg.itertuples(index=False):
            key = (r.from_team, r.to_team, r.player_id, r.draft_pick_id)
            if key in seen:
                continue
            seen.add(key)
            a = {"from": clean(r.from_team), "to": clean(r.to_team),
                 "date": clean(r.date)}
            if pd.notna(r.player_id):
                # str(): read_excel turns a surname like "True" into a bool
                nm = " ".join(str(x) for x in [clean(r.first_name), clean(r.last_name)]
                              if x is not None)
                a.update({"k": "P", "pid": int(r.player_id),
                          "name": nm or f"player #{int(r.player_id)} (no name in export)",
                          "cap": rint(r.cap_hit), "ret": rint(r.retained_hit)})
            else:
                a.update({"k": "D", "year": rint(r.draft_year),
                          "round": rint(r.draft_round),
                          "overall": rint(r.overall_position),
                          "orig": clean(r.draft_pick_team),
                          "cond": clean(r.draft_pick_conditions)})
            assets.append(a)
        details = [d for d in gg["details"].dropna().unique().tolist()]
        groups[g] = {"date": clean(gg["date"].min()), "details": details,
                     "assets": assets}

    mine = t[t["player_id"].isin(pids)]
    # same-day legs of a multi-team deal list in trade_id order (Lehner:
    # CHI->TOR is 254, TOR->VGK is 256), which is the order they happened
    for r in mine.sort_values(["date", "trade_id"]).itertuples(index=False):
        legs.setdefault(int(r.player_id), []).append({
            "g": r.g, "date": clean(r.date), "from": clean(r.from_team),
            "to": clean(r.to_team), "cap": rint(r.cap_hit),
            "ret": rint(r.retained_hit)})
    used = {l["g"] for v in legs.values() for l in v}
    groups = {g: v for g, v in groups.items() if g in used}
    log(f"trade legs for panel players: {sum(len(v) for v in legs.values()):,} "
        f"across {len(groups):,} trades")
    return groups, legs


# ---------------------------------------------------------------------------
# 6. Assemble and write
# ---------------------------------------------------------------------------
def main():
    log(SCRIPT_VERSION)
    log("=" * 74)
    pages, names, n_dup = build_pages()
    pids = list(pages.keys())
    bio, contracts = build_bio_contracts(pids)
    draft = build_draft(bio)
    war = build_war(names)
    trades, legs = build_trades(pids)

    players = {}
    for pid in pids:
        b = bio.get(pid, {})
        name = (f"{b.get('first','')} {b.get('last','')}".strip()
                or names.loc[pid, "full_name"])
        players[str(pid)] = {
            "name": name, "grp": names.loc[pid, "position"],
            "bio": b, "draft": draft.get(pid, []),
            "contracts": contracts.get(pid, []),
            "trades": legs.get(pid, []),
            "war": war.get(pid),
            "pages": {str(k): v for k, v in sorted(pages[pid].items())},
        }

    all_t0 = sorted({t for v in pages.values() for t in v})
    data = {
        "meta": {"version": SCRIPT_VERSION,
                 "built": datetime.now().strftime("%Y-%m-%d %H:%M"),
                 "first": all_t0[0], "last": all_t0[-1],
                 "n_players": len(players), "n_dup_collapsed": n_dup},
        "players": players,
        "trades": trades,
    }

    blob = json.dumps(data, separators=(",", ":"), ensure_ascii=True)
    blob = blob.replace("</", "<\\/")      # never close the <script> early
    html = F_TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in html:
        raise SystemExit("template placeholder missing")
    OUT_HTML.write_text(html.replace(PLACEHOLDER, blob), encoding="utf-8")
    log(f"wrote {OUT_HTML}  ({OUT_HTML.stat().st_size/1e6:.1f} MB)")
    log("CONFIDENTIAL: embeds PuckPedia data. Keep local; do not commit or share.")


if __name__ == "__main__":
    main()
