"""Report only: every fit that goes through one_regression.joint() (two rows a trade, clustered by trade) refitted on one
row a trade with robust (HC1) standard errors; every term's p-value compared. Writes nothing to 30_OUTPUT (to_csv and
write_text are no-ops for the duration)."""
import sys, io, contextlib, importlib.util, inspect, pathlib
import numpy as np, pandas as pd, statsmodels.api as sm
T = r"C:\Users\thoma\Desktop\xNPV\25_TESTS"
sys.path.insert(0, T); sys.path.insert(0, r"C:\Users\thoma\Desktop\xNPV\20_CODE")
pd.DataFrame.to_csv = lambda *a, **k: None           # nothing written
pathlib.Path.write_text = lambda *a, **k: None

def mod(name):
    spec = importlib.util.spec_from_file_location(name, f"{T}\{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

OR = mod("one_regression")
orig = OR.joint
REC = []
CTX = {"script": "one_regression"}

def joint(A, B, cols, flags):
    out, keep = orig(A, B, cols, flags)
    fl = inspect.currentframe().f_back.f_locals
    if list(cols) in [list(v) for v in OR.P5.values()]:
        return out, keep                                   # frame()'s internal guard fit (part 5's terms), not a reported fit
    rule = "main" if "m_retained" in cols else "any"
    lab = (fl.get("lab", "?") if CTX["script"] == "clause_disguise" else
           ("after 2022" if len(A) != 556 else "2017-22") if CTX["script"] == "one_regression_replication" else
           ("with cap hit" if len(keep) > 23 else "as in the document") if CTX["script"] == "findings_checks" else "as in the document")
    X = pd.DataFrame({c: A[c].astype(float) - B[c].astype(float) for c in keep}, index=A.index)
    for ylab, y in OR.YS:
        one = sm.OLS(A[y].astype(float), X).fit(cov_type="HC1")
        assert np.allclose(one.params.values, out[y].params[keep].values, atol=1e-9)
        for k in keep:
            REC.append(dict(script=CTX["script"], fit=lab, rule=rule, trades=len(A), outcome=ylab, term=OR.NAME.get(k, k), col=k,
                            b=one.params[k], p_two=out[y].pvalues[k], p_one=one.pvalues[k],
                            se_two=out[y].bse[k], se_one=one.bse[k]))
    return out, keep

OR.joint = joint
with contextlib.redirect_stdout(io.StringIO()):
    OR.main()
for name in ("clause_disguise", "one_regression_replication", "findings_checks"):
    M = mod(name); CTX["script"] = name
    ol = M.load
    M.load = lambda n, ol=ol: OR if n == "one_regression" else ol(n)
    with contextlib.redirect_stdout(io.StringIO()):
        M.main()
R = pd.DataFrame(REC)
R = R.drop_duplicates(["script", "fit", "rule", "trades", "outcome", "col"])
print(R.groupby(["script","fit","rule"]).size().to_string())
R["cross"] = (R["p_one"] < 0.05) != (R["p_two"] < 0.05)
R["ratio"] = R["se_one"] / R["se_two"]
print("fits x terms x outcomes compared:", len(R))
print("SE ratio one-row / two-row: min %.4f max %.4f" % (R["ratio"].min(), R["ratio"].max()))
print("largest p change:", float((R["p_one"] - R["p_two"]).abs().max()))
print("\nCROSSES 0.05:")
print(R[R["cross"]][["script", "fit", "rule", "trades", "outcome", "term", "b", "p_two", "p_one"]].to_string() if R["cross"].any() else "  none")
print("\nclosest to 0.05 (either version between 0.03 and 0.07):")
near = R[((R["p_one"].between(0.03, 0.07)) | (R["p_two"].between(0.03, 0.07)))]
near = near.drop_duplicates(["fit","rule","trades","outcome","col"])
print(near[["script", "fit", "rule", "trades", "outcome", "term", "b", "p_two", "p_one"]].to_string())
# findings status, the main regression
for rule in ("main", "any"):
    d = R[(R["script"] == "one_regression") & (R["rule"] == rule) & (R["fit"] == "as in the document")]
    for which in ("p_two", "p_one"):
        fnd = []
        for k, g in d.groupby("col", sort=False):
            g = g.set_index("outcome")
            gt, rw = g.loc["trade-day grade"], g.loc["realized value, WAR"]
            if gt[which] < 0.05 and rw[which] < 0.05 and np.sign(gt["b"]) == np.sign(rw["b"]):
                fnd.append(gt["term"])
        print(rule, which, "findings:", fnd)
R.to_csv  # (no-op)
pd.DataFrame.to_csv = pd.core.generic.NDFrame.to_csv
R.to_csv(r"C:\Users\thoma\AppData\Local\Temp\claude\bd60dca1ecd460d1\fba58235-91de-43ca-a456-be284a29ba2c\scratchpad\one_row_pcheck.csv", index=False)
