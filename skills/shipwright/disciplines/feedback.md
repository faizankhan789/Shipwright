# Receiving review feedback

This covers feedback from humans, PR comments, and reviewer subagents. It is technical input
to evaluate, not an order to obey and not a social moment.

1. **Read all of it** before acting. Items can be related.
2. **Restate** anything unclear and ask about it. Don't implement half-understood items.
3. **Verify each claim against the code.** Is it true here, in this codebase? Run the same triage as `phases/review.md`.
4. **Check that it's needed.** A "proper" generic solution for a case nobody hits fails YAGNI. Say so.
5. **Then act:** one item at a time, test-first, with checks re-run through `SW verify`.

## Responding

- **Correct:** fix it, then say what changed: "Fixed: guard added at `api.ts:42`, test `rejects_empty_id`."
- **Wrong:** push back with evidence: "Disagree: `parse()` already rejects empty input at `parse.ts:18`, covered by `test_empty`."
- **Unclear:** ask one specific question.
- **Never use performative agreement:**
  - "You're absolutely right!"
  - "Great catch!"
  - thanks before you've checked the claim
- **Outside reviewers** (unknown to the project) get the same scrutiny, and must be checked against the project's own decisions in `.shipwright/decisions/`.
