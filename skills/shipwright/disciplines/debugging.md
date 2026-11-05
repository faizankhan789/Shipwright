# Debugging

**Iron law: no fix without a root cause.** Guess-fixes waste time and add bugs. This applies
most when the fix "seems obvious" or time is short.

For depth, load:
- `library/debugging/systematic-debugging/GUIDE.md`, with its `root-cause-tracing.md` and `find-polluter.sh`
- `library/debugging/focused-fix/GUIDE.md` for failures that span a whole module
- the browser, performance, or Android debugging guides listed in `library/ROUTING.md`

Record each phase in the item log (`SW log <id> "HYPOTHESIS: ..."`). That record is what makes
the investigation auditable and resumable.

## Phase 1: Investigate

1. **Read the whole error:** message, stack trace, line numbers, codes. It often names the fix.
2. **Reproduce it reliably,** with exact steps or a failing test. If you can't reproduce it, gather more data. Don't guess.
3. **Check recent changes:** `git log` and `git diff` since the last known-good point, dependency bumps, config, environment.
4. **Multi-component systems:** instrument each boundary (log what goes in and what comes out), run once, and see which layer breaks.
5. **Trace the bad value backward** to where it first went wrong. Fix it at the source, not where it shows up.

## Phase 2: Compare

- Find similar code that works, in this repo or the library's own examples.
- List every difference between working and broken, however small. Don't assume one "can't matter".

## Phase 3: Hypothesis

- One hypothesis: "X is the root cause because Y." Log it.
- Test it with the smallest possible change, one variable at a time.
- If it's wrong, log that and form a new hypothesis. Don't stack fixes.

## Phase 4: Fix

1. Write a failing test that reproduces the bug, and record it with `SW verify <id> --expect-fail -- <test>`.
   `verified` refuses a bugfix that has no red run and no logged `HYPOTHESIS:`.
2. Make one fix, at the root cause. Then add validation at each layer the bad value crossed, so
   the bug can't come back by another path (`library/debugging/systematic-debugging/defense-in-depth.md`).
3. The test passes, and nothing else broke: run it through `SW verify`.

## Three strikes

If three fixes have failed, or each fix reveals a new problem somewhere else, the design is
probably wrong. Stop fixing.
- Log `SURPRISE:`, and tell the human what you've learned.
- In auto mode: `SW mark <id> blocked --reason "..."`.

| Thought | Reality |
|---|---|
| "Quick fix now, investigate later" | Later never comes. The first fix sets the pattern. |
| "Several changes at once will save time" | Then you can't tell which one worked. |
| "It's probably X" | Seeing the symptom isn't understanding the cause. Trace it. |
