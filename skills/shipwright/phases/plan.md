# Plan

Goal: a plan a builder with no other context can execute without asking anything.

## 1. Create and fill

1. The item already exists: it was created in Clarify, or in Frame for an initiative slice.
   - If it has `after` dependencies, read those plans first; `SW next` prints their paths.
   - Reuse their Code Map and Design Notes, and respect their Plan Change Log constraints.
2. Fill in its plan template. Delete every comment and every optional section you don't need.
   - **Intent** (frozen): problem, approach, the human's decisions.
   - **Boundaries** (frozen): Always and Never.
   - **I/O & Edge-Case Matrix** (frozen): every row will need a test.
   - **Code Map:** the investigation, so nobody re-searches.
   - **Tasks:** each one is `` `path` -- action -- rationale ``, ordered by dependency.
   - **Acceptance Criteria:** Given / When / Then, each provable without pointing at code.
   - **Verification:** the exact commands. These become required gates.

## 2. Ready-to-Build standard

| Property | Meaning |
|---|---|
| Actionable | Every task has a file path and a specific action |
| Ordered | Tasks follow dependencies |
| Testable | Each acceptance criterion and matrix row maps to a check that can fail |
| Outermost surface | Each AC is tested where the user meets it (CLI, API, UI), not only through an internal helper |
| Interfaces | A task that produces something another task uses names it, as `Produces: name(signature) -> type`. Names match across tasks |
| Verification complete | `## Verification` lists every command that proves the ACs, including the UI checks from `disciplines/ui.md`. After approval it is frozen |
| Complete | No placeholders, TBD, or "handle appropriately" |
| Coherent | No contradictions; one reading per sentence |
| Sized | M: 900–1600 tokens. Above that, offer to split; log deferred goals with `SW defer` |

Run `SW check <id>` and fix it until it passes. If something is missing:
- the repo can answer it: go look;
- only the human can answer it: add `## Open Questions` and go back to Clarify.

## 3. Self-review and builder check

Re-read the plan as the builder would, and ask:
- Could I build this without asking?
- Is any task secretly two goals?
- Does every matrix row have a test task?
- Do the interface names match across tasks?

Fix whatever you find.

**Builder check (M with risk medium or high):** dispatch a fresh subagent with no conversation
context, using `library/coding/brainstorming/builder-check-prompt.md` on the plan. Sort its
questions:
- **Already answered** by the conversation or the code: write the answer into the plan.
- **Minor:** settle it yourself and mark it `(ruling: why)`.
- **Theirs:** only the human can answer. It goes to `## Open Questions`.

**More than one credible approach, and risk high:** before writing Tasks, run the reduced
council (architect, staff engineer, red team; `phases/council.md`) on the approach. Its decision
goes into the Intent's `**Decisions:**` and the Design Notes.

**Pre-mortem (risk high):** ask a fresh subagent: "It is three months later, and this change
caused an incident. What happened?" Fold the real risks into Boundaries and the I/O matrix.

## Checkpoint (interactive; M only)

Present:
- the plan path
- a five-line summary
- the risk and why
- the size or token warning, if any

Then give the human these choices:
- **Approve and build**
- **Approve and stop:** leave it `ready` for a fresh session.
- **Revise:** discuss. Optionally have a subagent critique the plan first.

On approval:
1. Re-read the plan from disk, since the human may have edited it.
2. Run `SW mark <id> ready --approved-by "<the human's name>"`. This freezes the Intent, ACs, size, type and
   Verification by hash; any later edit fails `check` and blocks `verified`. In auto mode, use
   `--approved-by auto-ruling` and log the RULING.

For size S: no checkpoint. Run `SW mark <id> ready` once `check` passes.

## Next

`phases/build.md`
