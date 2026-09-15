"""production_adapter.py -- the LIVE CHAIN's own forecast, on the harness.

EXPERIMENTAL (50_REBUILD). Nothing here changes a production file.

WHY THIS EXISTS
    The rebuild's benchmark, A0Production, carries the trailing anchor flat at
    every horizon with games share and participation both one. It is a fair
    starting point and its own comment says so, but it is NOT the live chain:
    production projects through the locked aging path in
    skater_forward_projection.py and carries exit-hazard survival weights in
    contract_npv.py. Every improvement figure the rebuild reports against
    "production" is therefore an improvement against a simpler rule, and the
    gap is widest exactly where aging and exits do the most work, which is old
    players and long contracts.

    This adapter closes that. It runs production's OWN code and expresses the
    result in the three quantities the harness scores.

IT IMPORTS PRODUCTION RATHER THAN REIMPLEMENTING IT
    A reimplementation would be a second copy of the aging path and the hazard
    convention, and the project has already been bitten twice by a second copy
    of a rule drifting from the first (review item 1.5, which lived in two
    files and was fixed in one). So the locked aging curve, the D3 decay path
    with its D21 age-1 basing, the hazard table and the survival convention
    all come from the production modules themselves. If production changes,
    this changes with it.

WHAT IT CANNOT IMPORT, AND WHY THAT IS FINE
    SkaterProjector.__init__ reads the contract season spine, which is built
    from scraped clause data. The spine is about CONTRACTS. The forecast this
    adapter needs is about PLAYERS, and ratio_path() touches none of it, so the
    projector is built through __new__ and given only the two attributes the
    projection path uses, constructed from production's own modules. The
    alternative was to run a scrape to satisfy an import that the code being
    imported never reads.

THE MAPPING, and it is where the honesty lives
    rate_82   the production projection for that season: the trailing anchor
              walked along the locked decay path.
    gp_share  1.0. Production has no separate availability forecast. This is
              not an oversight in the adapter, it IS production's conflation of
              level with availability, and flattening it to 1 is what makes the
              comparison fair rather than flattering.
    p_play    the exit-hazard survival factor for that season, accumulated on
              production's own convention: S starts at one and each later
              season multiplies by one minus the hazard read at the PREVIOUS
              season's age and quality (review item 1.2).

WHAT IT INHERITS
    Production's own documented limitations travel with it, and they are not
    repaired here because repairing them would stop this being production. The
    aging curve is fitted on the whole panel, so its parameters are partly
    estimated on seasons after some valuation dates. The comparison is with the
    live chain as it actually is.

REQUIRES 30_OUTPUT/WAR_with_age.csv, built by 20_CODE/age_join.py, and the
environment variables production reads. Without them the adapter refuses
rather than falling back to something that looks like production.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C                      # loads .env for the imports below
from ability_forecast import BaseModel

SCRIPT_VERSION = "1.0"

_PROD = C.REPO_ROOT / "20_CODE"


def _production():
    """Import the production modules, or say exactly what is missing."""
    if str(_PROD) not in sys.path:
        sys.path.insert(0, str(_PROD))
    try:
        import skater_forward_projection as SFP
        from exit_hazard import build_transitions, build_hazard_table, bucket, age_group
    except KeyError as e:                        # production reads os.environ directly
        raise RuntimeError(
            f"the production modules need the environment variable {e} set. "
            "Copy .env.example to .env and point SOURCE_DIR and OUTPUT_DIR at "
            "this checkout.") from e
    if not Path(SFP.F_WAR_AGE).exists():
        raise RuntimeError(
            f"{SFP.F_WAR_AGE} is missing. It is built by 20_CODE/age_join.py "
            "and the production aging curve is fitted on it. Run that first; "
            "this adapter will not substitute anything for it.")
    return SFP, build_transitions, build_hazard_table, bucket, age_group


class ProductionChain(BaseModel):
    """Production's forecast: the locked aging path, carried by survival."""

    name = "the live chain (aging path and survival)"

    # Nothing is fitted here. Production's parameters are locked and its curve
    # is built from its own panel, so no horizon is outside a fitted range and
    # the guard has nothing to refuse.
    FITTED_HORIZONS = None

    _cache: dict = {}

    def fit(self, table: pd.DataFrame, before: int) -> None:
        super().fit(table, before)
        self.before = before
        key = "singleton"
        if key not in self._cache:
            SFP, build_transitions, build_hazard_table, bucket, age_group = _production()

            proj = SFP.SkaterProjector.__new__(SFP.SkaterProjector)
            proj.curve = SFP.AgingModel(str(SFP.F_WAR_AGE))
            proj.last_ratio_floored = []

            # The anchor lookup, built exactly as production builds it: D20
            # proration first, merged names dropped, team-halves summed under
            # the same guard, qualifying seasons only.
            war = pd.read_csv(SFP.F_WAR_SKATERS)
            war["syr"] = war["Season"].str.split("-").str[0].astype(int) + 2000
            war["WAR"] = war["WAR"] * war["syr"].map(SFP.PRORATION_FALLBACK
                                                     if hasattr(SFP, "PRORATION_FALLBACK")
                                                     else {2019: 82 / 70, 2020: 82 / 56}
                                                     ).fillna(1.0)
            war["nk"] = war["Player"].map(SFP.norm_name) + "|" + war["Position"]
            war = war[~war["Player"].map(SFP.norm_name).isin(SFP.MERGED_WAR_NAMES)].copy()
            agg = war.groupby(["nk", "syr"], as_index=False).agg(
                GP=("GP", "sum"), WAR=("WAR", "sum"))
            q = agg[agg["GP"] >= SFP.MIN_GP]
            proj.war_lut = q.set_index(["nk", "syr"])["WAR"].sort_index()
            proj.raw_name = (war.drop_duplicates("nk").set_index("nk")["Player"]
                             .to_dict())

            haz = build_hazard_table(build_transitions(
                C.F_WAR_SKATERS, Path(SFP.F_WAR_AGE)))
            self._cache[key] = (proj, haz, bucket, age_group, q)
        self.proj_, self.haz_, self._bucket, self._age_group, self._q = self._cache[key]

    def _anchor(self, nk: str, t0: int) -> float | None:
        """The locked 60/40 blend on the two most recent qualifying seasons
        before t0. Renormalised when only one is available, as production does."""
        try:
            s = self.proj_.war_lut.loc[nk]
        except KeyError:
            return None
        s = s[s.index < t0]
        if s.empty:
            return None
        recent = s.sort_index().iloc[-2:]
        if len(recent) == 1:
            return float(recent.iloc[0])
        return float(0.4 * recent.iloc[0] + 0.6 * recent.iloc[1])

    def predict(self, iset, subs, horizons):
        self._guard_horizons(horizons)
        t0 = int(iset.t0)
        hs = sorted(int(h) for h in horizons)
        hmax = max(hs)

        rows = []
        for r in subs.itertuples():
            nk = f"{r.pkey}"
            anchor = self._anchor(nk, t0)
            age0 = float(r.age) if pd.notna(r.age) else None
            if anchor is None:
                # Production prices from its spine and simply has no answer for
                # a player it cannot anchor. The harness requires an answer from
                # every model on every row, so the trailing level the harness
                # itself classified him on is used and the season is carried
                # flat, which is what production's own no-curve path does.
                anchor, ratios, tag = float(r.trailing_war), [1.0] * (hmax + 1), "no_anchor"
            else:
                # INTEGER AGE. The curve indexes an age array, so a float
                # raises inside it, and ratio_path swallows that as "no
                # qualifying season" and returns a flat path. Passing 27.0
                # instead of 27 therefore silently turns the aging chain off,
                # which would have made this adapter look exactly like the flat
                # benchmark it exists to replace.
                ratios, tag = self.proj_.ratio_path(
                    nk, None if age0 is None else int(round(age0)), hmax)
            if len(ratios) < hmax + 1:
                ratios = list(ratios) + [ratios[-1]] * (hmax + 1 - len(ratios))

            # Survival on production's convention: S_0 = 1, and each later
            # season multiplies by one minus the hazard read at the PREVIOUS
            # season's projected quality and age (review item 1.2).
            surv, S, prev = {}, 1.0, None
            for k in range(hmax + 1):
                pw = anchor * ratios[k]
                if k > 0:
                    h_age = None if age0 is None else age0 + (k - 1)
                    b = self._bucket(prev)
                    g = self._age_group(h_age) if h_age is not None else "unknown"
                    S *= 1.0 - self.haz_.get((b, g), self.haz_.get((b, "ALL"), 0.0))
                surv[k] = S
                prev = pw

            for h in hs:
                rows.append({
                    "career_key": r.career_key, "h": h,
                    "rate_82": anchor * ratios[h],
                    "gp_share": 1.0,
                    "p_play": float(np.clip(surv[h], 0.0, 1.0)),
                    "path": tag,
                })
        return pd.DataFrame(rows)
