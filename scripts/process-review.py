#!/usr/bin/env python3
"""
Process human review decisions exported from the review HTML page.

Usage:
  python3 scripts/process-review.py <review-decisions.json> <ad-sets-folder>

Actions:
  --summary         Print a summary of decisions (default if no action specified)
  --approved-csv    Write a new upload CSV containing only fully-approved sets
  --edit-brief      Write an edit-brief.md with instructions for items needing edits
  --filter-sets     Copy only fully-approved sets to a new output folder
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def load_decisions(path: Path) -> dict:
    return json.loads(path.read_text())


def load_ad_copy(set_dir: Path) -> dict:
    return json.loads((set_dir / "ad_copy.json").read_text())


def map_decisions_to_sets(
    decisions: list[dict], sets_dir: Path
) -> list[dict]:
    decision_lookup: dict[str, dict] = {}
    for d in decisions:
        key = f"{d['ad_name']}__{d['ratio']}"
        decision_lookup[key] = d

    set_dirs = sorted(
        p for p in sets_dir.iterdir() if p.is_dir() and p.name.startswith("set_")
    )

    results = []
    for set_dir in set_dirs:
        ad_copy = load_ad_copy(set_dir)
        source_images = ad_copy.get("source_images", [])

        ad_decisions = []
        for ad_name in source_images:
            for ratio in ("9x16", "1x1"):
                key = f"{ad_name}__{ratio}"
                entry = decision_lookup.get(key)
                if entry:
                    ad_decisions.append(entry)

        statuses = {d["decision"] for d in ad_decisions}

        if not ad_decisions:
            set_status = "unreviewed"
        elif statuses == {"approve"}:
            set_status = "approved"
        elif "reject" in statuses and statuses <= {"reject", "approve"}:
            set_status = "mixed-reject"
        elif "edit" in statuses:
            set_status = "needs-edit"
        else:
            set_status = "mixed"

        results.append({
            "set_dir": set_dir,
            "set_number": ad_copy["set_number"],
            "ad_set_key": ad_copy["ad_set_key"],
            "persona": ad_copy["persona"],
            "set_theme": ad_copy["set_theme"],
            "source_images": source_images,
            "ad_decisions": ad_decisions,
            "set_status": set_status,
            "ad_copy": ad_copy,
        })

    return results


def print_summary(results: list[dict]) -> None:
    approved = [r for r in results if r["set_status"] == "approved"]
    needs_edit = [r for r in results if r["set_status"] == "needs-edit"]
    mixed_reject = [r for r in results if r["set_status"] == "mixed-reject"]
    unreviewed = [r for r in results if r["set_status"] == "unreviewed"]

    total_items = sum(len(r["ad_decisions"]) for r in results)
    approved_items = sum(
        1 for r in results for d in r["ad_decisions"] if d["decision"] == "approve"
    )
    edit_items = sum(
        1 for r in results for d in r["ad_decisions"] if d["decision"] == "edit"
    )
    reject_items = sum(
        1 for r in results for d in r["ad_decisions"] if d["decision"] == "reject"
    )

    print(f"\n{'='*60}")
    print(f"REVIEW SUMMARY")
    print(f"{'='*60}")
    print(f"Items: {approved_items} approved, {edit_items} edit, {reject_items} rejected ({total_items} total)")
    print(f"Sets:  {len(approved)} approved, {len(needs_edit)} needs-edit, {len(mixed_reject)} mixed-reject, {len(unreviewed)} unreviewed ({len(results)} total)")

    if approved:
        print(f"\n--- FULLY APPROVED ({len(approved)} sets, ready to upload) ---")
        for r in approved:
            print(f"  set_{r['set_number']:02d}  {r['persona']} / {r['set_theme']}")

    if needs_edit:
        print(f"\n--- NEEDS EDIT ({len(needs_edit)} sets) ---")
        for r in needs_edit:
            edits = [d for d in r["ad_decisions"] if d["decision"] == "edit"]
            print(f"  set_{r['set_number']:02d}  {r['persona']} / {r['set_theme']}")
            for e in edits:
                note = e.get("notes", "").strip()
                print(f"    {e['number']} ({e['ratio']}): {note or '(no notes)'}")

    if mixed_reject:
        print(f"\n--- MIXED/REJECTED ({len(mixed_reject)} sets) ---")
        for r in mixed_reject:
            rejects = [d for d in r["ad_decisions"] if d["decision"] == "reject"]
            print(f"  set_{r['set_number']:02d}  {r['persona']} / {r['set_theme']}")
            for rej in rejects:
                print(f"    {rej['number']} ({rej['ratio']}): REJECT")

    print()


def write_edit_brief(results: list[dict], output_path: Path) -> None:
    lines = [
        f"# Edit Brief",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    edit_sets = [r for r in results if any(d["decision"] == "edit" for d in r["ad_decisions"])]

    if not edit_sets:
        lines.append("No edits needed.")
        output_path.write_text("\n".join(lines))
        print(f"Edit brief: {output_path} (no edits)")
        return

    for r in edit_sets:
        lines.append(f"## Set {r['set_number']:02d} - {r['persona']} / {r['set_theme']}")
        lines.append(f"Key: `{r['ad_set_key']}`")
        lines.append("")

        for d in r["ad_decisions"]:
            if d["decision"] != "edit":
                continue
            lines.append(f"### {d['number']} - {d['ad_name']} ({d['ratio']})")
            notes = d.get("notes", "").strip()
            if notes:
                lines.append(f"**Action:** {notes}")
            else:
                lines.append("**Action:** (no specific notes provided)")
            lines.append("")

    output_path.write_text("\n".join(lines))
    print(f"Edit brief: {output_path} ({len(edit_sets)} sets with edits)")


def write_approved_csv(
    results: list[dict],
    original_csv: Path,
    output_path: Path,
) -> None:
    approved_set_numbers = {
        r["set_number"] for r in results if r["set_status"] == "approved"
    }

    if not original_csv.exists():
        print(f"Warning: no original CSV at {original_csv}")
        return

    with original_csv.open() as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    approved_rows = [row for i, row in enumerate(rows) if (i + 1) in approved_set_numbers]

    with output_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(approved_rows)

    print(f"Approved CSV: {output_path} ({len(approved_rows)} of {len(rows)} sets)")


def filter_approved_sets(results: list[dict], output_dir: Path) -> None:
    approved = [r for r in results if r["set_status"] == "approved"]
    if not approved:
        print("No fully-approved sets to filter.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    for i, r in enumerate(approved, 1):
        src = r["set_dir"]
        dst = output_dir / f"set_{i:02d}"
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

    print(f"Filtered sets: {output_dir} ({len(approved)} approved sets)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Process review decisions from HTML review page")
    parser.add_argument("review_json", help="Path to review-decisions JSON file")
    parser.add_argument("ad_sets_folder", help="Path to ad_sets folder")
    parser.add_argument("--summary", action="store_true", help="Print summary (default)")
    parser.add_argument("--edit-brief", action="store_true", help="Write edit-brief.md")
    parser.add_argument("--approved-csv", action="store_true", help="Write CSV with only approved sets")
    parser.add_argument("--filter-sets", action="store_true", help="Copy approved sets to a new folder")
    parser.add_argument("--output", help="Output directory (default: ad_sets_folder)")
    args = parser.parse_args()

    review_path = Path(args.review_json).resolve()
    sets_dir = Path(args.ad_sets_folder).resolve()
    output_dir = Path(args.output).resolve() if args.output else sets_dir

    if not review_path.exists():
        raise SystemExit(f"Review file not found: {review_path}")
    if not sets_dir.is_dir():
        raise SystemExit(f"Not a directory: {sets_dir}")

    data = load_decisions(review_path)
    results = map_decisions_to_sets(data["decisions"], sets_dir)

    no_action = not any([args.edit_brief, args.approved_csv, args.filter_sets])
    if args.summary or no_action:
        print_summary(results)

    if args.edit_brief:
        write_edit_brief(results, output_dir / "edit-brief.md")

    if args.approved_csv:
        write_approved_csv(
            results,
            sets_dir / "upload_spreadsheet.csv",
            output_dir / "upload_spreadsheet_approved.csv",
        )

    if args.filter_sets:
        filter_approved_sets(results, output_dir / "approved_sets")


if __name__ == "__main__":
    main()
