#!/usr/bin/env python3
"""Model-led routing test: the way Shipwright routes at runtime. A real Claude model gets library/INDEX.md and a
request, and must pick the guide by context. Scores the pick against each case's expected area.

Usage: python3 evals/run_routing_model.py evals/heldout4_cases.json [more case files] -j 6 --model sonnet
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INDEX = ""  # loaded in main() so a freshly regenerated index is used
AREAS = json.loads((REPO / "evals" / "areas.json").read_text())
ASK = ("You are routing a software task to the single most useful guide in this library.\n\n{index}\n\n"
       "Request:\n<<<\n{prompt}\n>>>\n\n{hint}Reply with only the guide id in the form section/guide, nothing else.")


def shortlist(prompt: str) -> str:
    import importlib.util
    spec = importlib.util.spec_from_file_location("sw", REPO / "skills" / "shipwright" / "scripts" / "shipwright.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    gs = [r["guides"][0] for r in m.route(prompt, top=3)]
    return ("A fast keyword router suggests (a hint, not a verdict): " + ", ".join(gs) + "\n\n") if gs else ""


def pick(prompt: str, model: str, hybrid: bool) -> str:
    hint = shortlist(prompt) if hybrid else ""
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run(["claude", "-p", ASK.format(index=INDEX, prompt=prompt, hint=hint), "--model", model, "--max-turns", "1",
                            "--setting-sources", "project", "--no-session-persistence", "--tools", ""],
                           cwd=d, capture_output=True, text=True, timeout=180)
    m = re.search(r"shipwright_[a-z_]+/shipwright-[\w-]+", r.stdout)
    return m.group(0) if m else r.stdout.strip()[:80]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("-j", type=int, default=6)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--hybrid", action="store_true", help="also show the keyword shortlist, as the hook does at runtime")
    a = ap.parse_args()
    global INDEX
    INDEX = (REPO / "skills" / "shipwright" / "library" / "INDEX.md").read_text()
    jobs = []
    for f in a.files:
        for c in json.loads(Path(f).read_text())["cases"]:
            want = c.get("guide") or AREAS.get(c.get("area") or "")
            if c.get("trigger") and want:
                jobs.append((Path(f).name, c["prompt"], want))
    with cf.ThreadPoolExecutor(max_workers=a.j) as ex:
        got = list(ex.map(lambda j: pick(j[1], a.model, a.hybrid), jobs))
    per: dict = {}
    misses = []
    for (name, prompt, want), g in zip(jobs, got):
        ok = bool(re.search(want, g))
        per.setdefault(name, [0, 0])[0] += ok
        per[name][1] += 1
        if not ok:
            misses.append(f"  {name}: want *{want}* got {g} :: {prompt[:90]}")
    for name, (ok, n) in per.items():
        print(f"{name}: {ok}/{n}")
    total = sum(v[0] for v in per.values()), sum(v[1] for v in per.values())
    print(f"TOTAL model routing ({a.model}{', hybrid' if a.hybrid else ''}): {total[0]}/{total[1]}")
    print("\n".join(misses))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
