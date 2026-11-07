#!/usr/bin/env python3
"""Live trigger test: does the `shipwright` skill fire for the right prompts in real Claude Code runs?

Each case runs `claude -p` with this plugin loaded (--plugin-dir) in a throwaway project folder,
with editing tools disallowed, and reads the stream for Skill tool calls.

  --mode isolated  user-level settings, hooks and plugins are not loaded (--setting-sources project):
                   measures Shipwright on its own
  --mode real      the user's normal setup is loaded too: measures interference from other hooks/plugins

Usage: python3 evals/run_triggers.py --cases evals/routing_cases.json --mode isolated -j 4 [--limit N]
Prints accuracy and writes a JSON report next to the cases file (results/).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def run_case(prompt: str, mode: str, max_turns: int, timeout: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="sw-trigger-") as d:
        (Path(d) / "app.py").write_text("def main():\n    return 0\n")
        subprocess.run(["git", "init", "-q"], cwd=d)
        cmd = ["claude", "-p", prompt, "--plugin-dir", str(REPO), "--output-format", "stream-json", "--verbose",
               "--max-turns", str(max_turns), "--no-session-persistence",
               "--disallowedTools", "Edit", "Write", "NotebookEdit", "Bash"]
        if mode == "isolated":
            cmd += ["--setting-sources", "project"]
        try:
            out = subprocess.run(cmd, cwd=d, capture_output=True, text=True, timeout=timeout).stdout
        except subprocess.TimeoutExpired as e:
            out = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
    skills, tools, reads, first_text = [], [], [], ""
    for line in out.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = ev.get("message") if isinstance(ev, dict) else None
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tools.append(block.get("name"))
                if block.get("name") == "Skill":
                    skills.append(str((block.get("input") or {}).get("skill", "")))
                if block.get("name") == "Read":
                    reads.append(str((block.get("input") or {}).get("file_path", "")))
            if isinstance(block, dict) and block.get("type") == "text" and not first_text:
                first_text = block.get("text", "")[:160]
    # document asks skip the skill: reading the guide the hook named counts as firing
    fired = any("shipwright" in s for s in skills) or any("/shipwright_documents/" in r for r in reads)
    return {"fired": fired, "skills": skills, "reads": reads, "tools": tools, "first_text": first_text}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=str(REPO / "evals" / "routing_cases.json"))
    ap.add_argument("--mode", choices=["isolated", "real"], default="isolated")
    ap.add_argument("-j", type=int, default=4)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--max-turns", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=180)
    a = ap.parse_args()
    cases = json.loads(Path(a.cases).read_text())["cases"][: a.limit]
    with cf.ThreadPoolExecutor(max_workers=a.j) as ex:
        results = list(ex.map(lambda c: {**c, **run_case(c["prompt"], a.mode, a.max_turns, a.timeout)}, cases))
    tp = sum(r["trigger"] and r["fired"] for r in results)
    fn = sum(r["trigger"] and not r["fired"] for r in results)
    tn = sum(not r["trigger"] and not r["fired"] for r in results)
    fp = sum(not r["trigger"] and r["fired"] for r in results)
    other = {}
    for r in results:
        for s in r["skills"]:
            if "shipwright" not in s:
                other[s] = other.get(s, 0) + 1
    print(f"mode={a.mode} cases={len(results)}  should-fire: {tp}/{tp + fn}  should-stay-silent: {tn}/{tn + fp}  "
          f"overall: {tp + tn}/{len(results)}")
    for r in results:
        if r["trigger"] != r["fired"]:
            print(f"  MISS {'(missed)' if r['trigger'] else '(false fire)'} {r['prompt'][:70]!r} tools={r['tools']} said={r['first_text']!r}")
    if other:
        print("  other skills fired:", dict(sorted(other.items(), key=lambda x: -x[1])))
    out = Path(a.cases).parent / "results" / f"triggers-{a.mode}-{dt.datetime.now():%Y%m%d-%H%M%S}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(results, indent=1))
    print(f"report: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
