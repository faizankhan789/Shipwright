---
name: build-from-best
description: >-
  End-to-end "I want to create X" pipeline that chains REA (reverse-engineer-anything)
  and the 11 replica-* skills. REA phase searches the internet for the best existing
  apps/tools that do X, obtains their code or shipped artifacts and deeply analyses the
  complete codebase of each (architecture, data model, APIs, algorithms, security, with a
  coverage gate), picks the best (plus the best
  features of the runners-up) and writes a detailed spec. Replica phase then builds it
  deeply from that spec with hard verification gates (tests, parity, bugs, contrast,
  rebrand sweep). Use when the user says "I want to create/build/make X", "build
  something like X", "clone X", "make an app that does X", "build me a SaaS/tool for X",
  or names a product idea and wants it built. Use INSTEAD of shipwright:brainstorming
  for these requests.
---

> **Vendored into Shipwright.** `<shipwright>` below means the absolute path of the shipwright skill folder. Shipwright's precedence rules (`<shipwright>/library/ROUTING.md`) apply: use this guide's technique inside the current Shipwright phase, not its own workflow.


# build-from-best

Idea in, verified product out. Two phases, one shared folder:

```
research/            REA + web evidence. Reference only. Never copied into the app.
replica/             replica pack working folder (spec, recon, features.csv, bugs, parity...)
```

Do not run a brainstorming interview. Ask at most ONE scoping message, with your
proposed defaults, then go. If the user already gave platform/audience, ask nothing.

## Phase 0: intake (one message max)

Restate X in one line and propose defaults the user can override:
platform (default: web app, Next.js + Postgres), audience, core loop, budget for
paid APIs (default: free tiers). Proceed on "go" or silence-equivalent instructions.

## Phase 1: discover (REA lead, internet-wide)

1. WebSearch (send several searches in one turn) for the top apps/tools doing X:
   "best X app", "X alternatives", G2/Capterra/Product Hunt/AlternativeTo/Reddit
   lists, GitHub open-source equivalents.
2. Shortlist 3-5 candidates. Score each in `research/candidates.md`:

   | candidate | core loop | key features | rating + review count | pricing | platform | open source? | analysable artifact? | score /10 |

   Weight: user love (ratings, review sentiment) 30, feature depth 25, UX quality 20,
   analysable evidence 15, market gap 10.
3. Pick **one primary** (the model to build from) and a **borrow list**: the
   standout features of the runners-up worth adding. State the pick and why in 3 lines.

## Phase 2: analyse — complete, deep codebase analysis (REA)

Searching is not analysis. For EVERY shortlisted candidate (primary in full, runners-up
in full for their borrow-list areas at minimum), obtain the code or shipped artifact and
analyse the complete codebase, not a sample. Load `reverse-engineer-anything` and follow
its "Plan broader investigations" workflow.

### 2a. Get the code (per candidate, record route in `research/candidates.md`)

| what exists | how to get it | analyse with |
|---|---|---|
| open-source repo (GitHub/GitLab) | `git clone --depth 1` into `research/src/<candidate>/` | normal repo tools: parallel Explore agents, serena symbols, grep (REA skips plain source repos by design) |
| web app (closed) | live site, JS bundles, public source maps, network | REA `capture_browser_scenario`, browser runtime tools, source-map / JS artifact reconstruction, `inspect_web_network_capture` |
| desktop / Electron app | user-installed copy, ASAR | REA `analyze_javascript_application`, `inspect_electron_fuses`, Electron runtime tools |
| Android / iOS app | APK/IPA the user downloaded | REA `open_binary`, `inspect_android_package` (needs JADX: set `REA_JADX_MCP_JAR`) |
| native / .NET binary | user-installed binary | REA `open_binary` + Ghidra/IDA/Hopper provider, `inspect_managed_artifact` |

Missing engine (Ghidra/JADX/IDA): tell the user the exact env var to set, continue
with every other route, and mark that candidate's coverage partial. Never silently skip.

### 2b. Analyse the whole codebase (fan out)

Split each codebase into independent scopes (by module / package / feature area) and
dispatch parallel subagents, one scope each, all writing to the same ledger. Each scope
must answer, with evidence (file path + line, or REA Evidence ID):

1. **Architecture:** entry points, module map, layers, dependency graph, build/runtime stack
2. **Data model:** every entity, field, relationship, constraint, migration, storage engine
3. **API surface:** every route/endpoint/IPC channel/RPC, request/response shapes, auth on each
4. **Core algorithms:** how each must-have feature actually works step by step
   (sync, search, ranking, scheduling, realtime, offline, conflict resolution...)
5. **State & flows:** client state, server state, caching, background jobs, queues, webhooks
6. **Integrations:** third-party services, SDKs, payment, email, auth providers
7. **Security & perms:** authn/authz model, multi-tenancy, rate limits, secret handling
8. **Quality signals:** tests, error handling, perf tricks, known bugs/TODOs, tech debt
9. **UX implementation:** component library, design tokens, animation, a11y approach

Output per candidate in `research/rea/<candidate>/`:
`architecture.md`, `data-model.md`, `api.md`, `algorithms.md`, `flows.md`,
`integrations.md`, `security.md`, `quality.md`, `ux.md`, and `ledger.md`
(conclusion → evidence → confidence → unknowns).

### 2c. Coverage gate (analysis is not done until this passes)

Write `research/rea/<candidate>/coverage.md`:
- every top-level module / package / bundle chunk listed with status: analysed / partial / skipped (+ reason)
- every must-have feature traced from entry point to data and back
- open questions remaining

Pass: 100% of modules inventoried, 100% of must-have features traced, every
"partial" has a stated reason. Otherwise dispatch another pass on the gaps.

### 2d. Recon + users

1. **replica-recon** on the primary: screens S01.., flows F01.., components,
   `replica/features.csv`, now enriched with the real data model and API from 2b.
2. **replica-entrepreneur** across ALL candidates: what users hate, what is missing.
   These become `should`/`must` rows in features.csv and the positioning angle.
3. **Compare:** `research/comparison.md` — per feature, which candidate's implementation
   is best and why (from the code, not marketing). The spec uses the best of each.

### Licence and clean-room handling

- **Permissive open source (MIT/Apache/BSD):** may reuse code with attribution and the
  licence file kept; record every reused file in `replica/third-party.md`.
- **Copyleft (GPL/AGPL/LGPL) or closed source / decompiled:** behaviour only. Describe
  mechanisms in own words in `research/`; the build never copies code, strings or assets.
- If REA MCP tools are absent: tell the user to run `! npx rea-agents setup --client claude_code --yes`
  and restart; continue with repo + web routes meanwhile.

## Phase 3: spec (gate: user approves)

Write `replica/spec.md`. A builder must be able to build from it with no questions:

- Product: one-line pitch, audience, positioning angle (from entrepreneur)
- Core loop + every flow F.. with happy path, edge cases, click count to beat
- Screens S.. with every state (empty, loading, filled, error, denied, mobile)
- Feature matrix summary: must / should / could, source (primary, borrowed, fix-of-complaint)
- How each non-trivial feature works and which candidate's approach wins
  (from `research/rea/*/algorithms.md` + `research/comparison.md`, in own words)
- Architecture decisions justified by what the analysed codebases did well / badly
- Data model with constraints, API routes, integrations, auth, payments
- Non-functional: performance targets, accessibility (WCAG AA), security, privacy
- Out of scope / cannot clone (licensed content, network effects, owned data)
- Acceptance criteria per flow (these become the test plan)
- Size: S / M / L / XL

Show the user a 10-line summary + path to spec. **Do not build until they approve.**

## Phase 4: build deep (replica chain)

Run in order, each reads `replica/`:

```
replica-architect -> replica-design -> replica-build -> replica-backend -> replica-test -> replica-diff
```

- replica-architect reads `replica/spec.md` as well as recon.md.
- UI work also loads the design skills the global hook names (shipwright-design-craft, shipwright-art-direction, etc.).
- Use shipwright:test-driven-development for logic, shipwright:systematic-debugging for bugs.

## Phase 5: verification gates (loop until ALL pass)

| gate | check | pass |
|---|---|---|
| tests | project test suite + Playwright e2e from `replica/test-plan.md` | all green |
| bugs | `replica/bugs.md` | zero open S1/S2 |
| parity | `python3 <shipwright>/library/shipwright_product/shipwright-replica-diff/parity.py replica/features.csv` | 100% must-haves done |
| layout | `imgdiff.py` per key screen | structural match on core-loop screens |
| contrast | `python3 <shipwright>/library/shipwright_product/shipwright-replica-design/contrast.py replica/design/tokens.json` | WCAG AA |
| spec | every acceptance criterion in spec.md | demonstrated, with evidence |
| clean-room | `python3 <shipwright>/library/shipwright_product/shipwright-replica-brand/sweep.py . --config replica/brand.json` | exit 0 |

Failing gate -> fix -> rerun ALL gates. Report actual output, never "should pass".
Finish with shipwright:verification-before-completion.

## Phase 6: make it sellable and ship

```
replica-entrepreneur (apply fixes.md) -> replica-brand -> replica-launch -> replica-deploy
```

replica-deploy only on the user's explicit "go". Deploy, DNS, Stripe live mode,
store submissions are outward-facing: confirm each.

## Rules

- **Clean-room:** build rebuilds behaviour, never code, logos, copy, assets or private
  APIs, except permissive-licence code reused with attribution (see Phase 2).
  `research/` is reference only; the app never imports from it.
- **Legal:** only analyse artifacts the user may legally access; respect ToS/EULA. If
  terms forbid competitive use of an account, use public sources only and say so.
- **NexaQuanta policy:** never feed client binaries, client source or client data into
  this pipeline without written consent. Anonymise when in doubt.
- **Progress:** after each phase, one line: what finished, key number, what is next.
