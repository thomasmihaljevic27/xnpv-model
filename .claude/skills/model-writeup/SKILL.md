---
name: model-writeup
description: "Use when drafting or revising any reader-facing explanation of the xNPV model: thesis sections, supervisor documents (40_DOCS/Supervisor_Drafts), the 40_DOCS explainers, status reports, or a method write-up of any one component (aging, the chance of playing, the price line, draft picks, prospects). It turns a correct but unstructured account into a story the reader can follow, in which each step says why it exists, what it does, what else was tried and what the reader should take away. It then tightens sentences with STE-flavoured clarity rules. Triggers: write up, explain the model, rewrite this section, paper draft, supervisor document, 'info dump', 'make this read better', methods section. Not for chat replies, session logs or commit messages."
---

# Writing up the model so a reader can follow it

The 2026-09 aging document was accurate and dense, and it read as an info dump. A mechanical sentence
check (`scripts/ste-lint.py`) gives it 1.6 flags per 100 words, which is fairly clean. **So the problem
was not the sentences. It was that the document never told the reader why.** Fix the structure first
(§2-§4). Fix the sentences last (§5).

## 1. The supervisor's writing feedback (meeting, week of 2026-09-28)

These are the points made in the meeting, in the order they matter. The quotes are from the transcript.

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
   you're doing it." A step without its reason is the commonest failure.
4. **Basics before special cases.** In the exit section, the reader got the 31-34 star cell, the
   logistic link and the tenfold boundary jump before being told why exit risk matters at all. The
   supervisor's outline for that section was:
   - there is always a risk a player leaves before his contract ends;
   - so a club needs the chance he reaches each season;
   - so the model groups players by quality and age, estimates that chance with a logistic regression
     ("here it is"), and scales each season's projection by it.
   - Special cases come after that, if at all.
5. **State the motivating fact the reader is missing.** "Using the departure count alone would assign
   zero exit risk." What the text never said is "and that is wrong, because there is always a risk".
   That missing sentence is the reason for the whole paragraph.
6. **A sentence of principle beats an example that implies it.** On the 10%/90%/81% survival example:
   "if the idea to get across is: we calculate a value for each year, not one value for all of them,
   that's all you need to say." Keep an example only when it carries something the principle cannot,
   such as a worked number the reader will check.
7. **Show the mechanics.** "You need to be talking through that Excel file. These are the formulas
   used." He also asked for the regression output, and for a worked contract table: each season's
   projection, the chance of reaching it, and the result.
8. **Defend every judgement call.** "Usually you can get around it by saying: I tried these different
   values and nothing really changed." A hand-set number needs its sensitivity test beside it.
9. **Back non-standard methods with academic references.** On the Gaussian weights: "you better have
   some academic references to back it up. Otherwise it's just going to be dumb."
10. **Keep terms stable.** This was Thomas's own concern ("so many terms get flown around"), and the
    supervisor suggested a glossary: one name per concept, defined once, used every time.
11. **Signpost.** Subheadings help. Notes on what each paragraph is for are useful while drafting, "but
    ultimately you want the reader to know that, so you may as well just put it in."
12. **Write what you say.** "You tell a good story, but what you tell is so different from what you
    write." Thomas's spoken explanations in meetings were clearer than the text. Use them: explain the
    step aloud, or take the transcript, then edit that into prose (§9 does this).
13. **Know where to stop.** "There's always something more you can do in a model. At some point you
    do just have to say: this is as far as I can go." State the limit and what lies beyond it, then
    move on.

## 2. Workflow

1. **Read the code first.** Every mechanism is described from the script that runs it. Do not use
   `00_STATE/`, an earlier explainer or memory (CLAUDE.md, "Don't describe a mechanism you haven't
   read the code for"). Note which model the text covers. Since 2026-10-02 skaters are priced on
   xNPV 1 only. A document about xNPV 0 explains a model that no longer prices anything.
2. **Write the story spine** (§3) as bullet points before any prose. Each bullet is one sentence. If
   a step's "why" bullet is empty, stop and find the reason before writing.
3. **Draft from the spine.** One spine bullet becomes one paragraph, or a few (§4).
4. **Attach the evidence** (§6): formula, worked number, table, sensitivity test and reference for
   each choice.
5. **Sentence pass** (§5). Run the linter as an advisory check.
6. **Terms pass** (§7). Every technical term matches the glossary.
7. **Reader-facing pass** (§8).
8. **Voice pass.** If the `thomas-voice-humanizer` skill is available, run it last. It changes voice,
   not content, so it goes after the structure is right.

## 3. The story spine

**For a section about one model component:**

1. *The problem.* What the club needs to know, and why it cannot be observed directly.
2. *The idea.* The approach in one sentence, and why it is a sensible way to attack the problem.
3. *The steps,* in the order the code runs them. Each step gets four things:
   - **what** it does, in plain words, then the formula;
   - **why** it is needed (the problem the previous step left);
   - **how much it matters, and what else was tried** (the recorded test, its number and its source);
   - **the take-away** (one sentence the reader should keep).
4. *The result.* A worked example on one real player, end to end, with the numbers the reader can
   check in a table.
5. *The limits.* What the method cannot do, and where the work stops.

**For a single judgement call** (a weight, a cutoff, a window):
the risk it guards against, then the rule, then the value chosen, then what the value means in
practice, then the sensitivity test ("any value from A to B moves error by under X%"), then the
take-away ("the choice does not drive the results", or, honestly, "it does, and here is the
evidence for the value chosen").

## 4. Paragraph rules

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

## 5. Sentence rules (STE-flavoured)

These are adapted from the ASD-STE100 skill (github.com/danyuchn/asd-ste100-skill, MIT), in its
"STE-flavoured" mode for explanatory prose. The structural rules are applied. Its strict word-list
lockdown is not, except for technical terms (§7).

- **Active voice, with a named actor.** "The model fits the curve on seasons before the valuation
  date", not "The curve is fitted...". Use the passive only when the actor truly does not matter.
- **One idea per sentence.** About 25 words for a description is a guide. A sentence that needs a
  formula or a qualifier may run longer: flag it rather than lose the qualifier.
- **No semicolons.** Split the sentence. Use em dashes rarely. They usually mark a sentence that
  should be two.
- **Verbs, not nouns made from them.** "The model weights each comparable", not "the weighting of
  each comparable is performed".
- **No noun stacks of four or more words.** Write "the yardstick's pool of pairs", not "yardstick
  pair pool construction rule".
- **Plain verbs.** Write "start", not "kick off". Write "examine", not "dive into".
- **Keep every hedge at its strength.** "May", "about" and "in this sample" carry the confidence of
  the claim. A rewrite that turns "may" into "does" makes a new claim. A rewrite that supplies a
  cause, frequency or mechanism the source did not state has stopped being a rewrite.
- **Simple tenses**, unless the compound form carries meaning ("has been tested and still holds").
- **Don't shorten past clarity.** The goal is a sentence the reader cannot misread, not the
  shortest one.

**Mechanical check (advisory).** The checker is `scripts/ste-lint.py`, copied from that repository
(MIT, see `scripts/LICENSE-ste-lint`):

    python .claude/skills/model-writeup/scripts/ste-lint.py draft.md
    python .claude/skills/model-writeup/scripts/ste-lint.py --disable passive-voice draft.md

It flags semicolons, long sentences, phrasal verbs, nouns made from verbs, marketing adjectives,
synonym rotation, passives and compound tenses. It never flags hedges. Treat its output as a list to
look at, not a score to drive to zero. It cannot see structure, which was the real problem (see the
opening).

## 6. Evidence the reader needs

- **Formulas.** State the formula, define every symbol once, and walk one real number through it.
  Point to where it lives (a script function, or a named spreadsheet cell).
  - Example: weight = exp(−d² / (2h²)), where d is the distance and h is the yardstick. A comparable
    one yardstick away gets exp(−0.5) ≈ 0.61.
- **Regressions.** Show the fitted table: coefficients, standard errors and the sample (units, not
  only rows; CLAUDE.md, "Don't report a row count as the amount of evidence"). Then say in one
  sentence what the table means.
- **The worked contract.** One real player, one contract, one row per season. Show every quantity the
  value is built from, in the order the code multiplies them.
- **Judgement calls.** Give the sensitivity test with its number and its source document. If none
  exists, say the value is untested. Do not imply it was chosen by evidence.
- **References.** A method an economist would not recognise on sight needs a citation, for example
  kernel weighting or the median-distance yardstick. Never invent one. Write `[ref needed]` and list
  candidates for Thomas to check. `40_DOCS/Aging_Review_Meeting_Followups.md` §2 item 9 has a
  starting list for the Gaussian weights.

## 7. Terms

- **One name per concept, used every time.** If the text says "comparables", it never also says
  "similar players", "matches" and "the pool" for the same thing. The reader cannot tell whether
  those are four things or one.
- **Define each term once, at first use, in plain words.** Then say why it matters (the working-style
  rule in CLAUDE.md).
- **Keep a glossary at `40_DOCS/Glossary.md`.** Create it the first time it is needed. Write each
  entry from the code, with the function that implements it. Every document uses the glossary's
  words.
- **Codenames are not names.** Model labels, horizon codes, phase numbers and decision IDs go in
  parentheses after the plain description, if at all (CLAUDE.md, "Never use a codename as if it were
  a name").

## 8. Reader-facing checks (from CLAUDE.md)

- The text does not name the supervisor, mention "the meeting", or present itself as a reply to
  feedback. It stands on its own.
- Every figure carries its row label from the source table. Universal words ("all", "every",
  "none") are counted before they are written.
- No step of the pipeline is dropped from a simplified walkthrough. Discounting is the one that has
  gone missing before.
- A tightened sentence is checked against the code as carefully as the original was.

## 9. Worked rewrites

**A. Fixed comparables.** The original, from the 2026-09 aging document:

> The original similarity weights remain fixed as the projection moves forward. At each later age, the
> model uses the subsequent changes observed for those same comparable players. It does not update
> the match using the target player's future performance. As fewer comparables supply observations at
> older ages, the broader age pattern generally receives more influence.

Every sentence is true, and the reader is never told why any of it matters. The rewrite below is built
from Thomas's spoken explanation in the meeting, checked against `aging_curve.AgingModel.project`:

> Once the comparable players are chosen, they stay chosen. The model picks them and sets their
> weights once, at the player's last observed age, from seasons he has actually played. Each later
> year of the projection asks the same group the same question: how did these players change from
> this age to the next?
>
> The alternative would be to choose a new group every year. That would mean asking which historical
> players resemble the *projected* player, a version of him the model invented the year before. Each
> round would build on the last round's guess. Holding the group fixed keeps every step tied to
> evidence: real players at the same age, and what actually happened to them next.
>
> The cost is that the group thins out. At older ages fewer of the original comparables are still in
> the league, so fewer supply a change for each later age. The league-wide average change for the
> position and age then carries more of the estimate.

**B. A judgement call defended.** The original:

> The broader average receives a fixed weight of ten. The comparable side receives the sum of the
> individual similarity weights for players with an observed value at the age being estimated.

The rewrite, with its numbers taken from `aging_curve._shrunk` and the 2026-09-28 settings test:

> A small or poorly matched group of comparables could produce an extreme estimate on its own. To
> guard against that, the model mixes the comparables' average with the league average for the same
> position and age. The league average counts as ten extra comparables, each an exact match. When the
> comparables are many and close, their weights sum well above ten and they dominate. When they are
> few or distant, the league average takes over. Ten is a judgement call, so it was tested: any value
> from 0.01 to 20 changes forecast error by less than 0.06%. The choice does not drive the results.

## 10. Final checklist

- [ ] Written from the code that runs today, for the model that prices today.
- [ ] The spine is complete: every step has a why, a test or untested flag, and a take-away.
- [ ] The first sentence of each paragraph states its job.
- [ ] Basics come before special cases, and principles before examples.
- [ ] Each formula is shown with one worked number. The regression tables and the worked contract
      table are included where the section rests on them.
- [ ] Each judgement call carries its sensitivity test, or says it is untested.
- [ ] Non-standard methods are cited, or marked `[ref needed]`. No reference is invented.
- [ ] Terms match the glossary, with no synonym rotation and no bare codenames.
- [ ] The linter output has been reviewed, with hedges kept at their strength.
- [ ] Nothing addresses the supervisor or the meeting.
