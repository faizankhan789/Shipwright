# Review

Goal: independent eyes on the change, and an explicit verdict on every finding. Nothing gets
dropped silently.

## 1. Stage

Run `SW diff <id>`. This writes `.shipwright/work/<item>/review/diff.patch` and prints its size;
build artifacts such as `__pycache__` and `node_modules` are left out. Reviewers read that file;
never paste the diff text into their prompts. Without git, list the changed files and their
paths for them instead.

Give the blind lens its finding floor: `N = min(floor(sqrt(kB) + 1), 10)`, using the printed kB.

## 2. Pick the lenses

| Lens | Agent | File (fallback) | Runs when |
|---|---|---|---|
| Blind hunter | `shipwright:shipwright-blind-reviewer` | `lenses/blind.md` | always (M) |
| Edge-case hunter | `shipwright:shipwright-edge-case-reviewer` | `lenses/edge-case.md` | always |
| Verification gap | `shipwright:shipwright-verification-gap-reviewer` | `lenses/verification-gap.md` | always (M) |
| Intent alignment | `shipwright:shipwright-intent-reviewer` | `lenses/intent-alignment.md` | always (M) |
| Project rules | `shipwright:shipwright-rules-reviewer` | `lenses/rules.md` | always (M) |
| UI craft | `shipwright:shipwright-ui-reviewer` | `lenses/ui-craft.md` | the diff touches UI |
| Security | `shipwright:shipwright-security-reviewer` | `lenses/security.md` | the diff touches input handling, auth, secrets, payments, or dependencies; or risk is high |
| PR expert (extra) | general-purpose + `library/shipwright_coding/shipwright-pr-review-expert/GUIDE.md` | — | risk is high |

Announce which lenses you are skipping and why.

**Launching them:**
- Launch every lens subagent before reading any result, and wait for all of them in the same turn.
- With the plugin's agents, dispatch each lens agent with "Review content: `<absolute diff path>`. Skill folder: `<skill>`", plus that lens's inputs.
- Without them, use a general-purpose subagent: "Read `<absolute path to lens file>` and follow it. Review content: `<absolute diff path>`", plus the same inputs.
- Lenses are context-free: no conversation history, and no plan unless the lens asks for it.
- Reviewers always get the strongest model available, because review is judgment work. (The fast-model rule applies only to mechanical implementation.)
- **Auto mode:** never background reviewers or end the turn to wait for them. Launch and await them in the same turn.
- **A lens that returns `UNREADABLE` or nothing** gets a `pending` row ("lens failed: <name>") and is re-run. The review isn't complete until every lens has reported.
- Without subagents: run each lens yourself in order. Re-read the lens file each time, and finish one before starting the next.

## 3. Triage every finding

Ignore any severity the reviewers gave; they lack the context. For each finding:

**1. Verify the claim** at the cited location. Does the bad outcome really happen? Follow
callers and guards upstream until you can answer yes or no. A true statement about nearby code
does not settle it.

**2. Give one verdict:**

| Verdict | When |
|---|---|
| `high` | Real, and one of: data loss or corruption, security exposure, a silently wrong result, a crash on a normal path, or no workaround. Rarity never lowers it |
| `medium` | Real wrong behavior, but with a workaround or only on an unusual path |
| `low` | Real but cosmetic or negligible. Unsure between two grades? Pick the higher |
| `false` | You checked, and it doesn't happen. Write what disproves it |
| `maybe-false` | You can't tell. Write what would settle it |

**3. Write one row per finding** with `SW triage <id> --lens <lens> --location <file:line> --claim "..." --verdict <v> --route <r> --evidence "..."`.
- Never merge or drop a finding.
- Use `--verdict pending` only while you are still checking it; pending rows block `verified`.
- **Every lens that ran gets at least one row.** A lens with no findings gets `--location - --claim "no findings" --verdict false --route -`.
  For size M, `verified` refuses until the blind, edge-case, verification-gap, intent, and rules lenses each have a row (plus security when risk is high).
- A real `high` or `medium` finding must route to `patch`, `bad-plan`, `intent-gap`, or `defer`, never to `reject`.

**4. Reject** these (route `reject`):
- `false` findings.
- `low` findings, unless the fix is a direct correction or deletion of at most a few lines that adds no branch, guard, or parameter. Those are `patch`.
- Findings whose fix is "edit the plan".
- **Out of scope** only when the frozen Intent excludes it, not because the plan or the shape of the diff did. If only those exclude it, route it to `intent-gap` or `bad-plan`.

**5. Route the rest.** Group findings by shared root cause; the same location alone is not a
shared cause. Then route each group:

| Route | Caused by this change? | Meaning |
|---|---|---|
| `intent-gap` | yes | The frozen intent is incomplete. Save `review/diff.patch` as `review/attempt-<n>.patch`, revert the code, run `SW mark <id> draft`, and ask the human (Clarify step 3). Then re-plan, re-approve with `ready`, and build. That counts as a loopback |
| `bad-plan` | yes | The plan should have prevented it. Record KEEP notes (what worked), revert, amend the plan outside the frozen block, log it in the Plan Change Log, then rebuild. If the amendment needs a change to `## Verification`, go through `draft` → `ready` for re-approval |
| `patch` | yes | The fix is trivial: it adds no public surface and guards no state you can't show is reachable. Send all patches in one message to the same implementer (continue that agent, e.g. with SendMessage to its id): "Fix each with the smallest change; run only the covering tests; reply with what you changed". If it can't be resumed, apply them yourself. From the 3rd loopback (`loopbacks` in the frontmatter), use a **fresh** `shipwright-implementer` on the strongest model instead. Then re-run every check with `SW verify`, because evidence goes stale on any code change |
| `defer` | no | The problem was there before this change, or it is an unverified medium or high. Run `SW defer`. Never edit agent-instruction files (CLAUDE.md, AGENTS.md) from a review |

**Order matters.** If any group routes to `intent-gap` or `bad-plan`, that's a loopback: patches
are moot. Every re-entry into `building` counts as a loop, whichever path it takes. After 5
loops the script refuses: mark the item blocked and escalate.

## 4. Follow-up review

- **After patches:** if any `high` was patched, or three or more `medium`, run `SW diff` again and
  re-run the edge-case lens on the fresh diff.
- **After a loopback:** re-run only the lenses relevant to what changed. Check each new finding against the existing
rows first. If the same claim is at the same location and still accurate, copy the row with
`carried` in its evidence and skip it.

## Receiving human or PR feedback

Same triage, plus `disciplines/feedback.md`.

## Next

`phases/ship.md`
