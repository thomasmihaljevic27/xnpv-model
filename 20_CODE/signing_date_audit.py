"""signing_date_audit.py -- how much of the locked market-rate sample reads
performance that happened AFTER the contract was signed?

TEST ONLY. Reads the PuckPedia contract export and WAR.csv; writes three files
under OUTPUT_DIR with this script's name as prefix (the row-level file holds
confidential contract data and stays gitignored with the rest of 30_OUTPUT).
Touches no production file.

THE EXPOSURE (raised in the 2026-09-14 ground-up review, quantified here)
  The rate sample (skater_value_engine.stage0 / anchor_shrink_test.rate_sample)
  dates each contract by its START season and reads trailing WAR from the two
  seasons before that start. A contract signed before those seasons were
  played -- a star extended in July for a deal starting the following year,
  or any extension signed during the final year of the old deal -- is fitted
  on production the signing team had not seen. The NPV chain's own guard
  (D28, signing dates gate extensions) does not touch this sample builder.

DEFINITIONS
  The t-1 season is taken to run from Oct 1 of (start_yr - 1) to Jun 30 of
  start_yr. A contract is
    before  signed before Oct 1 (start_yr - 1): all of t-1 unseen at signing
    during  signed inside the t-1 season:        part of t-1 unseen
    after   signed after Jun 30 start_yr:        no look-ahead
  Tiers are the locked trailing blend at contract start (the regressor).
"""
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parent))
from skater_value_engine import (build_skater_war_lookup, trailing_weighted_war,
                                 norm_name, POSGRP, CAP_CEILING)

SCRIPT_VERSION = "1.0"
OUT = Path(os.environ["OUTPUT_DIR"])
PREFIX = "signing_date_audit"
TIERS = [-99, 0, 1, 2, 3, 99]
TIER_NAMES = ["below 0", "0 to 1", "1 to 2", "2 to 3", "3+"]


def rate_sample():
    """The locked n=2,349 sample, built exactly as skater_value_engine.stage0()."""
    raw = pd.read_excel(os.environ["PUCKPEDIA_CONTRACTS_XLSX"])
    raw["end_yr"] = pd.to_numeric(raw["contract_end"].astype(str).str.extract(r"^(\d{4})")[0],
                                  errors="coerce")
    raw["start_yr"] = raw["end_yr"] - raw["length"] + 1
    raw["posgrp"] = raw["position"].map(POSGRP)
    raw["nk"] = ((raw["first_name"].astype(str) + " " + raw["last_name"].astype(str))
                 .map(norm_name) + "|" + raw["posgrp"].astype(str))
    raw["cap_pct"] = raw["aav"] / raw["start_yr"].map(CAP_CEILING)
    ss = raw["signing_status"].astype(str)
    sk = raw[raw["start_yr"].between(2018, 2025) & (raw["contract_level"] == "standard_level")
             & ss.isin(["UFA", "RFA"]) & (raw["posgrp"] != "G") & raw["cap_pct"].notna()].copy()
    lut = build_skater_war_lookup(exclude_merged=False, prorate=True)
    res = [trailing_weighted_war(k, y, lut) for k, y in zip(sk["nk"], sk["start_yr"])]
    sk["wWAR"] = [r[0] for r in res]
    sk["src"] = [r[1] for r in res]
    return sk[sk["wWAR"].notna()].copy()


def main():
    clock = time.time()
    print(f"SCRIPT_VERSION={SCRIPT_VERSION}", flush=True)
    sk = rate_sample()
    assert abs(len(sk) - 2349) <= 5, f"rate sample n={len(sk)}, expected 2,349"
    sk["signed"] = pd.to_datetime(sk["signing_date"], errors="coerce")
    n_dated = int(sk["signed"].notna().sum())
    t1_open = pd.to_datetime((sk["start_yr"] - 1).astype(int).astype(str) + "-10-01")
    t1_close = pd.to_datetime(sk["start_yr"].astype(int).astype(str) + "-06-30")
    sk["group"] = np.select([sk["signed"] < t1_open,
                             (sk["signed"] >= t1_open) & (sk["signed"] <= t1_close)],
                            ["before", "during"], default="after")
    sk.loc[sk["signed"].isna(), "group"] = "undated"
    sk["days_before_t1_close"] = (t1_close - sk["signed"]).dt.days
    sk["tier"] = pd.cut(sk["wWAR"], TIERS, labels=TIER_NAMES)

    print(f"\nrate sample n={len(sk):,}; signing date on file for {n_dated:,}")
    overall = sk["group"].value_counts()
    for g in ["before", "during", "after", "undated"]:
        if g in overall:
            print(f"  {g:8s} {overall[g]:5d}  ({100 * overall[g] / len(sk):.1f}%)")
    tab = (sk.groupby(["tier", "group"], observed=True).size().unstack(fill_value=0)
             .reindex(columns=["before", "during", "after"], fill_value=0))
    tab["n"] = tab.sum(axis=1)
    tab["share_before"] = tab["before"] / tab["n"]
    tab["share_before_or_during"] = (tab["before"] + tab["during"]) / tab["n"]
    print("\nby trailing-WAR tier:")
    print(tab.round(3).to_string())
    bys = sk.groupby("signing_status")["group"].value_counts().unstack(fill_value=0)
    print("\nby signing status:")
    print(bys.to_string())
    cap = (sk.groupby(["tier", "group"], observed=True)["cap_pct"].agg(["mean", "count"])
             .unstack("group"))
    print("\nmean cap share at signing (percent) by tier and group -- a first look at whether "
          "early signers are paid differently at the same trailing WAR:")
    print((cap["mean"] * 100).round(2).to_string())
    print("\ncounts behind that table:")
    print(cap["count"].fillna(0).astype(int).to_string())
    tab.to_csv(OUT / f"{PREFIX}_by_tier.csv")
    sk[["contract_id", "player_id", "start_yr", "signing_status", "signing_date", "group",
        "days_before_t1_close", "wWAR", "src", "tier", "cap_pct"]].to_csv(
        OUT / f"{PREFIX}_rows.csv", index=False)
    (OUT / f"{PREFIX}_run.json").write_text(json.dumps(dict(
        script_version=SCRIPT_VERSION, n=len(sk), n_dated=n_dated,
        counts={k: int(v) for k, v in overall.items()},
        by_tier=tab.reset_index().astype({"tier": str}).to_dict(orient="records"),
        elapsed_seconds=time.time() - clock), indent=2, default=str))
    print(f"\n{time.time() - clock:.0f}s; outputs {PREFIX}_by_tier.csv, _rows.csv (confidential, "
          f"gitignored), _run.json")


if __name__ == "__main__":
    main()
