#!/usr/bin/env python3
"""shipwright state tool: work items, plans, gates and evidence on disk.

Standard library only (Python 3.9+). Run `python3 shipwright.py <command> -h` for details.
State lives in `.shipwright/` at the project root; the plan file's frontmatter is
the single source of truth for an item's status.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import os
import secrets
import statistics
import json
import re
import subprocess
import sys
from pathlib import Path

STATE_DIR = ".shipwright"
SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_DIR / "templates"

TRANSITIONS = {
    "draft": {"ready", "blocked", "dropped"},
    "ready": {"building", "draft", "blocked", "dropped"},
    "building": {"reviewing", "verified", "draft", "blocked", "dropped"},
    "reviewing": {"building", "verified", "draft", "blocked", "dropped"},
    "verified": {"done", "building", "blocked"},
    "blocked": {"draft", "ready", "building", "dropped"},
    "done": set(),
    "dropped": set(),
}
NEXT_HINT = {
    "draft": "finish the plan, run `check`, get approval (phases/plan.md)",
    "ready": "approved: start building (phases/build.md)",
    "building": "continue building (phases/build.md)",
    "reviewing": "run lenses + triage (phases/review.md)",
    "verified": "present to the human for acceptance (phases/ship.md)",
}
REQUIRED = {
    "S": ["Intent", "Verification", "Implementation Notes"],
    "M": ["Intent", "Boundaries", "Code Map", "Tasks", "Acceptance Criteria",
          "Verification", "Implementation Notes", "Plan Change Log", "Review Triage Log"],
}
FREE_TEXT = {"Implementation Notes", "Plan Change Log", "Review Triage Log", "Design Notes"}
MAX_LOOPBACKS = 5
POST_BUILD = ("Implementation Notes", "Plan Change Log", "Review Triage Log")
VERDICTS = ("high", "medium", "low", "false", "maybe-false", "pending")
ROUTES = ("patch", "bad-plan", "intent-gap", "defer", "reject", "-")
# untracked build artifacts that would only distract reviewers when no .gitignore covers them
JUNK_RE = re.compile(r"(^|/)(__pycache__|node_modules|\.pytest_cache|\.mypy_cache|\.venv|\.shipwright-art-direction|\.shipdesign)/|\.pyc$|(^|/)\.DS_Store$")
FM_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
FROZEN_RE = re.compile(r"<!-- frozen:start -->(.*?)<!-- frozen:end -->", re.S)


class SwError(Exception):
    pass


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "item"


def norm_cmd(cmd: str) -> str:
    return " ".join(cmd.split())


# ---------- locating state ----------

def find_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    here = Path.cwd().resolve()
    for d in [here, *here.parents]:
        if (d / STATE_DIR).is_dir():
            return d
    raise SwError(f"no {STATE_DIR}/ found from {here} upward; run `shipwright.py init` at the project root")


def state(root: Path) -> Path:
    return root / STATE_DIR


def item_dir(root: Path, item_id: str) -> Path:
    item_id = item_id.zfill(3)
    hits = sorted((state(root) / "work").glob(f"{item_id}-*"))
    if not hits:
        raise SwError(f"no work item {item_id}")
    return hits[0]


def all_items(root: Path) -> list[Path]:
    work = state(root) / "work"
    return sorted(p for p in work.iterdir() if p.is_dir()) if work.is_dir() else []


# ---------- plan file ----------

def read_plan(d: Path) -> tuple[dict, str]:
    text = (d / "plan.md").read_text(encoding="utf-8")
    m = FM_RE.match(text)
    if not m:
        raise SwError(f"{d / 'plan.md'}: missing frontmatter")
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm, text[m.end():]


def write_plan(d: Path, fm: dict, body: str) -> None:
    head = "\n".join(f"{k}: {v}" for k, v in fm.items())
    (d / "plan.md").write_text(f"---\n{head}\n---\n{body}", encoding="utf-8")


def sections(body: str) -> dict[str, str]:
    out, name, buf = {}, None, []
    for line in body.splitlines():
        m = re.match(r"^## (.+?)\s*$", line)
        if m:
            if name is not None:
                out[name] = "\n".join(buf)
            name, buf = m.group(1).strip(), []
        elif name is not None:
            buf.append(line)
    if name is not None:
        out[name] = "\n".join(buf)
    return out


def strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def approval_hash(fm: dict, body: str) -> str:
    """What the human approves: frozen intent + size + type + the Verification checks."""
    m = FROZEN_RE.search(body)
    if not m:
        return ""
    verification = strip_comments(sections(body).get("Verification", ""))
    acs = strip_comments(sections(body).get("Acceptance Criteria", ""))
    parts = [m.group(1), fm.get("size", ""), fm.get("type", ""), verification, acs]
    return hashlib.sha256("\x1f".join(" ".join(p.split()) for p in parts).encode()).hexdigest()[:16]


def approval_problem(fm: dict, body: str) -> str:
    stored = fm.get("approval_hash", "")
    if stored and stored != approval_hash(fm, body):
        return ("approved plan changed (frozen intent, size, type, ## Acceptance Criteria or ## Verification): only the human may "
                "change these; `mark <id> draft`, fix, and re-approve with `mark <id> ready`")
    return ""


def plan_tokens(body: str) -> int:
    """Approximate tokens of the plan proper; build-time logs don't count against the budget."""
    secs = sections(body)
    words = len(strip_comments(body).split())
    words -= sum(len(strip_comments(secs.get(n, "")).split()) for n in POST_BUILD)
    return int(words * 1.33)


def verification_commands(body: str) -> tuple[list[str], bool]:
    text = strip_comments(sections(body).get("Verification", ""))
    cmds = [norm_cmd(m.group(1)) for m in re.finditer(r"^\s*-\s*`([^`]+)`", text, re.M)]
    manual = bool(re.search(r"^\s*-\s*Manual:", text, re.M))
    return cmds, manual


def lint(fm: dict, body: str) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    size = fm.get("size", "M")
    secs = sections(body)
    for name in REQUIRED.get(size, REQUIRED["M"]):
        if name not in secs:
            errors.append(f"missing section: ## {name}")
    oq = strip_comments(secs.get("Open Questions", "")).strip()
    if oq:
        errors.append("## Open Questions is not empty: ask the human, record answers in Intent, delete the section")
    for n, line in enumerate(body.splitlines(), 1):
        if "FILL:" in line:
            errors.append(f"unfilled template marker on body line {n}: {line.strip()[:70]}")
    for name, text in secs.items():
        if name in FREE_TEXT:
            continue
        if re.search(r"\b(TBD|TODO|FIXME)\b", strip_comments(text)):
            errors.append(f"placeholder (TBD/TODO/FIXME) in ## {name}")
    if not FROZEN_RE.search(body):
        errors.append("missing frozen intent block (<!-- frozen:start --> ... <!-- frozen:end -->)")
    if size == "M":
        tasks = [l for l in strip_comments(secs.get("Tasks", "")).splitlines() if re.match(r"^\s*- \[", l)]
        if not tasks:
            errors.append("## Tasks has no `- [ ]` task lines")
        for t in tasks:
            if "`" not in t:
                errors.append(f"task without a `file path`: {t.strip()[:70]}")
        acs = [l for l in strip_comments(secs.get("Acceptance Criteria", "")).splitlines() if re.match(r"^\s*- ", l)]
        if not acs:
            errors.append("## Acceptance Criteria has no bullets")
        for ac in acs:
            if not re.search(r"\bgiven\b.+\bwhen\b.+\bthen\b", ac, re.I):
                errors.append(f"acceptance criterion not Given/When/Then: {ac.strip()[:70]}")
    cmds, manual = verification_commands(body)
    if not cmds and not manual:
        errors.append("## Verification needs a `command` bullet or a `- Manual:` bullet")
    tokens = plan_tokens(body)
    if size == "M" and tokens > 1600:
        warnings.append(f"plan is ~{tokens} tokens (>1600): consider splitting off secondary goals")
    if size == "S" and tokens > 700:
        warnings.append(f"plan is ~{tokens} tokens: this may really be size M")
    if fm.get("risk") not in ("low", "medium", "high"):
        errors.append("risk not set: `shipwright.py set <id> risk=low|medium|high` (business impact if this is wrong)")
    changed = approval_problem(fm, body)
    if changed:
        errors.append(changed)
    return errors, warnings


# ---------- evidence ----------

def key_bytes() -> bytes:
    """Per-machine signing key (override with SHIPWRIGHT_KEY_FILE, e.g. to share a team key)."""
    path = Path(os.environ.get("SHIPWRIGHT_KEY_FILE") or Path.home() / ".config" / "shipwright" / "key")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(secrets.token_hex(32))
        path.chmod(0o600)
    return path.read_text().strip().encode()


def mac_of(rec: dict) -> str:
    body = json.dumps({k: v for k, v in rec.items() if k != "mac"}, sort_keys=True).encode()
    return hmac.new(key_bytes(), body, hashlib.sha256).hexdigest()[:32]


def append_signed(f: Path, rec: dict) -> dict:
    """Append a record chained to the previous line and signed, so hand edits are detectable."""
    lines = [l for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.exists() else []
    rec = {**rec, "prev": hashlib.sha256(lines[-1].encode()).hexdigest()[:16] if lines else "genesis"}
    rec["mac"] = mac_of(rec)
    with f.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    return rec


def chain_problems(f: Path) -> list[str]:
    if not f.exists():
        return []
    prev = "genesis"
    for n, line in enumerate((l for l in f.read_text(encoding="utf-8").splitlines() if l.strip()), 1):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            return [f"{f.name} line {n} is not valid JSON: the file was edited outside shipwright.py"]
        if rec.get("prev") != prev or rec.get("mac") != mac_of(rec):
            return [f"{f.name} line {n} fails its signature or chain: the file was edited outside shipwright.py "
                    "(or signed with another machine's key; see SHIPWRIGHT_KEY_FILE)"]
        prev = hashlib.sha256(line.encode()).hexdigest()[:16]
    return []


def load_evidence(d: Path) -> list[dict]:
    f = d / "evidence.jsonl"
    if not f.exists():
        return []
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def append_log(d: Path, text: str) -> None:
    with (d / "log.md").open("a", encoding="utf-8") as fh:
        fh.write(f"- {now()} {text}\n")


def tree_fp(root: Path, base: str) -> str:
    """Fingerprint of the working tree's change since baseline (tracked diff + untracked files).

    Evidence carries the fingerprint it ran against, so any code change after a passing run makes
    that run stale. Empty without git (then only the build clock applies)."""
    if not base or base == "NO_VCS":
        return ""
    excl = f":(exclude){STATE_DIR}"
    h = hashlib.sha256(git(root, "diff", base, "--", ".", excl).stdout.encode())
    for f in sorted(git(root, "ls-files", "--others", "--exclude-standard", "--", ".", excl).stdout.splitlines()):
        if JUNK_RE.search(f):
            continue
        h.update(f.encode())
        try:
            h.update((root / f).read_bytes())
        except OSError:
            pass
    return h.hexdigest()[:16]


def evidence_gate(fm: dict, body: str, d: Path, root: Path) -> list[str]:
    tampered = chain_problems(d / "evidence.jsonl")
    if tampered:
        return tampered
    since = fm.get("building_since", "")
    allruns = load_evidence(d)
    runs = [r for r in allruns if r["ts"] >= since and not r.get("red")]
    if not runs:
        return ["no verification evidence since the build started: run `shipwright.py verify <id> -- <command>`"]
    fp = tree_fp(root, fm.get("baseline", ""))
    problems = []
    if fp:
        stale = sorted({r["cmd"] for r in runs if r.get("fp") != fp})
        runs = [r for r in runs if r.get("fp") == fp]
        for c in stale:
            if not any(r["cmd"] == c for r in runs):
                problems.append(f"code changed since the last run of: {c} (re-run it)")
    latest = {}
    for r in runs:
        latest[r["cmd"]] = r
    problems += [f"latest run failed (exit {r['exit']}): {c}" for c, r in latest.items() if r["exit"] != 0]
    cmds, manual = verification_commands(body)
    problems += [f"no current passing run for planned check: {c}" for c in cmds
                 if c not in latest and not any(c in p for p in problems)]
    if manual and not any(r.get("manual") for r in runs):
        problems.append("plan lists Manual checks but none recorded against the current code: "
                        "`shipwright.py verify <id> --manual \"what you checked\" --artifact <screenshot or report>`")
    first = fm.get("first_build", "") or since
    future = [r for r in allruns if r.get("ts", "") > now()]
    if future:
        problems.append(f"{len(future)} evidence record(s) have future timestamps: evidence.jsonl was edited by hand")
    if fm.get("type") in ("feature", "bugfix") and not any(
            r.get("red") and r.get("red_ok") and r.get("ts", "") >= first
            and r.get("status") in ("building", "reviewing") for r in allruns):
        problems.append("no red run recorded: test-first means a failing test before the code; record it with "
                        "`shipwright.py verify <id> --expect-fail -- <test command>` (type refactor/chore are exempt)")
    if fm.get("type") == "bugfix":
        log = (d / "log.md").read_text(encoding="utf-8") if (d / "log.md").exists() else ""
        hyps = [h for h in re.findall(r"HYPOTHESIS:(.*)", log) if len(h.split()) >= 6]
        if not hyps:
            problems.append("bugfix without a real root-cause hypothesis (6+ words, e.g. 'X is the root cause "
                            "because Y'): `shipwright.py log <id> \"HYPOTHESIS: ...\"`")
    return problems


TRIVIAL_PROGS = {"false", "true", "exit", "echo", "printf", "test", "[", "sh", "bash", "zsh", ":", "kill", "sleep"}
NOT_RED_RE = re.compile(r"ModuleNotFoundError|ImportError|SyntaxError|NameError|IndentationError|command not found|"
                        r"Cannot find module|ERR_MODULE_NOT_FOUND|no tests ran|No tests found|collected 0 items|"
                        r"error: no test|ReferenceError: \w+ is not defined")
UI_FILE_RE = re.compile(r"\.(tsx|jsx|vue|svelte|astro|html|css|scss|sass|less)$|(^|/)(components|pages|views|screens|ui)/")
LENS_KEYS = {"blind": "blind", "edge": "edge-case", "verification": "verification-gap", "intent": "intent", "rules": "rules"}


def change_size(root: Path, base: str) -> tuple[int, int]:
    """(files, lines) changed since baseline, untracked included; (0, 0) without git."""
    files = changed_files(root, base)
    if not files:
        return 0, 0
    excl = f":(exclude){STATE_DIR}"
    lines = 0
    for l in git(root, "diff", "--numstat", base, "--", ".", excl).stdout.splitlines():
        a, b, *_ = (l.split("\t") + ["0", "0"])[:3]
        lines += (int(a) if a.isdigit() else 0) + (int(b) if b.isdigit() else 0)
    for f in git(root, "ls-files", "--others", "--exclude-standard", "--", ".", excl).stdout.splitlines():
        if not JUNK_RE.search(f):
            try:
                lines += len((root / f).read_text(errors="ignore").splitlines())
            except OSError:
                pass
    return len(files), lines


def ui_gate(root: Path, fm: dict, body: str, d: Path) -> list[str]:
    ui = [f for f in changed_files(root, fm.get("baseline", "")) if UI_FILE_RE.search(f)]
    if not ui:
        return []
    since = fm.get("building_since", "")
    visual = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf", ".html", ".mp4", ".webm")
    if any(r.get("manual") and r.get("ts", "") >= since and str(r.get("artifact", "")).lower().endswith(visual)
           for r in load_evidence(d)):
        return []
    return [f"UI files changed ({', '.join(ui[:3])}{' ...' if len(ui) > 3 else ''}) but no screenshot check recorded: "
            "see disciplines/ui.md, then `shipwright.py verify <id> --manual \"...\" --artifact <screenshot>`"]


def table_cells(row: str) -> list[str]:
    cells = row.strip().replace("\\|", "\x00").strip("|").split("|")
    return [c.replace("\x00", "|").strip() for c in cells]


def triage_gate(body: str, fm: dict | None = None) -> list[str]:
    text = strip_comments(sections(body).get("Review Triage Log", ""))
    rows = [l for l in text.splitlines() if l.strip().startswith("|")]
    rows = [r for r in rows if not re.match(r"^\|[\s\-:|]+\|$", r.strip())]
    rows = [r for r in rows if not re.match(r"^\|\s*#\s*\|", r.strip())]  # header row
    if not rows:
        return ["## Review Triage Log has no rows: every lens finding needs a verdict row "
                "(or one 'no findings' row naming the lenses run)"]
    problems = []
    lenses_seen = set()
    all_keys = {**LENS_KEYS, "security": "security", "ui": "ui-craft", "pr": "pr-review"}
    for r in rows:
        cell = table_cells(r)[1].lower() if len(table_cells(r)) > 1 else ""
        hits = {k for k in all_keys if re.search(rf"\b{k}", cell)}
        if len(hits) > 1:
            problems_multi = f"one lens per triage row, not '{cell}': {r.strip()[:60]}"
            return [problems_multi]
        lenses_seen |= hits
    for r in rows:
        cells = table_cells(r)
        verdict = cells[4].lower() if len(cells) > 4 else ""
        route = cells[5].lower() if len(cells) > 5 else ""
        if verdict == "pending":
            problems.append(f"triage row still pending: {r.strip()[:80]}")
        elif verdict not in VERDICTS:
            problems.append(f"triage row has no valid verdict (column 5): {r.strip()[:80]}")
        elif verdict in ("high", "medium") and route not in ("patch", "bad-plan", "intent-gap", "defer"):
            problems.append(f"a real {verdict} finding must be patched, looped back or deferred, not '{route}': "
                            f"{r.strip()[:80]}")
    if fm is not None and fm.get("size") == "M":
        required = dict(LENS_KEYS)
        if fm.get("risk") == "high":
            required["security"] = "security"
        missing = [name for key, name in required.items() if key not in lenses_seen]
        if missing:
            problems.append(f"no triage row from required lens(es): {', '.join(missing)} (a lens with no findings "
                            "still gets one row: --claim \"no findings\" --verdict false --route -)")
    return problems


# ---------- commands ----------

def cmd_init(a) -> int:
    root = Path(a.root).resolve() if a.root else Path.cwd().resolve()
    s = state(root)
    for sub in ("work", "decisions", "initiatives"):
        (s / sub).mkdir(parents=True, exist_ok=True)
    ctx = s / "context.md"
    if not ctx.exists():
        ctx.write_text((TEMPLATES / "context.md").read_text(encoding="utf-8"), encoding="utf-8")
    dfr = s / "deferred.md"
    if not dfr.exists():
        dfr.write_text("# Deferred work\n\nAppend-only. One entry per deferred goal or finding.\n\n", encoding="utf-8")
    print(f"initialized {s}")
    return 0


def next_id(root: Path) -> str:
    ids = [int(p.name.split("-", 1)[0]) for p in all_items(root) if p.name[:3].isdigit()]
    return f"{(max(ids) + 1) if ids else 1:03d}"


def cmd_new(a) -> int:
    root = find_root(a.root)
    if a.initiative and not (state(root) / "initiatives" / a.initiative).is_dir():
        raise SwError(f"no initiative '{a.initiative}': create it with `shipwright.py initiative`")
    iid = next_id(root)
    d = state(root) / "work" / f"{iid}-{slugify(a.title)}"
    d.mkdir(parents=True)
    body = (TEMPLATES / f"plan-{a.size}.md").read_text(encoding="utf-8").replace("{title}", a.title)
    fm = {
        "id": iid, "title": a.title, "size": a.size, "type": a.type, "status": "draft",
        "risk": a.risk or "", "initiative": a.initiative or "", "after": a.after or "",
        "created": now(), "baseline": "", "building_since": "", "approval_hash": "", "loopbacks": "0",
    }
    write_plan(d, fm, body)
    append_log(d, f"CREATED size={a.size} type={a.type}")
    print(d / "plan.md")
    return 0


def cmd_initiative(a) -> int:
    root = find_root(a.root)
    d = state(root) / "initiatives" / slugify(a.title)
    d.mkdir(parents=True, exist_ok=True)
    for name in ("brief.md", "architecture.md"):
        f = d / name
        if not f.exists():
            f.write_text((TEMPLATES / name).read_text(encoding="utf-8").replace("{title}", a.title), encoding="utf-8")
    print(d)
    return 0


def cmd_check(a) -> int:
    d = item_dir(find_root(a.root), a.id)
    fm, body = read_plan(d)
    errors, warnings = lint(fm, body)
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"{'FAIL' if errors else 'PASS'}  {d.name} (~{plan_tokens(body)} tokens, excluding build logs)")
    return 1 if errors else 0


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def cmd_mark(a) -> int:
    root = find_root(a.root)
    d = item_dir(root, a.id)
    fm, body = read_plan(d)
    cur, new = fm.get("status", "draft"), a.status
    if new not in TRANSITIONS.get(cur, set()):
        allowed = ", ".join(sorted(TRANSITIONS.get(cur, set()))) or "none (terminal)"
        raise SwError(f"cannot go {cur} -> {new}; allowed from {cur}: {allowed}")
    if new in ("blocked", "dropped") and not a.reason:
        raise SwError(f"--reason is required for {new}")
    problems: list[str] = []
    if new == "ready":
        errors, _ = lint({**fm, "approval_hash": ""}, body)
        problems += errors
        if fm.get("initiative"):
            problems += [f"initiative not approved-ready: {e}" for e in lint_initiative(root, fm["initiative"])]
        if (fm.get("size") == "M" or fm.get("initiative")) and not a.approved_by:
            problems.append("size M and initiative slices need an explicit approver: `mark <id> ready --approved-by "
                            "<the human's name>` (auto mode: --approved-by auto-ruling, and log the RULING)")
        fm["approval_hash"] = approval_hash(fm, body)
        fm["approved_by"] = a.approved_by or "self (size S)"
    elif new == "building":
        # every path into building needs a current approval: blocked -> building cannot skip `ready`
        if not fm.get("approval_hash"):
            raise SwError("not approved: run `check`, get approval, then `mark <id> ready`")
        problems += lint(fm, body)[0]
        if fm.get("building_since"):  # any re-entry (after review, blocked, or re-approval) is a loopback
            loops = int(fm.get("loopbacks", "0") or 0) + 1
            if loops > MAX_LOOPBACKS:
                raise SwError(f"loopback cap ({MAX_LOOPBACKS}) reached: "
                              "`mark <id> blocked --reason ...` and escalate to the human")
            fm["loopbacks"] = str(loops)
        if not fm.get("first_build"):
            fm["first_build"] = now()
        if not fm.get("baseline"):
            r = git(root, "rev-parse", "HEAD")
            fm["baseline"] = r.stdout.strip() if r.returncode == 0 else "NO_VCS"
            dirty = dirty_files(root) if r.returncode == 0 else []
            if dirty and not a.allow_dirty:
                raise SwError("working tree has uncommitted changes outside .shipwright/ "
                              f"({', '.join(dirty[:5])}{' ...' if len(dirty) > 5 else ''}); they would be reviewed "
                              "and blamed on this item. Commit or stash them, or pass --allow-dirty --reason \"...\"")
            if dirty:
                if not a.reason:
                    raise SwError("--allow-dirty needs --reason")
                append_log(d, f"DIRTY-BASELINE {len(dirty)} files: {a.reason}")
        fm["building_since"] = now()
    elif new in ("verified", "done"):
        if new == "verified" and cur == "building" and fm.get("size") != "S":
            raise SwError("size M must pass review first: `mark <id> reviewing`")
        changed = approval_problem(fm, body)
        if changed or not fm.get("approval_hash"):
            problems.append(changed or "not approved")
        problems += evidence_gate(fm, body, d, root)
        problems += ui_gate(root, fm, body, d)
        reviewed = fm.get("size") != "S" or (new == "verified" and cur == "reviewing")
        if not reviewed:
            files, lines = change_size(root, fm.get("baseline", ""))
            if fm.get("risk") == "high" or files > 3 or lines > 100:
                problems.append(f"too big or risky to skip review as size S (risk={fm.get('risk')}, {files} files, "
                                f"{lines} lines): `mark <id> reviewing` and run the lenses")
        if reviewed:
            problems += triage_gate(body, fm)
            if fm.get("size") == "M" and fm.get("baseline") not in ("", "NO_VCS") \
                    and fm.get("review_ts", "") < fm.get("building_since", ""):
                problems.append("no review diff for the current build round: run `shipwright.py diff <id>` and the lenses")
    elif new == "draft":
        fm["approval_hash"] = ""
    if new in ("verified", "done"):
        problems += [f"changed file not named in Tasks, Code Map or Implementation Notes: {f} "
                     "(declare it with the reason, or revert it)" for f in scope_creep(root, fm, body)]
    if problems:
        print(f"REFUSED {cur} -> {new}:")
        for p in problems:
            print(f"  - {p}")
        return 1
    fm["status"] = new
    if new == "done":
        fm["done_at"] = now()
        fm["change_files"], fm["change_lines"] = (str(x) for x in change_size(root, fm.get("baseline", "")))
    write_plan(d, fm, body)
    append_log(d, f"STATUS {cur} -> {new}" + (f" ({a.reason})" if a.reason else ""))
    print(f"{d.name}: {cur} -> {new}")
    return 0


def dirty_files(root: Path) -> list[str]:
    out = git(root, "status", "--porcelain", "--untracked-files=all").stdout.splitlines()
    files = [l[3:] for l in out if l[3:]]
    return [f for f in files if not f.startswith(STATE_DIR + "/") and not JUNK_RE.search(f)]


def changed_files(root: Path, base: str) -> list[str]:
    if not base or base == "NO_VCS":
        return []
    excl = f":(exclude){STATE_DIR}"
    files = git(root, "diff", "--name-only", base, "--", ".", excl).stdout.splitlines()
    files += git(root, "ls-files", "--others", "--exclude-standard", "--", ".", excl).stdout.splitlines()
    return sorted({f for f in files if f and not JUNK_RE.search(f)})


def scope_creep(root: Path, fm: dict, body: str) -> list[str]:
    secs = sections(body)
    named = " ".join(secs.get(n, "") for n in ("Tasks", "Code Map", "Implementation Notes", "Verification"))
    return [f for f in changed_files(root, fm.get("baseline", "")) if f not in named]


def cmd_verify(a) -> int:
    root = find_root(a.root)
    d = item_dir(root, a.id)
    fm, body = read_plan(d)
    fp = tree_fp(root, fm.get("baseline", ""))
    if a.manual and a.cmd:
        raise SwError("give either --manual or a command, not both")
    if a.manual:
        if not a.artifact:
            raise SwError("--manual needs --artifact <path>: the screenshot, report or log that shows what you saw")
        art = (root / a.artifact) if not Path(a.artifact).is_absolute() else Path(a.artifact)
        if not art.is_file() or art.stat().st_size == 0:
            raise SwError(f"artifact not found or empty: {art}")
        if art.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf", ".html", ".json",
                                      ".txt", ".log", ".md", ".mp4", ".webm", ".har"):
            raise SwError(f"artifact must be a screenshot, recording, report or log, not {art.suffix or 'no extension'}")
        since = fm.get("building_since", "")
        made = dt.datetime.fromtimestamp(art.stat().st_mtime).isoformat(timespec="seconds")
        if since and made < since:
            raise SwError(f"artifact predates this build round ({made} < {since}): capture a fresh one")
        digest = hashlib.sha256(art.read_bytes()).hexdigest()[:16]
        rec = {"ts": now(), "cmd": f"manual: {a.manual}", "exit": 0, "manual": True, "tail": "",
               "artifact": str(art), "artifact_sha": digest, "fp": fp}
        print(f"recorded manual check: {a.manual} (artifact {art})")
        rc = 0
    else:
        cmd = norm_cmd(" ".join(a.cmd))
        if not cmd:
            raise SwError("give a command after `--`, or --manual \"...\"")
        try:
            # shell=True on purpose: checks are the project's own commands (e.g. `npm test && npm run lint`),
            # written by the agent/human driving the build, with the same trust as their own terminal.
            r = subprocess.run(cmd, shell=True, cwd=root, capture_output=True, text=True, timeout=a.timeout)
            out, rc = (r.stdout + r.stderr), r.returncode
        except subprocess.TimeoutExpired:
            out, rc = f"timed out after {a.timeout}s", 124
        tail = "\n".join(out.splitlines()[-30:])
        rec = {"ts": now(), "cmd": cmd, "exit": rc, "tail": tail, "fp": fp, "status": fm.get("status", "")}
        print(tail)
        if a.expect_fail:
            rec["red"] = True
            planned, _ = verification_commands(body)
            prog = cmd.split()[0] if cmd.split() else ""
            unbound = prog in TRIVIAL_PROGS or (planned and prog not in {c.split()[0] for c in planned if c.split()})
            bad = NOT_RED_RE.search(out) or rc in (124, 126, 127) or ("pytest" in cmd and rc != 1) or unbound
            if rc != 0 and bad:
                print(f"NOT RED: the command failed for the wrong reason (exit {rc}): {cmd}\n"
                      "A red run must use the plan's test runner (same program as a ## Verification command), "
                      "not false/exit/echo.\n"
                      "Import/syntax/name errors, missing commands, timeouts, or 'no tests ran' never reach the "
                      "behavior. Add a stub so the test reaches its assertion (disciplines/tdd.md).")
                rec["red_ok"] = False
                rc = 1
            elif rc == 0:
                print(f"NOT RED: expected a failing test but it passed: {cmd}\n"
                      "The test does not reach the missing behavior yet (see disciplines/tdd.md).")
                rec["red_ok"] = False
                rc = 1
            else:
                print(f"RED (expected failure, exit {rc}): {cmd}\n"
                      "Check the failure is the assertion on the missing behavior, not an import/syntax error.")
                rec["red_ok"] = True
                rc = 0
        else:
            print(f"{'PASS' if rc == 0 else 'FAIL'} (exit {rc}): {cmd}")
    append_signed(d / "evidence.jsonl", rec)
    tag = "RED" if rec.get("red") else "EVIDENCE"
    append_log(d, f"{tag} exit={rec['exit']} {rec['cmd']}")
    return rc


SETTABLE = {"risk", "after", "initiative", "size", "type", "title", "fixes"}
DRAFT_ONLY = {"size", "type", "title"}
CHOICES = {"risk": ("low", "medium", "high"), "size": ("S", "M"), "type": ("feature", "bugfix", "refactor", "chore")}


def cmd_set(a) -> int:
    root = find_root(a.root)
    d = item_dir(root, a.id)
    fm, body = read_plan(d)
    for pair in a.pairs:
        if "=" not in pair:
            raise SwError(f"expected key=value, got {pair}")
        k, v = pair.split("=", 1)
        if k not in SETTABLE:
            raise SwError(f"cannot set {k}; settable: {', '.join(sorted(SETTABLE))}")
        if k in DRAFT_ONLY and fm.get("status") != "draft":
            raise SwError(f"{k} is part of the approved plan; `mark <id> draft` first")
        if k in CHOICES and v not in CHOICES[k]:
            raise SwError(f"{k} must be one of {', '.join(CHOICES[k])}")
        if k == "initiative" and v and not (state(root) / "initiatives" / v).is_dir():
            raise SwError(f"no initiative '{v}'")
        fm[k] = v
        append_log(d, f"SET {k}={v}")
    write_plan(d, fm, body)
    if any(p.startswith("size=") for p in a.pairs):
        print(f"size changed: copy any missing sections from {TEMPLATES}/plan-{fm['size']}.md, then `check`")
    return 0


def cmd_diff(a) -> int:
    root = find_root(a.root)
    if a.initiative:
        rows = [r for r in item_rows(root) if r.get("initiative") == a.initiative]
        bases = [r["baseline"] for r in rows if r.get("baseline") and r["baseline"] != "NO_VCS"]
        if not bases:
            raise SwError(f"no built items with a git baseline in initiative '{a.initiative}'")
        # earliest baseline = the one that is an ancestor of all the others
        base = next((b for b in bases if all(git(root, "merge-base", "--is-ancestor", b, o).returncode == 0
                                             for o in bases)), bases[0])
        d = state(root) / "initiatives" / a.initiative
    else:
        if not a.id:
            raise SwError("give an item id, or --initiative <slug>")
        d = item_dir(root, a.id)
        fm, _ = read_plan(d)
        base = fm.get("baseline", "")
    if not base or base == "NO_VCS":
        raise SwError("no git baseline recorded: describe the changed files to reviewers instead")
    excl = f":(exclude){STATE_DIR}"
    parts = [git(root, "diff", base, "--", ".", excl).stdout]
    untracked = git(root, "ls-files", "--others", "--exclude-standard", "--", ".", excl).stdout.splitlines()
    for f in untracked:
        if JUNK_RE.search(f):
            continue
        parts.append(git(root, "diff", "--no-index", "--", "/dev/null", f).stdout)
    out = d / "review" / "diff.patch"
    out.parent.mkdir(exist_ok=True)
    if not a.initiative:
        fm2, body2 = read_plan(d)
        fm2["review_ts"] = now()
        write_plan(d, fm2, body2)
    out.write_text("".join(parts), encoding="utf-8")
    print(f"{out} ({out.stat().st_size / 1024:.1f} kB)")
    return 0


def cmd_triage(a) -> int:
    d = item_dir(find_root(a.root), a.id)
    fm, body = read_plan(d)
    cell = lambda s: " ".join(str(s).split()).replace("|", "\\|")
    lines = body.split("\n")
    start = next((i for i, l in enumerate(lines) if re.match(r"^## Review Triage Log\s*$", l)), None)
    if start is None:
        lines += ["", "## Review Triage Log", ""]
        start = len(lines) - 2
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    table = [i for i in range(start + 1, end) if lines[i].strip().startswith("|")]
    if not table:
        hdr = ["| # | Lens | Location | Claim | Verdict | Route | Evidence / action |",
               "|---|---|---|---|---|---|---|"]
        lines[start + 1:start + 1] = [""] + hdr
        table = [start + 2, start + 3]
    n = sum(1 for i in table if re.match(r"^\|\s*\d+\s*\|", lines[i].strip())) + 1
    row = f"| {n} | {cell(a.lens)} | {cell(a.location)} | {cell(a.claim)} | {a.verdict} | {a.route} | {cell(a.evidence)} |"
    lines.insert(table[-1] + 1, row)
    write_plan(d, fm, "\n".join(lines))
    print(row)
    return 0


# ---------- DORA delivery metrics ----------
# Five metrics (DORA 2024+): throughput = change lead time, deployment frequency, failed deployment
# recovery time; instability = change failure rate, deployment rework rate. Recorded from Shipwright's
# own state: work items + .shipwright/deploys.jsonl (signed, append-only).

def deploy_events(root: Path) -> list[dict]:
    f = state(root) / "deploys.jsonl"
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.exists() else []


def cmd_deploy(a) -> int:
    root = find_root(a.root)
    rows = {r["id"]: r for r in item_rows(root)}
    items = [x.strip().zfill(3) for x in a.items.split(",") if x.strip()]
    for i in items:
        if rows.get(i, {}).get("status") not in ("verified", "done"):
            raise SwError(f"item {i} is not verified/done: only verified work is deployed")
    deploys = [e for e in deploy_events(root) if e["event"] == "deploy"]
    did = f"D{len(deploys) + 1:03d}"
    fixes_deployed = all(rows[i].get("type") == "bugfix" and rows[i].get("fixes") for i in items)
    rec = {"event": "deploy", "id": did, "ts": now(), "env": a.env, "items": items,
           "ref": a.ref or git(root, "rev-parse", "HEAD").stdout.strip(), "rework": bool(a.rework or fixes_deployed)}
    append_signed(state(root) / "deploys.jsonl", rec)
    print(f"{did} deployed to {a.env}: {', '.join(items)}{' (rework)' if rec['rework'] else ''}")
    return 0


def cmd_deploy_event(a) -> int:
    root = find_root(a.root)
    ids = {e["id"] for e in deploy_events(root) if e["event"] == "deploy"}
    if a.deploy_id not in ids:
        raise SwError(f"no deploy {a.deploy_id}")
    rec = {"event": a.event, "id": a.deploy_id, "ts": now(), "note": a.reason}
    append_signed(state(root) / "deploys.jsonl", rec)
    print(f"{a.deploy_id}: {a.event}")
    return 0


def _parse(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(ts)


def _hours(xs: list[float]) -> str:
    if not xs:
        return "n/a"
    med = statistics.median(xs)
    return f"{med:.1f} h median" if med < 48 else f"{med / 24:.1f} d median"


def dora_metrics(root: Path, days: int, env: str) -> dict:
    since = (dt.datetime.now() - dt.timedelta(days=days)).isoformat(timespec="seconds")
    events = deploy_events(root)
    deploys = [e for e in events if e["event"] == "deploy" and e["ts"] >= since and e["env"] == env]
    failed = {e["id"]: e for e in events if e["event"] == "failed"}
    recovered = {e["id"]: e for e in events if e["event"] == "recovered"}
    rows = {r["id"]: r for r in item_rows(root)}
    lead = []
    for e in deploys:
        for i in e["items"]:
            start = rows.get(i, {}).get("first_build") or rows.get(i, {}).get("created")
            if start:
                lead.append((_parse(e["ts"]) - _parse(start)).total_seconds() / 3600)
    n = len(deploys)
    fails = [e for e in deploys if e["id"] in failed]
    recov = [(_parse(recovered[e["id"]]["ts"]) - _parse(failed[e["id"]]["ts"])).total_seconds() / 3600
             for e in fails if e["id"] in recovered]
    done = [r for r in rows.values() if r.get("status") == "done" and (r.get("done_at") or "") >= since]
    lines = [int(r["change_lines"]) for r in done if str(r.get("change_lines", "")).isdigit()]
    escaped = [r for r in rows.values() if r.get("type") == "bugfix" and r.get("fixes")]
    return {
        "window_days": days, "env": env, "deploys": n,
        "deployment_frequency_per_week": round(n / (days / 7), 2) if days else 0,
        "change_lead_time": _hours(lead),
        "change_failure_rate": round(len(fails) / n, 3) if n else None,
        "failed_deployment_recovery_time": _hours(recov),
        "unrecovered_failures": len([e for e in fails if e["id"] not in recovered]),
        "deployment_rework_rate": round(sum(1 for e in deploys if e.get("rework")) / n, 3) if n else None,
        "batch_size_lines_median": statistics.median(lines) if lines else None,
        "review_loopbacks_per_item": round(sum(int(r.get("loopbacks") or 0) for r in done) / len(done), 2) if done else None,
        "escaped_defects": len(escaped), "items_done": len(done),
    }


def cmd_metrics(a) -> int:
    m = dora_metrics(find_root(a.root), a.days, a.env)
    if a.json:
        print(json.dumps(m, indent=2))
        return 0
    pct = lambda v: "n/a" if v is None else f"{v * 100:.0f}%"
    print(f"DORA delivery metrics: last {m['window_days']} days, env={m['env']} ({m['deploys']} deploys)\n")
    print("Throughput")
    print(f"  Deployment frequency         {m['deployment_frequency_per_week']} / week")
    print(f"  Change lead time             {m['change_lead_time']}  (first build -> deployed)")
    print(f"  Failed deploy recovery time  {m['failed_deployment_recovery_time']}  "
          f"(unrecovered: {m['unrecovered_failures']})")
    print("Instability")
    print(f"  Change failure rate          {pct(m['change_failure_rate'])}")
    print(f"  Deployment rework rate       {pct(m['deployment_rework_rate'])}  (unplanned deploys fixing incidents)")
    print("Shipwright signals (leading indicators)")
    print(f"  Batch size                   {m['batch_size_lines_median'] or 'n/a'} changed lines per item (median)")
    print(f"  Review loopbacks             {m['review_loopbacks_per_item'] if m['review_loopbacks_per_item'] is not None else 'n/a'} per item")
    print(f"  Escaped defects              {m['escaped_defects']} bugfix items linked to shipped work "
          f"({m['items_done']} items done)")
    print("\nReference points often cited from DORA reports (approximate; DORA 2025 dropped fixed tiers):\n"
          "  on-demand deploys, lead time < 1 day, change failure rate ~5% or less, recovery < 1 hour.")
    return 0


def cmd_friction(a) -> int:
    root = find_root(a.root)
    found = 0
    for d in all_items(root):
        log = d / "log.md"
        for line in (log.read_text(encoding="utf-8").splitlines() if log.exists() else []):
            if "FRICTION:" in line:
                print(f"{d.name}: {line[2:]}")
                found += 1
    if not found:
        print("no FRICTION lines logged")
    return 0


COUNCIL_ROUNDS = ("round-1", "round-2", "round-3")


def council_dir(root: Path, ref: str) -> Path:
    base = state(root) / "councils"
    hits = sorted(base.glob(f"{ref}*")) or sorted(base.glob(f"*-{ref}*"))
    if not hits:
        raise SwError(f"no council matching '{ref}' in {base}")
    return hits[0]


def cmd_council_new(a) -> int:
    root = find_root(a.root)
    base = state(root) / "councils"
    base.mkdir(parents=True, exist_ok=True)
    nums = [int(p.name[:2]) for p in base.iterdir() if p.is_dir() and p.name[:2].isdigit()]
    d = base / f"{(max(nums) + 1) if nums else 1:02d}-{slugify(a.question)}"
    for r in COUNCIL_ROUNDS:
        (d / r).mkdir(parents=True)
    for src, dst in (("council-brief.md", "brief.md"), ("solution-design.md", "decision.md")):
        (d / dst).write_text((TEMPLATES / src).read_text(encoding="utf-8").replace("{title}", a.question),
                             encoding="utf-8")
    print(d)
    return 0


def lint_council_brief(text: str) -> list[str]:
    errs = [f"brief: missing section ## {n}" for n in
            ("Question", "Problem", "Constraints", "Quality scenarios", "Evidence") if n not in sections(text)]
    if "FILL" in strip_comments(text):
        errs.append("brief: unfilled FILL markers")
    qs = [l for l in sections(text).get("Quality scenarios", "").splitlines() if re.match(r"^\|\s*Q\d+", l)]
    if len(qs) < 3:
        errs.append(f"brief: needs at least 3 quality scenarios (Q1..), found {len(qs)}")
    return errs


MEMBER_NAME_RE = re.compile(r"(?:sw|shipwright)-[a-z-]+|principal (solution )?architect|ai engineer|staff engineer|design lead|"
                            r"red team|ui designer", re.I)


def lint_council_rounds(d: Path) -> list[str]:
    """Positions are saved by the moderator under anonymous labels (A.md, B.md ...); key.md maps them last."""
    errs = []
    label = re.compile(r"^[A-Z]\.md$")
    counts = {}
    for r in COUNCIL_ROUNDS:
        members = [f for f in (d / r).glob("*.md") if label.match(f.name) and f.stat().st_size > 200]
        counts[r] = len(members)
        if len(members) < 3:
            errs.append(f"{r}: needs positions from at least 3 members saved as A.md, B.md, ... (found {len(members)})")
        if r == "round-3":
            errs += [f"{r}/{f.name}: no '## Dissent' heading" for f in members
                     if not re.search(r"^#+\s*Dissent", f.read_text(), re.M | re.I)]
        if r != "round-1":
            inp = d / r / "input.md"
            if not inp.exists():
                errs.append(f"{r}: no input.md (the anonymized positions the members read)")
            elif MEMBER_NAME_RE.search(inp.read_text()):
                errs.append(f"{r}/input.md names a member or role: anonymize it (Position A, B, ...)")
    if counts and len(set(counts.values())) > 1:
        errs.append(f"rounds have different member counts {counts}: every member takes part in every round")
    judge = d / "judge.md"
    if not judge.exists() or not re.search(r"\|\s*[1-5](\.\d+)?\s*\|", judge.read_text()):
        errs.append("judge.md missing or without a numeric score matrix: save the shipwright-council-judge output there")
    key = d / "key.md"
    if not key.exists() or len(re.findall(r"^\s*-?\s*[A-Z]\s*[:=-]", key.read_text(), re.M)) < 3:
        errs.append("key.md missing: after round 3, map each label to its member (- A: shipwright-red-team)")
    return errs


def lint_decision(text: str) -> list[str]:
    secs = sections(text)
    errs = []
    for n in ("Options", "Evaluation", "Decision", "Architecture", "Well-Architected review", "Risks", "Dissent"):
        if n not in secs:
            errs.append(f"decision: missing section ## {n}")
        elif len(strip_comments(secs[n]).split()) < 3 and n != "Options":
            errs.append(f"decision: ## {n} is empty")
    if "FILL" in strip_comments(text):
        errs.append("decision: unfilled FILL markers")
    opts = re.findall(r"^### Option[^\n]*\n(.*?)(?=^### |^## |\Z)", text, re.M | re.S)
    if len([o for o in opts if len(strip_comments(o).split()) >= 15]) < 2:
        errs.append("decision: needs at least 2 fundamentally different options, each described (15+ words)")
    ev_rows = [l for l in strip_comments(secs.get("Evaluation", "")).splitlines()
               if l.strip().startswith("|") and not re.match(r"^\|[\s\-:|]+\|$", l.strip())][1:]
    if not any(re.search(r"\|\s*[1-5](\.\d+)?\s*\|", l) for l in ev_rows):
        errs.append("decision: ## Evaluation has no numeric scores (score each option 1-5 per quality scenario)")
    return errs


def lint_initiative(root: Path, slug: str) -> list[str]:
    d = state(root) / "initiatives" / slug
    if not d.is_dir():
        return [f"no initiative '{slug}'"]
    brief = (d / "brief.md").read_text(encoding="utf-8")
    arch = (d / "architecture.md").read_text(encoding="utf-8")
    errs = [f"{n}: unfilled FILL markers" for n, t in (("brief", brief), ("architecture", arch))
            if "FILL" in strip_comments(t)]
    reqs = sorted(set(re.findall(r"\bR\d+\b", strip_comments(sections(brief).get("Scope", brief)))), key=lambda x: int(x[1:]))
    if not reqs:
        errs.append("brief: no numbered requirements (R1, R2, ...) under Scope")
    slices = strip_comments(sections(arch).get("Slices", ""))
    covered = set(re.findall(r"\bR\d+\b", " ".join(l for l in slices.splitlines() if "covers" in l.lower())))
    missing = [r for r in reqs if r not in covered]
    if missing:
        errs.append(f"architecture: requirements not covered by any slice: {', '.join(missing)}")
    m = re.search(r"council:\s*`?([\w.-]+)`?", arch, re.I)
    if not m:
        errs.append("architecture: no `Council: <council folder>` line (size L decisions go through the council)")
    else:
        try:
            cd = council_dir(root, m.group(1))
            cerrs = lint_council_brief((cd / "brief.md").read_text()) + lint_council_rounds(cd) + \
                lint_decision((cd / "decision.md").read_text())
            errs += [f"council {cd.name}: {e}" for e in cerrs]
        except SwError as e:
            errs.append(str(e))
    return errs


def cmd_initiative_check(a) -> int:
    errs = lint_initiative(find_root(a.root), a.slug)
    for e in errs:
        print(f"ERROR {e}")
    print(f"{'FAIL' if errs else 'PASS'}  initiative {a.slug}")
    return 1 if errs else 0


def cmd_council_check(a) -> int:
    root = find_root(a.root)
    d = council_dir(root, a.ref)
    errs = lint_council_brief((d / "brief.md").read_text(encoding="utf-8"))
    if not a.brief:
        errs += lint_council_rounds(d) + lint_decision((d / "decision.md").read_text(encoding="utf-8"))
    for e in errs:
        print(f"ERROR {e}")
    print(f"{'FAIL' if errs else 'PASS'}  {d.name} ({'brief' if a.brief else 'full council'})")
    return 1 if errs else 0


def cmd_log(a) -> int:
    d = item_dir(find_root(a.root), a.id)
    append_log(d, a.text)
    return 0


def item_rows(root: Path) -> list[dict]:
    rows = []
    for d in all_items(root):
        fm, _ = read_plan(d)
        log = (d / "log.md").read_text(encoding="utf-8").splitlines() if (d / "log.md").exists() else []
        rows.append({**fm, "dir": d, "last": log[-1][2:] if log else ""})
    return rows


def cmd_status(a) -> int:
    root = find_root(a.root)
    rows = item_rows(root)
    if not rows:
        print("no work items")
    for r in rows:
        if a.active and r.get("status") in ("done", "dropped"):
            continue
        ini = f" [{r['initiative']}]" if r.get("initiative") else ""
        print(f"{r['id']}  {r.get('status', '?'):<9} {r.get('size', '?')}  {r.get('title', '')}{ini}")
    return 0


def deps_done(r: dict, by_id: dict) -> bool:
    deps = [x.strip().zfill(3) for x in r.get("after", "").split(",") if x.strip()]
    return all(by_id.get(x, {}).get("status") == "done" for x in deps)


def cmd_next(a) -> int:
    rows = item_rows(find_root(a.root))
    by_id = {r["id"]: r for r in rows}
    for wanted in ("building", "reviewing", "verified", "ready", "draft"):
        for r in rows:
            if r.get("status") == wanted and deps_done(r, by_id):
                print(f"{r['id']}  {wanted}  {r['title']}\n  next: {NEXT_HINT[wanted]}\n  plan: {r['dir'] / 'plan.md'}")
                for dep in [x.strip().zfill(3) for x in r.get("after", "").split(",") if x.strip()]:
                    if dep in by_id:
                        print(f"  read first (built before this; reuse its Code Map/Design Notes): "
                              f"{by_id[dep]['dir'] / 'plan.md'}")
                return 0
    print("nothing actionable (all done, dropped, blocked, or waiting on dependencies)")
    return 0


def cmd_resume(a) -> int:
    root = find_root(a.root)
    s = state(root)
    print(f"project context: {s / 'context.md'}  (read it first)")
    rows = [r for r in item_rows(root) if r.get("status") not in ("done", "dropped")]
    by_id = {r["id"]: r for r in item_rows(root)}
    if not rows:
        print("no open work items")
    for r in rows:
        st = r.get("status", "?")
        hint = NEXT_HINT.get(st, "")
        if st == "blocked":
            hint = "blocked: see last log line; needs the human"
        elif not deps_done(r, by_id):
            hint = f"waiting on {r.get('after')}"
        print(f"{r['id']} {st:<9} {r.get('size')} {r.get('title')}\n    last: {r['last']}\n    next: {hint}")
    dfr = s / "deferred.md"
    if dfr.exists():
        n = sum(1 for l in dfr.read_text(encoding="utf-8").splitlines() if l.startswith("- source:"))
        print(f"deferred entries: {n} ({dfr})")
    return 0


def cmd_adr(a) -> int:
    root = find_root(a.root)
    dd = state(root) / "decisions"
    dd.mkdir(parents=True, exist_ok=True)
    nums = [int(m.group(1)) for p in dd.glob("ADR-*.md") if (m := re.match(r"ADR-(\d+)", p.name))]
    n = (max(nums) + 1) if nums else 1
    f = dd / f"ADR-{n:04d}-{slugify(a.title)}.md"
    body = (TEMPLATES / "adr.md").read_text(encoding="utf-8")
    f.write_text(body.replace("{title}", a.title).replace("{n}", f"{n:04d}").replace("{date}", now()[:10]),
                 encoding="utf-8")
    print(f)
    return 0


def cmd_defer(a) -> int:
    root = find_root(a.root)
    with (state(root) / "deferred.md").open("a", encoding="utf-8") as fh:
        fh.write(f"- source: {a.source}\n  date: {now()[:10]}\n  summary: {a.summary}\n  evidence: {a.evidence}\n")
    print("deferred")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="shipwright.py", description=__doc__.splitlines()[0])
    p.add_argument("--root", help="project root (default: nearest folder with .shipwright/)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="create .shipwright/ in the current folder").set_defaults(fn=cmd_init)
    s = sub.add_parser("new", help="create a work item with a plan from the template")
    s.add_argument("title")
    s.add_argument("--size", choices=["S", "M"], required=True)
    s.add_argument("--type", choices=["feature", "bugfix", "refactor", "chore"], default="feature")
    s.add_argument("--after", help="comma-separated item ids this one waits on")
    s.add_argument("--initiative", help="initiative slug this item belongs to")
    s.add_argument("--risk", choices=["low", "medium", "high"])
    s.set_defaults(fn=cmd_new)
    s = sub.add_parser("initiative", help="create brief.md + architecture.md for a large effort")
    s.add_argument("title")
    s.set_defaults(fn=cmd_initiative)
    s = sub.add_parser("initiative-check", help="lint an initiative: requirements covered, council passed")
    s.add_argument("slug")
    s.set_defaults(fn=cmd_initiative_check)
    s = sub.add_parser("check", help="lint a plan against the Ready-to-Build standard")
    s.add_argument("id")
    s.set_defaults(fn=cmd_check)
    s = sub.add_parser("mark", help="change status; gates refuse unsafe transitions")
    s.add_argument("id")
    s.add_argument("status", choices=sorted(TRANSITIONS))
    s.add_argument("--reason", default="")
    s.add_argument("--allow-dirty", action="store_true", help="start building on a dirty tree (needs --reason)")
    s.add_argument("--approved-by", default="", help="who approved the plan (required for M at `ready`)")
    s.set_defaults(fn=cmd_mark)
    s = sub.add_parser("verify", help="run a check and record evidence (or --manual)")
    s.add_argument("id")
    s.add_argument("--manual", help="record a manual check you performed (needs --artifact)")
    s.add_argument("--artifact", help="screenshot/report/log proving the manual check")
    s.add_argument("--expect-fail", action="store_true", help="record a RED run: the test must fail before the code exists")
    s.add_argument("--timeout", type=int, default=900)
    s.add_argument("cmd", nargs="*", help="the check to run, after `--`")
    s.set_defaults(fn=cmd_verify)
    s = sub.add_parser("set", help="set frontmatter fields: risk, after, initiative (and size/type/title while draft)")
    s.add_argument("id")
    s.add_argument("pairs", nargs="+", metavar="key=value")
    s.set_defaults(fn=cmd_set)
    s = sub.add_parser("diff", help="write the change since baseline to review/diff.patch")
    s.add_argument("id", nargs="?")
    s.add_argument("--initiative", help="whole-initiative diff (earliest slice baseline to now) for the L review")
    s.set_defaults(fn=cmd_diff)
    s = sub.add_parser("log", help="append a line to the item's log (DECISION:, RULING:, HYPOTHESIS:...)")
    s.add_argument("id")
    s.add_argument("text")
    s.set_defaults(fn=cmd_log)
    s = sub.add_parser("triage", help="append one finding row to the plan's Review Triage Log")
    s.add_argument("id")
    s.add_argument("--lens", required=True)
    s.add_argument("--location", required=True, help="file:line, or - ")
    s.add_argument("--claim", required=True)
    s.add_argument("--verdict", required=True, choices=VERDICTS)
    s.add_argument("--route", required=True, choices=ROUTES)
    s.add_argument("--evidence", required=True, help="refutation, what would settle it, or the action taken")
    s.set_defaults(fn=cmd_triage)
    s = sub.add_parser("council", help="expert council for high-stakes decisions (see phases/council.md)")
    csub = s.add_subparsers(dest="council_cmd", required=True)
    c = csub.add_parser("new", help="create a council folder with brief.md, decision.md and round folders")
    c.add_argument("question")
    c.set_defaults(fn=cmd_council_new)
    c = csub.add_parser("check", help="lint the brief (--brief) or the whole council record")
    c.add_argument("ref", help="council number or slug")
    c.add_argument("--brief", action="store_true")
    c.set_defaults(fn=cmd_council_check)
    s = sub.add_parser("deploy", help="record a deployment of verified items (DORA)")
    s.add_argument("--items", required=True, help="comma-separated item ids")
    s.add_argument("--env", default="production")
    s.add_argument("--ref", default="", help="deployed commit (default: HEAD)")
    s.add_argument("--rework", action="store_true", help="unplanned deploy fixing a production incident")
    s.set_defaults(fn=cmd_deploy)
    for ev, hlp in (("failed", "the deployment caused a production failure"),
                    ("recovered", "service restored after that failure (fix deployed or rolled back)")):
        s = sub.add_parser(f"deploy-{ev}", help=hlp)
        s.add_argument("deploy_id")
        s.add_argument("--reason", default="")
        s.set_defaults(fn=cmd_deploy_event, event=ev)
    s = sub.add_parser("metrics", help="DORA delivery metrics + Shipwright leading indicators")
    s.add_argument("--days", type=int, default=30)
    s.add_argument("--env", default="production")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_metrics)
    sub.add_parser("friction", help="list FRICTION: lines from all item logs").set_defaults(fn=cmd_friction)
    s = sub.add_parser("status", help="list work items")
    s.add_argument("--active", action="store_true")
    s.set_defaults(fn=cmd_status)
    sub.add_parser("next", help="the next actionable item").set_defaults(fn=cmd_next)
    sub.add_parser("resume", help="orientation for a new session").set_defaults(fn=cmd_resume)
    s = sub.add_parser("adr", help="create a numbered decision record")
    s.add_argument("title")
    s.set_defaults(fn=cmd_adr)
    s = sub.add_parser("defer", help="append deferred work")
    s.add_argument("summary")
    s.add_argument("--source", required=True)
    s.add_argument("--evidence", required=True)
    s.set_defaults(fn=cmd_defer)

    a = p.parse_args(argv)
    try:
        return a.fn(a)
    except SwError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
