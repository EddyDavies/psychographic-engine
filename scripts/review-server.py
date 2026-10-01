#!/usr/bin/env python3
"""
Interactive ad review server with live SSE updates and inline regeneration.

Usage:
  uv run --with fastapi --with uvicorn --with httpx --with google-api-python-client --with google-auth-oauthlib --with google-auth-httplib2 python scripts/review-server.py <statics-folder> --client {client-name} [--port 8787]

The server watches batch folder(s) for new/changed files and pushes updates
to the browser via Server-Sent Events. Rejection triggers inline regeneration.
When a full ad set (3 ads) is approved, it packages into statics_ad_sets/,
uploads to Google Drive, and appends to the local CSV.
"""

import argparse
import asyncio
import base64
import json
import re
import sys
import time
import webbrowser
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from ad_set_builder import (
    ensure_image_pair,
    organize_sets,
    upload_csv_to_drive,
    upload_sets_to_drive,
)
from utils import (
    PROJECT_ROOT,
    SUPPORTED_EXTENSIONS,
    encode_image,
    extract_image_bytes,
    json_dump,
    openrouter_headers,
)

TEXT_MODEL = "anthropic/claude-sonnet-4-6"
IMAGE_MODEL = "google/gemini-3.1-flash-image-preview"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
TEXT_RETRIES = 3
IMAGE_RETRIES = 3
RETRY_DELAY = 5
ADS_PER_SET = 3

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

review_state: dict[str, dict] = {}  # ad_name -> {status, category, notes}
manifest_index: dict[str, tuple[Path, dict]] = {}  # ad_name -> (batch_dir, entry)
set_index: dict[str, list[str]] = {}  # ad_set_key -> [ad_name, ...]
statics_dir: Path
client_dir: Path
event_queues: list[asyncio.Queue] = []
executor = ThreadPoolExecutor(max_workers=4)
_background_tasks: set[asyncio.Task] = set()  # prevent GC of background tasks

# Cached file state for change detection
_file_state: dict[str, float] = {}  # filepath -> mtime


def state_path() -> Path:
    return statics_dir / "review-state.json"


def load_state() -> None:
    global review_state
    p = state_path()
    if p.exists():
        review_state = json.loads(p.read_text())
    # Reset any stuck "regenerating" states from a previous crashed session
    dirty = False
    for ad_name, state in review_state.items():
        if state.get("status") == "regenerating":
            state["status"] = "pending"
            state["category"] = ""
            state["notes"] = ""
            dirty = True
    if dirty:
        save_state()


def save_state() -> None:
    json_dump(review_state, state_path())


# ---------------------------------------------------------------------------
# Manifest / file scanning
# ---------------------------------------------------------------------------


def scan_manifests() -> None:
    """Build the manifest and set indexes from all batch dirs."""
    manifest_index.clear()
    set_index.clear()
    batch_dirs = sorted(
        p
        for p in statics_dir.iterdir()
        if p.is_dir() and p.name.startswith("test-") and (p / "manifest.json").exists()
    )
    for batch_dir in batch_dirs:
        manifest = json.loads((batch_dir / "manifest.json").read_text())
        for entry in manifest:
            copy_file = entry.get("copy_file", "")
            stem = Path(copy_file).stem.removesuffix("-copy")
            manifest_index[stem] = (batch_dir, entry)
            set_key = entry.get("ad_set_key", "")
            if set_key:
                set_index.setdefault(set_key, []).append(stem)


def parse_copy_file(path: Path) -> dict[str, str]:
    text = path.read_text()
    result: dict[str, str] = {}
    for heading in ("Image Prompt", "Primary Text", "Headline"):
        m = re.search(
            rf"## {re.escape(heading)}\s*\n+(.+?)(?=\n## |\Z)", text, re.DOTALL
        )
        key = heading.lower().replace(" ", "_")
        result[key] = m.group(1).strip() if m else ""

    # Extract the on-image copy from [COPY...] or [COPY_OVERLAY] blocks inside Image Prompt
    image_prompt = result.get("image_prompt", "")
    copy_match = re.search(
        r"\[COPY[^\]]*\]\s*\n(.+?)(?=\n\[|\Z)", image_prompt, re.DOTALL
    )
    result["on_image_copy"] = copy_match.group(1).strip() if copy_match else ""

    return result


def build_ad_data(ad_name: str) -> dict:
    """Build a single ad's data dict for the API response."""
    batch_dir, entry = manifest_index.get(ad_name, (None, None))
    if not entry:
        return {"ad_name": ad_name, "status": "unknown"}

    copy_file = batch_dir / entry["copy_file"]
    copy_sections = parse_copy_file(copy_file) if copy_file.exists() else {}

    img_9x16 = batch_dir / f"{ad_name}_9x16.png"
    img_1x1 = batch_dir / f"{ad_name}_1x1.png"

    state = review_state.get(ad_name, {})

    return {
        "ad_name": ad_name,
        "batch_dir": batch_dir.name,
        "set_key": entry.get("ad_set_key", ""),
        "sub_avatar": entry.get("sub_avatar", ""),
        "angle_name": entry.get("angle_name", ""),
        "visual_format": entry.get("visual_format", ""),
        "messaging_concept": entry.get("messaging_concept", ""),
        "headline": copy_sections.get("headline", entry.get("headline", "")),
        "primary_text": copy_sections.get(
            "primary_text", entry.get("primary_text", "")
        ),
        "image_prompt": copy_sections.get("image_prompt", ""),
        "on_image_copy": copy_sections.get("on_image_copy", ""),
        "has_9x16": img_9x16.exists(),
        "has_1x1": img_1x1.exists(),
        "review_status": state.get("status", "pending"),
        "review_category": state.get("category", ""),
        "review_notes": state.get("notes", ""),
        "copy_review": entry.get("copy_review", {}),
        "auto_review_status": entry.get("review_status", ""),
    }


def scan_for_changes() -> list[dict]:
    """Detect new or modified files, return SSE event payloads."""
    events = []
    batch_dirs = sorted(
        p
        for p in statics_dir.iterdir()
        if p.is_dir() and p.name.startswith("test-")
    )

    needs_rescan = False
    for batch_dir in batch_dirs:
        manifest_path = batch_dir / "manifest.json"
        if manifest_path.exists():
            key = str(manifest_path)
            mtime = manifest_path.stat().st_mtime
            if key not in _file_state or _file_state[key] != mtime:
                _file_state[key] = mtime
                needs_rescan = True

    if needs_rescan:
        scan_manifests()
        events.append({"type": "manifest_reload", "ad_count": len(manifest_index)})

    for ad_name, (batch_dir, entry) in manifest_index.items():
        copy_file = batch_dir / entry["copy_file"]
        if copy_file.exists():
            key = str(copy_file)
            mtime = copy_file.stat().st_mtime
            if key not in _file_state or _file_state[key] != mtime:
                _file_state[key] = mtime
                sections = parse_copy_file(copy_file)
                events.append(
                    {
                        "type": "ad:copy",
                        "ad_name": ad_name,
                        "headline": sections.get("headline", ""),
                        "primary_text": sections.get("primary_text", ""),
                        "image_prompt": sections.get("image_prompt", ""),
                        "on_image_copy": sections.get("on_image_copy", ""),
                    }
                )

        for suffix in ("9x16", "1x1"):
            img_path = batch_dir / f"{ad_name}_{suffix}.png"
            if img_path.exists():
                key = str(img_path)
                mtime = img_path.stat().st_mtime
                if key not in _file_state or _file_state[key] != mtime:
                    _file_state[key] = mtime
                    events.append(
                        {
                            "type": "ad:image",
                            "ad_name": ad_name,
                            "ratio": suffix,
                        }
                    )

    return events


# ---------------------------------------------------------------------------
# Regeneration
# ---------------------------------------------------------------------------


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


def image_request(
    prompt: str, aspect_ratio: str, reference_images: list[Path]
) -> bytes | None:
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
        "image_config": {"aspect_ratio": aspect_ratio, "image_size": "1K"},
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


def resolve_reference_images(entry: dict) -> list[Path]:
    """Get reference images from the manifest entry, resolving relative paths."""
    return [
        PROJECT_ROOT / ref
        for ref in entry.get("reference_images", [])
    ]


def regenerate_image(
    ad_name: str, ratio: str, notes: str, entry: dict, batch_dir: Path
) -> bool:
    """Regenerate a single image for an ad."""
    copy_file = batch_dir / entry["copy_file"]
    if not copy_file.exists():
        return False

    sections = parse_copy_file(copy_file)
    base_prompt = sections.get("image_prompt", "")
    if not base_prompt:
        return False

    prompt = base_prompt
    if notes:
        prompt += (
            f"\n\n### CRITICAL REVISION INSTRUCTION\n"
            f"The previous render was rejected. You MUST fix the following:\n"
            f"- {notes}\n"
            f"This is non-negotiable. The output MUST address the above feedback."
        )

    aspect_ratio = ratio.replace("x", ":")
    ref_images = resolve_reference_images(entry)
    image_bytes = image_request(prompt, aspect_ratio, ref_images)
    if not image_bytes:
        return False

    image_path = batch_dir / f"{ad_name}_{ratio}.png"
    image_path.write_bytes(image_bytes)
    print(f"  Regenerated: {image_path.relative_to(PROJECT_ROOT)}", flush=True)
    return True


def regenerate_copy(ad_name: str, notes: str, entry: dict, batch_dir: Path) -> bool:
    """Regenerate copy for an ad using the same angle/messaging/visual combo."""
    copy_file = batch_dir / entry["copy_file"]
    if not copy_file.exists():
        return False

    existing_sections = parse_copy_file(copy_file)

    prompt = (
        f"Rewrite this ad copy. Keep the same angle, messaging concept, and visual format.\n\n"
        f"**Current Image Prompt:**\n{existing_sections.get('image_prompt', '')}\n\n"
        f"**Current Primary Text:**\n{existing_sections.get('primary_text', '')}\n\n"
        f"**Current Headline:**\n{existing_sections.get('headline', '')}\n\n"
    )
    if notes:
        prompt += f"**Reviewer Feedback (MUST address):**\n{notes}\n\n"
    prompt += (
        "Return exactly this markdown shape:\n"
        f"# {ad_name}\n\n"
        "## Image Prompt\n\n[full image prompt]\n\n"
        "## Primary Text\n\n[primary text]\n\n"
        "## Headline\n\n[headline, max 40 chars]\n"
    )

    raw = llm_call([{"role": "user", "content": prompt}], temperature=0.6)

    # Parse the response
    img_match = re.search(
        r"## Image Prompt\s*\n+(.+?)(?=\n## Primary Text)", raw, re.DOTALL
    )
    pri_match = re.search(
        r"## Primary Text\s*\n+(.+?)(?=\n## Headline)", raw, re.DOTALL
    )
    hdl_match = re.search(r"## Headline\s*\n+(.+?)\s*$", raw, re.DOTALL)

    if not all([img_match, pri_match, hdl_match]):
        return False

    headline = hdl_match.group(1).strip()
    if len(headline) > 40:
        headline = headline[:40].rsplit(" ", 1)[0].rstrip() or headline[:40].strip()

    new_copy = (
        f"# {ad_name}\n\n"
        f"## Image Prompt\n\n{img_match.group(1).strip()}\n\n"
        f"## Primary Text\n\n{pri_match.group(1).strip()}\n\n"
        f"## Headline\n\n{headline}\n"
    )
    copy_file.write_text(new_copy)
    print(f"  Regenerated copy: {copy_file.relative_to(PROJECT_ROOT)}", flush=True)
    return True


# ---------------------------------------------------------------------------
# Drive upload
# ---------------------------------------------------------------------------

def _next_set_number(output_dir: Path) -> int:
    """Count existing set_XX dirs and return the next number."""
    if not output_dir.is_dir():
        return 1
    existing = [
        p for p in output_dir.iterdir()
        if p.is_dir() and p.name.startswith("set_")
    ]
    return len(existing) + 1


def _append_csv_row(output_dir: Path, record: dict, drive_link: str) -> None:
    """Append a single row to upload_spreadsheet.csv, creating it if needed."""
    import csv

    csv_path = output_dir / "upload_spreadsheet.csv"
    fieldnames = [
        "Date", "Month", "Persona", "Ad Amount", "Creative Strategist",
        "What Are You Testing", "Ad focus", "File type",
        "Ad copy 1", "Ad copy 2", "Headline 1", "Headline 2",
        "CTA", "Content Link", "Review Status",
    ]
    today = datetime.now()
    variants = record["variants"]
    variant_a = variants[0] if len(variants) > 0 else {}
    variant_b = variants[1] if len(variants) > 1 else {}

    row = {
        "Date": today.strftime("%d/%m/%y"),
        "Month": today.strftime("%b %y"),
        "Persona": record["persona"],
        "Ad Amount": len(record["source_images"]),
        "Creative Strategist": "Ryane",
        "What Are You Testing": record["set_theme"],
        "Ad focus": "RSSP",
        "File type": "static",
        "Ad copy 1": variant_a.get("primary_text", ""),
        "Ad copy 2": variant_b.get("primary_text", ""),
        "Headline 1": variant_a.get("headline", ""),
        "Headline 2": variant_b.get("headline", ""),
        "CTA": "Learn More",
        "Content Link": drive_link,
        "Review Status": record["review_status"],
    }

    write_header = not csv_path.exists()
    with csv_path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def upload_approved_set(set_key: str, ad_names: list[str]) -> str | None:
    """Package an approved set into ad_sets_YYYY-MM-DD/, upload to Drive, append CSV."""
    date_suffix = datetime.now().strftime("%Y-%m-%d")
    output_dir = statics_dir.parent / f"ad_sets_{date_suffix}"
    set_number = _next_set_number(output_dir)

    # Build the group dict that ad_set_builder expects
    sorted_names = sorted(ad_names)
    first_batch_dir, first_entry = manifest_index[sorted_names[0]]

    entries = []
    for ad_name in sorted_names:
        batch_dir, entry = manifest_index[ad_name]
        try:
            entry["image_files"] = ensure_image_pair(batch_dir, entry)
        except Exception as exc:
            print(f"  Image pair failed for {ad_name}: {exc}", flush=True)
            return None
        entries.append(entry)

    group = {
        "set_number": set_number,
        "batch_dir": first_batch_dir,
        "ad_set_key": set_key,
        "entries": entries,
        "persona": first_entry.get("sub_avatar", "").removeprefix("sub-"),
        "set_theme": first_entry.get("angle_name", ""),
        "review_status": "passed",
    }

    # Package into set_XX folder
    try:
        records = organize_sets([group], output_dir)
    except Exception as exc:
        print(f"  organize_sets failed: {exc}", flush=True)
        return None

    if not records:
        print("  organize_sets produced no records", flush=True)
        return None

    # Upload to Drive
    drive_links: list[str] = []
    try:
        drive_links, _parent_link = upload_sets_to_drive(output_dir, records)
    except Exception as exc:
        print(f"  Drive upload failed: {exc}", flush=True)
        return None

    link = drive_links[0] if drive_links else None

    # Append CSV row and upload to Drive
    try:
        _append_csv_row(output_dir, records[0], link or "")
        csv_path = output_dir / "upload_spreadsheet.csv"
        if csv_path.exists() and _parent_link:
            upload_csv_to_drive(csv_path, _parent_link)
    except Exception as exc:
        print(f"  CSV append/upload failed: {exc}", flush=True)

    return link


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------


async def push_event(event: dict) -> None:
    """Push an event to all connected SSE clients."""
    for q in event_queues:
        await q.put(event)


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------


def create_app() -> "FastAPI":
    from contextlib import asynccontextmanager

    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

    async def file_watcher():
        while True:
            await asyncio.sleep(1)
            loop = asyncio.get_event_loop()
            events = await loop.run_in_executor(None, scan_for_changes)
            for event in events:
                await push_event(event)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        scan_manifests()
        load_state()
        scan_for_changes()
        task = asyncio.create_task(file_watcher())
        yield
        task.cancel()

    app = FastAPI(title="Ad Review Server", lifespan=lifespan)

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return REVIEW_HTML

    @app.get("/api/ads")
    async def get_ads():
        ads = [build_ad_data(name) for name in sorted(manifest_index)]
        sets: dict[str, list[dict]] = {}
        for ad in ads:
            key = ad["set_key"]
            sets.setdefault(key, []).append(ad)
        return {"ads": ads, "sets": sets, "review_state": review_state}

    @app.get("/api/image/{batch_name}/{filename}")
    async def get_image(batch_name: str, filename: str):
        # Sanitize to prevent path traversal
        if ".." in batch_name or ".." in filename:
            return JSONResponse({"error": "invalid path"}, status_code=400)
        if not filename.endswith(".png"):
            return JSONResponse({"error": "only png supported"}, status_code=400)

        image_path = statics_dir / batch_name / filename
        if not image_path.exists():
            return JSONResponse({"error": "not found"}, status_code=404)
        # Verify the resolved path is under statics_dir
        try:
            image_path.resolve().relative_to(statics_dir.resolve())
        except ValueError:
            return JSONResponse({"error": "invalid path"}, status_code=400)

        from fastapi.responses import Response

        return Response(
            content=image_path.read_bytes(),
            media_type="image/png",
            headers={"Cache-Control": "no-cache"},
        )

    @app.get("/api/events")
    async def sse(request: Request):
        queue: asyncio.Queue = asyncio.Queue()
        event_queues.append(queue)

        async def stream():
            try:
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=15)
                        yield f"data: {json.dumps(event)}\n\n"
                    except asyncio.TimeoutError:
                        yield ": keepalive\n\n"
            finally:
                event_queues.remove(queue)

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.post("/api/approve/{ad_name}")
    async def approve_ad(ad_name: str):
        if ad_name not in manifest_index:
            return JSONResponse({"error": "unknown ad"}, status_code=404)

        review_state[ad_name] = {"status": "approved"}
        save_state()

        _, entry = manifest_index[ad_name]
        set_key = entry.get("ad_set_key", "")
        await push_event({"type": "ad:approved", "ad_name": ad_name})

        # Check if full set is now approved
        set_ads = set_index.get(set_key, [])
        all_approved = all(
            review_state.get(n, {}).get("status") == "approved" for n in set_ads
        )
        if all_approved and len(set_ads) >= ADS_PER_SET:
            await push_event(
                {"type": "set:uploading", "set_key": set_key}
            )
            loop = asyncio.get_event_loop()
            link = await loop.run_in_executor(
                executor, upload_approved_set, set_key, set_ads
            )
            if link:
                await push_event(
                    {"type": "set:uploaded", "set_key": set_key, "drive_link": link}
                )
            else:
                await push_event(
                    {"type": "set:upload_failed", "set_key": set_key}
                )

        return {"status": "approved", "set_complete": all_approved}

    @app.post("/api/reject")
    async def reject_ad(request: Request):
        body = await request.json()
        ad_name = body.get("ad_name", "")
        category = body.get("category", "concept")
        notes = body.get("notes", "")
        ratio = body.get("ratio", "9x16")

        if ad_name not in manifest_index:
            return JSONResponse({"error": "unknown ad"}, status_code=404)

        batch_dir, entry = manifest_index[ad_name]

        # concept = full reject, no regeneration
        if category == "concept":
            review_state[ad_name] = {
                "status": "rejected",
                "category": category,
                "notes": notes,
            }
            save_state()
            await push_event(
                {
                    "type": "ad:rejected",
                    "ad_name": ad_name,
                    "category": category,
                }
            )
            return {"status": "rejected", "regenerated": False}

        # Mark as regenerating
        review_state[ad_name] = {
            "status": "regenerating",
            "category": category,
            "notes": notes,
        }
        save_state()
        await push_event(
            {
                "type": "ad:regenerating",
                "ad_name": ad_name,
                "category": category,
                "ratio": ratio,
            }
        )

        # Run regeneration in background — return immediately
        # Store reference to prevent garbage collection (Python asyncio footgun)
        print(f"  Queued regeneration: {ad_name} ({category})", flush=True)
        task = asyncio.create_task(
            _regenerate_background(ad_name, category, notes, ratio, entry, batch_dir)
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

        return {"status": "queued"}

    async def _regenerate_background(
        ad_name: str,
        category: str,
        notes: str,
        ratio: str,
        entry: dict,
        batch_dir: Path,
    ) -> None:
        """Background coroutine that does the actual LLM/Gemini regeneration."""
        print(f"  Starting regeneration: {ad_name} ({category})", flush=True)
        loop = asyncio.get_event_loop()
        try:
            if category == "copy":
                print(f"  [{ad_name}] Regenerating copy...", flush=True)
                await push_event({"type": "ad:regen_step", "ad_name": ad_name, "step": "Regenerating copy..."})
                ok = await loop.run_in_executor(
                    executor, regenerate_copy, ad_name, notes, entry, batch_dir
                )
                if not ok:
                    raise RuntimeError("Copy regeneration failed")

                copy_file = batch_dir / entry["copy_file"]
                sections = parse_copy_file(copy_file)
                await push_event(
                    {
                        "type": "ad:copy",
                        "ad_name": ad_name,
                        "headline": sections.get("headline", ""),
                        "primary_text": sections.get("primary_text", ""),
                        "image_prompt": sections.get("image_prompt", ""),
                        "on_image_copy": sections.get("on_image_copy", ""),
                    }
                )

                for r in ("9x16", "1x1"):
                    print(f"  [{ad_name}] Rendering {r}...", flush=True)
                    await push_event({"type": "ad:regen_step", "ad_name": ad_name, "step": f"Rendering {r.replace('x', ':')}..."})
                    img_ok = await loop.run_in_executor(
                        executor, regenerate_image, ad_name, r, "", entry, batch_dir
                    )
                    if img_ok:
                        await push_event(
                            {"type": "ad:image", "ad_name": ad_name, "ratio": r}
                        )

            elif category in ("image-product", "image-execution"):
                ratios = [ratio] if ratio != "both" else ["9x16", "1x1"]
                for r in ratios:
                    print(f"  [{ad_name}] Rendering {r}...", flush=True)
                    await push_event({"type": "ad:regen_step", "ad_name": ad_name, "step": f"Rendering {r.replace('x', ':')}..."})
                    img_ok = await loop.run_in_executor(
                        executor, regenerate_image, ad_name, r, notes, entry, batch_dir
                    )
                    if img_ok:
                        await push_event(
                            {"type": "ad:image", "ad_name": ad_name, "ratio": r}
                        )

            review_state[ad_name] = {"status": "pending", "category": "", "notes": ""}
            save_state()
            await push_event(
                {
                    "type": "ad:regenerated",
                    "ad_name": ad_name,
                    "category": category,
                }
            )
            print(f"  [{ad_name}] Regeneration complete", flush=True)

        except Exception as exc:
            print(f"  [{ad_name}] Regeneration FAILED: {exc}", flush=True)
            review_state[ad_name] = {"status": "pending", "category": "", "notes": ""}
            save_state()
            await push_event(
                {
                    "type": "ad:regen_failed",
                    "ad_name": ad_name,
                    "error": str(exc),
                }
            )

    @app.get("/api/progress")
    async def progress():
        total = len(manifest_index)
        approved = sum(
            1
            for s in review_state.values()
            if s.get("status") == "approved"
        )
        rejected = sum(
            1
            for s in review_state.values()
            if s.get("status") == "rejected"
        )
        regenerating = sum(
            1
            for s in review_state.values()
            if s.get("status") == "regenerating"
        )
        pending = total - approved - rejected - regenerating
        return {
            "total": total,
            "approved": approved,
            "rejected": rejected,
            "regenerating": regenerating,
            "pending": pending,
        }

    return app


# ---------------------------------------------------------------------------
# Embedded HTML
# ---------------------------------------------------------------------------

REVIEW_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ad Review</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #0a0a0a;
    color: #e0e0e0;
    padding: 2rem;
}
.top-bar {
    position: sticky;
    top: 0;
    z-index: 100;
    background: #0a0a0a;
    border-bottom: 1px solid #2a2a2a;
    padding: 1rem 0;
    margin-bottom: 2rem;
}
.top-bar-inner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
}
.top-bar h1 { font-size: 1.5rem; color: #fff; }
.connection-status {
    font-size: 0.75rem;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    font-weight: 600;
}
.connection-status.connected { background: #14301f; color: #7ce5a4; }
.connection-status.disconnected { background: #301414; color: #e57c7c; }
.summary-counts {
    display: flex;
    gap: 0.75rem;
    align-items: center;
    font-size: 0.85rem;
}
.summary-counts .count {
    padding: 0.3rem 0.7rem;
    border-radius: 6px;
    font-weight: 600;
}
.count-total { background: #2a2a2a; color: #c9c9c9; }
.count-approved { background: #14301f; color: #7ce5a4; }
.count-rejected { background: #301414; color: #e57c7c; }
.count-pending { background: #1a1a2e; color: #9999cc; }
.count-regenerating { background: #382515; color: #ffbe74; }
.count-deployed { background: #1a2a1a; color: #6b9; }
.deployed-toggle {
    font-size: 0.8rem;
    color: #666;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}
.deployed-toggle input { cursor: pointer; }

/* Set groups */
.set-group {
    margin-bottom: 3rem;
}
.set-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    background: #161616;
    border: 1px solid #2a2a2a;
    border-radius: 10px 10px 0 0;
    margin-bottom: 0;
}
.set-header h2 {
    font-size: 1.1rem;
    color: #fff;
}
.set-header .set-meta {
    font-size: 0.8rem;
    color: #888;
}
.set-status-badge {
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.3rem 0.7rem;
    border-radius: 999px;
}
.set-status-badge.uploading { background: #382515; color: #ffbe74; }
.set-status-badge.uploaded { background: #14301f; color: #7ce5a4; }
.drive-link {
    color: #7ce5a4;
    text-decoration: none;
    font-size: 0.8rem;
    font-weight: 600;
}
.drive-link:hover { text-decoration: underline; }

/* Cards */
.card {
    background: #161616;
    border: 1px solid #2a2a2a;
    border-top: none;
    overflow: hidden;
}
.card:last-child {
    border-radius: 0 0 10px 10px;
}
.card.status-approved { border-left: 3px solid #7ce5a4; }
.card.status-rejected { border-left: 3px solid #e57c7c; opacity: 0.5; }
.card.status-regenerating { border-left: 3px solid #ffbe74; }
.card-header {
    padding: 1rem 1.5rem;
    border-bottom: 1px solid #222;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
}
.title-block { min-width: 0; }
.card-header h3 { font-size: 1rem; color: #fff; margin-bottom: 0.15rem; }
.card-number { color: #2563eb; font-weight: 700; margin-right: 0.3rem; }
.card-meta { font-size: 0.75rem; color: #666; font-family: monospace; }
.auto-review-badge {
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 0.25rem 0.6rem;
    white-space: nowrap;
}
.auto-review-badge.passed { background: #14301f; color: #7ce5a4; }
.auto-review-badge.needs_human_review { background: #382515; color: #ffbe74; }
.auto-review-badge.pending_review { background: #2a2a2a; color: #c9c9c9; }

/* Card body: on-image copy above images, meta copy toggleable below */
.card-body { padding: 1rem 1.5rem; }

/* On-image copy — the text baked into the creative */
.on-image-copy {
    background: #111;
    border: 1px solid #2a4a2a;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
    white-space: pre-wrap;
    font-size: 0.85rem;
    line-height: 1.6;
    color: #e0e0e0;
}
.on-image-copy h4 {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #7ce5a4;
    margin-bottom: 0.5rem;
}

/* Meta copy toggle */
.meta-copy-toggle {
    background: none;
    border: 1px solid #333;
    border-radius: 6px;
    color: #888;
    font-size: 0.75rem;
    padding: 0.25rem 0.6rem;
    cursor: pointer;
    margin-bottom: 0.5rem;
}
.meta-copy-toggle:hover { color: #ccc; border-color: #555; }
.meta-copy-section {
    display: none;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-bottom: 1rem;
}
.meta-copy-section.visible { display: grid; }
.copy-block { background: #111; border: 1px solid #242424; border-radius: 8px; padding: 0.75rem 1rem; }
.copy-block h4 {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #888;
    margin-bottom: 0.4rem;
}
.copy-block .headline-text { font-size: 1rem; font-weight: 600; color: #fff; }
.copy-block .primary-text { font-size: 0.85rem; line-height: 1.6; white-space: pre-wrap; }

/* Image prompt — collapsible */
.image-prompt-toggle {
    background: none;
    border: 1px solid #333;
    border-radius: 6px;
    color: #888;
    font-size: 0.75rem;
    padding: 0.25rem 0.6rem;
    cursor: pointer;
    margin-bottom: 0.5rem;
    margin-left: 0.5rem;
}
.image-prompt-toggle:hover { color: #ccc; border-color: #555; }
.image-prompt-block {
    display: none;
    background: #111;
    border: 1px solid #242424;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
    max-height: 150px;
    overflow-y: auto;
}
.image-prompt-block.visible { display: block; }
.image-prompt-block h4 {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #888;
    margin-bottom: 0.4rem;
}
.image-prompt-block .image-prompt-text { font-size: 0.8rem; color: #999; line-height: 1.5; white-space: pre-wrap; }

/* Images row */
.images-row {
    display: flex;
    gap: 1.5rem;
    justify-content: center;
    align-items: flex-start;
    flex-wrap: wrap;
    background: #111;
    border-radius: 8px;
    padding: 1rem;
}
.img-col {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
}
.img-wrapper { position: relative; }
.img-wrapper img {
    max-height: 420px;
    width: auto;
    border-radius: 6px;
    display: block;
}
.ratio-label {
    position: absolute;
    top: 6px; left: 6px;
    background: rgba(0,0,0,0.7);
    color: #fff;
    font-size: 0.75rem;
    padding: 2px 8px;
    border-radius: 4px;
    font-family: monospace;
    font-weight: 600;
}
.img-placeholder {
    width: 180px;
    height: 280px;
    border: 1px dashed #333;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #555;
    font-size: 0.8rem;
}
.img-spinner {
    width: 180px;
    height: 280px;
    border: 1px solid #382515;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #ffbe74;
    font-size: 0.8rem;
    background: #1a1508;
}
.regen-status {
    text-align: center;
    color: #ffbe74;
    font-size: 0.8rem;
    font-weight: 600;
    padding: 0.4rem 0;
    margin-bottom: 0.5rem;
}

/* Action buttons */
.card-actions {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    padding-top: 0.75rem;
    flex-wrap: wrap;
}
.btn {
    border: 1px solid #333;
    border-radius: 6px;
    padding: 0.4rem 0.9rem;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    background: #1a1a1a;
    color: #999;
    transition: all 0.15s;
}
.btn:hover { border-color: #555; color: #ddd; }
.btn-approve:hover, .btn-approve.active { background: #14301f; color: #7ce5a4; border-color: #7ce5a4; }
.btn-reject-copy:hover { background: #382515; color: #ffbe74; border-color: #ffbe74; }
.btn-reject-image:hover { background: #382515; color: #ffbe74; border-color: #ffbe74; }
.btn-reject-concept:hover, .btn-reject-concept.active { background: #301414; color: #e57c7c; border-color: #e57c7c; }
.btn-disabled { opacity: 0.4; pointer-events: none; }

/* Rejection panel */
.reject-panel {
    display: none;
    margin-top: 0.5rem;
    padding: 0.75rem;
    background: #111;
    border: 1px solid #333;
    border-radius: 8px;
}
.reject-panel.visible { display: block; }
.reject-panel label {
    font-size: 0.8rem;
    color: #ccc;
    display: block;
    margin-bottom: 0.3rem;
}
.reject-panel select {
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 4px;
    color: #e0e0e0;
    padding: 0.35rem 0.5rem;
    font-size: 0.8rem;
    margin-bottom: 0.5rem;
    width: 100%;
}
.reject-panel textarea {
    width: 100%;
    min-height: 50px;
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 4px;
    color: #e0e0e0;
    padding: 0.4rem 0.5rem;
    font-family: inherit;
    font-size: 0.8rem;
    resize: vertical;
    margin-bottom: 0.5rem;
}
.reject-panel textarea:focus, .reject-panel select:focus { outline: none; border-color: #555; }
.reject-panel .btn-send-reject {
    background: #382515;
    color: #ffbe74;
    border-color: #ffbe74;
}
.reject-panel .ratio-select { margin-bottom: 0.5rem; }
.ratio-select { display: none; }
.ratio-select.visible { display: block; }

/* Toast notifications */
.toast-container {
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    z-index: 200;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}
.toast {
    padding: 0.6rem 1rem;
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 500;
    animation: fadeIn 0.2s ease-out;
    max-width: 400px;
}
.toast.info { background: #1a1a2e; color: #9999cc; border: 1px solid #333366; }
.toast.success { background: #14301f; color: #7ce5a4; border: 1px solid #2a5a3a; }
.toast.warning { background: #382515; color: #ffbe74; border: 1px solid #5a4a2a; }
.toast.error { background: #301414; color: #e57c7c; border: 1px solid #5a2a2a; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
</style>
</head>
<body>
<div class="top-bar">
    <div class="top-bar-inner">
        <div>
            <h1>Ad Review</h1>
            <span class="connection-status disconnected" id="conn-status">Connecting...</span>
        </div>
        <label class="deployed-toggle">
          <input type="checkbox" id="show-approved" onchange="renderAll()"> Show approved
        </label>
        <label class="deployed-toggle">
          <input type="checkbox" id="show-deployed" onchange="renderAll()"> Show deployed
        </label>
        <div class="summary-counts" id="summary-counts">
            <span class="count count-total" id="c-total">-- total</span>
            <span class="count count-approved" id="c-approved">-- approved</span>
            <span class="count count-rejected" id="c-rejected">-- rejected</span>
            <span class="count count-regenerating" id="c-regenerating">-- regenerating</span>
            <span class="count count-pending" id="c-pending">-- pending</span>
            <span class="count count-deployed" id="c-deployed" style="display:none">-- deployed</span>
        </div>
    </div>
</div>
<div id="app"></div>
<div class="toast-container" id="toasts"></div>

<script>
// ---- State ----
let adsData = {};       // ad_name -> ad object
let setsData = {};      // set_key -> [ad objects]
let setDriveLinks = {}; // set_key -> drive link
let setUploading = {};  // set_key -> bool

// ---- SSE ----
function connectSSE() {
    const es = new EventSource('/api/events');
    const status = document.getElementById('conn-status');

    es.onopen = () => {
        status.textContent = 'Live';
        status.className = 'connection-status connected';
    };
    es.onerror = () => {
        status.textContent = 'Reconnecting...';
        status.className = 'connection-status disconnected';
    };
    es.onmessage = (e) => {
        const event = JSON.parse(e.data);
        handleEvent(event);
    };
}

function handleEvent(event) {
    const t = event.type;

    if (t === 'manifest_reload') {
        toast(`Manifest reloaded: ${event.ad_count} ads`, 'info');
        loadAds();
        return;
    }
    if (t === 'ad:copy') {
        const ad = adsData[event.ad_name];
        if (ad) {
            ad.headline = event.headline;
            ad.primary_text = event.primary_text;
            ad.image_prompt = event.image_prompt;
            ad.on_image_copy = event.on_image_copy;
            renderCard(event.ad_name);
        } else {
            loadAds();
        }
        return;
    }
    if (t === 'ad:image') {
        const ad = adsData[event.ad_name];
        if (ad) {
            if (event.ratio === '9x16') ad.has_9x16 = true;
            if (event.ratio === '1x1') ad.has_1x1 = true;
            renderCard(event.ad_name);
        }
        return;
    }
    if (t === 'ad:approved') {
        const ad = adsData[event.ad_name];
        if (ad) { ad.review_status = 'approved'; renderCard(event.ad_name); }
        updateCounts();
        return;
    }
    if (t === 'ad:rejected') {
        const ad = adsData[event.ad_name];
        if (ad) { ad.review_status = 'rejected'; renderCard(event.ad_name); }
        updateCounts();
        toast(`Rejected: ${event.ad_name}`, 'error');
        return;
    }
    if (t === 'ad:regenerating') {
        const ad = adsData[event.ad_name];
        if (ad) {
            ad.review_status = 'regenerating';
            // Track which ratios are being regenerated
            if (event.category === 'copy') {
                ad._regen_ratios = ['9x16', '1x1'];
            } else if (event.ratio === 'both') {
                ad._regen_ratios = ['9x16', '1x1'];
            } else {
                ad._regen_ratios = [event.ratio || '9x16'];
            }
            renderCard(event.ad_name);
        }
        updateCounts();
        toast(`Regenerating ${event.category}: ${event.ad_name}`, 'warning');
        return;
    }
    if (t === 'ad:regen_step') {
        const ad = adsData[event.ad_name];
        if (ad) {
            ad._regen_step = event.step;
            const stepEl = document.getElementById(`regen-step-${event.ad_name}`);
            if (stepEl) stepEl.textContent = event.step;
        }
        return;
    }
    if (t === 'ad:regen_failed') {
        const ad = adsData[event.ad_name];
        if (ad) { ad.review_status = 'pending'; delete ad._regen_step; delete ad._regen_ratios; renderCard(event.ad_name); }
        updateCounts();
        toast(`Regeneration failed: ${event.error}`, 'error');
        return;
    }
    if (t === 'ad:regenerated') {
        const ad = adsData[event.ad_name];
        if (ad) { ad.review_status = 'pending'; delete ad._regen_step; delete ad._regen_ratios; renderCard(event.ad_name); }
        updateCounts();
        toast(`Regenerated: ${event.ad_name}`, 'success');
        return;
    }
    if (t === 'set:uploading') {
        setUploading[event.set_key] = true;
        renderSetHeader(event.set_key);
        toast(`Uploading set to Drive...`, 'info');
        return;
    }
    if (t === 'set:uploaded') {
        delete setUploading[event.set_key];
        setDriveLinks[event.set_key] = event.drive_link;
        renderAll();
        toast(`Set uploaded to Drive!`, 'success');
        return;
    }
    if (t === 'set:upload_failed') {
        delete setUploading[event.set_key];
        renderSetHeader(event.set_key);
        toast(`Drive upload failed`, 'error');
        return;
    }
}

// ---- Data loading ----
async function loadAds() {
    const resp = await fetch('/api/ads');
    const data = await resp.json();
    adsData = {};
    data.ads.forEach(ad => { adsData[ad.ad_name] = ad; });
    setsData = data.sets;
    // Restore review state from server
    for (const [name, state] of Object.entries(data.review_state)) {
        if (adsData[name]) adsData[name].review_status = state.status || 'pending';
    }
    renderAll();
}

// ---- Rendering ----
function renderAll() {
    const app = document.getElementById('app');
    const setKeys = Object.keys(setsData).sort();

    let html = '';
    let cardNum = 0;

    const showDeployed = document.getElementById('show-deployed')?.checked;
    const showApproved = document.getElementById('show-approved')?.checked;
    for (const setKey of setKeys) {
        if (!showDeployed && setDriveLinks[setKey]) continue;
        const ads = setsData[setKey];
        const first = ads[0] || {};
        const setApproved = ads.every(a => (adsData[a.ad_name] || a).review_status === 'approved');
        if (!showApproved && setApproved && !setDriveLinks[setKey]) continue;

        html += `<div class="set-group" data-set-key="${esc(setKey)}">`;
        html += `<div class="set-header" id="set-header-${esc(setKey)}">`;
        html += `<div>`;
        html += `<h2>${esc(first.sub_avatar)} / ${esc(first.angle_name)}</h2>`;
        html += `<span class="set-meta">${ads.length} ads &middot; ${esc(setKey)}</span>`;
        html += `</div>`;
        html += renderSetStatus(setKey);
        html += `</div>`;

        for (const ad of ads) {
            cardNum++;
            const a = adsData[ad.ad_name] || ad;
            html += renderCardHTML(a, cardNum);
        }
        html += `</div>`;
    }

    app.innerHTML = html;
    updateCounts();
}

function renderSetStatus(setKey) {
    if (setDriveLinks[setKey]) {
        return `<a class="drive-link" href="${esc(setDriveLinks[setKey])}" target="_blank">View on Drive</a>`;
    }
    if (setUploading[setKey]) {
        return `<span class="set-status-badge uploading">Uploading...</span>`;
    }
    const ads = setsData[setKey] || [];
    const approvedCount = ads.filter(a => (adsData[a.ad_name] || a).review_status === 'approved').length;
    if (approvedCount === ads.length && ads.length > 0) {
        return `<span class="set-status-badge uploaded">All approved</span>`;
    }
    return `<span class="set-meta">${approvedCount}/${ads.length} approved</span>`;
}

function renderSetHeader(setKey) {
    const el = document.getElementById(`set-header-${setKey}`);
    if (!el) return;
    const statusEl = el.querySelector('.drive-link, .set-status-badge, .set-meta:last-child');
    // Re-render entire set header is simpler
    const ads = setsData[setKey] || [];
    const first = ads[0] ? (adsData[ads[0].ad_name] || ads[0]) : {};
    el.innerHTML = `<div><h2>${esc(first.sub_avatar || '')} / ${esc(first.angle_name || '')}</h2>`
        + `<span class="set-meta">${ads.length} ads &middot; ${esc(setKey)}</span></div>`
        + renderSetStatus(setKey);
}

function renderCardHTML(ad, num) {
    const statusClass = ad.review_status ? `status-${ad.review_status}` : '';
    const autoClass = (ad.auto_review_status || '').replace(/ /g, '_');
    const isRegen = ad.review_status === 'regenerating';
    const isRejected = ad.review_status === 'rejected';
    const isApproved = ad.review_status === 'approved';

    let html = `<div class="card ${statusClass}" id="card-${esc(ad.ad_name)}" data-ad="${esc(ad.ad_name)}">`;

    // Header
    html += `<div class="card-header"><div class="title-block">`;
    html += `<h3><span class="card-number">#${num}</span> ${esc(ad.visual_format)} x ${esc(ad.messaging_concept)}</h3>`;
    html += `<span class="card-meta">${esc(ad.ad_name)}</span>`;
    html += `</div>`;
    if (autoClass) {
        html += `<span class="auto-review-badge ${autoClass}">${esc(ad.auto_review_status)}</span>`;
    }
    html += `</div>`;

    // Body
    html += `<div class="card-body">`;

    // On-image copy — the text baked into the creative (shown prominently)
    if (ad.on_image_copy) {
        html += `<div class="on-image-copy"><h4>Copy on Image</h4>${esc(ad.on_image_copy)}</div>`;
    } else if (!ad.has_9x16 && !ad.has_1x1) {
        html += `<div class="on-image-copy"><h4>Copy on Image</h4><span style="color:#666">Waiting for copy...</span></div>`;
    }

    // Toggle buttons for secondary info
    const missingImages = !ad.has_9x16 || !ad.has_1x1;
    html += `<div style="margin-bottom:0.75rem">`;
    if (missingImages) {
        html += `<button class="meta-copy-toggle" onclick="this.parentElement.nextElementSibling.classList.toggle('visible')">Meta Ad Copy</button>`;
    }
    html += `<button class="image-prompt-toggle" onclick="document.getElementById('prompt-${esc(ad.ad_name)}').classList.toggle('visible')">Full Image Prompt</button>`;
    html += `</div>`;

    // Meta copy (primary text + headline) — only shown when images are missing
    if (missingImages) {
        html += `<div class="meta-copy-section">`;
        html += `<div class="copy-block"><h4>Headline</h4><p class="headline-text">${esc(ad.headline || '...')}</p></div>`;
        html += `<div class="copy-block"><h4>Primary Text</h4><p class="primary-text">${esc(ad.primary_text || 'Waiting for copy...')}</p></div>`;
        html += `</div>`;
    }

    // Full image prompt — hidden by default
    if (ad.image_prompt) {
        html += `<div class="image-prompt-block" id="prompt-${esc(ad.ad_name)}"><h4>Full Image Prompt</h4><p class="image-prompt-text">${esc(ad.image_prompt)}</p></div>`;
    }

    // Images
    html += `<div class="images-row">`;
    const regenRatios = (isRegen && ad._regen_ratios) ? ad._regen_ratios : [];
    if (isRegen) {
        const stepText = ad._regen_step || 'Regenerating...';
        html += `<div class="regen-status" id="regen-step-${esc(ad.ad_name)}">${esc(stepText)}</div>`;
    }
    for (const [ratio, label] of [['9x16', '9:16'], ['1x1', '1:1']]) {
        const hasImg = ratio === '9x16' ? ad.has_9x16 : ad.has_1x1;
        const ratioIsRegen = regenRatios.includes(ratio);
        html += `<div class="img-col">`;
        if (ratioIsRegen) {
            html += `<div class="img-spinner"><span>Regenerating...</span></div>`;
        } else if (hasImg) {
            const src = `/api/image/${esc(ad.batch_dir)}/${esc(ad.ad_name)}_${ratio}.png?t=${Date.now()}`;
            html += `<div class="img-wrapper">`;
            html += `<span class="ratio-label">${label}</span>`;
            html += `<img src="${src}" loading="lazy">`;
            html += `</div>`;
        } else {
            html += `<div class="img-placeholder">${label} pending</div>`;
        }
        html += `</div>`;
    }
    html += `</div>`;

    // Actions
    html += `<div class="card-actions">`;
    html += `<button class="btn btn-approve ${isApproved ? 'active' : ''}" onclick="approveAd('${esc(ad.ad_name)}')" ${isRegen ? 'disabled' : ''}>Approve</button>`;
    html += `<button class="btn btn-reject-copy" onclick="toggleReject('${esc(ad.ad_name)}','copy')" ${isRegen ? 'disabled' : ''}>Bad Copy</button>`;
    html += `<button class="btn btn-reject-image" onclick="toggleReject('${esc(ad.ad_name)}','image')" ${isRegen ? 'disabled' : ''}>Bad Image</button>`;
    html += `<button class="btn btn-reject-concept ${isRejected ? 'active' : ''}" onclick="rejectConcept('${esc(ad.ad_name)}')" ${isRegen ? 'disabled' : ''}>Kill Concept</button>`;
    html += `</div>`;

    // Reject panel
    html += `<div class="reject-panel" id="reject-panel-${esc(ad.ad_name)}">`;
    html += `<label>Category</label>`;
    html += `<select id="reject-cat-${esc(ad.ad_name)}">`;
    html += `<option value="copy">Bad Copy (regenerate copy + images)</option>`;
    html += `<option value="image-product">Wrong Product/Offer (regenerate image)</option>`;
    html += `<option value="image-execution">Bad Image Execution (regenerate image)</option>`;
    html += `</select>`;
    html += `<div class="ratio-select" id="ratio-select-${esc(ad.ad_name)}">`;
    html += `<label>Which ratio?</label>`;
    html += `<select id="reject-ratio-${esc(ad.ad_name)}">`;
    html += `<option value="both">Both (9:16 + 1:1)</option>`;
    html += `<option value="9x16">9:16 only</option>`;
    html += `<option value="1x1">1:1 only</option>`;
    html += `</select></div>`;
    html += `<label>Notes (be specific)</label>`;
    html += `<textarea id="reject-notes-${esc(ad.ad_name)}" placeholder="e.g. 'Should show the full kit, not a single bottle' or 'Text is illegible on dark background'"></textarea>`;
    html += `<button class="btn btn-send-reject" onclick="sendReject('${esc(ad.ad_name)}')">Regenerate</button>`;
    html += `</div>`;

    html += `</div></div>`;
    return html;
}

function renderCard(adName) {
    const el = document.getElementById(`card-${adName}`);
    if (!el) { renderAll(); return; }
    const ad = adsData[adName];
    if (!ad) return;
    const num = el.querySelector('.card-number')?.textContent.replace('#', '') || '?';

    const tmp = document.createElement('div');
    tmp.innerHTML = renderCardHTML(ad, num);
    const newCard = tmp.firstElementChild;
    el.replaceWith(newCard);
    updateCounts();

    // Also update set header
    if (ad.set_key) renderSetHeader(ad.set_key);
}

function updateCounts() {
    const ads = Object.values(adsData);
    const total = ads.length;
    const approved = ads.filter(a => a.review_status === 'approved').length;
    const rejected = ads.filter(a => a.review_status === 'rejected').length;
    const regen = ads.filter(a => a.review_status === 'regenerating').length;
    const pending = total - approved - rejected - regen;
    const deployedSets = Object.keys(setDriveLinks).length;

    document.getElementById('c-total').textContent = `${total} total`;
    document.getElementById('c-approved').textContent = `${approved} approved`;
    document.getElementById('c-rejected').textContent = `${rejected} rejected`;
    document.getElementById('c-regenerating').textContent = `${regen} regenerating`;
    document.getElementById('c-pending').textContent = `${pending} pending`;
    const deployedEl = document.getElementById('c-deployed');
    if (deployedSets > 0) {
        deployedEl.textContent = `${deployedSets} deployed`;
        deployedEl.style.display = '';
    } else {
        deployedEl.style.display = 'none';
    }
}

// ---- Actions ----
async function approveAd(adName) {
    const resp = await fetch(`/api/approve/${adName}`, { method: 'POST' });
    const data = await resp.json();
    if (data.status === 'approved') {
        adsData[adName].review_status = 'approved';
        renderCard(adName);
    }
}

function toggleReject(adName, mode) {
    const panel = document.getElementById(`reject-panel-${adName}`);
    const ratioSel = document.getElementById(`ratio-select-${adName}`);
    const catSel = document.getElementById(`reject-cat-${adName}`);

    panel.classList.toggle('visible');

    if (mode === 'copy') {
        catSel.value = 'copy';
        ratioSel.classList.remove('visible');
    } else {
        catSel.value = 'image-product';
        ratioSel.classList.add('visible');
    }

    // Update ratio visibility on category change
    catSel.onchange = () => {
        if (catSel.value === 'copy') {
            ratioSel.classList.remove('visible');
        } else {
            ratioSel.classList.add('visible');
        }
    };
}

async function sendReject(adName) {
    const category = document.getElementById(`reject-cat-${adName}`).value;
    const notes = document.getElementById(`reject-notes-${adName}`).value;
    const ratio = document.getElementById(`reject-ratio-${adName}`).value;

    adsData[adName].review_status = 'regenerating';
    renderCard(adName);

    // Non-blocking: server returns immediately, progress comes via SSE
    fetch('/api/reject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ad_name: adName, category, notes, ratio }),
    }).catch(err => toast(`Request failed: ${err.message}`, 'error'));
}

async function rejectConcept(adName) {
    if (!confirm(`Kill this concept? It won't be regenerated.`)) return;
    await fetch('/api/reject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ad_name: adName, category: 'concept', notes: '' }),
    });
    adsData[adName].review_status = 'rejected';
    renderCard(adName);
}

// ---- Helpers ----
function esc(s) { return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }

function toast(msg, type) {
    const container = document.getElementById('toasts');
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = msg;
    container.appendChild(el);
    setTimeout(() => el.remove(), 4000);
}

// ---- Init ----
loadAds();
connectSSE();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive ad review server")
    parser.add_argument(
        "statics_folder", help="Path to statics folder (e.g. clients/{client}/ads/statics)"
    )
    parser.add_argument("--client", required=True, help="Client name")
    parser.add_argument("--port", type=int, default=8787, help="Server port (default: 8787)")
    parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")
    args = parser.parse_args()

    global statics_dir, client_dir
    statics_dir = Path(args.statics_folder).resolve()
    client_dir = PROJECT_ROOT / "clients" / args.client

    if not statics_dir.is_dir():
        print(f"Error: not a directory: {statics_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Statics folder: {statics_dir}")
    print(f"Client: {args.client}")
    print(f"Server: http://localhost:{args.port}")

    app = create_app()

    if not args.no_browser:
        import threading

        threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{args.port}")).start()

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
