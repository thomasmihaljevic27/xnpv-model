# Thomas's feedback on "Valuing Prospects", 2026-10-14 to 2026-10-16

A record of each change Thomas asked for and each comment he left on "Valuing Prospects", in five rounds, and the
themes that run through them. Read it before drafting or revising any document for him. Sources: his commented copies
in git (`a0115a0`, `9e401e9`, `a63f158`, `dac260f`), the session logs (2026-10-15, 2026-10-15b, 2026-10-15c,
2026-10-16, 2026-10-16b) and his messages in session 2026-10-16b. Rounds 3 to 5 quote his comments word for word;
rounds 1 and 2 were answered in chat and survive only as the session logs' summaries.

## The rounds

### Round 1 (2026-10-15): 14 notes and one general request (session log 2026-10-15; summaries)

| Note | What he asked | Done |
|---|---|---|
| General | "you only show what the actual formula may be once. you should definitely show the adopted formula each time you add a variable to the model" | The adopted formula shown at each step |
| 0, 1 | The regression, and "star value for his seasons since the draft", were unclear | Rewritten as what is compared with what, with a worked #10 pick |
| 2 | Name seasons from the draft (D+1, not "season 0") | D+1 to D+5 and later throughout |
| 3 | The two simpler fade rules explained | Rewritten from the table's ratios |
| 4 | Is draft-year production in the model? | It is; the text now says which seasons each measure reads |
| 5 | What Table 2's numbers are | Caption: each is a held-out error in $M |
| 6 | Star probability zero for undrafted players | Answered: changes none of the 53 values |
| 7 | The curve against the star probability | Explained |
| 8 | Why age is centred at 18.5 | Answered; any centre gives the same values |
| 9 | The age wording | Rewritten with a worked number |
| 10 | Redraw counts beside p-values | p-values only |
| 11 | The negative production coefficient | Where the curve turns, explained |
| 12 | "Per 10" scaling | Explained (later dropped) |
| 13 | "170 players" | "170 different players, as some were traded more than once" |

### Round 2 (2026-10-15b): 20 notes, answered in chat (session log 2026-10-15b; summary)

Mostly questions: what a "step" is (a sudden drop, not a standard deviation); why the p-value is one-sided; whether
p = 0.084 is significant; what dividing by 10 does; what d is; the ages on September 15; whether "older now" means
"drafted older"; undrafted players' selection. Decisions in the round: age fully adopted with no age-removed version
("Age is fully adopted and we don't need to report an age removed version as sensitivity"); centring age at 18 "seems
like the simpler solution"; drafted players who died before the NHL "should probably be noted or excluded";
"I think we need to test without 2007"; production squared alone: "I'd be interested in exploring this version. Give
me the full test results and I want to see statistical significance on this." A save-percentage test for goaltenders
was raised.

### Round 3 (2026-10-15c): 13 comments on the rebuilt document (copy `9e401e9`; the first six also in `a0115a0`)

| # | Comment | On | Done |
|---|---|---|---|
| 0 | "I do not believe this data. This implies that everyone eventually makes the NHL which is obviously not the case" | Figure 1 | Redrawn as shares of the whole group |
| 1 | "I would honestly rather use the version of a full set of interaction terms. I think it is more straightforward to explain and it is something that Karl and I agree on." | Section 1's method | Described that way (built only in round 4) |
| 2 | "I just think this figure is kinda ugly lol" | Figure 2 | Three panels |
| 3 | "Missing prospects seasons" | "Most of those prospect-seasons" | "Missing prospect-seasons" |
| 4 | "Just call it root mean squared error uniformly throughout the doc" | "root mean squared miss" | Done |
| 5 | "I think this should be uniformly referred to as NHLe after it has been initially introduced" | "NHL-equivalent" | Done |
| 6 | "'the curve' is not a meaningful word. The whole thing is a curve. You mean 'The production squared term'" | "the curve" | Versions named by their terms |
| 7 | "This sentence is a good illustration about why being specific and consistent is extremely important ... You need to scan the entire document for confusing wording like this. You need to be specific and consistent." | "the full curve" | Rewritten; his p-value direction corrected |
| 8 | "I don't know what this is saying. Why are we talking about age here at all? It's very confusing" | The age-centring argument in Section 2 | Cut |
| 9 | "personally I don't like 'slot' because it feels non-specific and also 'the slot' is a common hockey term that is completely unrelated to the draft. It should be 'Draft position' throughout" | "slot" | Done |
| 10 | "I still think the wording here is clunky. I would recommend giving me rewrite options in chat." | Section 3's opening | Three options offered; he chose age now |
| 11 | "What is important is that a player who is 20's equivalent production is worth less than an 18 year olds production." | The age-discount wording | Age reported as age now |
| 12 | "don't we care about the age that the production comes from? Not the age a player was drafted at" | The same | The same |

His own edits in this round: the deceased-draftee paragraph cut to three sentences; a "The measure." label dropped;
"sourced from Elite Prospects" added.

### Round 4 (2026-10-16): 10 comments (copy `a63f158`)

| # | Comment | On | Done |
|---|---|---|---|
| 0 | "Just say something like 'I regressed surplus value… on each season from D+1 through to D+5 and onwards…'" | Section 1's method | His phrasing |
| 1 | "I just feel like this could be shortened and simplified." | The same | Three sentences |
| 2 | "Superfluous detail. Just make the regression actually be the interaction terms. I feel like I've said this multiple times." | The equivalence sentence | Code changed to one stacked regression (`prospect_values.py` v1.8); sentence cut |
| 3 | "This sentence makes it sound like those rules are in the model rather than tested and rejected alternatives" | The fade rules | "tested and rejected" |
| 4 | "If there are ties on this chart you should bold each." | Table 4 | Ties bolded |
| 5 | "This wording is clunky" | The star probability sentence | Rewritten with the 74.8% / 7.4% example |
| 6 | "Be specific. You mean statistically significant." | "reliable" | Throughout |
| 7 | "Doesn't this say that nothing in the model is significant from D+5 onwards?" | Table 6, D+5 and later | Joint test added (later cut) |
| 8 | "Why doesn't this table compare the candidate age models with the adopted draft+production models?" | Table 8 | Its baseline was that model; renamed by its terms |
| 9 | "Again, it appears nothing is statistically significant after D+5" | Table 9, D+5 and later | As 7 |

His own edits in this round: the date line, the call-up sentence, the Table 1 pointer and the leave-one-draft-out
figures cut; the production introduction rewritten in his words; "Bacon," and an SHL example cut from the citation;
"which makes no logical sense" restored; the D+1 age range cut.

### Round 5 (2026-10-16b): 2 comments and requests in chat (copy `dac260f`, session 2026-10-16b)

| Item | His words | Done |
|---|---|---|
| Comment 0 | "Wouldn't it be easier to just say 'the coefficient for each season is that season's (D+n) star value: the surplus value if a player in D+n were certain to be a star' ... you give my suggestion in the next paragraph? Are these not the same thing?" | His definition; the repeat cut |
| Comment 1 | "The sentence is still weirdly worded. Why can't you just be specific? ... why doesn't the equation shown include that? ... I still really don't know what value we get from this to be honest" | Measured (the draft-year terms moved the star values by at most $0.10M); removed from both models |
| Request | "go with alternatives" (for "rule" in Figure 2 and Table 3) | Done |
| Request | D+5 and later: "let's go with the adopted model" | Kept |
| Request | 14 concision edits: 13 accepted; the D+5 paragraph "cut entirely, we don't need to talk about the 24 permutations" | Done |
| Request | "both the prospect and draft models just have one intercept", then, shown its cost, "no intercept and no draft dummies" | Built |
| Request | "highlight all changes made"; "Make a new doc so I can compare the two versions easily" | Tracked-changes copies on the Desktop |
| Own edits | "(a full set of interaction terms)," cut; an Oxford comma added | Carried into the builder |

## Themes

Counted over the 25 comments quoted word for word (rounds 3 to 5), each under its main theme; rounds 1 and 2 and his
own edits are cited where they show the same thing.

1. **One specific, consistent name for each thing (9 of 25).** Round 3: 3, 4, 5, 6, 7, 9; round 4: 3, 6, 8. RMSE and
   NHLe used uniformly; "draft position", never "slot"; no "the curve" or "the full curve"; "statistically
   significant", never "reliable"; "alternative", not "rule", for something rejected; a table's baseline named by its
   terms. His own words: "You need to be specific and consistent." Round 1's D+1 naming belongs here too.
2. **Say it plainly and directly (6 of 25).** Round 3: 10; round 4: 0, 1, 5; round 5: 0, 1. "Just say ...", "Why
   can't you just be specific?", "clunky" (twice), "weirdly worded", "shortened and simplified". He often supplies
   the sentence himself, and it is shorter than the draft's. Rounds 1 and 2 were mostly the same complaint as
   questions: the reader could not tell what a regression, a table or a coefficient meant.
3. **Everything must earn its place.** No comment's main theme, but it runs through four of them (round 4: 1, 2;
   round 5: 0, 1) and through nearly every edit of his own: 7 cuts in round 4, 2 in round 3, 1 in round 5, the 24-
   combination paragraph cut, 13 of 14 concision cuts accepted, redraw counts dropped beside p-values (round 1).
   "Superfluous detail"; "Are these not the same thing?"; "I still really don't know what value we get from this".
   When he questions a part's value, the answer has been to measure it, and it has gone if it adds little.
4. **The numbers must make hockey sense (3 of 25).** Round 3: 0, 11, 12. He reads each figure against what he knows
   of the game: not everyone reaches the NHL; a point scored at 20 is worth less than one at 18; the age that matters
   is the age at which a player scored. Round 2's deceased draftees and the 2007 draft come from the same instinct, as
   does restoring "which makes no logical sense" in round 4.
5. **Read the statistics for him, honestly (2 of 25).** Round 4: 7, 9: "nothing is statistically significant after
   D+5". He reads the significance in each table himself and expects the text to say what he would conclude. Round
   2's questions (one-sided p, p = 0.084) belong here too.
6. **Build the method asked for, and show it (2 of 25).** Round 3: 1; round 4: 2 ("I feel like I've said this
   multiple times"). The interaction terms took two rounds because the first answer described an equivalent instead
   of building it. Showing the method goes with it: the formula at each step (round 1), the equation with every term
   in it (round 5: 1).
7. **Tables and figures that read at a glance (2 of 25).** Round 3: 2 (the ugly figure); round 4: 4 (bold every tie).
   Round 3's comment 0 also came from a figure whose base was unclear.
8. **Order: nothing before the reader needs it (1 of 25).** Round 3: 8: "Why are we talking about age here at all?"
   Round 4's comment 3 is related: a rejected alternative written as if it were part of the model.

Three themes run beside the comments, in his decisions and in how he works:

- **Fewer moving parts in the model.** No age-removed version; age centred at 18 because it is "the simpler
  solution"; one regression with interaction terms; the adopted model kept from D+5 on rather than a better-scoring
  combination; draft-year dummies dropped, and an intercept declined once its cost was shown.
- **He edits in Word himself.** Each round carries edits of his own, which a rebuild from the builder would lose
  unless they are carried into it; and he asks for rewrite options in chat and for tracked comparisons of versions.
- **Repeats cost him.** Two items needed asking more than once (the interaction terms; specific wording), and he said
  so. A note that comes back is a sign the first answer was wrong in kind, not in degree.

## Checks for the next draft

1. Each concept has one name, used every time; search the draft for each synonym before handing it over.
2. Each sentence says what is compared with what, in hockey terms, with a number; no specification language.
3. Each paragraph, table and caption is needed; nothing says the same thing twice; definitions appear once.
4. Each figure and claim survives a hockey reading (who arrives, who scores, at what age).
5. Each significance statement is the one he would draw from the table, at the 5% level, with its p-value.
6. The method in the text is the method in the code, with its full equation.
7. Ties are bold; a cumulative share shows its whole base; table baselines are named by their terms.
8. Nothing is argued before the section that introduces it; rejected options are called rejected first.
