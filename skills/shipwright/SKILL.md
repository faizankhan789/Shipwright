---
name: shipwright
description: Use when the user hands over a feature, bug fix, refactor, tests to write, migration, or whole product to build and expects working, verified code; when asked to analyze a problem, design or architect a solution, or plan a system before coding; when resuming earlier build work; when asked to plan, slice, or review a change; when asked to create or edit a Word, PDF, PowerPoint or Excel file or a codebase explainer video; or when the user says "shipwright". Not for questions, explanations, or dictated edits.
---

# Shipwright

Turn intent into verified, reviewed code. Plans, decisions, and evidence live on disk, and a script enforces the gates.

**Violating the letter of a rule is violating its spirit.**

## The five laws

1. **No build before intent is clear.** Investigate first; ask only what the code cannot answer. Open Questions must be empty before building.
2. **No production code without a failing test first** — wherever a test can run. Otherwise, name the check that replaces it in the plan.
3. **No fix without a root cause.** Bugs go through `disciplines/debugging.md` before any plan.
4. **No "done" without fresh evidence.** Only `shipwright.py verify` records evidence; `shipwright.py mark ... verified` refuses without it.
5. **Write state as you go.** Decisions, rulings, and surprises go to disk the moment they happen, not at the end.

## Tooling

`SW` below is shorthand, not a shell variable. Always type the full command,
`python3 <absolute path of this skill's folder>/scripts/shipwright.py` (Windows: `python` or `py`). Run `SW <command> -h` for flags.

| Need | Command |
|---|---|
| Orient at session start | `SW resume` (if no `.shipwright/`: `SW init` at the project root) |
| Create work | `SW new "<title>" --size S\|M [--type bugfix] [--risk high] [--after 001,002] [--initiative slug]` |
| Set fields | `SW set <id> risk=high` (also `after`, `initiative`; `size`/`type`/`title` only while draft) |
| Large effort | `SW initiative "<title>"` (brief + architecture) · `SW initiative-check <slug>` |
| Lint a plan | `SW check <id>` |
| Change status | `SW mark <id> <status> [--reason "..."] [--allow-dirty]` — draft → ready → building → reviewing → verified → done |
| Record evidence | `SW verify <id> -- <command>` · red run: `SW verify <id> --expect-fail -- <test>` · manual: `SW verify <id> --manual "..." --artifact <file>` |
| Diff for reviewers | `SW diff <id>` · whole initiative: `SW diff --initiative <slug>` |
| Log a review finding | `SW triage <id> --lens L --location F:N --claim "..." --verdict V --route R --evidence "..."` |
| Log a line | `SW log <id> "DECISION: ..."` (also `RULING:`, `HYPOTHESIS:`, `SURPRISE:`) |
| Pick library guides | `SW route "<task>" --id <id>` (deterministic; logs `GUIDE:` lines; UI work must have one before `verified`) |
| Expert council | `SW council new "<question>"` · `SW council check <n> [--brief]` |
| Record a decision | `SW adr "<title>"` |
| Defer work | `SW defer "<summary>" --source <id> --evidence "..."` (both flags required) |
| Collect skill friction | `SW friction` |
| DORA metrics | `SW deploy --items 001,002` · `SW deploy-failed D1` · `SW deploy-recovered D1` · `SW metrics [--days 30]` |

Without Python, follow the same files by hand and say the gates are unenforced.

## Step 0: Orient

Run `SW resume`. Read `.shipwright/context.md`.
- If its `## Commands` are empty, fill in test, lint, and build now, from the repo's config.
- If an item is open, continue it from its status (the output names the phase file).
- Otherwise, size the new request.

## Size the work

| Size | Signals | Path |
|---|---|---|
| **S** | Intent clear; about ≤100 changed lines, ≤3 files; no new dependency, schema, or public API | clarify-lite → build (TDD) → self-review → verify → ship |
| **M** | One user-facing goal, even across layers | clarify → plan → **approval** → build → review (lenses) → verify → ship |
| **L** | Two or more independently shippable goals, or a new product | frame (brief, **council**, architecture, slices) → **approval** → each slice runs as M |
| **Doc** | The deliverable is a file (Word, PDF, PowerPoint, Excel) or an explainer video, not software | Skip Step 0 and plans. Follow the matching `library/shipwright_documents/` guide, run its own checks (validate, recalc, render) and show their output before claiming done |
| **D** (design only) | The user wants a problem analyzed, a solution designed or architected, or a technical plan, but no code yet | clarify → **council** → solution design (`decision.md`) → **approval**. Build only when asked; it then continues as L or M |

- Bugs: debugging Phase 1 first.
- State the size and why in one line. The human can override it.
- If work grows, stop, say so, and move up a size. Never move down silently.
- Split rule: split only for top-level goals that could each merge as a separate PR. Never split "validate and show errors".

## Phases

Read each file on entering its phase.

| Phase | File | Exit gate |
|---|---|---|
| Clarify | `phases/clarify.md` | Open Questions empty; risk scored |
| Frame (L only) | `phases/frame.md` | brief + architecture approved; slices created |
| Council (L, D, high-stakes M) | `phases/council.md` | `SW council check` passes; decision approved |
| Plan | `phases/plan.md` | `SW check` passes; human approves → `SW mark <id> ready` |
| Build | `phases/build.md` | all tasks done test-first; checks run via `SW verify` |
| Review | `phases/review.md` | every finding has a verdict row; no `pending` |
| Verify + ship + learn | `phases/ship.md` | `SW mark <id> verified` passes; human accepts → `done` |

Disciplines, loaded when they apply: `disciplines/tdd.md` (every build), `disciplines/debugging.md`
(any bug or unexpected failure), `disciplines/verification.md` (before any success claim),
`disciplines/feedback.md` (when receiving review), `disciplines/ui.md` (any UI change).

## Library (bundled specialist guides)

`library/` holds 173 bundled guides in 11 categories: ui, coding, debugging, testing, security,
mobile, backend-infra, ai-ml, integrations, product, and documents. Choose by context: read `library/INDEX.md` (section map, then one line per
guide), take `SW route "<task>"` as a hint, and log your pick with `SW route --use <section/guide> --id <id>`.
`library/ROUTING.md` has the precedence rules.

## What the script enforces

`shipwright.py` refuses the status change until these hold:
- **`ready`:** a named approver (M); no placeholders or Open Questions; Given/When/Then ACs; file paths on tasks; a Verification check; a risk score. Intent, ACs, size, type and Verification are then hashed.
- **`building`:** current approval, clean git tree; every re-entry counts toward the 5-loop cap.
- **`verified`:** passing runs of every planned check against the current code; a red run (feature/bugfix); a `HYPOTHESIS:` (bugfix); manual-check artifacts; a design guide, a passing design check and a screenshot for UI changes; complete triage (M).
- **`done`:** the same gates, re-checked.

## Modes

- **Interactive (default):** halt at the two checkpoints, plan approval and acceptance. Ask everything in one numbered message.
- **Auto** (the user says "auto", "unattended", or "don't ask me"):
  - Never background subagents or end the turn to wait. Launch and await them in the same turn.
  - No checkpoints. Make rulings instead of stalling: log `RULING: <choice> because <reason>` and continue.
  - Exception: an intent gap that changes user-visible behavior. Mark the item `blocked --reason "..."` and move to the next actionable item (`SW next`).

## Working with other skills

- Shipwright owns the workflow: no other process skills in parallel. Unrelated domain skills are fine inside a phase.

## Internal agents

The Shipwright plugin ships these agents. Dispatch them by subagent type, and every prompt
gives absolute paths: the plan or diff, and `Skill folder: <this skill's folder>`.

| Agent (subagent type) | Phase | Give it |
|---|---|---|
| `shipwright:shipwright-investigator` | Clarify | the questions to answer |
| `shipwright:shipwright-principal-architect`, `shipwright:shipwright-ai-engineer`, `shipwright:shipwright-staff-engineer`, `shipwright:shipwright-design-lead`, `shipwright:shipwright-red-team`, `shipwright:shipwright-council-judge` | Council | the round number and the council folder (they debate in 3 rounds; `phases/council.md`) |
| `shipwright:shipwright-implementer` | Build | the plan path |
| `shipwright:shipwright-ui-designer` | Build (UI tasks) | the plan path, plus which tasks are UI |
| `shipwright:shipwright-debugger` | Any bug or unexpected failure | the symptom, the repro steps, and the item id for `HYPOTHESIS:` logging |
| `shipwright:shipwright-blind-reviewer` | Review | the diff path, and the finding floor N |
| `shipwright:shipwright-edge-case-reviewer` | Review | the diff path, and the plan as `claims_file` |
| `shipwright:shipwright-verification-gap-reviewer` | Review | the diff path |
| `shipwright:shipwright-intent-reviewer` | Review | the verbatim Intent block, and the diff path |
| `shipwright:shipwright-rules-reviewer` | Review | the diff path, and the project root |
| `shipwright:shipwright-ui-reviewer` | Review (UI diffs) | the diff path, and screenshot paths |
| `shipwright:shipwright-security-reviewer` | Review (trust boundaries touched, or high risk) | the diff path |

**If the agents aren't available,** dispatch a general-purpose subagent with: "Read `<skill>/lenses/<lens>.md` (or
`templates/implementer-prompt.md`) and follow it", plus the same inputs. Without any subagents,
do the work yourself, sequentially, reading each lens file fresh.

**Model choice:** the agents set their own models; for mechanical plans you may pass a faster one.

## Red flags: stop, you are rationalizing

| Thought | Reality |
|---|---|
| "Too small to plan" | S still gets intent, a failing test, and evidence. It takes minutes. |
| "I'll write the tests after" | Tests written after pass immediately and prove nothing. Delete the code and start test-first. |
| "Probably X, let me just fix it" | That is a guess, not a root cause. Go to debugging Phase 1. |
| "Should work now" / "looks good" | That is not evidence. Run it through `SW verify`. |
| "The subagent said it passed" | A report is not evidence. Re-run checks. |
| "I'll tweak the approved intent slightly" | It is frozen. Ask the human; `SW check` will catch the edit. |
| "Reviewer is wrong, skip it" | Write a `false` verdict with disproving evidence. |
| "Another fix attempt will do it" (3rd time) | Stop. Question the design and escalate. |
