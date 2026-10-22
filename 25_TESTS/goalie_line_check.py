"""goalie_line_check.py -- the goaltender price line on the forecast with its age term, against the tested version
without it (report only).

WHY (2026-10-21): Thomas adopted the price line goalie_review.py v1.0 Part D tested (the pulled forecast dated at the
signing, censored at the league minimum, with term: $2.04M per forecast WAR, $0.78M per year of term, held out $1.119M)
and, separately, an age term in the goaltender forecast. Fitted on the forecast as adopted (with the age term; the
quantity the line prices), goalie_value_engine.py v2.0 Stage G gives $1.27M per WAR and $0.91M per year of term. This
checks, on Stage G's own contracts and goalie_review's held-out procedure (5 groups of goaltenders x 20 repeats, seed
20261005), that the adopted version predicts cap hits at least as well as the tested one, and says what the age term
changes in the line.

Run from the repo root:  python 25_TESTS/goalie_line_check.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
import numpy as np
import pandas as pd
from scipy import stats


def main():
    import goalie_value_engine as GVE
    import xnpv1_price_line as XPL
    import contract_source as CS
    from skater_forward_projection import league_min_path
    CN, GP, nn = GVE._projector()
    raw = pd.read_excel(GVE.F_CONTRACT_XLSX)
    raw["start_yr"] = CS.contract_terms(raw)["first_yr"]
    d = raw[(raw["position"] == "Goaltender") & (raw["contract_level"] == "standard_level")
            & raw["start_yr"].between(2015, 2025)].copy()
    d["nname"] = CS.war_full_name(d, d["first_name"].astype(str) + " " + d["last_name"].astype(str)).map(nn)
    d["cap"] = d["start_yr"].map(lambda y: GVE.ceiling_for(int(y))[0])
    d["cap_pct"], d["floor_pct"] = d["aav"] / d["cap"], d["start_yr"].map(league_min_path) / d["cap"]
    d["signed"], d["bd"] = pd.to_datetime(d["signing_date"], errors="coerce"), pd.to_datetime(d["birthdate"], errors="coerce")
    d["length"] = pd.to_numeric(d["length"], errors="coerce")
    xa, xn = [], []
    for r in d.itertuples():
        page, ok = XPL.signing_page(r.signed)
        h = None if page is None else int(r.start_yr) - int(page)
        if not ok or h is None or h < 0:
            xa.append(np.nan); xn.append(np.nan); continue
        a0 = None if pd.isna(r.bd) else int(page) - r.bd.year - ((9, 15) < (r.bd.month, r.bd.day))
        fc, src = GP.forecast(r.nname, int(page), h, a0)
        if fc is None or src == "stale_anchor":
            xa.append(np.nan); xn.append(np.nan); continue
        xa.append(fc[h][1]); xn.append(GP.shrunk_projection(r.nname, int(page))[0])
    d["x_age"], d["x_flat"] = xa, xn
    d = d[np.isfinite(d["x_age"]) & d["cap_pct"].notna() & d["length"].notna()].reset_index(drop=True)
    cap25 = GVE.ceiling_for(2025)[0]
    y, fl = d["cap_pct"].to_numpy(float), d["floor_pct"].to_numpy(float)
    print(f"{len(d)} contracts (Stage G's); forecast with the age term: mean {d['x_age'].mean():.3f}, sd {d['x_age'].std():.3f}; "
          f"without: mean {d['x_flat'].mean():.3f}, sd {d['x_flat'].std():.3f}")

    def fit_pred(col, tr, te):
        X = d[[col, "length"]].to_numpy(float)
        f = XPL.fit_censored(y[tr], X[tr], fl[tr])
        mu = np.column_stack([np.ones(int(te.sum())), X[te]]) @ np.asarray(f["coef"])
        z = (fl[te] - mu) / f["sigma"]
        return fl[te] * stats.norm.cdf(z) + mu * (1 - stats.norm.cdf(z)) + f["sigma"] * stats.norm.pdf(z), f

    for col in ("x_age", "x_flat"):
        _, f = fit_pred(col, np.ones(len(d), bool), np.ones(len(d), bool))
        print(f"  {col}: ${f['coef'][0] * cap25 / 1e6:.2f}M + ${f['coef'][1] * cap25 / 1e6:.3f}M per WAR + "
              f"${f['coef'][2] * cap25 / 1e6:.3f}M per year of term")
    rng = np.random.default_rng(20261005)
    pl = d["nname"].unique()
    E = {c: [] for c in ("x_age", "x_flat")}
    for _ in range(20):
        fo = d["nname"].map(dict(zip(pl, rng.permutation(len(pl)) % 5))).to_numpy()
        for c in E:
            p = np.full(len(d), np.nan)
            for k in range(5):
                tr, te = fo != k, fo == k
                p[te] = fit_pred(c, tr, te)[0]
            E[c].append(float(np.sqrt(np.mean((p - y) ** 2))) * cap25 / 1e6)
    a, b = np.array(E["x_age"]), np.array(E["x_flat"])
    print(f"  held out, root mean squared error of the cap hit: with the age term ${a.mean():.3f}M; without ${b.mean():.3f}M; "
          f"with it lower in {int((a < b).sum())} of 20 repeats")


if __name__ == "__main__":
    main()
