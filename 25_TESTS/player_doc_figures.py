"""player_doc_figures.py v1.0 (2026-11-25) -- the tested choices behind "Valuing Players", read from today's runs.

WHY (Thomas, 2026-11-25: "Agreed, build it"). The player document defends each setting of the forecast, the price line
and the goaltender model with a test. Those figures were typed into model_doc.js's REC block from October logs; since
2026-11-25 every test runs on today's model, and this script reads each figure from the output that holds it, so the
builder types none. GUARDED: each figure is matched in its source by a pattern that must match exactly once, and the
build's own scores must equal the forecast audit's.

READS (OUTPUT_DIR): model_choices_current_scores.csv and _log.txt (25_TESTS/model_choices_current.py v1.0),
price_line_spec_tests_log.txt (v1.2), goalie_review_log.txt, goalie_play_spec_log.txt, goalie_line_check_log.txt (that
script's printout, saved), forecast_term_audit_rows.pkl (the all-82-games comparison, computed here on the audit's rows).
WRITES: OUTPUT_DIR/player_doc/numbers.json.

Run from the repo root:  python 25_TESTS/player_doc_figures.py   (seconds)
"""
import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
OUT = Path(os.environ["OUTPUT_DIR"])
SCRIPT_VERSION = "player_doc_figures.py v1.0 (2026-11-25)"
BASE = {"start": 1.1506, "whole": 1.3569, "war": 0.8054}      # forecast_term_audit.py on today's model


def one(pattern, text, what, flags=0):
    m = re.findall(pattern, text, flags)
    if len(m) != 1:
        sys.exit(f"GUARD FAILED: {what}: {len(m)} matches for {pattern!r}")
    return m[0]


def main():
    print(SCRIPT_VERSION)
    N = {"script": SCRIPT_VERSION}

    # ---- the forecast's choices
    sc = pd.read_csv(OUT / "model_choices_current_scores.csv")
    allr = sc[sc.rows_set.str.startswith("ALL")].set_index("version")
    b = allr.loc["base"]
    for k, v in BASE.items():
        if round(float(b[k]), 4) != v:
            sys.exit(f"GUARD FAILED: the build's {k} {b[k]:.4f}, the audit's {v}")
    keep = ["start", "whole", "war", "share", "logloss", "p_build_better_war", "p_version_better_war",
            "p_build_better_start_sq", "p_version_better_start_sq", "p_build_better_whole_sq", "p_version_better_whole_sq",
            "p_build_better_share_sq", "p_version_better_share_sq", "p_build_better_logloss", "p_version_better_logloss"]
    N["choices"] = {v: {k: (None if pd.isna(r[k]) else float(r[k])) for k in keep} for v, r in allr.iterrows()}
    w64 = sc[sc.rows_set.str.contains("60/40")]
    if len(w64) != 2:
        sys.exit("GUARD FAILED: the 60/40 rows")
    N["w6040"] = {"rows": int(w64.rows.iloc[0]), **{v: {k: (None if pd.isna(r[k]) else float(r[k])) for k in keep}
                                                     for v, r in w64.set_index("version").iterrows()}}
    e2 = sc[sc.rows_set.str.startswith("E2")].set_index("version")
    log = (OUT / "model_choices_current_log.txt").read_text(encoding="utf-8")
    c, s_, n_ = one(r"E2: contracts signed after July 1 of their first season, pages 2018-2021: ([\d,]+) contracts, ([\d,]+) "
                    r"contract-seasons, ([\d,]+) players", log, "E2 counts")
    N["e2"] = {"contracts": int(c.replace(",", "")), "seasons": int(s_.replace(",", "")), "players": int(n_.replace(",", "")),
               "played": float(e2.loc["read at July 1", "played"]),
               "jul1_mean": float(e2.loc["read at July 1", "mean_p"]), "jul1_ll": float(e2.loc["read at July 1", "logloss"]),
               "sign_mean": float(e2.loc["read at the signing", "mean_p"]), "sign_ll": float(e2.loc["read at the signing", "logloss"]),
               "p": float(e2.loc["read at the signing", "p_build_better_logloss"])}
    tw = one(r"best (\d\.\d\d) / (\d\.\d\d) / (\d\.\d\d), RMSE (\d\.\d{4})", log, "three-way best")
    N["three_way"] = {"own": float(tw[0]), "comps": float(tw[1]), "league": float(tw[2]), "start": float(tw[3])}
    bands = {}
    for line in log.split("THE AGING-CURVE VERSIONS BY AGE")[1].split("\n")[3:]:
        m = re.match(r"  (.+?)\s{2,}(\d\.\d{4})\s+(\d\.\d{4})\s+(\d\.\d{4})\s*$", line)
        if m:
            bands[m.group(1).strip()] = [float(m.group(i)) for i in (2, 3, 4)]
        elif bands:
            break
    if "base" not in bands or len(bands) != 16:
        sys.exit(f"GUARD FAILED: the age bands ({len(bands)} rows)")
    N["age_bands"] = bands
    bn = one(r"\(player-seasons played, one to five ahead\)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)", log, "age band counts")
    N["age_band_n"] = [int(x.replace(",", "")) for x in bn]
    hh = re.findall(r"yardstick by position D (\d\.\d{4}), F (\d\.\d{4}); pooled (\d\.\d{4})", log)
    if len(hh) != 7:
        sys.exit("GUARD FAILED: the seven pages' bandwidths")
    N["bandwidth_pages"] = [[float(x) for x in t] for t in hh]

    # ---- assuming every player plays all 82 games (Thomas's comment 37), on the audit's own rows and redraws
    D = pd.read_pickle(OUT / "forecast_term_audit_rows.pkl")
    D = D[np.isfinite(D["r|base"])].reset_index(drop=True)
    r, s, p, y = (D[c_].to_numpy() for c_ in ("r|base", "s|base", "p|base", "war_act"))
    lm, l82 = (p * r * s - y) ** 2, (p * r - y) ** 2
    if round(float(np.sqrt(lm.mean())), 4) != BASE["war"]:
        sys.exit("GUARD FAILED: the audit rows do not give the build's season WAR")
    codes, uniq = pd.factorize(D["career_key"])
    rng = np.random.default_rng(20261021)
    sa, sb = np.bincount(codes, l82, len(uniq)), np.bincount(codes, lm, len(uniq))
    p82 = 1.0 - float(np.mean([sb[ix].sum() < sa[ix].sum() for ix in (rng.integers(0, len(uniq), len(uniq)) for _ in range(2000))]))
    N["all82"] = {"war": float(np.sqrt(l82.mean())), "base": float(np.sqrt(lm.mean())), "p_build_better": p82, "rows": int(len(D))}

    # ---- the price line's other forms (price_line_spec_tests.py v1.2, on today's lock)
    pl = (OUT / "price_line_spec_tests_log.txt").read_text(encoding="utf-8")
    one(r"price_line_spec_tests\.py v(1\.2)", pl, "the price-line tests' version")
    n_c = one(r"0\. GUARD: ([\d,]+) contracts \(locked ([\d,]+)\)", pl, "the contracts")
    if n_c[0] != n_c[1]:
        sys.exit("GUARD FAILED: the price-line rows")
    spec = {}
    for name in ("length x forecast (one term)", "length premium by forecast group", "one step: premium below replacement",
                 "quadratic in the forecast", "bend at one forecast win", "separate RFA line", "separate 2022-2025 line"):
        g = one(re.escape(name) + r": log-likelihood ([\d,.]+) \(locked specification ([\d,.]+)\); gain \+([\d.]+), LR ([\d.]+) "
                r"on (\d) df, p ([\d.]+)", pl, name)
        h = one(r"\n  " + re.escape(name) + r"\s+(\d\.\d{4})\s+(\d\.\d{4})\s+(\d+) of 20\s+(\d+) of 20", pl, name + " held out")
        spec[name] = {"gain": float(g[2]), "df": int(g[4]), "p": float(g[5]), "rmse_M": float(h[0]), "mae_M": float(h[1]),
                      "beats": int(h[2])}
    lk = one(r"\n  locked specification\s+(\d\.\d{4})\s+(\d\.\d{4})\s*\n", pl, "the locked line held out")
    st = one(r"length premium a season per year: below 0 ([\d.]+)M, 0 or more ([\d.]+)M", pl, "the step's premiums")
    gs = one(r"per-group premium against the one step: gain \+([\d.]+), LR ([\d.]+) on 2 df, p ([\d.]+)", pl, "group vs step")
    N["spec"] = {"n": int(n_c[0].replace(",", "")), "locked_rmse_M": float(lk[0]), "locked_mae_M": float(lk[1]),
                 "variants": spec, "step_below_M": float(st[0]), "step_above_M": float(st[1]), "group_vs_step_p": float(gs[2])}

    # ---- the price line dated at the signing or at the contract's first season (xnpv1_price_line.py's log)
    xl = (OUT / "xnpv1_price_line_log.txt").read_text(encoding="utf-8")
    sd = one(r"start-dated, with term \(directive 4 alone\)\n.*\n.*\n\s+sigma [\d.]+\s+log-likelihood ([\d,.]+)", xl, "start-dated")
    gd = one(r"SIGNING-dated, with term \(directives 4 \+ 5; TERM-IN line\)\n.*\n.*\n\s+sigma [\d.]+\s+log-likelihood ([\d,.]+)",
             xl, "signing-dated")
    N["dating"] = {"start_ll": float(sd.replace(",", "")), "sign_ll": float(gd.replace(",", ""))}

    # ---- the goaltender model's choices
    gr = (OUT / "goalie_review_log.txt").read_text(encoding="utf-8")
    g_ = one(r"goaltenders\s+([\d,]+) pairs by (\d+) players: season WAR r = ([\d.]+) \(95% ([\d.]+) to ([\d.]+)\); WAR per game "
             r"r = ([\d.]+); 50/30/20 trailing against the season r = ([\d.]+)", gr, "goaltender persistence")
    s2 = one(r"skaters\s+([\d,]+) pairs by ([\d,]+) players: season WAR r = ([\d.]+) \(95% ([\d.]+) to ([\d.]+)\); WAR per game "
             r"r = ([\d.]+); 50/30/20 trailing against the season r = ([\d.]+)", gr, "skater persistence")
    cv = one(r"CV targets: (\d+) goaltender-seasons of 20\+ games with a trailing value, (\d+) goaltenders", gr, "CV targets")
    ag = one(r"as it runs ([\d.]+)\n\s+\+ age \(straight line\)\s+([\d.]+) \(-([\d.]+)%\); p that it is better ([\d.]+)\n"
             r"\s+\+ age and age squared\s+([\d.]+) \(-([\d.]+)%\); p that it is better ([\d.]+)", gr, "the age term")
    sl = one(r"in sample, the forecast's error on age: age (-[\d.]+) \(p = ([\d.]+)\)", gr, "the age slope")
    pu = one(r"as it runs \(no games filter, 2\.19\)\s+keep 0\.35: ([\d.]+) \(at 0\.35: [\d.]+; 0\.30 ([\d.]+); 0\.40 ([\d.]+)\)", gr, "the pull")
    g10 = one(r"a 10-game counting season\s+keep 0\.35: ([\d.]+); on the same rows, as it runs keep 0\.35: ([\d.]+)", gr, "10 games")
    ctl = one(r"decisions: (\d+); qualified ([\d.]+); played if qualified ([\d.]+); weight ([\d.]+)", gr, "control weight")
    cp = one(r"do the groups' qualifying rates differ\? chi-squared ([\d.]+) on (\d) degrees of freedom, p = ([\d.]+)", gr, "groups")
    cal = one(r"\+0 [\d.]+/([\d.]+)/([\d.]+);.*\+5 [\d.]+/([\d.]+)/([\d.]+)", gr, "calibration")
    gp = (OUT / "goalie_play_spec_log.txt").read_text(encoding="utf-8")
    sqp = [float(x) for x in re.findall(r"age_sq [+-][\d.]+ \(p ([\d.]+)\)", gp)]
    if len(sqp) != 6:
        sys.exit("GUARD FAILED: the goaltender age-squared p-values")
    llf = one(r"full \(age, age squared, forecast, games share\)\s+([\d.]+)", gp, "full log loss")
    lln = one(r"no age squared\s+([\d.]+) \(", gp, "no age squared log loss")
    gl = (OUT / "goalie_line_check_log.txt").read_text(encoding="utf-8")
    hl = one(r"with the age term \$([\d.]+)M; without \$([\d.]+)M; with it lower in (\d+) of 20", gl, "goalie line held out")
    N["goalie"] = {"g_pairs": int(g_[0].replace(",", "")), "g_goalies": int(g_[1]), "g_r": float(g_[2]), "g_lo": float(g_[3]),
                   "g_hi": float(g_[4]), "g_rate": float(g_[5]), "g_trail": float(g_[6]),
                   "s_pairs": int(s2[0].replace(",", "")), "s_players": int(s2[1].replace(",", "")), "s_r": float(s2[2]),
                   "s_lo": float(s2[3]), "s_hi": float(s2[4]), "s_rate": float(s2[5]), "s_trail": float(s2[6]),
                   "cv_n": int(cv[0]), "cv_goalies": int(cv[1]), "age_base": float(ag[0]), "age_lin": float(ag[1]),
                   "age_lin_pct": float(ag[2]), "age_lin_p": float(ag[3]), "age_quad": float(ag[4]), "age_quad_pct": float(ag[5]),
                   "age_quad_p": float(ag[6]), "slope": float(sl[0]), "slope_p": float(sl[1]),
                   "pull_mse": float(pu[0]), "pull_30": float(pu[1]), "pull_40": float(pu[2]),
                   "gp10": float(g10[0]), "gp10_base": float(g10[1]),
                   "ctl_n": int(ctl[0]), "ctl_q": float(ctl[1]), "ctl_play": float(ctl[2]), "ctl_w": float(ctl[3]),
                   "ctl_chi": float(cp[0]), "ctl_df": int(cp[1]), "ctl_p": float(cp[2]),
                   "fc0": float(cal[0]), "played0": float(cal[1]), "fc5": float(cal[2]), "played5": float(cal[3]),
                   "sq_p_min": min(sqp), "sq_p_max": max(sqp), "ll_full": float(llf), "ll_nosq": float(lln),
                   "line_aged_M": float(hl[0]), "line_flat_M": float(hl[1]), "line_aged_beats": int(hl[2])}

    # ---- the three terms the forecast's regressions no longer carry: their in-sample p-values in the 2025-26 regressions
    # that still had them (forecast_term_audit.py's run on skater_forecast v2.3, kept in the archive); the test that
    # dropped them is the alternative the document reports
    arch = ROOT / "90_ARCHIVE" / "2026-11-25" / "october_tests" / "forecast_term_audit_insample.csv"
    ins = pd.read_csv(arch)
    N["dropped"] = {}
    for m_, t_ in (("games share", "is_D"), ("chance of playing", "age_sq"), ("chance of playing", "exp_seasons")):
        x = ins[(ins.model == m_) & (ins.term == t_)]
        if len(x) != 13:
            sys.exit(f"GUARD FAILED: {m_} {t_}: {len(x)} seasons ahead")
        N["dropped"][t_] = {"model": m_, "n": int(len(x)), "fail": int((x.p > 0.05).sum()), "p_min": float(x.p.min()),
                            "p_max": float(x.p.max())}

    out = OUT / "player_doc"
    out.mkdir(exist_ok=True)
    (out / "numbers.json").write_text(json.dumps(N, indent=1), encoding="utf-8")
    print(f"wrote {out / 'numbers.json'}: {len(N['choices'])} forecast versions, {len(spec)} price-line forms; "
          f"all 82 games {N['all82']['war']:.4f} against {N['all82']['base']:.4f} (p {N['all82']['p_build_better']:.4f})")


if __name__ == "__main__":
    main()
