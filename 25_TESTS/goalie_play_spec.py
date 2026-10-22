"""goalie_play_spec.py -- the goaltender chance of playing's terms, under the agreed significance rule (report only).

WHY (Thomas, 2026-10-21: "replace the exit chain with a chance of playing by season ahead"). goalie_review.py v1.0 Part E
tested a logistic regression for each season ahead on age, age squared, the forecast and last season's games share.
Before it is built, each term faces the rule agreed for every adopted regression (MODEL_DIRECTIVES, "Thomas's second
round of notes", item 2): a term goes if it is not statistically significant at the 5% level AND dropping it does not
worsen the held-out forecast; failing terms are tested together as well as alone.

ROWS: every goaltender with a forecast at a page t0 (a season at t0-1; the forecast as goalie_review builds it: his
50/30/20 trailing WAR, D20-prorated, kept 35% and pulled 65% toward 2.19), seasons 0-5 ahead, outcome: one NHL game or
more in season t0+h. Ages on September 15 from goalie_birthdates.csv.
IN SAMPLE: each season ahead's regression on every page 2009-2025 whose outcome season has been played, errors clustered
by goaltender. HELD OUT: pages 2015-2021, each season ahead fitted on pages whose outcome season came before the page
(goalie_review's procedure); log loss; p = the share of 2,000 redraws of goaltenders (seed 20261021) in which the
version's summed log loss is NOT below the full version's.

Run from the repo root:  python 25_TESTS/goalie_play_spec.py   (writes 30_OUTPUT/goalie_play_spec_log.txt)
"""
import os
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
SCRIPT_VERSION = "goalie_play_spec.py v1.0 (2026-10-21)"
SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])
PRORATION = {2019: 82 / 70, 2020: 82 / 56}
LEAGUE_AVG, KEEP = 2.189172466, 0.35
TERMS = ["age", "age_sq", "pw", "gs"]
VERSIONS = {"full (age, age squared, forecast, games share)": TERMS, "no age squared": ["age", "pw", "gs"],
            "no forecast": ["age", "age_sq", "gs"], "no games share": ["age", "age_sq", "pw"]}
LOG = []


def log(s=""):
    print(s, flush=True)
    LOG.append(str(s))


def main():
    from skater_forward_projection import norm_name
    log(SCRIPT_VERSION)
    g = pd.read_csv(SOURCE_DIR / "Goalies_WAR.csv")
    g["syr"] = g["Season"].str.split("-").str[0].astype(int) + 2000
    g = g.groupby(["Goalie", "syr"], as_index=False).agg(WAR=("WAR", "sum"), GP=("GP", "sum"))
    g["WAR"] = g["WAR"] * g["syr"].map(PRORATION).fillna(1.0)
    g["nname"] = g["Goalie"].map(norm_name)
    bd = pd.read_csv(OUTPUT_DIR / "goalie_birthdates.csv")
    bd["bd"] = pd.to_datetime(bd["birthdate"].fillna(bd["pp_birthdate"].astype(str).str.split(";").str[0]), errors="coerce")
    g = g.merge(bd[["nname", "syr", "bd"]], on=["nname", "syr"], how="left")
    g["age"] = [np.nan if pd.isna(b) else y - b.year - ((9, 15) < (b.month, b.day)) for b, y in zip(g["bd"], g["syr"])]
    lut = g.set_index(["nname", "syr"])["WAR"].to_dict()
    gp = g.set_index(["nname", "syr"])["GP"].to_dict()
    agem = g.set_index(["nname", "syr"])["age"].to_dict()

    def trailing(n, t0):
        w = [lut.get((n, t0 - k), np.nan) for k in (1, 2, 3)]
        if np.isfinite(w).all():
            return 0.5 * w[0] + 0.3 * w[1] + 0.2 * w[2]
        if np.isfinite(w[0]) and np.isfinite(w[1]):
            return 0.625 * w[0] + 0.375 * w[1]
        return w[0]

    rows = []
    for t0 in range(2009, 2026):
        for n in {n for (n, y) in lut if y == t0 - 1}:
            tr = trailing(n, t0)
            a0 = agem.get((n, t0 - 1))
            if not np.isfinite(tr) or a0 is None or pd.isna(a0):
                continue
            for h in range(6):
                if t0 + h > 2025:
                    break
                a = a0 + 1 + h
                rows.append({"nname": n, "t0": t0, "h": h, "age": a - 27.22, "age_sq": (a - 27.22) ** 2,
                             "pw": KEEP * tr + (1 - KEEP) * LEAGUE_AVG, "gs": gp.get((n, t0 - 1), 0) / 82.0,
                             "y": float(gp.get((n, t0 + h), 0) >= 1)})
    A = pd.DataFrame(rows)
    log(f"rows: {len(A):,} goaltender-seasons ahead, {A['nname'].nunique()} goaltenders, pages 2009-2025")

    log("\nIN SAMPLE (each season ahead; errors clustered by goaltender): terms with p > 0.05")
    for h in range(6):
        x = A[A["h"] == h]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = sm.Logit(x["y"].to_numpy(), sm.add_constant(x[TERMS].to_numpy(float))).fit(
                disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(x["nname"])[0]})
        log(f"  +{h} ({len(x):,}): " + "; ".join(f"{t} {b:+.3f} (p {p:.3f})" for t, b, p in
                                                 zip(TERMS, m.params[1:], m.pvalues[1:])))

    log("\nHELD OUT (pages 2015-2021, each season ahead fitted on pages whose outcome came before the page): log loss")
    E = A[A["t0"].between(2015, 2021)].copy()
    for v, cols in VERSIONS.items():
        E[v] = np.nan
        for t0 in range(2015, 2022):
            for h in range(6):
                tr = A[(A["h"] == h) & (A["t0"] + h < t0)]
                te = E.index[(E["t0"] == t0) & (E["h"] == h)]
                if len(tr) < 50 or not len(te):
                    continue
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    m = sm.Logit(tr["y"].to_numpy(), sm.add_constant(tr[cols].to_numpy(float))).fit(disp=0, maxiter=200)
                E.loc[te, v] = m.predict(sm.add_constant(E.loc[te, cols].to_numpy(float), has_constant="add"))
    E = E.dropna(subset=list(VERSIONS))
    y = E["y"].to_numpy()
    L = {v: -(y * np.log(np.clip(E[v], 1e-6, 1)) + (1 - y) * np.log(np.clip(1 - E[v], 1e-6, 1))).to_numpy() for v in VERSIONS}
    codes, uniq = pd.factorize(E["nname"])
    rng = np.random.default_rng(20261021)
    idx = [rng.integers(0, len(uniq), len(uniq)) for _ in range(2000)]
    full = list(VERSIONS)[0]
    sb = np.bincount(codes, L[full], len(uniq))
    for v in VERSIONS:
        sv = np.bincount(codes, L[v], len(uniq))
        tail = "" if v == full else (f"; p that it is better {1 - np.mean([sv[i].sum() < sb[i].sum() for i in idx]):.3f}, "
                                     f"p that the full version is better {1 - np.mean([sb[i].sum() < sv[i].sum() for i in idx]):.3f}")
        log(f"  {v:<48} {L[v].mean():.4f} ({len(E):,} rows){tail}")
    (OUTPUT_DIR / "goalie_play_spec_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
