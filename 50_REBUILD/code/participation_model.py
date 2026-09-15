"""participation_model.py -- will he be playing at all?

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 2.

WHY THIS EXISTS
    Every forecast in this tree so far has assumed every player plays every
    season of the contract, forever. That placeholder is why the aging curve
    looked bad: walked forward five years, it said a 39-year-old would be half
    a win below replacement, and it was scored against an outcome that was a
    zero 98% of the time because he had retired. The model was answering the
    wrong question, confidently.

    The right answer is not "he will be terrible". It is "he will not be
    there".

WHAT IT PREDICTS
    For a player and a future season: the probability he plays a meaningful
    NHL season. "Meaningful" is the same ten-game bar the rate forecast is
    estimated on and the harness scores against, deliberately -- the rate is
    conditional on playing, so the probability multiplying it has to be the
    probability of the same event, or the product is of two different things.
    The plan's looser "one or more games" is a different quantity and would
    leave a gap between the two halves.

    Each future season gets its own probability rather than a survival chain
    that ends a career at the first absence. A player can be modelled as
    absent at +2 and back at +3, which is what actually happens: returns are
    common, and a hazard model that treats the first missed season as death
    cannot express one.

THE INTEGRATION RULE
    E[WAR] = p_play x rate_82 x gp_share, and that product is formed in
    exactly one place, in the harness. Participation multiplies the rate once.
    The production chain's separate exit-hazard haircut applied on top of an
    already-unconditional projection is the double count this removes.

CONTRACT STATE
    The new input. A player under contract for a season is far more likely to
    play it than one whose deal has expired, and that is knowable in advance.
    Only contracts SIGNED ON OR BEFORE the decision date count -- the
    generalised D28 rule -- so a valuation never benefits from knowing about
    an extension that had not been signed yet.

    Coverage is not uniform and is reported per page rather than assumed: the
    vendor's contract export thins out before about 2015, so early pages know
    less about contract state than late ones. Where a player has no contract
    record the model gets an explicit "unknown" rather than a false "not under
    contract", because those are different statements and only one of them is
    true.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
from player_season_table import norm_name

SCRIPT_VERSION = "1.0"

BASE_FEATURES = ["age", "age_sq", "level", "gp_share", "exp_seasons", "is_D"]
CONTRACT_FEATURES = ["under_contract", "contract_unknown"]
FEATURES = BASE_FEATURES + CONTRACT_FEATURES
MIN_FIT_ROWS = 400


# ---------------------------------------------------------------------------
# Contract state
# ---------------------------------------------------------------------------
def contract_spans(contracts: pd.DataFrame) -> pd.DataFrame:
    """One row per contract: who, which seasons it covers, when it was signed.

    The season span is END YEAR MINUS LENGTH PLUS ONE, not the export's own
    `season` field. That is the production engine's locked fix: the `season`
    field is unreliable for active multi-year deals, and taking it at face
    value would put some contracts in the wrong years entirely.
    """
    from contract_source import POSGRP
    c = contracts.copy()
    name = (c["first_name"].astype(str).str.strip() + " "
            + c["last_name"].astype(str).str.strip()).map(norm_name)
    c["pkey"] = name + "|" + c["position"].map(POSGRP).astype(str)
    c["end_yr"] = pd.to_numeric(
        c["contract_end"].astype(str).str.extract(r"^(\d{4})")[0], errors="coerce")
    c["start_yr"] = c["end_yr"] - c["length"] + 1
    c["signed"] = pd.to_datetime(c["signing_date"], errors="coerce")
    return c.dropna(subset=["pkey", "start_yr", "end_yr", "signed"])[
        ["pkey", "start_yr", "end_yr", "signed", "contract_level", "signing_status"]]


def under_contract_at(spans: pd.DataFrame, as_of: pd.Timestamp,
                      seasons) -> pd.DataFrame:
    """(pkey, season) -> was he under contract for that season, as known on
    `as_of`. Only deals signed on or before the decision date are visible."""
    known = spans[spans["signed"] <= as_of]
    rows = []
    for s in seasons:
        cov = known[(known["start_yr"] <= s) & (known["end_yr"] >= s)]
        if len(cov):
            rows.append(pd.DataFrame({"pkey": cov["pkey"].unique(), "season": s,
                                      "under_contract": 1.0}))
    if not rows:
        return pd.DataFrame(columns=["pkey", "season", "under_contract"])
    return pd.concat(rows, ignore_index=True).drop_duplicates(["pkey", "season"])


def players_with_any_contract(spans: pd.DataFrame, as_of: pd.Timestamp) -> set:
    """Who the contract export knows about at all, as of this date.

    Needed to tell "his deal has expired" from "the vendor has no record of
    him". Treating the second as the first would tell the model that every
    player the export misses is a free agent, which is false and is
    concentrated in the early pages where coverage is thin.
    """
    return set(spans.loc[spans["signed"] <= as_of, "pkey"].unique())


# ---------------------------------------------------------------------------
# The model
# ---------------------------------------------------------------------------
class ParticipationModel:
    """One logistic fit per horizon, rolling.

    Per horizon because the shape genuinely differs: whether a player suits up
    next season is mostly about his contract and his health, while whether he
    suits up in six years is mostly about his age. One fit with horizon as a
    regressor would force those two to share a slope on everything else.
    """

    def __init__(self, contracts: pd.DataFrame | None = None):
        self.spans = contract_spans(contracts) if contracts is not None else None
        # WITHOUT CONTRACT DATA THE TWO CONTRACT COLUMNS ARE CONSTANTS -- zero
        # and one for every row -- so `contract_unknown` is collinear with the
        # intercept and the logistic fit is singular. The first version passed
        # them anyway, every fit failed, and the model fell back to a single
        # base rate for everyone. That is not "participation without contract
        # data", it is no participation model at all, and it silently turned a
        # contract ABLATION into a participation ablation.
        self.features = list(BASE_FEATURES) + (
            list(CONTRACT_FEATURES) if self.spans is not None else [])
        self.coef_: dict = {}
        self.base_: dict = {}
        self.coverage_: dict = {}
        self.used_: dict = {}

    # -- features ----------------------------------------------------------
    def _rows(self, anchors: pd.DataFrame, h: int, as_of=None, table=None) -> pd.DataFrame:
        """One row per player for horizon h, with everything known at t0.

        CONTRACT STATE IS DATED PER ROW, not once for the whole frame. The
        first version of this took a single `as_of` for a training set drawn
        from a decade of valuation seasons, which handed a 2010 row the
        contract knowledge of 2015 -- a look-ahead leak of exactly the kind
        the rest of this tree is built to make impossible. Each row now uses
        1 July of its OWN valuation season, so a row can only ever see deals
        signed before the date it stands at.
        """
        d = pd.DataFrame({
            "career_key": anchors["career_key"].to_numpy(),
            "pkey": anchors["pkey"].to_numpy(),
            "season": anchors["t0"].to_numpy() + h,
            # age IN THE TARGET SEASON -- the question is whether a player of
            # that age plays, not whether a player of his current age does.
            "age": anchors["age"].to_numpy(float) + h,
            "level": anchors["tw_WAR"].to_numpy(float),
            "gp_share": anchors["tr_gp_share"].to_numpy(float),
            "exp_seasons": anchors["exp_seasons"].to_numpy(float),
            "is_D": anchors["is_D"].to_numpy(float),
        })
        d["age_sq"] = (d["age"] - 27.0) ** 2
        d["age"] = d["age"] - 27.0

        d["t0"] = anchors["t0"].to_numpy()
        d["under_contract"] = 0.0
        d["contract_unknown"] = 1.0
        if self.spans is not None:
            for t0, idx in d.groupby("t0").groups.items():
                ts = pd.Timestamp(year=int(t0), month=7, day=1)
                blk = d.loc[idx]
                uc = under_contract_at(self.spans, ts, sorted(blk["season"].unique()))
                known = players_with_any_contract(self.spans, ts)
                if len(uc):
                    key = set(map(tuple, uc[["pkey", "season"]].to_numpy()))
                    d.loc[idx, "under_contract"] = [
                        1.0 if (k, s) in key else 0.0
                        for k, s in zip(blk["pkey"], blk["season"])]
                # A player the export knows but who has no deal covering the
                # season is genuinely a free agent; only a player the export
                # has never heard of gets the unknown flag. Calling the second
                # "not under contract" would be a false statement, and it is
                # concentrated in the early pages where coverage is thin.
                d.loc[idx, "contract_unknown"] = (~blk["pkey"].isin(known)).astype(float).to_numpy()
            d.loc[d["contract_unknown"] > 0, "under_contract"] = 0.0
        return d.drop(columns=["t0"])

    # -- fit ---------------------------------------------------------------
    def fit(self, table: pd.DataFrame, before: int, anchors_fn, horizons=range(6)):
        """Fit on every (player, valuation season, horizon) whose OUTCOME
        season completed before `before`."""
        import statsmodels.api as sm

        played = table[table["GP"] >= C.MIN_GP]
        act = table.set_index(["career_key", "syr"])["GP"]
        all_anchors = anchors_fn(played)

        for h in horizons:
            a = all_anchors[all_anchors["t0"] + h < before]
            if not len(a):
                continue
            d = self._rows(a, h)
            ix = pd.MultiIndex.from_arrays([d["career_key"], d["season"]])
            gp = act.reindex(ix).fillna(0.0).to_numpy()
            d["y"] = (gp >= C.MIN_GP).astype(float)

            d = d.replace([np.inf, -np.inf], np.nan).dropna(subset=self.features + ["y"])
            self.base_[h] = float(d["y"].mean()) if len(d) else 0.5
            self.coverage_[h] = (float(1.0 - d["contract_unknown"].mean())
                                 if len(d) and "contract_unknown" in d else 0.0)
            if len(d) < MIN_FIT_ROWS:
                self.coef_[h] = None
                continue

            # DROP NEAR-CONSTANT COLUMNS AT THIS HORIZON. On the early pages
            # the contract export knows about 3% of the players five seasons
            # out, so the contract columns are all-but-constant there, the
            # design goes singular and the whole fit fails -- taking the age
            # and level terms down with it and falling back to one base rate
            # for everyone. The contract feature should be absent where it has
            # nothing to say, not fatal. Which columns were used is recorded
            # so a later run can see where the feature was live.
            use = [f for f in self.features if d[f].std() > 1e-8]
            self.used_[h] = list(use)
            X = sm.add_constant(d[use].to_numpy(float), has_constant="add")
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    # Lightly regularised: the contract flags are near-perfect
                    # predictors on some pages, and an unpenalised fit would
                    # chase separation to an infinite coefficient.
                    res = sm.Logit(d["y"].to_numpy(float), X).fit_regularized(
                        alpha=1e-4, disp=0, maxiter=200)
                self.coef_[h] = np.asarray(res.params, dtype=float)
            except Exception as e:              # noqa: BLE001 -- fall back, never guess
                # Loud, because a silent fallback to the base rate looks like a
                # working model that simply has no opinion, and that is how the
                # contract ablation went unnoticed.
                C.log(f"  [participation] horizon {h}: fit failed "
                      f"({e.__class__.__name__}), falling back to the base rate")
                self.coef_[h] = None
        return self

    # -- predict -----------------------------------------------------------
    def predict(self, anchors: pd.DataFrame, h: int, as_of=None) -> pd.Series:
        """P(plays a ten-game season), indexed by career_key. Contract state is
        dated from each row's own valuation season, as in the fit."""
        d = self._rows(anchors, h)
        base = self.base_.get(h, 0.6)
        coef = self.coef_.get(h)
        if coef is None:
            return pd.Series(base, index=d["career_key"])
        use = self.used_.get(h, self.features)
        X = np.column_stack([np.ones(len(d)), d[use].to_numpy(float)])
        ok = np.isfinite(X).all(axis=1)
        p = np.full(len(d), base)
        z = np.clip(X[ok] @ coef, -30, 30)
        p[ok] = 1.0 / (1.0 + np.exp(-z))
        # Never a hard 0 or 1: a certainty here would make the whole expected
        # value zero on one logistic coefficient, and nothing about a player's
        # future is that certain.
        return pd.Series(np.clip(p, 0.005, 0.995), index=d["career_key"])
