#!/usr/bin/env python3
"""
Upload existing ad_sets folders to a consolidated Drive folder.

Reads ad_copy.json from each set_XX/ subdirectory and uploads all assets
to a single dated Drive parent folder, reusing find-or-create logic from
ad_set_builder.upload_sets_to_drive().

Usage:
  uv run python scripts/upload-existing-sets.py \
    --folder clients/{client}/ads/statics_ad_sets \
    [--drive-parent ad_sets_2026-03-11]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from ad_set_builder import generate_csv, upload_csv_to_drive, upload_sets_to_drive


def load_records_from_sets(folder: Path) -> list[dict]:
    """Build records list from existing set_XX/ad_copy.json files."""
    records = []
    set_dirs = sorted(
        d for d in folder.iterdir()
        if d.is_dir() and d.name.startswith("set_") and (d / "ad_copy.json").exists()
    )
    for set_dir in set_dirs:
        ad_copy = json.loads((set_dir / "ad_copy.json").read_text())
        records.append({
            "set_number": ad_copy["set_number"],
            "set_dir": set_dir,
            "persona": ad_copy["persona"],
            "set_theme": ad_copy["set_theme"],
            "review_status": ad_copy.get("review_status", "passed"),
            "source_images": ad_copy.get("source_images", []),
            "variants": ad_copy.get("variants", []),
        })
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload existing ad sets to consolidated Drive folder")
    parser.add_argument("--folder", required=True, help="Folder containing set_XX/ subdirectories")
    parser.add_argument("--drive-parent", help="Drive folder name (default: ad_sets_YYYY-MM-DD)")
    parser.add_argument("--creative-strategist", default="Ryane", help="Creative strategist for CSV")
    parser.add_argument("--ad-focus", default="RSSP", help="Ad focus for CSV")
    parser.add_argument("--cta", default="Learn More", help="CTA for CSV")
    args = parser.parse_args()

    folder = Path(args.folder).resolve()
    if not folder.is_dir():
        raise SystemExit(f"Not a directory: {folder}")

    records = load_records_from_sets(folder)
    if not records:
        raise SystemExit(f"No set_XX/ directories with ad_copy.json found in {folder}")

    print(f"Found {len(records)} sets to upload")

    drive_parent = args.drive_parent or f"ad_sets_backfill_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}"
    drive_links, parent_link = upload_sets_to_drive(folder, records, drive_parent_name=drive_parent)

    print(f"\nAll sets uploaded to: {parent_link}")

    # Generate CSV with Drive links and upload it
    if drive_links:
        csv_path = generate_csv(
            folder,
            records,
            drive_links,
            creative_strategist=args.creative_strategist,
            ad_focus=args.ad_focus,
            cta=args.cta,
        )
        upload_csv_to_drive(csv_path, parent_link)


if __name__ == "__main__":
    main()
