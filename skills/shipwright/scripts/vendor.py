#!/usr/bin/env python3
"""Copy installed skills into shipwright/library/<category>/<name>/ as on-demand guides.

Categories and source paths come from library/sources.json (every key except "about").

Each copied SKILL.md is renamed GUIDE.md so it is never discovered as a separate, competing
skill: shipwright stays the single entry point and loads guides when a phase calls for them.
Writes library/INDEX.md (what each guide is for) and library/LICENSES.md (license status).
Stdlib only. Usage: python3 vendor.py [--claude-home ~/.claude] [--only name1,name2]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

LIB = Path(__file__).resolve().parent.parent / "library"
SKIP = shutil.ignore_patterns(".git", "node_modules", "__pycache__", ".DS_Store", "*.pyc", ".venv",
                              "*.backup", "test-pressure-*.md", "CREATION-LOG.md")
HEADER = ("> **Vendored into Shipwright.** `<shipwright>` below means the absolute path of the shipwright skill "
          "folder. Shipwright's precedence rules (`<shipwright>/library/ROUTING.md`) apply: use this guide's "
          "technique inside the current Shipwright phase, not its own workflow.\n\n")
LICENSE_NAMES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "COPYING", "NOTICE")


def frontmatter(text: str) -> dict:
    """Minimal YAML frontmatter reader, including folded/literal (>, >-, |) and indented continuations."""
    m = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    out, key = {}, None
    if m:
        for line in m.group(1).splitlines():
            if line[:1] in (" ", "\t") and key:
                out[key] = (out[key] + " " + line.strip()).strip()
            elif ":" in line:
                k, v = line.split(":", 1)
                key, v = k.strip(), v.strip()
                out[key] = "" if v in (">", ">-", "|", "|-", ">+", "|+") else v.strip("'\"")
    return out


def rewrite_refs(dest: Path, where: dict) -> None:
    """Point references to other installed skills at their library copies."""
    for f in dest.rglob("*"):
        if f.suffix not in (".md", ".sh", ".py", ".mjs", ".js", ".json") or not f.is_file():
            continue
        try:
            text = f.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        new = re.sub(r"~/\.claude/skills/([\w-]+)/",
                     lambda m: f"<shipwright>/library/{where[m.group(1)]}/{m.group(1)}/" if m.group(1) in where else m.group(0),
                     text)
        new = re.sub(r"\bsuperpowers:([\w-]+)",
                     lambda m: f"the `{m.group(1)}` guide (`<shipwright>/library/{where[m.group(1)]}/{m.group(1)}/GUIDE.md`)"
                     if m.group(1) in where else m.group(0), new)
        if new != text:
            f.write_text(new)


def find_license(src: Path, home: Path) -> str:
    """License file in the skill folder or any parent up to the plugin root; else frontmatter."""
    for d in [src, *src.parents]:
        if d == home or home not in d.parents:
            break
        for name in LICENSE_NAMES:
            f = d / name
            if f.is_file():
                first = next((l.strip() for l in f.read_text(errors="ignore").splitlines() if l.strip()), "")
                return f"{first} ({f.relative_to(home)})"
    fm = frontmatter((src / "SKILL.md").read_text(errors="ignore"))
    if fm.get("license"):
        return f"{fm['license']} (declared in SKILL.md frontmatter)"
    return "NONE FOUND: personal use only, do not redistribute"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--claude-home", default=str(Path.home() / ".claude"))
    p.add_argument("--only", help="comma-separated names to refresh")
    a = p.parse_args(argv)
    home = Path(a.claude_home).expanduser().resolve()
    sources = json.loads((LIB / "sources.json").read_text())
    only = set(a.only.split(",")) if a.only else None

    index, licenses, missing = [], [], []
    categories = [c for c in sources if c != "about"]
    where = {name: c for c in categories for name in sources[c]}
    for category in categories:
        for name, rel in sources[category].items():
            src = (home / rel).resolve()
            dest = LIB / category / name
            if not (src / "SKILL.md").is_file():
                missing.append(f"{name} ({rel})")
                if dest.exists():  # keep the previous copy rather than losing it
                    index.append((category, name, "(kept previous copy: source missing)"))
                continue
            if only is None or name in only:
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(src, dest, ignore=SKIP, symlinks=False)
                guide_text = (dest / "SKILL.md").read_text(errors="ignore")
                (dest / "SKILL.md").unlink()
                fm_m = re.match(r"\A---\n.*?\n---\n", guide_text, re.S)
                cut = fm_m.end() if fm_m else 0
                (dest / "GUIDE.md").write_text(guide_text[:cut] + "\n" + HEADER + guide_text[cut:])
                rewrite_refs(dest, where)
            guide = dest / "GUIDE.md"
            desc = frontmatter(guide.read_text(errors="ignore")).get("description", "") if guide.exists() else ""
            desc = re.sub(r"\s+", " ", desc)
            index.append((category, name, desc[:220] + ("..." if len(desc) > 220 else "")))
            licenses.append((name, find_license(src, home)))

    lines = ["# Library index (generated by scripts/vendor.py, do not edit)", "",
             "Guides are loaded on demand, as routed by `library/ROUTING.md`. Read a guide's `GUIDE.md`;",
             "paths inside it are relative to that guide's own folder.", ""]
    for category in categories:
        lines += [f"## {category}", "", "| Guide | Path | Use for |", "|---|---|---|"]
        lines += [f"| {n} | `library/{c}/{n}/GUIDE.md` | {d.replace('|', '/')} |" for c, n, d in index if c == category]
        lines.append("")
    (LIB / "INDEX.md").write_text("\n".join(lines))

    lic = ["# Bundled guide licenses (generated by scripts/vendor.py)", "",
           "Guides marked NONE FOUND have no license file and were copied from your own install:",
           "fine for personal use, but do not publish or redistribute this package with them included.", "",
           "| Guide | License |", "|---|---|"] + [f"| {n} | {l} |" for n, l in licenses]
    if missing:
        lic += ["", "## Not found at vendoring time", ""] + [f"- {m}" for m in missing]
    (LIB / "LICENSES.md").write_text("\n".join(lic) + "\n")

    unlicensed = sum(1 for _, l in licenses if l.startswith("NONE FOUND"))
    print(f"vendored {len(licenses)} guides into {LIB} ({unlicensed} without a license file)")
    for m in missing:
        print(f"missing: {m}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
