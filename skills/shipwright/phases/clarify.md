# Clarify

Goal: understand what the human actually wants and what the code already does, with the fewest
possible questions.

## 0. Open the item

Run `SW new "<title>" --size S|M [--type bugfix]` now, with your best-guess size. You can change
it with `SW set <id> size=M` while the item is still a draft. Having the id from the start
lets you log hypotheses, rulings, and blocks.

Size L: create the initiative in `phases/frame.md` instead.

## 1. Investigate before asking

- Read the request, the ticket or brief if there is one, and `.shipwright/context.md`.
- Search the code. Send broad searches to subagents (`shipwright:shipwright-investigator`, several in
  parallel for separate questions) and have them return short summaries:
  - the files and symbols involved
  - what to reuse
  - what must not change
  - existing tests that cover the area
- Give investigators **factual** questions: "how does X work today?", "where is it called?",
  "what tests cover it?". Never hand them the intent or a proposed design. They report what
  is, not what should be. Mark the claims your plan will rest on, and re-check those yourself.
- Do not ask the human anything during this step. Keep looking until the repo and its history
  have nothing more to say.
- Bug reports: run `disciplines/debugging.md` Phase 1 now, or dispatch `shipwright:shipwright-debugger`.
  Reproduce the bug before planning a fix.

## 2. List what is still unknown

An **intent gap** is a choice only the human can make, where the answer changes what gets built.
Everything else, settle yourself from the code and conventions, and note it as your call.

For each intent gap, write an Open Question:

```
1. <the choice in one line>
   a) <option> -- means <consequence>
   b) <option> -- means <consequence>
   Recommended: <letter>, because <reason>
```

Never write a guess into the Intent as if it were decided.

## 3. Ask once

- **Interactive:** send all Open Questions in one numbered message and wait. Answers become
  `**Decisions:**` lines in the Intent. A new gap exposed by an answer gets asked the same way.
- **Auto:**
  - If one reading is clearly most defensible, take it and log `RULING:`. Also write it into the
    plan's frozen `**Decisions:**` as `<choice> (ruling: <reason>)`, so reviewers judge against it
    and the human can overturn it later.
  - If the gap changes user-visible behavior, `SW mark <id> blocked --reason "<question>"`.

## 4. Score risk

Run `SW set <id> risk=low|medium|high`: the business impact if this change is wrong. `ready`
refuses an item without a risk score. Examples of high: money, auth, data loss, migrations, public APIs. High risk
means the thorough review, always.

## Analyzing the problem (L and D, or whenever the request is fuzzy)

Before solutions, write down:
- **Who hurts, when, and how badly.** What does doing nothing cost?
- **The job to be done.** What does success look like to the user, measured how?
- **Constraints and non-goals.**
- **Root cause vs symptom.** Ask "why" until the answer is something you can change.
- **Problem type:**
  - *clear*: apply the known pattern
  - *complicated*: analyze, ask experts (the council)
  - *complex*: probe with a cheap experiment or spike first
- **Three or more quality scenarios** (performance, availability, security, cost, usability):
  concrete and measurable. These feed the council brief and the plan.

## Next

- Size S: write the S plan (`phases/plan.md`, short form).
- Size M: `phases/plan.md`.
- Size L: `phases/frame.md`.
- Size D (design only): `phases/council.md`, then present `decision.md`.
