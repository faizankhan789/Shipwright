
# {title}

<!-- Size M plan. Target 900-1600 tokens: below risks ambiguity, above risks context rot.
     Use boundaries and examples, not step-by-step "how". Cross-layer work for ONE goal stays in ONE plan.
     Delete every comment when you fill it. Run `sw.py check <id>` until it passes. -->

<!-- frozen:start -->
## Intent

**Problem:** FILL: what is broken or missing, and why it matters (1-2 sentences)

**Approach:** FILL: the high-level approach, the "what" (1-2 sentences)

**Decisions:** <!-- One line each: the human's answers to Open Questions, and auto-mode rulings marked "(ruling: why)". Delete if none. -->

## Boundaries

**Always:** FILL: invariants this change must keep

**Never:** FILL: out of scope and forbidden approaches

## I/O & Edge-Case Matrix

<!-- Delete this section if there are no meaningful I/O scenarios. Every row must get a test. -->

| Scenario | Input / State | Expected behavior | Error handling |
|---|---|---|---|
| FILL: happy path | | | none |
| FILL: error case | | | |
<!-- frozen:end -->

## Code Map

<!-- From the investigation: paths, symbols, what to reuse, what NOT to touch. Saves the builder from re-searching. -->

- `FILL: path` -- role / relevance

## Tasks

<!-- Ordered by dependency. Each: `path` -- action -- rationale. If a matrix exists, include its test task.
     A task whose output another task uses adds a sub-bullet:  Produces: name(signature) -> type -->

- [ ] `FILL: path` -- action -- rationale

## Acceptance Criteria

<!-- System-level behavior not already in the matrix. Each provable without pointing at code. -->

- Given FILL, when FILL, then FILL

## Design Notes

<!-- Only when non-obvious: rationale and a 5-10 line golden example. Delete otherwise. -->

## Verification

<!-- Commands in backticks are REQUIRED to pass via `sw.py verify` before `verified`.
     UI work: add the impeccable detect / taste inspect commands from disciplines/ui.md.
     Add `- Manual: ...` for what no command can check; it is recorded with --artifact <screenshot>.
     This section is frozen at approval, like the Intent. -->

- `FILL: test command` -- expected: FILL

## Implementation Notes

<!-- Builder-owned, append-only: files touched, surprises, RULING: lines. Never delete. -->

## Plan Change Log

<!-- Append-only. One entry per bad-plan loopback: triggering finding, what was amended,
     the known-bad state avoided, KEEP instructions (what worked and must survive). -->

## Review Triage Log

<!-- Append-only. One row per lens finding, every pass. `pending` rows block `verified`.
     Verdict: high | medium | low | false | maybe-false. Route: patch | bad-plan | intent-gap | defer | reject.
     Add rows with `sw.py triage`. Every lens that ran gets at least one row; a lens with no findings:
     | n | <lens> | - | no findings | false | - | - | -->

| # | Lens | Location | Claim | Verdict | Route | Evidence / action |
|---|---|---|---|---|---|---|
