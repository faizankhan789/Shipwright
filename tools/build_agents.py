#!/usr/bin/env python3
"""Generate agents/*.md from the skill's lens and discipline files.

The skill files are the single source of truth; agents are generated, never hand-edited, so the
two can never drift apart (a duplicated reviewer prompt that drifted produced a silent
false-clean bug in BMad). `--check` exits 1 if agents/ is out of date (used by the tests).
Usage: python3 tools/build_agents.py [--check]
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "shipwright"
AGENTS = ROOT / "agents"

DISPATCH_NOTE = (
    "Your launch prompt gives absolute paths: the content or plan to work on, and `Skill folder:` "
    "(the shipwright skill). Paths in the instructions below that start with `library/`, `lenses/`, "
    "`disciplines/`, `council/` or `templates/` are relative to that skill folder."
)

REVIEW_TOOLS = "Read, Grep, Glob"
COUNCIL_TOOLS = "Read, Grep, Glob, WebSearch, WebFetch"

# name: (description, tools or None for all, model, preamble, source files)
SPECS = {
    "sw-implementer": (
        "Shipwright implementer: builds one approved Shipwright plan test-first with the smallest diff, "
        "records red/green evidence with sw.py, then reports DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / "
        "BLOCKED. Dispatched by the shipwright skill during Build; give it the plan path and the skill folder.",
        None, "inherit",
        "You are Shipwright's implementer.",
        ["disciplines/implementation.md", "disciplines/tdd.md"],
    ),
    "sw-blind-reviewer": (
        "Shipwright review lens: context-free blind hunter that reads only a diff and lists what is wrong "
        "or missing. Read-only. Dispatched by the shipwright skill during Review.",
        REVIEW_TOOLS, "opus",
        "You are Shipwright's blind-hunter reviewer.",
        ["lenses/blind.md"],
    ),
    "sw-edge-case-reviewer": (
        "Shipwright review lens: exhaustive path tracer that lists unhandled branches, deletions and "
        "falsified plan claims as JSON. Read-only. Dispatched by the shipwright skill during Review.",
        REVIEW_TOOLS, "opus",
        "You are Shipwright's edge-case reviewer.",
        ["lenses/edge-case.md"],
    ),
    "sw-verification-gap-reviewer": (
        "Shipwright review lens: finds changed behavior that could regress without any test failing. "
        "Read-only. Dispatched by the shipwright skill during Review.",
        REVIEW_TOOLS, "opus",
        "You are Shipwright's verification-gap reviewer.",
        ["lenses/verification-gap.md"],
    ),
    "sw-intent-reviewer": (
        "Shipwright review lens: audits whether a diff implements the approved intent, and flags "
        "divergence and unrequested scope. Read-only. Dispatched by the shipwright skill during Review.",
        REVIEW_TOOLS, "opus",
        "You are Shipwright's intent-alignment reviewer.",
        ["lenses/intent-alignment.md"],
    ),
    "sw-ui-reviewer": (
        "Shipwright review lens for UI changes: states, design system, hierarchy, accessibility, "
        "responsiveness, copy, generic-AI look. Read-only. Dispatched by the shipwright skill during Review.",
        REVIEW_TOOLS, "opus",
        "You are Shipwright's UI-craft reviewer.",
        ["lenses/ui-craft.md"],
    ),
    "sw-security-reviewer": (
        "Shipwright review lens for security: traces untrusted input to sinks, auth/authz on new routes, "
        "secrets, dependencies and config. Read-only. Dispatched by the shipwright skill during Review "
        "when a change touches trust boundaries or risk is high.",
        REVIEW_TOOLS, "opus",
        "You are Shipwright's security reviewer.",
        ["lenses/security.md"],
    ),
    "sw-rules-reviewer": (
        "Shipwright review lens: checks a diff against the project's own rules (AGENTS.md, CLAUDE.md, "
        ".shipwright/context.md conventions and pitfalls, accepted ADRs). Read-only. Dispatched by the "
        "shipwright skill on every size-M review.",
        REVIEW_TOOLS, "opus",
        "You are Shipwright's project-rules reviewer.",
        ["lenses/rules.md"],
    ),
    "sw-principal-architect": (
        "Shipwright council member, Principal Solution Architect (20+ years): boundaries, data ownership, contracts, quality-attribute trade-offs (ATAM), C4, Well-Architected review, build vs buy. Argues independently in 3 debate rounds "
        "(position, anonymized critique, revision with dissent). Dispatched by the shipwright council protocol.",
        COUNCIL_TOOLS, "opus",
        "You are a member of Shipwright's design council: Principal Solution Architect (20+ years).",
        ["council/member-rules.md", "council/architect.md"],
    ),
    "sw-ai-engineer": (
        "Shipwright council member, Full-Stack AI Engineer (20+ years): end-to-end buildability, AI pattern choice (call/RAG/tools/agent), evals, guardrails, model cost and latency, walking skeleton. Argues independently in 3 debate rounds "
        "(position, anonymized critique, revision with dissent). Dispatched by the shipwright council protocol.",
        COUNCIL_TOOLS, "opus",
        "You are a member of Shipwright's design council: Full-Stack AI Engineer (20+ years).",
        ["council/member-rules.md", "council/ai-engineer.md"],
    ),
    "sw-staff-engineer": (
        "Shipwright council member, Senior Staff Software Engineer (20+ years): simplicity, correctness hot spots, testability, fit with the existing codebase, migration/rollback, complexity budget. Argues independently in 3 debate rounds "
        "(position, anonymized critique, revision with dissent). Dispatched by the shipwright council protocol.",
        COUNCIL_TOOLS, "opus",
        "You are a member of Shipwright's design council: Senior Staff Software Engineer (20+ years).",
        ["council/member-rules.md", "council/engineer.md"],
    ),
    "sw-design-lead": (
        "Shipwright council member, Senior Product & UI Designer (20+ years): users and jobs, flows, every UI state, accessibility (WCAG 2.1 AA), design system, UX requirements on the backend. Argues independently in 3 debate rounds "
        "(position, anonymized critique, revision with dissent). Dispatched by the shipwright council protocol.",
        COUNCIL_TOOLS, "opus",
        "You are a member of Shipwright's design council: Senior Product & UI Designer (20+ years).",
        ["council/member-rules.md", "council/designer.md"],
    ),
    "sw-red-team": (
        "Shipwright council member, Red Team for reliability, security and cost (20+ years): pre-mortem, attacks on trust boundaries, failure modes, cost at 10x/100x, riskiest assumption. Argues independently in 3 debate rounds "
        "(position, anonymized critique, revision with dissent). Dispatched by the shipwright council protocol.",
        COUNCIL_TOOLS, "opus",
        "You are a member of Shipwright's design council: Red Team for reliability, security and cost (20+ years).",
        ["council/member-rules.md", "council/red-team.md"],
    ),
    "sw-council-judge": (
        "Shipwright council judge: scores the council's options blind against the brief's weighted quality "
        "scenarios, with a reason per score, close calls and the flip assumption. Does not debate. Dispatched "
        "by the shipwright council protocol after round 3.",
        "Read, Grep, Glob", "opus",
        "You are the judge of Shipwright's design council.",
        ["council/judge.md"],
    ),
    "sw-debugger": (
        "Shipwright debugger: finds the root cause of a bug or unexpected failure with the four-phase "
        "method, proves it with a failing test, and reports cause, evidence and the minimal fix. "
        "Dispatched by the shipwright skill.",
        None, "opus",
        "You are Shipwright's debugger. Find the root cause before anything else. Unless your prompt "
        "explicitly asks you to fix it, stop after writing the failing reproduction test and report: the "
        "root cause (file:line), the evidence, the hypotheses you ruled out, and the minimal fix you "
        "recommend. For depth, read `library/debugging/systematic-debugging/GUIDE.md`; for browser, "
        "performance or Android failures, pick the matching `library/debugging/` guide from "
        "`library/ROUTING.md`.",
        ["disciplines/debugging.md"],
    ),
    "sw-ui-designer": (
        "Shipwright UI designer/builder: designs and implements UI for an approved plan using the bundled "
        "design guides (taste-skill, impeccable, interface-design, emil, motion, mobile), then verifies "
        "in a real browser. Dispatched by the shipwright skill for UI tasks.",
        None, "inherit",
        "You are Shipwright's UI designer and builder. You work from an approved plan. Before designing, "
        "read `library/ROUTING.md` and load **one** primary guide for this kind of UI (and at most one "
        "polish or motion guide). The precedence rules there apply to you: take the guides' technique, "
        "not their workflow. Testable logic is built test-first (`disciplines/tdd.md`). Finish with a "
        "status line (DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED), the screenshots you took, "
        "and what you checked.",
        ["disciplines/ui.md"],
    ),
    "sw-investigator": (
        "Shipwright investigator: read-only codebase search that returns a short, plan-ready summary "
        "(files, symbols, what to reuse, what not to touch, covering tests). Dispatched by the shipwright "
        "skill during Clarify.",
        "Read, Grep, Glob, Bash", "sonnet",
        "You are Shipwright's investigator. Your prompt says what to find out. Search the code and the "
        "git history (read-only commands only: no edits, installs or network). Return at most 300 words:\n"
        "- **Files and symbols:** `path:line` with their role\n"
        "- **Reuse:** existing helpers and patterns to follow\n"
        "- **Don't touch:** what must not change, and why\n"
        "- **Tests:** what covers this area today, `path`\n"
        "- **Open:** anything the code cannot answer (these become Open Questions)\n"
        "No narration of the search itself. For an unfamiliar codebase, "
        "`library/coding/codebase-onboarding/GUIDE.md` has a method.",
        [],
    ),
}


def render(name: str) -> str:
    desc, tools, model, preamble, sources = SPECS[name]
    head = ["---", f"name: {name}", f"description: {desc}"]
    if tools:
        head.append(f"tools: {tools}")
    head += [f"model: {model}", "---", "",
             "<!-- GENERATED by tools/build_agents.py from the shipwright skill files. Do not edit. -->", ""]
    body = [preamble, "", DISPATCH_NOTE, ""]
    for src in sources:
        body += [f"<!-- source: skills/shipwright/{src} -->", (SKILL / src).read_text().strip(), ""]
    return "\n".join(head + body).rstrip() + "\n"


def main(argv: list[str]) -> int:
    check = "--check" in argv
    AGENTS.mkdir(exist_ok=True)
    stale = []
    for name in SPECS:
        f = AGENTS / f"{name}.md"
        want = render(name)
        if check:
            if not f.exists() or f.read_text() != want:
                stale.append(f.name)
        else:
            f.write_text(want)
    extra = {p.name for p in AGENTS.glob("*.md")} - {f"{n}.md" for n in SPECS}
    if check:
        if stale or extra:
            print(f"agents out of date: {sorted(stale)} extra: {sorted(extra)}; run tools/build_agents.py")
            return 1
        print("agents up to date")
        return 0
    for e in extra:
        (AGENTS / e).unlink()
    print(f"wrote {len(SPECS)} agents to {AGENTS}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
