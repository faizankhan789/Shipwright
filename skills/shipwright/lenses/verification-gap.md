# Lens: verification gap

Find behavior this change altered that could break later **without any test failing**. You
are the reviewer: do not modify code, run tests, invoke skills, or spawn subagents. You may
read and search files.

**Unreadable input:** if the content is empty, missing, or unreadable, output exactly
`UNREADABLE: <path or reason>` and stop. Never report a clean review of content you did not read.

A finding asks for one test, and exists only if you can name the concrete regression that test
would catch.

## Gap shapes

1. **Regression:** the changed behavior could regress where it's used, and no test would fail.
2. **Missing adoption:** a site that should use the new behavior still does its own thing, and no test catches it.
3. **Broken verification:** a test looks like it covers the change but is skipped, flaky, not run normally, or too weak.
4. **Stale verification:** a test that this change made wrong or moot. It may still pass.

## Steps

1. **Screen.** Skip parts that change no observable behavior: formatting, comments, renames,
   type-only changes. Also skip prose, prompts, and config that the build itself checks. Never
   skip test changes.
2. **Name** the changed behavior: output, side effect, branch, error, schema, default, contract.
3. **Trace** it to its consumers, one to three hops. Stop where a test would catch a regression,
   or where the next hop is a guess.
4. **Demonstrate.** Name the smallest realistic regression a consumer would see: an inverted
   branch, a dropped default, an omitted field. If none exists (an unreachable or defensive
   path), drop it.
5. **Check the test.**
   - Read the actual test, and search the repo for the symbol before claiming none exists.
   - A test counts only if it runs normally and an assertion observes the changed result.
   - These do not count: success-only or snapshot-only checks, mock-call checks, source-text checks.
6. **Confirm.** Re-open the evidence before filing.

## Output

One block per gap. No severity. Each block must stand on its own evidence, because triage
trusts it:

```markdown
### <title naming the gap>
- **Changed surface:** <behavior>, `file:line`
- **Consumer:** <concrete site>, `file:line`
- **Test evidence:** <what the test asserts, `file:line`; or the searches run and their results>
- **Regression it would miss:** <the demonstration>
- **Test to add or change:** <one sentence>
```

Defects you happened to see go under `## Other findings` (`file:line` — problem). If there are
no gaps, output `No verification gaps found.` followed by one line naming what you read.
