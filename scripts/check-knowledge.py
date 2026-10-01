#!/usr/bin/env python3
"""Validate client knowledge bases: profile and angle frontmatter, and the creative tracker.

Run from the repo root:
    uv run python scripts/check-knowledge.py              # every clients/*/ directory
    uv run python scripts/check-knowledge.py --client acme

What it checks, per clients/{client}/:
  avatars/core-*/profile.md               type: core-profile
  avatars/core-*/sub-*/profile.md         type: sub-profile
  avatars/core-*/sub-*/angle-*.md         type: angle
  testing/creative-tracker.csv            18-column header, field count, status and testing-method values

Placeholder rule: inside clients/_template/ only, free-text values that still hold
a placeholder ("{...}", "[...]", "YYYY-MM-DD") are accepted, and path and name
cross-checks are skipped for them. Enumerated fields (type, confidence, status,
strength, anchor_category, mass_instinct) must hold a real allowed value even in
the template. Outside the template, any placeholder is an error.

Exit 0 when there are no errors, 1 otherwise. Warnings are printed but never
change the exit code.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLIENTS = ROOT / "clients"
TEMPLATE_NAME = "_template"

TRACKER_HEADER = [
    "batch", "date", "concept", "testing-method", "sub-avatar", "core-avatar",
    "angle", "product", "offer", "variation", "messaging-concept", "visual-format",
    "format", "channel", "asset-ref", "status", "result", "notes",
]
LEGACY_TRACKER_HEADER = [
    "batch", "date", "sub-avatar", "core-avatar", "angle", "messaging-concept",
    "visual-format", "product-or-offer", "status", "result", "notes",
]

STATUS_VALUES = {"untested", "testing", "winner", "loser"}
CONFIDENCE_VALUES = {"low", "medium", "high"}
STRENGTH_VALUES = {"1", "2", "3"}
TESTING_METHOD_VALUES = {"discovery", "deep-iteration", "ab-split"}
ANCHOR_CATEGORY_VALUES = {"desire", "experience", "emotion", "behaviour", "behavior", "demographic"}
MASS_INSTINCT_VALUES = {"health", "sex", "status", "belonging", "control", "comfort"}

REQUIRED_KEYS = {
    "core-profile": ["type", "id", "anchor_category", "mass_instinct", "confidence", "sources", "updated"],
    "sub-profile": ["type", "id", "parent", "confidence", "sources", "updated"],
    "angle": ["type", "sub_avatar", "offer", "status", "strength", "updated"],
}
ENUMS = {
    "confidence": CONFIDENCE_VALUES,
    "status": STATUS_VALUES,
    "strength": STRENGTH_VALUES,
    "anchor_category": ANCHOR_CATEGORY_VALUES,
    "mass_instinct": MASS_INSTINCT_VALUES,
}

# Markdown under avatars/ that is expected and deliberately carries no frontmatter.
NON_FRONTMATTER_NAMES = {"README.md", "summary.md", "ranked-angles.md"}

PLACEHOLDER = re.compile(r"\{[^}]*\}|\[[^\]]*\]|YYYY-MM-DD")
INLINE_COMMENT = re.compile(r"\s+#.*$")
THREE_QUESTIONS = re.compile(r"\*\*Three Questions:\*\*(.*)", re.IGNORECASE)


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, path: Path, msg: str) -> None:
        self.errors.append(f"ERROR {rel(path)}: {msg}")

    def warn(self, path: Path, msg: str) -> None:
        self.warnings.append(f"WARN  {rel(path)}: {msg}")


@dataclass
class ClientStats:
    counts: dict[str, int] = field(default_factory=lambda: {"core-profile": 0, "sub-profile": 0, "angle": 0})
    tracker: str = "no tracker"
    not_frontmatter: list[str] = field(default_factory=list)
    placeholders: int = 0


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def clean(value: str) -> str:
    value = INLINE_COMMENT.sub("", value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def parse_frontmatter(text: str) -> dict[str, str | list[str]] | None:
    """Parse the small YAML subset used here: `key: value` and `key:` followed by `- item` lines."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    data: dict[str, str | list[str]] = {}
    current_list: str | None = None
    for line in text[4:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        stripped = line.strip()
        if stripped.startswith("- ") and current_list is not None:
            items = data[current_list]
            assert isinstance(items, list)
            items.append(clean(stripped[2:]))
            continue
        if ":" in line and not line.startswith((" ", "\t", "-")):
            key, _, raw = line.partition(":")
            key = key.strip()
            value = clean(raw)
            if value == "":
                data[key] = []
                current_list = key
            elif value.startswith("[") and value.endswith("]") and not PLACEHOLDER.fullmatch(value):
                data[key] = [clean(v) for v in value[1:-1].split(",") if v.strip()]
                current_list = None
            else:
                data[key] = value
                current_list = None
            continue
        current_list = None
    return data


def is_placeholder(value: str) -> bool:
    return bool(PLACEHOLDER.search(value))


def looks_like_path(value: str) -> bool:
    if value.startswith(("http://", "https://")):
        return False
    return " " not in value and ("/" in value or re.search(r"\.(md|csv|json|txt|pdf)$", value) is not None)


def check_profile_or_angle(path: Path, expected: str, client_dir: Path, in_template: bool,
                           report: Report, stats: ClientStats) -> None:
    text = path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    if fm is None:
        report.error(path, f"missing YAML frontmatter (expected type: {expected})")
        return

    def text_value(key: str) -> str | None:
        """Return a scalar value, or None after reporting a problem. Placeholders return None in the template."""
        value = fm.get(key)
        if isinstance(value, list):
            report.error(path, f"'{key}' must be a single value, not a list")
            return None
        if value is None or value == "":
            return None
        if is_placeholder(value):
            if in_template:
                stats.placeholders += 1
            else:
                report.error(path, f"'{key}' still holds a template placeholder: {value}")
            return None
        return value

    for key in REQUIRED_KEYS[expected]:
        value = fm.get(key)
        if value is None or value == "" or value == []:
            report.error(path, f"missing frontmatter key '{key}'")

    kind = fm.get("type")
    if kind != expected:
        report.error(path, f"type must be '{expected}' for this location, got '{kind}'")

    for key, allowed in ENUMS.items():
        if key not in REQUIRED_KEYS[expected] or key not in fm:
            continue
        value = fm[key]
        if isinstance(value, list) or value.lower() not in allowed:
            report.error(path, f"{key} must be one of {sorted(allowed)}, got '{value}'")

    updated = text_value("updated")
    if updated is not None:
        try:
            date.fromisoformat(updated)
        except ValueError:
            report.error(path, f"updated must be a YYYY-MM-DD date, got '{updated}'")

    core_dir = path.parent if expected == "core-profile" else path.parent.parent
    sub_dir = path.parent if expected != "core-profile" else None

    if expected in {"core-profile", "sub-profile"}:
        ident = text_value("id")
        own_dir = core_dir if expected == "core-profile" else sub_dir
        if ident is not None and own_dir is not None and ident != own_dir.name:
            report.error(path, f"id '{ident}' does not match its directory '{own_dir.name}'")

        sources = fm.get("sources")
        if isinstance(sources, str):
            report.error(path, "sources must be a list (one '- item' per line)")
        elif sources:
            for src in sources:
                if is_placeholder(src):
                    if in_template:
                        stats.placeholders += 1
                    else:
                        report.error(path, f"sources entry still holds a template placeholder: {src}")
                    continue
                if looks_like_path(src) and not (path.parent / src).resolve().exists():
                    report.error(path, f"sources entry does not resolve: {src}")

    if expected == "sub-profile":
        parent = text_value("parent")
        if parent is not None and parent != core_dir.name:
            report.error(path, f"parent '{parent}' does not match its core directory '{core_dir.name}'")
        match = THREE_QUESTIONS.search(text)
        if not match:
            report.warn(path, "no '**Three Questions:**' line in the Niche Gap section")
        elif not is_placeholder(match.group(1)) and re.search(r"\bno\b", match.group(1), re.IGNORECASE):
            report.warn(path, "niche gap test has a 'no' answer; merge or justify this sub-avatar")

    if expected == "angle":
        sub_avatar = text_value("sub_avatar")
        if sub_avatar is not None and sub_dir is not None and sub_avatar != sub_dir.name:
            report.error(path, f"sub_avatar '{sub_avatar}' does not match its directory '{sub_dir.name}'")
        offer = text_value("offer")
        if offer is not None:
            candidates = [client_dir / "products" / f"{offer}.md", client_dir / "offers" / f"{offer}.md"]
            if not any(c.exists() for c in candidates):
                report.error(path, f"offer '{offer}' has no products/{offer}.md or offers/{offer}.md")

    stats.counts[expected] += 1


def check_tracker(path: Path, report: Report, stats: ClientStats) -> None:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader, [])
        if header == LEGACY_TRACKER_HEADER:
            report.error(path, "legacy 11-column header; migrate to the 18 columns in testing/creative-tracker.md")
            stats.tracker = "tracker rows not checked (legacy header)"
            return
        if header != TRACKER_HEADER:
            report.error(path, f"header must be {','.join(TRACKER_HEADER)}")
            stats.tracker = "tracker rows not checked (bad header)"
            return
        status_i = TRACKER_HEADER.index("status")
        method_i = TRACKER_HEADER.index("testing-method")
        rows = 0
        for n, row in enumerate(reader, 2):
            if not any(cell.strip() for cell in row):
                continue
            rows += 1
            if len(row) != len(TRACKER_HEADER):
                report.error(path, f"line {n}: expected {len(TRACKER_HEADER)} fields, got {len(row)}")
                continue
            if row[status_i] not in STATUS_VALUES:
                report.error(path, f"line {n}: status must be one of {sorted(STATUS_VALUES)}, got '{row[status_i]}'")
            if row[method_i] and row[method_i] not in TESTING_METHOD_VALUES:
                report.error(path, f"line {n}: testing-method must be empty or one of {sorted(TESTING_METHOD_VALUES)}, got '{row[method_i]}'")
        stats.tracker = f"tracker {rows} row(s)"


def check_client(client_dir: Path, report: Report) -> ClientStats:
    stats = ClientStats()
    in_template = client_dir.name == TEMPLATE_NAME
    avatars = client_dir / "avatars"

    if avatars.is_dir():
        for path in sorted(avatars.rglob("*.md")):
            parts = path.relative_to(avatars).parts
            if parts[0] == "research":
                stats.not_frontmatter.append(str(path.relative_to(client_dir)))
                continue
            if len(parts) == 2 and parts[0].startswith("core-") and parts[1] == "profile.md":
                check_profile_or_angle(path, "core-profile", client_dir, in_template, report, stats)
            elif len(parts) == 3 and parts[0].startswith("core-") and parts[1].startswith("sub-") and parts[2] == "profile.md":
                check_profile_or_angle(path, "sub-profile", client_dir, in_template, report, stats)
            elif len(parts) == 3 and parts[0].startswith("core-") and parts[1].startswith("sub-") and parts[2].startswith("angle-"):
                check_profile_or_angle(path, "angle", client_dir, in_template, report, stats)
            elif path.name in NON_FRONTMATTER_NAMES:
                stats.not_frontmatter.append(str(path.relative_to(client_dir)))
            else:
                report.warn(path, "outside the avatars/core-*/sub-*/ layout, so its frontmatter was not validated")
    else:
        report.warn(client_dir, "no avatars/ directory")

    tracker = client_dir / "testing" / "creative-tracker.csv"
    if tracker.exists():
        check_tracker(tracker, report, stats)
    else:
        report.error(tracker, "missing creative tracker (copy it from clients/_template/testing/)")
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--client", help="check only clients/{client}/")
    args = parser.parse_args()

    if args.client:
        client_dirs = [CLIENTS / args.client]
        if not client_dirs[0].is_dir():
            print(f"check-knowledge: no such client directory: {rel(client_dirs[0])}")
            return 1
    else:
        client_dirs = sorted(p for p in CLIENTS.iterdir() if p.is_dir() and not p.name.startswith("."))

    report = Report()
    summary: list[str] = []
    for client_dir in client_dirs:
        stats = check_client(client_dir, report)
        c = stats.counts
        line = (f"  {client_dir.name}: {c['core-profile']} core profile(s), {c['sub-profile']} sub profile(s), "
                f"{c['angle']} angle(s), {stats.tracker}; {len(stats.not_frontmatter)} other avatar file(s) not frontmatter-checked")
        if stats.not_frontmatter:
            shown = ", ".join(stats.not_frontmatter[:5])
            more = f" and {len(stats.not_frontmatter) - 5} more" if len(stats.not_frontmatter) > 5 else ""
            line += f" ({shown}{more})"
        if stats.placeholders:
            line += f"; {stats.placeholders} template placeholder value(s) accepted"
        summary.append(line)

    for msg in report.errors + report.warnings:
        print(msg)
    print(f"check-knowledge: {len(client_dirs)} client dir(s)")
    for line in summary:
        print(line)
    print(f"check-knowledge: {len(report.errors)} error(s), {len(report.warnings)} warning(s)")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
