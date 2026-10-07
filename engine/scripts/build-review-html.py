"""
Build an HTML review page from generated ad images + copy files.
Usage: python3 scripts/build-review-html.py <ads-folder>
"""

from __future__ import annotations

import base64
import html
import json
import re
import sys
from pathlib import Path


def load_image_b64(path: str) -> str:
    with open(path, "rb") as handle:
        return base64.b64encode(handle.read()).decode()


def parse_copy(path: str) -> tuple[str, str]:
    with open(path) as handle:
        text = handle.read()
    primary = ""
    headline = ""
    match = re.search(r"## Primary Text\n\n(.+?)(?=\n## |\Z)", text, re.DOTALL)
    if match:
        primary = match.group(1).strip()
    match = re.search(r"## Headline\n\n(.+?)(?=\n## |\Z)", text, re.DOTALL)
    if match:
        headline = match.group(1).strip()
    return primary, headline


def load_manifest(folder: Path) -> dict[str, dict]:
    manifest_path = folder / "manifest.json"
    if not manifest_path.exists():
        return {}

    entries = json.loads(manifest_path.read_text())
    manifest: dict[str, dict] = {}
    for entry in entries:
        copy_file = entry.get("copy_file", "")
        stem = Path(copy_file).stem.removesuffix("-copy")
        manifest[stem] = entry
    return manifest


def load_sidecar_review(folder: Path, ad_name: str, ratio_suffix: str) -> dict | None:
    sidecar_path = folder / f"{ad_name}_{ratio_suffix}.json"
    if not sidecar_path.exists():
        return None
    data = json.loads(sidecar_path.read_text())
    return data.get("review")


def discover_ad_names(folder: Path, manifest_entries: dict[str, dict]) -> list[str]:
    png_names = {
        re.sub(r"_(9x16|1x1)\.png$", "", path.name)
        for path in folder.glob("*.png")
    }
    copy_names = {path.stem.removesuffix("-copy") for path in folder.glob("*-copy.md")}
    return sorted(png_names | copy_names | set(manifest_entries))


def render_status_badge(status: str) -> str:
    label = status.replace("_", " ").title()
    css_class = {
        "passed": "passed",
        "needs_human_review": "needs-human-review",
        "pending_review": "pending-review",
    }.get(status, "pending-review")
    return f'<span class="status-badge {css_class}">{html.escape(label)}</span>'


def collect_review_details(folder: Path, ad_name: str, manifest_entry: dict | None) -> dict[str, object]:
    copy_review = (manifest_entry or {}).get("copy_review", {})
    review_results = dict((manifest_entry or {}).get("review_results", {}))
    overall_status = (manifest_entry or {}).get("review_status", "legacy_unreviewed")

    for suffix in ("9x16", "1x1"):
        if suffix not in review_results:
            sidecar_review = load_sidecar_review(folder, ad_name, suffix)
            if sidecar_review:
                review_results[suffix] = sidecar_review

    # Separate copy vs image feedback
    copy_failures: list[str] = []
    copy_flags: list[str] = []
    copy_summary = ""
    image_failures: list[str] = []
    image_flags: list[str] = []
    image_summaries: list[str] = []
    ratio_statuses: list[str] = []

    if copy_review:
        for failure in copy_review.get("hard_rule_failures", []):
            if isinstance(failure, dict):
                copy_failures.append(failure.get("message", "").strip())
        copy_flags.extend(str(flag) for flag in copy_review.get("manual_flags", []))
        copy_summary = copy_review.get("summary", "")

    for ratio_label, result in sorted(review_results.items()):
        status = result.get("status")
        if status:
            ratio_statuses.append(f"{ratio_label}: {status}")
        for failure in result.get("hard_rule_failures", []):
            if isinstance(failure, dict):
                image_failures.append(f"{ratio_label}: {failure.get('message', '')}".strip())
        image_flags.extend(f"{ratio_label}: {flag}" for flag in result.get("manual_flags", []))
        if result.get("summary"):
            image_summaries.append(f"{ratio_label}: {result['summary']}")

    def dedupe(items: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for item in items:
            cleaned = item.strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            unique.append(cleaned)
        return unique

    return {
        "overall_status": overall_status,
        "ratio_statuses": dedupe(ratio_statuses),
        "copy_failures": dedupe(copy_failures),
        "copy_flags": dedupe(copy_flags),
        "copy_summary": copy_summary,
        "image_failures": dedupe(image_failures),
        "image_flags": dedupe(image_flags),
        "image_summaries": dedupe(image_summaries),
    }


def render_list(items: list[str], empty_label: str, css_class: str) -> str:
    if not items:
        return f'<p class="{css_class} empty">{html.escape(empty_label)}</p>'
    rendered = "".join(f"<li>{html.escape(item)}</li>" for item in items)
    return f'<ul class="{css_class}">{rendered}</ul>'


def build_html(folder_arg: str) -> None:
    folder = Path(folder_arg).resolve()
    name = folder.name
    manifest_entries = load_manifest(folder)
    ad_names = discover_ad_names(folder, manifest_entries)

    cards_html = []
    for card_num, ad_name in enumerate(ad_names, 1):
        img_9x16 = folder / f"{ad_name}_9x16.png"
        img_1x1 = folder / f"{ad_name}_1x1.png"
        copy_file = folder / f"{ad_name}-copy.md"
        manifest_entry = manifest_entries.get(ad_name)

        primary = ""
        headline = ""
        if copy_file.exists():
            primary, headline = parse_copy(str(copy_file))
        elif manifest_entry:
            primary = manifest_entry.get("primary_text", "")
            headline = manifest_entry.get("headline", "")

        pretty = ad_name.replace("-", " ").replace("_", " ").title()
        review_details = collect_review_details(folder, ad_name, manifest_entry)

        # Build images with per-ratio numbering (1a, 1b)
        images_html = ""
        ratio_items = [
            (img_9x16, "9x16", "9:16", "a"),
            (img_1x1, "1x1", "1:1", "b"),
        ]
        for image_path, ratio_key, ratio_display, suffix_letter in ratio_items:
            item_id = f"{card_num}{suffix_letter}"
            data_key = f"{ad_name}__{ratio_key}"
            if image_path.exists():
                b64 = load_image_b64(str(image_path))
                images_html += (
                    f'<div class="img-col" data-key="{html.escape(data_key)}">'
                    f'<div class="img-wrapper">'
                    f'<span class="ratio-label">{item_id} \u2014 {ratio_display}</span>'
                    f'<img src="data:image/png;base64,{b64}">'
                    f'</div>'
                    f'<div class="decision-buttons">'
                    f'<button class="btn-approve" onclick="setDecision(\'{html.escape(data_key)}\',\'approve\',this)">Approve</button>'
                    f'<button class="btn-edit" onclick="setDecision(\'{html.escape(data_key)}\',\'edit\',this)">Edit</button>'
                    f'<button class="btn-reject" onclick="setDecision(\'{html.escape(data_key)}\',\'reject\',this)">Reject</button>'
                    f'</div>'
                    f'<textarea class="item-notes" data-key="{html.escape(data_key)}" '
                    f'placeholder="Notes for {item_id}..." oninput="saveNotes(this)"></textarea>'
                    f'</div>\n'
                )
            else:
                images_html += (
                    f'<div class="img-col" data-key="{html.escape(data_key)}">'
                    f'<div class="img-wrapper img-missing">'
                    f'<div class="placeholder">{item_id} \u2014 {ratio_display} missing</div>'
                    f'</div>'
                    f'</div>\n'
                )

        cards_html.append(
            f"""
        <div class="card" id="{html.escape(ad_name)}">
            <div class="card-header">
                <div class="title-block">
                    <h2><span class="card-number">#{card_num}</span> {html.escape(pretty)}</h2>
                    <span class="filename">{html.escape(ad_name)}</span>
                </div>
                {render_status_badge(str(review_details["overall_status"]))}
            </div>
            <div class="card-body">
                <div class="images">{images_html}</div>
                <div class="sidebar">
                    <div class="review-group">
                        <h3 class="group-label image-label">Image Review</h3>
                        <div class="review-section">
                            <div class="review-block">
                                <h3>Ratio Status</h3>
                                {render_list(review_details["ratio_statuses"], "No ratio review data yet.", "status-list")}
                            </div>
                            <div class="review-block">
                                <h3>Hard Rule Failures</h3>
                                {render_list(review_details["image_failures"], "No image failures.", "failure-list")}
                            </div>
                            <div class="review-block">
                                <h3>Flags</h3>
                                {render_list(review_details["image_flags"], "No flags.", "flag-list")}
                            </div>
                            <div class="review-block">
                                <h3>Notes</h3>
                                {render_list(review_details["image_summaries"], "No image review notes.", "summary-list")}
                            </div>
                        </div>
                    </div>
                    <div class="review-group">
                        <h3 class="group-label copy-label">Copy Review</h3>
                        <div class="review-section">
                            <div class="review-block">
                                <h3>Hard Rule Failures</h3>
                                {render_list(review_details["copy_failures"], "No copy failures.", "failure-list")}
                            </div>
                            <div class="review-block">
                                <h3>Flags</h3>
                                {render_list(review_details["copy_flags"], "No flags.", "flag-list")}
                            </div>
                        </div>
                        <div class="copy-section">
                            <div class="copy-block">
                                <h3>Primary Text</h3>
                                <p class="primary-text">{html.escape(primary)}</p>
                            </div>
                            <div class="copy-block">
                                <h3>Headline</h3>
                                <p class="headline-text">{html.escape(headline)}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>"""
        )

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ad Review \u2014 {html.escape(name)}</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: #0a0a0a;
        color: #e0e0e0;
        padding: 2rem;
    }}
    .top-bar {{
        position: sticky;
        top: 0;
        z-index: 100;
        background: #0a0a0a;
        border-bottom: 1px solid #2a2a2a;
        padding: 1rem 0 1rem 0;
        margin-bottom: 2rem;
    }}
    .top-bar-inner {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 1rem;
    }}
    .top-bar h1 {{
        font-size: 1.5rem;
        color: #fff;
    }}
    .summary-counts {{
        display: flex;
        gap: 1rem;
        align-items: center;
        font-size: 0.85rem;
    }}
    .summary-counts .count {{
        padding: 0.3rem 0.7rem;
        border-radius: 6px;
        font-weight: 600;
    }}
    .count-total {{ background: #2a2a2a; color: #c9c9c9; }}
    .count-approved {{ background: #14301f; color: #7ce5a4; }}
    .count-edit {{ background: #382515; color: #ffbe74; }}
    .count-rejected {{ background: #301414; color: #e57c7c; }}
    .count-unreviewed {{ background: #1a1a2e; color: #9999cc; }}
    .top-actions {{
        display: flex;
        gap: 0.5rem;
    }}
    .btn-export {{
        background: #2563eb;
        color: #fff;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 600;
        cursor: pointer;
    }}
    .btn-export:hover {{ background: #1d4ed8; }}
    .btn-clear {{
        background: #333;
        color: #ccc;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-size: 0.85rem;
        cursor: pointer;
    }}
    .btn-clear:hover {{ background: #444; }}
    .card {{
        background: #161616;
        border: 1px solid #2a2a2a;
        border-radius: 12px;
        margin-bottom: 2rem;
        overflow: hidden;
    }}
    .card-header {{
        padding: 1.25rem 1.5rem;
        border-bottom: 1px solid #2a2a2a;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
    }}
    .title-block {{
        min-width: 0;
    }}
    .card-header h2 {{
        font-size: 1.1rem;
        color: #fff;
        margin-bottom: 0.25rem;
    }}
    .card-number {{
        color: #2563eb;
        font-weight: 700;
        margin-right: 0.3rem;
    }}
    .filename {{
        font-size: 0.75rem;
        color: #666;
        font-family: monospace;
    }}
    .status-badge {{
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 0.35rem 0.7rem;
        white-space: nowrap;
    }}
    .status-badge.passed {{
        background: #14301f;
        color: #7ce5a4;
    }}
    .status-badge.needs-human-review {{
        background: #382515;
        color: #ffbe74;
    }}
    .status-badge.pending-review {{
        background: #2a2a2a;
        color: #c9c9c9;
    }}
    .card-body {{
        display: flex;
        align-items: stretch;
    }}
    .images {{
        display: flex;
        gap: 1.5rem;
        padding: 1.5rem;
        background: #111;
        justify-content: center;
        align-items: flex-start;
        flex-wrap: wrap;
        flex-shrink: 0;
    }}
    .sidebar {{
        flex: 1;
        min-width: 300px;
        overflow-y: auto;
        border-left: 1px solid #2a2a2a;
    }}
    .img-col {{
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.75rem;
        flex-shrink: 0;
    }}
    .img-wrapper {{
        position: relative;
        flex-shrink: 0;
    }}
    .img-wrapper img {{
        max-height: 500px;
        width: auto;
        border-radius: 8px;
        display: block;
    }}
    .ratio-label {{
        position: absolute;
        top: 8px;
        left: 8px;
        background: rgba(0,0,0,0.7);
        color: #fff;
        font-size: 0.8rem;
        padding: 3px 10px;
        border-radius: 4px;
        font-family: monospace;
        font-weight: 600;
    }}
    .img-missing {{
        width: 200px;
        height: 300px;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .placeholder {{
        color: #555;
        font-size: 0.85rem;
        text-align: center;
        border: 1px dashed #333;
        border-radius: 8px;
        padding: 2rem;
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .decision-buttons {{
        display: flex;
        gap: 0.4rem;
    }}
    .decision-buttons button {{
        border: 1px solid #333;
        border-radius: 6px;
        padding: 0.35rem 0.75rem;
        font-size: 0.8rem;
        font-weight: 600;
        cursor: pointer;
        background: #1a1a1a;
        color: #999;
        transition: all 0.15s;
    }}
    .decision-buttons button:hover {{
        border-color: #555;
        color: #ddd;
    }}
    .decision-buttons button.active-approve {{
        background: #14301f;
        color: #7ce5a4;
        border-color: #7ce5a4;
    }}
    .decision-buttons button.active-edit {{
        background: #382515;
        color: #ffbe74;
        border-color: #ffbe74;
    }}
    .decision-buttons button.active-reject {{
        background: #301414;
        color: #e57c7c;
        border-color: #e57c7c;
    }}
    .item-notes {{
        width: 100%;
        max-width: 320px;
        min-height: 40px;
        background: #111;
        border: 1px solid #2a2a2a;
        border-radius: 6px;
        color: #e0e0e0;
        padding: 0.5rem;
        font-family: inherit;
        font-size: 0.8rem;
        resize: vertical;
        display: none;
    }}
    .item-notes.visible {{
        display: block;
    }}
    .item-notes:focus {{
        outline: none;
        border-color: #444;
    }}
    .review-group {{
        border-bottom: 1px solid #2a2a2a;
    }}
    .group-label {{
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-weight: 700;
        padding: 0.6rem 1rem 0;
        margin: 0;
    }}
    .image-label {{
        color: #66a;
    }}
    .copy-label {{
        color: #a86;
    }}
    .review-section {{
        padding: 0.75rem 1rem;
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }}
    .review-block {{
        background: #111;
        border: 1px solid #242424;
        border-radius: 10px;
        padding: 1rem;
    }}
    .review-block h3 {{
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #888;
        margin-bottom: 0.6rem;
    }}
    ul {{
        list-style: disc;
        padding-left: 1rem;
    }}
    li {{
        color: #ddd;
        font-size: 0.85rem;
        line-height: 1.5;
        margin-bottom: 0.35rem;
    }}
    .empty {{
        color: #666;
        font-size: 0.85rem;
        line-height: 1.5;
    }}
    .copy-section {{
        padding: 1rem;
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }}
    .copy-block h3 {{
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #888;
        margin-bottom: 0.5rem;
    }}
    .primary-text {{
        font-size: 0.95rem;
        line-height: 1.6;
        white-space: pre-wrap;
    }}
    .headline-text {{
        font-size: 1.1rem;
        font-weight: 600;
        color: #fff;
    }}
</style>
</head>
<body>
    <div class="top-bar">
        <div class="top-bar-inner">
            <div>
                <h1>Ad Review \u2014 {html.escape(name)}</h1>
            </div>
            <div class="summary-counts">
                <span class="count count-total" id="count-total">0 total</span>
                <span class="count count-approved" id="count-approved">0 approved</span>
                <span class="count count-edit" id="count-edit">0 edit</span>
                <span class="count count-rejected" id="count-rejected">0 rejected</span>
                <span class="count count-unreviewed" id="count-unreviewed">0 unreviewed</span>
            </div>
            <div class="top-actions">
                <button class="btn-export" onclick="exportDecisions()">Export JSON</button>
                <button class="btn-clear" onclick="clearAll()">Clear All</button>
            </div>
        </div>
    </div>
    {"".join(cards_html)}
<script>
const BATCH = {json.dumps(name)};
const STORAGE_KEY = 'ad-review-' + BATCH;

function loadState() {{
    try {{
        return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {{}};
    }} catch (e) {{
        return {{}};
    }}
}}

function saveState(state) {{
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}}

function setDecision(key, decision, btn) {{
    const state = loadState();
    // Toggle off if clicking the same decision
    if (state[key] && state[key].decision === decision) {{
        delete state[key];
    }} else {{
        state[key] = state[key] || {{}};
        state[key].decision = decision;
    }}
    saveState(state);
    renderAll();
}}

function saveNotes(textarea) {{
    const key = textarea.dataset.key;
    const state = loadState();
    if (!state[key]) state[key] = {{}};
    state[key].notes = textarea.value;
    saveState(state);
}}

function renderAll() {{
    const state = loadState();
    // Update button states and notes visibility
    document.querySelectorAll('.img-col').forEach(col => {{
        const key = col.dataset.key;
        if (!key) return;
        const entry = state[key] || {{}};
        const decision = entry.decision || '';
        col.querySelectorAll('.decision-buttons button').forEach(btn => {{
            btn.className = btn.className.replace(/active-\\w+/g, '').trim();
        }});
        if (decision) {{
            const btnClass = 'active-' + decision;
            const btnSelector = '.btn-' + decision;
            const activeBtn = col.querySelector(btnSelector);
            if (activeBtn) activeBtn.classList.add(btnClass);
        }}
        // Show notes textarea when decision is 'edit' or has existing notes
        const notes = col.querySelector('.item-notes');
        if (notes) {{
            const showNotes = decision === 'edit' || decision === 'reject' || (entry.notes && entry.notes.trim());
            notes.classList.toggle('visible', showNotes);
            if (entry.notes !== undefined) notes.value = entry.notes;
        }}
    }});
    // Update summary counts
    const allCols = document.querySelectorAll('.img-col[data-key]');
    let approved = 0, edit = 0, rejected = 0, unreviewed = 0;
    allCols.forEach(col => {{
        const key = col.dataset.key;
        const d = (state[key] || {{}}).decision || '';
        if (d === 'approve') approved++;
        else if (d === 'edit') edit++;
        else if (d === 'reject') rejected++;
        else unreviewed++;
    }});
    document.getElementById('count-total').textContent = allCols.length + ' total';
    document.getElementById('count-approved').textContent = approved + ' approved';
    document.getElementById('count-edit').textContent = edit + ' edit';
    document.getElementById('count-rejected').textContent = rejected + ' rejected';
    document.getElementById('count-unreviewed').textContent = unreviewed + ' unreviewed';
}}

function exportDecisions() {{
    const state = loadState();
    const decisions = [];
    document.querySelectorAll('.img-col[data-key]').forEach((col, i) => {{
        const key = col.dataset.key;
        const entry = state[key] || {{}};
        // Parse ad_name and ratio from key (format: adname__ratio)
        const parts = key.split('__');
        decisions.push({{
            number: col.closest('.card').querySelector('.card-number').textContent.replace('#','') + (parts[1] === '9x16' ? 'a' : 'b'),
            ad_name: parts[0],
            ratio: parts[1],
            decision: entry.decision || 'unreviewed',
            notes: entry.notes || ''
        }});
    }});
    const output = {{
        batch: BATCH,
        timestamp: new Date().toISOString(),
        decisions: decisions
    }};
    const blob = new Blob([JSON.stringify(output, null, 2)], {{ type: 'application/json' }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'review-decisions-' + BATCH + '.json';
    a.click();
    URL.revokeObjectURL(url);
}}

function clearAll() {{
    if (!confirm('Clear all decisions? This cannot be undone.')) return;
    localStorage.removeItem(STORAGE_KEY);
    document.querySelectorAll('.item-notes').forEach(t => t.value = '');
    renderAll();
}}

// Init on load
renderAll();
</script>
</body>
</html>"""

    out_path = folder / "review.html"
    out_path.write_text(html_doc)
    print(f"Saved: {out_path}")
    print(f"{len(ad_names)} ads")


def build_cards_for_folder(folder: Path, card_offset: int = 0) -> tuple[list[str], int]:
    """Build card HTML for all ads in a folder. Returns (cards_html, ad_count)."""
    manifest_entries = load_manifest(folder)
    ad_names = discover_ad_names(folder, manifest_entries)

    cards_html = []
    for idx, ad_name in enumerate(ad_names, 1):
        card_num = card_offset + idx
        img_9x16 = folder / f"{ad_name}_9x16.png"
        img_1x1 = folder / f"{ad_name}_1x1.png"
        copy_file = folder / f"{ad_name}-copy.md"
        manifest_entry = manifest_entries.get(ad_name)

        primary = ""
        headline = ""
        if copy_file.exists():
            primary, headline = parse_copy(str(copy_file))
        elif manifest_entry:
            primary = manifest_entry.get("primary_text", "")
            headline = manifest_entry.get("headline", "")

        pretty = ad_name.replace("-", " ").replace("_", " ").title()
        review_details = collect_review_details(folder, ad_name, manifest_entry)

        images_html = ""
        ratio_items = [
            (img_9x16, "9x16", "9:16", "a"),
            (img_1x1, "1x1", "1:1", "b"),
        ]
        for image_path, ratio_key, ratio_display, suffix_letter in ratio_items:
            item_id = f"{card_num}{suffix_letter}"
            data_key = f"{ad_name}__{ratio_key}"
            if image_path.exists():
                b64 = load_image_b64(str(image_path))
                images_html += (
                    f'<div class="img-col" data-key="{html.escape(data_key)}">'
                    f'<div class="img-wrapper">'
                    f'<span class="ratio-label">{item_id} \u2014 {ratio_display}</span>'
                    f'<img src="data:image/png;base64,{b64}">'
                    f'</div>'
                    f'<div class="decision-buttons">'
                    f'<button class="btn-approve" onclick="setDecision(\'{html.escape(data_key)}\',\'approve\',this)">Approve</button>'
                    f'<button class="btn-edit" onclick="setDecision(\'{html.escape(data_key)}\',\'edit\',this)">Edit</button>'
                    f'<button class="btn-reject" onclick="setDecision(\'{html.escape(data_key)}\',\'reject\',this)">Reject</button>'
                    f'</div>'
                    f'<textarea class="item-notes" data-key="{html.escape(data_key)}" '
                    f'placeholder="Notes for {item_id}..." oninput="saveNotes(this)"></textarea>'
                    f'</div>\n'
                )
            else:
                images_html += (
                    f'<div class="img-col" data-key="{html.escape(data_key)}">'
                    f'<div class="img-wrapper img-missing">'
                    f'<div class="placeholder">{item_id} \u2014 {ratio_display} missing</div>'
                    f'</div>'
                    f'</div>\n'
                )

        cards_html.append(
            f"""
        <div class="card" id="{html.escape(ad_name)}">
            <div class="card-header">
                <div class="title-block">
                    <h2><span class="card-number">#{card_num}</span> {html.escape(pretty)}</h2>
                    <span class="filename">{html.escape(ad_name)}</span>
                </div>
                {render_status_badge(str(review_details["overall_status"]))}
            </div>
            <div class="card-body">
                <div class="images">{images_html}</div>
                <div class="sidebar">
                    <div class="review-group">
                        <h3 class="group-label image-label">Image Review</h3>
                        <div class="review-section">
                            <div class="review-block">
                                <h3>Ratio Status</h3>
                                {render_list(review_details["ratio_statuses"], "No ratio review data yet.", "status-list")}
                            </div>
                            <div class="review-block">
                                <h3>Hard Rule Failures</h3>
                                {render_list(review_details["image_failures"], "No image failures.", "failure-list")}
                            </div>
                            <div class="review-block">
                                <h3>Flags</h3>
                                {render_list(review_details["image_flags"], "No flags.", "flag-list")}
                            </div>
                            <div class="review-block">
                                <h3>Notes</h3>
                                {render_list(review_details["image_summaries"], "No image review notes.", "summary-list")}
                            </div>
                        </div>
                    </div>
                    <div class="review-group">
                        <h3 class="group-label copy-label">Copy Review</h3>
                        <div class="review-section">
                            <div class="review-block">
                                <h3>Hard Rule Failures</h3>
                                {render_list(review_details["copy_failures"], "No copy failures.", "failure-list")}
                            </div>
                            <div class="review-block">
                                <h3>Flags</h3>
                                {render_list(review_details["copy_flags"], "No flags.", "flag-list")}
                            </div>
                        </div>
                        <div class="copy-section">
                            <div class="copy-block">
                                <h3>Primary Text</h3>
                                <p class="primary-text">{html.escape(primary)}</p>
                            </div>
                            <div class="copy-block">
                                <h3>Headline</h3>
                                <p class="headline-text">{html.escape(headline)}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>"""
        )

    return cards_html, len(ad_names)


def render_page(title: str, subtitle: str, body_html: str, out_path: Path, storage_key: str) -> None:
    """Write the full HTML page with shared CSS and JS."""
    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ad Review \u2014 {html.escape(title)}</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: #0a0a0a;
        color: #e0e0e0;
        padding: 2rem;
    }}
    .top-bar {{
        position: sticky;
        top: 0;
        z-index: 100;
        background: #0a0a0a;
        border-bottom: 1px solid #2a2a2a;
        padding: 1rem 0 1rem 0;
        margin-bottom: 2rem;
    }}
    .top-bar-inner {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 1rem;
    }}
    .top-bar h1 {{
        font-size: 1.5rem;
        color: #fff;
    }}
    .top-bar .subtitle {{
        color: #888;
        font-size: 0.85rem;
        margin-top: 0.15rem;
    }}
    .summary-counts {{
        display: flex;
        gap: 1rem;
        align-items: center;
        font-size: 0.85rem;
    }}
    .summary-counts .count {{
        padding: 0.3rem 0.7rem;
        border-radius: 6px;
        font-weight: 600;
    }}
    .count-total {{ background: #2a2a2a; color: #c9c9c9; }}
    .count-approved {{ background: #14301f; color: #7ce5a4; }}
    .count-edit {{ background: #382515; color: #ffbe74; }}
    .count-rejected {{ background: #301414; color: #e57c7c; }}
    .count-unreviewed {{ background: #1a1a2e; color: #9999cc; }}
    .top-actions {{
        display: flex;
        gap: 0.5rem;
    }}
    .btn-export {{
        background: #2563eb;
        color: #fff;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 600;
        cursor: pointer;
    }}
    .btn-export:hover {{ background: #1d4ed8; }}
    .btn-clear {{
        background: #333;
        color: #ccc;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-size: 0.85rem;
        cursor: pointer;
    }}
    .btn-clear:hover {{ background: #444; }}
    .set-heading {{
        font-size: 1.25rem;
        color: #fff;
        margin-top: 2.5rem;
        margin-bottom: 0.25rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #333;
    }}
    .set-count {{
        color: #888;
        font-size: 0.85rem;
        margin-bottom: 1.5rem;
    }}
    .card {{
        background: #161616;
        border: 1px solid #2a2a2a;
        border-radius: 12px;
        margin-bottom: 2rem;
        overflow: hidden;
    }}
    .card-header {{
        padding: 1.25rem 1.5rem;
        border-bottom: 1px solid #2a2a2a;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
    }}
    .title-block {{
        min-width: 0;
    }}
    .card-header h2 {{
        font-size: 1.1rem;
        color: #fff;
        margin-bottom: 0.25rem;
    }}
    .card-number {{
        color: #2563eb;
        font-weight: 700;
        margin-right: 0.3rem;
    }}
    .filename {{
        font-size: 0.75rem;
        color: #666;
        font-family: monospace;
    }}
    .status-badge {{
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 0.35rem 0.7rem;
        white-space: nowrap;
    }}
    .status-badge.passed {{
        background: #14301f;
        color: #7ce5a4;
    }}
    .status-badge.needs-human-review {{
        background: #382515;
        color: #ffbe74;
    }}
    .status-badge.pending-review {{
        background: #2a2a2a;
        color: #c9c9c9;
    }}
    .card-body {{
        display: flex;
        align-items: stretch;
    }}
    .images {{
        display: flex;
        gap: 1.5rem;
        padding: 1.5rem;
        background: #111;
        justify-content: center;
        align-items: flex-start;
        flex-wrap: wrap;
        flex-shrink: 0;
    }}
    .sidebar {{
        flex: 1;
        min-width: 300px;
        overflow-y: auto;
        border-left: 1px solid #2a2a2a;
    }}
    .img-col {{
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.75rem;
        flex-shrink: 0;
    }}
    .img-wrapper {{
        position: relative;
        flex-shrink: 0;
    }}
    .img-wrapper img {{
        max-height: 500px;
        width: auto;
        border-radius: 8px;
        display: block;
    }}
    .ratio-label {{
        position: absolute;
        top: 8px;
        left: 8px;
        background: rgba(0,0,0,0.7);
        color: #fff;
        font-size: 0.8rem;
        padding: 3px 10px;
        border-radius: 4px;
        font-family: monospace;
        font-weight: 600;
    }}
    .img-missing {{
        width: 200px;
        height: 300px;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .placeholder {{
        color: #555;
        font-size: 0.85rem;
        text-align: center;
        border: 1px dashed #333;
        border-radius: 8px;
        padding: 2rem;
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .decision-buttons {{
        display: flex;
        gap: 0.4rem;
    }}
    .decision-buttons button {{
        border: 1px solid #333;
        border-radius: 6px;
        padding: 0.35rem 0.75rem;
        font-size: 0.8rem;
        font-weight: 600;
        cursor: pointer;
        background: #1a1a1a;
        color: #999;
        transition: all 0.15s;
    }}
    .decision-buttons button:hover {{
        border-color: #555;
        color: #ddd;
    }}
    .decision-buttons button.active-approve {{
        background: #14301f;
        color: #7ce5a4;
        border-color: #7ce5a4;
    }}
    .decision-buttons button.active-edit {{
        background: #382515;
        color: #ffbe74;
        border-color: #ffbe74;
    }}
    .decision-buttons button.active-reject {{
        background: #301414;
        color: #e57c7c;
        border-color: #e57c7c;
    }}
    .item-notes {{
        width: 100%;
        max-width: 320px;
        min-height: 40px;
        background: #111;
        border: 1px solid #2a2a2a;
        border-radius: 6px;
        color: #e0e0e0;
        padding: 0.5rem;
        font-family: inherit;
        font-size: 0.8rem;
        resize: vertical;
        display: none;
    }}
    .item-notes.visible {{
        display: block;
    }}
    .item-notes:focus {{
        outline: none;
        border-color: #444;
    }}
    .review-group {{
        border-bottom: 1px solid #2a2a2a;
    }}
    .group-label {{
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-weight: 700;
        padding: 0.6rem 1rem 0;
        margin: 0;
    }}
    .image-label {{
        color: #66a;
    }}
    .copy-label {{
        color: #a86;
    }}
    .review-section {{
        padding: 0.75rem 1rem;
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }}
    .review-block {{
        background: #111;
        border: 1px solid #242424;
        border-radius: 10px;
        padding: 1rem;
    }}
    .review-block h3 {{
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #888;
        margin-bottom: 0.6rem;
    }}
    ul {{
        list-style: disc;
        padding-left: 1rem;
    }}
    li {{
        color: #ddd;
        font-size: 0.85rem;
        line-height: 1.5;
        margin-bottom: 0.35rem;
    }}
    .empty {{
        color: #666;
        font-size: 0.85rem;
        line-height: 1.5;
    }}
    .copy-section {{
        padding: 1rem;
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }}
    .copy-block h3 {{
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #888;
        margin-bottom: 0.5rem;
    }}
    .primary-text {{
        font-size: 0.95rem;
        line-height: 1.6;
        white-space: pre-wrap;
    }}
    .headline-text {{
        font-size: 1.1rem;
        font-weight: 600;
        color: #fff;
    }}
</style>
</head>
<body>
    <div class="top-bar">
        <div class="top-bar-inner">
            <div>
                <h1>Ad Review \u2014 {html.escape(title)}</h1>
                <p class="subtitle">{html.escape(subtitle)}</p>
            </div>
            <div class="summary-counts">
                <span class="count count-total" id="count-total">0 total</span>
                <span class="count count-approved" id="count-approved">0 approved</span>
                <span class="count count-edit" id="count-edit">0 edit</span>
                <span class="count count-rejected" id="count-rejected">0 rejected</span>
                <span class="count count-unreviewed" id="count-unreviewed">0 unreviewed</span>
            </div>
            <div class="top-actions">
                <button class="btn-export" onclick="exportDecisions()">Export JSON</button>
                <button class="btn-clear" onclick="clearAll()">Clear All</button>
            </div>
        </div>
    </div>
    {body_html}
<script>
const BATCH = {json.dumps(storage_key)};
const STORAGE_KEY = 'ad-review-' + BATCH;

function loadState() {{
    try {{
        return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {{}};
    }} catch (e) {{
        return {{}};
    }}
}}

function saveState(state) {{
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}}

function setDecision(key, decision, btn) {{
    const state = loadState();
    if (state[key] && state[key].decision === decision) {{
        delete state[key];
    }} else {{
        state[key] = state[key] || {{}};
        state[key].decision = decision;
    }}
    saveState(state);
    renderAll();
}}

function saveNotes(textarea) {{
    const key = textarea.dataset.key;
    const state = loadState();
    if (!state[key]) state[key] = {{}};
    state[key].notes = textarea.value;
    saveState(state);
}}

function renderAll() {{
    const state = loadState();
    document.querySelectorAll('.img-col').forEach(col => {{
        const key = col.dataset.key;
        if (!key) return;
        const entry = state[key] || {{}};
        const decision = entry.decision || '';
        col.querySelectorAll('.decision-buttons button').forEach(btn => {{
            btn.className = btn.className.replace(/active-\\w+/g, '').trim();
        }});
        if (decision) {{
            const btnClass = 'active-' + decision;
            const btnSelector = '.btn-' + decision;
            const activeBtn = col.querySelector(btnSelector);
            if (activeBtn) activeBtn.classList.add(btnClass);
        }}
        const notes = col.querySelector('.item-notes');
        if (notes) {{
            const showNotes = decision === 'edit' || decision === 'reject' || (entry.notes && entry.notes.trim());
            notes.classList.toggle('visible', showNotes);
            if (entry.notes !== undefined) notes.value = entry.notes;
        }}
    }});
    const allCols = document.querySelectorAll('.img-col[data-key]');
    let approved = 0, edit = 0, rejected = 0, unreviewed = 0;
    allCols.forEach(col => {{
        const key = col.dataset.key;
        const d = (state[key] || {{}}).decision || '';
        if (d === 'approve') approved++;
        else if (d === 'edit') edit++;
        else if (d === 'reject') rejected++;
        else unreviewed++;
    }});
    document.getElementById('count-total').textContent = allCols.length + ' total';
    document.getElementById('count-approved').textContent = approved + ' approved';
    document.getElementById('count-edit').textContent = edit + ' edit';
    document.getElementById('count-rejected').textContent = rejected + ' rejected';
    document.getElementById('count-unreviewed').textContent = unreviewed + ' unreviewed';
}}

function exportDecisions() {{
    const state = loadState();
    const decisions = [];
    document.querySelectorAll('.img-col[data-key]').forEach((col, i) => {{
        const key = col.dataset.key;
        const entry = state[key] || {{}};
        const parts = key.split('__');
        decisions.push({{
            number: col.closest('.card').querySelector('.card-number').textContent.replace('#','') + (parts[1] === '9x16' ? 'a' : 'b'),
            ad_name: parts[0],
            ratio: parts[1],
            decision: entry.decision || 'unreviewed',
            notes: entry.notes || ''
        }});
    }});
    const output = {{
        batch: BATCH,
        timestamp: new Date().toISOString(),
        decisions: decisions
    }};
    const blob = new Blob([JSON.stringify(output, null, 2)], {{ type: 'application/json' }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'review-decisions-' + BATCH + '.json';
    a.click();
    URL.revokeObjectURL(url);
}}

function clearAll() {{
    if (!confirm('Clear all decisions? This cannot be undone.')) return;
    localStorage.removeItem(STORAGE_KEY);
    document.querySelectorAll('.item-notes').forEach(t => t.value = '');
    renderAll();
}}

renderAll();
</script>
</body>
</html>"""

    out_path.write_text(html_doc)
    print(f"Saved: {out_path}")


def build_html(folder_arg: str) -> None:
    folder = Path(folder_arg).resolve()
    name = folder.name
    cards_html, ad_count = build_cards_for_folder(folder)
    render_page(
        title=name,
        subtitle=f"{ad_count} creatives",
        body_html="".join(cards_html),
        out_path=folder / "review.html",
        storage_key=name,
    )
    print(f"{ad_count} ads")


def build_combined_html(folder_args: list[str]) -> None:
    all_sections: list[str] = []
    total_ads = 0
    card_offset = 0

    for folder_arg in sorted(folder_args):
        folder = Path(folder_arg).resolve()
        section_name = folder.name
        cards_html, ad_count = build_cards_for_folder(folder, card_offset)
        card_offset += ad_count
        total_ads += ad_count

        all_sections.append(
            f'<div class="set-section">'
            f'<h2 class="set-heading">{html.escape(section_name.replace("_", " ").title())}</h2>'
            f'<p class="set-count">{ad_count} creatives</p>'
            f'{"".join(cards_html)}'
            f'</div>'
        )

    parent = Path(folder_args[0]).resolve().parent
    title = parent.name
    render_page(
        title=title,
        subtitle=f"{total_ads} creatives across {len(folder_args)} sets",
        body_html="".join(all_sections),
        out_path=parent / "review.html",
        storage_key=title,
    )
    print(f"{total_ads} ads across {len(folder_args)} sets")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/build-review-html.py <ads-folder> [<ads-folder> ...]")
        sys.exit(1)
    if len(sys.argv) > 2:
        build_combined_html(sys.argv[1:])
    else:
        build_html(sys.argv[1])
