"""goalie_review.py -- the goaltender model's choices, tested again after the skater changes (report only).

WHY (Thomas, 2026-10-21, notes 33-35 on "Valuing Players, Draft Picks, and Prospects"): "Goaltenders have a simpler
model, because their WAR varies far more from season to season than a skater's" -- "You cannot simply state that, you
need to show proof"; "No aging curve was fitted for goaltenders: the signal was judged too weak, and the birthdates
needed were then missing for a third of them" -- "You should show that. 2. the birthdates aren't missing anymore";
"It's probably worth revisiting the goalie model just to be sure these decisions are justified still after all the many
changes made". Agreed order: after the forecast audit and the re-lock, before the back-test. TEST ONLY: nothing in
20_CODE changes. The back-test is not read.

THE GOALTENDER MODEL AS IT RUNS (contract_npv.GoalieProjector, _npv_goalie; goalie_value_engine.py):
  forecast   his 50/30/20 WAR over the three seasons before (62.5/37.5 with two, the most recent alone with one; no
             games filter on those seasons), D20-prorated, kept 35% and pulled 65% toward a league average of 2.19 WAR
             (a recovered constant), held flat for every season; no age term
  price      cap share = 0.01398 + 0.01097 x forecast (contract_npv recovers both from the July goalie spine), floored at
             the league minimum; no term, no censoring
  playing    the first season certain; each later season multiplied by one minus a yearly exit risk by quality bucket
             (the skater thresholds) and age group, fitted on goaltender-seasons 2018-2024
DATA: Goalies_WAR.csv (team rows summed, as the model does; D20 proration); ages on September 15 from the NHL's
birthdates (goalie_birthdates.py, 2026-10-21); names normalised as contract_npv normalises them.

PART A  PROOF THAT GOALTENDER WAR VARIES MORE FROM SEASON TO SEASON. Consecutive seasons with 20+ games in both: the
        correlation of season WAR, and of WAR per game, for goaltenders and for skaters (WAR_with_age.csv, the same
        rule); the correlation of the 50/30/20 trailing WAR with the next season. 95% intervals from 2,000 redraws of
        players (seed 20261021).
PART B  AGING. The average change in WAR per game from one age to the next, by age (20+ games in both seasons). Held
        out: the forecast as it runs against the forecast plus an age term (linear; linear and squared) fitted on the
        training goaltenders' errors; 5 folds split by goaltender x 6 seeds, the procedure goalie_value_engine uses to
        choose the 65% pull; targets are goaltender-seasons of 20+ games with a trailing value. In sample: the age
        terms on the forecast's error, errors clustered by goaltender.
PART C  THE PULL'S SETTINGS, held out the same way: the share kept (grid 0 to 1) under (i) today's rules; (ii) a
        10-game counting season on the trailing seasons (skaters' rule); (iii) the league average re-estimated on the
        training goaltenders instead of the recovered 2.19.
PART D  THE PRICE LINE. Standard-level goaltender contracts starting 2015-2025 with a trailing value (goalie_value_engine
        ._rate_sample). The price as it runs (the recovered constants applied to the pulled forecast) against fits on:
        the pulled forecast at the contract's start; the pulled forecast dated at the signing (xnpv1_price_line
        .signing_page); the same, censored at the league minimum; and with a term for contract length. In-sample
        log-likelihood (censored versions) and held-out error (5 groups of goaltenders x 20 repeats, seed 20261005),
        $M at the 2025-26 cap.
PART E  THE CHANCE OF PLAYING. Every goaltender with a forecast on pages 2015-2021, seasons 0-5 ahead: did he play an
        NHL game? (a) the exit chain as it runs (first season certain), its table fitted only on transitions known
        before the page; (b) the same chain with the live 2018-2024 table (look-ahead on early pages; reference);
        (c) one logistic regression per season ahead on age, the forecast and last season's games share, fitted on
        pages before. Log loss and Brier score, all seasons and seasons 1-5.
PART F  THE CONTROL-SEASON WEIGHT: qualify-or-walk decisions on goaltender contracts ending 2018-2024 (as
        contract_npv._calibrate_goalie_control counts them), by forecast group, with a test that the groups differ.

HOW TO RUN (repo root, laptop; needs the PuckPedia export; about 10 minutes):  python 25_TESTS/goalie_review.py
Writes 30_OUTPUT/goalie_review_log.txt.
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
from scipy import stats

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
SCRIPT_VERSION = "goalie_review.py v1.0 (2026-10-21)"
SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])
PRORATION = {2019: 82 / 70, 2020: 82 / 56}
LEAGUE_AVG, KEEP = 2.189172466, 0.35
SEEDS, FOLDS = (0, 1, 2, 3, 4, 5), 5
LOG = []


def log(s=""):
    print(s, flush=True)
    LOG.append(str(s))


def boot_ci(df, key, fn, n=2000, seed=20261021):
    """95% interval of fn(df) from redraws of the units in column `key`."""
    rng = np.random.default_rng(seed)
    units = df[key].unique()
    groups = {u: g for u, g in df.groupby(key)}
    vals = []
    for _ in range(n):
        pick = rng.choice(units, len(units), replace=True)
        vals.append(fn(pd.concat([groups[u] for u in pick], ignore_index=True)))
    return np.percentile(vals, [2.5, 97.5])


def main():
    from skater_forward_projection import norm_name, league_min_path
    log(SCRIPT_VERSION)
    # ---- goaltender seasons -----------------------------------------------------------------------------------------
    g = pd.read_csv(SOURCE_DIR / "Goalies_WAR.csv")
    g["syr"] = g["Season"].str.split("-").str[0].astype(int) + 2000
    g = g.groupby(["Goalie", "syr"], as_index=False).agg(WAR=("WAR", "sum"), GP=("GP", "sum"))
    g["WAR"] = g["WAR"] * g["syr"].map(PRORATION).fillna(1.0)
    g["GP82"] = g["GP"] * g["syr"].map(PRORATION).fillna(1.0)
    g["nname"] = g["Goalie"].map(norm_name)
    bd = pd.read_csv(OUTPUT_DIR / "goalie_birthdates.csv")
    bd["bd"] = pd.to_datetime(bd["birthdate"], errors="coerce")
    pp_bd = bd.dropna(subset=["pp_birthdate"]).assign(b2=lambda x: pd.to_datetime(x["pp_birthdate"].str.split(";").str[0]))
    g = g.merge(bd[["nname", "syr", "bd"]], on=["nname", "syr"], how="left")
    fill = pp_bd.drop_duplicates("nname").set_index("nname")["b2"]
    g["bd"] = g["bd"].fillna(g["nname"].map(fill))
    g["age"] = [np.nan if pd.isna(b) else y - b.year - ((9, 15) < (b.month, b.day)) for b, y in zip(g["bd"], g["syr"])]
    log(f"goaltender-seasons: {len(g):,} ({g['nname'].nunique()} goaltenders); with an age {int(g['age'].notna().sum()):,}")
    lut = g.set_index(["nname", "syr"])["WAR"].to_dict()
    gplut = g.set_index(["nname", "syr"])["GP"].to_dict()

    def trailing(n, t0, min_gp=0):
        w = [lut.get((n, t0 - k)) if gplut.get((n, t0 - k), 0) >= min_gp else None for k in (1, 2, 3)]
        w = [np.nan if v is None else v for v in w]
        if np.isfinite(w).all():
            return 0.5 * w[0] + 0.3 * w[1] + 0.2 * w[2]
        if np.isfinite(w[0]) and np.isfinite(w[1]):
            return 0.625 * w[0] + 0.375 * w[1]
        if np.isfinite(w[0]):
            return w[0]
        return np.nan

    # ================================================================================================= PART A
    log("\nPART A. SEASON-TO-SEASON PERSISTENCE (consecutive seasons, 20+ games in both; D20-prorated)")
    sk = pd.read_csv(OUTPUT_DIR / "WAR_with_age.csv", usecols=["Player", "Season", "Position", "GP", "WAR"])
    sk["syr"] = sk["Season"].str.split("-").str[0].astype(int) + 2000
    sk = sk.groupby(["Player", "Position", "syr"], as_index=False).agg(WAR=("WAR", "sum"), GP=("GP", "sum"))
    sk["WAR"] = sk["WAR"] * sk["syr"].map(PRORATION).fillna(1.0)
    sk["key"] = sk["Player"] + "|" + sk["Position"].astype(str)
    gg = g.assign(key=g["nname"])

    def pairs(df):
        a = df[df["GP"] >= 20][["key", "syr", "WAR", "GP"]]
        b = a.assign(syr=a["syr"] - 1)
        p = a.merge(b, on=["key", "syr"], suffixes=("", "_next"))
        p["rate"], p["rate_next"] = p["WAR"] / p["GP"], p["WAR_next"] / p["GP_next"]
        return p

    def trail_pairs(df):
        L = df.set_index(["key", "syr"])["WAR"].to_dict()
        G = df.set_index(["key", "syr"])["GP"].to_dict()
        rows = []
        for r in df[df["GP"] >= 20].itertuples():
            w = [L.get((r.key, r.syr - k)) if G.get((r.key, r.syr - k), 0) >= 20 else None for k in (1, 2, 3)]
            if w[0] is None:
                continue
            if None not in w:
                t = 0.5 * w[0] + 0.3 * w[1] + 0.2 * w[2]
            elif w[1] is not None:
                t = 0.625 * w[0] + 0.375 * w[1]
            else:
                t = w[0]
            rows.append({"key": r.key, "trail": t, "WAR": r.WAR})
        return pd.DataFrame(rows)

    res_a = {}
    for lab, df in (("goaltenders", gg), ("skaters", sk)):
        p = pairs(df)
        tp = trail_pairs(df)
        c1 = float(np.corrcoef(p["WAR"], p["WAR_next"])[0, 1])
        c2 = float(np.corrcoef(p["rate"], p["rate_next"])[0, 1])
        c3 = float(np.corrcoef(tp["trail"], tp["WAR"])[0, 1])
        ci1 = boot_ci(p, "key", lambda x: np.corrcoef(x["WAR"], x["WAR_next"])[0, 1], n=500)
        ci3 = boot_ci(tp, "key", lambda x: np.corrcoef(x["trail"], x["WAR"])[0, 1], n=500)
        res_a[lab] = (c1, c2, c3)
        log(f"  {lab:<12} {len(p):,} pairs by {p['key'].nunique():,} players: season WAR r = {c1:.3f} "
            f"(95% {ci1[0]:.3f} to {ci1[1]:.3f}); WAR per game r = {c2:.3f}; 50/30/20 trailing against the season "
            f"r = {c3:.3f} (95% {ci3[0]:.3f} to {ci3[1]:.3f}; {len(tp):,} seasons)")

    # ================================================================================================= CV machinery
    tg = []
    for r in g[g["GP"] >= 20].itertuples():
        tr = trailing(r.nname, r.syr)
        if np.isfinite(tr):
            tg.append({"nname": r.nname, "syr": r.syr, "actual": r.WAR, "trail": tr, "age": r.age,
                       "trail10": trailing(r.nname, r.syr, 10)})
    T = pd.DataFrame(tg)
    log(f"\nCV targets: {len(T):,} goaltender-seasons of 20+ games with a trailing value, {T['nname'].nunique()} goaltenders "
        f"(goalie_value_engine.estimate_lambda's rule); with an age {int(T['age'].notna().sum()):,}")

    def folds(seed):
        rng = np.random.default_rng(seed)
        pl = T["nname"].unique()
        f = {p: i % FOLDS for i, p in enumerate(rng.permutation(pl))}
        return T["nname"].map(f).to_numpy()

    def cv(pred_fn):
        """Mean squared error over seeds x folds; pred_fn(train, test) -> predictions for test."""
        out, per = [], np.zeros(len(T))
        for s in SEEDS:
            fo = folds(s)
            for f in range(FOLDS):
                tr, te = fo != f, fo == f
                p = pred_fn(T[tr], T[te])
                out.append(float(np.mean((p - T["actual"].to_numpy()[te]) ** 2)))
                if s == 0:
                    per[te] = p
        return float(np.mean(out)), per

    # ================================================================================================= PART B
    log("\nPART B. AGING")
    pb = pairs(gg).merge(g[["nname", "syr", "age"]].rename(columns={"nname": "key"}), on=["key", "syr"])
    pb["d_rate"] = (pb["rate_next"] - pb["rate"]) * 60          # WAR per 60 games
    ag = pb.dropna(subset=["age"]).groupby("age")["d_rate"].agg(["mean", "count"])
    log("  average change in WAR per 60 games from age a to a+1 (20+ games both seasons): " + "; ".join(
        f"{int(a)}: {m:+.2f} (n {int(n)})" for a, (m, n) in ag.iterrows() if n >= 10))
    xb = pb.dropna(subset=["age"])
    rb = sm.OLS(xb["d_rate"].to_numpy(float), sm.add_constant(np.column_stack([xb["age"].to_numpy(float) - 30]))).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(xb["key"])[0]})
    log(f"  the yearly change against age (a straight line, errors clustered by goaltender): {rb.params[1]:+.3f} WAR per 60 "
        f"games for each year older (p = {rb.pvalues[1]:.3f}); at 30 {rb.params[0]:+.3f} (p = {rb.pvalues[0]:.3f})")
    base_mse, base_per = cv(lambda tr, te: KEEP * te["trail"].to_numpy() + (1 - KEEP) * LEAGUE_AVG)

    def age_arm(deg):
        def f(tr, te):
            p_tr = KEEP * tr["trail"] + (1 - KEEP) * LEAGUE_AVG
            ok = tr["age"].notna()
            e = (tr["actual"] - p_tr)[ok]
            a = tr.loc[ok, "age"] - 30
            X = np.column_stack([np.ones(ok.sum())] + [a ** k for k in range(1, deg + 1)])
            b = np.linalg.lstsq(X, e.to_numpy(), rcond=None)[0]
            at = te["age"].fillna(30) - 30
            Xt = np.column_stack([np.ones(len(te))] + [at ** k for k in range(1, deg + 1)])
            return (KEEP * te["trail"] + (1 - KEEP) * LEAGUE_AVG).to_numpy() + Xt @ b
        return f

    def p_redraw(e_new, e_base, seed=20261021, n=2000):
        """One-sided: the share of redraws of goaltenders in which the new version's summed squared error is NOT below
        the base's (seed 0's out-of-fold predictions)."""
        codes, uniq = pd.factorize(T["nname"])
        a = np.bincount(codes, e_new, len(uniq)); b = np.bincount(codes, e_base, len(uniq))
        rng = np.random.default_rng(seed)
        return 1.0 - float(np.mean([a[ix].sum() < b[ix].sum() for ix in (rng.integers(0, len(uniq), len(uniq)) for _ in range(n))]))

    y = T["actual"].to_numpy()
    eb = (base_per - y) ** 2
    log(f"  held out, mean squared error of season WAR ({len(SEEDS)} seeds x {FOLDS} folds by goaltender): as it runs "
        f"{base_mse:.4f}")
    for deg, lab in ((1, "+ age (straight line)"), (2, "+ age and age squared")):
        m, per = cv(age_arm(deg))
        log(f"    {lab:<24} {m:.4f} ({100 * (m / base_mse - 1):+.2f}%); p that it is better {p_redraw((per - y) ** 2, eb):.3f}")
    xi = T.dropna(subset=["age"])
    ei = xi["actual"] - (KEEP * xi["trail"] + (1 - KEEP) * LEAGUE_AVG)
    ri = sm.OLS(ei.to_numpy(float), sm.add_constant(np.column_stack([xi["age"].to_numpy(float) - 30, (xi["age"].to_numpy(float) - 30) ** 2]))).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(xi["nname"])[0]})
    log(f"  in sample, the forecast's error on age: age {ri.params[1]:+.4f} (p = {ri.pvalues[1]:.3f}), age squared "
        f"{ri.params[2]:+.4f} (p = {ri.pvalues[2]:.3f}); joint p = {float(ri.f_test(np.eye(3)[1:]).pvalue):.3f}")

    # ================================================================================================= PART C
    log("\nPART C. THE PULL TOWARD THE LEAGUE AVERAGE (held out as in Part B; grid of the share kept, 0 to 1 in 0.05)")
    grid = np.round(np.arange(0, 1.0001, 0.05), 2)

    def best(colname, target_fn):
        sc = {k: cv(lambda tr, te, k=k: k * te[colname].to_numpy() + (1 - k) * target_fn(tr))[0] for k in grid}
        kb = min(sc, key=sc.get)
        return kb, sc

    for lab, col, tf in (("as it runs (no games filter, 2.19)", "trail", lambda tr: LEAGUE_AVG),
                         ("a 10-game counting season", "trail10", lambda tr: LEAGUE_AVG),
                         ("league average from the training goaltenders", "trail", lambda tr: tr["actual"].mean())):
        TT = T if col == "trail" else T[np.isfinite(T[col])]
        if col != "trail":
            keep_rows = np.isfinite(T[col]).to_numpy()
            log(f"  ({lab}: {int((~keep_rows).sum())} targets lose their trailing value and drop out of this row's scores)")
            T_save = T.copy()
            globals_T = T_save[keep_rows].reset_index(drop=True)
            kb, sc = None, None
            # score on the rows both versions answer
            saveT = T
            Tsub = saveT[keep_rows].reset_index(drop=True)
            def cv_sub(fn):
                outl = []
                for s in SEEDS:
                    rng = np.random.default_rng(s)
                    pl = Tsub["nname"].unique()
                    fmap = {p: i % FOLDS for i, p in enumerate(rng.permutation(pl))}
                    fo = Tsub["nname"].map(fmap).to_numpy()
                    for f in range(FOLDS):
                        tr_, te_ = Tsub[fo != f], Tsub[fo == f]
                        outl.append(float(np.mean((fn(tr_, te_) - te_["actual"].to_numpy()) ** 2)))
                return float(np.mean(outl))
            sc = {k: cv_sub(lambda tr, te, k=k: k * te[col].to_numpy() + (1 - k) * LEAGUE_AVG) for k in grid}
            sc0 = {k: cv_sub(lambda tr, te, k=k: k * te["trail"].to_numpy() + (1 - k) * LEAGUE_AVG) for k in grid}
            kb, kb0 = min(sc, key=sc.get), min(sc0, key=sc0.get)
            log(f"  {lab:<46} keep {kb:.2f}: {sc[kb]:.4f}; on the same rows, as it runs keep {kb0:.2f}: {sc0[kb0]:.4f}")
            continue
        kb, sc = best(col, tf)
        log(f"  {lab:<46} keep {kb:.2f}: {sc[kb]:.4f} (at 0.35: {sc[0.35]:.4f}; 0.30 {sc[0.3]:.4f}; 0.40 {sc[0.4]:.4f})")
    log(f"  the league average of the 20+ game goaltender-seasons: {T['actual'].mean():.3f} (the model uses {LEAGUE_AVG:.3f})")

    # ================================================================================================= PART D
    log("\nPART D. THE PRICE LINE")
    import goalie_value_engine as GVE
    import xnpv1_price_line as XPL
    import contract_npv as CN
    raw = pd.read_excel(GVE.F_CONTRACT_XLSX)
    import contract_source as CS
    raw["start_yr"] = CS.contract_terms(raw)["first_yr"]
    d = raw[(raw["position"] == "Goaltender") & (raw["contract_level"] == "standard_level")
            & raw["start_yr"].between(2015, 2025)].copy()
    d["nname"] = CS.war_full_name(d, d["first_name"].astype(str) + " " + d["last_name"].astype(str)).map(norm_name)
    d["cap"] = d["start_yr"].map(lambda s: GVE.ceiling_for(int(s))[0])
    d["cap_pct"] = d["aav"] / d["cap"]
    d["floor_pct"] = d["start_yr"].map(league_min_path) / d["cap"]
    d["signed"] = pd.to_datetime(d["signing_date"], errors="coerce")
    d["tr_start"] = [trailing(n, int(s)) for n, s in zip(d["nname"], d["start_yr"])]
    pg = [XPL.signing_page(s) for s in d["signed"]]
    d["page"] = [p if ok else np.nan for p, ok in pg]
    d["tr_sign"] = [trailing(n, int(p)) if np.isfinite(p) else np.nan for n, p in zip(d["nname"], d["page"])]
    d = d[np.isfinite(d["tr_start"]) & np.isfinite(d["tr_sign"]) & d["cap_pct"].notna()].reset_index(drop=True)
    d["f_start"] = KEEP * d["tr_start"] + (1 - KEEP) * LEAGUE_AVG
    d["f_sign"] = KEEP * d["tr_sign"] + (1 - KEEP) * LEAGUE_AVG
    d["length"] = pd.to_numeric(d["length"], errors="coerce")
    cap25 = GVE.ceiling_for(2025)[0]
    log(f"  contracts: {len(d):,} standard-level goaltender contracts starting 2015-2025 with a trailing value at the start "
        f"and at the signing ({int((d['cap_pct'] <= d['floor_pct'] + 1e-12).sum())} at the league minimum); "
        f"contract_npv's constants: alpha {CN.ALPHA_G:.5f}, beta {CN.BETA_G:.5f}")
    live = np.maximum(CN.ALPHA_G + CN.BETA_G * d["f_start"], d["floor_pct"])
    log(f"  as it runs (contract_npv's constants on the pulled forecast at the start, floored): root mean squared error "
        f"${np.sqrt(np.mean((live - d['cap_pct']) ** 2)) * cap25 / 1e6:.3f}M, mean error "
        f"{np.mean(live - d['cap_pct']) * cap25 / 1e6:+.3f}M (in sample for every version below)")

    def design(col, term):
        cols = [d[col].to_numpy(float)] + ([d["length"].to_numpy(float)] if term else [])
        return np.column_stack(cols)

    def ols_pred(Xtr, ytr, Xte):
        A = np.column_stack([np.ones(len(Xtr)), Xtr]); b = np.linalg.lstsq(A, ytr, rcond=None)[0]
        return np.column_stack([np.ones(len(Xte)), Xte]) @ b

    def tobit_pred(Xtr, ytr, ftr, Xte, fte):
        f = XPL.fit_censored(ytr, Xtr, ftr)
        mu = np.column_stack([np.ones(len(Xte)), Xte]) @ np.asarray(f["coef"])
        z = (fte - mu) / f["sigma"]
        return fte * stats.norm.cdf(z) + mu * (1 - stats.norm.cdf(z)) + f["sigma"] * stats.norm.pdf(z), f

    versions = {"pulled forecast at the start, least squares": ("f_start", False, "ols"),
                "dated at the signing, least squares": ("f_sign", False, "ols"),
                "dated at the signing, censored": ("f_sign", False, "tobit"),
                "dated at the signing, censored, with term": ("f_sign", True, "tobit")}
    yv, fv = d["cap_pct"].to_numpy(float), d["floor_pct"].to_numpy(float)
    for lab, (col, term, how) in versions.items():
        X = design(col, term)
        if how == "ols":
            p = np.maximum(ols_pred(X, yv, X), fv)
            r = sm.OLS(yv, sm.add_constant(X)).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d["nname"])[0]})
            log(f"  {lab:<46} ${r.params[0] * cap25 / 1e6:.2f}M + ${r.params[1] * cap25 / 1e6:.2f}M per WAR "
                f"(p {r.pvalues[1]:.3g}); R-squared {r.rsquared:.3f}")
        else:
            p, f = tobit_pred(X, yv, fv, X, fv)
            se_line = XPL.as_line(f, term) if False else None
            ll = None
            log(f"  {lab:<46} ${f['coef'][0] * cap25 / 1e6:.2f}M + ${f['coef'][1] * cap25 / 1e6:.2f}M per WAR"
                + (f" + ${f['coef'][2] * cap25 / 1e6:.2f}M per year of term" if term else "")
                + f"; sigma ${f['sigma'] * cap25 / 1e6:.2f}M")
    # held out
    rng = np.random.default_rng(20261005)
    pl = d["nname"].unique()
    errs = {k: [] for k in ["as it runs"] + list(versions)}
    for rep in range(20):
        fmap = dict(zip(pl, rng.permutation(len(pl)) % 5))
        fo = d["nname"].map(fmap).to_numpy()
        pred = {k: np.full(len(d), np.nan) for k in versions}
        for f_ in range(5):
            tr, te = fo != f_, fo == f_
            for k, (col, term, how) in versions.items():
                X = design(col, term)
                pred[k][te] = (np.maximum(ols_pred(X[tr], yv[tr], X[te]), fv[te]) if how == "ols"
                               else tobit_pred(X[tr], yv[tr], fv[tr], X[te], fv[te])[0])
        errs["as it runs"].append(float(np.sqrt(np.mean((live - yv) ** 2))) * cap25 / 1e6)
        for k in versions:
            errs[k].append(float(np.sqrt(np.mean((pred[k] - yv) ** 2))) * cap25 / 1e6)
    b0 = np.array(errs["dated at the signing, censored, with term"])
    log("  held out (5 groups of goaltenders x 20 repeats): root mean squared error of the cap hit, $M at the 2025-26 cap")
    for k, v in errs.items():
        v = np.array(v)
        log(f"    {k:<46} {v.mean():.3f}" + ("" if k == "as it runs" else
                                              f"   (beats 'as it runs' in {int((v < np.array(errs['as it runs'])).sum())} of 20)"))

    # ================================================================================================= PART E
    log("\nPART E. THE CHANCE OF PLAYING (did he play an NHL game in the season)")
    from exit_hazard import build_transitions, build_hazard_table, bucket, age_group
    dg = build_transitions(CN.F_GOALIE_WAR, None, name_col="Goalie", t_first=2007, t_last=2025)
    dg["nname"] = dg["player"].map(norm_name)
    dg = dg.merge(g[["nname", "syr", "age"]].rename(columns={"syr": "t"}), on=["nname", "t"], how="left", suffixes=("_x", ""))
    dg["age_grp"] = dg["age"].map(age_group)
    live_tab = build_hazard_table(dg[dg["t"].between(2018, 2024)])
    played = {(n, y) for (n, y), gp in gplut.items() if gp >= 1}
    rows = []
    for t0 in range(2015, 2022):
        tab = build_hazard_table(dg[dg["t"] <= t0 - 2])
        for n in {n for (n, y) in lut if y == t0 - 1}:
            tr = trailing(n, t0)
            if not np.isfinite(tr):
                continue
            pw = KEEP * tr + (1 - KEEP) * LEAGUE_AVG
            a0 = g.loc[(g["nname"] == n) & (g["syr"] == t0 - 1), "age"]
            a0 = None if a0.empty or pd.isna(a0.iloc[0]) else float(a0.iloc[0]) + 1
            gs = gplut.get((n, t0 - 1), 0) / 82.0
            S_d = S_l = 1.0
            for h in range(6):
                if t0 + h > 2025:
                    break
                if h > 0:
                    a_ = None if a0 is None else a0 + h - 1
                    for which, T_ in (("d", tab), ("l", live_tab)):
                        hz = T_.get((bucket(pw), age_group(a_) if a_ is not None else "unknown"),
                                    T_.get((bucket(pw), "ALL"), 0.0))
                        if which == "d":
                            S_d *= 1 - hz
                        else:
                            S_l *= 1 - hz
                rows.append({"nname": n, "t0": t0, "h": h, "pw": pw, "age": a0 if a0 is None else a0 + h, "gs": gs,
                             "y": float((n, t0 + h) in played), "chain": S_d, "chain_live": S_l})
    E = pd.DataFrame(rows)
    # (c) logistic per season ahead, fitted on pages before (outcome season before t0)
    allrows = []
    for t0 in range(2009, 2026):
        for n in {n for (n, y) in lut if y == t0 - 1}:
            tr = trailing(n, t0)
            if not np.isfinite(tr):
                continue
            a0 = g.loc[(g["nname"] == n) & (g["syr"] == t0 - 1), "age"]
            a0 = np.nan if a0.empty or pd.isna(a0.iloc[0]) else float(a0.iloc[0]) + 1
            for h in range(6):
                if t0 + h > 2025:
                    break
                allrows.append({"nname": n, "t0": t0, "h": h, "pw": KEEP * tr + (1 - KEEP) * LEAGUE_AVG,
                                "age": a0 + h, "gs": gplut.get((n, t0 - 1), 0) / 82.0,
                                "y": float((n, t0 + h) in played)})
    A_ = pd.DataFrame(allrows).dropna(subset=["age"])
    E["logit"] = np.nan
    for t0 in range(2015, 2022):
        for h in range(6):
            tr_ = A_[(A_["h"] == h) & (A_["t0"] + h < t0)]
            te_ = E.index[(E["t0"] == t0) & (E["h"] == h) & E["age"].notna()]
            if len(tr_) < 50 or not len(te_):
                continue
            X = np.column_stack([tr_["age"] - 30, (tr_["age"] - 30) ** 2, tr_["pw"], tr_["gs"]])
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                m = sm.Logit(tr_["y"].to_numpy(), sm.add_constant(X)).fit(disp=0, maxiter=200)
            xe = E.loc[te_]
            Xe = np.column_stack([xe["age"] - 30, (xe["age"] - 30) ** 2, xe["pw"], xe["gs"]])
            E.loc[te_, "logit"] = m.predict(sm.add_constant(Xe, has_constant="add"))
    ok = E["logit"].notna()
    log(f"  {int(ok.sum()):,} goaltender-seasons ({E.loc[ok, 'nname'].nunique()} goaltenders, pages 2015-2021, 0-5 ahead) "
        f"answered by every version; played {E.loc[ok, 'y'].mean():.3f}")

    def ll(p, y_):
        p = np.clip(p, 1e-6, 1 - 1e-6)
        return float(np.mean(-(y_ * np.log(p) + (1 - y_) * np.log(1 - p))))

    for lab, mask in (("all seasons 0-5 ahead", ok), ("seasons 1-5 ahead", ok & (E["h"] > 0))):
        x = E[mask]
        log(f"  {lab} ({len(x):,}; played {x['y'].mean():.3f}): log loss / Brier -- chain, table before the page "
            f"{ll(x['chain'], x['y']):.4f} / {np.mean((x['chain'] - x['y']) ** 2):.4f}; chain, live 2018-2024 table "
            f"{ll(x['chain_live'], x['y']):.4f} / {np.mean((x['chain_live'] - x['y']) ** 2):.4f}; logistic by season ahead "
            f"{ll(x['logit'], x['y']):.4f} / {np.mean((x['logit'] - x['y']) ** 2):.4f}")
    log("  mean forecast against the share who played, by season ahead (chain before the page / logistic / played): " + "; ".join(
        f"+{h} {x['chain'].mean():.3f}/{x['logit'].mean():.3f}/{x['y'].mean():.3f}" for h, x in E[ok].groupby("h")))

    # ================================================================================================= PART F
    log("\nPART F. THE CONTROL-SEASON WEIGHT (goaltender contracts ending 2018-2024 with the player a restricted free agent)")
    sp = pd.read_csv(OUTPUT_DIR / "contract_season_spine.csv")
    sp = sp[sp["position"] == "Goaltender"].copy()
    sp["nname"] = CS.war_full_name(sp, sp["first_name"].astype(str) + " " + sp["last_name"].astype(str)).map(norm_name)
    last = sp.sort_values("season_start").groupby("contract_id").tail(1)
    el = last[last["season_start"].between(2018, 2024) & last["pp_expiry"].isin(["RFA", "UFA no QO"])].copy()
    el["there"] = [gplut.get((n, int(s)), 0) >= 1 for n, s in zip(el["nname"], el["season_start"])]
    el = el[el["there"]].copy()
    el["q"] = el["pp_expiry"] == "RFA"
    el["plays"] = [gplut.get((n, int(s) + 1), 0) >= 1 for n, s in zip(el["nname"], el["season_start"])]
    el["pw"] = [KEEP * trailing(n, int(s) + 1) + (1 - KEEP) * LEAGUE_AVG for n, s in zip(el["nname"], el["season_start"])]
    el["grp"] = pd.cut(el["pw"], [-99, 1.5, 2.0, 2.5, 99], labels=["below 1.5", "1.5-2", "2-2.5", "2.5+"])
    log(f"  decisions: {len(el)}; qualified {el['q'].mean():.3f}; played if qualified {el.loc[el['q'], 'plays'].mean():.3f}; "
        f"weight {el['q'].mean() * el.loc[el['q'], 'plays'].mean():.3f} (contract_npv's own: 0.893 x 0.859 = 0.767, 103)")
    for gname, x in el.groupby("grp", observed=True):
        log(f"    forecast {gname:<10} n {len(x):>3}: qualified {x['q'].mean():.3f}; played if qualified "
            f"{(x.loc[x['q'], 'plays'].mean() if x['q'].any() else float('nan')):.3f}")
    ct = pd.crosstab(el["grp"], el["q"])
    if ct.shape == (4, 2) or ct.shape[1] == 2:
        chi = stats.chi2_contingency(ct)
        log(f"  do the groups' qualifying rates differ? chi-squared {chi[0]:.2f} on {chi[2]} degrees of freedom, p = {chi[1]:.3f}")
    (OUTPUT_DIR / "goalie_review_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    log(f"\nwritten: {OUTPUT_DIR / 'goalie_review_log.txt'}")


if __name__ == "__main__":
    main()
