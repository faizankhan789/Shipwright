#!/usr/bin/env python3
"""UserPromptSubmit hook: recognise Shipwright tasks and route them before Claude acts.

For a build / fix / design / plan / resume request it adds a short note: invoke the `shipwright`
skill, and which bundled guides fit (from library/routing.json, the same engine as
`shipwright.py route`). A request for a Word, PDF, PowerPoint or Excel file or an explainer video
gets the guide's path and no workflow. Questions, explanations, chat and slash commands get nothing.
Stdlib only; always exits 0 so it can never block a prompt.
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SW = ROOT / "skills" / "shipwright" / "scripts" / "shipwright.py"

NOTE = {
    "resume": "resume the open Shipwright work: run its `shipwright.py resume` first",
    "design": "this is a design-only request (size D): analyze the problem, then convene the council (phases/council.md)",
    "debug": "this is a bug or failure: follow disciplines/debugging.md (root cause before any fix)",
    "ui": "this is UI work: follow disciplines/ui.md and record the design guide with `shipwright.py route ... --id`",
}


def main() -> None:
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        prompt = json.load(sys.stdin).get("prompt", "")
        spec = importlib.util.spec_from_file_location("shipwright_cli", SW)
        sw = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sw)
        kind = sw.classify_prompt(prompt)
        if not kind:
            return
        if kind == "document":  # a file to produce, not software: the guide is enough, no plan or gates
            paths = [str(sw.LIBRARY / r["guides"][0] / "GUIDE.md") for r in sw.route(prompt, top=2)]
            print("Shipwright: this asks for a file, not software, so no plan, gates or skill call are needed. "
                  f"Read {' and '.join(paths)} and follow it. Paths inside a guide are relative to its folder.")
            return
        guides = [f"library/{r['guides'][0]}/GUIDE.md" for r in sw.route(prompt, top=3)] if kind != "resume" else []
        lines = [f"Shipwright: invoke the `shipwright` skill (Skill tool) before acting. First action: call the Skill tool "
                 f"with skill \"shipwright\" (if a session rule requires other skills first, do those, then shipwright), "
                 f"even for small tasks such as tests or refactors; "
                 f"{NOTE.get(kind, 'it sizes the task and follows its phases')}."]
        if guides:
            lines.append("Keyword shortlist (a hint): " + ", ".join(guides) + ". Choose by context from "
                         "library/INDEX.md (sections, then guides) and log the pick with `shipwright.py route --use`.")
        lines.append("Shipwright bundles the design, debugging, testing and process guides other autoload hooks may "
                     "suggest; where instructions overlap, follow Shipwright and its bundled guides.")
        print(" ".join(lines))
    except Exception:  # a routing hint must never break the user's prompt
        return


if __name__ == "__main__":
    main()
