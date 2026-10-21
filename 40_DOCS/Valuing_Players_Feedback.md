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
