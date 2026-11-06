# Library routing

The library bundles 168 specialist guides in 10 categories. Shipwright's own disciplines are
the floor and always apply; a guide adds depth when the work calls for it.

**How to choose (by context, two steps):** read the section map at the top of `library/INDEX.md`, pick the
section that fits the request's meaning, then the guide whose "Use for" line fits. `shipwright.py route "<task>"
--top 5` gives a keyword shortlist as a hint; log your final pick with `route --use <section/guide> --id <item>`.

**The keyword engine:** `shipwright.py route "<task in your own words>" --id <item> --top 5`.
- It matches the whole request against **every** guide in `library/catalog.json` (all 168, by name,
  description and headings, with developer-synonym expansion). The curated rules in `routing.json` add a
  precision boost. It logs `GUIDE:` lines. The prompt hook uses the same engine.
- Treat the result as a ranked shortlist and pick by context. If a better guide is in `INDEX.md`, log your
  own pick: `shipwright.py route --use <section/guide> --id <item>`.

**How to load one:**
1. Read `library/<category>/<name>/GUIDE.md`.
2. Follow only the references it points to that you need. Paths inside a guide are relative to its own folder, and its scripts run from there.
3. `library/INDEX.md` lists every guide with what it is for. Search it when the table below has no row for your situation.

## Categories

| Category | Covers |
|---|---|
| **ui** (31) | art-direction, design-craft, ui-polish, frontend-design, interface-design, Apple feel, mobile UI, motion, Figma-to-code, a11y |
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
   - Process-heavy guides (`shipwright_coding/shipwright-brainstorming`, `shipwright_coding/shipwright-writing-plans`, `shipwright_coding/shipwright-executing-plans`, `shipwright_coding/shipwright-subagent-driven-development`, `shipwright_coding/shipwright-spec-driven-workflow`, `product/*`) are reference material only, inside the matching Shipwright phase.
2. **The project beats taste.** `.shipwright/context.md` and existing code conventions override any guide's defaults.
3. **When guides disagree:**

   | Situation | Winner |
   |---|---|
   | Public or marketing pages | `art-direction` |
   | App screens | `interface-design` |
   | Motion | `animate` |
   | Debugging | `systematic-debugging` |
   | Tests | `test-driven-development` |

   Record a choice once in context.md (for example, the elevation style), then keep to it.

   Two specifics:
   - art-direction also claims app screens. For dashboards and tools, `interface-design` still wins.
   - design-craft's `DESIGN.md` / `PRODUCT.md` may serve as the design-system source; context.md links to them.

   Working folders that guides create (hidden scratch folders) are scratch space and are kept out of review diffs.
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
| Unfamiliar or large codebase | Clarify | `shipwright_coding/shipwright-codebase-onboarding`, `shipwright_coding/shipwright-code-tour`, `shipwright_coding/shipwright-monorepo-navigator` |
| Vague idea that needs shaping (L) | Frame | `shipwright_coding/shipwright-brainstorming` (questions only) |
| Copy or beat an existing product (L) | Frame | `shipwright_product/shipwright-build-from-best`, `shipwright_product/shipwright-reverse-engineer-anything`, `shipwright_product/shipwright-replica-recon` |
| Schema, migrations, data model | Frame / Plan | `shipwright_backend_infra/shipwright-database-designer`, `shipwright_backend_infra/shipwright-database-schema-designer`, `shipwright_coding/shipwright-migration-architect` |
| API design | Frame / Plan | `shipwright_backend_infra/shipwright-api-design-reviewer` |
| Feature flags or a risky rollout | Plan | `shipwright_coding/shipwright-feature-flags-architect` |
| **Build** | | |
| Tests, mocks, test design | Build | `shipwright_coding/shipwright-test-driven-development` |
| Keeping diffs surgical | Build | `shipwright_coding/shipwright-surgical-change-guidelines`, `shipwright_coding/shipwright-surgical-coding` |
| SQL | Build | `shipwright_backend_infra/shipwright-sql-database-assistant` |
| Containers, CI/CD, Kubernetes, Helm, Terraform | Build | `shipwright_backend_infra/shipwright-docker-development`, `shipwright_backend_infra/shipwright-ci-cd-pipeline-builder`, `shipwright_backend_infra/shipwright-kubernetes-operator`, `shipwright_backend_infra/shipwright-helm-chart-builder`, `shipwright_backend_infra/shipwright-terraform-patterns` |
| Observability, SLOs, runbooks | Build | `shipwright_backend_infra/shipwright-observability-designer`, `shipwright_backend_infra/shipwright-slo-architect`, `shipwright_backend_infra/shipwright-runbook-generator` |
| MCP server | Build | `shipwright_backend_infra/shipwright-mcp-server-builder` |
| RAG, agents, LLM cost | Build | `shipwright_ai_ml/shipwright-rag-implementation`, `shipwright_ai_ml/shipwright-rag-architect`, `shipwright_ai_ml/shipwright-agent-designer`, `shipwright_ai_ml/shipwright-llm-cost-optimizer` |
| Hugging Face models, training, Spaces | Build | `shipwright_ai_ml/shipwright-huggingface-best` first, then the specific `shipwright_ai_ml/shipwright-huggingface-*` / `shipwright_ai_ml/shipwright-trl-training` guide |
| Payments with Stripe | Plan → Build | `shipwright_integrations/shipwright-stripe-best-practices`, `shipwright_integrations/shipwright-stripe-docs` |
| Android / Kotlin / Compose | Build | `shipwright_mobile/shipwright-android-dev` (router), `shipwright_mobile/shipwright-compose`, `shipwright_mobile/shipwright-kotlin-coroutines`, `shipwright_mobile/shipwright-android-data-layer`, `shipwright_mobile/shipwright-koin` |
| Swift / iOS | Build | `shipwright_mobile/shipwright-write-swift` |
| Parallel slices | Build (L) | `shipwright_coding/shipwright-dispatching-parallel-agents`, `shipwright_coding/shipwright-using-git-worktrees` |
| **UI** | | |
| Public page: landing, marketing, portfolio | Plan → Build → Verify | `shipwright_ui/shipwright-art-direction` |
| App screens: dashboard, admin, settings | Plan → Build | `shipwright_ui/shipwright-interface-design` |
| Any UI: craft, critique, audit, polish | Build → Review | `shipwright_ui/shipwright-design-craft` |
| Aesthetic direction for new UI | Plan | `shipwright_ui/shipwright-frontend-design` |
| Final polish, component feel | Build → Review | `shipwright_ui/shipwright-ui-polish` |
| Mobile screens | Plan → Build | `shipwright_ui/shipwright-mobile-app-ui-design`, `shipwright_ui/shipwright-mobile-native`, `shipwright_mobile/shipwright-android-ux` |
| Gestures, springs, iOS feel | Build | `shipwright_ui/shipwright-fluid-motion-design` |
| Choosing a component library | Plan | `shipwright_ui/shipwright-pick-ui-library` |
| Toasts (Sonner) | Build | `shipwright_ui/shipwright-ask-sonner` |
| Throwaway prototype or spike | Clarify | `shipwright_ui/shipwright-prototype` |
| Figma file to code | Build | `shipwright_ui/shipwright-figma-design-to-code`, `shipwright_ui/shipwright-figma-code-connect`, `shipwright_ui/shipwright-figma-implement-motion` |
| Building motion | Build | `shipwright_ui/shipwright-animate`, `shipwright_ui/shipwright-animate-expo` (Expo/React Native) |
| Janky animation | Build | `shipwright_ui/shipwright-animation-performance` |
| **Debug** | | |
| Any bug or unexpected failure | Clarify → Build | `shipwright_debugging/shipwright-systematic-debugging` |
| Failure spread across a module | Build | `shipwright_debugging/shipwright-focused-fix` |
| Slow code, memory, bundle size | Build | `shipwright_debugging/shipwright-performance-profiler`, `shipwright_debugging/shipwright-memory-leak-debugging` |
| Browser bugs, LCP, cookies, a11y tree | Build | `shipwright_debugging/shipwright-chrome-devtools`, `shipwright_debugging/shipwright-debug-optimize-lcp`, `shipwright_debugging/shipwright-cookie-debugging`, `shipwright_debugging/shipwright-a11y-debugging` |
| Android crashes and ANRs | Build | `shipwright_debugging/shipwright-android-debugging` |
| **Review and verify** | | |
| Extra lens on high-risk change | Review | `shipwright_coding/shipwright-pr-review-expert` |
| Security-sensitive change (auth, input, secrets, payments) | Review | `shipwright_security/shipwright-security-guidance`, `shipwright_security/shipwright-owasp-top-10-testing`, `shipwright_security/shipwright-find-security-vulnerabilities-in-code` |
| Dependency or secret hygiene | Review | `shipwright_security/shipwright-dependency-auditor`, `shipwright_security/shipwright-env-secrets-manager`, `shipwright_security/shipwright-secrets-vault-manager` |
| Pentest an app you own (authorized) | Verify | `shipwright_security/shipwright-penetration-testing-with-strix`, `shipwright_security/shipwright-web-app-penetration-testing`, `shipwright_security/shipwright-api-security-testing` |
| Accessibility audit | Review | `shipwright_ui/shipwright-a11y-audit` |
| UI with worst-case data | Review | `shipwright_ui/shipwright-break-ui` |
| Motion review | Review | `shipwright_ui/shipwright-review-animations`, `shipwright_ui/shipwright-improve-animations` |
| API or e2e test suites | Build → Verify | `shipwright_testing/shipwright-api-test-suite-builder`, `shipwright_testing/shipwright-browser-automation` |
| Resilience | Verify | `shipwright_testing/shipwright-chaos-engineering` |
| About to claim success | Verify | `shipwright_coding/shipwright-verification-before-completion`, `shipwright_coding/shipwright-ship-gate`, `shipwright_coding/shipwright-self-eval` |
| Human or PR feedback | Review | `shipwright_coding/shipwright-receiving-code-review` |
| **Ship** | | |
| Merge or PR, when the human asks | Ship | `shipwright_coding/shipwright-finishing-a-development-branch` |
| Changelog or release | Ship | `shipwright_coding/shipwright-changelog-generator`, `shipwright_coding/shipwright-release-manager` |
| Recording debt | Learn | `shipwright_coding/shipwright-tech-debt-tracker` |
