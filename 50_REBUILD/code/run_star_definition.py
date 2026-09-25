"""run_star_definition.py -- what counts as a "star", tested rather than assumed.

EXPERIMENTAL (50_REBUILD). Development pages 2015-2021 only. An evaluation of a
REPORTING GROUP: no model is fitted or changed, and nothing is adopted.

WHY
    Every star result so far uses the harness's tier "3+": a trailing total of
    three wins or more, where the trailing total is the locked 60/40 blend of
    the two latest qualifying seasons, falling back to the latest, then the
    second, then the third (`forecast_harness.subjects_at`). The cut-off was
    inherited, not tested. WAR totals are already stated on an 82-game basis
    for the two shortened seasons (D20 proration in `player_season_table`), so
    the scale is comparable across pages; whether the cut-off matters is the
    open question.

THE DEFINITIONS, DECLARED BEFORE THE RUN (membership fixed per player and page,
all from information the page could see)
    T2.0 .. T4.0  the 60/40 trailing total at or above 2.0, 2.5, 3.0 (the
                  current definition), 3.5, 4.0
    P2, P5, P10   the top 2%, 5%, 10% of the page's subjects by that total
    R5            the top 5% by the 60/40 trailing RATE per 82, among subjects
                  whose 60/40 games are at least 40 (same fallbacks)

THE TESTS
    1. membership: size per page, distinct players, overlap with T3.0;
    2. the adopted leader's miss across the whole level range, by page
       percentile of the trailing total, with no cut-off at all;
    3. the headline star figures under every definition;
    4. whether any scored candidate's verdict on the star group changes.
       DECLARED: a definition "makes a difference" to a candidate if the share
       of career-resamples in which the candidate's squared season-WAR error on
       the group is below the adopted leader's lands on the other side of 50%,
       or crosses into or out of the decisive bands (>= 1950/2000 or <= 50/2000),
       relative to the T3.0 result.

INPUTS: the harness rows already written by `run_star_residual.py` (v1.0-v1.4),
each file carrying the adopted leader and its candidates on identical rows.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
from player_season_table import build as build_table, birthdate_source
import run_skater_contract_test as RSC

SCRIPT_VERSION = "1.0"

FILES = {"star_residual.csv": ["survivor_aging", "no_level_aging", "reduced_form"],
         "star_residual_v11.csv": ["no_level_matched", "level_hinge"],
         "star_residual_v12.csv": ["multi_level"],
         "star_residual_v13.csv": ["sustained"],
         "star_residual_v14.csv": ["recency"]}
LABELS = {"survivor_aging": "survivors-only curve", "no_level_aging": "no level terms, unmatched",
          "reduced_form": "per-season regression", "no_level_matched": "no level terms, matched",
          "level_hinge": "second level slope", "multi_level": "multi-season level",
          "sustained": "sustained level", "recency": "recency weighting"}
DEFS = ["T2.0", "T2.5", "T3.0", "T3.5", "T4.0", "P2", "P5", "P10", "R5"]
COLS = ["variant", "career_key", "page", "h", "trailing_war", "played", "e_rate", "e_war"]


def trailing_rate(table: pd.DataFrame) -> pd.DataFrame:
    """60/40 trailing WAR per 82 and games, same seasons and fallbacks as the
    harness's trailing total, per (career_key, page)."""
    s = table[table["GP"] >= C.MIN_GP][["career_key", "syr", "WAR_82", "GP"]]
    out = []
    for page in C.DEV_PAGES:
        t1, t2, t3 = page - 1, page - 2, page - 3
        g = {t: s[s["syr"] == t].set_index("career_key") for t in (t1, t2, t3)}
        keys = sorted(set().union(*[set(v.index) for v in g.values()]))
        f = pd.DataFrame(index=pd.Index(keys, name="career_key"))
        for col in ("WAR_82", "GP"):
            a, b, c = (g[t][col].reindex(f.index) for t in (t1, t2, t3))
            f[col] = (a * 0.6 + b * 0.4).fillna(a).fillna(b).fillna(c)
        f["page"] = page
        out.append(f.reset_index())
    return pd.concat(out, ignore_index=True).rename(columns={"WAR_82": "tr_rate", "GP": "tr_gp"})


def membership(base: pd.DataFrame) -> pd.DataFrame:
    """One row per (career_key, page) with a boolean column per definition."""
    m = base[["career_key", "page", "trailing_war", "tr_rate", "tr_gp"]].drop_duplicates(
        ["career_key", "page"]).copy()
    for x in (2.0, 2.5, 3.0, 3.5, 4.0):
        m[f"T{x:.1f}"] = m["trailing_war"] >= x
    for p in (2, 5, 10):
        cut = m.groupby("page")["trailing_war"].transform(lambda v: v.quantile(1 - p / 100))
        m[f"P{p}"] = m["trailing_war"] >= cut
    elig = m["tr_gp"] >= 40
    cut = m[elig].groupby("page")["tr_rate"].quantile(0.95)
    m["R5"] = elig & (m["tr_rate"] >= m["page"].map(cut))
    return m


def main() -> None:
    C.banner("run_star_definition.py", SCRIPT_VERSION)
    path, how = birthdate_source()
    C.log(f"  birthdates: {how}")
    table = build_table(birthdate_csv=path, verbose=False)
    runs = {}
    for f, cands in FILES.items():
        d = pd.read_csv(C.out_path(f), low_memory=False, usecols=COLS)
        runs[f] = (d, cands)
    ref = runs["star_residual_v14.csv"][0]
    ref = ref[ref["variant"] == "adopted"].copy()
    tr = trailing_rate(table)
    ref = ref.merge(tr, on=["career_key", "page"], how="left", validate="many_to_one")
    mem = membership(ref)
    C.log("")

    # ---- 1. membership ---------------------------------------------------
    C.log("1. MEMBERSHIP. Per page: members (min to max); distinct players over the")
    C.log("seven pages; overlap with the current definition (T3.0).")
    C.log("")
    C.log(f"    {'definition':<12}{'per page':>12}{'players':>9}{'in T3.0':>10}{'T3.0 in it':>12}")
    t3 = mem["T3.0"]
    for k in DEFS:
        per = mem.groupby("page")[k].sum()
        both = (mem[k] & t3).sum()
        C.log(f"    {k:<12}{f'{per.min()}-{per.max()}':>12}{mem.loc[mem[k], 'career_key'].nunique():>9}"
              f"{both / max(mem[k].sum(), 1):>10.0%}{both / max(t3.sum(), 1):>12.0%}")
    cuts = mem.groupby("page")["trailing_war"].quantile([0.90, 0.95, 0.98]).unstack()
    C.log("")
    C.log("  page-relative cut-offs on the trailing total, by page (P10 / P5 / P2):")
    for pg, r in cuts.iterrows():
        C.log(f"    {pg}: {r[0.90]:.2f} / {r[0.95]:.2f} / {r[0.98]:.2f}")
    C.log("")

    # ---- 2. the miss across the level range, no cut-off --------------------
    ref["pct"] = ref.groupby(["page", "h"])["trailing_war"].rank(pct=True)
    bands = [0, 0.50, 0.75, 0.90, 0.95, 0.98, 1.0001]
    names = ["bottom half", "50-75", "75-90", "90-95", "95-98", "top 2%"]
    ref["band"] = pd.cut(ref["pct"], bands, labels=names, right=False)
    C.log("2. THE ADOPTED LEADER'S MISS ACROSS THE LEVEL RANGE, by page percentile of")
    C.log("the trailing total. Rate miss among seasons played (per 82), and season WAR")
    C.log("miss over every forecast, at one, three and five seasons out.")
    C.log("")
    C.log(f"    {'band':<13}{'trailing':>9}" + "".join(f"{'rate h' + str(h):>10}" for h in (1, 3, 5))
          + f"{'WAR h5':>9}{'n h5':>7}")
    for b in names:
        g = ref[ref["band"] == b]
        line = f"    {b:<13}{g['trailing_war'].mean():>9.2f}"
        for h in (1, 3, 5):
            x = g[(g["h"] == h) & (g["played"] == 1)]["e_rate"].mean()
            line += f"{x:>+10.3f}"
        g5 = g[g["h"] == 5]
        C.log(line + f"{g5['e_war'].mean():>+9.3f}{len(g5):>7}")
    C.log("")

    # ---- 3. headline under every definition --------------------------------
    rj = ref.merge(mem[["career_key", "page"] + DEFS], on=["career_key", "page"], how="left")
    C.log("3. THE HEADLINE STAR FIGURES UNDER EVERY DEFINITION (adopted leader).")
    C.log("")
    C.log(f"    {'definition':<12}" + "".join(f"{'rate h' + str(h):>10}" for h in (1, 3, 5))
          + f"{'WAR h5':>9}{'n h5':>7}{'players':>9}")
    for k in DEFS:
        g = rj[rj[k]]
        line = f"    {k:<12}"
        for h in (1, 3, 5):
            line += f"{g[(g['h'] == h) & (g['played'] == 1)]['e_rate'].mean():>+10.3f}"
        g5 = g[g["h"] == 5]
        C.log(line + f"{g5['e_war'].mean():>+9.3f}{len(g5):>7}{g['career_key'].nunique():>9}")
    C.log("")

    # ---- 4. candidate verdicts under every definition ----------------------
    C.log("4. DOES ANY CANDIDATE'S VERDICT ON THE STAR GROUP CHANGE? Share of 2,000")
    C.log("career-resamples in which the candidate's squared season-WAR error on the")
    C.log("group is below the adopted leader's, same rows. Declared test: a change of")
    C.log("side of 50%, or into / out of >= 1950 or <= 50, against T3.0.")
    C.log("")
    C.log(f"    {'candidate':<28}" + "".join(f"{k:>10}" for k in DEFS) + "   changes")
    keys = ["career_key", "page", "h"]
    changes = []
    for f, (d, cands) in runs.items():
        a = d[d["variant"] == "adopted"].merge(mem[["career_key", "page"] + DEFS],
                                                on=["career_key", "page"], how="left")
        a = a.set_index(keys)
        for c in cands:
            v = d[d["variant"] == c].set_index(keys).reindex(a.index)
            line = f"    {LABELS[c]:<28}"
            shares = {}
            for k in DEFS:
                m = a[k].fillna(False).to_numpy(bool)
                boot = RSC.Boot(pd.Series(a.index.get_level_values("career_key")[m]))
                sh = boot.lower_share(a.loc[m, "e_war"].to_numpy() ** 2,
                                      v.loc[m, "e_war"].to_numpy() ** 2)
                shares[k] = sh
                line += f"{int(round(sh * RSC.N_BOOT)):>10}"
            base = shares["T3.0"]
            band = lambda x: "hi" if x >= 0.975 else ("lo" if x <= 0.025 else "mid")
            ch = [k for k in DEFS if k != "T3.0"
                  and ((shares[k] > 0.5) != (base > 0.5) or band(shares[k]) != band(base))]
            changes.append((c, ch))
            C.log(line + "   " + (", ".join(ch) if ch else "none"))
    C.log("")
    n_ch = sum(1 for _, ch in changes if ch)
    C.log(f"  candidates whose verdict changes under at least one definition: {n_ch} of {len(changes)}")
    C.log("")
    rj.to_csv(C.out_path("star_definition.csv"), index=False)
    C.write_log("star_definition_run_log.txt")


if __name__ == "__main__":
    main()
