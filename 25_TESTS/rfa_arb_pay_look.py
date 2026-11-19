"""rfa_arb_pay_look.py -- how much less arbitration-eligible RFAs re-sign for than the locked price line pays the same
forecast (Thomas, 2026-11-19: arbitration cost from "RFA re-signing pay"). REPORT ONLY: nothing changes; measured before
the rule is built, so Thomas sees the size of the discount first.

ROWS: the locked term-in price line's own 2,296 skater contracts (xnpv1_price_line.run on stage3_sample; GUARD: the rows
fingerprint and n equal XNPV1_RATE's), each with its forecast dated at its signing.
ARBITRATION-ELIGIBLE RFA SIGNING: signing_status RFA, and the same player's previous contract (PuckPedia, same nhl_id)
ends the season before this one starts with expiry RFA and arbitration_eligible = 1 (the flag the model reads,
rfa_terminal_value.load_arbitration_flags).
MEASURES, each in $M a season at the 2025-26 cap:
  1. the locked specification plus ONE indicator for an arbitration-eligible RFA signing (the discount, holding the
     forecast, position and term), censored at the league minimum as the line is;
  2. the same with the indicator split by position (forward, defenceman);
  3. the mean of observed cap share less the locked line's expected cap share (E[max(y*, floor)]) for those signings.
OUTPUT: OUTPUT_DIR/rfa_arb_pay_look_log.txt
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from scipy import stats

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "20_CODE"))
sys.path.insert(0, str(ROOT / "25_TESTS"))
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
SCRIPT_VERSION = "rfa_arb_pay_look.py v1.0 (2026-11-19)"
LOG = []


def log(s=""):
    print(s)
    LOG.append(s)


def main():
    import xnpv1_price_line as XPL
    import skater_forward_projection as SFP
    import skater_value_engine as SVE
    import skater_forecast as SF
    import price_line_spec_tests as PST
    log(SCRIPT_VERSION)
    cap = SVE.CAP_CEILING[2025]
    PST.CAP = cap
    quiet, XPL.log = XPL.log, (lambda s="": None)
    try:
        d, fp, _free, _tin = XPL.run(XPL.stage3_sample(), SF.ContractForecaster(), cap)
    finally:
        XPL.log = quiet
    L = SFP.XNPV1_RATE
    assert fp == L["rows_fingerprint"] and len(d) == L["n"], "not the locked line's rows"
    log(f"  the locked line's rows: {len(d):,} (fingerprint {fp}, as locked)")

    pp = pd.read_excel(SFP.F_PP_CONTRACTS, usecols=["nhl_id", "contract_end", "expiry_status", "arbitration_eligible"])
    pp = pp.dropna(subset=["nhl_id", "contract_end"])
    pp["end"] = pp["contract_end"].astype(str).str[:4].astype(int)
    prev = pp[pp["expiry_status"].astype(str) == "RFA"].drop_duplicates(["nhl_id", "end"])
    flag = {(int(a), int(b)): int(c) for a, b, c in zip(prev["nhl_id"], prev["end"], prev["arbitration_eligible"])}
    rfa = d["signing_status"].astype(str) == "RFA"
    arb = np.array([bool(r) and flag.get((int(i), int(s) - 1)) == 1 if pd.notna(i) else False
                    for r, i, s in zip(rfa, d["nhl_id"], d["start_yr"])])
    found = np.array([bool(r) and (int(i), int(s) - 1) in flag if pd.notna(i) else False
                      for r, i, s in zip(rfa, d["nhl_id"], d["start_yr"])])
    log(f"  RFA signings {int(rfa.sum()):,}: previous RFA contract found {int(found.sum()):,}, of them arbitration-eligible "
        f"{int(arb.sum()):,}")
    isd = (d["posgrp"].astype(str) == "D").to_numpy(float) if "posgrp" in d.columns else None
    if isd is None:
        isd = XPL.design(d, "xwar_signed", True)[:, 1] != 0
        isd = isd.astype(float)

    def show(name, names, coef, se):
        for k, nm in enumerate(names[4:], start=4):
            z = coef[k] / se[k]
            log(f"    {nm:<38} {coef[k] * cap / 1e6:+.3f}M a season (s.e. {se[k] * cap / 1e6:.3f}M), p = "
                f"{2 * stats.norm.sf(abs(z)):.3f}")

    a = arb.astype(float)
    log("\n1. ONE DISCOUNT: the locked specification plus an arbitration-eligible RFA indicator")
    names, coef, sig, ll, se, conv = PST.fit(d, {"arbitration-eligible RFA": a})
    show("one", names, coef, se)
    log(f"    (converged {conv}; alpha {coef[0] * cap / 1e6:+.3f}M, beta {coef[1] * cap / 1e6:+.3f}M a win)")
    log("\n2. BY POSITION")
    names2, coef2, _s, _l, se2, conv2 = PST.fit(d, {"arbitration-eligible RFA, forward": a * (1 - isd),
                                                    "arbitration-eligible RFA, defenceman": a * isd})
    show("pos", names2, coef2, se2)
    log("\n3. MEAN RESIDUAL against the locked line's expected cap share")
    base = PST.fit(d, {})
    X = np.column_stack([np.ones(len(d)), XPL.design(d, "xwar_signed", True)])
    e = PST.expected_cap(base[1], base[2], X, d["floor_pct"].to_numpy(float))
    r = d["cap_pct"].to_numpy(float) - e
    for lab, m in (("arbitration-eligible RFA", arb), ("other RFA", rfa.to_numpy() & ~arb), ("UFA", ~rfa.to_numpy())):
        v = r[m] * cap / 1e6
        log(f"    {lab:<28} n {m.sum():>5,}  mean {v.mean():+.3f}M (s.e. {v.std(ddof=1) / np.sqrt(len(v)):.3f}M)")
    (OUTPUT_DIR / "rfa_arb_pay_look_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
