#!/usr/bin/env python3
"""
Generate static ad batches using the angle-brief + ad-assembly pipeline.

`--dry-run` still generates angle briefs, copy files, and manifests. It only skips
the image-rendering step so batch structure can be reviewed before spending image credits.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from review_engine import (
    build_copy_rule_context,
    build_render_rule_block,
    creative_quality_review,
    derive_creative_review_status,
    force_human_review,
    load_review_config,
    resolve_offer_context,
    review_copy_rules,
    review_rendered_image,
)
from utils import (
    PROJECT_ROOT,
    SUPPORTED_EXTENSIONS,
    encode_image,
    extract_image_bytes,
    get_env,
    get_google_services,
    json_dump,
    openrouter_headers,
)

TEXT_MODEL = get_env("OPENROUTER_TEXT_MODEL", "anthropic/claude-sonnet-4-6")
IMAGE_MODEL = get_env("OPENROUTER_IMAGE_MODEL", "google/gemini-3.1-flash-image-preview")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
TEXT_RETRIES = 3
IMAGE_RETRIES = 3
RETRY_DELAY = 5
DELAY_BETWEEN_IMAGES = 3
ADS_PER_SET = 3
DEFAULT_ADS_PER_ANGLE = ADS_PER_SET
COPY_REVIEW_ATTEMPTS = 3
IMAGE_REVIEW_ATTEMPTS = 3

FORMAT_POOLS = {
    "emotional": [
        "relatable-hook",
        "accidental-ideal-outcome",
        "pubity-style",
        "avatar-callout",
        "indirect-avatar",
    ],
    "product": [
        "annotated-lifestyle",
        "annotated-lifestyle-hero",
        "annotated-lifestyle-flexible",
        "studio-product-hero",
        "flatlay-product-grid",
        "ugc-whiteboard-kitchen",
        "solution-exaggeration",
    ],
    "offer": [
        "classy-offer",
        "the-free-ad",
        "stealing-credibility",
        "this-is-not",
        "specific-pain-point",
        "simplified-us-vs-them",
        "minimal-us-vs-them",
    ],
}

SPREAD_FORMATS = {
    "annotated-lifestyle",
    "annotated-lifestyle-hero",
    "annotated-lifestyle-flexible",
    "flatlay-product-grid",
    "classy-offer",
    "the-free-ad",
}


@dataclass(frozen=True)
class Angle:
    core_avatar: str
    sub_avatar: str
    angle_num: int
    angle_name: str
    angle_slug: str
    reason_to_buy: str
    angle_path: Path


@dataclass(frozen=True)
class AdTask:
    sequence: int
    angle: Angle
    awareness_bucket: str
    visual_slug: str
    messaging_slug: str
    batch_dir: Path

    @property
    def ad_set_key(self) -> str:
        return f"{self.angle.sub_avatar}--{self.angle.angle_slug}"

    @property
    def stem(self) -> str:
        return f"{self.visual_slug}-{self.messaging_slug}-{self.angle.angle_slug}"


def parse_ranked_angles(ranked_angles_path: Path) -> list[Angle]:
    text = ranked_angles_path.read_text()
    core_name = ranked_angles_path.parent.name

    angles: list[Angle] = []
    current_sub: str | None = None
    current_angle: dict[str, object] | None = None

    def flush_current() -> None:
        nonlocal current_angle
        if not current_angle:
            return
        required = {"sub_avatar", "angle_num", "angle_name", "reason_to_buy", "angle_path"}
        if required.issubset(current_angle):
            angle_path = ranked_angles_path.parent / str(current_angle["angle_path"])
            angles.append(
                Angle(
                    core_avatar=core_name,
                    sub_avatar=str(current_angle["sub_avatar"]),
                    angle_num=int(current_angle["angle_num"]),
                    angle_name=str(current_angle["angle_name"]),
                    angle_slug=angle_path.stem.removeprefix("angle-"),
                    reason_to_buy=str(current_angle["reason_to_buy"]),
                    angle_path=angle_path,
                )
            )
        current_angle = None

    for raw_line in text.splitlines():
        line = raw_line.strip()

        sub_match = re.match(r"^## (sub-[\w-]+)", line)
        if sub_match:
            flush_current()
            current_sub = sub_match.group(1)
            continue

        angle_match = re.match(r"^\*\*Angle (\d+): (.+)\*\*$", line)
        if angle_match and current_sub:
            flush_current()
            current_angle = {
                "sub_avatar": current_sub,
                "angle_num": int(angle_match.group(1)),
                "angle_name": angle_match.group(2),
            }
            continue

        reason_match = re.match(r"^Reason to Buy: (.+)$", line)
        if reason_match and current_angle is not None:
            current_angle["reason_to_buy"] = reason_match.group(1)
            continue

        path_match = re.match(r"^-> \[full angle\]\((.+)\)$", line)
        if path_match and current_angle is not None:
            current_angle["angle_path"] = path_match.group(1)

    flush_current()
    return angles


def load_awareness_levels(avatars_dir: Path) -> dict[str, str]:
    awareness_levels: dict[str, str] = {}

    for profile_path in sorted(avatars_dir.glob("core-*/sub-*/profile.md")):
        text = profile_path.read_text()
        match = re.search(r"## Awareness Level\s*\n(.+?)(?=\n## |\Z)", text, re.DOTALL)
        if not match:
            continue
        awareness_levels[profile_path.parent.name] = normalize_awareness_bucket(match.group(1))

    return awareness_levels


def normalize_awareness_bucket(section_text: str) -> str:
    bold_match = re.search(r"\*\*(.+?)\*\*", section_text)
    label = bold_match.group(1) if bold_match else section_text.strip()
    label = label.replace("->", "→")

    if "→" in label:
        label = label.split("→", 1)[0].strip()

    lowered = label.lower()
    if "problem aware" in lowered:
        return "emotional"
    if "solution aware" in lowered:
        return "product"
    if "product aware" in lowered or "most aware" in lowered:
        return "offer"
    return "product"


def load_markdown_library(directory: Path) -> dict[str, str]:
    library: dict[str, str] = {}
    for path in sorted(directory.glob("*.md")):
        if path.name in {"README.md", "_template.md"}:
            continue
        library[path.stem] = path.read_text()
    return library


def resolve_brand_context(client_dir: Path) -> tuple[str, str, str]:
    voice = (client_dir / "brand" / "guidelines" / "voice.md").read_text()
    visual_identity = (client_dir / "brand" / "guidelines" / "visual-identity.md").read_text()
    no_gos = (client_dir / "brand" / "no-gos" / "no-gos.md").read_text()
    return voice, visual_identity, no_gos


def resolve_product_context(client_dir: Path, angle: Angle) -> str:
    parts: list[str] = []

    products_dir = client_dir / "products"
    offers_dir = client_dir / "offers"

    for md in sorted(products_dir.glob("*.md")):
        if md.name in {"_template.md", "shared-mechanisms.md"}:
            continue
        parts.append(md.read_text())

    for md in sorted(offers_dir.glob("*.md")):
        if md.name == "_template.md":
            continue
        parts.append(md.read_text())

    if not parts:
        shared = products_dir / "shared-mechanisms.md"
        if shared.exists():
            parts.append(shared.read_text())

    return "\n\n".join(parts)


def llm_call(messages: list[dict], temperature: float = 0.5) -> str:
    import httpx

    payload = {
        "model": TEXT_MODEL,
        "messages": messages,
        "temperature": temperature,
    }

    last_error: Exception | None = None
    for attempt in range(1, TEXT_RETRIES + 1):
        try:
            response = httpx.post(
                OPENROUTER_URL,
                json=payload,
                headers=openrouter_headers(),
                timeout=300,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            last_error = exc
            if attempt < TEXT_RETRIES:
                time.sleep(RETRY_DELAY)

    raise RuntimeError(f"LLM call failed after {TEXT_RETRIES} attempts: {last_error}")


def build_angle_source(angle: Angle) -> str:
    return (
        f"# Angle: {angle.angle_name}\n\n"
        f"**Reason to Buy:** {angle.reason_to_buy}\n\n"
        f"**Source File:** {angle.angle_path.relative_to(PROJECT_ROOT)}"
    )


def generate_angle_brief(
    template: str,
    angle: Angle,
    sub_avatar_profile: str,
    product_context: str,
) -> str:
    prompt = (
        f"{template}\n\n"
        "Use the template above and build the angle brief for the provided inputs.\n\n"
        f"**Product Knowledge:**\n{product_context}\n\n"
        f"**Angle:**\n{build_angle_source(angle)}\n\n"
        f"**Target Sub-Avatar(s):**\n{sub_avatar_profile}\n\n"
        "Return only the finished angle brief markdown in the exact template format."
    )
    return llm_call([{"role": "user", "content": prompt}], temperature=0.3)


def parse_copy_sections(raw_markdown: str) -> dict[str, str] | None:
    def clean_block(value: str) -> str:
        return re.sub(r"\n+---\s*$", "", value.strip(), flags=re.DOTALL).strip()

    image_match = re.search(
        r"## Image Prompt\s*\n+(.+?)(?=\n## Primary Text)",
        raw_markdown,
        re.DOTALL,
    )
    primary_match = re.search(
        r"## Primary Text\s*\n+(.+?)(?=\n## Headline)",
        raw_markdown,
        re.DOTALL,
    )
    headline_match = re.search(
        r"## Headline\s*\n+(.+?)\s*$",
        raw_markdown,
        re.DOTALL,
    )

    if not all([image_match, primary_match, headline_match]):
        return None

    headline = headline_match.group(1).strip()
    if len(headline) > 40:
        headline = headline[:40].rsplit(" ", 1)[0].rstrip() or headline[:40].strip()

    return {
        "image_prompt": clean_block(image_match.group(1)),
        "primary_text": clean_block(primary_match.group(1)),
        "headline": headline,
    }


def generate_ad_copy(
    template: str,
    task: AdTask,
    angle_brief: str,
    messaging_concept: str,
    visual_concept: str,
    brand_voice: str,
    brand_visual_identity: str,
    brand_no_gos: str,
    review_context: str,
    asset_mode: str,
    correction_feedback: list[str] | None = None,
) -> dict[str, str]:
    for attempt in range(2):
        prompt = (
            f"{template}\n\n"
            "Create one assembled static ad for the combination below.\n\n"
            f"**Angle Brief:**\n{angle_brief}\n\n"
            f"**Messaging Concept ({task.messaging_slug}):**\n{messaging_concept}\n\n"
            f"**Visual Concept ({task.visual_slug}):**\n{visual_concept}\n\n"
            f"**Brand Voice:**\n{brand_voice}\n\n"
            f"**Brand Visual Identity:**\n{brand_visual_identity}\n\n"
            f"**Brand No-Gos:**\n{brand_no_gos}\n\n"
            f"{review_context}\n"
            "### Additional Instructions\n"
            "- The hook/headline must emerge from the angle × messaging concept collision.\n"
            "- Do not reuse any prewritten hooks from source angle files.\n"
            "- Keep the primary text to 3-6 sentences.\n"
            "- Keep the headline to 40 characters or fewer.\n"
            "- In the image prompt, start with a [MESSAGING DIRECTION] block and then provide the adapted visual prompt.\n"
            "- Replace any unresolved placeholders with concrete direction or final copy. Do not leave {placeholders} behind.\n\n"
            "- Only use social-proof numbers, star ratings, review counts, customer totals, or rankings when they are explicitly supported by the provided client/product inputs.\n"
            "- If those numbers are not explicitly supported, omit social proof entirely from both the primary text and the image prompt. Do not guess or substitute placeholder counts.\n"
            "Return exactly this markdown shape:\n"
            f"# {task.stem}\n\n"
            "## Image Prompt\n\n"
            "[full image prompt]\n\n"
            "## Primary Text\n\n"
            "[primary text]\n\n"
            "## Headline\n\n"
            "[headline]\n"
        )

        if asset_mode == "digital":
            prompt += (
                "\nThis client is a digital product/app, not a physical-product bundle.\n"
                "- Adapt any visual-template instructions about products, packaging, bundles, variants, or reference photos into app screens, devices, coach imagery, and grounded lifestyle scenes.\n"
                "- Do not mention or invent reference images, exact packaging replication, product counts, gift sets, free items, bottles, boxes, or packshots.\n"
                "- If the visual needs a 'hero product', use the client's app shown on a phone or device in a believable real-world setting.\n"
            )

        if attempt == 1:
            prompt += (
                "\nThe previous attempt did not satisfy the exact format or headline length. "
                "Return only the corrected markdown."
            )

        if correction_feedback:
            prompt += "\nFix these hard-rule issues in the next draft:\n"
            for feedback in correction_feedback:
                prompt += f"- {feedback}\n"

        raw = llm_call([{"role": "user", "content": prompt}], temperature=0.6)
        parsed = parse_copy_sections(raw)
        if parsed:
            parsed["raw_markdown"] = (
                f"# {task.stem}\n\n"
                f"## Image Prompt\n\n{parsed['image_prompt']}\n\n"
                f"## Primary Text\n\n{parsed['primary_text']}\n\n"
                f"## Headline\n\n{parsed['headline']}\n"
            )
            return parsed

    raise RuntimeError(f"Could not parse copy output for {task.stem}")


def generate_reviewable_ad_copy(
    template: str,
    task: AdTask,
    angle_brief: str,
    messaging_concept: str,
    visual_concept: str,
    brand_voice: str,
    brand_visual_identity: str,
    brand_no_gos: str,
    review_config: dict,
    offer_context: dict[str, str],
    asset_mode: str,
) -> tuple[dict[str, str], dict[str, object], int]:
    review_context = build_copy_rule_context(review_config, task.visual_slug, offer_context)
    feedback: list[str] = []
    last_copy_data: dict[str, str] | None = None
    last_review: dict[str, object] | None = None

    for attempt in range(1, COPY_REVIEW_ATTEMPTS + 1):
        copy_data = generate_ad_copy(
            template,
            task,
            angle_brief,
            messaging_concept,
            visual_concept,
            brand_voice,
            brand_visual_identity,
            brand_no_gos,
            review_context,
            asset_mode,
            correction_feedback=feedback,
        )
        review_result = review_copy_rules(review_config, copy_data, offer_context)
        copy_data["copy_review"] = review_result
        last_copy_data = copy_data
        last_review = review_result
        if review_result["status"] == "passed":
            return copy_data, review_result, attempt

        feedback = [
            failure.get("message", "Hard rule failed.")
            for failure in review_result.get("hard_rule_failures", [])
            if isinstance(failure, dict)
        ]

    assert last_copy_data is not None
    assert last_review is not None
    forced = force_human_review(last_review, COPY_REVIEW_ATTEMPTS)
    last_copy_data["copy_review"] = forced
    return last_copy_data, forced, COPY_REVIEW_ATTEMPTS


def rewrite_prompt_with_corrections(base_prompt: str, failures: list[dict[str, str]]) -> str:
    corrections = "\n".join(f"- {f.get('message', '').strip()}" for f in failures if f.get("message"))
    instruction = (
        "Rewrite the image generation prompt below so that the following corrections "
        "are naturally integrated into the prompt in the places where they belong. "
        "Do not add any section headers, labels, or meta-commentary about corrections. "
        "The output should read as if it was written correctly the first time. "
        "Keep the prompt's style, length, and structure intact.\n\n"
        f"Corrections to integrate:\n{corrections}\n\n"
        f"Original prompt:\n{base_prompt}"
    )
    return llm_call([{"role": "user", "content": instruction}], temperature=0.2)


def build_render_prompt(
    base_prompt: str,
    review_config: dict,
    visual_slug: str,
    offer_context: dict[str, str],
    failures: list[dict[str, str]] | None = None,
) -> str:
    prompt = base_prompt.rstrip()
    if failures:
        prompt = rewrite_prompt_with_corrections(prompt, failures)
    return f"{prompt}\n\n{build_render_rule_block(review_config, visual_slug, offer_context)}\n"


def image_request(prompt: str, aspect_ratio: str, reference_images: list[Path]) -> bytes | None:
    import httpx

    content: list[dict] = []
    for image_path in reference_images:
        if image_path.exists():
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": encode_image(image_path)},
                }
            )
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
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429 and attempt < IMAGE_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
                continue
            raise
        except httpx.HTTPError:
            if attempt >= IMAGE_RETRIES:
                raise

        time.sleep(RETRY_DELAY)

    return None


def find_reference_images(client_dir: Path, visual_slug: str) -> list[Path]:
    image_dirs = [
        client_dir / "offers" / "images",
        client_dir / "products" / "images",
    ]

    all_images: list[Path] = []
    for image_dir in image_dirs:
        if image_dir.is_dir():
            all_images.extend(sorted(p for p in image_dir.iterdir() if p.is_file()))

    if not all_images:
        return []

    if visual_slug in SPREAD_FORMATS:
        return all_images[:1]

    return all_images[:4]


def build_task_queue(
    angles: list[Angle],
    awareness_levels: dict[str, str],
    batch_date: date,
    output_root: Path,
    messaging_slugs: list[str],
    ads_per_angle: int,
    limit: int,
    has_real_offers: bool,
) -> list[AdTask]:
    queue: list[AdTask] = []
    messaging_index = 0
    visual_offsets: defaultdict[str, int] = defaultdict(int)

    for angle in angles:
        awareness_bucket = awareness_levels.get(angle.sub_avatar, "product")
        if awareness_bucket == "offer" and not has_real_offers:
            awareness_bucket = "product"
        visual_pool = FORMAT_POOLS[awareness_bucket]
        start_index = visual_offsets[awareness_bucket]

        for variation in range(ads_per_angle):
            if len(queue) >= limit:
                return queue

            visual_slug = visual_pool[(start_index + variation) % len(visual_pool)]
            messaging_slug = messaging_slugs[messaging_index % len(messaging_slugs)]
            messaging_index += 1

            queue.append(
                AdTask(
                    sequence=len(queue) + 1,
                    angle=angle,
                    awareness_bucket=awareness_bucket,
                    visual_slug=visual_slug,
                    messaging_slug=messaging_slug,
                    batch_dir=output_root / f"test-{angle.sub_avatar.removeprefix('sub-')}-{batch_date.isoformat()}",
                )
            )

        visual_offsets[awareness_bucket] = (start_index + ads_per_angle) % len(visual_pool)

    return queue


def write_copy_file(task: AdTask, copy_data: dict[str, str]) -> Path:
    task.batch_dir.mkdir(parents=True, exist_ok=True)
    output_path = task.batch_dir / f"{task.stem}-copy.md"
    output_path.write_text(copy_data["raw_markdown"])
    return output_path


def write_image_metadata(
    task: AdTask,
    ratio_label: str,
    image_path: Path,
    copy_data: dict[str, str],
    reference_images: list[Path],
    render_prompt: str,
    review_result: dict[str, object],
    review_attempt: int,
) -> None:
    metadata = {
        "ad_set_key": task.ad_set_key,
        "sequence": task.sequence,
        "core_avatar": task.angle.core_avatar,
        "sub_avatar": task.angle.sub_avatar,
        "angle_name": task.angle.angle_name,
        "angle_slug": task.angle.angle_slug,
        "awareness_bucket": task.awareness_bucket,
        "visual_format": task.visual_slug,
        "messaging_concept": task.messaging_slug,
        "aspect_ratio": ratio_label.replace("x", ":"),
        "copy_file": f"{task.stem}-copy.md",
        "headline": copy_data["headline"],
        "primary_text": copy_data["primary_text"],
        "render_prompt": render_prompt,
        "reference_images": [str(path.relative_to(PROJECT_ROOT)) for path in reference_images if path.exists()],
        "review": {
            "status": review_result.get("status"),
            "hard_rule_failures": review_result.get("hard_rule_failures", []),
            "manual_flags": review_result.get("manual_flags", []),
            "summary": review_result.get("summary", ""),
            "attempt": review_attempt,
        },
        "timestamp": datetime.now().astimezone().isoformat(),
    }
    json_dump(metadata, image_path.with_suffix(".json"))


class SetTracker:
    """Thread-safe tracker that detects when a set of N ads is complete."""

    def __init__(self, ads_per_set: int = ADS_PER_SET, on_set_complete=None):
        self.ads_per_set = ads_per_set
        self.on_set_complete = on_set_complete
        self._lock = threading.Lock()
        self._entries: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
        self._completed_sets: list[str] = []
        self._set_counter = 0

    def add_result(self, ad_set_key: str, entry: dict[str, object]) -> None:
        fire_callback = False
        set_number = 0
        entries: list[dict[str, object]] = []

        with self._lock:
            self._entries[ad_set_key].append(entry)
            if len(self._entries[ad_set_key]) == self.ads_per_set:
                self._set_counter += 1
                set_number = self._set_counter
                entries = list(self._entries[ad_set_key])
                self._completed_sets.append(ad_set_key)
                fire_callback = True

        if fire_callback and self.on_set_complete:
            self.on_set_complete(set_number, ad_set_key, entries)

    @property
    def completed_keys(self) -> list[str]:
        with self._lock:
            return list(self._completed_sets)


class StreamingUploader:
    """Packages and uploads completed ad sets to Drive, updates a Google Sheet."""

    SHEET_HEADERS = [
        "Set",
        "Date",
        "Sub-Avatar",
        "Angle",
        "Visual A",
        "Visual B",
        "Visual C",
        "Status",
        "Drive Link",
    ]

    MIME_TYPES = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".md": "text/markdown",
        ".json": "application/json",
    }

    def __init__(self, drive_service, folder_name: str, output_root: Path):
        self._drive = drive_service
        self._output_root = output_root
        self._lock = threading.Lock()
        self._batch_folder_id: str | None = None
        self._tracker_file_id: str | None = None
        self._tracker_rows: list[list[str]] = []
        self._folder_name = folder_name
        self._print_lock = threading.Lock()

    def _ensure_batch_folder(self) -> str:
        if self._batch_folder_id:
            return self._batch_folder_id

        folder = self._drive.files().create(
            body={"name": self._folder_name, "mimeType": "application/vnd.google-apps.folder"},
            fields="id",
        ).execute()
        self._batch_folder_id = folder["id"]

        self._drive.permissions().create(
            fileId=self._batch_folder_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()

        with self._print_lock:
            print(
                f"Drive folder: https://drive.google.com/drive/folders/{self._batch_folder_id}",
                flush=True,
            )
        return self._batch_folder_id

    def _upload_tracker_csv(self) -> None:
        """Write tracker rows to a local CSV then upload/update on Drive."""
        import csv
        import io
        from googleapiclient.http import MediaInMemoryUpload

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(self.SHEET_HEADERS)
        writer.writerows(self._tracker_rows)
        csv_bytes = buf.getvalue().encode("utf-8")
        media = MediaInMemoryUpload(csv_bytes, mimetype="text/csv", resumable=False)

        batch_id = self._ensure_batch_folder()
        file_name = f"{self._folder_name}_tracker.csv"

        if self._tracker_file_id:
            self._drive.files().update(
                fileId=self._tracker_file_id,
                media_body=media,
            ).execute()
        else:
            result = self._drive.files().create(
                body={"name": file_name, "parents": [batch_id]},
                media_body=media,
                fields="id",
            ).execute()
            self._tracker_file_id = result["id"]
            with self._print_lock:
                print(f"Tracker CSV uploaded: {file_name}", flush=True)

    def upload_set(self, set_number: int, ad_set_key: str, entries: list[dict]) -> str | None:
        from googleapiclient.http import MediaFileUpload

        with self._lock:
            batch_id = self._ensure_batch_folder()

        set_name = f"set_{set_number:02d}"
        batch_dir = entries[0].get("_batch_dir")
        if not batch_dir:
            return None

        set_folder = self._drive.files().create(
            body={
                "name": set_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [batch_id],
            },
            fields="id",
        ).execute()
        set_folder_id = set_folder["id"]

        uploaded = 0
        for entry in sorted(entries, key=lambda e: e.get("sequence", 0)):
            copy_file = Path(batch_dir) / str(entry["copy_file"])
            if copy_file.exists():
                media = MediaFileUpload(str(copy_file), mimetype="text/markdown", resumable=False)
                self._drive.files().create(
                    body={"name": copy_file.name, "parents": [set_folder_id]},
                    media_body=media,
                    fields="id",
                ).execute()
                uploaded += 1

            image_files = entry.get("image_files", {})
            for suffix, filename in sorted(image_files.items()):
                image_path = Path(batch_dir) / filename
                if not image_path.exists():
                    continue
                mime = self.MIME_TYPES.get(image_path.suffix.lower(), "application/octet-stream")
                media = MediaFileUpload(str(image_path), mimetype=mime, resumable=False)
                self._drive.files().create(
                    body={"name": image_path.name, "parents": [set_folder_id]},
                    media_body=media,
                    fields="id",
                ).execute()
                uploaded += 1

                sidecar = image_path.with_suffix(".json")
                if sidecar.exists():
                    media = MediaFileUpload(str(sidecar), mimetype="application/json", resumable=False)
                    self._drive.files().create(
                        body={"name": sidecar.name, "parents": [set_folder_id]},
                        media_body=media,
                        fields="id",
                    ).execute()
                    uploaded += 1

        link = f"https://drive.google.com/drive/folders/{set_folder_id}"

        with self._print_lock:
            print(f"  Uploaded {set_name}: {uploaded} files -> {link}", flush=True)

        return link

    def update_tracker(
        self,
        set_number: int,
        ad_set_key: str,
        entries: list[dict],
        drive_link: str,
        batch_date: str,
    ) -> None:
        parts = ad_set_key.split("--", 1)
        sub_avatar = parts[0] if parts else ad_set_key
        angle = parts[1] if len(parts) > 1 else ""

        visuals = [str(e.get("visual_format", "")) for e in sorted(entries, key=lambda e: e.get("sequence", 0))]
        statuses = [str(e.get("review_status", "")) for e in entries]
        overall = "passed" if all(s == "passed" for s in statuses) else "needs_review"

        row = [
            f"set_{set_number:02d}",
            batch_date,
            sub_avatar,
            angle,
            visuals[0] if len(visuals) > 0 else "",
            visuals[1] if len(visuals) > 1 else "",
            visuals[2] if len(visuals) > 2 else "",
            overall,
            drive_link,
        ]

        with self._lock:
            self._tracker_rows.append(row)
            self._upload_tracker_csv()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate static ad batches from ranked angles")
    parser.add_argument("--client", required=True, help="Client name (e.g. acme)")
    parser.add_argument("--count", type=int, default=6, help="Number of ads to generate")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate angle briefs, copy files, and manifests only",
    )
    parser.add_argument(
        "--sub-avatar",
        action="append",
        help="Limit generation to one or more sub-avatar names",
    )
    parser.add_argument(
        "--messaging",
        nargs="+",
        help="Optional list of messaging concept slugs to cycle through",
    )
    parser.add_argument("--skip", type=int, default=0, help="Skip the first N queued ads")
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers for ad generation (default: 1 = sequential)",
    )
    parser.add_argument(
        "--upload-r2",
        action="store_true",
        help="Upload generated batches to R2 after generation",
    )
    parser.add_argument(
        "--ads-per-angle",
        type=int,
        default=DEFAULT_ADS_PER_ANGLE,
        help="Fixed at 3 to keep every ad set at 3 creatives",
    )
    parser.add_argument(
        "--date",
        help="Override the batch date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload completed ad sets to Google Drive as they finish",
    )
    parser.add_argument(
        "--sheet",
        action="store_true",
        help="Update a Google Sheet tracker in the Drive folder (implies --upload)",
    )
    parser.add_argument(
        "--drive-folder",
        help="Custom Drive folder name (default: {client}-ads-{date})",
    )
    args = parser.parse_args()

    if args.sheet:
        args.upload = True

    client_dir = PROJECT_ROOT / "clients" / args.client
    avatars_dir = client_dir / "avatars"
    output_root = client_dir / "ads" / "statics"
    output_root.mkdir(parents=True, exist_ok=True)

    if args.ads_per_angle != ADS_PER_SET:
        print(
            f"Error: --ads-per-angle is fixed at {ADS_PER_SET} so every set has 3 ads.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.count % ADS_PER_SET != 0:
        print(
            f"Error: --count must be a multiple of {ADS_PER_SET} so sets are complete.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.skip % ADS_PER_SET != 0:
        print(
            f"Error: --skip must be a multiple of {ADS_PER_SET} to avoid partial sets.",
            file=sys.stderr,
        )
        sys.exit(1)

    ranked_files = sorted(avatars_dir.glob("core-*/ranked-angles.md"))
    if not ranked_files:
        print(f"Error: no ranked-angles.md files found in {avatars_dir}", file=sys.stderr)
        sys.exit(1)

    all_angles: list[Angle] = []
    for ranked_file in ranked_files:
        all_angles.extend(parse_ranked_angles(ranked_file))

    if args.sub_avatar:
        allowed = set(args.sub_avatar)
        all_angles = [angle for angle in all_angles if angle.sub_avatar in allowed]

    if not all_angles:
        print("Error: no angles matched the current filters", file=sys.stderr)
        sys.exit(1)

    awareness_levels = load_awareness_levels(avatars_dir)
    visual_library = load_markdown_library(PROJECT_ROOT / "prompts" / "concepts" / "visual")
    messaging_library = load_markdown_library(PROJECT_ROOT / "prompts" / "concepts" / "messaging")
    angle_brief_template = (PROJECT_ROOT / "prompts" / "angles" / "angle-brief.md").read_text()
    ad_assembly_template = (PROJECT_ROOT / "prompts" / "concepts" / "ad-assembly.md").read_text()
    brand_voice, brand_visual_identity, brand_no_gos = resolve_brand_context(client_dir)
    review_config = load_review_config(client_dir)
    offer_context = resolve_offer_context(review_config)

    messaging_slugs = args.messaging or sorted(messaging_library)
    missing_messages = [slug for slug in messaging_slugs if slug not in messaging_library]
    if missing_messages:
        print(f"Error: unknown messaging concepts: {', '.join(missing_messages)}", file=sys.stderr)
        sys.exit(1)

    missing_visuals = [slug for pool in FORMAT_POOLS.values() for slug in pool if slug not in visual_library]
    if missing_visuals:
        print(
            f"Error: missing visual concept files: {', '.join(sorted(set(missing_visuals)))}",
            file=sys.stderr,
        )
        sys.exit(1)

    batch_date = date.fromisoformat(args.date) if args.date else date.today()
    has_real_offers = any(
        path.name != "_template.md" for path in (client_dir / "offers").glob("*.md")
    )
    offer_images_dir = client_dir / "offers" / "images"
    has_reference_images = offer_images_dir.exists() and any(offer_images_dir.iterdir())
    asset_mode = "physical" if has_reference_images else "digital"
    queue = build_task_queue(
        angles=all_angles,
        awareness_levels=awareness_levels,
        batch_date=batch_date,
        output_root=output_root,
        messaging_slugs=messaging_slugs,
        ads_per_angle=max(1, args.ads_per_angle),
        limit=args.count + max(args.skip, 0),
        has_real_offers=has_real_offers,
    )

    if args.skip:
        queue = queue[args.skip :]
    queue = queue[: args.count]

    if not queue:
        print("Error: queue is empty after applying skip/count", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(all_angles)} ranked angles")
    print(f"Queued {len(queue)} ads across {len({task.batch_dir for task in queue})} batch folder(s)")
    print(f"Mode: {'copy-only dry run' if args.dry_run else 'copy + image render'}\n")

    angle_brief_cache: dict[Path, str] = {}
    angle_brief_lock = threading.Lock()
    manifests: defaultdict[Path, list[dict[str, object]]] = defaultdict(list)
    manifest_lock = threading.Lock()
    print_lock = threading.Lock()
    failed_ads: list[tuple[int, str, str]] = []
    failed_lock = threading.Lock()

    # --- Streaming upload setup ---
    uploader: StreamingUploader | None = None
    if args.upload and not args.dry_run:
        drive_service, _ = get_google_services()
        folder_name = args.drive_folder or f"{args.client}-ads-{batch_date.isoformat()}"
        uploader = StreamingUploader(
            drive_service,
            folder_name,
            output_root,
        )
        uploader._print_lock = print_lock

    def on_set_complete(set_number: int, ad_set_key: str, entries: list[dict]) -> None:
        with print_lock:
            print(f"\n  SET COMPLETE: set_{set_number:02d} ({ad_set_key})", flush=True)

        if not uploader:
            return

        try:
            link = uploader.upload_set(set_number, ad_set_key, entries)
            if link and args.sheet:
                uploader.update_tracker(
                    set_number,
                    ad_set_key,
                    entries,
                    link,
                    batch_date.isoformat(),
                )
        except Exception as exc:
            with print_lock:
                print(f"  Upload failed for set_{set_number:02d}: {exc}", flush=True, file=sys.stderr)

    set_tracker = SetTracker(ads_per_set=ADS_PER_SET, on_set_complete=on_set_complete)

    def process_ad(index: int, task: AdTask) -> dict[str, object]:
        with print_lock:
            print(
                f"[{index}/{len(queue)}] {task.angle.sub_avatar} | {task.angle.angle_name} "
                f"| {task.visual_slug} × {task.messaging_slug} [{task.awareness_bucket}]",
                flush=True,
            )

        with angle_brief_lock:
            if task.angle.angle_path not in angle_brief_cache:
                product_context = resolve_product_context(client_dir, task.angle)
                sub_avatar_profile = (task.angle.angle_path.parent / "profile.md").read_text()
                angle_brief_cache[task.angle.angle_path] = generate_angle_brief(
                    angle_brief_template,
                    task.angle,
                    sub_avatar_profile,
                    product_context,
                )
            angle_brief = angle_brief_cache[task.angle.angle_path]

        copy_data, copy_review, copy_attempts = generate_reviewable_ad_copy(
            ad_assembly_template,
            task,
            angle_brief,
                messaging_library[task.messaging_slug],
                visual_library[task.visual_slug],
                brand_voice,
                brand_visual_identity,
                brand_no_gos,
                review_config,
                offer_context,
                asset_mode,
        )
        copy_path = write_copy_file(task, copy_data)
        reference_images = find_reference_images(client_dir, task.visual_slug)

        # Non-blocking creative quality review
        creative_quality: dict[str, object] = {}
        if copy_review["status"] == "passed":
            sub_avatar_text = (task.angle.angle_path.parent / "profile.md").read_text()
            creative_quality = creative_quality_review(
                copy_data,
                sub_avatar_text,
                messaging_library[task.messaging_slug],
                task.awareness_bucket,
            )
            score = creative_quality.get("overall_score", 0)
            hook = creative_quality.get("hook_strength", "?")
            with print_lock:
                print(f"  [{index}] Creative quality: {score}/5, hook: {hook}", flush=True)

        entry: dict[str, object] = {
            "sequence": task.sequence,
            "ad_set_key": task.ad_set_key,
            "core_avatar": task.angle.core_avatar,
            "sub_avatar": task.angle.sub_avatar,
            "angle_name": task.angle.angle_name,
            "angle_slug": task.angle.angle_slug,
            "awareness_bucket": task.awareness_bucket,
            "visual_format": task.visual_slug,
            "messaging_concept": task.messaging_slug,
            "copy_file": copy_path.name,
            "headline": copy_data["headline"],
            "primary_text": copy_data["primary_text"],
            "image_files": {},
            "reference_images": [
                str(path.relative_to(PROJECT_ROOT)) for path in reference_images if path.exists()
            ],
            "copy_review": copy_review,
            "copy_review_attempts": copy_attempts,
            "creative_quality": creative_quality,
            "review_results": {},
            "review_status": "pending_review",
            "angle_brief_file": None,
            "_batch_dir": str(task.batch_dir),
        }

        if copy_review["status"] != "passed":
            entry["review_status"] = "needs_human_review"
            with print_lock:
                print(f"  [{index}] Copy blocked by hard rules: {copy_review.get('summary', '')}", flush=True)
            return entry

        if args.dry_run:
            entry["review_status"] = "pending_review"
            with print_lock:
                print(f"  [{index}] Saved copy only: {copy_path.relative_to(PROJECT_ROOT)}", flush=True)
        else:
            review_results: dict[str, dict[str, object]] = {}
            for aspect_ratio, suffix in [("9:16", "9x16"), ("1:1", "1x1")]:
                image_path = task.batch_dir / f"{task.stem}_{suffix}.png"
                failures_for_retry: list[dict[str, str]] = []
                final_review: dict[str, object] | None = None
                final_prompt = ""
                attempt_used = 0

                failed_dir = task.batch_dir / "failed"

                for review_attempt in range(1, IMAGE_REVIEW_ATTEMPTS + 1):
                    final_prompt = build_render_prompt(
                        copy_data["image_prompt"],
                        review_config,
                        task.visual_slug,
                        offer_context,
                        failures_for_retry,
                    )
                    image_bytes = image_request(final_prompt, aspect_ratio, reference_images)
                    if not image_bytes:
                        raise RuntimeError(f"Image generation failed for {task.stem} ({aspect_ratio})")

                    attempt_path = failed_dir / f"{task.stem}_{suffix}_attempt{review_attempt}.png"
                    failed_dir.mkdir(parents=True, exist_ok=True)
                    attempt_path.write_bytes(image_bytes)

                    final_review = review_rendered_image(
                        review_config,
                        task.visual_slug,
                        aspect_ratio,
                        copy_data,
                        final_prompt,
                        attempt_path,
                        reference_images,
                        offer_context,
                    )
                    attempt_used = review_attempt

                    write_image_metadata(
                        task,
                        suffix,
                        attempt_path,
                        copy_data,
                        reference_images,
                        final_prompt,
                        final_review,
                        review_attempt,
                    )

                    if final_review["status"] == "passed":
                        shutil.copy2(attempt_path, image_path)
                        attempt_path.unlink()
                        attempt_path.with_suffix(".json").unlink(missing_ok=True)
                        break
                    if final_review["status"] != "failed_regenerate":
                        shutil.copy2(attempt_path, image_path)
                        break
                    failures_for_retry = [
                        failure
                        for failure in final_review.get("hard_rule_failures", [])
                        if isinstance(failure, dict)
                    ]
                    with print_lock:
                        print(
                            f"  [{index}] {suffix} failed hard-rule review on attempt {review_attempt}; "
                            "regenerating with corrections.",
                            flush=True,
                        )
                    if review_attempt < IMAGE_REVIEW_ATTEMPTS:
                        time.sleep(DELAY_BETWEEN_IMAGES)

                assert final_review is not None
                if final_review["status"] == "failed_regenerate":
                    last_attempt = failed_dir / f"{task.stem}_{suffix}_attempt{attempt_used}.png"
                    if last_attempt.exists():
                        shutil.copy2(last_attempt, image_path)
                    final_review = force_human_review(final_review, IMAGE_REVIEW_ATTEMPTS)

                review_results[suffix] = final_review
                cast_image_files = entry["image_files"]
                assert isinstance(cast_image_files, dict)
                cast_image_files[suffix] = image_path.name
                with print_lock:
                    print(
                        f"  [{index}] Saved {suffix}: {image_path.relative_to(PROJECT_ROOT)} "
                        f"[{final_review.get('status')}]",
                        flush=True,
                    )

                if final_review["status"] != "passed":
                    break

            entry["review_results"] = review_results
            entry["review_status"] = derive_creative_review_status(review_results)

        return entry

    workers = max(1, args.workers)
    if workers > 1:
        print(f"Running with {workers} parallel workers\n", flush=True)

    def handle_completed_ad(index: int, task: AdTask, entry: dict[str, object]) -> None:
        with manifest_lock:
            manifests[task.batch_dir].append(entry)
        set_tracker.add_result(task.ad_set_key, entry)

    if workers == 1:
        for index, task in enumerate(queue, 1):
            try:
                entry = process_ad(index, task)
            except Exception as exc:
                with print_lock:
                    print(f"  [{index}] FAILED: {exc}", flush=True, file=sys.stderr)
                with failed_lock:
                    failed_ads.append((index, task.ad_set_key, str(exc)))
                continue
            handle_completed_ad(index, task, entry)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(process_ad, index, task): (index, task)
                for index, task in enumerate(queue, 1)
            }
            for future in as_completed(futures):
                index, task = futures[future]
                try:
                    entry = future.result()
                except Exception as exc:
                    with print_lock:
                        print(f"  [{index}] FAILED: {exc}", flush=True, file=sys.stderr)
                    with failed_lock:
                        failed_ads.append((index, task.ad_set_key, str(exc)))
                    continue
                handle_completed_ad(index, task, entry)

    # --- Write manifests (merge, don't overwrite) ---
    for batch_dir, entries in manifests.items():
        manifest_path = batch_dir / "manifest.json"
        existing: list[dict] = []
        if manifest_path.exists():
            try:
                existing = json.loads(manifest_path.read_text())
            except (json.JSONDecodeError, ValueError):
                pass
        existing_stems = {e.get("copy_file") for e in existing}
        merged = existing + [e for e in entries if e.get("copy_file") not in existing_stems]
        # Strip internal _batch_dir field before writing
        for e in merged:
            e.pop("_batch_dir", None)
        json_dump(merged, manifest_path)
        print(f"Manifest: {manifest_path.relative_to(PROJECT_ROOT)} ({len(merged)} entries)")

    # --- Summary ---
    completed = sum(len(v) for v in manifests.values())
    print(f"\nCompleted: {completed}/{len(queue)} ads")
    print(f"Sets uploaded: {len(set_tracker.completed_keys)}")
    if failed_ads:
        print(f"Failed: {len(failed_ads)} ads")
        for idx, key, err in failed_ads:
            print(f"  [{idx}] {key}: {err}")

    if args.upload_r2:
        from r2 import upload_batch
        for batch_dir in manifests:
            count = upload_batch(batch_dir)
            print(f"Uploaded {count} files to R2")


if __name__ == "__main__":
    main()
