# Verification before any success claim

**Iron law: no claim of done, fixed, passing, or working without fresh evidence from this
session.**

## The gate

Before you say or imply success:
1. **Identify** the command that proves the claim.
2. **Run** it fully and freshly, through `SW verify <id> -- <command>`.
3. **Read** all the output: the exit code, the failure count, and the warnings.
4. **Claim** only what the output shows, and cite it.

| Claim | Requires | Not enough |
|---|---|---|
| Tests pass | Test run: 0 failures, and the expected tests actually ran | An earlier run; "should pass" |
| Build succeeds | Build exit 0 | Lint passing |
| Bug fixed | The reproducing test now passes | "Code changed" |
| Requirements met | Each acceptance criterion checked one by one | Tests passing |
| Subagent finished | The diff, read by you, and the checks re-run by you | The agent's report |
| UI works | Browser screenshot at two widths, with the states checked | It compiles |

## Words that mean you skipped the gate

"should", "probably", "seems to", "looks good", "great, done!", or any satisfaction expressed
before running anything.

Partial evidence gets a partial claim: "Unit tests pass; I could not run the e2e suite because ...".
Say it plainly. Never round it up.
