"""
traded_player_values.py -- every traded player the player model can value, valued at his trade's page (2018-19 on).

The counterpart of page_2017_values.py (the 2017 page, on CapWages contracts) for the pages PuckPedia covers. Until
now a traded player's value at his trade was read off contract_npv_panel (a validation exhibit valued as of July 1
of each page). This values each traded asset directly, on the engine the panel uses:

  NPVEngine.npv(player, page, as_of)
  * page = trade_page.page(trade date) (Thomas, 2026-10-14: a trade after its season's last regular-season game is
    valued on the next season's page);
  * as_of = the trade date when it falls inside the page's window (July 1 of the page to June 30 after), so the
    contracts and extensions the club held on that date are the ones valued; for a post-season trade (valued on the
    next page) the window starts after the trade, so as_of is the page date, July 1, and every contract signed
    between the trade and that July 1 is LISTED (it was known to the page, not to the trade).
  * THE SEASON LEFT AND RETAINED SALARY (v1.2, Thomas 2026-10-19): a trade during the regular season counts only the
    share of that season's days left (trade_page.season_left_share), for value and cap hit alike; the acquirer pays
    (1 - retained share) of the retained contract's cap hit (trades.db retention_pct; the contract being played only),
    and retained_pv records what the retaining club pays (positive dollars, at the page's cap).
  * RIGHTS ONLY (v1.1, every trade; v1.0 post-season trades only): when the contract the page would value was signed
    after the trade, the club acquired his rights, not that contract. Status "rights only (...)", valued by
    rights_values.py (RFA: his control seasons from the page; UFA: zero).
  * the player: his NHL id (prospect_values.csv's identities: PuckPedia ids, the drafted match, the undrafted path),
    to PuckPedia's player id, which the engine keys on.

Not here: prospects (prospect_values.py), the 2017 page (page_2017_values.py), veterans with no forecast
(buried_contract_values.py). A player whose contract ended before the page (a post-season trade of an expiring
contract: the rights to a pending free agent) has no contract at the page: status "no contract at the page", listed.

OUTPUTS: OUTPUT_DIR/traded_player_values.csv (one row per asset), traded_player_values_log.txt.
Run from the repo root:  python 20_CODE/traded_player_values.py   (after prospect_values.py)
"""

import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "traded_player_values.py v1.2 (2026-10-19)"   # v1.2: season left, retained salary; v1.1: rights only
load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_source as CS                         # noqa: E402
import contract_npv as CN                            # noqa: E402
from skater_forward_projection import page_date   # noqa: E402
import trade_page as TP                              # noqa: E402  v1.2: the share of the season left
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
FIRST_PAGE = 2018
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def main():
    log(SCRIPT_VERSION)
    v = pd.read_csv(OUTPUT_DIR / "prospect_values.csv")
    link = pd.read_csv(OUTPUT_DIR / "draft_pick_linkage.csv")
    LID = {(int(a), int(b)): int(c) for a, b, c in zip(link["draftYear"], link["overallPickNumber"], link["playerId"])
           if pd.notna(c)}
    pc, _ = CS.load_contracts()
    PPID = {int(b): int(a) for a, b in zip(pc["player_id"], pc["nhl_id"]) if pd.notna(a) and pd.notna(b)}
    eng = CN.NPVEngine()
    # v1.2 (Thomas, 2026-10-19: "Yes, include retained salary"): trades.db's retained share of each asset's cap hit
    import sqlite3
    ret = pd.read_sql("select asset_id, retention_pct, retained_aav from trade_assets where retained_aav > 0",
                      sqlite3.connect(Path(os.environ["SOURCE_DIR"]) / "trades.db"))
    RET = dict(zip(ret["asset_id"], ret["retention_pct"].astype(float)))
    rows = []
    for _, r in v.iterrows():
        st, y = str(r["status"]), int(r["valuation_page"])
        if st.startswith(("prospect, valued", "undrafted prospect, valued")) or y < FIRST_PAGE:
            continue
        nid = next((int(r[c]) for c in ("nhl_id", "nhl_id_undrafted") if c in r and pd.notna(r[c])), None)
        if nid is None and pd.notna(r.get("draftYear")) and pd.notna(r.get("pick")):
            nid = LID.get((int(r["draftYear"]), int(r["pick"])))
        rec = {"asset_id": r["asset_id"], "trade_date": r["trade_date"], "trade_season": r["trade_season"],
               "valuation_page": y, "post_season": y != int(r["trade_season"]), "player_name": r["player_name"],
               "acquiring_team": r["acquiring_team"], "nhl_id": nid}
        pid = PPID.get(nid) if nid is not None else None
        if pid is None:
            rec["status"] = "no PuckPedia player" if nid is not None else "no NHL id"
            rows.append(rec)
            continue
        date = pd.Timestamp(r["trade_date"])
        as_of = date if page_date(y) <= date < page_date(y + 1) else page_date(y)
        masked = {}
        # RIGHTS ONLY: the contract the page would value (the first with a row in season y, the one
        # contract_chain starts from) was signed after the trade, so it did not exist when the club acquired him:
        # it acquired his rights. v1.0 checked this for post-season trades only (Kevin Hayes's rights went to
        # Philadelphia on 2019-06-03; he signed for seven years on 2019-06-19). v1.1 (Thomas, 2026-10-18: "value an
        # unsigned player traded inside the page's window as rights only, using rights_values.py's rule") applies
        # it to every trade: contract_chain checks the signing date of an extension but not of the contract it
        # starts from, so a player traded unsigned after July 1 was valued on the deal he signed later (Josh
        # Anderson, traded 2020-10-06, signed for seven years 2020-10-08). rights_values.py values these rows.
        spine = eng.sp.spine if (eng.sp.spine["player_id"] == pid).any() else eng.gp_spine
        mine = spine[spine["player_id"] == pid]
        act = mine.loc[mine["season_start"] == y, "contract_id"]
        if len(act) and pd.notna(eng.sp.signed.get(int(act.iloc[0]))) and eng.sp.signed[int(act.iloc[0])] > date:
            rec.update({"player_id": pid, "as_of": as_of.date(),
                        "status": "rights only (his contract at the page was signed after the trade)"})
            rows.append(rec)
            continue
        if as_of > date:
            # POST-SEASON: the page's July 1 comes after the trade. A later-signed extension did not exist at the
            # trade either, so it is left out of the chain (its signing date masked for this valuation). Inside the
            # window as_of is the trade date, and contract_chain already leaves out an extension signed after it.
            for c in mine["contract_id"].unique():
                sg = eng.sp.signed.get(int(c))
                if pd.notna(sg) and date < sg <= as_of:
                    masked[int(c)] = sg
                    eng.sp.signed[int(c)] = pd.NaT
            rec["signed_after_trade_left_out"] = len(masked)
        # v1.2 (Thomas, 2026-10-19: "Yes, account for in-season trades"; "Days left, value and cap"): the season left on
        # the trade date (1.0 off-season and for a post-season trade, valued on the next page), and the retained share
        share = TP.season_left_share(date, y)
        rpct = float(RET.get(r["asset_id"], 0.0))
        rec.update({"season_share": share, "retained_pct": rpct})
        d, s = eng.npv(pid, y, as_of, first_season_share=share, retained_pct=rpct)
        eng.sp.signed.update(masked)                    # restore the dates for every other valuation
        rec.update({"player_id": pid, "as_of": as_of.date(), "status": s.get("status"),
                    **{k: s[k] for k in ("npv_total", "npv_contract", "npv_terminal", "npv_total_qo",
                                         "npv_total_term_free", "n_contract_seasons", "retained_pv") if k in s}})
        if s.get("status") == "no_contract":
            rec["status"] = "no contract at the page"
        rows.append(rec)
    d = pd.DataFrame(rows)
    log(f"\nTRADED PLAYERS VALUED AT THEIR TRADE'S PAGE ({FIRST_PAGE}-{str(FIRST_PAGE + 1)[2:]} on): {len(d)} assets")
    log(d["status"].value_counts().to_string())
    ok = d[d["status"] == "ok"]
    log(f"  priced: {len(ok)}; npv_total ${ok['npv_total'].sum() / 1e6:,.1f}M; post-season trades among them: "
        f"{int(ok['post_season'].sum())}")
    late = d[d.get("signed_after_trade_left_out", pd.Series(0, index=d.index)).fillna(0) > 0]
    log(f"  post-season trades with an extension signed after the trade, left out: {len(late)}"
        + "".join(f"\n    {x.trade_date} {x.player_name}" for x in late.itertuples()))
    ro = d[d["status"].astype(str).str.startswith("rights only")]
    log(f"  rights only (contract at the page signed after the trade): {len(ro)}"
        + "".join(f"\n    {x.trade_date} {x.player_name} (page {x.valuation_page}"
                  f"{', post-season' if x.post_season else ''})" for x in ro.itertuples()))
    nc = d[d["status"] == "no contract at the page"]
    log(f"  no contract at the page: {len(nc)}" + "".join(
        f"\n    {x.trade_date} {x.player_name} (page {x.valuation_page}{', post-season' if x.post_season else ''})"
        for x in nc.itertuples()))
    d.to_csv(OUTPUT_DIR / "traded_player_values.csv", index=False)
    (OUTPUT_DIR / "traded_player_values_log.txt").write_text("\n".join(LOG), encoding="utf-8")
    log(f"\nwrote traded_player_values.csv and its log in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
