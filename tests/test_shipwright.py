"""Tests for shipwright/scripts/shipwright.py. Run: python3 -m unittest discover -s tests -v"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SW = REPO / "skills" / "shipwright" / "scripts" / "shipwright.py"
KEY_DIR = tempfile.mkdtemp()
ENV = {**os.environ, "SHIPWRIGHT_KEY_FILE": str(Path(KEY_DIR) / "key")}

S_PLAN = """
# {title}

<!-- frozen:start -->
## Intent

**Problem:** Users cannot log out.

**Approach:** Add a logout endpoint that clears the session.
<!-- frozen:end -->

## Verification

- `{cmd}` -- expected: exit 0

## Implementation Notes

- app.py -- touched by the change
"""

M_PLAN = """
# {title}

<!-- frozen:start -->
## Intent

**Problem:** Exports time out for large accounts.

**Approach:** Stream the CSV instead of building it in memory.

## Boundaries

**Always:** keep the column order.

**Never:** change the export URL.
<!-- frozen:end -->

## Code Map

- `src/export.py` -- builds the CSV

## Tasks

- [ ] `src/export.py` -- stream rows -- avoid memory blowup

## Acceptance Criteria

- Given an account with 1M rows, when exporting, then the download starts within 2s

## Verification

- `{cmd}` -- expected: exit 0

## Implementation Notes

## Plan Change Log

## Review Triage Log

| # | Lens | Location | Claim | Verdict | Route | Evidence / action |
|---|---|---|---|---|---|---|
{rows}
"""


LENS_ROWS = "\n".join(f"| {i} | {lens} | - | no findings | false | - | - |" for i, lens in
                      enumerate(["blind", "edge-case", "verification-gap", "intent", "rules"], 1))
GUARD = REPO / "hooks" / "guard_state.py"
DESIGN_HOOK = REPO / "hooks" / "design_check.py"
CHECK = ("python3", str(SW), "design-check")


def write_council(d: Path, members=3):
    (d / "brief.md").write_text(
        "# Brief\n\n## Question\n\nHow?\n\n## Problem\n\nSlow search.\n\n## Constraints\n\nPostgres.\n\n"
        "## Quality scenarios\n\n| ID | A | S | P |\n|---|---|---|---|\n| Q1 | perf | p95<300ms | H |\n"
        "| Q2 | cost | <$500/mo | M |\n| Q3 | avail | 99.9% | M |\n\n## Evidence\n\n- src/search.py\n")
    body = "position with evidence " * 20
    for i in range(members):
        L = "ABCDE"[i]
        (d / "round-1" / f"{L}.md").write_text(body)
        (d / "round-2" / f"{L}.md").write_text(body)
        (d / "round-3" / f"{L}.md").write_text(body + "\n\n## Dissent\n\nNone material: all objections answered.")
    (d / "round-2" / "input.md").write_text("Position A ...\nPosition B ...")
    (d / "round-3" / "input.md").write_text("Position A ...\nPosition B ...")
    (d / "key.md").write_text("- A: shipwright-principal-architect\n- B: shipwright-staff-engineer\n- C: shipwright-red-team\n")
    (d / "judge.md").write_text("| Scenario | A | B |\n|---|---|---|\n| Q1 (3) | 4 | 5 |\n")
    opt = "described with enough words to explain how it works and what it costs in practice here"
    (d / "decision.md").write_text(
        f"# D\n\n## Options\n\n### Option A: Postgres FTS\n{opt}\n\n### Option B: OpenSearch\n{opt}\n\n"
        "## Evaluation\n\n| Scenario | A | B |\n|---|---|---|\n| Q1 (3) | 4 | 5 |\n| Q2 (2) | 5 | 2 |\n\n"
        "## Decision\n\nOption A because cost dominates.\n\n## Architecture\n\nOne Postgres container serves search.\n\n"
        "## Well-Architected review\n\nReliability covered by replicas.\n\n## Risks\n\n| index bloat | M | M | vacuum | ops |\n\n"
        "## Dissent\n\n- One member: OpenSearch wins above 10M docs.\n")


class SwTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.sw("init")

    def tearDown(self):
        self.tmp.cleanup()

    def sw(self, *args, ok=True):
        r = subprocess.run([sys.executable, str(SW), "--root", str(self.root), *args],
                           capture_output=True, text=True, cwd=self.root, env=ENV)
        if ok is True:
            self.assertEqual(r.returncode, 0, f"sw {args} failed:\n{r.stdout}\n{r.stderr}")
        elif ok is False:
            self.assertNotEqual(r.returncode, 0, f"sw {args} unexpectedly passed:\n{r.stdout}")
        return r

    def new(self, title="Logout", size="S", extra=(), type_="chore", risk="low"):
        risk_args = ("--risk", risk) if risk else ()
        r = self.sw("new", title, "--size", size, "--type", type_, *risk_args, *extra)
        return Path(r.stdout.strip())

    def git(self, *a):
        return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *a],
                              cwd=self.root, capture_output=True, check=True)

    def git_repo(self):
        self.git("init", "-q")
        (self.root / "app.py").write_text("x = 1\n")
        self.git("add", "app.py")
        self.git("commit", "-q", "-m", "base")

    def fill(self, plan: Path, template: str, **kw):
        text = plan.read_text()
        fm_end = text.index("\n---\n", 4) + 5
        plan.write_text(text[:fm_end] + template.format(title="t", **kw))

    def fm(self, plan: Path) -> dict:
        head = plan.read_text().split("\n---\n", 1)[0]
        return dict(l.split(": ", 1) if ": " in l else (l.rstrip(":"), "") for l in head.splitlines()[1:])

    # --- layout ---
    def test_init_layout_and_idempotent(self):
        for p in ("work", "decisions", "initiatives", "context.md", "deferred.md"):
            self.assertTrue((self.root / ".shipwright" / p).exists(), p)
        self.sw("init")

    def test_new_creates_draft_with_sequential_ids(self):
        a = self.new("One")
        b = self.new("Two")
        self.assertTrue(a.parent.name.startswith("001-"))
        self.assertTrue(b.parent.name.startswith("002-"))
        self.assertEqual(self.fm(a)["status"], "draft")

    # --- plan lint ---
    def test_fresh_template_fails_check(self):
        plan = self.new(size="M")
        r = self.sw("check", "001", ok=False)
        self.assertIn("unfilled template marker", r.stdout)

    def test_filled_s_plan_passes_check(self):
        plan = self.new()
        self.fill(plan, S_PLAN, cmd="true")
        self.sw("check", "001")

    def test_m_plan_lint_rules(self):
        plan = self.new(size="M")
        self.fill(plan, M_PLAN, cmd="true", rows="")
        self.sw("check", "001")
        text = plan.read_text()
        bad = (text.replace("- [ ] `src/export.py` -- stream", "- [ ] src/export.py -- stream")
                   .replace("- Given an account", "- An account"))
        plan.write_text(bad + "\n## Open Questions\n\n1. CSV or XLSX?\n")
        r = self.sw("check", "001", ok=False)
        self.assertIn("task without a `file path`", r.stdout)
        self.assertIn("not Given/When/Then", r.stdout)
        self.assertIn("Open Questions is not empty", r.stdout)

    def test_tbd_in_body_fails(self):
        plan = self.new()
        self.fill(plan, S_PLAN.replace("Users cannot log out.", "TBD"), cmd="true")
        r = self.sw("check", "001", ok=False)
        self.assertIn("placeholder", r.stdout)

    # --- transitions ---
    def test_illegal_transition_refused(self):
        self.new()
        r = self.sw("mark", "001", "building", ok=False)
        self.assertIn("cannot go draft -> building", r.stderr)

    def test_ready_refused_while_lint_fails(self):
        self.new()
        r = self.sw("mark", "001", "ready", ok=False)
        self.assertIn("REFUSED", r.stdout)

    def test_blocked_requires_reason(self):
        self.new()
        self.sw("mark", "001", "blocked", ok=False)
        self.sw("mark", "001", "blocked", "--reason", "waiting on API keys")

    # --- evidence gate (S path) ---
    def s_building(self, cmd="true"):
        plan = self.new()
        self.fill(plan, S_PLAN, cmd=cmd)
        self.sw("mark", "001", "ready")
        self.sw("mark", "001", "building")
        return plan

    def test_verified_needs_evidence(self):
        self.s_building()
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("no verification evidence", r.stdout)

    def test_failing_evidence_blocks_then_passing_allows(self):
        self.s_building(cmd="true")
        self.sw("verify", "001", "--", "false", ok=False)
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("latest run failed", r.stdout)
        self.assertIn("no current passing run for planned check: true", r.stdout)
        self.sw("verify", "001", "--", "true")
        r = self.sw("mark", "001", "verified", ok=False)  # 'false' still failing as latest of its cmd
        self.assertIn("latest run failed (exit 1): false", r.stdout)

    def test_s_happy_path_to_done(self):
        plan = self.s_building(cmd="true")
        self.sw("verify", "001", "--", "true")
        self.sw("mark", "001", "verified")
        self.sw("mark", "001", "done")
        self.assertEqual(self.fm(plan)["status"], "done")
        ev = [json.loads(l) for l in (plan.parent / "evidence.jsonl").read_text().splitlines()]
        self.assertEqual(ev[-1]["exit"], 0)

    def test_manual_check_required_when_planned(self):
        plan = self.new()
        self.fill(plan, S_PLAN.replace("## Implementation Notes",
                                       "- Manual: screenshot at 375px\n\n## Implementation Notes"), cmd="true")
        self.sw("mark", "001", "ready")
        self.sw("mark", "001", "building")
        self.sw("verify", "001", "--", "true")
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("Manual checks but none recorded", r.stdout)
        self.sw("verify", "001", "--manual", "375px screenshot ok", ok=False)  # artifact required
        self.sw("verify", "001", "--manual", "ok", "--artifact", "missing.png", ok=False)
        (self.root / "shot.png").write_bytes(b"\x89PNG fake")
        self.sw("verify", "001", "--manual", "375px screenshot ok", "--artifact", "shot.png")
        self.sw("mark", "001", "verified")

    def test_verify_keeps_inner_double_dash_and_rejects_mixed(self):
        plan = self.s_building(cmd="echo a -- b")
        r = self.sw("verify", "001", "--", "echo", "a", "--", "b")
        self.assertIn("PASS (exit 0): echo a -- b", r.stdout)
        self.sw("mark", "001", "verified")
        self.sw("verify", "001", "--manual", "x", "--", "true", ok=False)

    # --- frozen intent ---
    def test_intent_edit_after_approval_is_caught(self):
        plan = self.s_building()
        plan.write_text(plan.read_text().replace("Users cannot log out.", "Users cannot log in."))
        r = self.sw("check", "001", ok=False)
        self.assertIn("approved plan changed", r.stdout)
        self.sw("verify", "001", "--", "true")
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("approved plan changed", r.stdout)

    # --- M path: review + triage + loopback cap ---
    def m_reviewing(self, rows=""):
        plan = self.new(size="M")
        self.fill(plan, M_PLAN, cmd="true", rows=rows)
        self.sw("mark", "001", "ready", ok=False)  # M needs an explicit approver
        self.sw("mark", "001", "ready", "--approved-by", "tester")
        self.sw("mark", "001", "building")
        self.sw("verify", "001", "--", "true")
        return plan

    def test_m_cannot_skip_review(self):
        self.m_reviewing()
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("must pass review first", r.stderr)

    def test_m_needs_triage_rows_without_pending(self):
        plan = self.m_reviewing(rows=LENS_ROWS + "\n| 6 | blind | a.py:3 | x | pending | - | - |")
        self.sw("mark", "001", "reviewing")
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("triage row still pending", r.stdout)
        plan.write_text(plan.read_text().replace("| pending | - | - |", "| false | reject | guarded at a.py:1 |"))
        self.sw("mark", "001", "verified")

    def test_m_empty_triage_log_refused(self):
        self.m_reviewing()
        self.sw("mark", "001", "reviewing")
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("Review Triage Log has no rows", r.stdout)

    def test_loopback_cap(self):
        self.m_reviewing()
        for _ in range(5):
            self.sw("mark", "001", "reviewing")
            self.sw("mark", "001", "building")
        self.sw("mark", "001", "reviewing")
        r = self.sw("mark", "001", "building", ok=False)
        self.assertIn("loopback cap", r.stderr)

    def test_evidence_before_loopback_is_stale(self):
        plan = self.m_reviewing(rows="| 1 | all | - | no findings | false | - | lenses: all |")
        self.sw("mark", "001", "reviewing")
        self.sw("mark", "001", "building")  # loopback restarts the evidence clock
        self.sw("mark", "001", "reviewing")
        # any hand edit of the evidence (here: back-dating) breaks the signature chain
        ev = plan.parent / "evidence.jsonl"
        ev.write_text(ev.read_text().replace('"ts": "', '"ts": "0'))
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("edited outside shipwright.py", r.stdout)

    # --- dependencies, resume, records ---
    def test_next_respects_dependencies(self):
        self.new("First")
        self.new("Second", extra=("--after", "1"))
        self.assertIn("First", self.sw("next").stdout)
        self.sw("mark", "001", "dropped", "--reason", "superseded")
        # 002 waits on 001, which is dropped (not done), so nothing is actionable
        self.assertIn("nothing actionable", self.sw("next").stdout)

    def test_resume_lists_open_items(self):
        self.new("Alpha")
        self.sw("log", "001", "DECISION: use cookies")
        r = self.sw("resume")
        self.assertIn("Alpha", r.stdout)
        self.assertIn("DECISION: use cookies", r.stdout)

    def test_adr_numbering_and_defer(self):
        a = Path(self.sw("adr", "Use Postgres").stdout.strip())
        b = Path(self.sw("adr", "Use Redis").stdout.strip())
        self.assertIn("ADR-0001", a.name)
        self.assertIn("ADR-0002", b.name)
        self.sw("defer", "Add pagination", "--source", "001", "--evidence", "out of scope")
        self.assertIn("Add pagination", (self.root / ".shipwright" / "deferred.md").read_text())

    def test_initiative_and_membership(self):
        self.sw("initiative", "Billing v2")
        self.assertTrue((self.root / ".shipwright/initiatives/billing-v2/brief.md").exists())
        self.sw("new", "Skeleton", "--size", "M", "--initiative", "billing-v2")
        self.sw("new", "X", "--size", "M", "--initiative", "nope", ok=False)

    # --- git diff ---
    def test_diff_includes_untracked_and_excludes_state(self):
        g = lambda *a: subprocess.run(["git", *a], cwd=self.root, capture_output=True, check=True)
        g("init", "-q")
        g("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "base")
        self.s_building()
        (self.root / "new_file.py").write_text("print('hi')\n")
        r = self.sw("diff", "001")
        patch = Path(r.stdout.split(" (")[0]).read_text()
        self.assertIn("new_file.py", patch)
        self.assertNotIn(".shipwright", patch)
        (self.root / "__pycache__").mkdir()
        (self.root / "__pycache__" / "x.cpython-313.pyc").write_bytes(b"\x00junk")
        (self.root / ".DS_Store").write_bytes(b"\x00")
        r = self.sw("diff", "001")
        patch = Path(r.stdout.split(" (")[0]).read_text()
        self.assertNotIn("__pycache__", patch)
        self.assertNotIn(".DS_Store", patch)

    # --- triage helper, token budget, friction ---
    def test_triage_appends_rows_and_pending_blocks(self):
        plan = self.m_reviewing()
        self.sw("triage", "001", "--lens", "blind", "--location", "a.py:3", "--claim", "x | y",
                "--verdict", "pending", "--route", "-", "--evidence", "checking")
        self.sw("triage", "001", "--lens", "edge", "--location", "b.py:9", "--claim", "z",
                "--verdict", "low", "--route", "patch", "--evidence", "fixed")
        text = plan.read_text()
        self.assertIn("| 1 | blind | a.py:3 | x \\| y | pending |", text)
        self.assertIn("| 2 | edge | b.py:9 | z | low | patch | fixed |", text)
        self.sw("mark", "001", "reviewing")
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("pending", r.stdout)
        self.sw("triage", "001", "--lens", "x", "--location", "-", "--claim", "c",
                "--verdict", "bogus", "--route", "-", "--evidence", "e", ok=False)

    def test_triage_creates_table_when_missing(self):
        plan = self.new()
        self.fill(plan, S_PLAN, cmd="true")
        self.sw("triage", "001", "--lens", "edge", "--location", "-", "--claim", "no findings",
                "--verdict", "false", "--route", "-", "--evidence", "lenses: edge")
        text = plan.read_text()
        self.assertIn("## Review Triage Log", text)
        self.assertIn("| # | Lens |", text)
        self.assertIn("| 1 | edge |", text)

    def test_token_budget_ignores_build_logs(self):
        plan = self.new(size="M")
        self.fill(plan, M_PLAN, cmd="true", rows="")
        notes = "word " * 2000
        plan.write_text(plan.read_text().replace("## Plan Change Log", f"{notes}\n\n## Plan Change Log"))
        r = self.sw("check", "001")
        self.assertNotIn(">1600", r.stdout)

    def test_friction_collects_lines(self):
        self.new("A")
        self.new("B")
        self.sw("log", "002", "FRICTION: blind lens floor unclear")
        r = self.sw("friction")
        self.assertIn("002-b: ", r.stdout)
        self.assertIn("FRICTION: blind lens floor unclear", r.stdout)


    # --- loopholes found by the audit ---
    def test_blocked_cannot_bypass_approval(self):
        self.new(size="M")  # unfilled template
        self.sw("mark", "001", "blocked", "--reason", "x")
        r = self.sw("mark", "001", "building", ok=False)
        self.assertIn("not approved", r.stderr)

    def test_size_type_and_verification_frozen_at_approval(self):
        plan = self.s_building(cmd="make test")
        self.sw("set", "001", "size=M", ok=False)
        self.sw("set", "001", "type=feature", ok=False)
        plan.write_text(plan.read_text().replace("`make test`", "`true`"))
        r = self.sw("check", "001", ok=False)
        self.assertIn("approved plan changed", r.stdout)
        self.sw("verify", "001", "--", "true")
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("approved plan changed", r.stdout)
        text = plan.read_text().replace("size: S", "size: M").replace("`true`", "`make test`")
        plan.write_text(text)
        self.sw("mark", "001", "verified", ok=False)

    def test_risk_required_for_ready(self):
        plan = self.new(risk="")
        self.fill(plan, S_PLAN, cmd="true")
        r = self.sw("mark", "001", "ready", ok=False)
        self.assertIn("risk not set", r.stdout)
        self.sw("set", "001", "risk=high")
        self.sw("mark", "001", "ready")

    def test_feature_needs_real_red_run(self):
        plan = self.new(type_="feature")
        self.fill(plan, S_PLAN, cmd="python3 -c pass")
        self.sw("mark", "001", "ready")
        self.sw("mark", "001", "building")
        self.sw("verify", "001", "--", "python3 -c pass")
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("no red run recorded", r.stdout)
        r = self.sw("verify", "001", "--expect-fail", "--", "python3 -c pass", ok=False)
        self.assertIn("NOT RED", r.stdout)
        r = self.sw("verify", "001", "--expect-fail", "--", "false", ok=False)  # not the plan's test runner
        self.assertIn("wrong reason", r.stdout)
        self.sw("mark", "001", "verified", ok=False)
        self.sw("verify", "001", "--expect-fail", "--", "python3 -c 'assert 1 == 2'")
        self.sw("mark", "001", "verified")

    def test_bugfix_needs_hypothesis(self):
        plan = self.new(type_="bugfix")
        self.fill(plan, S_PLAN, cmd="python3 -c pass")
        self.sw("mark", "001", "ready")
        self.sw("mark", "001", "building")
        self.sw("verify", "001", "--expect-fail", "--", "python3 -c 'assert 0'")
        self.sw("verify", "001", "--", "python3 -c pass")
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("HYPOTHESIS", r.stdout)
        self.sw("log", "001", "HYPOTHESIS: x")
        self.sw("mark", "001", "verified", ok=False)  # too thin to be a hypothesis
        self.sw("log", "001", "HYPOTHESIS: off-by-one in pager because end index is inclusive")
        self.sw("mark", "001", "verified")

    def test_evidence_goes_stale_when_code_changes_and_done_rechecks(self):
        self.git_repo()
        self.s_building()
        (self.root / "app.py").write_text("x = 2\n")
        self.sw("verify", "001", "--", "true")
        self.sw("mark", "001", "verified")
        (self.root / "app.py").write_text("x = 3\n")  # patched after verification
        r = self.sw("mark", "001", "done", ok=False)
        self.assertIn("code changed since the last run of: true", r.stdout)
        self.sw("verify", "001", "--", "true")
        self.sw("mark", "001", "done")

    def test_clean_tree_required_to_start_building(self):
        self.git_repo()
        plan = self.new()
        self.fill(plan, S_PLAN, cmd="true")
        self.sw("mark", "001", "ready")
        (self.root / "app.py").write_text("unrelated edit\n")
        r = self.sw("mark", "001", "building", ok=False)
        self.assertIn("uncommitted changes", r.stderr)
        self.sw("mark", "001", "building", "--allow-dirty", ok=False)  # needs a reason
        self.sw("mark", "001", "building", "--allow-dirty", "--reason", "human said keep WIP")

    def test_every_reentry_to_building_counts(self):
        plan = self.s_building()
        self.sw("mark", "001", "draft")
        self.sw("mark", "001", "ready")
        self.sw("mark", "001", "building")
        self.assertEqual(self.fm(plan)["loopbacks"], "1")
        self.sw("mark", "001", "blocked", "--reason", "x")
        self.sw("mark", "001", "building")
        self.assertEqual(self.fm(plan)["loopbacks"], "2")

    def test_triage_reads_verdict_column_only(self):
        plan = self.m_reviewing(rows=LENS_ROWS + "\n| 6 | blind | a.py:3 | was pending upstream | false | reject | not pending |")
        self.sw("mark", "001", "reviewing")
        self.sw("mark", "001", "verified")

    def test_scope_creep_warning(self):
        self.git_repo()
        plan = self.s_building()
        (self.root / "app.py").write_text("x = 2\n")
        (self.root / "stray.py").write_text("y = 1\n")
        plan.write_text(plan.read_text().replace("## Implementation Notes", "## Implementation Notes\n\n- app.py"))
        self.sw("verify", "001", "--", "true")
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("not named in Tasks, Code Map or Implementation Notes: stray.py", r.stdout)
        self.assertNotIn(": app.py", r.stdout)

    def test_initiative_diff(self):
        self.git_repo()
        self.sw("initiative", "Billing")
        self.make_passing_initiative("billing")
        p1 = self.new("Slice one", extra=("--initiative", "billing"))
        self.fill(p1, S_PLAN, cmd="true")
        self.sw("mark", "001", "ready", "--approved-by", "tester")
        self.sw("mark", "001", "building")
        (self.root / "billing.py").write_text("total = 0\n")
        r = self.sw("diff", "--initiative", "billing")
        patch = Path(r.stdout.split(" (")[0]).read_text()
        self.assertIn("billing.py", patch)


    def make_passing_initiative(self, slug):
        d = self.root / ".shipwright" / "initiatives" / slug
        cd = Path(self.sw("council", "new", "Billing architecture").stdout.strip())
        write_council(cd)
        (d / "brief.md").write_text("# Brief\n\n## Scope\n\n- R1: invoices\n- R2: refunds\n")
        (d / "architecture.md").write_text(f"# A\n\nCouncil: {cd.name}\n\n## Slices\n\n"
                                           "1. Skeleton -- covers: R1\n2. Refunds -- after: 1 -- covers: R2\n")

    def test_initiative_check_gates_slice_ready(self):
        self.sw("initiative", "Shop")
        plan = self.new("Slice", extra=("--initiative", "shop"))
        self.fill(plan, S_PLAN, cmd="true")
        r = self.sw("mark", "001", "ready", ok=False)
        self.assertIn("initiative not approved-ready", r.stdout)
        d = self.root / ".shipwright" / "initiatives" / "shop"
        (d / "brief.md").write_text("# B\n\n## Scope\n\n- R1: cart\n- R2: checkout\n")
        (d / "architecture.md").write_text("# A\n\n## Slices\n\n1. Cart -- covers: R1\n")
        r = self.sw("initiative-check", "shop", ok=False)
        self.assertIn("not covered by any slice: R2", r.stdout)
        self.assertIn("no `Council:", r.stdout)
        self.make_passing_initiative("shop")
        self.sw("initiative-check", "shop")
        self.sw("mark", "001", "ready", "--approved-by", "tester")

    # --- council ---
    def test_council_record_is_enforced(self):
        d = Path(self.sw("council", "new", "How should search scale").stdout.strip())
        for f in ("brief.md", "decision.md", "round-1", "round-2", "round-3"):
            self.assertTrue((d / f).exists(), f)
        r = self.sw("council", "check", "01", "--brief", ok=False)
        self.assertIn("unfilled FILL", r.stdout)
        r = self.sw("council", "check", "how-should", ok=False)
        self.assertIn("round-1: needs positions from at least 3 members", r.stdout)
        write_council(d)
        self.sw("council", "check", "01")
        # loopholes: names in input, missing key, hollow decision, uneven rounds, no Dissent heading
        (d / "round-2" / "input.md").write_text("Position A (the red team) says ...")
        self.assertIn("names a member or role", self.sw("council", "check", "01", ok=False).stdout)
        write_council(d)
        (d / "key.md").unlink()
        self.assertIn("key.md missing", self.sw("council", "check", "01", ok=False).stdout)
        write_council(d)
        (d / "round-2" / "C.md").unlink()
        self.assertIn("different member counts", self.sw("council", "check", "01", ok=False).stdout)
        write_council(d)
        (d / "round-3" / "A.md").write_text("position " * 60 + " no dissent here")
        self.assertIn("no '## Dissent' heading", self.sw("council", "check", "01", ok=False).stdout)
        write_council(d)
        (d / "decision.md").write_text("# D\n\n## Options\n\n### Option A\n\n### Option B\n\n## Evaluation\n\n"
                                       "## Decision\n\n## Architecture\n\n## Well-Architected review\n\n## Risks\n\n"
                                       "## Dissent\n\n- none\n")
        r = self.sw("council", "check", "01", ok=False)
        self.assertIn("needs at least 2 fundamentally different options", r.stdout)
        self.assertIn("no numeric scores", r.stdout)
        self.assertIn("## Decision is empty", r.stdout)

    def test_works_without_git_installed(self):
        plan = self.new()
        self.fill(plan, S_PLAN, cmd="true")
        env = {**ENV, "PATH": "/nonexistent"}
        run = lambda *a: subprocess.run([sys.executable, str(SW), "--root", str(self.root), *a], capture_output=True,
                                        text=True, cwd=self.root, env=env)
        self.assertEqual(run("mark", "001", "ready").returncode, 0)
        r = run("mark", "001", "building")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("baseline: NO_VCS", plan.read_text())

    # --- security review ---
    def test_gate_rejects_lookalike_tool_and_shell_syntax(self):
        m = load_cli()
        real = f"python3 {SW} design-check site.css"
        self.assertEqual(m.design_check_targets(real), ["site.css"])
        self.assertIsNone(m.design_check_targets("python3 /tmp/fake/shipwright.py design-check site.css"))
        for bad in (real + " || true", real + " | cat", real + "; true", real + " > /dev/null", "$(x) " + real):
            self.assertIsNone(m.design_check_targets(bad), bad)

    def test_log_cannot_forge_gate_lines(self):
        self.new()
        for text in ("GUIDE: shipwright_ui/shipwright-ui-polish", "STATUS done -> done", "EVIDENCE exit=0 true"):
            self.sw("log", "001", text, ok=False)
        self.sw("log", "001", "DECISION: mention GUIDE: in passing is fine")

    def test_newlines_cannot_forge_log_lines_or_frontmatter(self):
        plan = self.new()
        forged = "note\n- 2026-01-01T00:00:00 GUIDE: shipwright_ui/shipwright-ui-polish"
        self.sw("log", "001", forged)
        self.sw("mark", "001", "blocked", "--reason", forged)
        log = (plan.parent / "log.md").read_text()
        self.assertNotRegex(log, r"(?m)^- \S+ GUIDE:")
        self.sw("set", "001", "after=1\napproval_hash: forged")
        self.assertNotRegex(plan.read_text(), r"(?m)^approval_hash: forged")
        title = self.sw("new", "T\nstatus: done", "--size", "S").stdout.strip()
        self.assertEqual(self.fm(Path(title))["status"], "draft")

    def test_route_use_accepts_only_catalog_guides(self):
        self.new()
        for bad in ("../../../phases", "shipwright_ui/../shipwright_ui/shipwright-ui-polish", "shipwright_ui"):
            self.sw("route", "--use", bad, "--id", "001", ok=False)

    def test_no_git_baseline_is_logged(self):
        plan = self.s_building()
        self.assertIn("NO_VCS: no git baseline", (plan.parent / "log.md").read_text())

    def test_missing_engine_fails_closed_unless_acknowledged(self):
        import argparse, contextlib, io, os as _os
        from unittest import mock
        m = load_cli()
        (self.root / "site.css").write_text("h1{color:#111}\n")
        (self.root / "A.tsx").write_text("export const A = () => <b>hi</b>;\n")
        args = lambda paths, allow: argparse.Namespace(paths=paths, json=False, allow_no_engine=allow)
        cwd = _os.getcwd()
        _os.chdir(self.root)
        try:
            with mock.patch.object(m, "design_engine", return_value=None), contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(m.cmd_design_check(args(["site.css"], False)), 1)
                self.assertEqual(m.cmd_design_check(args(["site.css"], True)), 0)
                self.assertEqual(m.cmd_design_check(args(["A.tsx"], False)), 0)  # JSX rules still ran
        finally:
            _os.chdir(cwd)

    # --- second audit loopholes ---
    def test_small_item_too_big_or_risky_must_review(self):
        self.git_repo()
        plan = self.new(risk="high")
        self.fill(plan, S_PLAN, cmd="true")
        self.sw("mark", "001", "ready")
        self.sw("mark", "001", "building")
        (self.root / "app.py").write_text("x = 2\n")
        self.sw("verify", "001", "--", "true")
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("too big or risky to skip review", r.stdout)

    def test_red_must_fail_for_the_right_reason_after_build_start(self):
        plan = self.new(type_="feature")
        self.fill(plan, S_PLAN, cmd="python3 -c pass")
        self.sw("verify", "001", "--expect-fail", "--", "python3 -c 'assert 0'")  # recorded while still draft
        self.sw("mark", "001", "ready")
        self.sw("mark", "001", "building")
        r = self.sw("verify", "001", "--expect-fail", "--", "no_such_command_xyz", ok=False)
        self.assertIn("wrong reason", r.stdout)
        r = self.sw("verify", "001", "--expect-fail", "--", "python3 -c 'import nonexistent_mod_q'", ok=False)
        self.assertIn("wrong reason", r.stdout)
        self.sw("verify", "001", "--", "python3 -c pass")
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("no red run recorded", r.stdout)  # the draft-time red predates the build
        self.sw("verify", "001", "--expect-fail", "--", "python3 -c 'assert 1 == 2'")
        self.sw("mark", "001", "verified")

    def test_triage_requires_each_lens_and_real_findings_not_rejected(self):
        plan = self.m_reviewing(rows="| 1 | blind | - | no findings | false | - | - |")
        self.sw("mark", "001", "reviewing")
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("no triage row from required lens(es): edge-case, verification-gap, intent, rules", r.stdout)
        plan.write_text(plan.read_text().replace("| 1 | blind | - | no findings | false | - | - |",
                                                 LENS_ROWS + "\n| 6 | blind | a.py:1 | leak | high | reject | meh |"))
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("real high finding must be patched", r.stdout)
        plan.write_text(plan.read_text().replace("| high | reject | meh |", "| high | patch | guarded, test added |"))
        self.sw("mark", "001", "verified")

    def test_one_lens_per_triage_row(self):
        self.m_reviewing(rows="| 1 | blind edge verification intent rules security | - | none | false | - | - |")
        self.sw("mark", "001", "reviewing")
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("one lens per triage row", r.stdout)

    def test_m_review_diff_required_for_current_round(self):
        self.git_repo()
        plan = self.new(size="M")
        self.fill(plan, M_PLAN, cmd="true", rows=LENS_ROWS)
        self.sw("mark", "001", "ready", "--approved-by", "tester")
        self.sw("mark", "001", "building")
        (self.root / "src").mkdir()
        (self.root / "src" / "export.py").write_text("rows = []\n")
        self.sw("verify", "001", "--", "true")
        self.sw("mark", "001", "reviewing")
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("no review diff for the current build round", r.stdout)
        self.sw("diff", "001")
        self.sw("mark", "001", "verified")

    def test_acceptance_criteria_frozen(self):
        plan = self.new(size="M")
        self.fill(plan, M_PLAN, cmd="true", rows="")
        self.sw("mark", "001", "ready", "--approved-by", "tester")
        plan.write_text(plan.read_text().replace("within 2s", "within 20s"))
        self.assertIn("approved plan changed", self.sw("check", "001", ok=False).stdout)

    def test_ui_change_needs_screenshot_evidence(self):
        self.git_repo()
        plan = self.s_building()
        (self.root / "Button.tsx").write_text("export const B = () => null\n")
        plan.write_text(plan.read_text().replace("## Implementation Notes", "## Implementation Notes\n\n- Button.tsx"))
        self.sw("verify", "001", "--", "true")
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("UI files changed", r.stdout)
        shots = plan.parent / "review"
        shots.mkdir(exist_ok=True)
        (shots / "shot-375.png").write_bytes(b"\x89PNG fake")
        (shots / "notes.py").write_text("x")
        self.sw("verify", "001", "--manual", "ok", "--artifact", str(shots / "notes.py"), ok=False)  # wrong type
        self.sw("verify", "001", "--manual", "375 and 1280 ok", "--artifact", str(shots / "shot-375.png"))
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("no design guide was consulted", r.stdout)
        out = self.sw("route", "build", "the", "settings", "screen", "--id", "001").stdout
        self.assertIn("shipwright_ui/", out)
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("without a passing design check", r.stdout)
        self.sw("verify", "001", "--", *CHECK, "Button.tsx")
        self.sw("mark", "001", "verified")

    def ui_item(self, css):
        self.git_repo()
        plan = self.s_building()
        (self.root / "site.css").write_text(css)
        plan.write_text(plan.read_text().replace("## Implementation Notes", "## Implementation Notes\n\n- site.css"))
        self.sw("verify", "001", "--", "true")
        shots = plan.parent / "review"
        shots.mkdir(exist_ok=True)
        (shots / "s.png").write_bytes(b"\x89PNG fake")
        self.sw("verify", "001", "--manual", "375 and 1280 ok", "--artifact", str(shots / "s.png"))
        self.sw("route", "--use", "shipwright_ui/shipwright-ui-polish", "--id", "001")
        return plan

    def test_design_check_cannot_be_faked(self):
        self.ui_item("h1{color:#111}\n")
        self.sw("verify", "001", "--", "echo", "shipwright-design", "detect", "site.css")  # not the detector
        self.sw("verify", "001", "--", *CHECK, "other-file.css", "||", "true", ok=None)  # chained: exit code masked
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("without a passing design check on the current code: site.css", r.stdout)
        self.sw("verify", "001", "--", *CHECK, "site.css")
        self.sw("mark", "001", "verified")

    def test_design_findings_block_verified(self):
        self.ui_item("h1{background:linear-gradient(90deg,#a855f7,#3b82f6);-webkit-background-clip:text;color:transparent}\n")
        self.sw("verify", "001", "--", *CHECK, "site.css", ok=False)
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("site.css", r.stdout)

    def test_design_check_goes_stale_when_ui_changes(self):
        self.ui_item("h1{color:#111}\n")
        self.sw("verify", "001", "--", *CHECK, "site.css")
        (self.root / "site.css").write_text("h1{color:#222}\n")
        self.sw("verify", "001", "--", "true")
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("without a passing design check on the current code", r.stdout)

    def test_future_dated_evidence_is_rejected(self):
        plan = self.s_building()
        with (plan.parent / "evidence.jsonl").open("a") as fh:
            fh.write(json.dumps({"ts": "2999-01-01T00:00:00", "cmd": "true", "exit": 0, "fp": ""}) + "\n")
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("edited outside shipwright.py", r.stdout)

    def test_forged_exit_code_is_detected(self):
        plan = self.s_building()
        self.sw("verify", "001", "--", "false", ok=False)
        ev = plan.parent / "evidence.jsonl"
        ev.write_text(ev.read_text().replace('"exit": 1', '"exit": 0').replace("false", "true"))
        r = self.sw("mark", "001", "verified", ok=False)
        self.assertIn("edited outside shipwright.py", r.stdout)


def load_cli():
    import importlib.util
    spec = importlib.util.spec_from_file_location("shipwright_cli", SW)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class RoutingTest(unittest.TestCase):
    """The deterministic trigger/route layer must stay exact on every labelled prompt we have."""
    @classmethod
    def setUpClass(cls):
        cls.m = load_cli()

    def check_set(self, name, area_map=None):
        cases = json.loads((REPO / "evals" / name).read_text())["cases"]
        bad = []
        for c in cases:
            k = self.m.classify_prompt(c["prompt"])
            if (k is not None) != c["trigger"] or (c.get("kind") and k != c["kind"]):
                bad.append(f"trigger {c['prompt']!r} -> {k}")
            want = c.get("guide") or (area_map or {}).get(c.get("area"))
            if c["trigger"] and want:
                gs = [r["guides"][0] for r in self.m.route(c["prompt"])]
                if not any(want in g for g in gs):
                    bad.append(f"route {c['prompt']!r} -> {gs}")
        self.assertEqual(bad, [])

    def test_labelled_set(self):
        self.check_set("routing_cases.json")

    def test_heldout_set(self):
        area = {"debugging-general": "systematic-debugging", "performance": "performance-profiler", "memory-leak": "memory-leak",
                "janky-animation": "animation-performance", "public-page-ui": "art-direction", "app-screen-ui": "interface-design",
                "ui-critique": "design-craft", "mobile-gestures": "fluid-motion-design", "figma": "figma", "toasts": "sonner",
                "accessibility": "a11y", "tests-unit": "test-driven-development", "tests-e2e-browser": "browser-automation",
                "tests-api": "api-test-suite", "ci-cd": "ci-cd", "docker": "docker", "kubernetes": "kubernetes",
                "terraform": "terraform", "sql": "sql", "data-model-migration": "database", "api-design": "api-design",
                "feature-flags": "feature-flags", "security-auth": "security", "dependencies-secrets": "dependency",
                "rag-llm": "rag", "huggingface-training": "huggingface", "mcp-server": "mcp", "stripe-payments": "stripe",
                "android": "android", "ios-swift": "swift", "release-deploy": "release",
                "merge-pr": "finishing-a-development-branch", "pr-feedback": "receiving-code-review",
                "codebase-onboarding": "onboarding"}
        self.check_set("heldout_cases.json", area)
        self.check_set("heldout2_cases.json", area)
        self.check_set("heldout3_cases.json", area)

    def test_catalog_lists_every_guide_and_is_in_sync(self):
        lib = REPO / "skills" / "shipwright" / "library"
        on_disk = {f"{s.name}/{g.name}" for s in lib.iterdir() if s.is_dir() for g in s.iterdir() if (g / "GUIDE.md").is_file()}
        cat = {g["guide"] for g in json.loads((lib / "catalog.json").read_text())["guides"]}
        self.assertEqual(on_disk - cat, set(), "guides missing from the catalog")
        self.assertEqual(cat - on_disk, set(), "catalog lists guides that do not exist")
        r = subprocess.run([sys.executable, str(SW), "catalog", "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_every_guide_is_reachable_by_context(self):
        miss = [g["guide"] for g in self.m.catalog()
                if g["guide"] not in [x[1]["guide"] for x in self.m.bm25(g["description"][:220] or g["name"])][:3]]
        self.assertEqual(miss, [])

    def test_route_use_logs_a_chosen_guide(self):
        with tempfile.TemporaryDirectory() as t:
            run = lambda *a: subprocess.run([sys.executable, str(SW), "--root", t, *a], capture_output=True, text=True, env=ENV)
            run("init"); run("new", "Settings", "--size", "S", "--type", "chore", "--risk", "low")
            self.assertEqual(run("route", "--use", "shipwright_ui/shipwright-ui-polish", "--id", "001").returncode, 0)
            self.assertNotEqual(run("route", "--use", "shipwright_ui/nope", "--id", "001").returncode, 0)
            log = next(Path(t, ".shipwright", "work").glob("001-*")) / "log.md"
            self.assertIn("GUIDE: shipwright_ui/shipwright-ui-polish (chosen)", log.read_text())

    def test_paraphrase_set_triggers(self):
        # indirect phrasings: the hook must still recognise the task (routing them is the model's job, see evals)
        cases = json.loads((REPO / "evals" / "heldout4_cases.json").read_text())["cases"]
        bad = [c["prompt"] for c in cases if (self.m.classify_prompt(c["prompt"]) is not None) != c["trigger"]]
        self.assertEqual(bad, [])

    def test_every_routed_guide_exists(self):
        lib = REPO / "skills" / "shipwright" / "library"
        rules = json.loads((lib / "routing.json").read_text())["rules"]
        self.assertEqual([g for r in rules for g in r["guides"] if not (lib / g / "GUIDE.md").exists()], [])

    def test_prompt_hook_speaks_only_for_tasks(self):
        hook = REPO / "hooks" / "route_prompt.py"
        run = lambda p: subprocess.run([sys.executable, str(hook)], input=json.dumps({"prompt": p}),
                                       capture_output=True, text=True)
        task = run("Build a landing page for my coffee shop")
        self.assertEqual(task.returncode, 0)
        self.assertIn("invoke the `shipwright` skill", task.stdout)
        self.assertIn("shipwright-art-direction", task.stdout)
        for q in ("What does this regex do?", "/help", "thanks!", "set MAX_RETRIES to 5 in settings.py"):
            r = run(q)
            self.assertEqual((r.returncode, r.stdout), (0, ""), q)
        broken = subprocess.run([sys.executable, str(hook)], input="not json", capture_output=True, text=True)
        self.assertEqual(broken.returncode, 0)


class PortabilityTest(unittest.TestCase):
    def test_every_python_hook_goes_through_the_launcher(self):
        hooks = json.loads((REPO / "hooks" / "hooks.json").read_text())["hooks"]
        cmds = [h["command"] for ev in hooks.values() for g in ev for h in g["hooks"]]
        py = [c for c in cmds if '.py"' in c]  # commands that execute a Python script
        self.assertGreaterEqual(len(py), 3)
        self.assertTrue(all("hooks/py.sh" in c and not c.startswith("python") for c in py), py)

    def test_launcher_passes_exit_codes_and_survives_no_python(self):
        with tempfile.TemporaryDirectory() as t:
            script = Path(t) / "x.py"
            script.write_text("import sys; print('ran'); sys.exit(2)")
            r = subprocess.run(["sh", str(REPO / "hooks" / "py.sh"), str(script)], capture_output=True, text=True)
            self.assertEqual((r.returncode, r.stdout.strip()), (2, "ran"))
            r = subprocess.run(["/bin/sh", str(REPO / "hooks" / "py.sh"), str(script)], capture_output=True, text=True,
                               env={"PATH": t})
            self.assertEqual((r.returncode, r.stdout), (0, ""))

    def test_every_platform_engine_is_bundled_and_clean(self):
        base = REPO / "skills/shipwright/library/shipwright_ui/shipwright-design-craft/scripts/bin"
        want = {"darwin-arm64/shipwright-design-engine", "darwin-x64/shipwright-design-engine",
                "linux-arm64/shipwright-design-engine", "linux-x64/shipwright-design-engine",
                "windows-x64/shipwright-design-engine.exe"}
        self.assertEqual({str(p.relative_to(base)) for p in base.glob("*/*")}, want)
        for w in want:
            b = (base / w).read_bytes()
            self.assertEqual([t for t in (b"impeccable", b"npx shipwright", b"shipwright.style") if t in b], [], w)


class DesignRulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SW.parent))
        import design_rules
        cls.r = design_rules

    def rules(self, jsx):
        return sorted({f["antipattern"] for f in self.r.check_jsx(jsx, "x.tsx")})

    def test_each_rule_fires(self):
        cases = {
            "gradient-text": "<h1 style={{ background: 'linear-gradient(red,blue)', WebkitBackgroundClip: 'text' }}>a</h1>",
            "low-contrast": "<p style={{ color: '#aaa', backgroundColor: '#bbb' }}>a</p>",
            "tiny-text": "<p className='text-[10px]'>a</p>",
            "justified-text": "<p style={{ textAlign: 'justify' }}>a</p>",
            "img-no-alt": "<img src='/a.png' />",
            "clickable-div": "<div onClick={() => go()}>a</div>",
            "input-no-label": "<input type='text' />",
            "focus-removed": "<a className='outline-none' href='/'>a</a>",
            "icon-button-no-name": "<button><TrashIcon /></button>",
        }
        for rule, jsx in cases.items():
            self.assertIn(rule, self.rules(jsx), jsx)

    def test_tailwind_contrast_uses_real_palette(self):
        self.assertIn("low-contrast", self.rules('<p className="text-gray-400 bg-white">a</p>'))
        self.assertEqual(self.rules('<p className="text-gray-900 bg-white">a</p>'), [])
        self.assertAlmostEqual(self.r.contrast("000000", "ffffff"), 21.0, places=1)

    def test_good_code_stays_clean(self):
        good = """
        const List = ({ items }: { items: Item[] }) => (
          <section className="text-gray-900 bg-white">
            <img src="/a.png" alt="Chart" />
            <button aria-label="Delete"><TrashIcon /></button>
            <button onClick={save}>Save</button>
            <label htmlFor="n">Name</label><input id="n" />
            <input type="hidden" name="t" />
            <div role="button" tabIndex={0} onClick={go}>Go</div>
            <a className="outline-none focus-visible:ring-2" href="/">Home</a>
            {items.map((i) => (i.count > 3 ? <b key={i.id}>{i.name}</b> : null))}
          </section>
        );
        """
        self.assertEqual(self.rules(good), [])

    def test_disable_comment_silences_a_line(self):
        self.assertEqual(self.rules("{/* shipwright-disable decorative */}\n<img src='/d.png' />"), [])


class DesignHookTest(unittest.TestCase):
    BAD = "h1{background:linear-gradient(90deg,#a855f7,#3b82f6);-webkit-background-clip:text;color:transparent}\n"

    def run_hook(self, path, cwd, tool="Edit"):
        return subprocess.run([sys.executable, str(DESIGN_HOOK)], capture_output=True, text=True,
                              input=json.dumps({"tool_name": tool, "tool_input": {"file_path": str(path)}, "cwd": str(cwd)}))

    def test_reports_findings_without_blocking(self):
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / "site.css"
            f.write_text(self.BAD)
            r = self.run_hook(f, t)
            self.assertEqual(r.returncode, 0)
            ctx = json.loads(r.stdout)["hookSpecificOutput"]
            self.assertEqual(ctx["hookEventName"], "PostToolUse")
            self.assertIn("gradient-text", ctx["additionalContext"])

    def test_silent_when_clean_or_not_ui_or_generated(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "ok.css").write_text("h1{color:#111}\n")
            (root / "a.py").write_text(self.BAD)
            (root / "node_modules").mkdir()
            (root / "node_modules" / "x.css").write_text(self.BAD)
            for f in ("ok.css", "a.py", "node_modules/x.css", "missing.css"):
                r = self.run_hook(root / f, t)
                self.assertEqual((r.returncode, r.stdout), (0, ""), f)

    def test_project_under_a_folder_named_build_is_still_checked(self):
        with tempfile.TemporaryDirectory() as t:
            proj = Path(t) / "build" / "app"
            proj.mkdir(parents=True)
            (proj / "site.css").write_text(self.BAD)
            self.assertIn("gradient-text", self.run_hook(proj / "site.css", proj).stdout)

    def test_bad_payload_never_breaks_an_edit(self):
        r = subprocess.run([sys.executable, str(DESIGN_HOOK)], input="not json", capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout), (0, ""))


class GuardHookTest(unittest.TestCase):
    def run_guard(self, payload):
        return subprocess.run([sys.executable, str(GUARD)], input=json.dumps(payload),
                              capture_output=True, text=True)

    def bash(self, cmd):
        return self.run_guard({"tool_name": "Bash", "tool_input": {"command": cmd}}).returncode

    def test_blocks_hand_edits_to_records(self):
        for name in ("evidence.jsonl", "deploys.jsonl", "log.md"):
            r = self.run_guard({"tool_name": "Write", "tool_input": {
                "file_path": f"/p/.shipwright/work/001-x/{name}", "content": "{}"}})
            self.assertEqual(r.returncode, 2, name)

    def test_shell_bypasses_from_the_audit_are_blocked(self):
        for cmd in ("echo '{}' >> .shipwright/work/001-x/evidence.jsonl",
                    "echo x >> .shipwright/work/001/evidence.jsonl # shipwright.py",
                    "cd .shipwright/work/001-x && echo '{}' >> evidence.jsonl",
                    "python3 - <<EOF\nopen('evidence.jsonl','a').write('x')\nEOF",
                    "sed -i 's/status: draft/status: ready/' .shipwright/work/001-x/plan.md",
                    "cp /tmp/forged.jsonl .shipwright/deploys.jsonl"):
            self.assertEqual(self.bash(cmd), 2, cmd)

    def test_normal_commands_pass(self):
        for cmd in ("python3 /s/scripts/shipwright.py verify 001 -- pytest -q",
                    "python3 /s/scripts/shipwright.py log 001 'HYPOTHESIS: cache key ignores locale because ...'",
                    "cat .shipwright/work/001-x/evidence.jsonl | jq .exit",
                    "npm test 2>&1 | tail -5"):
            self.assertEqual(self.bash(cmd), 0, cmd)

    def test_plan_frontmatter_locked_by_position_body_editable(self):
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / ".shipwright" / "work" / "001-x" / "plan.md"
            f.parent.mkdir(parents=True)
            f.write_text("---\nstatus: building\nrisk: low\n---\n# T\n\n- [ ] `a.py` -- add\n")
            edit = lambda old: self.run_guard({"tool_name": "Edit", "tool_input": {
                "file_path": str(f), "old_string": old, "new_string": "zzz"}}).returncode
            self.assertEqual(edit("atus: building"), 2)  # mid-line edit of a frontmatter field
            self.assertEqual(edit("risk: low"), 2)
            self.assertEqual(edit("- [ ] `a.py` -- add"), 0)
            write = lambda content: self.run_guard({"tool_name": "Write", "tool_input": {
                "file_path": str(f), "content": content}}).returncode
            self.assertEqual(write("---\nstatus: building\nrisk: low\n---\nnew body\n"), 0)
            self.assertEqual(write("---\nstatus: done\nrisk: low\n---\nnew body\n"), 2)

    def test_windows_paths_are_protected_too(self):
        for name in ("evidence.jsonl", "deploys.jsonl", "log.md"):
            r = self.run_guard({"tool_name": "Write", "tool_input": {
                "file_path": f"C:\\Users\\me\\app\\.shipwright\\work\\001-x\\{name}", "content": "x"}})
            self.assertEqual(r.returncode, 2, name)
        self.assertEqual(self.bash("echo x >> .shipwright\\work\\001-x\\evidence.jsonl"), 2)

    def test_ignores_unrelated_files(self):
        r = self.run_guard({"tool_name": "Write", "tool_input": {"file_path": "/p/src/app.py", "content": "x"}})
        self.assertEqual(r.returncode, 0)


class DoraTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.sw("init")

    def tearDown(self):
        self.tmp.cleanup()

    def sw(self, *args, ok=True):
        r = subprocess.run([sys.executable, str(SW), "--root", str(self.root), *args],
                           capture_output=True, text=True, cwd=self.root, env=ENV)
        self.assertEqual(r.returncode == 0, ok, f"{args}: {r.stdout}{r.stderr}")
        return r

    def done_item(self, title, type_="chore", extra=()):
        out = self.sw("new", title, "--size", "S", "--type", type_, "--risk", "low", *extra).stdout.strip()
        plan = Path(out)
        text = plan.read_text()
        head = text[:text.index("\n---\n", 4) + 5]
        plan.write_text(head + S_PLAN.format(title=title, cmd="python3 -c pass"))
        iid = plan.parent.name[:3]
        self.sw("mark", iid, "ready")
        self.sw("mark", iid, "building")
        if type_ in ("feature", "bugfix"):
            self.sw("verify", iid, "--expect-fail", "--", "python3 -c 'assert 0'")
        if type_ == "bugfix":
            self.sw("log", iid, "HYPOTHESIS: the cache key ignores locale because it hashes path only")
        self.sw("verify", iid, "--", "python3 -c pass")
        self.sw("mark", iid, "verified")
        self.sw("mark", iid, "done")
        return iid

    def test_deploys_failures_recovery_and_rework(self):
        a = self.done_item("Feature A", "feature")
        b = self.done_item("Feature B", "feature")
        self.sw("deploy", "--items", "009", ok=False)  # unknown/unverified item
        self.sw("deploy", "--items", a)                      # D001
        self.sw("deploy", "--items", b)                      # D002
        self.sw("deploy-failed", "D002", "--reason", "500s on checkout")
        fix = self.done_item("Fix checkout", "bugfix", extra=())
        self.sw("set", fix, "fixes=" + b)
        self.sw("deploy", "--items", fix)                    # D003: rework (bugfix with fixes)
        self.sw("deploy-recovered", "D002", "--reason", "D003 fixed it")
        m = json.loads(self.sw("metrics", "--json").stdout)
        self.assertEqual(m["deploys"], 3)
        self.assertAlmostEqual(m["change_failure_rate"], 0.333, places=3)
        self.assertAlmostEqual(m["deployment_rework_rate"], 0.333, places=3)
        self.assertEqual(m["unrecovered_failures"], 0)
        self.assertEqual(m["escaped_defects"], 1)
        self.assertEqual(m["items_done"], 3)
        self.assertIn("median", m["change_lead_time"])
        self.assertIn("Deployment frequency", self.sw("metrics").stdout)

    def test_deploy_records_are_signed(self):
        a = self.done_item("Feature A", "feature")
        self.sw("deploy", "--items", a)
        f = self.root / ".shipwright" / "deploys.jsonl"
        self.assertIn('"mac"', f.read_text())


class SkillStructureTest(unittest.TestCase):
    skill = REPO / "skills" / "shipwright"

    def test_frontmatter(self):
        text = (self.skill / "SKILL.md").read_text()
        m = re.match(r"\A---\nname: (.+)\ndescription: (.+)\n---\n", text)
        self.assertIsNotNone(m, "SKILL.md frontmatter")
        self.assertEqual(m.group(1), "shipwright")
        self.assertTrue(m.group(2).startswith("Use when"))
        self.assertLess(len(m.group(0)), 1024)

    def own_docs(self):
        """Shipwright's own markdown (vendored guides have their own relative references)."""
        for md in self.skill.rglob("*.md"):
            rel = md.relative_to(self.skill)
            if rel.parts[0] != "library" or rel.name == "ROUTING.md":
                yield md

    def test_every_referenced_skill_file_exists(self):
        missing = []
        pat = r"`((?:phases|disciplines|lenses|templates|scripts|library|council)/[\w./-]+)`"
        for md in [*self.own_docs(), *(REPO / "agents").glob("*.md")]:
            for ref in re.findall(pat, md.read_text()):
                if not (self.skill / ref).exists():
                    missing.append(f"{md.name} -> {ref}")
        self.assertEqual(missing, [])

    def test_routing_names_only_vendored_guides(self):
        routing = (self.skill / "library" / "ROUTING.md").read_text()
        cats = [c.name for c in (self.skill / "library").iterdir() if c.is_dir() and c.name.startswith("shipwright_")]
        refs = set(re.findall(r"`((?:" + "|".join(cats) + r")/[\w-]+)`", routing))
        self.assertGreater(len(refs), 60)
        missing = [r for r in refs if not (self.skill / "library" / r / "GUIDE.md").exists()]
        self.assertEqual(missing, [])

    def test_no_nested_skill_md_in_library(self):
        # a nested SKILL.md could be discovered as a separate, competing skill
        self.assertEqual(list((self.skill / "library").rglob("SKILL.md")), [])

    def test_agents_generated_and_in_sync(self):
        r = subprocess.run([sys.executable, str(REPO / "tools" / "build_agents.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        for f in (REPO / "agents").glob("*.md"):
            self.assertRegex(f.read_text(), r"\A---\nname: shipwright-[\w-]+\ndescription: .+\n")

    def test_agents_named_in_skill_exist(self):
        text = " ".join(p.read_text() for p in self.own_docs())
        names = set(re.findall(r"shipwright:(shipwright-[\w-]+)", text))
        self.assertGreaterEqual(len(names), 17)
        missing = [n for n in names if not (REPO / "agents" / f"{n}.md").exists()]
        self.assertEqual(missing, [])

    def test_vendored_guides_are_marked_and_indexed(self):
        guides = list((self.skill / "library").rglob("GUIDE.md"))
        self.assertGreaterEqual(len(guides), 160)
        unmarked = [str(g) for g in guides if "Vendored into Shipwright" not in g.read_text(errors="ignore")[:4000]]
        self.assertEqual(unmarked, [])
        index = (self.skill / "library" / "INDEX.md").read_text()
        empty = [l for l in index.splitlines() if l.startswith("| ") and l.rstrip().endswith("|  |")]
        self.assertEqual(empty, [])
        junk = [p for p in (self.skill / "library").rglob("*") if p.name.endswith(".backup")]
        self.assertEqual(junk, [])

    def test_session_hook_only_speaks_in_shipwright_projects(self):
        hooks = json.loads((REPO / "hooks" / "hooks.json").read_text())
        cmd = hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        with tempfile.TemporaryDirectory() as d:
            env = {"CLAUDE_PROJECT_DIR": d, "PATH": "/usr/bin:/bin"}
            quiet = subprocess.run(["bash", "-c", cmd], env=env, capture_output=True, text=True)
            self.assertEqual((quiet.returncode, quiet.stdout), (0, ""))
            (Path(d) / ".shipwright").mkdir()
            loud = subprocess.run(["bash", "-c", cmd], env=env, capture_output=True, text=True)
            self.assertIn("shipwright.py resume", loud.stdout)

    def test_readme_stays_accurate(self):
        text = (REPO / "README.md").read_text()
        guides = json.loads((self.skill / "library" / "catalog.json").read_text())["guides"]
        missing = [g["guide"] for g in guides if f"`{g['guide'].split('/')[1].removeprefix('shipwright-')}`" not in text]
        self.assertEqual(missing, [], "guides missing from the README explorer")
        self.assertIn(f"badge/guides-{len(guides)}-", text)
        self.assertIn(f"badge/agents-{len(list((REPO / 'agents').glob('*.md')))}-", text)
        tests = len(re.findall(r"^\s+def test_", Path(__file__).read_text(), re.M))
        self.assertIn(f"{tests} tests pass", text)
        slugs = {re.sub(r"[^\w -]", "", h.lower()).replace(" ", "-") for h in re.findall(r"^## (.+)$", text, re.M)}
        self.assertEqual([x for x in re.findall(r'href="#([\w-]+)"', text) if x not in slugs], [])
        self.assertEqual(text.count("<details>"), text.count("</details>"))
        for asset in re.findall(r'src="(assets/[^"]+)"', text):
            self.assertTrue((REPO / asset).is_file(), asset)

    def test_plugin_manifests(self):
        plugin = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text())
        market = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
        self.assertEqual(plugin["name"], "shipwright")
        self.assertEqual(market["plugins"][0]["name"], "shipwright")
        self.assertEqual(market["name"], "shipwright")
        self.assertTrue((REPO / plugin["icon"]).is_file())
        self.assertEqual(plugin["version"], market["plugins"][0]["version"])
        self.assertIn('src="assets/logo.png"', (REPO / "README.md").read_text())

    def test_skill_md_stays_lean(self):
        words = len((self.skill / "SKILL.md").read_text().split())
        self.assertLess(words, 1700, f"SKILL.md is {words} words; move detail into phase files")


if __name__ == "__main__":
    unittest.main()
