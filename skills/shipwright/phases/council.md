# Council: expert debate for high-stakes decisions

Five senior members debate a decision in rounds. You, the moderator, run the protocol and make
the final call. The protocol follows what multi-agent debate research found works:

| Research finding | What the protocol does |
|---|---|
| Debate improves reasoning and factuality | Members answer independently first, then read each other and revise |
| Gains level off after about 3 rounds | Exactly 3 rounds |
| Debates fail through sycophancy and conformity | Anonymous positions; change only with evidence; a dedicated red team; dissent recorded |
| A central judge is robust | An independent judge scores the options against a rubric; the moderator decides with the scores, never by majority vote |
| Weaker agents drag the group down | Every member runs on the strongest model |
| Multi-agent costs about 15× the tokens | Convene only when the decision is worth it |

## When to convene

- **Required:** size L (in Frame), a design-only request ("design / architect / plan a solution for X"), and any decision that is hard to reverse:
  - data model or store
  - service boundaries
  - auth model
  - AI pattern (RAG, agent, or fine-tune)
  - a vendor lock-in
- **Optional:** an M item with risk high, when there is more than one credible approach. Use the reduced council: architect, engineer, red team.
- **Never:** S items, or decisions the code already settles. Answer those from the code.

## Members

| Agent | Owns |
|---|---|
| `shipwright:shipwright-principal-architect` | Boundaries, data, contracts, quality trade-offs, Well-Architected |
| `shipwright:shipwright-ai-engineer` | Buildability end to end; AI pattern, evals, guardrails, cost |
| `shipwright:shipwright-staff-engineer` | Simplicity, correctness, testability, fit with the codebase, delivery |
| `shipwright:shipwright-design-lead` | Users, flows, states, accessibility, design system |
| `shipwright:shipwright-red-team` | Pre-mortem, attacks on security, reliability, cost and assumptions |
| `shipwright:shipwright-council-judge` | Not a debater. After round 3 it scores the options blind, against the brief's quality scenarios |

Drop the design lead when there is no user-facing surface, and the AI engineer when there is no
AI and no full-stack slice. Say which members you dropped and why. Without the plugin agents,
use general-purpose subagents told to read `council/member-rules.md` plus their persona file.

## Protocol

**0. Prepare** (you, the moderator):
1. Run `SW council new "<decision question>"`.
2. Fill in `brief.md` from Clarify or Frame: the problem, users, constraints, quality scenarios, the options already known, and the evidence paths.
3. Run `SW council check <slug>` until the brief passes.

**Labels:** before round 1, assign each member a random letter (A, B, C, ...) and keep that
mapping in your head, never in the council folder, until step 5. Members return text; **you**
save every round as `round-N/<letter>.md`, so no file on disk names a member.

**1. Independent positions** (in parallel, in one turn):
- Launch every member with: "Round 1. Council folder: `<abs>`. Read `brief.md`. Return your position. Skill folder: `<skill>`."
- Save each reply to `round-1/<letter>.md`. No member sees another's position.

**2. Critique:**
1. Write `round-2/input.md`: every round-1 position as `Position A`, `Position B`, ... with no names or roles.
2. Resume each member (SendMessage to its id), or start a fresh one: "Round 2. Read `round-2/input.md` (your own is among them). Return your critique."
3. Save each reply to `round-2/<letter>.md`.

**3. Revise:**
1. Write `round-3/input.md` with the round-2 critiques, anonymized the same way.
2. Each member returns its revised position ending in `## Dissent`. Save it to `round-3/<letter>.md`.

**4. Judge, then decide:**
1. Dispatch `shipwright:shipwright-council-judge` with the brief, the option list, and `round-3/input.md` (anonymized).
   It returns a weighted score matrix with a reason per score. Save that output as `judge.md`.
2. Then fill in `decision.md` from `templates/solution-design.md`. Put the judge's matrix in `## Evaluation`.
- **Options:** at least 2 fundamentally different ones, plus "do nothing" or "buy" when relevant. Each gets its real strengths, not a strawman.
- **Evaluation:** score every option against the brief's quality scenarios. Weight the scenarios by the brief's priorities. The highest score doesn't win automatically: explain the call.
- **Arguments:** judge by evidence, never by how many members said something or how confident they sounded.
- **Dissent:** record every unresolved disagreement, with its trigger condition (when the dissent would turn out to be right).
- **Red-team holes:** each one is either closed by a design change, or accepted as a risk with an owner and a mitigation.
- **ADRs:** each irreversible decision gets `SW adr`.

**5. Key and check:**
1. Write `key.md`, mapping each label to its member (`- A: shipwright-red-team`).
2. Run `SW council check <slug>`. It refuses unless:
   - the brief is complete, with 3+ quality scenarios
   - every round has the same 3+ anonymous members
   - round 3 includes Dissent
   - the input files name no member or role
   - the key and the judge's matrix (`judge.md`) exist
   - the decision has 2+ described options, numeric scores, and non-empty sections

**For size L,** add `Council: <council folder>` to `architecture.md`. `SW initiative-check <slug>`
then requires the council to pass and every brief requirement to be covered by a slice, before
any slice can be marked `ready`.

**6. Present** (interactive): the decision, the main trade-off, the strongest dissent, and the
top risks. The human approves, or sends it back with new constraints, which restarts from round 1.

**Next:** the decision feeds `architecture.md` and the slices (Frame), or the plan's Intent and
Design Notes (M). A design-only request stops here, and its deliverable is `decision.md`.
