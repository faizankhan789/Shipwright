# Frame (size L)

Goal: turn a big idea into an ordered set of size-M slices that each ship on their own, with
the cross-cutting decisions made once.

## 0. Copying or beating an existing product?

If the goal is "like X" or "better than X":
1. Run `library/shipwright_product/shipwright-build-from-best/GUIDE.md` Phases 1–2 (research the best existing
   products, then write the spec) and feed the result into the brief.
2. Put its Phase 5 gate commands into the matching slices' `## Verification`.

Shipwright keeps the process; build-from-best supplies the research and the gates.

## 1. Brief

First, play back your understanding in chunks of about 250 words: what it's for and who it
serves, then the core flows. After each chunk, ask what's wrong or missing.

Then run `SW initiative "<title>"` and fill in `brief.md`. Number the in-scope requirements
`R1`, `R2`, and so on. Cover:
- problem
- users and the moment they need this
- success measures
- in / out / anti-goals
- constraints
- risks

Use the human's own words, and mark your own guesses `(guess)`.

Run a builder check on the brief: a fresh subagent with
`library/shipwright_coding/shipwright-brainstorming/builder-check-prompt.md`. Clear the Open Questions with the human
as in `phases/clarify.md` step 3.

Existing codebase: investigate first. The brief describes the change, not the whole system.

## 2. Council, then architecture

Convene the council (`phases/council.md`) on the hard-to-reverse decisions:
- the shape of the system
- the data store and model
- the auth model
- the AI pattern
- build vs buy

Its `decision.md` is the source for this step.

Fill in `architecture.md` with only the decisions that keep separately built slices consistent:
- the shape of the system
- the data model
- contracts between parts
- cross-cutting rules (errors, config, auth, testing levels, performance and accessibility floors)

For each significant choice, run `SW adr "<title>"` and fill the ADR.

**Picking a stack:**
- Prefer boring, managed, well-documented tools.
- In an existing project, reuse what is already there.
- State a default in one line; the human can override it.

## 3. Slice

**Vertical slices**, each a size-M work item with one user-facing goal:
- Slice 1 is a **walking skeleton**: the thinnest end-to-end path. It proves the architecture.
- Order by dependency, then by risk: retire the scariest unknown early.
- Each slice must be shippable, testable, and reviewable without the next one.

Create each slice:

```
SW new "<title>" --size M --initiative <slug> --after <ids>
```

List the slices in the `## Slices` section of `architecture.md`, each with
`covers: R<n>, ...`. Every requirement must be covered by some slice.

## Checkpoint (interactive)

Present:
- the brief in 5 lines
- the key architecture decisions
- the slice list with dependencies

Ask the human to approve, or to change anything.

In auto mode: proceed, logging a `RULING:` in the first slice's log.

## Next

`SW next`, then run that slice through `phases/plan.md`.

When every slice is `done`, run the initiative retro in `phases/ship.md` (Learn).
