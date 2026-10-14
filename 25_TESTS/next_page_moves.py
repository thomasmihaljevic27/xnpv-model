"""
next_page_moves.py -- what moves when trades made after the regular season are valued on the next season's page.

DECIDED (Thomas, 2026-10-14): "Value trades made after the regular season ends (June) on the next season's page, for
players, prospects and picks alike; show me what moves." Rule: trade_page.page().

COMPARED (before: copies of the outputs taken before the change, in the folder given; after: OUTPUT_DIR)
  * prospects: prospect_values.csv, value_M by asset (status changes counted: a prospect at the old page may be the
    player model's at the new one);
  * players: the after value is traded_player_values.csv (pages 2018-19 on) or page_2017_values.csv; the before value
    of a post-season trade is the old page's: page_2017_values.csv (before) for 2017-18 trades, and for 2018-19 trades
    the engine at page 2018 as of the trade date, computed here (no trade-level value was kept before);
  * picks: traded_pick_values.csv, unchanged by construction (a pick's value is the star value x its slot's star
    chance; the slot comes from the draft calendar and the standings on the trade date, not from a page): asserted.
Run from the repo root:  python 25_TESTS/next_page_moves.py <folder with the earlier files>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
import pandas as pd
import trade_page as TP

B, A = Path(sys.argv[1]), Path("30_OUTPUT")
print("next_page_moves.py v1.0 (2026-10-14)")

# ---- picks --------------------------------------------------------------------------------------------
pb, pa = pd.read_csv(B / "traded_pick_values.csv"), pd.read_csv(A / "traded_pick_values.csv")
m = pb.merge(pa, on="asset_id", suffixes=("_b", "_a"))
gap = (m["value_M_b"].fillna(0) - m["value_M_a"].fillna(0)).abs().max()
post = sum(TP.page(d) != TP.trade_season(d) for d in pa["trade_date"])
print(f"\nPICKS: {len(pa)}; traded after the regular season: {post}; largest change in value ${gap:.6f}M (none by "
      f"construction)")
assert gap < 1e-9

# ---- prospects ----------------------------------------------------------------------------------------
vb, va = pd.read_csv(B / "prospect_values.csv"), pd.read_csv(A / "prospect_values.csv")
m = vb.merge(va, on="asset_id", suffixes=("_b", "_a"))
moved = m[m["valuation_page"] != m["trade_season_a"]] if "valuation_page" in m else m.iloc[0:0]
print(f"\nPROSPECTS (prospect_values): post-season assets moved to the next page: {len(moved)}")
vb_ok = moved["status_b"].astype(str).str.contains("valued")
va_ok = moved["status_a"].astype(str).str.contains("valued")
print(f"  valued before {int(vb_ok.sum())} (${moved.loc[vb_ok, 'value_M_b'].sum():.2f}M); valued after "
      f"{int(va_ok.sum())} (${moved.loc[va_ok, 'value_M_a'].sum():.2f}M)")
ch = moved[moved["status_b"] != moved["status_a"]]
print(f"  status changed: {len(ch)}")
for r in ch.itertuples():
    print(f"    {r.trade_date_a}  {r.player_name_a:<24} {r.status_b} -> {r.status_a}")
both = moved[vb_ok & va_ok].assign(d=lambda x: x["value_M_a"] - x["value_M_b"])
print(f"  valued both times: {len(both)}; total {both['d'].sum():+.2f}M; largest moves:")
for r in both.reindex(both["d"].abs().sort_values(ascending=False).index).head(10).itertuples():
    print(f"    {r.trade_date_a}  {r.player_name_a:<24} k {int(r.seasons_since_draft_b)} -> {int(r.seasons_since_draft_a)}: "
          f"${r.value_M_b:.2f}M -> ${r.value_M_a:.2f}M ({r.d:+.2f})")

# ---- players ------------------------------------------------------------------------------------------
tp = pd.read_csv(A / "traded_player_values.csv")
p17b, p17a = pd.read_csv(B / "page_2017_values.csv"), pd.read_csv(A / "page_2017_values.csv")
post = tp[tp["post_season"]].copy()
b17 = p17b.set_index("asset_id")
before = {}
need18 = post[post["trade_season"] == 2018]
if len(need18):
    import contract_npv as CN
    import contract_source as CS
    pc, _ = CS.load_contracts()
    PPID = {int(b): int(x) for x, b in zip(pc["player_id"], pc["nhl_id"]) if pd.notna(x) and pd.notna(b)}
    eng = CN.NPVEngine()
    for r in need18.itertuples():
        pid = PPID.get(int(r.nhl_id)) if pd.notna(r.nhl_id) else None
        if pid is not None:
            _, s = eng.npv(pid, 2018, pd.Timestamp(r.trade_date))
            before[r.asset_id] = s.get("npv_total") if s.get("status") == "ok" else None
for r in post[post["trade_season"] == 2017].itertuples():
    if r.asset_id in b17.index and b17.loc[r.asset_id, "status"] in ("ok", "buried veteran (cost above burial)"):
        before[r.asset_id] = b17.loc[r.asset_id, "npv_total"]
post["before_M"] = post["asset_id"].map(before) / 1e6
post["after_M"] = post["npv_total"].where(post["status"] == "ok") / 1e6
print(f"\nPLAYERS: post-season trades valued on the next page: {len(post)} assets "
      f"({int((post['trade_season'] == 2017).sum())} of 2017-18, {int((post['trade_season'] == 2018).sum())} of 2018-19)")
print("  after: " + ", ".join(f"{k} {v}" for k, v in post["status"].value_counts().items()))
bo = post.dropna(subset=["before_M", "after_M"]).assign(d=lambda x: x["after_M"] - x["before_M"])
print(f"  valued on both pages: {len(bo)}; before ${bo['before_M'].sum():,.2f}M, after ${bo['after_M'].sum():,.2f}M "
      f"({bo['d'].sum():+,.2f}M); moved by $1M or more: {int((bo['d'].abs() >= 1).sum())}")
for r in bo.reindex(bo["d"].abs().sort_values(ascending=False).index).head(12).itertuples():
    print(f"    {r.trade_date}  {r.player_name:<24} page {r.trade_season} -> {r.valuation_page}: "
          f"${r.before_M:7.2f}M -> ${r.after_M:7.2f}M ({r.d:+.2f})")
ro = post[post["status"].astype(str).str.startswith(("rights only", "no contract at the page"))]
print(f"  rights only at the next page (no contract the trade carried): {len(ro)}; their old-page value "
      f"${ro['before_M'].sum():,.2f}M:")
for r in ro.sort_values("before_M").itertuples():
    print(f"    {r.trade_date}  {r.player_name:<24} old page ${r.before_M:6.2f}M")
