---
name: writing-style
description: "Thomas's writing style for formal academic and technical text: thesis and paper sections, supervisor documents, methodology write-ups, status reports, and model explainers. Use when drafting, rewriting, editing, or reviewing formal prose, including a single paragraph. Runs in two passes: (1) structure and econometric rigor, and (2) voice, full-sentence flow, and AI-trope removal, then a mechanical check of the banned patterns. Triggers: write up, rewrite this, draft a section, edit this paragraph, make this read better, info dump, sounds like AI, methods section, status report. Not for casual chat replies, session logs, or commit messages."
---

# Writing Style

Version 2.0 (2026-11-25): the revamp Thomas wrote, merged with the parts of version 1 it had dropped
(the personification ban, the project vocabulary, two worked rewrites, the mechanical check, and "write
what you say"). The version-controlled copy is `40_DOCS/writing-style/SKILL.md` in the xNPV repository.

This skill governs all formal academic and technical writing. It operates on a strict priority
hierarchy. When rules conflict, the higher item wins:

1. **Facts and code.** Never trade empirical accuracy for style.
2. **Structure.** Tell a logical story; every paragraph must earn its place.
3. **Academic register and voice.** Write for a Master's economics committee in impersonal, formal prose.
4. **Full-sentence flow and clarity.** Every sentence must be grammatically complete, unambiguous, and
   smoothly connected.
5. **AI-pattern removal.** Strip both generic AI clichés and over-corrected, robotic templates.

---

## Pass 1: Structure, Logic, and Evidence

Build the logical skeleton before writing prose. Polished sentences cannot rescue a paragraph with no job.
A document that scores well on sentence-level checks can still be an info dump if it never tells the
reader why each step exists.

### 1.1 The story spine

Outline any section as one-sentence bullets before drafting. If a step's "why" is empty, find the reason
before writing.

**For a method or model component:**
1. **The problem.** What must be estimated, and why it cannot be observed directly.
2. **The idea.** The approach in one sentence, and why it is a sensible way to solve the problem.
3. **The steps, in execution order.** For each step, state:
   - **what** it does in plain words, followed by the formula;
   - **why** it is needed (the problem the previous step left open);
   - **what else was tried and how much it matters** (the test result and its number);
   - **the take-away** (one sentence the reader should keep).
4. **The result.** One worked example on a real case, end to end, with numbers the reader can check.
5. **The limits.** What the method cannot do, and where the work stops. State the limit and what lies
   beyond it, then move on.

**For a judgement call** (a weight, cutoff, or window): state the risk it guards against, the rule, the
value chosen, what that value means in practice, the sensitivity test (or state that it is untested), and
the take-away.

**Write what you say.** Thomas explains a step more clearly aloud than the first drafts did on paper.
Where a meeting transcript or his own explanation exists, start from it and edit it into prose.

### 1.2 Paragraph rules

- **One job per paragraph.** The opening sentence states what the paragraph establishes; the rest
  supports it. If the reader's one-line take-away cannot be written, merge or cut the paragraph.
- **Reason before mechanism.** State why an adjustment is needed before explaining how it works.
- **Principle before example.** State the general rule first. Keep an example only when it carries
  something the principle cannot (such as a worked number).
- **Basics before special cases.** Establish the main path before discussing edge cases or exceptions.
- **Nothing argued before it is introduced.** A reason that rests on a later section is moved after it.
- **No "mic dropping."** Never end a paragraph with a standalone fact or number without explaining why
  it matters.
- **Call rejected options rejected first.** Signal that an alternative was tested and rejected *before*
  describing it, so the reader never mistakes it for part of the adopted model.
- **Explicitly introduce uniform examples.** If one case (for example, a D+2 prospect) is the running
  example across tables or text, state that up front.
- **Anti-template rule.** Never stamp the same sentence frame across consecutive subsections (for
  example, repeating *"The options were X or Y. Y was adopted..."*). Vary how decisions are introduced:
  lead with the problem, the data, or the rule itself.
- **Cut repeats.** When two paragraphs say the same thing, keep the shorter one.

### 1.3 Evidence and econometric standards

- **Formulas.** State the formula, define each symbol once ("C is his cap hit", never "and C his cap
  hit"), and walk one real number through it.
- **Write every value formula in full.** Each season's value and cost in that season's dollars, divided
  by (1.03)^k, the same way for each model; then say in one line where cap growth and discounting cancel.
  Never present the cancelled cap-share sum as the formula.
- **Show the model each time it grows.** Display the updated equation each time a variable or term is
  added, not just once at the end. Every term discussed in the text appears in the equation.
- **Describe the code that runs.** Never describe an "equivalent" specification; describe the method
  the code implements.
- **Explain regressions by what they compare.** State what is compared with what, and what the
  coefficient means in hockey or economic terms, with one worked number. Where a quadratic term bends a
  curve, state where the curve turns.
- **Dummy variables and interaction terms.** Name the set of dummy variables and its groups, say that
  exactly one is 1 for each row, and say that interacting it with a term gives that term a separate,
  estimated coefficient in each group.
- **Statistical significance.** Report p-values cleanly (the test defined once in a table note). Write
  *"statistically significant at the 5% level (p = 0.03)"*, never *"reliable."* State honestly where
  terms are not significant. Say what each p-value tests against (no effect, or the current model). An
  adopted term with p above 0.05 needs a stated reason or a test of dropping it.
- **No claim without its proof.** A claim the document does not show (a figure or a table) is cut or
  shown.
- **Tables and figures.** Bold every tie at the precision shown. Draw cumulative shares as a share of
  the whole group so the never-reached share is visible. Several tested figures go in a table, not a
  paragraph.
- **References.** Cite peer-reviewed sources for non-standard econometric methods. Never invent a
  citation; write `[ref needed]` if a source must be verified. Name each data source with who it is and
  why it is credible.

---

## Pass 2: Voice, Clarity, and AI-Trope Removal

### 2.1 Register and academic terminology

- **No first person.** Do not use *"I"*, *"me"*, or *"my"* in academic writing. Use impersonal
  constructions (*"A separate value was chosen..."*, *"The model estimates..."*, *"Each prospect's
  remaining NPV is regressed on..."*).
- **No personification.** A model, forecast, regression, discount, or price line does not act, know,
  ask, see, read, learn, or treat. Say what is done to what: *"A cap hit is in fixed dollars, so on the
  cost side discounting is present,"* never *"on the cost side only the discount acts."*
- **No contractions.** Write *"do not"*, *"cannot"*, *"it is"*.
- **No personality injection.** Do not add humour, tangents, or casual commentary to sound human.
  Precision and directness are the voice.
- **Use standard Master's-level econometric terminology.** Plain English applies to sentence structure,
  *not* to turning technical terms into folk English. Define each term once, at first use:
  - Write **dummy variable** (or **indicator variable**), never *"yes-or-no input."*
  - Write **interaction term**, never *"a slope for defencemen."*
  - Write **regression**, never *"the fit."*
  - Write **RMSE** (root mean squared error); on seasons the estimation did not use, **out-of-sample
    RMSE**. Never *"held-out error."*
  - Name variables accurately (for example, *"year-over-year change"*, not *"trend"*, if it only
    measures two consecutive seasons).
  - Name a coined label by its technical name (a kernel's **bandwidth**, not *"yardstick"*).

### 2.2 Full-sentence flow (anti-"caveman talk")

Do not over-compress prose into telegraphic fragments.

- **Every sentence requires a clear grammatical subject and a main verb.** Never drop subjects or leave
  verbs hanging without a subject.
- **Connect sentences with transitions.** Use transitional words and phrases to carry the logic from one
  sentence to the next. Begin a step with the problem the last step left open.
- **No staccato openers.** Avoid abrupt, choppy, one-clause fragments as opening sentences.
- **One number-claim per clause.** Do not cram a decision, a p-value, a sample size, and a bootstrap
  definition into one comma-spliced sentence. Split into two sentences or move the technical definition
  to a table note.
- **Active voice where the actor matters.** "The model fits the curve on seasons before the valuation
  date." Use the passive when the actor does not matter, and for the impersonal register in 2.1.
- **Inanimate possessives.** Prefer a natural noun compound where one exists (*"forecast error"*,
  *"contract length"*, *"pick value"*) over a forced possessive (*"the forecast's error"*). Keep the
  possessive when the compound would be ambiguous or a stack of four or more nouns, and for people
  (*"Pacioretty's contract"*).
- **Do not shorten past clarity.** The goal is a sentence the reader cannot misread, not the shortest one.

### 2.3 Hard bans and mandatory swaps

The mechanical check (2.6) lists each of these; clear them all before handing a draft over.

- **Zero forward references or meta-signposting.** Never write *"Section 5 checks..."*, *"The terminal
  value is added in Section 4"*, or *"This section builds X; Section Y prices it."* Define terms where
  they first appear and discuss later topics when they are reached.
- **Zero dev-log leakage.** Never include script filenames (`forecast_term_audit.py`), internal run or
  audit dates, manual data-hygiene checks (for example, *"Ages are complete for goaltenders"*), or
  database export trivia. Write for an academic reader, not for the developer.
- **No earlier versions of the model.** Defend each parameter of the model as it exists. A tested
  alternative may stay, briefly; a superseded version, or anything no longer in the model, is not
  mentioned.
- **Ban `"against"` for numerical comparisons.** Never write *"1.1506 against 1.1525."* Use *"compared
  with"*, *"versus"*, or state the change (*"lowered RMSE from 1.1525 to 1.1506"*).
- **Ban `"if he plays"`.** Remove all instances of *"Forecasted WAR if he plays"* or *"if he plays at all."*
- **No sentence starts with `"And"`.** Use a transition (*"Moreover,"*, *"In addition,"*).
- **No defining by negation.** Define concepts by what they *are*, not what they *are not* (cut *"A draft
  pick has no contract and no player yet"*).
- **Periods over colons for independent clauses.** Do not use a colon to join two complete sentences
  when a period is cleaner. Use *"X, which is Y"* for inline definitions. A colon still introduces a list.
- **Zero em dashes.** Use commas, periods, or parentheses instead.
- **No circular reasons.** The reason for a choice is what makes it right, never that the model makes it.
- **Be exact with numbers and outcomes.** Write *"-0.5 WAR"* instead of *"0.50 below replacement."*
  Distinguish *"counts as zero"* from *"is excluded / not counted."* Avoid vague shorthand like
  *"zeroing 44% of players."* Name the measure and its unit each time a figure appears, and say what a
  difference of that size means.

### 2.4 Verified voice habits

- **Oxford comma, always**, in every list of three or more.
- **Cut intensifiers:** remove *"at all"*, *"badly"*, *"genuinely"*, *"deliberately"*, and *"itself"*
  whenever the sentence is true without them.
- **Cut contrastive `"not X"` tags** (*"estimated, not assumed"* becomes *"estimated"*) unless the
  contrast does essential identification work.
- **Semicolon plus connector:** use `"; however,"` and `"; for example,"` to join two closely tied
  clauses. Never use a semicolon to string separate ideas together.
- **Comma-wrap mid-sentence `"therefore"`:** *"is, therefore, aged."*
- **Scope `"each"` properly:** use *"each"* for members of a set treated one at a time, not as a blind
  replacement for *"all"* or plural nouns (*"in all 20 repeats"*, not *"in each of 20 repeats"*).
- **Restart rather than extend:** *"...arrives. This is estimated from..."* over a trailing participle.
- **Keep hedges at their exact strength.** Collapse stacked hedges (*"could potentially possibly"*
  becomes *"may"*), but never upgrade *"may"* to *"does,"* and never remove the last hedge.
- **Heading capitalization:** top-level numbered sections use **Title Case** (`1. Expected Net Present
  Value`); all sub-headings below that use **sentence case** (`The discount rate`). No *"Decision:"*
  headings; name the topic.
- **Inline-header lists:** plain text (not bold), followed by a period (not a colon), carrying
  substantive analytical content.
- **One term per concept.** Never rotate synonyms (for example, *"comparables"* / *"similar players"* /
  *"matches"* / *"the pool"*). Spell out full proper names (*"the Game Value metric"*, *"salary cap
  ceiling"*). Name a model version by its terms (*"linear and squared production"*), never by its shape
  (*"the full curve"*).

### 2.5 Standard AI checklist (always remove)

- **AI vocabulary:** *actually, additionally, crucial, delve, emphasizing, enhance, fostering, interplay,
  intricate, key (adj.), landscape (abstract), pivotal, showcase, tapestry, testament, underscore (verb),
  vibrant.*
- **Copula avoidance:** replace *"serves as"*, *"boasts"*, *"features"* with *"is"*, *"are"*, *"has."*
- **Superficial `-ing` tack-ons:** cut trailing *"...ensuring..."*, *"...highlighting..."*,
  *"...reflecting..."* phrases.
- **Negative parallelisms:** rewrite *"It is not just X; it is Y"* as a direct statement.
- **Filler phrases:** *"in order to"* becomes *"to"*; *"due to the fact that"* becomes *"because"*; *"at
  this point in time"* becomes *"now."*
- **Vague attributions and promotional language:** name the source or cut the claim.
- **Generic closings:** never end with *"Summary:"*, *"In conclusion:"*, or generic positive wrap-ups.

### 2.6 The mechanical check

Two scripts run on every draft. Their output is a list to read, not a score to drive to zero; neither
can see structure.

- **The banned-pattern check.** In the xNPV repository, `python 25_TESTS/doc_check.py FILE` (a .docx or
  a text file; a copy is in this skill's `scripts/`). It lists each hit of the hard bans in 2.3, the
  project vocabulary, first person, contractions, personification, and the AI checklist, with its
  paragraph and context. BAN rules are cleared before a draft is handed over; LOOK rules (a colon, a
  section number, "trend") are read and decided one by one. Both document builders run it on the file
  they write.
- **The clarity linter.** `python scripts/ste-lint.py --disable semicolon draft.md` (adapted from the
  ASD-STE100 skill, MIT, see `scripts/LICENSE-ste-lint`). It flags long sentences, phrasal verbs, nouns
  made from verbs, synonym rotation, and passives. Always disable its semicolon rule, which conflicts
  with 2.4.

---

## Project-Specific Rules (xNPV Thesis)

- **Read the code first.** Describe each mechanism from the script that runs it, not from memory or old
  explainers. Label a column or a date by what the code puts there.
- **Reader-facing documents stand alone.** Never mention the supervisor, meetings, or prior feedback
  rounds.
- **Values.** An asset's value at a valuation date is its expected net present value (xNPV); a drafted
  player's played career is its net present value (NPV), and a prospect's outcome his remaining NPV; one
  season's value less its cost is its net value. Never *"surplus value."* Values are stated as a share of
  the salary cap.
- **Standard terms:** `D0` (draft season), `D+1`, *draft position* (never *"the slot"*), *star value*,
  *star probability*, *NHLe*, *terminal value* (the value of the control seasons), *performance* (never
  *"play"*; a forecast of it is *forecasted performance*), *most recent season* (never *"last"*), and
  *RMSE*, each the same way every time.
- **Hockey sanity check:** verify every number and claim against hockey reality (who reaches the NHL,
  when, and at what age). A figure that looks wrong to Thomas is wrong until shown otherwise.
- **Recount enumerated lists:** verify that *"four decisions"* lists four items. Count before writing
  *"all"*, *"every"*, or *"none."*
- **Simplified walkthroughs drop no step** of the pipeline; discounting is the step that has gone missing
  before.
- **Thomas edits the Word file himself.** When a document is built by a script, carry each of his edits
  into the builder before rebuilding, and keep his commented copy in git.
- **Fewer moving parts.** An added term, parameter, or version is a decision for Thomas, never a side
  effect of a rewrite.
- **A note that comes back twice was answered wrongly in kind.** Change the approach, not the wording;
  offer rewrite options in chat instead of a third guess.

---

## Worked Rewrites

**A. Fixed comparables.** The original:

> The original similarity weights remain fixed as the projection moves forward. At each later age, the
> model uses the subsequent changes observed for those same comparable players. It does not update the
> match using the target player's future performance.

Each sentence is true, and the reader is never told why any of it matters. The rewrite, built from
Thomas's spoken explanation and checked against the code:

> The comparable players and their weights are chosen once, from seasons the player has played. Each
> later year of the projection uses the change those same players made from that age to the next.
> Choosing a new group each year would mean matching historical players to a version of the player that
> the projection invented the year before, so each round would build on the last round's guess. Holding
> the group fixed keeps each step tied to real players at the same age. The cost is that the group thins
> out at older ages; the league-wide average change for the position and age, therefore, carries more of
> the estimate.

**B. A judgement call defended.** The original:

> The broader average receives a fixed weight of ten. The comparable side receives the sum of the
> individual similarity weights.

The rewrite:

> A small or poorly matched group of comparables could produce an extreme estimate on its own. To guard
> against that, the comparables' average is mixed with the league average for the same position and age,
> which counts as ten extra comparables, each an exact match. When the comparables are many and close,
> their weights sum well above ten and they dominate; when they are few or distant, the league average
> takes over. Ten was tested as a judgement call: any value from 0.01 to 20 changes forecast RMSE by less
> than 0.06%.

---

## Process

1. **For a small edit** (a sentence or a paragraph), make the edit with Pass 2 in mind.
2. **For a section or a document:**
   1. Read the code first.
   2. Write the story spine (1.1), and agree three to five take-aways with Thomas.
   3. Draft from the spine, with Pass 2 in mind from the start.
   4. Attach the evidence (1.3).
   5. Run the mechanical check (2.6); clear every BAN hit and decide every LOOK hit.
   6. Read the draft back once and fix what still tags it as AI-written, or as not Thomas's.
   7. Run the final checklist on every sentence, caption, and table.

## Final Pre-Delivery Checklist

- [ ] **Facts match the code** and the records that apply today.
- [ ] **No first person** (*"I"*, *"me"*, *"my"*) and no personification anywhere in academic text.
- [ ] **No forward references** (*"Section X will..."*) or meta-signposting.
- [ ] **No dev-log leakage** (zero script filenames, internal audit dates, or data-hygiene trivia) and no
      earlier versions of the model.
- [ ] **Standard econometric terms used** (*dummy variable*, *interaction term*, *regression*, *RMSE*;
      zero *"held-out error"*).
- [ ] **Hard bans cleared:** zero *"against"* for numerical comparisons, zero *"if he plays"*, zero
      sentences starting with *"And"*, zero em dashes, zero contractions.
- [ ] **The mechanical check is run** and its BAN list is empty.
- [ ] **Full-sentence flow:** every sentence has a clear subject, main verb, and transition; no staccato
      openers or "mic drops."
- [ ] **No copy-paste templates** repeated across consecutive subsections; forced inanimate `'s` cleaned up.
- [ ] **Equations and evidence:** updated equation shown each time a term is added, written in full with
      discounting; one worked number per formula; rejected options labeled rejected before description;
      ties bolded; each p-value says what it tests against.
