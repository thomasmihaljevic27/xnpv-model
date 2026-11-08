"""
stata_expected.py -- the figures each Stata command in the walkthrough should print, computed as Stata computes them
(v1.0, 2026-11-08). A library: the three Stata exports (stata_export.py, stata_export_players.py,
stata_export_backtest.py) import it; stata_refresh.py writes its figures into the do-file.

WHY: Thomas runs the model's regressions in Stata in front of the supervisor (2026-10-23 meeting). Each command in
the do-file carries, as a comment, the figure it should give, so a mismatch shows on the spot. Those figures are
computed here from the CSVs exactly as written, with Stata's conventions, so they are what Stata will print:

  regress (ordinary least squares)
    robust errors        HC1, the sandwich times N/(N-K)                                   vce(robust)
    clustered errors     the sandwich summed by cluster, times G/(G-1) x (N-1)/(N-K)       vce(cluster id)
    coefficient p        Student's t on N-K degrees of freedom (robust or plain), on G-1 (clustered)
    test / testparm      F = Wald / q on (q, N-K), or on (q, G-1) when clustered
    testnl               the same F, with the restriction's gradient (the delta method)
    R-squared            uncentered when there is no constant (noconstant), centred otherwise
  logit and tobit (maximum likelihood)
    default errors       the inverse of the negative Hessian
    clustered errors     the sandwich summed by cluster, times G/(G-1) only
    coefficient p        the normal distribution
    test                 chi2(q)
    lrtest               chi2 = 2 x the log-likelihood gain, on the number of added terms

The model itself reports chi2 Wald tests with normal p-values in places (prospect_doc_figures.py, model_doc_figures.py);
Stata's F versions differ from those in the third or fourth decimal of a p-value. The walkthrough says so once.
"""

import json
from pathlib import Path

import numpy as np
import statsmodels.api as sm
from scipy import stats


# =============================== the registry ==========================================================================
class Expected:
    """Key -> the text a do-file comment shows. Keys are written {{KEY}} in the template; stata_refresh.py fills them."""

    def __init__(self):
        self.v = {}

    def add(self, key, value, fmt="{:.4f}"):
        assert key not in self.v, f"expected figure {key} set twice"
        self.v[key] = value if isinstance(value, str) else fmt.format(value)

    def p(self, key, p):
        """A p-value as Stata shows it to four decimals, 'p < 0.0001' below that."""
        self.add(key, "p < 0.0001" if p < 0.00005 else f"p = {p:.4f}")

    def write(self, path):
        Path(path).write_text(json.dumps(self.v, indent=1, sort_keys=True), encoding="utf-8")


# =============================== least squares (regress) ===============================================================
class OLS:
    """regress, as Stata computes it. X has no constant column unless const=True adds one (first)."""

    def __init__(self, y, X, names, cluster=None, robust=False, const=False):
        y = np.asarray(y, float)
        X = np.asarray(X, float)
        if X.ndim == 1:
            X = X[:, None]
        self.names = (["_cons"] if const else []) + list(names)
        if const:
            X = np.column_stack([np.ones(len(y)), X])
        if cluster is not None:
            g = np.unique(np.asarray(cluster), return_inverse=True)[1]
            m = sm.OLS(y, X).fit(cov_type="cluster", cov_kwds={"groups": g})   # G/(G-1) x (N-1)/(N-K), as Stata
            self.df = int(g.max()) + 1 - 1
        elif robust:
            m = sm.OLS(y, X).fit(cov_type="HC1")
            self.df = int(m.df_resid)
        else:
            m = sm.OLS(y, X).fit()
            self.df = int(m.df_resid)
        self.m, self.b, self.V = m, np.asarray(m.params, float), np.asarray(m.cov_params(), float)
        self.se = np.sqrt(np.diag(self.V))
        self.n, self.r2 = int(m.nobs), float(m.rsquared)       # statsmodels: uncentered without a constant, as Stata

    def i(self, name):
        return self.names.index(name)

    def coef(self, name):
        return float(self.b[self.i(name)])

    def sei(self, name):
        return float(self.se[self.i(name)])

    def pval(self, name):
        t = self.coef(name) / self.sei(name)
        return float(2 * stats.t.sf(abs(t), self.df))

    def test(self, R, r=None):
        """Stata's test / testparm: F = Wald / q on (q, df). R is a list of {name: weight} rows (each row = r)."""
        Rm = np.zeros((len(R), len(self.names)))
        for j, row in enumerate(R):
            for nm, w in row.items():
                Rm[j, self.i(nm)] = w
        rv = np.zeros(len(R)) if r is None else np.asarray(r, float)
        d = Rm @ self.b - rv
        W = float(d @ np.linalg.solve(Rm @ self.V @ Rm.T, d))
        q = len(R)
        return W / q, float(stats.f.sf(W / q, q, self.df))

    def zero(self, names):
        """testparm: every named coefficient zero."""
        return self.test([{n: 1.0} for n in names])

    def testnl(self, fns):
        """testnl: each fn(b_dict) = 0, its gradient by central differences (the delta method), F on (q, df)."""
        def val(b):
            bd = dict(zip(self.names, b))
            return np.array([f(bd) for f in fns])
        g0 = val(self.b)
        h = np.maximum(np.abs(self.b) * 1e-6, 1e-8)
        G = np.column_stack([(val(self.b + np.eye(len(self.b))[k] * h[k]) - val(self.b - np.eye(len(self.b))[k] * h[k]))
                             / (2 * h[k]) for k in range(len(self.b))])
        W = float(g0 @ np.linalg.solve(G @ self.V @ G.T, g0))
        q = len(fns)
        return W / q, float(stats.f.sf(W / q, q, self.df))


def interact(frame, cols_by_group, group_col="season_group"):
    """Stata's ibn.season_group#c.(cols): one column per (group, col), zero outside the group. Names 'g.col'."""
    blocks, names = [], []
    for g in sorted(cols_by_group):
        on = (frame[group_col] == g).to_numpy()
        for c in cols_by_group[g]:
            blocks.append(np.where(on, frame[c].to_numpy(float), 0.0))
            names.append(f"{g}.{c}")
    return np.column_stack(blocks), names


# =============================== logit ==================================================================================
class Logit:
    """logit, as Stata computes it (default or clustered errors; z p-values; chi2 tests)."""

    def __init__(self, y, X, names, cluster=None):
        y, X = np.asarray(y, float), np.asarray(X, float)
        Xc = np.column_stack([np.ones(len(y)), X])
        self.names = ["_cons"] + list(names)
        mod = sm.Logit(y, Xc)
        m = mod.fit(disp=0, maxiter=500, method="newton")
        b = np.asarray(m.params, float)
        Hinv = np.linalg.inv(-mod.hessian(b))
        if cluster is None:
            V = Hinv
        else:
            g = np.unique(np.asarray(cluster), return_inverse=True)[1]
            S = mod.score_obs(b)
            Sg = np.zeros((g.max() + 1, S.shape[1]))
            np.add.at(Sg, g, S)
            G = Sg.shape[0]
            V = Hinv @ (Sg.T @ Sg) @ Hinv * G / (G - 1)
        self.b, self.V, self.se = b, V, np.sqrt(np.diag(V))
        self.ll, self.n = float(m.llf), int(len(y))
        self.ll0 = float(mod.loglike(np.r_[np.log(y.mean() / (1 - y.mean())), np.zeros(X.shape[1])]))
        self.pr2 = 1 - self.ll / self.ll0                                # Stata's pseudo R-squared

    def coef(self, name):
        return float(self.b[self.names.index(name)])

    def pval(self, name):
        i = self.names.index(name)
        return float(2 * stats.norm.sf(abs(self.b[i] / self.se[i])))

    def zero(self, names):
        idx = [self.names.index(n) for n in names]
        d = self.b[idx]
        W = float(d @ np.linalg.solve(self.V[np.ix_(idx, idx)], d))
        return W, float(stats.chi2.sf(W, len(idx)))


# =============================== tobit, censored below =================================================================
class Tobit:
    """tobit y X, ll(lo): fitted by the price line's own fitter (xnpv1_price_line.fit_censored, in cap shares), reported
    in the units of y_scale x cap share (the do-file uses $M at the 2025-26 cap). Default errors are the inverse of the
    negative Hessian; clustered errors are the sandwich times G/(G-1), as Stata's tobit vce(cluster)."""

    def __init__(self, cap_share, X, names, floor_share, scale, cluster=None):
        import xnpv1_price_line as XPL
        X = np.asarray(X, float)
        if X.ndim == 1:
            X = X[:, None]
        f = XPL.fit_censored(np.asarray(cap_share, float), X, np.asarray(floor_share, float))
        assert f["converged"], "the censored fit did not converge"
        self.names = ["_cons"] + list(names)
        y = np.asarray(cap_share, float) * scale
        lo = np.asarray(floor_share, float) * scale
        Xc = np.column_stack([np.ones(len(y)), X])
        cens = y <= lo + 1e-12 * scale
        k = Xc.shape[1]

        def ll_vec(pv):
            beta, sig = pv[:k], np.exp(pv[k])
            mu = Xc @ beta
            out = np.empty_like(y)
            out[~cens] = -np.log(sig) + stats.norm.logpdf((y[~cens] - mu[~cens]) / sig)
            out[cens] = stats.norm.logcdf((lo[cens] - mu[cens]) / sig)
            return out

        pv = np.append(f["coef"] * scale, np.log(f["sigma"] * scale))
        K = len(pv)
        h = np.maximum(np.abs(pv) * 1e-4, 1e-6)
        E = np.eye(K)
        S = np.column_stack([(ll_vec(pv + E[j] * h[j]) - ll_vec(pv - E[j] * h[j])) / (2 * h[j]) for j in range(K)])
        H = np.empty((K, K))
        for j in range(K):
            up = np.column_stack([(ll_vec(pv + E[j] * h[j] + E[i] * h[i]) - ll_vec(pv + E[j] * h[j] - E[i] * h[i]))
                                  / (2 * h[i]) for i in range(K)]).sum(0)
            dn = np.column_stack([(ll_vec(pv - E[j] * h[j] + E[i] * h[i]) - ll_vec(pv - E[j] * h[j] - E[i] * h[i]))
                                  / (2 * h[i]) for i in range(K)]).sum(0)
            H[j] = (up - dn) / (2 * h[j])
        H = (H + H.T) / 2
        Hinv = np.linalg.inv(-H)
        if cluster is None:
            V = Hinv
        else:
            g = np.unique(np.asarray(cluster), return_inverse=True)[1]
            Sg = np.zeros((g.max() + 1, K))
            np.add.at(Sg, g, S)
            G = Sg.shape[0]
            V = Hinv @ (Sg.T @ Sg) @ Hinv * G / (G - 1)
        self.b = pv[:k]                                    # coefficients (the beta block is the same under any
        self.se = np.sqrt(np.diag(V))[:k]                  # parametrisation of sigma)
        self.sigma = float(np.exp(pv[k]))
        self.ll = float(ll_vec(pv).sum())
        self.n, self.n_cens, self.share_coef = int(len(y)), int(cens.sum()), f["coef"]

    def coef(self, name):
        return float(self.b[self.names.index(name)])

    def sei(self, name):
        return float(self.se[self.names.index(name)])

    def pval(self, name):
        i = self.names.index(name)
        return float(2 * stats.norm.sf(abs(self.b[i] / self.se[i])))


def lrtest(small, big, df):
    """lrtest: chi2 = 2 x (ll_big - ll_small) on df."""
    lr = 2.0 * (big.ll - small.ll)
    return lr, float(stats.chi2.sf(lr, df))
