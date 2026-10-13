"""
arbitration_player_compare.py -- what the arbitration rule does to contract values (report only).

WHY (agreed with the supervisor 2026-10-13 to build and compare; rule set by Thomas the same day):
the qualifying-offer chain may overvalue RFA control years, the same way it overvalues picks. The
contract engine now prices every contract both ways: npv_total (the qualifying-offer chain, the
headline) and npv_total_arb (control seasons costed at the higher of the qualifying offer and the
contract line's price of his 50/30/20 trailing WAR once he is eligible for arbitration;
rfa_terminal_value.py v2.3, contract_npv.py v2.4, contract_npv_panel.py v1.4). Nothing is adopted.

PART 1 -- THE PANEL. Every contract-page in contract_npv_panel.csv, both values: how many move, by
how much, by page; and the top of each page's list under each cost (does the top lose its RFAs?).
The contract seasons are identical in both; only the control years differ.

PART 2 -- OUR ELIGIBILITY RULE AGAINST PUCKPEDIA. For every skater contract that ended as an RFA
in 2018-19 to 2024-25, the rule the engine uses (rfa_terminal_value.TerminalValuer._arb_history and
arb_eligible, CBA 12.1(a) with our proxies) is applied at the first control season with every
season before it observed, and compared with PuckPedia's `arbitration_eligible` for the contract.
(Inside a valuation, seasons after the valuation date count as played; here all are observed.)

INPUTS: OUTPUT_DIR/contract_npv_panel.csv (v1.4), the contract spine and season table the engine
reads, SOURCE_DIR's PuckPedia contract export (confidential; read, never written).

Run from the repo root:  python 25_TESTS/arbitration_player_compare.py
"""

import os
import sys
import types
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "arbitration_player_compare.py v1.0 (2026-10-13)"
print(SCRIPT_VERSION)
load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
OUT, SRC = Path(os.environ["OUTPUT_DIR"]), Path(os.environ["SOURCE_DIR"])
F_PANEL = OUT / "contract_npv_panel.csv"
F_PP = SRC / "PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.csv"
for p in (F_PANEL, F_PP):
    print(f"  input: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")
M = 1e6

# ---- PART 1: the panel ------------------------------------------------------------------------------
pn = pd.read_csv(F_PANEL)
assert "npv_total_arb" in pn.columns, "panel predates contract_npv_panel.py v1.4: run the refresh first"
pn["diff"] = pn["npv_total_arb"] - pn["npv_total"]
assert (pn["diff"] <= 1.0).all(), "a contract rose under the arbitration cost"
moved = pn["diff"] < -1.0
print(f"\nPART 1. {len(pn):,} contract-pages; {int(moved.sum()):,} lower under the arbitration cost "
      f"({moved.mean():.0%}); none higher")
print(f"  of the {int((pn['npv_terminal'] > 1).sum()):,} with positive control-year value, "
      f"{int((moved & (pn['npv_terminal'] > 1)).sum()):,} move")
by = pn.groupby("valuation_season").agg(rows=("diff", "size"), moved=("diff", lambda s: int((s < -1).sum())),
                                        total_M=("npv_total", lambda s: s.sum() / M),
                                        total_arb_M=("npv_total_arb", lambda s: s.sum() / M),
                                        median_move_M=("diff", lambda s: s[s < -1].median() / M))
by["change_M"] = by["total_arb_M"] - by["total_M"]          # league totals are negative: report dollars, not %
print(by.round(2).to_string())
mv = pn[moved]
print(f"  among those that move: median -${-mv['diff'].median() / M:.2f}M, largest -${-mv['diff'].min() / M:.2f}M; "
      f"skaters {int((mv['position'] == 'skater').sum()):,}, goalies {int((mv['position'] == 'goalie').sum()):,}")

N = 20
for page in (2024, 2025):
    p = pn[pn["valuation_season"] == page]
    a = p.nlargest(N, "npv_total")
    b = p.nlargest(N, "npv_total_arb")
    print(f"\nTOP {N} on the {page}-{(page + 1) % 100:02d} page, qualifying-offer chain (headline) | arbitration cost")
    print(f"  of the headline's top {N}: {int((a['npv_terminal'] > 1).sum())} carry control-year value; "
          f"{len(set(a['contract_id']) & set(b['contract_id']))} stay in the top {N} under arbitration")
    left = a.reset_index(drop=True)
    right = b.reset_index(drop=True)
    for i in range(N):
        l, r = left.iloc[i], right.iloc[i]
        print(f"  {i + 1:2d} {l['full_name'][:22]:22s} {l['npv_total'] / M:6.2f} (control {l['npv_terminal'] / M:5.2f})"
              f"  | {r['full_name'][:22]:22s} {r['npv_total_arb'] / M:6.2f} (was {r['npv_total'] / M:5.2f})")

# ---- PART 2: eligibility against PuckPedia -----------------------------------------------------------
import rfa_terminal_value as rtv                     # noqa: E402
from skater_forward_projection import SkaterProjector  # noqa: E402

sp = SkaterProjector()
helper = types.SimpleNamespace(sp=sp)               # _arb_history reads only .sp (and caches on self)
pp = pd.read_csv(F_PP, low_memory=False, encoding="latin-1")[["contract_id", "arbitration_eligible", "expiry_status"]]
last = sp.spine.sort_values("season_start").groupby("contract_id").tail(1)
last = last[(last["pp_expiry"] == "RFA") & last["season_start"].between(2018, 2024)]
rows = []
for r in last.itertuples():
    t = int(r.season_start) + 1                     # the first control season; everything before observed
    observed, need = rtv.TerminalValuer._arb_history(helper, r.nk, t)
    ours = rtv.arb_eligible(t, t, need, {z: v[0] for z, v in observed.items()})
    rows.append({"contract_id": int(r.contract_id), "player": r.full_name, "end": int(r.season_start),
                 "need": need, "pro_seasons": sum(1 for z, v in observed.items() if v[0] >= rtv.ARB_GP.get(z, 10)),
                 "ours": ours})
e = pd.DataFrame(rows).merge(pp, on="contract_id", how="left")
print(f"\nPART 2. {len(e):,} skater contracts ending as RFAs 2018-19 to 2024-25; PuckPedia flag present for "
      f"{int(e['arbitration_eligible'].notna().sum()):,}; never eligible here for want of a signing age: "
      f"{int(e['need'].isna().sum())} ({int((e['need'].isna() & (e['pro_seasons'] == 0)).sum())} of them with no "
      f"NHL season of 10+ games)")
e = e.dropna(subset=["arbitration_eligible"])
print(pd.crosstab(e["ours"].map({True: "ours: eligible", False: "ours: not"}),
                  e["arbitration_eligible"].map({1: "PuckPedia: eligible", 0: "PuckPedia: not"})).to_string())
agree = (e["ours"] == (e["arbitration_eligible"] == 1)).mean()
print(f"  agree on {agree:.1%}")
late = e[~e["ours"] & (e["arbitration_eligible"] == 1)]
early = e[e["ours"] & (e["arbitration_eligible"] == 0)]
print(f"  ours later than PuckPedia: {len(late)} (expected: no AHL games, so fewer professional seasons); "
      f"ours earlier: {len(early)}")
for name, s in (("later", late), ("earlier", early)):
    if len(s):
        print(f"    {name}, first 8: " + "; ".join(f"{x.player} ({x.end}, need {x.need}, {x.pro_seasons} NHL)"
                                          for x in s.head(8).itertuples()))
e.to_csv(OUT / "arbitration_eligibility_check.csv", index=False)
print(f"\nwrote arbitration_eligibility_check.csv in {OUT}")
