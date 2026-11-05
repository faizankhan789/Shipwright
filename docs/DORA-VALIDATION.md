# Shipwright against DORA

DORA (DevOps Research and Assessment, Google Cloud) is the largest long-running research program
on software delivery performance. This report checks Shipwright two ways:

1. **By design:** each DORA metric and capability is mapped to the plugin mechanism that moves it, with the gaps stated.
2. **By measurement:** `shipwright.py metrics` computes the five DORA metrics from the plugin's own signed records, so the effect can be measured on real projects rather than claimed.

**Status: the design is validated; the outcomes are not yet measured.** No project has run Shipwright long
enough to produce DORA numbers. The measurement plan is in the last section.

## The five DORA metrics (2024+ model)

| Group | Metric | What it is | How Shipwright records it |
|---|---|---|---|
| Throughput | Change lead time | Time from change to production | First build → `shipwright.py deploy` |
| Throughput | Deployment frequency | Deploys per period | `shipwright.py deploy` records |
| Throughput | Failed deployment recovery time | Time from a failed deploy to restored service | `deploy-failed` → `deploy-recovered` |
| Instability | Change failure rate | Share of deploys that cause a failure needing remediation | `deploy-failed` / deploys |
| Instability | Deployment rework rate | Share of deploys that are unplanned fixes for incidents | `--rework`, or auto when every deployed item is a bugfix with `fixes:` |

The deploy log is append-only, hash-chained and signed, and the guard hook blocks hand edits.
Lead time is measured from the first build, a proxy for DORA's "commit to production": Shipwright
items start building at their first change.

## How the design moves each metric

| Metric | Mechanisms that improve it | Risk it adds | Net expectation |
|---|---|---|---|
| **Change failure rate** | Red-then-green tests, recorded with signatures and tied to the plan's test runner. Evidence fingerprinted to the exact code. 7 context-free review lenses, including security and project rules. Clean-tree baseline. Frozen acceptance criteria. UI screenshot gate | None | **Strong improvement.** This is the plugin's core purpose |
| **Deployment rework rate** | The same quality gates. Escaped defects are linked to shipped work with `fixes:`, so they become visible | None | Improvement |
| **Change lead time** | Small single-goal plans (900–1600 tokens). An S path for small work. Parallel agents. Plans and decisions resume across sessions | Planning, review and council add time per change | **Mixed.** Slower per change, fewer reworked changes. Measure it |
| **Deployment frequency** | Vertical slices with a walking skeleton first. Small batches. Each item is mergeable on its own | Does not deploy; depends on the project's CI/CD | Enables it, doesn't drive it |
| **Failed deployment recovery time** | Root-cause debugging discipline, defense-in-depth, rollback and migration planning in the council's Delivery section, failure and recovery records | No automated rollback or incident tooling | Partial |

**Why this matters for AI-assisted teams:** the DORA 2024 and 2025 research reports that AI adoption
raises delivery throughput while hurting stability (more change failures and rework). Shipwright puts
its enforcement on the stability side: tests, evidence, review, and frozen intent.

## DORA AI Capabilities Model (2025)

| Capability | Shipwright | Rating |
|---|---|---|
| Clear and communicated AI stance | Not an org policy, but the plugin makes the AI's process explicit and auditable (laws, gates, approvals with named approvers) | Partial (org responsibility) |
| Healthy data ecosystems | Out of scope | — |
| AI-accessible internal data | Investigator agent, context.md, ADRs, plans and the project-rules lens give agents company-specific context | Strong |
| Strong version control practices | Clean-tree baseline, a recorded baseline commit, diff-based review, evidence tied to the tree, deploy records with refs. Commits only when asked | Strong |
| Working in small batches | Single-goal plans with a token budget, S/M/L sizing, slices, and a forced review for oversized S items | Strong |
| User-centric focus | Design lead in the council, jobs-to-be-done and flows, ACs tested at the user's surface, UI states and accessibility floor | Strong |
| Quality internal platforms | One plugin with shared gates and guardrails across projects | Partial |

## Classic DORA capabilities

| Capability | Shipwright | Rating |
|---|---|---|
| Version control | Baselines, diffs, refs | Strong |
| Test automation | Required test commands, red/green evidence, verification-gap lens | Strong |
| Small batches | Plan budget, slices, S path | Strong |
| Streamlined change approval (peer review, not a change board) | Automated parallel lenses plus one human approval | Strong |
| Documentation quality | Plans, ADRs, context.md, decision.md, all in the repo | Strong |
| Loosely coupled architecture | Council on boundaries and contracts, architecture template | Strong (by design) |
| Monitoring and observability | Well-Architected review in decisions; observability guides in the library | Partial |
| Continuous integration | Runs the project's checks; doesn't create CI (`library/shipwright_backend_infra/shipwright-ci-cd-pipeline-builder` can) | Partial |
| Trunk-based development | Not enforced | Gap |
| Deployment automation | Not provided | Gap (out of scope) |

## Measurement plan (turning design into evidence)

1. **Record every production deploy:** `shipwright.py deploy --items <ids>`. On an incident, `shipwright.py deploy-failed <D>`, then
   `deploy-recovered <D>` once service is restored. Link fix items with `shipwright.py set <fix> fixes=<id>`.
2. **Baseline:** 30 days on a project or team without Shipwright, using the same definitions (from CI/CD history).
3. **Treatment:** 30 days with Shipwright, then `shipwright.py metrics --days 30`.
4. **Judge by the pair.** Stability (change failure rate and rework rate) should drop without lead time rising more than the rework saved. Watch the leading indicators every week:
   - batch size
   - review loopbacks per item
   - escaped defects
5. **Report it in the initiative retro.** If change failure rate doesn't fall, the gates aren't biting. Read `shipwright.py friction` and the triage logs to find out why.

## Sources

- DORA metrics and their grouping: [DORA metrics guide](https://coralogix.com/guides/dora-metrics/), [Swarmia: DORA metrics](https://help.swarmia.com/metrics-and-definitions/dora-metrics), [2025 benchmarks summary](https://rdel.substack.com/p/rdel-115-what-are-the-2025-benchmarks)
- 2025 report and AI findings: [DORA 2025 report](https://cloud.google.com/resources/content/2025-dora-ai-assisted-software-development-report), [Google: inside the 2025 DORA report](https://blog.google/technology/developers/dora-report-2025/), [Splunk review](https://www.splunk.com/en_us/blog/learn/state-of-devops.html)
- AI Capabilities Model: [Introducing DORA's AI Capabilities Model](https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model), [dora.dev capabilities](https://dora.dev/capabilities/clear-and-communicated-ai-stance/)
