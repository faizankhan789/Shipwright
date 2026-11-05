# Library routing

The library bundles 168 specialist guides in 10 categories. Shipwright's own disciplines are
the floor and always apply; a guide adds depth when the work calls for it.

**How to load one:**
1. Read `library/<category>/<name>/GUIDE.md`.
2. Follow only the references it points to that you need. Paths inside a guide are relative to its own folder, and its scripts run from there.
3. `library/INDEX.md` lists every guide with what it is for. Search it when the table below has no row for your situation.

## Categories

| Category | Covers |
|---|---|
| **ui** (31) | taste-skill, impeccable, emil, frontend-design, interface-design, Apple feel, mobile UI, motion, Figma-to-code, a11y |
| **coding** (26) | TDD, verification, code review, plans, parallel agents, worktrees, onboarding, migrations, flags, releases |
| **debugging** (11) | systematic debugging, focused-fix, performance, Chrome DevTools, Android debugging |
| **testing** (5) | API suites, browser automation, chaos |
| **security** (13) | OWASP, Strix pentesting, secrets, dependencies |
| **mobile** (23) | Android, Kotlin, Compose, KMP, Swift |
| **backend-infra** (13) | APIs, databases, SQL, Docker, CI/CD, Kubernetes, Terraform, observability, MCP servers |
| **ai-ml** (24) | RAG, agents, Hugging Face |
| **integrations** (9) | Stripe, Firecrawl |
| **product** (13) | build-from-best and the replica-* app-building chain |

## Precedence (read before loading any guide)

1. **Shipwright owns the process.**
   - Its laws, gates, phases, statuses, and "commit only when asked" override any process instruction inside a guide: its own interview, plan format, ledger, mandatory skill loading, hook setup, or commit/PR/deploy steps.
   - Take a guide's *technique*, not its *workflow*.
   - Process-heavy guides (`coding/brainstorming`, `coding/writing-plans`, `coding/executing-plans`, `coding/subagent-driven-development`, `coding/spec-driven-workflow`, `product/*`) are reference material only, inside the matching Shipwright phase.
2. **The project beats taste.** `.shipwright/context.md` and existing code conventions override any guide's defaults.
3. **When guides disagree:**

   | Situation | Winner |
   |---|---|
   | Public or marketing pages | `taste-skill` |
   | App screens | `interface-design` |
   | Motion | `animate` |
   | Debugging | `systematic-debugging` |
   | Tests | `test-driven-development` |

   Record a choice once in context.md (for example, the elevation style), then keep to it.

   Two specifics:
   - taste-skill also claims app screens. For dashboards and tools, `interface-design` still wins.
   - impeccable's `DESIGN.md` / `PRODUCT.md` may serve as the design-system source; context.md links to them.

   Working folders that guides create (`.taste-skill/`, `.impeccable/`) are scratch space and are kept out of review diffs.
4. **Load little.**
   - At most one primary guide, plus one supporting guide per task. Never a whole category.
   - Read a guide's main file first, and open its references only when a step needs them.
5. **Tools and accounts.**
   - Some guides drive external tools: Strix, Figma, Chrome DevTools, Stripe, Hugging Face, Firecrawl.
   - Use them only when that tool is available and the human has authorized it.
   - Security scanners may only target what the human owns or has explicit permission to test.
6. **Missing guide:** use the installed skill with the same name if there is one. Otherwise the Shipwright floor applies alone.

## Default picks

| Situation | Phase | Guide(s) |
|---|---|---|
| **Understand and plan** | | |
| Unfamiliar or large codebase | Clarify | `coding/codebase-onboarding`, `coding/code-tour`, `coding/monorepo-navigator` |
| Vague idea that needs shaping (L) | Frame | `coding/brainstorming` (questions only) |
| Copy or beat an existing product (L) | Frame | `product/build-from-best`, `product/reverse-engineer-anything`, `product/replica-recon` |
| Schema, migrations, data model | Frame / Plan | `backend-infra/database-designer`, `backend-infra/database-schema-designer`, `coding/migration-architect` |
| API design | Frame / Plan | `backend-infra/api-design-reviewer` |
| Feature flags or a risky rollout | Plan | `coding/feature-flags-architect` |
| **Build** | | |
| Tests, mocks, test design | Build | `coding/test-driven-development` |
| Keeping diffs surgical | Build | `coding/karpathy-guidelines`, `coding/karpathy-coder` |
| SQL | Build | `backend-infra/sql-database-assistant` |
| Containers, CI/CD, Kubernetes, Helm, Terraform | Build | `backend-infra/docker-development`, `backend-infra/ci-cd-pipeline-builder`, `backend-infra/kubernetes-operator`, `backend-infra/helm-chart-builder`, `backend-infra/terraform-patterns` |
| Observability, SLOs, runbooks | Build | `backend-infra/observability-designer`, `backend-infra/slo-architect`, `backend-infra/runbook-generator` |
| MCP server | Build | `backend-infra/mcp-server-builder` |
| RAG, agents, LLM cost | Build | `ai-ml/rag-implementation`, `ai-ml/rag-architect`, `ai-ml/agent-designer`, `ai-ml/llm-cost-optimizer` |
| Hugging Face models, training, Spaces | Build | `ai-ml/huggingface-best` first, then the specific `ai-ml/huggingface-*` / `ai-ml/trl-training` guide |
| Payments with Stripe | Plan → Build | `integrations/stripe-best-practices`, `integrations/stripe-docs` |
| Android / Kotlin / Compose | Build | `mobile/android-dev` (router), `mobile/compose`, `mobile/kotlin-coroutines`, `mobile/android-data-layer`, `mobile/koin` |
| Swift / iOS | Build | `mobile/write-swift` |
| Parallel slices | Build (L) | `coding/dispatching-parallel-agents`, `coding/using-git-worktrees` |
| **UI** | | |
| Public page: landing, marketing, portfolio | Plan → Build → Verify | `ui/taste-skill` |
| App screens: dashboard, admin, settings | Plan → Build | `ui/interface-design` |
| Any UI: craft, critique, audit, polish | Build → Review | `ui/impeccable` |
| Aesthetic direction for new UI | Plan | `ui/frontend-design` |
| Final polish, component feel | Build → Review | `ui/emil-design-eng` |
| Mobile screens | Plan → Build | `ui/mobile-app-ui-design`, `ui/mobile-native`, `mobile/android-ux` |
| Gestures, springs, iOS feel | Build | `ui/apple-design` |
| Choosing a component library | Plan | `ui/pick-ui-library` |
| Toasts (Sonner) | Build | `ui/ask-sonner` |
| Throwaway prototype or spike | Clarify | `ui/prototype` |
| Figma file to code | Build | `ui/figma-design-to-code`, `ui/figma-code-connect`, `ui/figma-implement-motion` |
| Building motion | Build | `ui/animate`, `ui/animate-expo` (Expo/React Native) |
| Janky animation | Build | `ui/animation-performance` |
| **Debug** | | |
| Any bug or unexpected failure | Clarify → Build | `debugging/systematic-debugging` |
| Failure spread across a module | Build | `debugging/focused-fix` |
| Slow code, memory, bundle size | Build | `debugging/performance-profiler`, `debugging/memory-leak-debugging` |
| Browser bugs, LCP, cookies, a11y tree | Build | `debugging/chrome-devtools`, `debugging/debug-optimize-lcp`, `debugging/cookie-debugging`, `debugging/a11y-debugging` |
| Android crashes and ANRs | Build | `debugging/android-debugging` |
| **Review and verify** | | |
| Extra lens on high-risk change | Review | `coding/pr-review-expert` |
| Security-sensitive change (auth, input, secrets, payments) | Review | `security/security-guidance`, `security/owasp-top-10-testing`, `security/find-security-vulnerabilities-in-code` |
| Dependency or secret hygiene | Review | `security/dependency-auditor`, `security/env-secrets-manager`, `security/secrets-vault-manager` |
| Pentest an app you own (authorized) | Verify | `security/penetration-testing-with-strix`, `security/web-app-penetration-testing`, `security/api-security-testing` |
| Accessibility audit | Review | `ui/a11y-audit` |
| UI with worst-case data | Review | `ui/break-ui` |
| Motion review | Review | `ui/review-animations`, `ui/improve-animations` |
| API or e2e test suites | Build → Verify | `testing/api-test-suite-builder`, `testing/browser-automation` |
| Resilience | Verify | `testing/chaos-engineering` |
| About to claim success | Verify | `coding/verification-before-completion`, `coding/ship-gate`, `coding/self-eval` |
| Human or PR feedback | Review | `coding/receiving-code-review` |
| **Ship** | | |
| Merge or PR, when the human asks | Ship | `coding/finishing-a-development-branch` |
| Changelog or release | Ship | `coding/changelog-generator`, `coding/release-manager` |
| Recording debt | Learn | `coding/tech-debt-tracker` |
