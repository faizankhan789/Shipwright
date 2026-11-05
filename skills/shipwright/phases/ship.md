# Verify, ship, learn

## 1. Verify

Read `disciplines/verification.md`, then:

1. Re-run every Verification command fresh with `SW verify <id> -- <command>`. Earlier runs are stale after any patch.
2. UI changes: run the UI checks from `disciplines/ui.md`. The screenshot check is recorded with
   `SW verify <id> --manual "what you saw" --artifact <screenshot>`; the artifact file is required.
3. Run `SW mark <id> verified`. If it refuses, the gate lists what is missing. Fix that; never route around it.
   Any code change after `verified` makes the evidence stale, and `done` re-runs the same gates.
4. **Deploying?** If the human asks to ship to an environment, first run the ship gate:
   `SW verify <id> -- python3 <skill>/library/coding/ship-gate/scripts/ship_gate_scanner.py --no-interactive .`

## 2. Present (interactive)

Keep it short and lead with the outcome:
- **What changed:** for the user-visible behavior, two or three lines.
- **Evidence:** each check and its result, from `evidence.jsonl` / the log.
- **Review:** verdict counts, what was patched, and what was deferred (with the path).
- **Risks and follow-ups:** anything the human should look at first.
- **Where to look:** the plan path and the key files, as clickable paths.

The human accepts → `SW mark <id> done`.

The human wants changes → treat them as review feedback (`phases/review.md`, with `disciplines/feedback.md`).

**Commits:**
- Commit only if the human asks, or if the project's instructions say to.
- Never push unless asked.

**Auto mode:** mark `done` after `verified`, then `SW next`.

**Deploys (DORA):**
- When the work reaches production, record it: `SW deploy --items <ids> [--ref <sha>]`.
- If a deploy causes a production failure: `SW deploy-failed <D-id> --reason "..."`.
- Create the fix as a bugfix item, linked with `SW set <fix> fixes=<id>`.
- Once service is restored: `SW deploy-recovered <D-id>`.

`SW metrics` reports the five DORA metrics: deployment frequency, change lead time, change failure
rate, recovery time, and rework rate.

## 3. Learn (every item; takes about two minutes)

**`.shipwright/context.md`** — anything that cost time and will again:
- a command you had to discover
- a pitfall, written as "symptom → cause → what to do"
- a convention

Delete lines that are no longer true. Keep the file under 80 lines.

**Decisions:** a choice gets `SW adr "<title>"`, plus a one-liner under `## Decisions` in context.md, only when all three hold:
- it is hard to reverse,
- it would surprise a newcomer,
- it was a real trade-off.

Everything else stays in the plan.

**Delivery health:** in the initiative retro, or monthly, run `SW metrics --days 30` and compare with
the last period. A rising change-failure or rework rate means the gates aren't biting: read the
triage logs and `SW friction` to find out why.

**Skill friction:** anything in this workflow that slowed you down or misled you goes in `SW log <id> "FRICTION: ..."`. `SW friction` collects these lines from every item, so the skill can be improved later.

## Initiative review and retro (all slices of an L are done)

Per-slice review can't see defects at the seams between slices, so review the whole initiative once:

1. **Integration diff:** `SW diff --initiative <slug>` covers everything since the earliest slice's baseline.
   - Run the blind, edge-case, and intent lenses on it, with the brief's Problem and Scope as the intent.
   - Look for duplication between slices and for contracts that drifted from `architecture.md`.
2. **End-to-end:** run the brief's main user flows through the real surface (UI, API, or CLI).
   Save the output or screenshots in the initiative folder.
3. **Coverage:** every requirement `R<n>` in the brief must be covered by a `done` slice
   (`covers:` in the Slices list) and backed by evidence.
4. **Verdict:**
   - **Accepted:** every slice is done, every R is covered, and the end-to-end flows pass.
   - **Rejected:** anything else. Name what is missing, and create slices for it.

Then read every slice's plan (the Triage Log, Plan Change Log, and Implementation Notes) and its
log, and write `retro.md` in the initiative folder:

- **What shipped against the brief's success measures.**
- **Patterns in the findings:** repeated bad-plan loopbacks mean planning missed something, so name it.
- **Deferred work** worth scheduling.
- **Proposed** ADRs and context.md updates. Apply them only with the human's approval.
