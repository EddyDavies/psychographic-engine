"""
Package approved creatives into local ad set folders.

Used by review-server.py: when all ads in a set are approved, the set is copied
into `ad_sets_YYYY-MM-DD/set_XX/` beside the statics folder, with an
`ad_copy.json` describing its variants.
"""

from __future__ import annotations

import shutil
import time
from datetime import datetime
from pathlib import Path

from utils import (
    DELAY_BETWEEN_IMAGES,
    encode_image,
    json_dump,
    recompose,
)


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
