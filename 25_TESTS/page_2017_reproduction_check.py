"""
page_2017_reproduction_check.py -- does a CapWages-built contract price like PuckPedia's own? (report only)

For the 2017-18 assets whose contract PuckPedia's spine also carries at 2017 with the same cap hit and last season,
page_2017_values.py prices the CapWages contract; this prices the same player at the same page and date on the
unchanged engine (PuckPedia's spine rows) and compares npv_total, the contract part and the terminal part. Where they
differ, the inputs the CapWages build supplies itself are the suspects: the UFA year (CBA Group 3 here, PuckPedia's
ufa_year there), the arbitration flag (CapWages's "RFA (Arb)" here, PuckPedia's flag there), the final base salary.
Run from the repo root:  python 25_TESTS/page_2017_reproduction_check.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
import pandas as pd
import contract_npv as CN

v = pd.read_csv("30_OUTPUT/page_2017_values.csv")
sp = pd.read_csv("30_OUTPUT/contract_season_spine.csv", usecols=["contract_id", "player_id", "season_start", "pp_cap_hit",
                                                                 "cs_cap_hit", "pp_expiry", "ufa_year"])
last = sp.groupby("contract_id")["season_start"].max()
s17 = sp[sp["season_start"] == 2017].assign(last=lambda d: d["contract_id"].map(last),
                                             cost=lambda d: d["cs_cap_hit"].fillna(d["pp_cap_hit"]))
s17 = s17.drop_duplicates("player_id").set_index("player_id")
ok = v[(v["status"] == "ok") & (v["player_id"] > 0)].copy()
ok = ok[ok["player_id"].isin(s17.index)]
ok["same"] = [(abs(s17.loc[p, "cost"] - c) < 1) and (s17.loc[p, "last"] == l)
              for p, c, l in zip(ok["player_id"], ok["cap_hit_2017"], ok["contract_last_season"])]
ok = ok[ok["same"] & (ok["extensions"] == 0)]
eng = CN.NPVEngine()
rows = []
for r in ok.itertuples():
    d, s = eng.npv(int(r.player_id), 2017, pd.Timestamp(r.trade_date))
    rows.append((r.trade_date, r.player_name, r.expiry, r.ufa_year, s17.loc[r.player_id, "pp_expiry"],
                 s17.loc[r.player_id, "ufa_year"], r.npv_total / 1e6, s.get("npv_total", float("nan")) / 1e6,
                 r.npv_terminal / 1e6, s.get("npv_terminal", float("nan")) / 1e6))
x = pd.DataFrame(rows, columns=["date", "player", "cw_expiry", "cw_ufa", "pp_expiry", "pp_ufa", "cw_total", "pp_total",
                                "cw_terminal", "pp_terminal"])
x["gap"] = x["cw_total"] - x["pp_total"]
print(f"contracts the two sources agree on (no extension): {len(x)}; npv_total within $0.01M: {int((x['gap'].abs() < 0.01).sum())}")
print(x.round(3).to_string())
