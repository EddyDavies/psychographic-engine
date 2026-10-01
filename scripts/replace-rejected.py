#!/usr/bin/env python3
"""
Replace rejected ads with new visual format × messaging concept combinations.

Reads a review JSON, finds rejected ads, picks unused visual formats from the
same awareness-bucket pool, and runs the full copy + image pipeline to generate
replacements. Updates the batch manifest with the new entries.

Usage:
  python3 scripts/replace-rejected.py <review.json> --statics <statics-folder> --client <client>
"""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

import importlib
_gen = importlib.import_module("generate-ads")

ADS_PER_SET = _gen.ADS_PER_SET
FORMAT_POOLS = _gen.FORMAT_POOLS
AdTask = _gen.AdTask
Angle = _gen.Angle
build_render_prompt = _gen.build_render_prompt
find_reference_images = _gen.find_reference_images
generate_angle_brief = _gen.generate_angle_brief
generate_reviewable_ad_copy = _gen.generate_reviewable_ad_copy
image_request = _gen.image_request
load_awareness_levels = _gen.load_awareness_levels
load_markdown_library = _gen.load_markdown_library
parse_ranked_angles = _gen.parse_ranked_angles
resolve_brand_context = _gen.resolve_brand_context
resolve_product_context = _gen.resolve_product_context
write_copy_file = _gen.write_copy_file
write_image_metadata = _gen.write_image_metadata

from review_engine import (
    derive_creative_review_status,
    force_human_review,
    load_review_config,
    resolve_offer_context,
    review_rendered_image,
)
from utils import PROJECT_ROOT, json_dump

DELAY_BETWEEN_IMAGES = 3
IMAGE_REVIEW_ATTEMPTS = 3


def load_review_decisions(path: Path) -> list[dict]:
    return json.loads(path.read_text())["decisions"]


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
            stem = Path(entry["copy_file"]).stem.removesuffix("-copy")
            index[stem] = (batch_dir, entry)
    return index


def find_rejected_by_set(
    decisions: list[dict],
    manifest_index: dict[str, tuple[Path, dict]],
) -> dict[str, list[dict]]:
    """Group rejected ads by ad_set_key."""
    by_ad: dict[str, list[str]] = defaultdict(list)
    for d in decisions:
        if d["decision"] == "reject":
            by_ad[d["ad_name"]].append(d["ratio"])

    # Only include ads where both ratios are rejected
    fully_rejected = [name for name, ratios in by_ad.items() if len(ratios) == 2]

    sets: dict[str, list[dict]] = defaultdict(list)
    for name in fully_rejected:
        if name in manifest_index:
            _, entry = manifest_index[name]
            sets[entry["ad_set_key"]].append(entry)

    return dict(sets)


def pick_replacement_visuals(
    set_key: str,
    rejected_entries: list[dict],
    manifest_index: dict[str, tuple[Path, dict]],
) -> list[tuple[str, str]]:
    """Pick new visual × messaging combos for rejected ads."""
    # Find all entries in this set
    all_set_entries = [e for _, e in manifest_index.values() if e["ad_set_key"] == set_key]
    rejected_stems = {Path(e["copy_file"]).stem.removesuffix("-copy") for e in rejected_entries}

    # What's currently used (approved + rejected)
    approved_visuals = {
        e["visual_format"] for e in all_set_entries
        if Path(e["copy_file"]).stem.removesuffix("-copy") not in rejected_stems
    }
    rejected_visuals = {e["visual_format"] for e in rejected_entries}
    all_used_visuals = approved_visuals | rejected_visuals

    bucket = rejected_entries[0]["awareness_bucket"]
    pool = FORMAT_POOLS[bucket]

    # Available = pool visuals not used by any current ads (approved or rejected)
    available = [v for v in pool if v not in all_used_visuals]

    replacements = []
    already_picked: set[str] = set()
    for i, rejected in enumerate(rejected_entries):
        candidates = [v for v in available if v not in already_picked]
        if candidates:
            new_visual = candidates[0]
        else:
            # Fallback: reuse a rejected visual (will get entirely fresh copy + images)
            fallback = [v for v in pool if v not in approved_visuals and v not in already_picked]
            new_visual = fallback[0] if fallback else pool[i % len(pool)]

        already_picked.add(new_visual)
        replacements.append((new_visual, rejected["messaging_concept"]))

    return replacements


def find_angle_for_set(
    set_key: str,
    all_angles: list[Angle],
) -> Angle | None:
    for angle in all_angles:
        candidate_key = f"{angle.sub_avatar}--{angle.angle_slug}"
        if candidate_key == set_key:
            return angle
        # Also try pipe separator
        candidate_key2 = f"{angle.sub_avatar}|{angle.angle_slug}"
        if candidate_key2 == set_key:
            return angle
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Replace rejected ads with new visual combos")
    parser.add_argument("review_json", nargs="+", help="Review decisions JSON file(s)")
    parser.add_argument("--statics", required=True, help="Statics folder with test-* batch dirs")
    parser.add_argument("--client", required=True, help="Client name (e.g. acme)")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without generating")
    args = parser.parse_args()

    statics_dir = Path(args.statics).resolve()
    client_dir = PROJECT_ROOT / "clients" / args.client
    avatars_dir = client_dir / "avatars"
    offer_images_dir = client_dir / "offers" / "images"
    has_reference_images = offer_images_dir.exists() and any(offer_images_dir.iterdir())
    asset_mode = "physical" if has_reference_images else "digital"

    batch_dirs = find_batch_dirs(statics_dir)
    manifest_index = build_manifest_index(batch_dirs)

    # Collect all rejected ads from all review files
    all_decisions: list[dict] = []
    for rj in args.review_json:
        all_decisions.extend(load_review_decisions(Path(rj).resolve()))

    rejected_by_set = find_rejected_by_set(all_decisions, manifest_index)

    if not rejected_by_set:
        print("No rejected ads to replace.")
        return

    # Load pipeline resources
    ranked_files = sorted(avatars_dir.glob("core-*/ranked-angles.md"))
    all_angles: list[Angle] = []
    for rf in ranked_files:
        all_angles.extend(parse_ranked_angles(rf))

    awareness_levels = load_awareness_levels(avatars_dir)
    visual_library = load_markdown_library(PROJECT_ROOT / "prompts" / "concepts" / "visual")
    messaging_library = load_markdown_library(PROJECT_ROOT / "prompts" / "concepts" / "messaging")
    angle_brief_template = (PROJECT_ROOT / "prompts" / "angles" / "angle-brief.md").read_text()
    ad_assembly_template = (PROJECT_ROOT / "prompts" / "concepts" / "ad-assembly.md").read_text()
    brand_voice, brand_visual_identity, brand_no_gos = resolve_brand_context(client_dir)
    review_config = load_review_config(client_dir)
    offer_context = resolve_offer_context(review_config)

    # Plan replacements
    total_replacements = 0
    plan: list[tuple[str, list[dict], list[tuple[str, str]], Angle]] = []

    for set_key, rejected_entries in sorted(rejected_by_set.items()):
        replacements = pick_replacement_visuals(set_key, rejected_entries, manifest_index)
        angle = find_angle_for_set(set_key, all_angles)

        if not angle:
            print(f"WARNING: no angle found for {set_key}, skipping")
            continue

        plan.append((set_key, rejected_entries, replacements, angle))
        total_replacements += len(replacements)

        print(f"\n{set_key} ({len(rejected_entries)} rejected -> {len(replacements)} replacement(s))")
        for (new_vis, msg), old in zip(replacements, rejected_entries):
            old_vis = old["visual_format"]
            print(f"  {old_vis} x {msg}  ->  {new_vis} x {msg}")

    print(f"\nTotal: {total_replacements} ads to generate")

    if args.dry_run:
        return

    # Generate replacements
    angle_brief_cache: dict[Path, str] = {}
    succeeded = 0
    failed = 0

    for set_key, rejected_entries, replacements, angle in plan:
        batch_dir = manifest_index[Path(rejected_entries[0]["copy_file"]).stem.removesuffix("-copy")][0]

        # Generate angle brief (cached)
        if angle.angle_path not in angle_brief_cache:
            product_context = resolve_product_context(client_dir, angle)
            sub_avatar_profile = (angle.angle_path.parent / "profile.md").read_text()
            angle_brief_cache[angle.angle_path] = generate_angle_brief(
                angle_brief_template, angle, sub_avatar_profile, product_context,
            )
        angle_brief = angle_brief_cache[angle.angle_path]

        for (new_visual, messaging_slug), old_entry in zip(replacements, rejected_entries):
            old_stem = Path(old_entry["copy_file"]).stem.removesuffix("-copy")
            new_stem = f"{new_visual}-{messaging_slug}-{angle.angle_slug}"

            print(f"\n--- Replacing {old_stem} with {new_stem} ---")

            # Create a fake AdTask for the pipeline
            task = AdTask(
                sequence=old_entry["sequence"],
                angle=angle,
                awareness_bucket=old_entry["awareness_bucket"],
                visual_slug=new_visual,
                messaging_slug=messaging_slug,
                batch_dir=batch_dir,
            )

            try:
                # Generate copy
                copy_data, copy_review, copy_attempts = generate_reviewable_ad_copy(
                    ad_assembly_template,
                    task,
                    angle_brief,
                    messaging_library[messaging_slug],
                    visual_library[new_visual],
                    brand_voice,
                    brand_visual_identity,
                    brand_no_gos,
                    review_config,
                    offer_context,
                    asset_mode,
                )
                copy_path = write_copy_file(task, copy_data)
                print(f"  Copy: {copy_path.relative_to(PROJECT_ROOT)}")

                if copy_review["status"] != "passed":
                    print(f"  Copy blocked by hard rules: {copy_review.get('summary', '')}")

                # Generate images
                reference_images = find_reference_images(client_dir, new_visual)
                image_files: dict[str, str] = {}

                for aspect_ratio, suffix in [("9:16", "9x16"), ("1:1", "1x1")]:
                    image_path = batch_dir / f"{task.stem}_{suffix}.png"
                    failures_for_retry: list[dict[str, str]] = []
                    final_review = None

                    for review_attempt in range(1, IMAGE_REVIEW_ATTEMPTS + 1):
                        render_prompt = build_render_prompt(
                            copy_data["image_prompt"],
                            review_config,
                            new_visual,
                            offer_context,
                            failures_for_retry,
                        )
                        image_bytes = image_request(render_prompt, aspect_ratio, reference_images)
                        if not image_bytes:
                            raise RuntimeError(f"Image generation failed for {task.stem} ({aspect_ratio})")

                        image_path.write_bytes(image_bytes)
                        final_review = review_rendered_image(
                            review_config, new_visual, aspect_ratio,
                            copy_data, render_prompt, image_path,
                            reference_images, offer_context,
                        )

                        if final_review["status"] == "passed":
                            break
                        if final_review["status"] != "failed_regenerate":
                            break

                        failures_for_retry = [
                            f for f in final_review.get("hard_rule_failures", [])
                            if isinstance(f, dict)
                        ]
                        print(f"  {suffix} failed review attempt {review_attempt}, retrying...")
                        if review_attempt < IMAGE_REVIEW_ATTEMPTS:
                            time.sleep(DELAY_BETWEEN_IMAGES)

                    if final_review and final_review["status"] == "failed_regenerate":
                        final_review = force_human_review(final_review, IMAGE_REVIEW_ATTEMPTS)

                    write_image_metadata(
                        task, suffix, image_path, copy_data,
                        reference_images, render_prompt, final_review, review_attempt,
                    )
                    image_files[suffix] = image_path.name
                    print(f"  Image: {image_path.relative_to(PROJECT_ROOT)} [{final_review.get('status')}]")
                    time.sleep(DELAY_BETWEEN_IMAGES)

                # Update manifest: remove old entry, add new one
                manifest_path = batch_dir / "manifest.json"
                manifest = json.loads(manifest_path.read_text())
                manifest = [e for e in manifest if Path(e["copy_file"]).stem.removesuffix("-copy") != old_stem]

                review_results = {}
                new_entry = {
                    "sequence": old_entry["sequence"],
                    "ad_set_key": old_entry["ad_set_key"],
                    "core_avatar": angle.core_avatar,
                    "sub_avatar": angle.sub_avatar,
                    "angle_name": angle.angle_name,
                    "angle_slug": angle.angle_slug,
                    "awareness_bucket": old_entry["awareness_bucket"],
                    "visual_format": new_visual,
                    "messaging_concept": messaging_slug,
                    "copy_file": copy_path.name,
                    "headline": copy_data["headline"],
                    "primary_text": copy_data["primary_text"],
                    "image_files": image_files,
                    "reference_images": [
                        str(p.relative_to(PROJECT_ROOT)) for p in reference_images if p.exists()
                    ],
                    "copy_review": copy_review,
                    "copy_review_attempts": copy_attempts,
                    "review_results": review_results,
                    "review_status": derive_creative_review_status(review_results) if review_results else "passed",
                    "angle_brief_file": None,
                }
                manifest.append(new_entry)
                json_dump(manifest, manifest_path)

                succeeded += 1

            except Exception as exc:
                print(f"  FAILED: {exc}")
                failed += 1

    print(f"\n{'='*50}")
    print(f"Done: {succeeded} replaced, {failed} failed")

    if succeeded:
        print(f"\nNext steps:")
        print(f"  1. Rebuild ad sets:  python3 scripts/ad_set_builder.py --folder {statics_dir}")
        print(f"  2. Rebuild review:   python3 scripts/build-review-html.py <ad-sets-folder>")


if __name__ == "__main__":
    main()
