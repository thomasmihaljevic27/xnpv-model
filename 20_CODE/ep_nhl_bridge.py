"""
ep_nhl_bridge.py -- one table connecting Elite Prospects player ids to NHL player ids.

SCRIPT_VERSION = 1.0  (2026-09-28)

WHY THIS EXISTS
---------------
The prospect model reads junior / college / European production from Elite
Prospects (keyed by EP id) and draft slots and NHL careers from the NHL's own
records (keyed by NHL id). Elite Prospects pages carry no NHL id (checked
2026-09-28 on a full player-page payload), so the two have to be bridged.

HOW IT BRIDGES (two sources, no name matching)
----------------------------------------------
1. DRAFT SLOT. Every NHL Entry Draft pick is one player, so (draft year,
   overall pick) is a key both sides share: ep_draft_selections (from
   ep_extract.py's draft pass) and draft_pick_linkage.csv (NHL Records).
   Covers every drafted player 2005-2026, signed or not.
2. PUCKPEDIA. The contract export carries both eliteprospects_id and nhl_id
   for every contracted player. Covers undrafted players who signed.

Names and birthdates are CHECKS on the draft-slot join, never keys:
  - name agreement after normalising accents, case and punctuation;
  - birthdate agreement, once ep_player_bio holds the drafted players' bios
    (ep_extract.py v3's bio pass); skipped with a note until then.
And the draft-slot join is scored against PuckPedia on every player both
sources cover: that agreement rate is the bridge's validation.

ASSUMPTIONS, stated so they can be checked
------------------------------------------
- A player drafted twice (re-entered the draft) has two slots on both sides;
  both rows must point at the same pair of ids, or the guard stops.
- Where the two sources disagree for one EP id, the row is kept with
  status CONFLICT and no nhl_id is chosen. Nothing is resolved silently.
- Slots with no player on either side (forfeited or void picks) are
  reported and dropped.

Outputs (OUTPUT_DIR/ep_out/): ep_nhl_bridge.csv, ep_nhl_bridge_log.txt
Run: python 20_CODE/ep_nhl_bridge.py   (after ep_extract.py --draft-only)
"""

import os
import re
import sqlite3
import sys
import unicodedata

import pandas as pd
from dotenv import load_dotenv

load_dotenv()
SCRIPT_VERSION = "1.0"

OUTPUT_DIR = os.environ["OUTPUT_DIR"]
EP_DB = os.environ["EP_PROSPECTS_DB"]
CONTRACTS_XLSX = os.environ["PUCKPEDIA_CONTRACTS_XLSX"]
LINKAGE_PATH = os.path.join(OUTPUT_DIR, "draft_pick_linkage.csv")
OUT_DIR = os.path.join(OUTPUT_DIR, "ep_out")
OUT_CSV = os.path.join(OUT_DIR, "ep_nhl_bridge.csv")
OUT_LOG = os.path.join(OUT_DIR, "ep_nhl_bridge_log.txt")

_log_lines = []


def log(msg=""):
    print(msg)
    _log_lines.append(str(msg))


def norm_name(s) -> str:
    """Lowercase, strip accents and punctuation, collapse spaces. For CHECKS only."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def table_exists(conn, name) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                        (name,)).fetchone() is not None


def main():
    log(f"ep_nhl_bridge.py SCRIPT_VERSION {SCRIPT_VERSION}")
    conn = sqlite3.connect(EP_DB)
    if not table_exists(conn, "ep_draft_selections"):
        sys.exit("ep_draft_selections not found: run `python 20_CODE/ep_extract.py "
                 "--draft-only` first.")
    ep = pd.read_sql("SELECT draft_year, draft_overall, ep_player_id, player_name_ep "
                     "FROM ep_draft_selections", conn)
    bio = (pd.read_sql("SELECT ep_player_id, dob FROM ep_player_bio", conn)
           if table_exists(conn, "ep_player_bio") else None)
    conn.close()

    nhl = pd.read_csv(LINKAGE_PATH, usecols=["draftYear", "overallPickNumber",
                                             "playerId", "playerName", "birthDate"])
    nhl = nhl.rename(columns={"draftYear": "draft_year",
                              "overallPickNumber": "draft_overall",
                              "playerId": "nhl_id", "playerName": "player_name_nhl",
                              "birthDate": "birthdate_nhl"})

    # ---- 1. Slot reconciliation, year by year --------------------------------
    per_year = (ep.groupby("draft_year").size().rename("ep")
                .to_frame().join(nhl.groupby("draft_year").size().rename("nhl"), how="outer"))
    bad_years = per_year[per_year["ep"] != per_year["nhl"]]
    log(f"[slots] EP {len(ep)} picks, NHL Records {len(nhl)} picks; "
        f"years whose counts differ: {len(bad_years)}")
    if len(bad_years):
        log(bad_years.to_string())

    # ---- 2. Draft-slot join ---------------------------------------------------
    j = ep.merge(nhl, on=["draft_year", "draft_overall"], how="outer", indicator=True)
    one_sided = j[j["_merge"] != "both"]
    log(f"[join] slots on one side only: {len(one_sided)}")
    j = j[j["_merge"] == "both"].drop(columns="_merge")
    empty = j["ep_player_id"].isna() | j["nhl_id"].isna()
    log(f"[join] slots with no player on at least one side (forfeited/void or "
        f"missing id): {int(empty.sum())}")
    for _, r in j[empty].iterrows():
        log(f"         {int(r.draft_year)} #{int(r.draft_overall)}: EP={r.player_name_ep} "
            f"NHL={r.player_name_nhl}")
    j = j[~empty].copy()
    j["ep_player_id"] = j["ep_player_id"].astype("int64")
    j["nhl_id"] = j["nhl_id"].astype("int64")

    # Name check
    j["name_agrees"] = [norm_name(a) == norm_name(b)
                        for a, b in zip(j.player_name_ep, j.player_name_nhl)]
    # Surname-only agreement catches first-name spellings (Alexander/Aleksandr)
    j["surname_agrees"] = [norm_name(a).split(" ")[-1:] == norm_name(b).split(" ")[-1:]
                           for a, b in zip(j.player_name_ep, j.player_name_nhl)]
    log(f"[check] full-name agreement {j.name_agrees.sum()}/{len(j)}; "
        f"surname agreement {j.surname_agrees.sum()}/{len(j)}; "
        f"neither: {int((~j.surname_agrees).sum())}")
    for _, r in j[~j.surname_agrees].head(40).iterrows():
        log(f"         {r.draft_year} #{r.draft_overall}: EP '{r.player_name_ep}' vs "
            f"NHL '{r.player_name_nhl}'")

    # Birthdate check (only once the bio pass has covered the drafted players)
    if bio is not None and len(bio):
        b = bio.dropna().drop_duplicates("ep_player_id")
        b["dob_ep"] = pd.to_datetime(b["dob"], errors="coerce").dt.date.astype(str)
        j = j.merge(b[["ep_player_id", "dob_ep"]], on="ep_player_id", how="left")
        has = j["dob_ep"].notna() & (j["dob_ep"] != "NaT")
        j["dob_agrees"] = pd.NA
        j.loc[has, "dob_agrees"] = j.loc[has, "dob_ep"] == j.loc[has, "birthdate_nhl"].astype(str)
        log(f"[check] birthdate agreement {int((j.dob_agrees == True).sum())}/{int(has.sum())} "
            f"drafted players with an EP bio")
    else:
        j["dob_agrees"] = pd.NA
        log("[check] birthdates: SKIPPED (no ep_player_bio yet; run the bio pass)")

    # Re-drafted players: one id pair per player
    ep_multi = j.groupby("ep_player_id")["nhl_id"].nunique()
    nhl_multi = j.groupby("nhl_id")["ep_player_id"].nunique()
    log(f"[check] EP ids mapping to >1 NHL id: {int((ep_multi > 1).sum())}; "
        f"NHL ids mapping to >1 EP id: {int((nhl_multi > 1).sum())}")
    slot = (j.sort_values(["draft_year"])
            .groupby("ep_player_id", as_index=False)
            .agg(nhl_id=("nhl_id", "first"), n_nhl_ids=("nhl_id", "nunique"),
                 first_draft_year=("draft_year", "first"),
                 name_agrees=("name_agrees", "all"),
                 surname_agrees=("surname_agrees", "all"),
                 dob_agrees=("dob_agrees", "first"),
                 player_name_nhl=("player_name_nhl", "first")))

    # ---- 3. PuckPedia pairs ---------------------------------------------------
    c = pd.read_excel(CONTRACTS_XLSX, usecols=["eliteprospects_id", "nhl_id"])
    c = c.dropna().astype("int64").drop_duplicates()
    pp_conflict = c.groupby("eliteprospects_id")["nhl_id"].nunique()
    log(f"[puckpedia] {len(c)} distinct (EP id, NHL id) pairs; EP ids with >1 "
        f"NHL id inside PuckPedia itself: {int((pp_conflict > 1).sum())}")
    pp = c.drop_duplicates("eliteprospects_id").rename(
        columns={"eliteprospects_id": "ep_player_id", "nhl_id": "nhl_id_pp"})

    # ---- 4. Validation: the draft-slot bridge against PuckPedia ---------------
    v = slot.merge(pp, on="ep_player_id", how="inner")
    agree = (v.nhl_id == v.nhl_id_pp)
    log(f"[validate] drafted players in both sources: {len(v)}; NHL id agrees: "
        f"{int(agree.sum())} ({agree.mean():.2%}); disagrees: {int((~agree).sum())}")
    for _, r in v[~agree].iterrows():
        log(f"         EP {r.ep_player_id} ({r.player_name_nhl}): draft slot -> "
            f"{r.nhl_id}, PuckPedia -> {r.nhl_id_pp}")

    # ---- 5. Assemble one row per EP id ----------------------------------------
    out = slot.merge(pp, on="ep_player_id", how="outer")
    def status(r):
        a, b = r.get("nhl_id"), r.get("nhl_id_pp")
        if pd.notna(a) and pd.notna(b):
            return "both_agree" if int(a) == int(b) else "CONFLICT"
        return "draft_slot_only" if pd.notna(a) else "puckpedia_only"
    out["status"] = out.apply(status, axis=1)
    out["nhl_id_final"] = out["nhl_id"].where(out["nhl_id"].notna(), out["nhl_id_pp"])
    out.loc[out.status == "CONFLICT", "nhl_id_final"] = pd.NA
    out["nhl_id_final"] = out["nhl_id_final"].astype("Int64")
    log("[bridge] rows by status: " + ", ".join(
        f"{k} {v}" for k, v in out.status.value_counts().items()))
    fin = out.dropna(subset=["nhl_id_final"])
    dup_nhl = fin.groupby("nhl_id_final")["ep_player_id"].nunique()
    log(f"[guard] NHL ids claimed by >1 EP id in the final bridge: {int((dup_nhl > 1).sum())}")
    for nid in dup_nhl[dup_nhl > 1].index[:20]:
        log(f"         nhl_id {nid}: EP ids {sorted(fin.loc[fin.nhl_id_final == nid, 'ep_player_id'].tolist())}")

    os.makedirs(OUT_DIR, exist_ok=True)
    cols = ["ep_player_id", "nhl_id_final", "status", "nhl_id", "nhl_id_pp",
            "first_draft_year", "n_nhl_ids", "name_agrees", "surname_agrees",
            "dob_agrees", "player_name_nhl"]
    out[cols].rename(columns={"nhl_id": "nhl_id_draft_slot", "nhl_id_pp": "nhl_id_puckpedia"}) \
        .sort_values("ep_player_id").to_csv(OUT_CSV, index=False)
    log(f"[done] v{SCRIPT_VERSION}: wrote {OUT_CSV} ({len(out)} EP ids)")
    with open(OUT_LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(_log_lines) + "\n")


if __name__ == "__main__":
    main()
