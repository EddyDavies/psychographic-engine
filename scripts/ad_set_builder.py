#!/usr/bin/env python3
"""
Build structural ad sets from generated batch folders.

The expected input is one `test-*-YYYY-MM-DD/` folder created by `generate-ads.py`,
or a parent directory containing multiple such batch folders. Each batch must include
`manifest.json`.
"""

from __future__ import annotations

import argparse
import csv
import shutil
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from utils import (
    DELAY_BETWEEN_IMAGES,
    SUPPORTED_EXTENSIONS,
    encode_image,
    get_google_services,
    json_dump,
    load_manifest,
    recompose,
)

ADS_PER_SET = 3


def is_packagable_entry(entry: dict) -> bool:
    status = entry.get("review_status")
    return status in {None, "passed"}


def parse_copy_file(path: Path) -> dict[str, str]:
    text = path.read_text()
    sections: dict[str, str] = {}
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("## "):
            if current_heading is not None:
                sections[current_heading] = "\n".join(current_lines).strip()
            current_heading = line.removeprefix("## ").strip()
            current_lines = []
            continue
        if current_heading is not None:
            current_lines.append(line)

    if current_heading is not None:
        sections[current_heading] = "\n".join(current_lines).strip()

    return {
        "image_prompt": sections.get("Image Prompt", "").rstrip("- \n"),
        "primary_text": sections.get("Primary Text", "").rstrip("- \n"),
        "headline": sections.get("Headline", "").rstrip("- \n"),
    }


def discover_batch_dirs(folder: Path) -> list[Path]:
    if (folder / "manifest.json").exists():
        return [folder]

    batch_dirs = sorted(
        path for path in folder.iterdir() if path.is_dir() and (path / "manifest.json").exists()
    )
    return batch_dirs


def ensure_image_pair(batch_dir: Path, entry: dict) -> dict[str, str]:
    image_files = dict(entry.get("image_files", {}))
    base_stem = Path(entry["copy_file"]).stem.removesuffix("-copy")

    def resolve(label: str) -> Path | None:
        name = image_files.get(label)
        if not name:
            candidate = batch_dir / f"{base_stem}_{label}.png"
            return candidate if candidate.exists() else None
        path = batch_dir / name
        return path if path.exists() else None

    img_9x16 = resolve("9x16")
    if img_9x16 and "9x16" not in image_files:
        image_files["9x16"] = img_9x16.name
    img_1x1 = resolve("1x1")
    if img_1x1 and "1x1" not in image_files:
        image_files["1x1"] = img_1x1.name

    if img_9x16 is None and img_1x1 is None:
        raise FileNotFoundError(f"No rendered images found for {base_stem}")

    if img_9x16 is None and img_1x1 is not None:
        generated = batch_dir / f"{base_stem}_9x16.png"
        generated_bytes = recompose(encode_image(img_1x1), "9:16")
        if not generated_bytes:
            raise RuntimeError(f"Could not generate missing 9x16 asset for {base_stem}")
        generated.write_bytes(generated_bytes)
        img_9x16 = generated
        image_files["9x16"] = generated.name
        time.sleep(DELAY_BETWEEN_IMAGES)

    if img_1x1 is None and img_9x16 is not None:
        generated = batch_dir / f"{base_stem}_1x1.png"
        generated_bytes = recompose(encode_image(img_9x16), "1:1")
        if not generated_bytes:
            # Fallback: center-crop 9x16 to 1x1 locally
            try:
                from PIL import Image
                with Image.open(img_9x16) as im:
                    w, h = im.size
                    side = min(w, h)
                    left = (w - side) // 2
                    top = (h - side) // 2
                    cropped = im.crop((left, top, left + side, top + side))
                    cropped.save(generated, "PNG")
            except Exception:
                raise RuntimeError(f"Could not generate missing 1x1 asset for {base_stem}")
        else:
            generated.write_bytes(generated_bytes)
        img_1x1 = generated
        image_files["1x1"] = generated.name
        time.sleep(DELAY_BETWEEN_IMAGES)

    required_labels = {"9x16", "1x1"}
    if not required_labels.issubset(image_files):
        raise RuntimeError(f"{base_stem} is missing one of the required aspect ratios: {required_labels}")

    return {label: image_files[label] for label in sorted(required_labels)}


def build_structural_groups(batch_dirs: list[Path]) -> list[dict]:
    groups: list[dict] = []
    set_number = 1
    skipped_entries = 0

    for batch_dir in batch_dirs:
        grouped: defaultdict[str, list[dict]] = defaultdict(list)
        for entry in load_manifest(batch_dir / "manifest.json"):
            if not is_packagable_entry(entry):
                skipped_entries += 1
                continue
            entry["image_files"] = ensure_image_pair(batch_dir, entry)
            grouped[entry["ad_set_key"]].append(entry)

        for ad_set_key, entries in sorted(
            grouped.items(),
            key=lambda item: min(entry["sequence"] for entry in item[1]),
        ):
            ordered_entries = sorted(entries, key=lambda entry: entry["sequence"])
            if len(ordered_entries) % ADS_PER_SET != 0:
                print(
                    f"Warning: {ad_set_key} has {len(ordered_entries)} creatives "
                    f"(need {ADS_PER_SET}). Skipping incomplete set."
                )
                skipped_entries += len(ordered_entries)
                continue

            for chunk_index in range(0, len(ordered_entries), ADS_PER_SET):
                chunk = ordered_entries[chunk_index : chunk_index + ADS_PER_SET]
                groups.append(
                    {
                        "set_number": set_number,
                        "batch_dir": batch_dir,
                        "ad_set_key": ad_set_key,
                        "entries": chunk,
                        "persona": chunk[0]["sub_avatar"].removeprefix("sub-"),
                        "set_theme": chunk[0]["angle_name"],
                        "review_status": "passed",
                    }
                )
                set_number += 1

    if not groups and skipped_entries:
        raise ValueError("No review-passed creatives found. Resolve or override failed reviews before packaging.")

    return groups


def organize_sets(groups: list[dict], output_dir: Path) -> list[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []

    for group in groups:
        set_number = group["set_number"]
        batch_dir: Path = group["batch_dir"]
        set_dir = output_dir / f"set_{set_number:02d}"
        set_dir.mkdir(parents=True, exist_ok=True)

        variants = []
        source_images = []
        copied_assets = 0

        for index, entry in enumerate(group["entries"], start=1):
            copy_path = batch_dir / entry["copy_file"]
            copy_data = parse_copy_file(copy_path)
            variant_label = chr(64 + index)
            creative_stem = copy_path.stem.removesuffix("-copy")

            variants.append(
                {
                    "variant": variant_label,
                    "visual_format": entry["visual_format"],
                    "messaging_concept": entry["messaging_concept"],
                    "primary_text": copy_data["primary_text"] or entry.get("primary_text", ""),
                    "headline": copy_data["headline"] or entry.get("headline", ""),
                }
            )

            shutil.copy2(copy_path, set_dir / copy_path.name)
            copied_assets += 1
            for ratio_label, filename in sorted(entry["image_files"].items()):
                image_path = batch_dir / filename
                sidecar_path = image_path.with_suffix(".json")
                shutil.copy2(image_path, set_dir / image_path.name)
                copied_assets += 1
                if sidecar_path.exists():
                    shutil.copy2(sidecar_path, set_dir / sidecar_path.name)
                    copied_assets += 1
            if creative_stem not in source_images:
                source_images.append(creative_stem)

        ad_copy = {
            "set_number": set_number,
            "ad_set_key": group["ad_set_key"],
            "persona": group["persona"],
            "set_theme": group["set_theme"],
            "review_status": group["review_status"],
            "source_images": source_images,
            "variants": variants,
            "timestamp": datetime.now().astimezone().isoformat(),
        }
        json_dump(ad_copy, set_dir / "ad_copy.json")

        record = {
            "set_number": set_number,
            "set_dir": set_dir,
            "persona": group["persona"],
            "set_theme": group["set_theme"],
            "review_status": group["review_status"],
            "source_images": source_images,
            "variants": variants,
        }
        records.append(record)
        print(f"set_{set_number:02d}: {copied_assets} files, {len(variants)} variants")

    return records


def upload_sets_to_drive(
    output_dir: Path,
    records: list[dict],
    drive_parent_name: str | None = None,
) -> tuple[list[str], str]:
    """Upload sets to Drive, reusing a dated parent folder if it already exists.

    Returns (set_links, parent_folder_link).
    """
    from googleapiclient.http import MediaFileUpload

    service, _ = get_google_services()

    folder_name = drive_parent_name or f"ad_sets_{datetime.now().strftime('%Y-%m-%d')}"

    # Find existing folder with this name
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    existing = service.files().list(q=query, fields="files(id)", pageSize=1).execute()
    if existing.get("files"):
        batch_folder_id = existing["files"][0]["id"]
        print(f"Reusing existing Drive folder: {folder_name} ({batch_folder_id})")
    else:
        batch_folder = service.files().create(
            body={"name": folder_name, "mimeType": "application/vnd.google-apps.folder"},
            fields="id",
        ).execute()
        batch_folder_id = batch_folder["id"]
        service.permissions().create(
            fileId=batch_folder_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()
        print(f"Created Drive folder: {folder_name} ({batch_folder_id})")

    links: list[str] = []
    for record in records:
        set_folder = service.files().create(
            body={
                "name": record["set_dir"].name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [batch_folder_id],
            },
            fields="id",
        ).execute()
        set_folder_id = set_folder["id"]

        uploaded = 0
        for file_path in sorted(record["set_dir"].iterdir()):
            if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            mime_type = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp",
            }.get(file_path.suffix.lower(), "application/octet-stream")
            media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=False)
            service.files().create(
                body={"name": file_path.name, "parents": [set_folder_id]},
                media_body=media,
                fields="id",
            ).execute()
            uploaded += 1

        link = f"https://drive.google.com/drive/folders/{set_folder_id}"
        links.append(link)
        print(f"{record['set_dir'].name}: uploaded {uploaded} files -> {link}")

    parent_link = f"https://drive.google.com/drive/folders/{batch_folder_id}"
    print(f"Batch folder: {parent_link}")
    return links, parent_link


def generate_csv(
    output_dir: Path,
    records: list[dict],
    drive_links: list[str],
    creative_strategist: str,
    ad_focus: str,
    cta: str,
) -> Path:
    today = datetime.now()
    csv_path = output_dir / "upload_spreadsheet.csv"
    fieldnames = [
        "Date",
        "Month",
        "Persona",
        "Ad Amount",
        "Creative Strategist",
        "What Are You Testing",
        "Ad focus",
        "File type",
        "Ad copy 1",
        "Ad copy 2",
        "Headline 1",
        "Headline 2",
        "CTA",
        "Content Link",
        "Review Status",
    ]

    rows = []
    for index, record in enumerate(records):
        variants = record["variants"]
        variant_a = variants[0] if len(variants) > 0 else {}
        variant_b = variants[1] if len(variants) > 1 else {}
        rows.append(
            {
                "Date": today.strftime("%d/%m/%y"),
                "Month": today.strftime("%b %y"),
                "Persona": record["persona"],
                "Ad Amount": len(record["source_images"]),
                "Creative Strategist": creative_strategist,
                "What Are You Testing": record["set_theme"],
                "Ad focus": ad_focus,
                "File type": "static",
                "Ad copy 1": variant_a.get("primary_text", ""),
                "Ad copy 2": variant_b.get("primary_text", ""),
                "Headline 1": variant_a.get("headline", ""),
                "Headline 2": variant_b.get("headline", ""),
                "CTA": cta,
                "Content Link": drive_links[index] if index < len(drive_links) else "",
                "Review Status": record["review_status"],
            }
        )

    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV: {csv_path}")
    return csv_path


def upload_csv_to_drive(csv_path: Path, parent_folder_link: str) -> None:
    """Upload a CSV file to an existing Drive folder (extracted from its link)."""
    from googleapiclient.http import MediaFileUpload

    folder_id = parent_folder_link.rstrip("/").split("/")[-1]
    service, _ = get_google_services()
    media = MediaFileUpload(str(csv_path), mimetype="text/csv", resumable=False)
    service.files().create(
        body={"name": csv_path.name, "parents": [folder_id]},
        media_body=media,
        fields="id",
    ).execute()
    print(f"Uploaded CSV to Drive: {csv_path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build structural ad sets from generated batches")
    parser.add_argument("--folder", required=True, help="Batch folder or parent folder containing batch folders")
    parser.add_argument("--output", help="Output directory (default: {foldername}_ad_sets)")
    parser.add_argument("--upload", action="store_true", help="Upload built sets to Google Drive")
    parser.add_argument("--csv", action="store_true", help="Generate upload_spreadsheet.csv")
    parser.add_argument("--creative-strategist", default="Ryane", help="Creative strategist value for CSV")
    parser.add_argument("--ad-focus", default="RSSP", help="Ad focus value for CSV")
    parser.add_argument("--cta", default="Learn More", help="CTA value for CSV")
    args = parser.parse_args()

    folder = Path(args.folder).resolve()
    if not folder.is_dir():
        raise SystemExit(f"Not a directory: {folder}")

    batch_dirs = discover_batch_dirs(folder)
    if not batch_dirs:
        raise SystemExit(f"No batch folders with manifest.json found under {folder}")

    output_dir = Path(args.output).resolve() if args.output else folder.parent / f"ad_sets_{datetime.now().strftime('%Y-%m-%d')}"
    print(f"Source batches: {', '.join(batch_dir.name for batch_dir in batch_dirs)}")
    print(f"Output: {output_dir}")

    try:
        groups = build_structural_groups(batch_dirs)
    except ValueError as exc:
        raise SystemExit(str(exc))

    records = organize_sets(groups, output_dir)

    drive_links: list[str] = []
    if args.upload:
        drive_links, parent_link = upload_sets_to_drive(output_dir, records)

    if args.csv:
        csv_path = generate_csv(
            output_dir,
            records,
            drive_links,
            creative_strategist=args.creative_strategist,
            ad_focus=args.ad_focus,
            cta=args.cta,
        )
        if args.upload and drive_links:
            upload_csv_to_drive(csv_path, parent_link)


if __name__ == "__main__":
    main()
