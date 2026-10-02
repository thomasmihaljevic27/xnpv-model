# The curvature retest: the headline claim does not survive at the top

Run 2026-09-15 in `50_REBUILD/`. Experimental. This gates the thesis's central claim, so the
rule was fixed before looking: if a curved price line beats the straight one out of sample, the
currency adopts the curve and the surplus gradient is an artifact to that extent.

## Why it was rerun

Surplus under the fitted currency rises with forecast production, and the implied price per
forecast win falls fourfold across the range. Read one way that is "clubs underpay for elite
production" — the finding the project exists to establish. Read the other way it is "the price
function is concave and we fitted a straight line". **The arithmetic is identical. Only an
out-of-sample test separates them.**

The locked record rejected a curved line out of sample at Stage 3. That test used anchors dated
at the **contract start**, and the audit later found 30% of that sample was signed before its
trailing seasons had finished — 58% at 3+ wins. Curvature is a claim about the top of the
market, and the top is exactly where the start-dated anchors were most wrong.

## The test

Held out by season, error in cap share, identical rows, 2,309 contracts.

| specification | error | vs straight | seasons won |
|---|---:|---:|---:|
| straight line | 0.00821 | — | — |
| plus a square | 0.00821 | +0.09% | 4 of 8 |
| square root | 0.00823 | +0.25% | 4 of 8 |
| **log** | **0.00814** | **−0.81%** | **6 of 8** |
| hinge at 1 win | 0.00820 | −0.03% | 5 of 8 |

The log specification wins. The margin is small — 0.81% is about **$6,000 a contract** — but it
wins six seasons of eight, which is more consistent than the decision-B split that was called no
distinction at 4 of 8.

**The old answer was right for the wrong reason.** Curvature does show up once the anchors are
dated when the pen moved; it did not on start-dated anchors.

## What it does to the finding

Mean surplus over the deal, in millions, under each currency:

| forecast wins/season | n | straight line | log currency |
|---|---:|---:|---:|
| below 0 | 481 | −0.39 | −0.48 |
| 0 to 0.5 | 1,267 | +0.35 | +0.29 |
| 0.5 to 1 | 333 | +0.93 | +1.51 |
| 1 to 2 | 191 | +3.05 | +3.15 |
| **2+** | **37** | **+3.00** | **−0.78** |

**The gradient survives in the middle and reverses at the top.** From below-replacement through
two wins a season the two currencies agree, and the spread between the top and bottom of that
range only narrows from $2.90M to $2.43M. But the 2-plus tier goes from the second-best value in
the market to slightly overpaid.

## What can and cannot be claimed

**Can be claimed.** Clubs systematically get more surplus from good-but-not-elite players —
roughly half a win to two wins a season of forecast production. That holds under both
specifications, on 524 contracts, and it is the finding the rebuilt chain supports.

**Cannot be claimed.** That elite production is underpaid. That result rests on 37 contracts and
it changes sign under a specification the data marginally prefers. Stating it as a finding would
be presenting a modelling choice as a discovery, and it is precisely the claim a reader looking
for identification problems would attack first.

The 2-plus cell was always thin — six contracts above three wins a season. Nothing at the very
top of this market is estimated on enough data to carry a claim alone, and the curvature test
now shows the thinness is not the only problem with it.

## What changes

1. **The currency adopts the log specification as primary**, per the rule fixed before the test,
   with the straight line retained as a reported sensitivity.
2. **The headline claim narrows** from "clubs underpay for production" to "clubs underpay for
   good-but-not-elite production, and the elite end is not identified on this sample."
3. The back-test, when it runs, reports both currencies for any category whose result depends on
   which one is used.

## What this does not settle

- Whether elite players are underpaid. The sample cannot answer it. A longer panel, or pooling
  with the goalie and prospect pillars, might.
- The log form is one curve among several that were tried; it won a close race. It is not
  established as the shape of the market, only as the best of five on this sample.
