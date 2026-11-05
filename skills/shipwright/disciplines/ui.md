# UI changes

Goal: interfaces that look intentional and work for everyone, verified in a real browser.
This file is the floor. For depth, load the bundled guides as routed in `library/ROUTING.md`:
- `ui/taste-skill` for public pages
- `ui/interface-design` for app screens
- `ui/impeccable` for craft, critique, and audit
- `ui/emil-design-eng` for polish
- the motion and mobile guides when they apply

Their browser inspectors and detectors count as checks: run them through `SW verify`.

## Before building

- Read `## Design system` in `.shipwright/context.md`. If the project keeps impeccable's
  `DESIGN.md` / `PRODUCT.md`, context.md points to them, so there is one source of truth.
  - Reuse the existing tokens, components, and patterns.
  - No system yet: define a minimal one (color roles, type scale, spacing scale, radius, and **one** elevation style, shadow or border, never both) and record it there.
- Design every state, not just the happy one: loading, empty, error, success, disabled, long content, zero, many.

## Craft floor

- **Hierarchy:** one clear primary action per view. Size, weight, and contrast show importance; colour alone does not.
- **Typography:**
  - at most 2 families
  - a modular scale
  - body text at 16px or larger, line length 45–75 characters
- **Spacing:** use only the scale. Align to a grid. Group related items closer together than unrelated ones.
- **Avoid the generic AI look:**
  - default purple/blue gradients
  - everything centered
  - emoji used as icons
  - a pile of identical cards
  - decorative blobs
  - stock filler text

  Choose a direction on purpose and keep to it.
- **Copy:**
  - buttons say what happens ("Save changes", not "Submit")
  - errors say what went wrong and how to fix it
  - empty states say what to do next
- **Motion:**
  - only to explain a change, at 150–300ms
  - animate `transform` and `opacity` only
  - respect `prefers-reduced-motion`

## Accessibility floor (not optional)

- **Contrast:** at least 4.5:1 for text, 3:1 for large text and UI parts.
- **Keyboard:** everything reachable by keyboard, with a visible focus ring and a logical tab order.
- **Labels:** every input has a label, every icon button has an accessible name, every image has alt text (empty if it's decorative).
- **Touch:** targets at least 44×44px.
- **Zoom:** works at 200% zoom and from 320px wide upward.

## Verify

**Put these checks in the plan's `## Verification`,** so the gate requires them. `<skill>` is
this skill's absolute folder.

**Any UI change:**
- `<skill>/library/ui/impeccable/scripts/impeccable detect <changed UI files or dir>`: exit 0 means no anti-patterns.

**Public pages** (landing, marketing, portfolio):
- `node <skill>/library/ui/taste-skill/scripts/inspect.mjs <url or file.html>`: no FAIL rows. It screenshots at 1440, 768, and 390.

**The project's own a11y and lint tooling,** if it has any.

**Then look:**
1. Open the UI in a real browser (Playwright or DevTools).
2. Screenshot it with the key states set up: at 375px and 1280px at minimum. taste-skill's 390/768/1440 set also counts.
3. Render the component with worst-case data (`library/ui/break-ui/GUIDE.md`: long names, empty, huge counts, non-Latin text) and screenshot that too.
4. Check the hierarchy, alignment, overflow, truncation, and contrast. Fix what's wrong.
5. Save screenshots in `.shipwright/work/<item>/review/`. Files saved elsewhere in the repo count as code changes and make earlier evidence stale.
   Record the check with `SW verify <id> --manual "<what you checked>" --artifact <screenshot path>`.
