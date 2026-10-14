"""
price_line_crosswalk_check.py -- what the name crosswalk does to the locked price line (report only; locks nothing)

CONTEXT (2026-10-14): war_name_crosswalk.py joins 34 contracted players whose PuckPedia and WAR spellings differ
(Dadonov, Beniers, Peterka ...). xnpv1_price_line.py v2.1 then refuses to run: its Stage 3 sample is 2,378
contracts against the recorded 2,349 (its guard: "this is not the locked Stage 3 sample"). Re-locking is Thomas's
decision; this measures what each choice would mean.

WHAT IT DOES (xnpv1_price_line's own functions, its guard bypassed only here)
  A. the locked sample: the crosswalk switched off for the sample (contract_source.war_full_name returns the
     PuckPedia spelling), so the rows are the recorded 2,349 (asserted by fingerprint); forecast as now built.
  B. the corrected sample: the crosswalk on (2,378 contracts); forecast as now built.
  Each line (term-in and term-free) against the lock in skater_forward_projection: coefficients, n, fingerprint.

Run from the repo root:  python 25_TESTS/price_line_crosswalk_check.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
import contract_source as CS                       # noqa: E402
import xnpv1_price_line as PL                       # noqa: E402
import skater_forward_projection as SFP             # noqa: E402
import skater_forecast as SF                        # noqa: E402

print("price_line_crosswalk_check.py v1.0 (2026-10-14)")
real = CS.war_full_name
CS.war_full_name = lambda df, base, id_col="nhl_id": base          # A: crosswalk off for the sample only
skA = PL.stage3_sample()
CS.war_full_name = real
skB = PL.stage3_sample()
fpA, fpB = PL.fingerprint(skA), PL.fingerprint(skB)
print(f"A locked sample: {len(skA):,} contracts, fingerprint {fpA} (recorded {PL.SAMPLE_N:,}, {PL.SAMPLE_FINGERPRINT})")
assert len(skA) == PL.SAMPLE_N and fpA == PL.SAMPLE_FINGERPRINT, "the crosswalk-off sample is not the locked one"
added = set(map(tuple, skB[["nk", "start_yr"]].values)) - set(map(tuple, skA[["nk", "start_yr"]].values))
print(f"B corrected sample: {len(skB):,} contracts, fingerprint {fpB}; added by the crosswalk: {len(added)}: "
      + ", ".join(sorted({k.split('|')[0] for k, _ in added})))

fc = SF.ContractForecaster()
cap = PL.SVE.CAP_CEILING[2025]
lock, lock_free = SFP.XNPV1_RATE, SFP.XNPV1_RATE_TERM_FREE
for lab, sk in (("A locked sample", skA), ("B corrected sample", skB)):
    d, fp, free, tin = PL.run(sk, fc, cap)
    for nm, got, lk in (("term-in", tin, lock), ("term-free", free, lock_free)):
        gap = {k: got[k] - lk[k] for k in ("alpha", "beta", "beta_d_add", "gamma_term")}
        print(f"  {lab}, {nm}: n {len(d)} (locked {lk['n']}); fingerprint {fp} (locked {lk['rows_fingerprint']}); "
              + "; ".join(f"{k} {got[k]:.10f} ({gap[k]:+.2e})" for k in gap)
              + f"; at the 2025-26 cap: ${got['beta'] * cap / 1e6:.3f}M a win (locked ${lk['beta'] * cap / 1e6:.3f}M)")
