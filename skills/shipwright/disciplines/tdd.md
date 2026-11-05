# Test-first

**Iron law: no production code without a failing test first.**

If you wrote code before its test, delete it and start from the test.
- Don't keep it as a "reference".
- Don't adapt it while writing the test.

## The cycle

1. **Red:** write one small test for one behavior. Run it.
   - It must **fail**, and fail for the expected reason: the missing behavior, not a typo or import error.
   - A test that passes immediately proves nothing. Fix the test.
   - **Red for the wrong reason doesn't count.** These fail before your behavior is ever reached:
     - an `ImportError`, `NameError` or "module not found" for a function that doesn't exist yet
     - a syntax error
     - a CLI exiting on an unknown flag

     First add the smallest stub (the function returning nothing, the flag accepted but ignored)
     so the test reaches your assertion, then watch the **assertion** fail. The same goes for
     tests that pass before you implement anything: for example, "rejects `--top 0`" passing
     because the flag doesn't exist yet proves nothing. Re-check them once the stub exists.
   - Record the real red run with `SW verify <id> --expect-fail -- <test command>`. It refuses
     to count a test that already passes.
2. **Green:** write the simplest code that passes. Run the test, and the nearby tests too.
3. **Refactor:** remove duplication, improve names. Keep it green; add no behavior.
4. Repeat for the next behavior.

## Good tests

- **One behavior per test.** The name says the behavior: `rejects_expired_token`, not `test_auth_2`.
- **Test through the public surface.** Mock only true boundaries: network, clock, randomness, paid APIs.
- **Assert the outcome,** not the implementation. These don't count as assertions:
  - success / no-throw checks
  - snapshots alone
  - "mock was called"
- **Cover the I/O matrix rows** and the error paths, not just the happy path.
- **Test at the outermost surface the user named.** "The CLI prints X" needs a test that runs
  the CLI. A helper-only test is a proxy, not proof.
- **Run new tests twice.** A result that flips means a race or shared state. Fix the cause;
  never add retries, sleeps, or `@flaky`.

## When a test is truly impossible

Examples: pure styling, a third-party UI you can't drive, infrastructure config. Say so in the
plan's Verification section and name the check that replaces the test, such as a screenshot
review, a dry run, or a schema validation. Never skip a test silently.

## Never

- Weaken, skip, or delete a test to make it pass. A wrong test is fixed in its own step, with the reason written in Implementation Notes.
- Edit an expected value to match what the code produces without first proving the code is right.

| Excuse | Reality |
|---|---|
| "Too simple to test" | Simple code breaks too. The test takes 30 seconds. |
| "I'll test after" | Tests written after are shaped by the code and miss what it should do. |
| "I already checked it by hand" | Manual checks don't re-run. The test does. |
| "TDD slows me down" | Debugging untested code is slower. |
