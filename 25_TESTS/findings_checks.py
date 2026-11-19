"""
findings_checks.py - two checks on the findings document's one regression, raised by an outside review (Thomas,
2026-11-19: "I guess run the tests"). Declared in 40_DOCS/Backtest_Protocol.md before it was built. Report only.

ROWS AND DESIGN: one_regression.frame() (v2.2): the 556 two-team trades of the declared window, both rules, each trade
once, the first club's value on the two clubs' differences, no constant, robust (HC1) standard errors, four outcomes.

1 THE CAP HIT HELD CONSTANT. The document's regression with one term added, the cap hit in $M:
    main player rule  the main player's cap hit (the highest cap hit received, who_overpaid's rule)
    any player rule   the total cap hit of the players received
    a club that received no player: 0 (as every player characteristic).
  The cap hit is player_facts' cap_hit (the ledger's, as clause_disguise.py reads it), so the guard can compare like with like.
  GUARD: the clause and age 28 to 31 coefficients equal clause_disguise.csv's "+ cap hit" fit, both rules, both outcomes.
  The finding rule is the document's: trade-day grade and realized WAR both p < 0.05, same sign; g and s mark the checks.

2 ADJUSTED P-VALUES. A term's p-value as a finding is the LARGER of its trade-day and realized-WAR p-values (both tests
  must pass), or 1 where the two signs differ. These are adjusted by Benjamini-Hochberg (statsmodels' fdr_bh), which holds
  the expected share of false findings among those declared at 5%. Two sets of terms, each rule separately:
    (a) the 12 player characteristics (one_regression.PC)
    (b) every term in the fit (23 in the document's fit; 24 with the cap hit, which is counted)
  Reported for the document's fit and the cap-hit fit.
  GUARD: the document's fit reproduces one_regression.csv's estimates and p-values on every term (so the adjusted figures
  are the ones disclosed in the protocol).

OUTPUTS: OUTPUT_DIR/findings_checks_log.txt, findings_checks.csv
"""
import importlib.util
import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from statsmodels.stats.multitest import multipletests

load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
SCRIPT_VERSION = "findings_checks.py v1.0 (2026-11-19)"
CONT = {"trailing_war", "rep_gap", "gp_share_last", "avg_war", "avg_gap", "avg_gs"}   # the continuous terms (as one_regression)
LOG, OUT = [], []


def log(s=""):
    print(s)
    LOG.append(s)


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def pair_p(fs, k):
    """The term's p-value as a finding: the larger of the trade-day and realized-WAR p-values; 1 if the signs differ."""
    a, b = fs["net_M"], fs["out_net_M"]
    if np.sign(a.params[k]) != np.sign(b.params[k]):
        return 1.0
    return max(a.pvalues[k], b.pvalues[k])


def main():
    log(SCRIPT_VERSION)
    OR = load("one_regression")
    OR.LOG = LOG
    log(f"  on {OR.SCRIPT_VERSION}")
    A, B, t, f, key, WO = OR.frame()

    # ---- the cap hit, each club (player_facts' cap_hit, $M; clause_disguise.py's construction) ----
    p = f[key + ["cap_hit"]].copy()
    p["cap_M"] = p["cap_hit"].fillna(0) / 1e6
    main_cap = p.sort_values("cap_hit", ascending=False, kind="stable").drop_duplicates(key).set_index(key)["cap_M"]
    tot_cap = p.groupby(key)["cap_M"].sum()
    for X in (A, B):
        X["m_cap"] = [main_cap.get((tid, c), np.nan) for tid, c in zip(X.index, X["club"])]
        X["a_cap"] = [tot_cap.get((tid, c), np.nan) for tid, c in zip(X.index, X["club"])]
        for c in ("m_cap", "a_cap"):
            X[c] = np.where(X["recv"] == 1, X[c], 0.0)
            assert X[c].notna().all(), c
    log(f"  cap hit: mean main player's ${pd.concat([A, B]).query('recv == 1')['m_cap'].mean():.2f}M on the clubs that "
        f"received a player")

    ref = pd.read_csv(OUTPUT_DIR / "one_regression.csv")
    cd = pd.read_csv(OUTPUT_DIR / "clause_disguise.csv")
    cd = cd[cd["part"] == "+ cap hit"]
    YN = {y: lab for lab, y in OR.YS}
    fits = {}
    for rule in OR.P5:
        cap = "m_cap" if rule.startswith("main") else "a_cap"
        base = [c for c in OR.P5[rule] if c not in OR.DUP[rule] and c != OR.BELOW[rule]] + OR.PC[rule] + ["recv"]
        fl = set(base) - CONT
        doc, keep0 = OR.joint(A, B, base, fl)
        withcap, keep1 = OR.joint(A, B, base + [cap], fl)
        # GUARD: the document's fit reproduces one_regression.csv, every term, every outcome
        r = ref[ref["rule"] == rule]
        for lab, y in OR.YS:
            rr = r[r["outcome"] == lab].set_index("col")
            assert list(rr.index) == keep0, (rule, "terms")
            assert np.allclose(doc[y].params[keep0].values, rr["estimate"].values, atol=1e-9), (rule, y)
            assert np.allclose(doc[y].pvalues[keep0].values, rr["p"].values, atol=1e-12), (rule, y)
        # GUARD: clause and age with the cap hit equal clause_disguise's "+ cap hit" fit
        for nm, c in (("clause", OR.PC[rule][3]), ("aged 28 to 31", OR.PC[rule][0])):
            for y in ("net_M", "out_net_M"):
                want = cd[(cd["rule"] == rule) & (cd["term"] == nm) & (cd["outcome"] == y)]["estimate"]
                assert len(want) == 1 and abs(withcap[y].params[c] - want.iloc[0]) < 1e-9, (rule, nm, y)
        fits[rule] = {"as in the document": (doc, keep0), "with the cap hit": (withcap, keep1)}
    log("  check: the document's fit reproduces one_regression.csv on every term, outcome, estimate and p-value, both rules "
        "(PASS)")
    log("  check: with the cap hit, the clause and age 28 to 31 equal clause_disguise.csv's '+ cap hit' fit, both rules (PASS)")

    # ---- 1 the cap hit held constant: every term ----
    log("\n1. THE CAP HIT HELD CONSTANT ($M a club, positive = the club gained; robust standard errors; 556 trades)")
    log("   F = a finding (trade-day grade and realized WAR both p < 0.05, same sign); g = Game Value agrees, s = seasons played")
    for rule in OR.P5:
        doc, keep0 = fits[rule]["as in the document"]
        wc, keep1 = fits[rule]["with the cap hit"]
        log(f"\n  {rule}")
        log(f"  {'term':<40}{'document: trade-day | realized':>36}   {'cap hit held: trade-day | realized':>40}"
            f"{'  Game Value':>22}{'  seasons played':>22}  finding (document -> cap held)")
        for k in keep1:
            def tag(fs):
                if k not in fs["net_M"].params.index:
                    return ""
                ps = [fs[y].pvalues[k] for _, y in OR.YS]
                bs = [fs[y].params[k] for _, y in OR.YS]
                same = lambda i: ps[i] < 0.05 and np.sign(bs[i]) == np.sign(bs[0])   # noqa: E731
                return ("F" + ("g" if same(2) else "") + ("s" if same(3) else "")) if (ps[0] < 0.05 and same(1)) else "-"
            d = (f"{doc['net_M'].params[k]:+.2f} p={doc['net_M'].pvalues[k]:.3f} | "
                 f"{doc['out_net_M'].params[k]:+.2f} p={doc['out_net_M'].pvalues[k]:.3f}") if k in keep0 else "(not in)"
            w = (f"{wc['net_M'].params[k]:+.2f} ({wc['net_M'].bse[k]:.2f}) p={wc['net_M'].pvalues[k]:.3f} | "
                 f"{wc['out_net_M'].params[k]:+.2f} ({wc['out_net_M'].bse[k]:.2f}) p={wc['out_net_M'].pvalues[k]:.3f}")
            g = f"{wc['gv_net_M'].params[k]:+.2f} p={wc['gv_net_M'].pvalues[k]:.3f}"
            s = f"{wc['real_net_M'].params[k]:+.2f} p={wc['real_net_M'].pvalues[k]:.3f}"
            name = OR.NAME.get(k, "cap hit, each $1M")
            log(f"  {name:<40}{d:>36}   {w:>40}{g:>22}{s:>22}  {tag(doc) if k in keep0 else ''} -> {tag(wc)}")
            for lab, y in OR.YS:
                OUT.append({"part": "cap hit held", "rule": rule, "term": name, "col": k, "outcome": lab,
                            "n_trades": int(wc[y].nobs) // 2, "estimate": wc[y].params[k], "se": wc[y].bse[k],
                            "p": wc[y].pvalues[k]})

    # ---- 2 adjusted p-values ----
    log("\n2. ADJUSTED P-VALUES (Benjamini-Hochberg on each term's p-value as a finding: the larger of trade-day and "
        "realized WAR, 1 if the signs differ)")
    log("   set (a): the 12 player characteristics; set (b): every term in the fit")
    for rule in OR.P5:
        for fit in ("as in the document", "with the cap hit"):
            fs, keep = fits[rule][fit]
            pc = [k for k in keep if k in OR.PC[rule]]
            pp = pd.Series({k: pair_p(fs, k) for k in keep})
            adj_a = pd.Series(multipletests(pp[pc].values, method="fdr_bh")[1], index=pc)
            adj_b = pd.Series(multipletests(pp.values, method="fdr_bh")[1], index=keep)
            log(f"\n  {rule}, {fit} ({len(pc)} player characteristics, {len(keep)} terms)")
            log(f"  {'term':<44}{'trade-day p':>12}{'realized p':>12}{'as a finding':>14}{'adjusted (a)':>14}{'adjusted (b)':>14}")
            for k in pp.sort_values(kind="stable").index[:8]:
                a_ = f"{adj_a[k]:.3f}" if k in adj_a.index else "-"
                log(f"  {OR.NAME.get(k, 'cap hit, each $1M'):<44}{fs['net_M'].pvalues[k]:>12.4f}"
                    f"{fs['out_net_M'].pvalues[k]:>12.4f}{pp[k]:>14.4f}{a_:>14}{adj_b[k]:>14.3f}")
            for k in keep:
                OUT.append({"part": f"adjusted, {fit}", "rule": rule, "term": OR.NAME.get(k, "cap hit, each $1M"), "col": k,
                            "outcome": "as a finding", "p": pp[k],
                            "p_adj_characteristics": adj_a.get(k, np.nan), "p_adj_all_terms": adj_b[k]})
    pd.DataFrame(OUT).to_csv(OUTPUT_DIR / "findings_checks.csv", index=False)
    (OUTPUT_DIR / "findings_checks_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
