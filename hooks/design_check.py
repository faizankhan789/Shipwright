#!/usr/bin/env python3
"""PostToolUse hook: after an edit to a UI file, run Shipwright's design check and tell Claude what it found.

Runs the bundled engine plus the JSX rules, so it needs nothing else installed. Never blocks: it adds context for
Claude and always exits 0. Stays silent when the file is clean, is not a UI file, or is generated or vendored code.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SW = ROOT / "skills" / "shipwright" / "scripts" / "shipwright.py"
MAX_FINDINGS = 8


def summarize(findings: list, name: str) -> str:
    lines = []
    for f in findings[:MAX_FINDINGS]:
        where = f":{f['line']}" if f.get("line") else ""
        lines.append(f"- {name}{where} [{f.get('antipattern', '?')}] {str(f.get('description', ''))[:140]}")
    if len(findings) > MAX_FINDINGS:
        lines.append(f"- ...and {len(findings) - MAX_FINDINGS} more")
    return (f"Shipwright design check: found {len(findings)} UI issue(s) in the file you just edited. Fix them now, "
            "or add a shipwright-disable comment with the reason if one is a false positive:\n" + "\n".join(lines))


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        if payload.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
            return
        path = Path((payload.get("tool_input") or {}).get("file_path") or "")
        cwd = Path(payload.get("cwd") or path.parent)
        sys.path.insert(0, str(SW.parent))
        spec = importlib.util.spec_from_file_location("shipwright_cli", SW)
        sw = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sw)
        try:
            inside = path.resolve().relative_to(cwd.resolve()).parts
        except ValueError:
            inside = path.parts[-3:]  # outside the project: only look at the nearest folders
        if not sw.DETECT_FILE_RE.search(path.name) or sw.DESIGN_SKIP_DIRS & set(inside) or not path.is_file():
            return
        findings = sw.design_findings([str(path)], cwd)
        if findings:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                                     "additionalContext": summarize(findings, path.name)}}))
    except Exception:  # a design hint must never break an edit
        return


if __name__ == "__main__":
    main()
