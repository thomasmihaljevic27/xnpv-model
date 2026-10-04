---
name: writing-style
description: "Thomas's writing style for any formal text he will put his name to: thesis and paper sections, supervisor documents, methodology write-ups, status reports, model explainers, course papers. Use when drafting, rewriting, editing or reviewing such text, including a single paragraph. Three jobs in one pass. Structure: tell the reader a story in which each step says why it exists, what it does, what else was tried and what to take away, not an info dump. Clarity: short, active, unambiguous sentences with one term per concept. Voice: Thomas's verified editing habits, with the tells of AI-written prose removed. Triggers: write up, rewrite this, draft a section, edit this paragraph, make this read better, info dump, humanize, sounds like AI, methods section, status report. Not for casual chat replies, session logs or commit messages."
---

# Writing style

This skill merges two earlier skills: `thomas-voice-humanizer` (voice and AI tells) and
`model-writeup` (structure and clarity, built from the supervisor's feedback in the 2026-09 aging
review). It does three jobs:

1. **Structure.** Tell the reader a story, so each paragraph has a reason to exist (Part 1).
2. **Voice.** Write the way Thomas edits (Part 2), with the AI tells removed (Part 4).
3. **Clarity.** Make each sentence impossible to misread (Part 3).

Do the jobs in that order of importance, but write the first draft with all of them in mind.
Bolted-on voice reads as bolted on, and polished sentences cannot rescue a paragraph with no job.

**The evidence that structure comes first.** The 2026-09 aging document scored 1.6 sentence-level
flags per 100 words on the clarity linter, which is fairly clean. The supervisor still called it an
info dump. The sentences were fine, but the document never told the reader why.

**When rules conflict, this order wins:**

1. what the code and the records say (facts are never traded for style);
2. Part 1, structure;
3. Part 2, Thomas's verified voice;
4. Part 3, clarity rules;
5. Part 4, the general AI checklist.

Part 5 lists the known conflicts and how each one is resolved.

---

## Part 1: Structure (the supervisor's feedback)

### 1.1 What the supervisor said

These points come from the aging review meeting (week of 2026-09-28), in the order they matter.
The quotes are from the transcript.

1. **Tell a story, not an info dump.** "The problem with the writing is you're not telling a story."
   The supervisor's outline for the aging section:
   - A contract covers future seasons nobody can observe yet, and the goal is to estimate the most
     likely outcome.
   - "The best way to estimate this is to compare him to similar players."
   - The next question is how to define similar: "I'm going to look at these eight statistics, and I
     think these ones are more important, so I'm going to weight them more. And here's why."
   - Then: "there could be a lot of noise there", so the estimate is blended toward a broader
     average.
   - Then: "this is probably a better estimate of where they should be, and I'm just going to project
     from there."
   - "You just kind of bring them along for the ride."
2. **Every paragraph has a job.** "With every paragraph: what should the person have taken away? Why
   did I tell them this?"
3. **Say why you did each thing.** "You're talking about this adjustment, but you're not telling why
   you're doing it." A step without its reason is the most common failure.
4. **Basics before special cases.** In the exit section, the reader got the 31-34 star cell, the
   logistic link and the tenfold boundary jump before being told why exit risk matters. The
   supervisor's outline for that section was:
   - there is always a risk a player leaves before his contract ends;
   - so a club needs the chance he reaches each season;
   - so the model groups players by quality and age, estimates that chance with a logistic regression
     ("here it is"), and scales each season's projection by it.
   - Special cases come after that, if at all.
5. **State the motivating fact the reader is missing.** "Using the departure count alone would assign
   zero exit risk." The text never added "and that is wrong, because there is always a risk". That
   missing sentence is the reason for the whole paragraph.
6. **A sentence of principle beats an example that implies it.** On the 10%/90%/81% survival example:
   "if the idea to get across is: we calculate a value for each year, not one value for all of them,
   that's all you need to say." Keep an example only when it carries something the principle cannot,
   such as a worked number the reader will check.
7. **Show the mechanics.** "You need to be talking through that Excel file. These are the formulas
   used." He also asked for the regression output, and for a worked contract table: each season's
   projection, the chance of reaching it, and the result.
8. **Defend each judgement call.** "Usually you can get around it by saying: I tried these different
   values and nothing really changed." A hand-set number needs its sensitivity test beside it.
9. **Back non-standard methods with academic references.** On the Gaussian weights: "you better have
   some academic references to back it up."
10. **Keep terms stable.** This was Thomas's own concern ("so many terms get flown around"). The
    supervisor suggested a glossary: one name per concept, defined once, used each time.
11. **Signpost.** Subheadings help. Notes on what each paragraph is for are useful while drafting,
    "but ultimately you want the reader to know that, so you may as well just put it in."
12. **Write what you say.** "You tell a good story, but what you tell is so different from what you
    write." Thomas's spoken explanations in meetings were clearer than the text. Use them: explain the
    step aloud, or take the transcript, then edit that into prose (Part 7 does this).
13. **Know where to stop.** "There's always something more you can do in a model. At some point you
    do just have to say: this is as far as I can go." State the limit and what lies beyond it, then
    move on.

### 1.2 The story spine

Write the spine as bullet points before any prose. Each bullet is one sentence. If a step's "why"
bullet is empty, stop and find the reason before writing.

**For a section about one method or model component:**

1. *The problem.* What the reader needs to know, and why it cannot be observed directly.
2. *The idea.* The approach in one sentence, and why it is a sensible way to attack the problem.
3. *The steps,* in the order the method runs them. Each step gets four things:
   - **what** it does, in plain words, then the formula;
   - **why** it is needed (the problem the previous step left);
   - **how much it matters, and what else was tried** (the recorded test, its number and its source);
   - **the take-away** (one sentence the reader should keep).
4. *The result.* A worked example on one real case, end to end, with numbers the reader can check.
5. *The limits.* What the method cannot do, and where the work stops.

**For a single judgement call** (a weight, a cutoff, a window): the risk it guards against, then the
rule, then the value chosen, then what the value means in practice, then the sensitivity test ("any
value from A to B moves error by under X%"), then the take-away.

### 1.3 Paragraph rules

- **One job per paragraph.** The first sentence says what the paragraph establishes. The rest
  supports it.
- **The take-away test.** Write the reader's one-line take-away for each paragraph in the margin. If
  you cannot, the paragraph has no job: merge it or cut it.
- **Principle, then detail, then example.** An example illustrates a principle already stated. It
  never replaces one.
- **Reason before mechanism.** "To stop a thin group of comparables controlling the estimate, the
  model mixes in the league average" is better than "The model mixes in the league average. This
  prevents..."
- **Special cases and edge rules go last**, or into a footnote or appendix, after the main path is
  clear.
- **Six sentences at most** as a guide. A longer paragraph usually holds two jobs.
- **Transitions carry the logic.** Begin a step with the problem the last step left open ("This
  estimate rests on two seasons, and two seasons are noisy. So...").
- **Cut repeats.** When two paragraphs say the same thing, keep the shorter (Part 2, content habits).

### 1.4 Evidence the reader needs

- **Formulas.** State the formula, define each symbol once, and walk one real number through it.
  Point to where it lives (a script function, or a named spreadsheet cell). Example: weight =
  exp(−d² / (2h²)), where d is the distance and h is the yardstick, so a comparable one yardstick away
  gets exp(−0.5) ≈ 0.61.
- **Regressions.** Show the fitted table, which is the coefficients, standard errors and sample. Give
  the sample in independent units, not only rows. Then say in one sentence what the table means.
- **Worked cases.** One real case, one row per period, with each quantity the result is built from,
  in the order the method combines them.
- **Judgement calls.** Give the sensitivity test with its number and its source document. If none
  exists, say the value is untested. Do not imply it was chosen by evidence.
- **References.** A method an economist would not recognise on sight needs a citation. Never invent
  one. Write `[ref needed]` and list candidates for Thomas to check.

### 1.5 Terms

- **One name per concept, used each time.** If the text says "comparables", it never also says
  "similar players", "matches" and "the pool" for the same thing. The reader cannot tell whether those
  are four things or one. (This is also Part 4, item 11.)
- **Define each term once, at first use, in plain words**, then say why it matters.
- **Keep a glossary** where the project has one (in the xNPV project, `40_DOCS/Glossary.md`; create it
  the first time it is needed, each entry written from the code).
- **Codenames are not names.** Model labels, horizon codes, phase numbers and decision IDs go in
  parentheses after the plain description, if at all.

---

## Part 2: Thomas's verified voice

Built by diffing a Claude-drafted status report against Thomas's own final edit of it, sentence by
sentence. Each rule here traces to a real before → after pair from that diff.

### Strong patterns (3+ confirmed instances, treat as close to hard rules)

- **"Every" → "Each."** Confirmed three times independently. Default to "each" when referring to
  individual members of a set treated one at a time.
- **Cuts intensifiers.** "at all," "badly," "genuinely," "deliberately," "itself" were removed each
  time one appeared. Don't add these for emphasis. If the sentence is true without the intensifier,
  leave it out.
- **Cuts contrastive "not X" tags after a claim.** "estimated, not assumed" → "estimated." "a planning
  assumption, not a historical average" → "a planning assumption." State the positive claim once.
  Keep the "not X" only when the contrast itself does identification work the paragraph would
  otherwise lose.
- **Oxford comma, always**, in each list of three or more.
- **Restarts a new sentence with "This is / This was / This produced"** rather than extending with a
  participle or a colon. "...arrives, estimated from the historical data..." → "...arrives. This is
  estimated from the historical data..."
- **"X, which is Y" over "X: Y"** for definitions. "an aging curve: the age-conditional pattern..." →
  "an aging curve, which is the age-conditional pattern..."

### Reliable patterns (2 confirmed instances)

- **Explicit "for example" / "e.g." signaling**, even in place of an implicit "so." "...full panel, so
  a projection dated 2019..." → "...full panel; for example, a projection dated 2019..."
- **Comma-wraps mid-sentence "therefore."** "is therefore aged" → "is, therefore, aged." This is a
  real preference. Don't strip these commas out as an error.
- **Semicolon + connector** instead of two sentences or "and." "...final season. A contract
  expiring..." → "...final season; however, one expiring..."
- **Plain word over the literary synonym.** "arithmetic" → "math"; "trailing cascade" → "trailing
  weighted average."
- **Spells out the full proper name rather than a shorthand**, even on repeat reference. "the
  game-level metric" → "the Game Value metric"; "known ceiling" → "known salary cap ceiling."

### Single-instance patterns (apply with judgment)

- "the ones" → "those" (more formal register).
- Exact figures over vague fractions: "one quarter" → "25%."
- "no X and no Y" → "no X or Y" in negative constructions. This is also standard grammar, so apply it
  even without a second confirmed instance.
- "There exist two qualifications with this" as an opener. One instance only, so don't over-apply it.
  It is more formal than the surrounding prose.

### Content-level habits (judgment calls, not phrasing swaps)

Thomas's edits also removed content, not just words. When two versions of a paragraph say the same
thing, default to the shorter one:

- Cut a whole paragraph that restated a point already made elsewhere.
- Cut closing summary sentences that added no new information beyond what the prior sentence's
  numbers already established.
- Fix a miscount. "Five candidate mechanical fixes" → "Four," when the list only enumerated four.
  Always recount an enumerated list against its own parenthetical before finalizing the number.

### Register

Formal academic prose with no contractions, written for an econometrics-trained reader who weighs
identification above all else. First person singular is correct ("I wrote it to apportion...").
Do not inject personality, humour, tangents or "mess" to sound human. Precision and directness are
what read as Thomas.

---

## Part 3: Clarity rules (STE-flavoured)

These are adapted from the ASD-STE100 skill (github.com/danyuchn/asd-ste100-skill, MIT) in its
"STE-flavoured" mode for explanatory prose. The structural rules apply. The strict word-list lockdown
does not, except for technical terms (1.5).

- **Active voice, with a named actor.** "The model fits the curve on seasons before the valuation
  date", not "The curve is fitted...". Use the passive only when the actor does not matter.
- **One idea per sentence.** About 25 words for a description is a guide, not a cap. A sentence that
  needs a formula or a qualifier may run longer.
- **Verbs, not nouns made from them.** "The model weights each comparable", not "the weighting of each
  comparable is performed".
- **No noun stacks of four or more words.** Write "the yardstick's pool of pairs", not "yardstick pair
  pool construction rule".
- **Plain verbs.** Write "start", not "kick off". Write "examine", not "dive into".
- **Keep each hedge at its strength.** "May", "about" and "in this sample" carry the confidence of
  the claim. A rewrite that turns "may" into "does" makes a new claim. A rewrite that supplies a cause,
  frequency or mechanism the source did not state has stopped being a rewrite.
- **Simple tenses**, unless the compound form carries meaning ("has been tested and still holds").
- **Don't shorten past clarity.** The goal is a sentence the reader cannot misread, not the shortest
  one.

**Mechanical check (advisory).** The checker is `scripts/ste-lint.py` in this skill's folder, copied
from that repository (MIT, see `scripts/LICENSE-ste-lint`). Always disable its semicolon rule, which
conflicts with Thomas's voice (Part 5):

    python scripts/ste-lint.py --disable semicolon draft.md

It flags long sentences, phrasal verbs, nouns made from verbs, marketing adjectives, synonym rotation,
passives and compound tenses. It never flags hedges. Treat its output as a list to look at, not a
score to drive to zero. It cannot see structure.

---

## Part 4: General AI-pattern checklist

Based on Wikipedia's "Signs of AI writing" guide. Apply it everywhere except where Part 5 overrides.

**Content patterns:**
1. **Undue significance/legacy framing.** "stands as a testament," "underscores its importance,"
   "represents a shift." Cut.
2. **Undue notability claims.** "independent coverage," "active social media presence." Replace with a
   specific sourced claim or cut.
3. **Superficial -ing tack-ons.** "...ensuring...", "...highlighting...", "...reflecting..." appended
   for fake depth. Cut or make a real sentence.
4. **Promotional language.** "vibrant," "profound," "showcases," "renowned," "must-visit." Replace with
   specific, factual description.
5. **Vague attributions.** "industry reports," "observers have cited." Name the source or delete the
   claim.
6. **Formulaic "Challenges and Future Prospects" boilerplate.** Replace with specific facts or cut.

**Language and grammar:**
7. **Overused AI vocabulary.** actually, additionally, crucial, delve, emphasizing, enhance,
   fostering, interplay, intricate, key (adj.), landscape (abstract), pivotal, showcase, tapestry,
   testament, underscore (verb), vibrant. Plain language or cut.
8. **Copula avoidance.** "serves as," "boasts," "features [a]." Use "is/are/has."
9. **Negative parallelisms.** "It's not just X; it's Y." Rewrite as a direct statement.
10. **Rule-of-three padding.** Use as many items as exist.
11. **Elegant variation** (protagonist/main character/central figure/hero for the same referent). Pick
    one term and use it throughout.
12. **False ranges.** "from X to Y" where X and Y aren't on a real scale. List the actual items.
13. **Passive voice / subjectless fragments.** "No configuration file needed." Restore the subject
    where it's clearer.

**Style patterns:**
14. **Em dash overuse.** Rewrite with commas, periods, or parentheses. Zero tolerance in Thomas's
    documents: each prior document pass in the NHL project drove the em-dash count to zero, so keep it
    there.
15. **Boldface overuse.** Remove from inline terms unless critical.
16. **Inline-header vertical lists.** Bolded headers + colons inside bullets. See the override in
    Part 5.
17. **Title case in headings.** See the partial override in Part 5.
18. **Emojis in structured content.** Remove.
19. **Curly quotation marks** in code or plain-text contexts. Use straight quotes instead. Word
    documents keep Word's own curly quotes and apostrophes. This rule is about markdown and code
    contexts, not .docx prose.

**Communication patterns:**
20. **Collaborative artifacts.** "I hope this helps," "Certainly!," "let me know." Delete and start
    with content.
21. **Knowledge-cutoff disclaimers.** Rewrite as plain uncertainty or find a real source.
22. **Sycophantic tone.** Delete the flattery.

**Filler and hedging:**
23. **Filler phrases.** "in order to" → "to"; "due to the fact that" → "because"; "at this point in
    time" → "now."
24. **Excessive hedging.** Collapse stacked qualifiers ("could potentially possibly") into one plain
    claim. See Part 5 for how this meets the clarity rule on hedges.
25. **Generic positive conclusions.** "the future looks bright." Cut, or end on a specific fact.
26. **Hyphenated pair overuse.** third-party, cross-functional, data-driven, real-time, long-term
    when used as reflexive filler compounds. Drop the hyphen or the word where it adds no precision.
27. **Persuasive authority tropes.** "at its core," "what really matters," "fundamentally." Delete the
    framing and make the point directly.
28. **Signposting/announcements.** "let's dive in," "here's what you need to know." Delete and start
    with content. This is not the signposting in 1.1 point 11: a subheading or a topic sentence that
    tells the reader what the paragraph establishes is wanted, while an announcement that content is
    coming is not.
29. **Fragmented headers.** A heading followed by a one-line paragraph that only restates the heading.
    Delete the filler line.

---

## Part 5: Conflicts and overrides

**Semicolons (clarity vs voice).** STE bans the semicolon. Thomas uses a semicolon plus a connector
("; however,", "; for example,") on purpose. **Thomas's voice wins.** Use the semicolon with a
connector where it joins two closely tied clauses. Do not use it to string a list of separate ideas
into one sentence, which the one-idea rule still forbids.

**Colons for definitions.** Use "X, which is Y" (Part 2). A colon still introduces a list or a worked
example.

**Hedges (checklist item 24 vs Part 3).** Collapse a stack of qualifiers into one, at the same
strength: "could potentially possibly" becomes "may". Never remove the last hedge, and never upgrade
"may" to "does".

**Override of item 16 (inline-header vertical lists).** Thomas's status reports use this pattern on
purpose and consistently: a short label, a period, then prose, e.g. "First attempt: freeze any weak
baseline flat. Hold anything below..." and "Draft-pick valuation. Fit the value-by-pick-position
curve..." It is a load-bearing structure in his documents, not a generic AI tic. **Keep it.** The
generic rule targets bolded-header-plus-colon constructions used as a crutch for thin content.
Thomas's version is plain text (not bold), uses a period (not a colon), and each bullet carries real
analytical content. That is the test if it's unclear which case you're in.

**Partial override of item 17 (title case in headings).** Thomas's documents use two tiers, both on
purpose:
- **Top-level numbered sections keep title case**: "1. The Project in Brief," "5. Identification
  Threats," "7. Remaining Work, in Order."
- **All sub-headings below that use sentence case**: "Step 3: Projecting forward with the aging
  curve," "A consequential case: players currently below replacement level," "Look-ahead bias,"
  "Goaltenders."

Match whichever tier you're writing. Don't flatten the numbered top-level headings to sentence case.

**No "personality" pass.** Some humanizing guides tell the writer to add opinions, humour or
tangents. Do not apply that here (Part 2, register).

---

## Part 6: Rules for the xNPV thesis project

Apply these when the text explains the NHL trade-market model. The repository's CLAUDE.md has the full
list.

- **Read the code first.** Describe each mechanism from the script that runs it. Do not use the state
  files, an earlier explainer or memory. Note which model the text covers: since 2026-10-02 skaters
  are priced on xNPV 1 only, and a document about xNPV 0 explains a model that no longer prices
  anything.
- **Reader-facing documents stand alone.** They do not name the supervisor, mention "the meeting", or
  present themselves as a reply to feedback.
- **Figures keep their row labels** from the source table. Count before writing "all", "every" or
  "none".
- **Simplified walkthroughs drop no step** of the pipeline. Discounting is the step that has gone
  missing before.
- **A tightened sentence is checked against the code** as carefully as the original was.
- **Editing a .docx in place.** Follow the project's assert-guarded XML editing workflow: str_replace
  on `document.xml` run text, validate with the docx skill's validator, never hand-edit verbatim.

---

## Part 7: Worked rewrites

**A. Fixed comparables.** The original, from the 2026-09 aging document:

> The original similarity weights remain fixed as the projection moves forward. At each later age, the
> model uses the subsequent changes observed for those same comparable players. It does not update
> the match using the target player's future performance. As fewer comparables supply observations at
> older ages, the broader age pattern generally receives more influence.

Each sentence is true, and the reader is never told why any of it matters. The rewrite is built from
Thomas's spoken explanation in the meeting, checked against `aging_curve.AgingModel.project`:

> Once the comparable players are chosen, they stay chosen. The model picks them and sets their
> weights once, at the player's last observed age, from seasons he has played. Each later year of the
> projection asks the same group the same question: how did these players change from this age to the
> next?
>
> The alternative would be to choose a new group each year. That would mean asking which historical
> players resemble the projected player, which is a version of him the model invented the year
> before. Each round would build on the last round's guess. Holding the group fixed keeps each step
> tied to evidence: real players at the same age, and what happened to them next.
>
> The cost is that the group thins out. At older ages fewer of the original comparables are still in
> the league, so fewer supply a change for each later age. The league-wide average change for the
> position and age, therefore, carries more of the estimate.

**B. A judgement call defended.** The original:

> The broader average receives a fixed weight of ten. The comparable side receives the sum of the
> individual similarity weights for players with an observed value at the age being estimated.

The rewrite, with its numbers from `aging_curve._shrunk` and the 2026-09-28 settings test:

> A small or poorly matched group of comparables could produce an extreme estimate on its own. To
> guard against that, the model mixes the comparables' average with the league average for the same
> position and age. The league average counts as ten extra comparables, each an exact match. When the
> comparables are many and close, their weights sum well above ten and they dominate; when they are
> few or distant, the league average takes over. Ten is a judgement call, so it was tested: any value
> from 0.01 to 20 changes forecast error by less than 0.06%. The choice does not drive the results.

---

## Process

1. **For a small edit** (a sentence or a paragraph), make the edit with Parts 2-5 in mind. No full
   cycle is needed.
2. **For a section or a document:**
   1. In the xNPV project, read the code first (Part 6).
   2. Write the story spine (1.2).
   3. Draft from the spine, with Parts 2-4 in mind from the start.
   4. Attach the evidence (1.4).
   5. Run the clarity linter with `--disable semicolon` and review what it flags.
   6. Read the draft back once and ask what still tags it as AI-written, or as not Thomas's. Fix those
      specifically.
   7. Run the final checklist.

## Final checklist

- [ ] Facts match the code and records that apply today.
- [ ] The spine is complete: each step has a why, a test or an "untested" flag, and a take-away.
- [ ] The first sentence of each paragraph states its job. Basics come before special cases, and
      principles before examples.
- [ ] Formulas come with one worked number. Regression tables and worked cases are included where the
      section rests on them.
- [ ] Each judgement call carries its sensitivity test, or says it is untested.
- [ ] Non-standard methods are cited or marked `[ref needed]`. No reference is invented.
- [ ] Terms match the glossary, with no synonym rotation and no bare codenames.
- [ ] Voice: "each" for members taken one at a time, no intensifiers, Oxford commas, no contractions,
      zero em dashes.
- [ ] Hedges are kept at their strength, and stacked hedges are collapsed to one.
- [ ] Enumerated lists are recounted against their stated number.
- [ ] Reader-facing text does not address the supervisor or the meeting.
