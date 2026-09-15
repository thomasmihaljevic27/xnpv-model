# Thirty-one players, both models

Run 2026-09-15 in `50_REBUILD/`. A demonstration, not a test: no model is selected or tuned
here. All valuation dates are 1 July, 2015–2021; the confirmatory seasons are untouched, which
is why Eichel-to-Vegas and the recent extensions are absent.

Production value over the contract term, in dollars. **Today's chain**: trailing two seasons
blended 60/40, carried flat, everyone plays every season, priced on the locked linear rate.
**The rebuilt chain**: three-season window, additive aging with the survivorship correction,
participation, priced on the currency. Value side only — no cost, retention or trade accounting.

## A specification error this demonstration caught

The first run of it put each contract's actual term into the price line and called the result a
production value. That priced Brent Seabrook's 0.20 forecast wins at **$47.2M**, because an
eight-year deal carries eight years of term premium whether or not the player produces anything.

Term-in does not mean a premium added per season. It means the replacement counterfactual is a
player signed for the remaining term rather than re-signed each year — which belongs in the
replacement baseline and in the contract-price model, not in the production value. Today's chain
has no term term at all, so a like-for-like comparison holds term neutral on both sides. The
premium is now reported in its own column, where it can be seen.

## What the two models say

| player | yr | yrs | anchor | new wins | today $M | new $M | diff | term premium |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **contracts the market regretted** | | | | | | | | |
| Milan Lucic | 2016 | 7 | 0.79 | 3.82 | 16.6 | 12.2 | −4.5 | 30.3 |
| Loui Eriksson | 2016 | 6 | 4.29 | 10.46 | 49.2 | 22.9 | −26.3 | 21.4 |
| Andrew Ladd | 2016 | 7 | 1.34 | 3.92 | 23.1 | 12.2 | −10.8 | 30.3 |
| Brent Seabrook | 2016 | 8 | −0.06 | 0.20 | 7.5 | 6.5 | −1.0 | 40.9 |
| Jeff Skinner | 2019 | 8 | 3.47 | 14.48 | 60.0 | 33.7 | −26.3 | 44.2 |
| Oliver Ekman-Larsson | 2019 | 8 | 0.80 | 2.03 | 22.5 | 12.6 | −9.9 | 44.2 |
| **bargains** | | | | | | | | |
| Nathan MacKinnon | 2016 | 7 | 1.35 | 9.82 | 23.2 | 23.8 | +0.6 | 30.3 |
| Nikita Kucherov | 2019 | 8 | 4.19 | 18.60 | 70.4 | 39.3 | −31.1 | 44.2 |
| Brad Marchand | 2017 | 8 | 4.36 | 13.50 | 69.1 | 30.5 | −38.6 | 41.8 |
| Mark Stone | 2019 | 8 | 4.85 | 16.97 | 80.2 | 37.0 | −43.2 | 44.2 |
| **the top of the market** | | | | | | | | |
| Connor McDavid | 2018 | 8 | 6.08 | 27.91 | 95.9 | 48.5 | −47.5 | 43.2 |
| Auston Matthews | 2019 | 5 | 3.81 | 14.84 | 38.6 | 27.5 | −11.1 | 14.8 |
| Mitch Marner | 2019 | 6 | 2.64 | 12.38 | 34.5 | 27.3 | −7.2 | 22.6 |
| Artemi Panarin | 2019 | 7 | 3.81 | 13.13 | 56.0 | 30.1 | −25.9 | 32.5 |
| Drew Doughty | 2019 | 8 | 0.33 | 0.85 | 14.7 | 9.1 | −5.6 | 44.2 |
| Erik Karlsson | 2019 | 8 | 0.83 | 2.50 | 22.9 | 14.0 | −9.0 | 44.2 |
| **memorable trades** | | | | | | | | |
| P.K. Subban | 2016 | 6 | 2.20 | 7.30 | 31.2 | 21.2 | −10.0 | 21.4 |
| Shea Weber | 2016 | 8 | 3.60 | 11.52 | 63.8 | 30.7 | −33.1 | 52.8 |
| Taylor Hall | 2016 | 4 | 1.17 | 4.36 | 11.8 | 11.3 | −0.5 | 8.2 |
| Ryan O'Reilly | 2018 | 5 | 3.28 | 10.08 | 33.7 | 22.0 | −11.7 | 14.6 |
| Jack Eichel | 2018 | 8 | 1.77 | 9.67 | 34.2 | 25.9 | −8.3 | 43.2 |

**The rebuilt chain values production lower across the board, and most on long deals for good
players.** That is the star over-projection fix arriving in dollars: today's chain carries a
4.85-win Mark Stone flat, in perfect health, for eight seasons. The rebuilt chain ages him,
prices the chance he misses time, and arrives at 16.97 wins over the term instead of 38.8.

Two individual results are worth reading. Today's chain says **Loui Eriksson's** six years at
$6M were worth $49.2M of production — one of the most criticised contracts of the decade,
valued as a bargain, because he was carried forward at the 4.29 wins he had just posted. The
rebuilt chain says $22.9M. And **Brent Seabrook**, correctly, is near the floor in both.

## The result that matters, and it is a problem

Against the actual cap cost, on the deals where the cap hit is public:

| player | cost $M | surplus today | surplus, rebuilt |
|---|---:|---:|---:|
| Connor McDavid | 100 | −4.1 | **−51.5** |
| Nikita Kucherov | 76 | −5.6 | −36.7 |
| Mark Stone | 76 | +4.2 | −39.0 |
| Brad Marchand | 49 | +20.1 | −18.5 |
| Nathan MacKinnon | 44 | −20.9 | −20.3 |
| Loui Eriksson | 36 | +13.2 | **−13.1** |

The rebuilt chain gets Eriksson right and today's chain gets him spectacularly wrong. But the
rebuilt chain also says **McDavid at $12.5M was overpaid by $51M, and Kucherov, Marchand and
MacKinnon were all bad contracts.** No one who follows this sport would accept that, and they
would be right not to.

**This is the elite-tier problem from the curvature test, with names on it.** The log currency
prices production concavely, so the better a player is, the less each win is worth, and every
high-production contract comes out negative. The tier table said the 2-plus group flipped from
+$3.00M to −$0.78M on 37 contracts; this says the same thing in a form that cannot be waved
through.

## What I am changing, and why it is uncomfortable

Two rounds ago the log currency was adopted because it beat the straight line out of sample by
0.81%, about $6,000 a contract, and the rule had been fixed in advance. **That adoption should
be reversed for valuation**, and the reason has to be stated honestly: it is a face-validity
failure, not a new statistical result. A currency that concludes Connor McDavid was the worst
contract in this sample is wrong about something the data cannot see, and a $6,000-a-contract
edge in predicting prices does not buy the right to that conclusion.

The uncomfortable part: rejecting a specification because it disagrees with what I already
believed about McDavid is exactly the reasoning the confirmatory seal exists to prevent. So it
is recorded as what it is — domain evidence overriding a marginal statistical preference — and
the position is:

- **The straight line is primary for valuation.** It puts McDavid at roughly break-even, which
  is defensible where −$51M is not.
- **The log line is retained for price prediction**, where it genuinely won, and is reported as
  the sensitivity.
- **Neither is validated at the elite end.** Thirty-seven contracts above two wins a season, six
  above three. The honest statement remains that the top of this market is not identified on this
  sample, and no currency choice fixes that.

The middle of the distribution — half a win to two wins a season, 524 contracts — is where both
currencies agree and where the surplus finding stands.
