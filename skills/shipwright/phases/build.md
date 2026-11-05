# Build

Goal: the plan, implemented test-first with the smallest diff that does the job.

## Start

1. **Clean tree.** Commit or stash unrelated work first: `SW mark <id> building` refuses a
   dirty tree, because those changes would be reviewed and blamed on this item. Use
   `--allow-dirty --reason "..."` only when the human says so.
2. **Start.** `SW mark <id> building` records the git baseline and starts the evidence clock.
   Evidence counts only if it was recorded after this, against the current code.
3. **Baseline run.** Before the first edit, run each Verification command once through
   `SW verify`. Note any pre-existing failures in `## Implementation Notes`, so they are
   neither blamed on this item nor fixed silently.

Read `disciplines/tdd.md` now.

## Implement

**With subagents (M):**
- Dispatch `shipwright:sw-implementer` with "Plan: `<abs plan path>`. Skill folder: `<skill>`".
  The plan is its only source of truth; do not paste extra context.
- UI tasks go to `shipwright:sw-ui-designer` instead, or to both in sequence when a plan mixes UI and logic.
- Without the plugin's agents, use a general-purpose subagent with `templates/implementer-prompt.md`.
- Keep it addressable, because review fixes go back to the same implementer.

**Without subagents, or size S:** implement it yourself, task by task.

**For every task:**
1. **Red.** Write the test for the behavior. Record its failure with
   `SW verify <id> --expect-fail -- <test command>`, and check it fails for the right reason.
   `verified` refuses a feature or bugfix with no red run.
2. **Green.** Write the minimum code that passes it.
3. **Refactor.** Clean up with the tests still green.
4. Tick the task in the plan. Append files touched and surprises to `## Implementation Notes`.

## Rules while building

- **Surgical diffs.** Every changed line traces to a task. Don't reformat, rename, or "improve" neighboring code.
- **Unrelated problems:** note them in Implementation Notes, or run `SW defer`. Don't fix them.
- **Frozen sections are read-only:** the frozen block, `## Verification`, size, and type. `sw.py` hashes them at approval.
  - Plan wrong outside the frozen block: amend it and add a `## Plan Change Log` entry.
  - The intent itself is wrong: stop, then follow `phases/clarify.md` step 3.
- **A check fails unexpectedly:** read `disciplines/debugging.md`. No guess-fixes.
- **The UI changes:** follow `disciplines/ui.md` for this task.
- **A judgment call** comes up: log it as `RULING:` (auto mode) or `DECISION:` (agreed with the human).

## Implementer status handling

| Status | Action |
|---|---|
| DONE | Continue to the audit below |
| DONE_WITH_CONCERNS | Read the concerns. If they touch correctness or scope, resolve them before the audit |
| NEEDS_CONTEXT | Answer from the plan or the code. If the plan lacked it, fix the plan and log it in the change log |
| BLOCKED | Find the cause. If the plan is wrong, amend it. If it's an intent gap, go to Clarify. If the task is too big, split it |

## Audit before review

1. Read the actual diff (`SW diff <id>`), not just the implementer's report.
2. Run every Verification command through `SW verify <id> -- <command>`. A failing command is unfinished work.
3. **Matrix audit:** every I/O matrix row has a test that ran and passed. A skipped, filtered, or unregistered test counts as missing.
4. If a test disagrees with the matrix, fix the code, not the expectation. If the row itself is ambiguous, ask the human.

## Next

- Size M: `SW mark <id> reviewing`, then `phases/review.md`.
- Size S: run the edge-case lens yourself (`lenses/edge-case.md`) on the diff and fix what's real, then `phases/ship.md`.
- Size S, if the self-review finds something worth recording: `SW mark <id> reviewing` and log the findings in a `## Review Triage Log` table like the M template.
