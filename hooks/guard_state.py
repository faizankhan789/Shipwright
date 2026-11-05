#!/usr/bin/env python3
"""PreToolUse guard: Shipwright's gate records are written only by sw.py.

Blocks (exit 2, reason on stderr) when an agent tries to hand-edit:
- evidence.jsonl, deploys.jsonl, log.md under .shipwright/ (evidence, DORA records, audit trail)
- the signing key (~/.config/shipwright/key)
- a plan's frontmatter (status, approval, baseline, timestamps...): located by its real position in the
  file, so mid-line edits are caught too
- any shell command that names those files together with a write-capable tool

Plan bodies stay editable with Edit/Write: agents fill plans, tick tasks and append notes.
This is defense in depth: sw.py also signs and hash-chains its records, so edits that slip past this
guard are still detected at the gate. Stdlib only; reads the hook payload from stdin.
"""
import json
import re
import sys
from pathlib import Path

RECORDS = ("evidence.jsonl", "deploys.jsonl", "log.md")
SHELL_RECORD = re.compile(r"(evidence|deploys)\.jsonl|\blog\.md\b|shipwright/key\b")
SHELL_PLAN = re.compile(r"\bplan\.md\b")
# tools and syntax that can write: redirection (not 2>&1), tee, in-place editors, interpreters, file ops
SHELL_WRITE = re.compile(
    r"(?<![0-9&])>|\btee\b|\bsed\b|\bperl\b|\bpython[0-9.]*\b|\bruby\b|\bnode\b|\bawk\b|\bcp\b|\bmv\b|\brm\b|"
    r"\btruncate\b|\bdd\b|\bed\b|\bex\b|\bvim?\b|\binstall\b|\brsync\b|\bln\b|\bchmod\b")


def block(msg: str) -> None:
    print(f"Shipwright guard: {msg}", file=sys.stderr)
    sys.exit(2)


def frontmatter_end(text: str) -> int:
    m = re.match(r"\A---\n.*?\n---\n", text or "", re.S)
    return m.end() if m else 0


def in_state(path: str) -> bool:
    return "/.shipwright/" in path or path.startswith(".shipwright/")


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return
    tool = payload.get("tool_name", "")
    ti = payload.get("tool_input") or {}

    if tool == "Bash":
        cmd = ti.get("command", "")
        # sw.py itself never needs these file names on its command line, so there is no exemption for it
        if SHELL_RECORD.search(cmd) and SHELL_WRITE.search(cmd):
            block("evidence, deploy records, logs and the signing key are written only by sw.py "
                  "(`sw.py verify`, `sw.py deploy`, `sw.py log`). Read them with cat/grep/jq only.")
        if SHELL_PLAN.search(cmd) and ".shipwright" in cmd and SHELL_WRITE.search(cmd):
            block("edit plan bodies with the Edit tool; status and approval change only through "
                  "`sw.py mark` / `sw.py set`.")
        return

    if tool not in ("Write", "Edit", "MultiEdit"):
        return
    path = ti.get("file_path", "")
    if path.endswith("shipwright/key"):
        block("the signing key is managed by sw.py.")
    if not in_state(path):
        return
    name = Path(path).name
    if name in RECORDS:
        block(f"{name} is written only by sw.py.")
    if name != "plan.md":
        return
    try:
        current = Path(path).read_text(encoding="utf-8")
    except OSError:
        return  # new file: sw.py creates plans; nothing to protect yet
    end = frontmatter_end(current)
    if tool == "Write":
        new = ti.get("content", "")
        if current[:end] != new[:frontmatter_end(new)]:
            block("plan frontmatter changes only through `sw.py mark` / `sw.py set`; edit the plan body instead.")
        return
    edits = ti.get("edits") or [{"old_string": ti.get("old_string", "")}]
    for e in edits:
        old = e.get("old_string", "") or ""
        start = current.find(old) if old else -1
        while start != -1:
            if start < end:
                block("that edit touches the plan frontmatter, which changes only through `sw.py mark` / `sw.py set`.")
            start = current.find(old, start + 1)


if __name__ == "__main__":
    main()
