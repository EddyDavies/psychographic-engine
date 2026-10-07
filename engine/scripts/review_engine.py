from __future__ import annotations

import json
import re
import time
from pathlib import Path

from utils import PROJECT_ROOT, encode_image, openrouter_headers

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
REVIEW_MODEL = "google/gemini-3-flash-preview"
REVIEW_RETRIES = 3
RETRY_DELAY = 5

COPY_REVIEW_RULES = [
    "no_competitor_names",
    "no_fake_offers",
    "review_count_truth",
    "bundle_truth",
]


def load_review_config(client_dir: Path) -> dict:
    config_path = client_dir / "brand" / "review-rules.json"
    if not config_path.exists():
        return {
            "enabled": False,
            "client": client_dir.name,
            "offer_file": "",
            "allowed_review_count_variants": [],
            "banned_competitors": [],
            "banned_offer_phrases": [],
            "full_pack_required_formats": [],
            "manual_checks": [],
        }
    config = json.loads(config_path.read_text())
    config["enabled"] = True
    return config


def extract_markdown_section(text: str, heading: str) -> str:
    pattern = rf"## {re.escape(heading)}\s*\n(.+?)(?=\n## |\Z)"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""


def resolve_offer_context(config: dict) -> dict[str, str]:
    offer_rel = config.get("offer_file", "")
    offer_path = PROJECT_ROOT / offer_rel
    offer_text = offer_path.read_text() if offer_rel and offer_path.is_file() else ""
    return {
        "offer_path": str(offer_path.relative_to(PROJECT_ROOT)) if offer_path.is_file() else offer_rel,
        "full_text": offer_text,
        "bundle_summary": extract_markdown_section(offer_text, "What The Customer Gets"),
    }


def is_full_pack_required(config: dict, visual_slug: str) -> bool:
    return visual_slug in set(config.get("full_pack_required_formats", []))


def client_label(config: dict) -> str:
    return str(config.get("client", "client")).title()


def bundle_display_name(config: dict) -> str:
    return str(config.get("bundle_display_name", "the full product bundle"))


def build_copy_rule_context(config: dict, visual_slug: str, offer_context: dict[str, str]) -> str:
    if not config.get("enabled"):
        return ""

    full_pack_policy = (
        f"This visual format should show {bundle_display_name(config)}."
        if is_full_pack_required(config, visual_slug)
        else "If products appear, keep them reference-accurate. Full-pack display is preferred but not mandatory for this format."
    )
    allowed_counts = ", ".join(config.get("allowed_review_count_variants", []))
    bundle_summary = offer_context.get("bundle_summary", "").strip()

    return (
        f"### {client_label(config)} Hard Rules For This Ad\n"
        f"- Bundle/product truth source: `{offer_context.get('offer_path', '')}`.\n"
        f"- {full_pack_policy}\n"
        f"- If you mention review volume, use only: {allowed_counts}.\n"
        "- Never mention competitors by name.\n"
        "- Never invent unsupported promotions or offer mechanics.\n"
        "- Do not fabricate testimonial/review-style quotes or customer names.\n"
        "- Keep all product descriptions faithful to the offer and reference imagery.\n\n"
        f"### Bundle Summary\n{bundle_summary}\n"
    )


def build_render_rule_block(config: dict, visual_slug: str, offer_context: dict[str, str]) -> str:
    if not config.get("enabled"):
        return ""

    full_pack_policy = (
        f"Show {bundle_display_name(config)} in the image."
        if is_full_pack_required(config, visual_slug)
        else "If products are visible, keep them accurate to the reference image. Full-pack display is preferred but optional for this format."
    )
    allowed_counts = ", ".join(config.get("allowed_review_count_variants", []))
    bundle_summary = offer_context.get("bundle_summary", "").strip()

    image_rule_lines = "".join(f"- {rule}\n" for rule in config.get("image_rules", []))

    block = (
        f"[{client_label(config).upper()} HARD RULES - MUST FOLLOW]\n"
        "- If products are visible, check them against the specific rules below — do not penalise stylistic differences from the reference images.\n"
        f"- {full_pack_policy}\n"
        f"- Bundle truth comes from {offer_context.get('offer_path', '')}.\n"
        f"- Bundle summary: {bundle_summary}\n"
        f"{image_rule_lines}"
        f"- If a review count appears anywhere, use only: {allowed_counts}.\n"
        "- Never mention competitors by name anywhere in the image.\n"
        "- Never show fake offers or unsupported promotion mechanics.\n"
        "- Any text placed in the image must remain readable against the background.\n"
        "- Keep anatomy and object structure realistic; no extra fingers or malformed hands.\n"
    )

    return block


def append_regeneration_feedback(prompt: str, failures: list[dict[str, str]]) -> str:
    if not failures:
        return prompt

    lines = [
        "[REGENERATION FEEDBACK - FIX THESE FAILURES EXACTLY]",
        "The previous render failed review. Correct every item below in this new render.",
    ]
    for failure in failures:
        lines.append(f"- {failure.get('message', '').strip()}")
    return f"{prompt.rstrip()}\n\n" + "\n".join(lines) + "\n"


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def _review_count_failures(
    text: str, allowed_counts: set[str], allowed_display: list[str]
) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    pattern = re.compile(r"(?i)\b(\d[\d,\.]*(?:k)?\+?)\s+(?:five-star\s+)?reviews?\b")
    for match in pattern.finditer(text):
        raw_value = _normalize_text(match.group(1))
        if raw_value not in allowed_counts:
            failures.append(
                {
                    "id": "review_count_truth",
                    "message": (
                        f"Found review count '{match.group(1)} reviews'. "
                        f"Use only {' / '.join(allowed_display)}."
                    ),
                }
            )
    return failures


def _regex_copy_check(config: dict, combined: str) -> list[dict[str, str]]:
    lowered = _normalize_text(combined)
    failures: list[dict[str, str]] = []

    for competitor in config.get("banned_competitors", []):
        if competitor.lower() in lowered:
            failures.append(
                {
                    "id": "no_competitor_names",
                    "message": f"Competitor reference '{competitor}' found in generated copy/prompt.",
                }
            )

    for phrase in config.get("banned_offer_phrases", []):
        if phrase.lower() in lowered:
            failures.append(
                {
                    "id": "no_fake_offers",
                    "message": f"Unsupported offer phrase '{phrase}' found in generated copy/prompt.",
                }
            )

    allowed_display = config.get("allowed_review_count_variants", [])
    allowed_review_counts = {_normalize_text(value) for value in allowed_display}
    if allowed_review_counts:
        failures.extend(_review_count_failures(combined, allowed_review_counts, allowed_display))

    return failures


def _llm_copy_check(config: dict, copy_data: dict[str, str], offer_context: dict[str, str]) -> dict[str, object]:
    import httpx

    hard_rules = config.get("hard_rules", [])
    copy_rules = [rule for rule in hard_rules if rule.get("id") in COPY_REVIEW_RULES]
    if not copy_rules:
        return {"status": "passed", "hard_rule_failures": [], "manual_flags": []}

    rules_text = "\n".join(f"- [{rule['id']}] {rule['description']}" for rule in copy_rules)
    banned_competitors = ", ".join(config.get("banned_competitors", [])) or "none listed"
    banned_phrases = ", ".join(config.get("banned_offer_phrases", [])) or "none listed"
    allowed_counts = ", ".join(config.get("allowed_review_count_variants", [])) or "any"
    offer_text = offer_context.get("full_text", "").strip()

    prompt = (
        "You are a strict QA reviewer for ad copy. Check the copy below against these hard rules.\n\n"
        f"Hard rules:\n{rules_text}\n\n"
        f"Banned competitors: {banned_competitors}\n"
        f"Banned offer phrases: {banned_phrases}\n"
        f"Allowed review-count variants: {allowed_counts}\n\n"
        f"Offer file (this is the product truth — flag any copy that contradicts it):\n{offer_text}\n\n"
        "CRITICAL — WHAT COUNTS AS A FAILURE:\n"
        "- Only flag copy that STATES something INCORRECT (wrong product, wrong count, wrong offer).\n"
        "- NEVER flag copy for OMITTING information. Ads do not have to mention the review count, "
        "the product name, the bundle contents, or the offer. Curiosity-based and emotional ads "
        "deliberately leave details out — this is valid creative strategy, not a rule violation.\n"
        "- Review count rule: ONLY fails if a specific number is stated AND that number is wrong. "
        "Not mentioning reviews at all is perfectly fine.\n"
        "- Bundle truth rule: ONLY fails if the copy describes the WRONG product (e.g. wrong item count, "
        "wrong product type). Describing a single item when the offer is a pack is fine; "
        "the ad may be focusing on one item from the pack. Only flag outright contradictions.\n\n"
        "Look for paraphrased or indirect violations, not just exact matches. "
        "For example, alluding to a competitor without naming them exactly, or rewording a banned offer.\n\n"
        "Ignore proofreading, spelling, and grammar — only check hard rules.\n\n"
        f"Headline: {copy_data.get('headline', '')}\n"
        f"Primary text: {copy_data.get('primary_text', '')}\n"
        f"Image prompt: {copy_data.get('image_prompt', '')}\n\n"
        "Return JSON only:\n"
        "{\n"
        '  "status": "passed" | "failed_regenerate",\n'
        '  "hard_rule_failures": [{"id": "rule_id", "message": "what failed"}],\n'
        '  "manual_flags": ["non-blocking observations"],\n'
        '  "summary": "one sentence summary"\n'
        "}\n"
        "If no rules are broken, return status 'passed' with empty hard_rule_failures."
    )

    payload = {
        "model": REVIEW_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }

    last_error: Exception | None = None
    for attempt in range(1, REVIEW_RETRIES + 1):
        try:
            response = httpx.post(
                OPENROUTER_URL,
                json=payload,
                headers=openrouter_headers(),
                timeout=120,
            )
            response.raise_for_status()
            raw = response.json()["choices"][0]["message"]["content"]
            if isinstance(raw, list):
                raw = "".join(block.get("text", "") for block in raw if isinstance(block, dict))
            parsed = _parse_review_json(str(raw))
            if not parsed:
                raise ValueError("Could not parse copy review JSON")

            failures = parsed.get("hard_rule_failures", [])
            status = str(parsed.get("status", "passed")).strip()
            if status not in {"passed", "failed_regenerate"}:
                status = "failed_regenerate" if failures else "passed"
            if failures and status == "passed":
                status = "failed_regenerate"

            return {
                "status": status,
                "hard_rule_failures": failures,
                "manual_flags": parsed.get("manual_flags", []),
                "summary": str(parsed.get("summary", "")).strip(),
            }
        except Exception as exc:
            last_error = exc
            if attempt < REVIEW_RETRIES:
                time.sleep(RETRY_DELAY)

    return {
        "status": "passed",
        "hard_rule_failures": [],
        "manual_flags": [],
        "summary": f"LLM copy review unavailable ({last_error}); regex checks passed.",
    }


def review_copy_rules(config: dict, copy_data: dict[str, str], offer_context: dict[str, str] | None = None) -> dict[str, object]:
    if not config.get("enabled"):
        return {
            "status": "passed",
            "hard_rule_failures": [],
            "manual_flags": [],
            "summary": "No client-specific hard-rule config enabled.",
        }

    combined = "\n".join(
        [
            copy_data.get("headline", ""),
            copy_data.get("primary_text", ""),
            copy_data.get("image_prompt", ""),
        ]
    )

    # Stage 1: fast regex checks
    regex_failures = _regex_copy_check(config, combined)
    if regex_failures:
        return {
            "status": "failed_regenerate",
            "hard_rule_failures": regex_failures,
            "manual_flags": [],
            "summary": "Copy violated one or more hard rules (regex).",
        }

    # Stage 2: LLM review for paraphrased/indirect violations
    llm_result = _llm_copy_check(config, copy_data, offer_context or {})
    if llm_result["status"] != "passed":
        return {
            "status": "failed_regenerate",
            "hard_rule_failures": llm_result.get("hard_rule_failures", []),
            "manual_flags": llm_result.get("manual_flags", []),
            "summary": str(llm_result.get("summary", "Copy violated one or more hard rules (LLM).")),
        }

    return {
        "status": "passed",
        "hard_rule_failures": [],
        "manual_flags": llm_result.get("manual_flags", []),
        "summary": "Copy passed hard-rule checks.",
    }


def _strip_json_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_review_json(raw: str) -> dict | None:
    text = _strip_json_fences(raw)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def review_rendered_image(
    config: dict,
    visual_slug: str,
    aspect_ratio: str,
    copy_data: dict[str, str],
    render_prompt: str,
    image_path: Path,
    reference_images: list[Path],
    offer_context: dict[str, str],
) -> dict[str, object]:
    if not config.get("enabled"):
        return {
            "status": "passed",
            "hard_rule_failures": [],
            "manual_flags": [],
            "summary": "No client-specific image review configured.",
        }

    import httpx

    local_copy_review = review_copy_rules(config, copy_data, offer_context)
    if local_copy_review["status"] != "passed":
        return local_copy_review

    if not image_path.exists():
        return {
            "status": "needs_human_review",
            "hard_rule_failures": [],
            "manual_flags": [],
            "summary": f"Rendered image missing: {image_path.name}",
        }

    full_pack_policy = (
        f"{bundle_display_name(config).capitalize()} is REQUIRED in this format."
        if is_full_pack_required(config, visual_slug)
        else "This format may omit the full product bundle, but any products shown must remain accurate to the reference images."
    )
    image_rule_lines = "".join(f"- {rule}\n" for rule in config.get("image_rules", []))
    reference_note_lines = "".join(f"- {note}\n" for note in config.get("reference_notes", []))
    allowed_counts = " / ".join(config.get("allowed_review_count_variants", []))
    review_count_line = (
        f"- Review count, if shown, must be {allowed_counts} only. Not showing a review count is fine.\n"
        if allowed_counts
        else ""
    )
    content: list[dict] = [
        {
            "type": "text",
            "text": (
                f"You are a strict QA reviewer for {client_label(config)} ad images. "
                "The first images are product REFERENCE photos showing the real products. "
                "The final image is the AI-GENERATED ad to review.\n\n"
                f"Visual format: {visual_slug}\n"
                f"Aspect ratio: {aspect_ratio}\n"
                f"{full_pack_policy}\n"
                f"Bundle truth source: {offer_context.get('offer_path', '')}\n"
                f"Offer file contents (this is the product truth — flag anything that contradicts it):\n{offer_context.get('full_text', '')}\n\n"
                f"Allowed review-count variants: {allowed_counts}\n\n"
                "HARD RULES — flag as failure:\n"
                "- Product accuracy: Compare generated products CAREFULLY against the reference photos. "
                "Check that shapes, colours, materials, and packaging match.\n"
                f"{image_rule_lines}"
                "- No competitor names anywhere.\n"
                "- No fake offers or unsupported promotions.\n"
                f"{review_count_line}"
                "- Text must be readable against the background.\n"
                "- No watermarks, AI generation artifacts, or model signatures (especially the Gemini star watermark — reject if present).\n"
                "- Reject obvious realism failures (extra fingers, malformed hands).\n"
                "- Reject text in the image with missing spaces between words, garbled/nonsense words, or obvious typos.\n\n"
                "NON-BLOCKING FLAGS (report as manual_flags, not failures):\n"
                "- Too much text on screen / visual clutter.\n"
                "- Weak subheads or awkward supporting text.\n"
                "- Layout feels overloaded or noisy.\n\n"
                "IMPORTANT:\n"
                "- Be precise about what you see. Do not guess or infer defects that are not clearly visible.\n"
                f"{reference_note_lines}"
                f"Primary text: {copy_data.get('primary_text', '')}\n"
                f"Headline: {copy_data.get('headline', '')}\n"
                f"Render prompt excerpt: {render_prompt[:2500]}\n\n"
                "Return JSON only with this shape:\n"
                "{\n"
                '  "status": "passed" | "failed_regenerate" | "needs_human_review",\n'
                '  "hard_rule_failures": [{"id": "rule_id", "message": "what failed"}],\n'
                '  "manual_flags": ["non-blocking observations"],\n'
                '  "summary": "one sentence summary"\n'
                "}\n"
                "If any hard rule is broken, use status 'failed_regenerate'. "
                "Use 'needs_human_review' only when the image is too ambiguous to judge confidently."
            ),
        }
    ]

    for reference_image in reference_images:
        if reference_image.exists():
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": encode_image(reference_image)},
                }
            )

    content.append(
        {
            "type": "image_url",
            "image_url": {"url": encode_image(image_path)},
        }
    )

    payload = {
        "model": REVIEW_MODEL,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.1,
    }

    last_error: Exception | None = None
    for attempt in range(1, REVIEW_RETRIES + 1):
        try:
            response = httpx.post(
                OPENROUTER_URL,
                json=payload,
                headers=openrouter_headers(),
                timeout=300,
            )
            response.raise_for_status()
            raw = response.json()["choices"][0]["message"]["content"]
            if isinstance(raw, list):
                raw = "".join(block.get("text", "") for block in raw if isinstance(block, dict))
            parsed = _parse_review_json(str(raw))
            if not parsed:
                raise ValueError("Could not parse review JSON")

            failures = parsed.get("hard_rule_failures", [])
            manual_flags = parsed.get("manual_flags", [])
            status = str(parsed.get("status", "needs_human_review")).strip()
            if status not in {"passed", "failed_regenerate", "needs_human_review"}:
                status = "needs_human_review"
            if failures and status == "passed":
                status = "failed_regenerate"

            return {
                "status": status,
                "hard_rule_failures": failures,
                "manual_flags": manual_flags,
                "summary": str(parsed.get("summary", "")).strip(),
            }
        except Exception as exc:
            last_error = exc
            if attempt < REVIEW_RETRIES:
                time.sleep(RETRY_DELAY)

    return {
        "status": "needs_human_review",
        "hard_rule_failures": [],
        "manual_flags": [],
        "summary": f"Image review failed: {last_error}",
    }


def creative_quality_review(
    copy_data: dict[str, str],
    sub_avatar_text: str,
    messaging_concept_text: str,
    awareness_bucket: str,
) -> dict[str, object]:
    """Non-blocking creative quality check. Returns flags, never blocks generation."""
    import httpx

    prompt = (
        "You are a creative quality reviewer for direct-response Facebook ads. "
        "This is NOT a compliance check — the ad already passed compliance. "
        "You are checking whether the ad will actually PERFORM.\n\n"
        "Review the ad copy against the sub-avatar and messaging concept below. "
        "Flag issues but do not block — everything is advisory.\n\n"
        f"**Sub-Avatar:**\n{sub_avatar_text}\n\n"
        f"**Messaging Concept:**\n{messaging_concept_text}\n\n"
        f"**Awareness Bucket:** {awareness_bucket}\n\n"
        f"**Headline:** {copy_data.get('headline', '')}\n"
        f"**Primary Text:** {copy_data.get('primary_text', '')}\n\n"
        "Check these five things:\n"
        "1. **messaging_concept_followed**: Does the primary text open with or clearly follow the messaging concept's structure pattern? (e.g. 'I accidentally...' should actually start that way)\n"
        "2. **gap_addressed**: Does the copy speak to this specific sub-avatar's Gap — the structural problem described in their profile — or is it generic category copy?\n"
        "3. **awareness_matched**: Is the copy calibrated to the awareness level? Problem Aware needs education/reframing. Solution Aware needs proof/differentiation. Most Aware needs a trigger/offer.\n"
        "4. **hook_strength**: Is the headline specific and arresting, or could it work for any brand in the category? Rate: strong / generic / weak.\n"
        "5. **copy_freshness**: Does the primary text feel like a distinct piece of creative, or does it read like a template with proof points slotted in?\n\n"
        "Return JSON only:\n"
        "{\n"
        '  "messaging_concept_followed": {"pass": true/false, "note": "..."},\n'
        '  "gap_addressed": {"pass": true/false, "note": "..."},\n'
        '  "awareness_matched": {"pass": true/false, "note": "..."},\n'
        '  "hook_strength": "strong" | "generic" | "weak",\n'
        '  "hook_note": "...",\n'
        '  "copy_freshness": "fresh" | "templated" | "stale",\n'
        '  "copy_note": "...",\n'
        '  "overall_score": 1-5,\n'
        '  "summary": "one sentence overall assessment"\n'
        "}\n"
    )

    payload = {
        "model": REVIEW_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }

    try:
        response = httpx.post(
            OPENROUTER_URL,
            json=payload,
            headers=openrouter_headers(),
            timeout=120,
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        if isinstance(raw, list):
            raw = "".join(block.get("text", "") for block in raw if isinstance(block, dict))
        parsed = _parse_review_json(str(raw))
        if parsed:
            return parsed
    except Exception as exc:
        return {
            "summary": f"Creative quality review unavailable: {exc}",
            "overall_score": 0,
        }

    return {
        "summary": "Creative quality review could not parse response.",
        "overall_score": 0,
    }


def force_human_review(review_result: dict[str, object], max_attempts: int) -> dict[str, object]:
    failures = list(review_result.get("hard_rule_failures", []))
    summary = str(review_result.get("summary", "")).strip()
    if not summary:
        summary = "Max regeneration attempts reached."
    else:
        summary = f"{summary} Max regeneration attempts reached ({max_attempts})."
    return {
        "status": "needs_human_review",
        "hard_rule_failures": failures,
        "manual_flags": list(review_result.get("manual_flags", [])),
        "summary": summary,
    }


def derive_creative_review_status(review_results: dict[str, dict[str, object]]) -> str:
    if not review_results:
        return "pending_review"

    statuses = {result.get("status") for result in review_results.values()}
    if statuses == {"passed"}:
        return "passed"
    if "needs_human_review" in statuses:
        return "needs_human_review"
    if "failed_regenerate" in statuses:
        return "needs_human_review"
    return "pending_review"
