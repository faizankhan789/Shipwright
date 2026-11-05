# Shipwright (Claude Code plugin)

One plugin that takes a feature, bug fix, refactor, or whole product from intent to verified,
reviewed code. It contains:
- **One skill** (`shipwright`) that owns the workflow.
- **17 internal agents:** a 5-member expert council that debates architecture decisions, an independent council judge, an implementer, a UI designer, a debugger, an investigator, and seven review lenses.
- **2 hooks:** a session-start reminder to resume open work, and a guard that blocks hand-edits to evidence, logs, and plan gate fields.
- **168 bundled specialist guides:** UI/design, coding, debugging, testing, security, mobile,
  backend/infra, AI/ML, integrations, and app-building. They load only when a phase needs them.

It brings together, in one workflow:
- **Planning:** plans and decisions on disk, frozen human-owned intent, an Open Questions gate, sized
  routing, ADRs and retrospectives.
- **Building:** test-first development, root-cause debugging, and evidence before "done".
- **Reviewing:** parallel context-free review with a verdict on every finding, and honest handling of
  feedback.
- **Orchestration and UI:** subagent orchestration, and a UI craft and accessibility floor.

The prose gates are backed by a stdlib-only script (`shipwright.py`) that refuses unsafe status changes.

## Layout

```
.claude-plugin/plugin.json        plugin manifest
.claude-plugin/marketplace.json   local marketplace ("shipwright-local") listing this plugin
agents/                           17 agents, GENERATED from the skill's council/lens/discipline files
hooks/hooks.json                  SessionStart resume nudge + PreToolUse guard
hooks/guard_state.py              blocks hand-edits to evidence, logs and plan gate fields
skills/shipwright/
  SKILL.md                        entry: laws, sizing, phases, agents, library, modes, red flags
  phases/                         clarify, frame (L), council (L/D), plan, build, review, ship (+ learn)
  council/                        member rules + 5 expert personas
  disciplines/                    tdd, debugging, verification, feedback, ui
  lenses/                         blind, edge-case, verification-gap, intent-alignment, rules, ui-craft, security
  templates/                      plan-S, plan-M, brief, architecture, adr, context, council-brief, solution-design, implementer-prompt
  scripts/shipwright.py                   state + gates CLI (Python 3.9+, no dependencies)
  library/
    ROUTING.md                    which guide for which situation + precedence rules
    INDEX.md                      every guide with its purpose (generated)
    ui/ coding/ debugging/ testing/ security/ mobile/ backend-infra/ ai-ml/ integrations/ product/
tools/build_agents.py             regenerates agents/ from the skill files (--check verifies sync)
docs/DORA-VALIDATION.md          DORA metrics + AI Capabilities Model validation and measurement plan
tests/test_shipwright.py                  68 tests: every gate and every loophole found in two audits, the evidence fingerprint, the council and initiative checks, the guard hook, structure, agents, manifests
evals/cases.json                  trigger + behavior cases for measuring the plugin with real runs
```

## Expert council (solution architecture)

For problem analysis and solution architecture (size L, design-only requests, and high-stakes
decisions), five senior personas debate the decision in three rounds:

1. independent positions
2. anonymized critique
3. revision with recorded dissent

The members are a **principal solution architect**, a **full-stack AI engineer**, a **senior
staff engineer**, a **senior product/UI designer**, and a **red team**. The moderator decides by
a weighted quality-scenario matrix, never by vote, and writes `decision.md`. That is the solution
design, with options, trade-off points, C4 views, a Well-Architected review, risks, and dissent.
`shipwright.py council check` enforces the full record.

The protocol is built on published findings:
- **Multi-agent debate improves reasoning and factuality,** with diminishing returns after about 3 rounds ([Du et al.](https://arxiv.org/abs/2305.14325)).
- **Debate fails through sycophancy and conformity** ([2509.23055](https://arxiv.org/abs/2509.23055), [2510.07517](https://arxiv.org/html/2510.07517v4)). Hence anonymized positions, "change only with evidence", a dedicated red team, and a central judge.
- **Weaker agents degrade debate** ([2509.05396](https://arxiv.org/abs/2509.05396v2)). All members run on the strongest model.
- **Multi-agent systems cost about 15× the tokens and suit high-value, parallel work** ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)). The council is only for decisions worth it.
- **Architecture method:** quality scenarios and trade-off points ([arc42](https://docs.arc42.org/tips/10-8/), [ATAM](https://cio-wiki.com/wiki/Architecture_Tradeoff_Analysis_Method_(ATAM))), real alternatives ([design docs/RFCs](https://blog.pragmaticengineer.com/rfcs-and-design-docs/)), and Well-Architected pillars ([Azure](https://learn.microsoft.com/en-gb/azure/well-architected), [Google Cloud](https://docs.cloud.google.com/architecture/framework)).

## DORA metrics

`shipwright.py deploy`, `deploy-failed` and `deploy-recovered` record production deploys and incidents in a signed log.
`shipwright.py metrics` then reports the five DORA metrics:
- **Throughput:** deployment frequency, change lead time, failed-deployment recovery time.
- **Instability:** change failure rate, deployment rework rate.

It also reports Shipwright's leading indicators: batch size, review loopbacks, and escaped defects.

`docs/DORA-VALIDATION.md` maps every DORA metric, the 2025 AI Capabilities Model, and the classic
capabilities to the plugin's mechanisms, with the gaps stated and a 30-day measurement plan.

## Agents

| Agent | Role |
|---|---|
| `shipwright-principal-architect`, `shipwright-ai-engineer`, `shipwright-staff-engineer`, `shipwright-design-lead`, `shipwright-red-team` | Council members (20+ years personas) debating in 3 anonymized rounds |
| `shipwright-council-judge` | Scores the options blind against weighted quality scenarios; does not debate |
| `shipwright-investigator` | Read-only code search; returns a plan-ready summary |
| `shipwright-implementer` | Builds one approved plan test-first; reports DONE / CONCERNS / NEEDS_CONTEXT / BLOCKED |
| `shipwright-ui-designer` | Builds UI with the bundled design guides; verifies in a browser |
| `shipwright-debugger` | Four-phase root-cause analysis; failing repro test |
| `shipwright-blind-reviewer`, `shipwright-edge-case-reviewer`, `shipwright-verification-gap-reviewer`, `shipwright-intent-reviewer`, `shipwright-rules-reviewer`, `shipwright-ui-reviewer`, `shipwright-security-reviewer` | Context-free, read-only review lenses |

The agents are generated from `skills/shipwright/lenses/*.md` and `disciplines/*.md`, so the
skill and the agents can never drift apart. After editing a lens or discipline, run
`python3 tools/build_agents.py`.

## Installing (you run these)

From Claude Code:

```text
/plugin marketplace add <absolute path to this folder>
/plugin install shipwright@shipwright-local
```

**To keep one workflow in charge:**
- Disable any standalone plugins and skills whose content Shipwright now bundles. They would
  otherwise trigger alongside it.
- Remove session hooks that force-load other process skills (brainstorming, build-from-best, the
  design-skill autoload).

## Maintaining

```bash
python3 ~/.shipwright-build/vendor.py --plugin .  # rebuild the library (private build tooling, kept outside this repo)
python3 tools/build_agents.py                    # regenerate agents after editing lenses/disciplines
python3 -m unittest discover -s tests -v         # 68 tests
claude plugin validate .                         # manifest check
```

## License

Shipwright is licensed under the **Shipwright License** (see [LICENSE](LICENSE)).
Third-party material it includes is listed, with the notices its licenses require, in
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

## Where the design came from

A rubric audit (12 dimensions, 0–10, with file and line evidence) compared two existing AI delivery
workflows, at 68% and 63%. Shipwright takes the best of each dimension. It targets the two lowest
scores, coherence and enforcement, with one workflow owner and script gates.

A trial run on a real feature (size M, auto mode) reached `done` with 4 review lenses and 18
triaged findings. Its 13 friction points have been fixed.

Those numbers are design targets plus one trial, not a benchmark. To measure the plugin, run
the cases in `evals/cases.json` with and without it (`claude plugin eval` is available).
