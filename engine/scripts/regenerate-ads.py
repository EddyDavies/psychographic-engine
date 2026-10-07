#!/usr/bin/env python3
"""
Regenerate ad images based on human review decisions.

Reads one or more review JSON files exported from the review HTML page, finds
the source batch entries, and regenerates images for items marked as 'edit'
with the reviewer's notes appended as additional instructions.

Usage:
  python3 scripts/regenerate-ads.py <review.json> [<review2.json> ...] <statics-folder> [--workers 4]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from utils import PROJECT_ROOT, encode_image, extract_image_bytes, openrouter_headers

IMAGE_MODEL = "google/gemini-3.1-flash-image-preview"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
IMAGE_RETRIES = 3
RETRY_DELAY = 5


def load_review_decisions(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    return data["decisions"]


def find_batch_dirs(statics_dir: Path) -> list[Path]:
    return sorted(
        p for p in statics_dir.iterdir()
        if p.is_dir() and p.name.startswith("test-") and (p / "manifest.json").exists()
    )


def build_manifest_index(batch_dirs: list[Path]) -> dict[str, tuple[Path, dict]]:
    index: dict[str, tuple[Path, dict]] = {}
    for batch_dir in batch_dirs:
        manifest = json.loads((batch_dir / "manifest.json").read_text())
        for entry in manifest:
            copy_file = entry.get("copy_file", "")
            stem = Path(copy_file).stem.removesuffix("-copy")
            index[stem] = (batch_dir, entry)
    return index


def parse_image_prompt(copy_path: Path) -> str:
    text = copy_path.read_text()
    match = re.search(r"## Image Prompt\s*\n+(.+?)(?=\n## Primary Text)", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def update_headline_in_copy(copy_path: Path, new_headline: str) -> None:
    text = copy_path.read_text()
    updated = re.sub(
        r"(## Headline\s*\n+).+?\s*$",
        f"\\g<1>{new_headline}\n",
        text,
        flags=re.DOTALL,
    )
    copy_path.write_text(updated)


def image_request(
    prompt: str,
    aspect_ratio: str,
    reference_images: list[Path],
) -> bytes | None:
    import httpx

    content: list[dict] = []
    for image_path in reference_images:
        if image_path.exists():
            content.append({
                "type": "image_url",
                "image_url": {"url": encode_image(image_path)},
            })
    content.append({"type": "text", "text": prompt})

    payload = {
        "model": IMAGE_MODEL,
        "messages": [{"role": "user", "content": content}],
        "modalities": ["image", "text"],
        "image_config": {
            "aspect_ratio": aspect_ratio,
            "image_size": "1K",
        },
    }

    for attempt in range(1, IMAGE_RETRIES + 1):
        try:
            response = httpx.post(
                OPENROUTER_URL,
                json=payload,
                headers=openrouter_headers(),
                timeout=300,
            )
            response.raise_for_status()
            image_bytes = extract_image_bytes(response.json())
            if image_bytes:
                return image_bytes
        except Exception as exc:
            if attempt >= IMAGE_RETRIES:
                raise
            print(f"  Retry {attempt}: {exc}", flush=True)
            time.sleep(RETRY_DELAY * attempt)

    return None


def regenerate_item(
    number: str,
    ad_name: str,
    ratio: str,
    notes: str,
    batch_dir: Path,
    entry: dict,
) -> bool:
    copy_path = batch_dir / entry["copy_file"]
    if not copy_path.exists():
        print(f"[{number}] SKIP: copy file not found: {copy_path}", flush=True)
        return False

    aspect_ratio = ratio.replace("x", ":")
    suffix = ratio
    image_path = batch_dir / f"{ad_name}_{suffix}.png"

    # Check if this is a headline-only edit
    headline_match = re.match(
        r'headline should be ["\u201c](.+?)["\u201d]',
        notes,
        re.IGNORECASE,
    )
    if headline_match:
        new_headline = headline_match.group(1)
        print(f"[{number}] Updating headline to: {new_headline}", flush=True)
        update_headline_in_copy(copy_path, new_headline)

    base_prompt = parse_image_prompt(copy_path)
    if not base_prompt:
        print(f"[{number}] SKIP: no image prompt in {copy_path}", flush=True)
        return False

    feedback_prompt = base_prompt
    if notes:
        feedback_prompt += (
            f"\n\n### CRITICAL REVISION INSTRUCTION\n"
            f"The previous render was rejected. You MUST fix the following:\n"
            f"- {notes}\n"
            f"This is non-negotiable. The output MUST address the above feedback."
        )

    ref_paths = [PROJECT_ROOT / ref for ref in entry.get("reference_images", [])]

    print(f"[{number}] Generating {ad_name}_{suffix}...", flush=True)
    image_bytes = image_request(feedback_prompt, aspect_ratio, ref_paths)
    if not image_bytes:
        print(f"[{number}] FAILED: no image returned", flush=True)
        return False

    image_path.write_bytes(image_bytes)
    print(f"[{number}] Saved: {image_path.relative_to(PROJECT_ROOT)}", flush=True)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate ads based on review decisions")
    parser.add_argument("review_json", nargs="+", help="Path(s) to review-decisions JSON file(s)")
    parser.add_argument("--statics", required=True, help="Path to statics folder containing test-* batch dirs")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be regenerated")
    parser.add_argument("--include-rejects", action="store_true", help="Also regenerate rejected items")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers (default: 4)")
    args = parser.parse_args()

    statics_dir = Path(args.statics).resolve()
    batch_dirs = find_batch_dirs(statics_dir)
    manifest_index = build_manifest_index(batch_dirs)

    # Collect edit items from all review files, deduplicating by ad_name+ratio
    seen: set[str] = set()
    items: list[dict] = []
    target_decisions = {"edit"}
    if args.include_rejects:
        target_decisions.add("reject")

    for review_path_str in args.review_json:
        review_path = Path(review_path_str).resolve()
        for d in load_review_decisions(review_path):
            if d["decision"] not in target_decisions:
                continue
            key = f"{d['ad_name']}__{d['ratio']}"
            if key not in seen:
                seen.add(key)
                items.append(d)

    if not items:
        print("No items to regenerate.")
        return

    # Resolve manifest entries
    work: list[tuple[dict, Path, dict]] = []
    for item in items:
        ad_name = item["ad_name"]
        if ad_name not in manifest_index:
            print(f"[{item['number']}] SKIP: {ad_name} not found in any batch manifest")
            continue
        batch_dir, entry = manifest_index[ad_name]
        work.append((item, batch_dir, entry))

    print(f"{'DRY RUN: ' if args.dry_run else ''}Regenerating {len(work)} items with {args.workers} workers\n")

    if args.dry_run:
        for item, batch_dir, entry in work:
            print(f"[{item['number']}] {item['ad_name']}_{item['ratio']}.png — {item.get('notes', '')}")
        print(f"\n{len(work)} items would be regenerated.")
        return

    succeeded = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                regenerate_item,
                item["number"],
                item["ad_name"],
                item["ratio"],
                item.get("notes", "").strip(),
                batch_dir,
                entry,
            ): item
            for item, batch_dir, entry in work
        }
        for future in as_completed(futures):
            item = futures[future]
            try:
                ok = future.result()
                if ok:
                    succeeded += 1
                else:
                    failed += 1
            except Exception as exc:
                print(f"[{item['number']}] ERROR: {exc}", flush=True)
                failed += 1

    print(f"\nDone: {succeeded} succeeded, {failed} failed")

    if succeeded:
        print(f"\nNext steps:")
        print(f"  1. Rebuild ad sets:  python3 scripts/ad_set_builder.py --folder {statics_dir}")
        print(f"  2. Rebuild review:   python3 scripts/build-review-html.py <ad-sets-folder>")


if __name__ == "__main__":
    main()
