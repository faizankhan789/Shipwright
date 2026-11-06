"""JSX-aware UI checks for .tsx/.jsx (stdlib only, runs on every OS).

The compiled design engine reads these files as plain text, so it can't see inline style objects or colour pairs
on one element. These rules parse each JSX tag and check what can be decided without rendering:
gradient text, contrast, tiny text, justified text, missing alt text and labels, removed focus outlines.

Colours set in other components or CSS files can't be resolved statically: a clean result here is not a rendered
check. Scan built HTML or a running dev-server URL for that. Findings use the engine's JSON shape.
A `shipwright-disable` comment on the same or previous line silences that line.
"""
from __future__ import annotations

import re

GRAYS = {
    "gray": "f9fafb f3f4f6 e5e7eb d1d5db 9ca3af 6b7280 4b5563 374151 1f2937 111827 030712",
    "slate": "f8fafc f1f5f9 e2e8f0 cbd5e1 94a3b8 64748b 475569 334155 1e293b 0f172a 020617",
    "zinc": "fafafa f4f4f5 e4e4e7 d4d4d8 a1a1aa 71717a 52525b 3f3f46 27272a 18181b 09090b",
    "neutral": "fafafa f5f5f5 e5e5e5 d4d4d4 a3a3a3 737373 525252 404040 262626 171717 0a0a0a",
    "stone": "fafaf9 f5f5f4 e7e5e4 d6d3d1 a8a29e 78716c 57534e 44403c 292524 1c1917 0c0a09",
}
SHADES = "50 100 200 300 400 500 600 700 800 900 950".split()
PALETTE = {"white": "ffffff", "black": "000000"}
for fam, vals in GRAYS.items():
    PALETTE.update({f"{fam}-{s}": v for s, v in zip(SHADES, vals.split())})
RULE_TEXT = {
    "gradient-text": ("Gradient text", "warning", "Gradient text is decorative and a common AI tell. Use a solid colour."),
    "low-contrast": ("Low contrast", "error", "Text contrast is below WCAG AA (4.5:1). Darken the text or change the background."),
    "tiny-text": ("Tiny text", "warning", "Text under 12px is hard to read. Use 12px or larger, and 16px for body text."),
    "justified-text": ("Justified text", "warning", "Justified text creates uneven gaps. Left-align it."),
    "img-no-alt": ("Image without alt", "error", "Add alt text, or alt=\"\" if the image is decorative."),
    "icon-button-no-name": ("Icon button without a name", "error", "Add aria-label so screen readers can announce the button."),
    "clickable-div": ("Clickable non-button", "error", "Use a <button>, or add role and keyboard handling so it works without a mouse."),
    "input-no-label": ("Input without a label", "error", "Give the input a <label>, aria-label or aria-labelledby."),
    "focus-removed": ("Focus outline removed", "error", "outline-none without a focus style hides keyboard focus. Add focus-visible styles."),
}


def _lum(hex6: str) -> float:
    vals = [int(hex6[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in vals]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _hex6(value: str) -> str | None:
    m = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", value.strip())
    if not m:
        return {"white": "ffffff", "black": "000000"}.get(value.strip().lower())
    h = m.group(1).lower()
    return "".join(c * 2 for c in h) if len(h) == 3 else h


def jsx_tags(text: str):
    """Yield (offset, tag name, attribute text, end offset) for each opening JSX tag, tracking braces and quotes."""
    for m in re.finditer(r"<([A-Za-z][\w.]*)", text):
        depth, quote, i = 0, "", m.end()
        while i < len(text):
            c = text[i]
            if quote:
                if c == "\\":
                    i += 1
                elif c == quote:
                    quote = ""
            elif c in "\"'`":
                quote = c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            elif c == ">" and depth == 0 and text[i - 1] != "=":
                yield m.start(), m.group(1), text[m.end():i], i + 1
                break
            elif c == "<" and depth == 0:
                break  # a generic or comparison, not a tag
            i += 1


def _style(attrs: str) -> dict:
    m = re.search(r"style=\{\{(.*?)\}\}", attrs, re.S)
    out = {}
    if m:
        for k, v in re.findall(r"([A-Za-z]+)\s*:\s*(\"[^\"]*\"|'[^']*'|`[^`]*`|[\d.]+)", m.group(1)):
            out[k] = v.strip("\"'`")
    return out


def _classes(attrs: str) -> list:
    m = re.search(r"className=(?:\"([^\"]*)\"|'([^']*)'|\{[`\"']([^`\"']*)[`\"']\})", attrs)
    return (next(g for g in m.groups() if g is not None).split() if m else [])


def _tw_color(classes: list, prefix: str) -> str | None:
    for c in classes:
        if c.startswith(prefix) and c[len(prefix):] in PALETTE:
            return PALETTE[c[len(prefix):]]
    return None


def check_jsx(text: str, path: str = "") -> list:
    found = []
    lines = text.splitlines()

    def add(rule: str, offset: int, detail: str = "") -> None:
        line = text.count("\n", 0, offset) + 1
        near = " ".join(lines[max(line - 2, 0):line])
        if "shipwright-disable" in near:
            return
        name, severity, desc = RULE_TEXT[rule]
        found.append({"antipattern": rule, "name": name, "severity": severity, "category": "quality",
                      "description": f"{detail + '. ' if detail else ''}{desc}", "file": path, "line": line})

    for pos, tag, attrs, end in jsx_tags(text):
        style, classes = _style(attrs), _classes(attrs)
        bg = style.get("background", "") + style.get("backgroundImage", "")
        clip = style.get("backgroundClip", "") + style.get("WebkitBackgroundClip", "")
        if "gradient" in bg and "text" in clip:
            add("gradient-text", pos)
        pair = (_hex6(style.get("color", "")), _hex6(style.get("backgroundColor") or style.get("background") or ""))
        if not all(pair):
            pair = (_tw_color(classes, "text-"), _tw_color(classes, "bg-"))
        if all(pair):
            ratio = contrast(*pair)
            if ratio < 4.5:
                add("low-contrast", pos, f"{ratio:.1f}:1 on this element")
        size = style.get("fontSize", "")
        px = re.fullmatch(r"([\d.]+)(px)?", size)
        tw = next((re.fullmatch(r"text-\[([\d.]+)px\]", c) for c in classes if re.fullmatch(r"text-\[([\d.]+)px\]", c)), None)
        value = float(px.group(1)) if px else float(tw.group(1)) if tw else None
        if value is not None and value < 12:
            add("tiny-text", pos, f"{value:g}px")
        if style.get("textAlign") == "justify" or "text-justify" in classes:
            add("justified-text", pos)
        if "outline-none" in classes and not any(c.startswith(("focus:", "focus-visible:")) for c in classes):
            add("focus-removed", pos)
        if tag in ("img", "Image") and not re.search(r"\balt=", attrs):
            add("img-no-alt", pos)
        if tag == "div" and re.search(r"\bonClick=", attrs) and not re.search(r"\brole=", attrs):
            add("clickable-div", pos)
        if tag == "input" and not re.search(r"\b(aria-label|aria-labelledby|id)=|type=[\"']hidden", attrs):
            add("input-no-label", pos)
        if tag == "button" and not attrs.rstrip().endswith("/") and not re.search(r"\b(aria-label|aria-labelledby|title)=", attrs):
            close = text.find("</button>", end)
            inner = text[end:close] if close != -1 else ""
            if close != -1 and re.fullmatch(r"\s*<[A-Z][\w.]*[^<>]*/>\s*", inner):
                add("icon-button-no-name", pos)
    return found
