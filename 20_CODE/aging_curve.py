"""
aging_curve.py  (production, mean-reversion hybrid)
===================================================
The player-aging engine for the NHL trade-market NPV project. Given a player and
the age we are valuing him from, it projects his WAR-per-82 across the future
years of a contract. This SUPERSEDES the earlier global-by-position curve.

WHAT IT DOES, IN ONE BREATH
---------------------------
1. Anchor on a denoised estimate of the player's current level (since
   2026-10-04c a games-weighted 50/30/20 average over this age and the two
   before, LEVEL_WEIGHTS; until then a two-year trailing average).
2. Pull that anchor partway toward the "type-and-age norm" -- where comparable
   players his age typically sit -- because an unusually high or low season
   regresses toward true talent. The pull is LAMBDA (kept) vs 1-LAMBDA (norm).
3. Walk the anchor forward with an age-conditional, survivorship-safe aging
   curve built from within-player year-over-year changes.

WHY THIS SHAPE (and what we rejected to get here)
-------------------------------------------------
A 16-cell factorial tested four switches against held-out data. The winners:
  * smoothing the anchor (two-year average) -- the single biggest, safest gain
  * matching comps AT THE PLAYER'S AGE, not on a career-average profile
    (career/age-blind matching added essentially nothing; bootstrap-confirmed
     that age-conditional matching is a real improvement)
  * shrinking the anchor toward the comp-type-age norm = MEAN REVERSION, the
    largest single lever at long horizons
The losers, dropped: a durability trait (added nothing); a pure level/comp
predictor (lowest raw error but survivorship-EXPOSED and it threw away current
form, so wrong for valuation).

VALIDATION (held-out, player-split 5-fold; MAE in WAR-per-82)
-------------------------------------------------------------
        horizon:   1yr     6yr
  persistence       1.055   1.364
  old global curve  1.048   1.264
  THIS hybrid       0.898   1.034     (~15% / ~18% better than the old curve)

IDENTIFICATION NOTES (for the committee)
----------------------------------------
* Survivorship: the forward aging is delta-based (within-player changes only),
  and the mean-reversion prior uses a CURRENT-AGE cross-section, so no future
  survivor levels feed the projection.
* Look-ahead (REVISED 2026-09-28, D3 revision). The player's own inputs were
  always trailing. The comparables pool, the z-score means and SDs, the
  yardstick and the league-average curves were NOT: they were built once from
  every season in the file, including seasons other players played after the
  valuation date. `AgingModel(before=t0)` fits all of them on seasons that
  started before t0 only, and the pricing chain now builds one such curve per
  valuation page (skater_forward_projection.SkaterProjector.curve_for). Scored
  2026-09-28 (40_DOCS/model_evidence/Aging_Choices_Test.md): on the live age table the
  pre-valuation fit costs 1.73% season-WAR RMSE in the live chain; with the
  Elite Prospects ages restored, 0.84%. `before=None` keeps the whole-file fit
  for tests and experiments that were recorded on it.
* LAMBDA is 0.65 since 2026-10-04c (directive 3: one 65/35 blend in the model).
  The xNPV 1 forecast reads only this curve's changes, so LAMBDA moves no
  forecast. The record below is the 0.55 it replaced:
* LAMBDA = 0.55 was locked by cross-validation on TRAIN players and confirmed on
  held-out players (fold picks 0.55-0.60, sd 0.02), so it is not tuned to the
  evaluation set.

KEY ASSUMPTIONS (flagged): MIN_GP=20 per usable season; level = games-weighted
50/30/20 over ages a, a-1, a-2 (LEVEL_WEIGHTS, directive 2); two-season trailing
window for profiles; equal weight per attribute (5 style shares split one
attribute's worth; Pens share dropped to remove the compositional collinearity);
shrinkage K pulls thin comp estimates toward the global position curve; hard F/D
matching gate.

USAGE
-----
    python3 aging_curve.py                  # fit, self-validate, demo projection

 =============================================================================
 REVIEW ITEMS 1.6 AND 1.7 (2026-07-26)
 -----------------------------------------------------------------------------
 1.6  Careers are keyed on the CLEANED name. This file used to group on the
      raw name text while every other script in the chain cleaned names first,
      so a player the source spells two ways became two short careers. Nick
      Paul was the costly case: the projection looked up "Nicholas Paul", two
      seasons, instead of "Nick Paul", ten, and applied that fragment's shape
      to his seven-year contract. Five spellings now collapse into their real
      careers. CURVE_NAME_SPLITS keeps the two Elias Petterssons apart, since
      cleaning strips the "(D)" the source uses to distinguish them. Grouping
      on name plus position was the alternative and was rejected: it splits
      four players who changed position mid-career, Brent Burns most of all.
      A traded player's team-halves are now added together (as review item 1.5
      does elsewhere), with the same 82-game guard against gluing two people
      into one.

 1.7  A two-season window must be two CONSECUTIVE seasons. The smoothing took
      the previous ENTRY in a player's list of qualifying seasons, which after
      an injury year or a season under the games threshold is not last season.
      338 windows paired non-consecutive seasons, the worst treating ages 21
      and 30 as back-to-back. Three changes: the level falls back to the
      single season where the previous one is not one year earlier; those
      entries are dropped from the comparables pool rather than kept as a
      different kind of entry; and the trend feature divides by the real age
      gap instead of always by one.

 EFFECT ON THE CURVE
   careers            1,479 -> 1,478      comparables pool  7,869 -> 7,531
   bandwidth          2.555 -> 2.526      spellings merged  5

 EFFECT ON VALUATIONS (full chain, 2,909 contracts)
   1,011 contracts move, 573 up and 438 down, +$30.5M in total. The median
   move is $5k and 90% are under $167k; the largest single move is $1.33M
   (Couture 2019). Nine contracts switch projection track, eight of them off
   the flat fallback and onto the curve because their careers are now whole.

 LAMBDA WAS RE-TESTED, NOT ASSUMED
   Changing the curve's inputs could have changed the best value for LAMBDA.
   Re-running the selection test on the rebuilt curve (sampled careers, same
   sample at every setting) gives mean absolute error of 1.0226 at 0.35,
   1.0110 at 0.45, 1.0068 at 0.55, 1.0095 at 0.65, 1.0192 at 0.75. 0.55 still
   wins. The locked value stands, unchanged and now re-earned.
 =============================================================================
    from aging_curve import AgingModel
    m = AgingModel()                      # reads OUTPUT_DIR/WAR_with_age.csv
    m.project("Cale Makar", current_age=26, horizon=6)
"""
import os

import numpy as np
import pandas as pd

from dotenv import load_dotenv

load_dotenv()

# WAR_with_age.csv is generated by age_join.py -> it lives in OUTPUT_DIR.
# Callers in the chain pass an explicit path; this is the standalone default.
DEFAULT_WAR_AGE = os.path.join(os.environ["OUTPUT_DIR"], "WAR_with_age.csv")

# ---------------------------- config ----------------------------------------
MIN_GP = 20
WIN = 2                 # trailing window for the PROFILE (style, ice time, trend); not the level
SHRINK_K = 10.0         # pull thin comp estimates toward the global curve
# DIRECTIVE 3 (Thomas, 2026-10-04): one own-versus-comparables blend in the model,
# 65/35, replacing the 0.55 locked here earlier. The forecast reads only this
# curve's year-to-year changes, and the anchor this sets cancels out of them, so
# changing it moves no forecast (00_STATE/MODEL_DIRECTIVES.md, entry 3).
LAMBDA = 0.65           # mean-reversion: kept current form vs (1-LAMBDA) type-age norm

# DIRECTIVE 2 (Thomas, 2026-10-04; games weighting 2026-10-04c). A player's LEVEL
# at age a is the 50/30/20 average of his per-82 rates at ages a, a-1, a-2, each
# weight multiplied by that season's games, over the 20-game seasons he has at
# those ages (rescaled, so a missing season is not a zero). It replaced the equal
# average of the last two consecutive seasons. One measure, used everywhere the
# curve uses a level: the profile's "lvl", the year-to-year changes, and the
# comparables' level. Evidence: 25_TESTS/aging_level_weights_test.py and
# level_games_weighting_test.py (MODEL_DIRECTIVES.md, entries 1 and 2).
LEVEL_WEIGHTS = (0.5, 0.3, 0.2)   # this age, the age before, the one before that
LEVEL_BY_GAMES = True
# A departed player's missing season is entered at replacement (rate 0) with HIS
# OWN last season's games (investigation C6, Thomas 2026-10-05; until then a
# carried 82). See skater_forecast.imputed_aging_model.


def level_at(byage, a):
    """The directive-2 level at age a. `byage` maps age -> season dict with
    'w82' (rate per 82) and 'gp' (games); ages he has no 20-game season at are
    simply absent. Raises KeyError if he has no season at a itself."""
    if a not in byage:
        raise KeyError(a)
    num = den = 0.0
    for lag, wt in enumerate(LEVEL_WEIGHTS):
        s = byage.get(a - lag)
        if s is None:
            continue
        ww = wt * (s["gp"] if LEVEL_BY_GAMES else 1.0)
        num += ww * s["w82"]; den += ww
    return num / den
STYLE = ["EVO WAR", "EVD WAR", "PP WAR", "PK WAR", "Shoot WAR"]   # Pens dropped (collinearity)
SHARE = [f"sh_{c.split()[0]}" for c in STYLE]
FEATS = SHARE + ["toi_pg", "lvl", "slope"]

# ---- REVIEW ITEM 1.6: name cleaning, shared with the rest of the chain -----
# Imported rather than redefined so the curve and the value engine can never
# drift apart on what counts as the same player. The fallback keeps this file
# runnable on its own, which the existing PRORATION import already does
# elsewhere in the chain.
try:
    from skater_value_engine import norm_name, MERGED_WAR_NAMES
except ImportError:                                    # standalone fallback
    import re as _re
    import unicodedata as _ud

    def norm_name(s):
        s = _ud.normalize("NFKD", str(s))
        s = "".join(c for c in s if not _ud.combining(c))
        s = _re.sub(r"[^a-z ]", " ", s.lower())
        return _re.sub(r"\s+", " ", s).strip()
    MERGED_WAR_NAMES = {"ryan johnson", "nathan smith"}

# Known same-name pairs the source distinguishes with a marker that cleaning
# would strip. Only Pettersson needs it: the source already writes the others
# as "Sebastian Aho Swe" and "Erik Gustafsson 88", which survive cleaning as
# distinct keys on their own.
CURVE_NAME_SPLITS = {"Elias Pettersson(D)": "elias pettersson d"}


def career_key(player):
    """One key per real career. Cleans the name, then applies the manual
    splits for same-name players the cleaning would otherwise merge."""
    if player in CURVE_NAME_SPLITS:
        return CURVE_NAME_SPLITS[player]
    return norm_name(player)


def _attr_weights():
    # equal weight per conceptual attribute; the style shares split one attribute
    groups = {"style": SHARE, "usage": ["toi_pg"], "level": ["lvl"], "slope": ["slope"]}
    w = {f: 1.0 / len(fs) for fs in groups.values() for f in fs}
    return np.array([w[f] for f in FEATS])


def _profile(rows, level):
    """One feature vector from a window of a player's season-dicts."""
    gp = sum(r["gp"] for r in rows)
    comp = np.sum([r["comp"] for r in rows], axis=0)
    gross = np.sum(np.abs(comp)) or 1e-9
    f = {fn: v for fn, v in zip(SHARE, comp / gross)}
    f["toi_pg"] = sum(r["toi"] for r in rows) / gp
    f["lvl"] = level
    w = [r["w82"] for r in rows]
    # REVIEW ITEM 1.7. The trend divided the change by the NUMBER OF ROWS
    # minus one, which is always 1 for a two-season window, regardless of how
    # many years actually separated them. A nine-year change was recorded as a
    # one-year trend, and that inflated figure is one of the inputs used to
    # pick a player's comparables. Dividing by the real age gap fixes it. With
    # the pool now holding only consecutive seasons the gap is always 1, so
    # this is a guard rather than a live correction -- but it means the
    # feature stays correct if WIN or the pool rule ever changes.
    gap = (rows[-1]["age"] - rows[0]["age"]) if len(rows) > 1 else 0
    f["slope"] = (w[-1] - w[0]) / gap if gap > 0 else 0.0
    return np.array([f[k] for k in FEATS])


class AgingModel:
    def __init__(self, war_age_path=None, before=None):
        df = pd.read_csv(war_age_path or DEFAULT_WAR_AGE)
        # D3 REVISION (2026-09-28): fit on seasons that STARTED before `before`
        # (a season-start year, the valuation page t0). Every season kept has
        # finished by July 1 of t0, the page date. None: the whole file, the
        # pre-revision fit, kept for recorded tests and experiments only.
        self.before = before
        if before is not None:
            syr = df["Season"].str.split("-").str[0].astype(int) + 2000
            df = df[syr < int(before)].copy()

        # ---- REVIEW ITEM 1.6: careers are keyed on the CLEANED name --------
        # Every other script in the chain cleans names before matching; this
        # one grouped on the raw text, so a player the source spells two ways
        # became two short careers. Nick Paul was the costly one: the
        # projection looked up "Nicholas Paul", holding two seasons, instead
        # of "Nick Paul", holding ten, and applied that two-season shape to
        # his seven-year contract.
        #
        # Cleaning alone would have created a worse error. There are two
        # different Elias Petterssons, a forward and a defenceman, kept apart
        # in the source by writing one as "Elias Pettersson(D)" -- and
        # cleaning strips that marker. CURVE_NAME_SPLITS handles it by hand,
        # the same way the project already handles Sebastian Aho. Grouping on
        # name plus position was the alternative and was rejected: it would
        # have split four real players who changed position mid-career, Brent
        # Burns most of all.
        df["career"] = df["Player"].map(career_key)
        # bookkeeping: how many raw spellings collapsed into one career
        self.n_spellings_merged = df["Player"].nunique() - df["career"].nunique()
        df = df[~df["career"].isin(MERGED_WAR_NAMES)].copy()

        # A traded player has one row per team. Those rows are halves of one
        # season and must be added together, exactly as the value engine and
        # the projection now do (review item 1.5). Summing happens BEFORE the
        # games filter so a small half is not silently lost.
        dup = df.duplicated(["career", "Season"], keep=False)
        if dup.any():
            # GUARD. If cleaning ever glues two different players together,
            # they will show up here as one season with an impossible number
            # of games. No real season exceeds 82.
            tot = df[dup].groupby(["career", "Season"])["GP"].sum()
            assert (tot <= 82).all(), (
                "combined games above a full season for "
                f"{list(tot[tot > 82].index)} -- cleaning has merged two "
                "different players. Add them to CURVE_NAME_SPLITS.")
        sums = {c: "sum" for c in ["GP", "TOI", "WAR"] + STYLE}
        df = (df.groupby(["career", "Season"], as_index=False)
                .agg(**{c: (c, f) for c, f in sums.items()},
                     age=("age", "first"), Position=("Position", "last")))

        df = df[df["age"].notna() & (df["GP"] >= MIN_GP)].copy()
        df["age"] = df["age"].astype(int)
        df["w82"] = df["WAR"] / df["GP"] * 82.0
        self.players = {}
        self.n_nonadjacent = 0          # item 1.7 bookkeeping
        for name, g in df.groupby("career"):
            g = g.sort_values("age"); comps = g[STYLE].to_numpy()
            seasons = [{"age": int(r.age), "w82": r.w82, "gp": r.GP, "toi": r.TOI, "comp": comps[i]}
                       for i, r in enumerate(g.itertuples())]
            raw = {s["age"]: s["w82"] for s in seasons}

            # ---- REVIEW ITEM 1.7: "last season" must actually be last -----
            # The two-season average took the PREVIOUS ENTRY in the player's
            # list of qualifying seasons. If he missed a year, or had a season
            # under the games threshold that was filtered out, the previous
            # entry is not last season. 339 of 7,869 windows paired
            # non-consecutive seasons; the worst treated ages 21 and 30 as
            # back-to-back. (Until 2026-10-04c, where the previous season was not
            # exactly one year earlier the level was the single season alone.)
            # DIRECTIVE 2 (2026-10-04c): the level is level_at() -- games-weighted
            # 50/30/20 over the 20-game seasons at this age and the two before,
            # read BY AGE, so a missing age simply drops out and never pairs
            # across a gap. `adjacent` still governs the PROFILE window and the
            # comparables pool (_build_bank), not the level.
            sm, adjacent = {}, {}
            byage = {s["age"]: s for s in seasons}
            for i, s in enumerate(seasons):
                is_adj = i > 0 and (s["age"] - seasons[i - 1]["age"] == 1)
                adjacent[s["age"]] = is_adj
                sm[s["age"]] = float(level_at(byage, s["age"]))
                if i > 0 and not is_adj:
                    self.n_nonadjacent += 1
            self.players[name] = {"pos": g["Position"].iloc[-1], "seasons": seasons,
                                  "raw": raw, "sm": sm, "adjacent": adjacent}
        ages = [s["age"] for p in self.players.values() for s in p["seasons"]]
        self.AMIN, self.nages = min(ages), max(ages) - min(ages) + 1
        self._build_bank()
        self._build_globals()

    # ---- comp bank: one age-conditional (smoothed) profile per qualifying season
    def _build_bank(self):
        rows = []
        self.n_bank_skipped = 0          # item 1.7 bookkeeping
        for name, p in self.players.items():
            ss = p["seasons"]
            for i in range(WIN - 1, len(ss)):
                # REVIEW ITEM 1.7. An entry in the comparables pool is meant
                # to be a two-CONSECUTIVE-season window. Where the previous
                # qualifying season is not one year earlier, this is not that,
                # so the entry is skipped -- the same treatment a player's
                # first season already gets, and for the same reason. The
                # alternative, keeping it as a single-season entry, was
                # rejected: single-season entries always have a trend of zero,
                # which would distort the scale everything is compared on.
                if not p["adjacent"].get(ss[i]["age"], False):
                    self.n_bank_skipped += 1
                    continue
                lvl = p["sm"][ss[i]["age"]]
                rows.append((name, p["pos"], ss[i]["age"], _profile(ss[i - (WIN - 1): i + 1], lvl)))
        self.names = np.array([r[0] for r in rows])
        self.pos = np.array([r[1] for r in rows])
        self.agek = np.array([r[2] for r in rows])
        X = np.array([r[3] for r in rows], dtype=float)
        # standardise within position
        self.stats = {}; Z = np.empty_like(X)
        for pp in np.unique(self.pos):
            m = self.pos == pp; mu = X[m].mean(0); sd = X[m].std(0); sd[sd == 0] = 1e-9
            Z[m] = (X[m] - mu) / sd; self.stats[pp] = (mu, sd)
        self.fw = _attr_weights(); self.Zw = Z * np.sqrt(self.fw)
        # smoothed level / delta lookups per row's player, indexed by age column
        def series(p):
            L = np.full(self.nages, np.nan); D = np.full(self.nages, np.nan)
            for a, v in p["sm"].items():
                L[a - self.AMIN] = v
                if (a + 1) in p["sm"]:
                    D[a - self.AMIN] = p["sm"][a + 1] - v
            return L, D
        pser = {n: series(p) for n, p in self.players.items()}
        self.Lser = np.array([pser[n][0] for n in self.names])
        self.Dser = np.array([pser[n][1] for n in self.names])
        self.by_age = {}
        for r in range(len(self.names)):
            self.by_age.setdefault(int(self.agek[r]), []).append(r)
        self.by_age = {k: np.array(v) for k, v in self.by_age.items()}
        # bandwidth (the "yardstick") = median within-position pairwise distance
        # (sampled). INVESTIGATION A1 (Thomas, 2026-10-05): one yardstick PER
        # POSITION, each the median of its own position's sampled distances, as
        # agreed in the 2026-10-02 aging review; it replaced the pooled median,
        # which is kept in self.h for reporting only. Self-pairs stay in (A2 was
        # dropped). Evidence: 25_TESTS/aging_investigations_abc.py and
        # aging_abc_followup.py (00_STATE/MODEL_DIRECTIVES.md, investigation A).
        rng = np.random.default_rng(0); ds = []; self.h_by_pos = {}
        for pp in np.unique(self.pos):
            Xi = self.Zw[self.pos == pp]
            if len(Xi) < 3:
                continue
            idx = rng.choice(len(Xi), size=min(1200, len(Xi)), replace=False); Xi = Xi[idx]
            sq = (Xi ** 2).sum(1); d2 = np.clip(sq[:, None] + sq[None, :] - 2 * Xi @ Xi.T, 0, None)
            ds.append(np.sqrt(d2[np.triu_indices(len(Xi), 1)]))
            self.h_by_pos[pp] = float(np.median(ds[-1]))
        self.h = float(np.median(np.concatenate(ds)))

    def _build_globals(self):
        dn, dc, ln, lc = {}, {}, {}, {}
        for p in self.players.values():
            pos = p["pos"]; ss = p["seasons"]; ser = p["sm"]
            for i in range(len(ss)):
                a = ss[i]["age"]; ln[(pos, a)] = ln.get((pos, a), 0) + ser[a]; lc[(pos, a)] = lc.get((pos, a), 0) + 1
                if i + 1 < len(ss) and ss[i + 1]["age"] - a == 1:
                    d = ser[ss[i + 1]["age"]] - ser[a]; dn[(pos, a)] = dn.get((pos, a), 0) + d; dc[(pos, a)] = dc.get((pos, a), 0) + 1
            self.gdelta = {k: dn[k] / dc[k] for k in dn}; self.glevel = {k: ln[k] / lc[k] for k in ln}

    # ---- weights from a target profile to the comps at a given age ----------
    def _weights(self, target_z, pos, age, exclude=None):
        cand = self.by_age.get(age, np.array([], int))
        cand = cand[self.pos[cand] == pos] if len(cand) else cand
        if len(cand) == 0:
            return cand, None
        h = self.h_by_pos[pos]                       # A1: the target's own position's yardstick
        w = np.exp(-((self.Zw[cand] - target_z) ** 2).sum(1) / (2 * h ** 2))
        if exclude is not None:
            w[self.names[cand] == exclude] = 0.0
        return cand, w

    def _shrunk(self, vals_col, cand, w, glob_target):
        m = ~np.isnan(vals_col); ww = w * m
        return (np.nansum(ww * np.where(m, vals_col, 0.0)) + SHRINK_K * glob_target) / (ww.sum() + SHRINK_K)

    # ---- the projection -----------------------------------------------------
    def project(self, player, current_age=None, horizon=7, _exclude_self=True):
        # Careers are keyed on the cleaned name (item 1.6). Accept a raw name
        # too, so existing callers and demos keep working.
        if player not in self.players:
            player = career_key(player)
        p = self.players[player]; ss = p["seasons"]; pos = p["pos"]
        if current_age is None:
            current_age = ss[-1]["age"]
        idx = next((i for i, s in enumerate(ss) if s["age"] == current_age), None)
        if idx is None:
            raise ValueError("player has no qualifying season at age %s" % current_age)
        sm_level = p["sm"][current_age]
        # build target profile (falls back to single season if no trailing year)
        # REVIEW ITEM 1.7: also falls back when the previous qualifying season
        # is not one year earlier, so the profile never straddles a gap.
        lo = idx if not p["adjacent"].get(current_age, False) else max(0, idx - (WIN - 1))
        tv_raw = _profile(ss[lo: idx + 1], sm_level)
        mu, sd = self.stats[pos]; tv = ((tv_raw - mu) / sd) * np.sqrt(self.fw)
        cand, w = self._weights(tv, pos, current_age, exclude=player if _exclude_self else None)
        # mean-reversion anchor
        if cand is not None and len(cand):
            compnorm = self._shrunk(self.Lser[cand, current_age - self.AMIN], cand, w,
                                    self.glevel.get((pos, current_age), sm_level))
        else:
            compnorm = sm_level
        anchor = LAMBDA * sm_level + (1 - LAMBDA) * compnorm
        # walk forward on the age-conditional delta curve
        traj = [{"age": current_age, "projected_war_per_82": anchor, "note": "anchor"}]
        level = anchor
        for k in range(1, horizon + 1):
            a = current_age + k - 1
            if (pos, a) not in self.gdelta and (cand is None or not len(cand)):
                break
            if cand is not None and len(cand):
                step = self._shrunk(self.Dser[cand, a - self.AMIN], cand, w, self.gdelta.get((pos, a), 0.0))
            else:
                step = self.gdelta.get((pos, a), 0.0)
            level += step
            traj.append({"age": a + 1, "projected_war_per_82": level, "note": ""})
        return pd.DataFrame(traj)

    # ---- self-validation: hybrid vs persistence vs old global curve ---------
    def validate(self):
        gdr = {}; cnt = {}
        for p in self.players.values():
            pos = p["pos"]; ss = p["seasons"]
            for i in range(len(ss)):
                a = ss[i]["age"]
                if i + 1 < len(ss) and ss[i + 1]["age"] - a == 1:
                    d = ss[i + 1]["w82"] - ss[i]["w82"]; gdr[(pos, a)] = gdr.get((pos, a), 0) + d; cnt[(pos, a)] = cnt.get((pos, a), 0) + 1
        gdr = {k: gdr[k] / cnt[k] for k in gdr}
        err = {}
        def add(tag, h, pred, act): e = err.setdefault((tag, h), [0.0, 0]); e[0] += abs(pred - act); e[1] += 1
        for name, p in self.players.items():
            ss = p["seasons"]; pos = p["pos"]
            for i in range(WIN - 1, len(ss)):
                a = ss[i]["age"]
                fut = [(ss[j]["age"] - a, ss[j]["age"]) for j in range(i + 1, len(ss)) if ss[j]["age"] - a in range(1, 7)]
                if not fut:
                    continue
                tr = self.project(name, a, horizon=max(k for k, _ in fut))
                proj = {int(r.age): r.projected_war_per_82 for r in tr.itertuples()}
                L0 = p["raw"][a]
                for k, fa in fut:
                    act = p["raw"][fa]
                    add("persist", k, L0, act)
                    add("global", k, L0 + sum(gdr.get((pos, a + j), 0.0) for j in range(k)), act)
                    if (a + k) in proj:
                        add("hybrid", k, proj[a + k], act)
        print(" h |  n   | persist | global | hybrid")
        for h in [1, 2, 3, 4, 5, 6]:
            e = err.get(("hybrid", h))
            if not e:
                continue
            def m(t): x = err.get((t, h)); return x[0] / x[1] if x else float("nan")
            print(" %d |%5d | %.3f   | %.3f  | %.3f" % (h, e[1], m("persist"), m("global"), m("hybrid")))


if __name__ == "__main__":
    m = AgingModel()
    print("fit: %d players, %d comp profiles, bandwidth %.3f, lambda %.2f\n" % (
        len(m.players), len(m.names), m.h, LAMBDA))
    m.validate()
    print("\ndemo projections:")
    for name, age in [("Cale Makar", 26), ("Nathan MacKinnon", 29)]:
        if name in m.players:
            tr = m.project(name, age, horizon=6)
            s = ", ".join("%d:%.2f" % (r.age, r.projected_war_per_82) for r in tr.itertuples())
            print("  %s (from %d): %s" % (name, age, s))
