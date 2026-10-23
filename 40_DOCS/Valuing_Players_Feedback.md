# Thomas's notes on "Valuing Players, Draft Picks, and Prospects"

Round 1: 14 comments on v2 (2026-10-19 build), pages 1 to 4, written 2026-10-21. He stopped there: "I can tell there
are some changes it would be best to knock out first before I continue." His annotated copy is kept in the session's
scratchpad, not the repo; the comments are transcribed in full below, each with the text it was anchored on.

## Round 1, as written

| # | Anchored on | His note |
|---|---|---|
| 0 | "Player production throughout is Patrick Bacon's wins above replacement (WAR)." | You should be describing what WAR is and who Patrick Bacon is and why he is a credible source of this data |
| 1 | "Contracts and their terms come from PuckPedia, and CapWages ... The trades come from a ledger collected from CapFriendly" | Trades come from PuckPedia. As with the prior comment, defining who we are getting the sources from is useful for describing the credibility of the data |
| 2 | "In each of those seasons the asset delivers play" | Does a draft pick delivery play? No it doesn't. |
| 3 | "a cap hit, an entry-level salary, or a qualifying offer" | These are not mutually exclusive. |
| 4 | "for each season k the club controls, counted from the valuation season (k = 0), the season's value V less its cost C, in that season's dollars, discounted 3% a year" | Word soup |
| 5 | "play" | Important to use "performance" rather than "play". |
| 6 | "and C his cap hit" | That makes it sound like C is a verb. C IS his cap hit. I hate wording like this. |
| 7 | "the discount acts" | The Discount is not a noun and it cannot act. This is a MAJOR tell of AI writing. Do not personify things in the model. The passage should read like "A cap hit is in fixed dollars, so on the cost side discounting is present." |
| 8 | "A drafted player's career has already happened" | The structure of this document is kinda ass. If we're going to have a section like this at the beginning of the document, it should be speaking in general terms. It should be introducing the concept and explaining why it's important, and the general terms of how it works. This sentence is indecipherable unless you've already read the document. There is no context for why this is something we'd even consider bringing up until you get to the relevant section. The entire document needs to be cleared of writing continuity errors like this. |
| 9 | "Decision" (a heading) | I am not a fan of these "Decision:" headers |
| 10 | "play" | performance |
| 11 | "value = Σ (pk × Vk − Ck) / 1.03^k + value of the control seasons" | "Value of the control seasons" is called Terminal Value |
| 12 | "forecast play" | Forecasted performance |
| 13 | "forecast" | forecasted |

## Themes

1. **Write like a person: no personified model parts (7).** A discount, a forecast, a regression or a price line
   does not act, know, ask, see or read. Name what is done and to what: "on the cost side discounting is present".
2. **Opening sections speak in general terms; nothing before it is introduced (8, 4).** The opening explains the
   concept, why it matters and how it works in general. A detail that needs a later section goes in that section.
   This is the same as round 3's note on "Valuing Prospects" ("Why are we talking about age here at all?"), now
   applied to the whole document.
3. **The project's own names (5, 10, 11, 12, 13).** Performance, not play; forecasted performance; the value of the
   control seasons is the terminal value.
4. **Plain definitions (6, 4, 3).** "C is his cap hit", not "C his cap hit"; one claim per sentence; lists whose
   items do not overlap.
5. **Say who the sources are and why they are credible (0, 1).** WAR is defined and its maker introduced; each data
   provider is named for what it is.
6. **Precision about which asset does what (2).** A pick delivers nothing until its player reaches the NHL.
7. **No "Decision:" headings (9).** The reasoning stays; the heading names the topic.

## Checks for the next draft

1. Search for personification: a model part as the subject of a verb of thought or perception (knows, asks, sees,
   reads, learns, expects, treats, credits, lets, wants), or an abstract noun acting ("the discount acts").
2. Each section reads on its own at its place: no term, rule or number from a later section.
3. "Performance" for what a player delivers; "forecasted" for the adjective; "terminal value" for the control seasons'
   value.
4. Each symbol is defined with "is": "C is his cap hit".
5. No heading starts with "Decision:".
6. Each source is introduced once with what it is and why it is used.

---

# Round 2: 39 comments and 15 text edits on v3 (2026-10-21 build), the whole document, written 2026-10-21

His annotated copy is kept byte-equal in `90_ARCHIVE/2026-10-21/Valuing Players, Draft Picks, and Prospects (Thomas
notes, round 2).docx`. He also asked that "Valuing Prospects" be brought up to date, since he has not yet met Karl on it.

## His own text edits (carry each verbatim into `model_doc.js`; check each after the build)

Found by a paragraph-by-paragraph diff of his copy against the v3 he was sent (commit 12f6a2e).

1. Opening: "...how each of the three kinds of asset is valued and are put on a comparable scale." (his wording; "how
   the three values" removed)
2. WAR definition: "in the WAR metric used here".
3. Sources: the sentence "One provider is used for every player and every asset, so that each win is measured on one
   scale: ..." deleted; the paragraph now opens "Bacon also supplies the two inputs ...".
4. Section 1 title: "1. Surplus Value" (was "The Common Currency").
5. Section 1 rates: "and salary cap growth has to be projected at some rate"; "a discount rate above cap growth;" (", as
   a market interest rate would be" deleted).
6. Starting level: "an injury can influence it greatly" (was "move it a long way").
7. Pacioretty's starting level: "Therefore, his starting level is ...".
8. Comparable players: "so the five style shares together share a quarter of the weight and the remaining attributes
   share a quarter each" (was "count as one attribute").
9. Weight of ten: the last two sentences deleted (the 10-game league average version, and "The weight of ten was
   kept.").
10. Chance of playing: "A contract costs its cap hit" (was "pays").
11. Section 4: "A contract's value is the sum of it's remaining seasons and the terminal value" (his text, "it's" as
    written).
12. Control-season cost: "the price line's price of his arbitration years WAR".
13. Circularity: "with no input from Bacon's WAR model"; "adjusted for score-state (tied, leading, trailing)".
14. "Why Bacon's WAR is kept" (heading and paragraph) deleted.
15. Prospects: "by neither model at a given valuation date"; "A prospect is valued in the pick model's currency."
    deleted; "full seasons in two different leagues"; "since NHLe converts only skater scoring and says nothing of
    goaltender performance"; "In the adopted model draft position is kept from D+1 to D+3, and production alone is used
    from D+4." (", one parameter fewer ..." deleted); "The discount on linear production alone was kept."

## Comments, as written

| # | Anchored on | His note |
|---|---|---|
| 0 | "A club holds an asset for the seasons it controls it." | Circular. "A club holds an asset for the seasons a club holds an asset." Try "A club holds an asset only for a finite period of time, either determined by contract length or determined through the NHL's CBA." |
| 1 | "Against what an asset delivers stands what it costs the club" | What? That isn't a proper sentence. |
| 2 | "first times the second" (forecasted WAR if he plays) | Why not just use the actual variables? Remember what I said about CONSISTENCY |
| 3 | "Each part is estimated only from seasons completed before the valuation season, so it is refitted for each valuation season; where this document shows a fit, it is the one for 2025-26 ..." | Confusing wording |
| 4 | (the starting-level formula) | "their change to the evaluation season" should be replaced with "aging". You should also show the games played weighting in "own rate" |
| 5 | "last" | Most recent. This should be the term used to avoid confusion between last meaning previous and last meaning final. |
| 6 | "Each was chosen on the forecast's error" | Why not something like "Each decision was evaluated using the forecast's error." You should search the document for sentences like this. |
| 7 | "Setting" (Table 2's column) | Why not "Decisions"? |
| 8 | "A fixed rule with no fitted parameter; the best of the simple weightings" | Word soup |
| 9 | "Start 1.1506 against 1.1526; one to five seasons ahead 1.3598 against 1.3618 (p = 0.087 and 0.099)" (games weighting) | Meaingless numbers and also statistically insignificant? |
| 10 | "Best pull in the same test" | You cannot just say that. You should show why |
| 11 | "Start 1.1506 against 1.1611; one to five seasons ahead 1.3598 against 1.3689" | Again you need to say what this number is. I can just say random numbers too if I wanted to and act like they mean anything |
| 12 | "The threshold used throughout the model" (10 games) | Horribly circular reasoning. |
| 13 | Pacioretty's five closest comparables | A table would be good here |
| 14 | "The comparable players' level is therefore blended with the league average ..., which counts as ten more comparable players" | Why not just say "The league average for the player's position and age is included alongside the comparable players weight at a level of 10" |
| 15 | "consistently across redraws of careers" | Unfortunately you'll have to explain what this means very very briefly |
| 16 | "Leaving a player's own other seasons out of the yardstick's sample was also tested ..." | This makes it sound like Pacioretty, for example, could be Pacioretty's comparable player. He isn't so this needs to be reworded that it is only relevant for determining the yardstick itself |
| 17 | "The same comparable players, chosen once at his last counted age, supply each change." | Horrible wording. "At each age step the same pool of comparable players provide their change in performance from one age to the next" or something like that |
| 18 | "Their changes are used, not their levels: ... while his own level stays his own." | "The nominal change in performance is used, not the level itself" or something instead of "while his own levels stays his own" sucks and should say something like "and those average changes are applied to the players starting level" |
| 19 | "as the model's earlier projection did" (Adding the aging changes) | If you were someone reading this paper, would you give a shit what a model that doesn't exist did? No. It's so easy to just say something like "the changes are then added or subtracted from the.." earlier in this section. I'm only leaving this entire section here so that you can see this comment. |
| 20 | "the sweep found no best level within the range tested, so the level would have been set by the edge of the range." | Wtf does this even mean |
| 21 | "Age enters less 27, near the peak, which changes no forecast and makes the intercept a 27-year-old's." | Feels arbitrary |
| 22 | "0.05" (the games-share floor) | Why not 0? |
| 23 | "With trailing WAR in the regression, position is no longer statistically significant at the 5% level (p = 0.404)." | Well then why the hell is it there |
| 24 | Games share: trailing total against rate, and the term above one win, in prose with four errors and two p-values | Shit like this is where a table is helpful |
| 25 | Table 5, (Age − 27)² in the adopted column: "0.002 (0.001) [0.111]" | I'm getting tired of seeing things that aren't statistically significant in these results.. I don't know how you thought this kind of result is acceptable |
| 26 | "The model's earlier projection lowered each season by a chain of yearly exit risks ... That fails twice." | It is really really important to know when to talk about what prior versions of the model did, and this is not one of those cases. |
| 27 | "Dating the forecast at the signing" (the earlier price line on trailing WAR) | This is another instance where we are spending considerable time describing a model as it no longer exists. Yes, it is important to make clear that we are pricing the player based on what they are expected to produce the following season. If I'm signing a player to a 4 year contract on July 1st, I am going to use my expectation of what next year is going to look like to determine what to pay him. But the thing is that should be clear and logical through what has already been described in the document. Spending time talking about a prior model that was misspecified is not something valuable. What's important is defending the parameters used in the model as it exists and describing how and why they are used. This is simply a case of a prior model not being properly specified, which I do not think is a good use of time. Writing all this out honestly makes me rethink the pricing regression because in some sense wouldn't you also want to consider the performance you are expecting to buy? This model has no input for *future projected performance over the course of the contract*, we are only projecting one year forward instead of over the full term of the deal. It's worth considering. |
| 28 | "Term does not mean more wins ... How term enters a season's price also had to be decided ..." | Another instance where it's best to shortly and simply defend the choice made rather than spend too much time describing what a prior model did. |
| 29 | "is PuckPedia's" (each season's cap hit) | Is FROM PuckPedia |
| 30 | "Until October 13, 2026, a control season cost the qualifying offer." | Again! This model no longer exists! Nobody wants to hear this! |
| 31 | "a contract signed on the trade date is left out of a traded player's value" | I think it is fair to do it this way but you contradicted yourself from earlier |
| 32 | "Table 10. Max Pacioretty's contract, valued at the trade" | Kinda weird to not include Tatar here |
| 33 | "Goaltenders have a simpler model, because their WAR varies far more from season to season than a skater's" | You cannot simply state that, you need to show proof |
| 34 | "No aging curve was fitted for goaltenders: the signal was judged too weak, and the birthdates needed were then missing for a third of them." | You should show that. 2. the birthdates aren't missing anymore |
| 35 | The goaltender price line, chance of playing and control-season weight | It's probably worth revisiting the goalie model just to be sure these decisions are justified still after all the many changes made |
| 36 | "Table 12. Brayden Point (2014, #79), from his draft to the end of club control" | For consistency, since Montreal received the eventual 50th overall pick in 2019, maybe we replace this chart with a player who was selected 50th. Some examples are Milan Lucic, Colton Sissons, and Jordan Greenway |
| 37 | "The cost of keeping a drafted player" (the qualifying-offer chain as an option) | I don't mind discussing alternatives here, but I don't think the QO chain should be brought up since it is no longer present in any part of the model. |
| 38 | Table 22, production (b) in D+1: "-0.074 (0.047) [0.113]" | Pretty obvious that the production term needs to be removed. The model should be a c d and e |

## Themes

1. **Describe the model as it is; never what an earlier version did (19, 26, 27, 28, 30, 37; his deletion 14).** Defend
   each parameter of the model as it runs, shortly, by why it is right. An earlier version, a misspecified one above
   all, is not an alternative to discuss. Alternatives tested against the model as it is may stay, briefly. The
   qualifying-offer chain is in no part of the model, so it is not brought up, nor reported beside values.
2. **Every number says what it is (9, 11, 10).** An error figure carries its name and unit, and what a difference of
   that size means; "best in the same test" is shown, not asserted.
3. **No term in an adopted model that is not statistically significant without a stated reason he accepts (23, 25,
   38, 9).** "I'm getting tired of seeing things that aren't statistically significant in these results."
4. **No circular reasons (0, 12).** "A club holds an asset for the seasons it controls it"; "the threshold used
   throughout the model" as the reason for the threshold.
5. **Proof, not assertion (33, 34, 10).**
6. **Tables for comparisons (13, 24, 32).** Several tested numbers in prose go in a table; Tatar goes in Table 10 beside
   Pacioretty.
7. **Consistency (2, 31, 36).** Symbols, not "the first times the second"; one rule for a same-day contract across the
   document and the model; the pick example matches the trade (the 50th pick).
8. **Words (1, 3, 5, 6, 7, 14, 17, 18, 29).** "Most recent", not "last"; "each decision was evaluated using";
   "Decisions", not "Settings"; "from PuckPedia"; plain sentences in place of compressed ones.

## Work the notes ask for (model and tests, before the rebuild)

- **Prospect model: drop linear production (38).** Thomas: "The model should be a c d and e": star probability (a),
  production squared (c), no production record (d), production × (age − 18) (e). The record already holds this form's
  figures, as "production squared alone" in Table 21 (`model_doc_figures.py`: the adopted columns less `nhle82`):
  held-out error 2.1980 against 2.1962 (one-sided p = 0.331 that the current form is better), traded drafted skaters
  $80.50M against $68.90M. Then the trade chain, the back-test, and "Valuing Prospects".
- **A contract signed on the trade date (31).** In the code, not only the text: `traded_player_values.py` masks it from
  the contract chain, but `participation_model.under_contract_at` reads every deal signed on or before the trade date,
  so the chance of playing still counts it as signed. Make the two agree.
- **Games share (21, 22, 23).** The defenceman term (p = 0.404 beside trailing WAR); the floor at 0.05 (why not 0); age
  centred at 27.
- **Chance of playing (25).** (Age − 27)² at p = 0.111 in the valuation season.
- **Games weighting of the starting level (9).** Not statistically significant at the 5% level (p = 0.087 and 0.099).
- **Pricing on the forecast over the contract's term (27).** "This model has no input for future projected performance
  over the course of the contract ... It's worth considering."
- **The goaltender model (33, 34, 35).** Show that goaltender WAR varies more from season to season; birthdates are no
  longer missing, so an aging curve can be tested; the price line is fitted on unpulled WAR and applied to the pulled
  forecast; the chance of playing and the control-season weight. Revisit after the changes made to skaters.
- **The 50th pick for the drafted-player table (36).** Colton Sissons (2012) or Jordan Greenway (2015); Milan Lucic
  (2006) is outside the 2007-2017 drafts the pick model is fitted on.

## To include in the next draft (Thomas, 2026-10-21)

- **Pricing on the forecast over the contract's term (note 27) was tested and is stated as tested.** Thomas: "I want these
  results to be discussed in the overall doc when the time comes. If a reviewer thinks of this it's important that it be
  stated it was tested." `25_TESTS/term_average_price_line.py` v1.0 (sessions/2026-10-21.md): the first-season line
  fits and predicts better than the term average and the term average with the chance of playing (held out, beaten in
  none of 20 repeats); the term premium rises on the averages, so it is not paying for later performance. Section 3,
  as a tested alternative, without describing any earlier version of the price line.
