"""
goalie_hazard_overlap.py -- does the RFA qualify gate already absorb exit?

THE QUESTION IN PLAIN ENGLISH
-----------------------------
The model charges a player's future control years twice over, potentially.

  * The EXIT HAZARD asks: what is the chance this player is simply not in
    the league next season? Estimated from the WAR panel by talent and age.
  * The QUALIFY GATE (D14(c)) asks: what is the chance his team declines to
    tender him a qualifying offer at expiry? Estimated from real expiries.

If declining to qualify a player IS how he leaves the league, then these two
are the same event wearing different clothes, and applying both charges one
departure twice. The skater side already reasons this way -- the hazard is
switched off for control years. The open item is whether goalies should
follow, and the honest answer requires knowing whether the two really do
overlap, and whether they overlap the SAME AMOUNT for both positions.

THE TEST
--------
Take every observable qualify-or-walk decision, exactly the population
D14(c) calibrates on. Then ask a separate question of each one: did the
player actually appear in the league the following season?

That gives a two-by-two:

                        played next season   vanished
    qualified                  A                 B
    not qualified              C                 D

If C is large, then walking away from a player is NOT the same as him
leaving -- he signed somewhere else -- and the gate measures TEAM RETENTION
while the hazard measures LEAGUE EXIT. Two different things, so applying
both is legitimate.

If C is near zero, then not qualifying a player is effectively how he
disappears, the two gates fire on the same men, and applying both
double-charges.

The whole point is to run it separately for goalies and skaters, because
the model currently treats them differently and nobody has checked whether
the data supports that.

STALENESS
---------
Runs on the read-only project mirror, two sessions behind. Indicative only.
"""

import os
import numpy as np
import pandas as pd
import re
import warnings

from dotenv import load_dotenv

load_dotenv()

warnings.filterwarnings("ignore")

# Source (vendor) vs output (generated) split -- see .env.example.
# contract_season_spine.csv (join_clauses_to_spine.py) and WAR_with_age.csv
# (age_join.py) are generated; Goalies_WAR.csv is a vendor input.
SPINE = os.path.join(os.environ["OUTPUT_DIR"], "contract_season_spine.csv")
SKATER_WAR = os.path.join(os.environ["OUTPUT_DIR"], "WAR_with_age.csv")
GOALIE_WAR = os.path.join(os.environ["SOURCE_DIR"], "Goalies_WAR.csv")
MIN_GP = 20                      # same qualifying filter the hazard uses


def nk(s):
    """Normalised name key. Lowercase, strip accents-ish punctuation and
    spaces, so 'J.T. Miller' and 'JT Miller' land on the same key."""
    s = str(s).lower()
    s = re.sub(r"[^a-z]", "", s)
    return s


def season_start(label):
    """'18-19' -> 2018."""
    y = int(str(label)[:2])
    return 1900 + y if y > 50 else 2000 + y


def appearances():
    """Set of (name key, season_start) for every qualifying player-season,
    kept separately for skaters and goalies."""
    sk = pd.read_csv(SKATER_WAR)
    sk = sk[sk["GP"] >= MIN_GP]
    sk_set = {(nk(p), season_start(s)) for p, s in zip(sk["Player"], sk["Season"])}

    go = pd.read_csv(GOALIE_WAR)
    go = go[go["GP"] >= 10]      # goalies play fewer games; 10 is the usual bar
    go_set = {(nk(p), season_start(s)) for p, s in zip(go["Goalie"], go["Season"])}
    return sk_set, go_set


def decisions():
    """The D14(c) calibration population: last season of each contract,
    expiring 2018-2024, where the team either qualified (pp_expiry 'RFA')
    or walked ('UFA no QO')."""
    sp = pd.read_csv(SPINE)
    last = sp.sort_values("season_start").groupby("contract_id").tail(1)
    e = last[last["season_start"].between(2018, 2024)
             & last["pp_expiry"].isin(["RFA", "UFA no QO"])].copy()
    e["nk"] = (e["first_name"].astype(str) + e["last_name"].astype(str)).map(nk)
    e["qualified"] = (e["pp_expiry"] == "RFA").astype(int)
    e["is_goalie"] = e["position"].astype(str).str.upper().str.startswith("G")
    return e


def main():
    sk_set, go_set = appearances()
    e = decisions()
    print(f"qualify-or-walk decisions found: {len(e):,} "
          f"({e.is_goalie.sum()} goalie, {(~e.is_goalie).sum()} skater)\n")

    for label, mask, pool in (("GOALIES", e.is_goalie, go_set),
                              ("SKATERS", ~e.is_goalie, sk_set)):
        d = e[mask].copy()
        # CONDITIONING, and it is load-bearing. Restrict to players who were
        # actually NHL regulars in the DECISION season. Without this, roughly
        # half of every "vanished" count is an AHL player who was never in the
        # league to leave it, and the exit rates come out absurd (60% of
        # QUALIFIED goalies apparently disappearing). The exit hazard measures
        # transitions OUT OF the qualifying panel, so the comparison has to
        # start from inside that panel too.
        d["in_league_now"] = [
            (k, s) in pool for k, s in zip(d["nk"], d["season_start"])]
        d = d[d["in_league_now"]]

        # did he appear anywhere in the league the FOLLOWING season?
        d["played_next"] = [
            (k, s + 1) in pool for k, s in zip(d["nk"], d["season_start"])]
        ct = pd.crosstab(d["qualified"], d["played_next"])
        ct.index = ["not qualified", "qualified"]
        ct.columns = ["vanished", "played next season"][:ct.shape[1]]
        print("=" * 66)
        print(label)
        print("=" * 66)
        print(ct.to_string())
        nq = d[d["qualified"] == 0]
        q = d[d["qualified"] == 1]
        if len(nq):
            print(f"\n  of those NOT qualified, {100*nq.played_next.mean():.1f}% "
                  f"still played the next season (n={len(nq)})")
        if len(q):
            print(f"  of those qualified,     {100*q.played_next.mean():.1f}% "
                  f"played the next season (n={len(q)})")
        if len(nq) and len(q):
            print(f"\n  implied exit rate | walked   = {100*(1-nq.played_next.mean()):.1f}%")
            print(f"  implied exit rate | qualified = {100*(1-q.played_next.mean()):.1f}%")
        print()


if __name__ == "__main__":
    main()
