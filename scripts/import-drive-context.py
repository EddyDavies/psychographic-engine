#!/usr/bin/env python3
"""Import shared Google Drive context into the repo knowledge base."""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import shlex
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

try:
    from googleapiclient.errors import HttpError
except ModuleNotFoundError:
    class HttpError(Exception):
        """Fallback so --help works without optional Google dependencies."""

from utils import PROJECT_ROOT, get_google_services

DRIVE_IMPORT_SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly",
]

FOLDER_MIME = "application/vnd.google-apps.folder"
SHORTCUT_MIME = "application/vnd.google-apps.shortcut"
GOOGLE_EXPORTS = {
    "application/vnd.google-apps.document": {
        "export_mime": "text/plain",
        "suffix": ".md",
        "mode": "markdown",
    },
    "application/vnd.google-apps.presentation": {
        "export_mime": "text/plain",
        "suffix": ".md",
        "mode": "markdown",
    },
    "application/vnd.google-apps.spreadsheet": {
        "export_mime": "text/csv",
        "suffix": ".csv",
        "mode": "bytes",
        "note": "Google Sheets exports only the first tab when saved as CSV.",
    },
    "application/vnd.google-apps.drawing": {
        "export_mime": "image/png",
        "suffix": ".png",
        "mode": "bytes",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import a shared Google Drive folder into the repo knowledge base"
    )
    parser.add_argument(
        "--folder",
        required=True,
        help="Drive folder URL or folder ID",
    )
    destination_group = parser.add_mutually_exclusive_group()
    destination_group.add_argument(
        "--client",
        help="Client slug. Imports into clients/{client}/research/drive-imports/",
    )
    destination_group.add_argument(
        "--output-dir",
        help="Explicit output directory. Use instead of --client for ad hoc imports.",
    )
    parser.add_argument(
        "--name",
        help="Override the local folder name used under the output directory.",
    )
    return parser.parse_args()


def parse_drive_folder_id(value: str) -> str:
    candidate = value.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{10,}", candidate):
        return candidate

    parsed = urlparse(candidate)
    if not parsed.netloc:
        raise SystemExit(f"Could not parse Drive folder ID from: {value}")

    path_match = re.search(r"/folders/([A-Za-z0-9_-]+)", parsed.path)
    if path_match:
        return path_match.group(1)

    query_id = parse_qs(parsed.query).get("id")
    if query_id:
        return query_id[0]

    raise SystemExit(f"Could not parse Drive folder ID from: {value}")


def safe_path_component(name: str) -> str:
    cleaned = name.replace("/", "-").replace("\0", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip(".")
    return cleaned or "untitled"


def timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_drive_metadata(service, file_id: str) -> dict:
    return (
        service.files()
        .get(
            fileId=file_id,
            fields=(
                "id,name,mimeType,modifiedTime,webViewLink,size,"
                "shortcutDetails(targetId,targetMimeType)"
            ),
            supportsAllDrives=True,
        )
        .execute()
    )


def list_folder_children(service, folder_id: str) -> list[dict]:
    children: list[dict] = []
    page_token = None
    while True:
        response = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields=(
                    "nextPageToken,"
                    "files(id,name,mimeType,modifiedTime,webViewLink,size,"
                    "shortcutDetails(targetId,targetMimeType))"
                ),
                orderBy="folder,name_natural",
                pageSize=1000,
                pageToken=page_token,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            )
            .execute()
        )
        children.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return children


def resolve_shortcut(service, metadata: dict) -> dict:
    if metadata.get("mimeType") != SHORTCUT_MIME:
        return metadata

    shortcut = metadata.get("shortcutDetails") or {}
    target_id = shortcut.get("targetId")
    if not target_id:
        raise RuntimeError(f"Shortcut {metadata['name']} has no targetId")

    resolved = get_drive_metadata(service, target_id)
    resolved["name"] = metadata["name"]
    resolved["shortcut"] = {
        "id": metadata["id"],
        "mimeType": metadata["mimeType"],
        "webViewLink": metadata.get("webViewLink"),
        "targetId": target_id,
        "targetMimeType": shortcut.get("targetMimeType"),
    }
    return resolved


def exported_text_markdown(metadata: dict, text: str, note: str | None = None) -> str:
    body = text.strip()
    if not body:
        body = "_No text content was returned by Google Drive export._"

    lines = [
        f"# {metadata['name']}",
        "",
        f"Source: {metadata.get('webViewLink', '')}",
        f"Drive ID: {metadata['id']}",
        f"Imported: {timestamp()}",
        f"Original MIME type: {metadata['mimeType']}",
    ]
    if note:
        lines.append(f"Note: {note}")
    if metadata.get("shortcut"):
        lines.append(f"Shortcut source: {metadata['shortcut'].get('webViewLink', '')}")
    lines.extend(["", "## Content", "", body, ""])
    return "\n".join(lines)


def download_request_bytes(request) -> bytes:
    data = request.execute()
    if isinstance(data, bytes):
        return data
    if isinstance(data, str):
        return data.encode("utf-8")
    return bytes(data)


def local_file_path(destination: Path, metadata: dict, suffix: str | None = None) -> Path:
    original = Path(metadata["name"])
    extension = suffix or original.suffix
    if not extension:
        extension = mimetypes.guess_extension(metadata.get("mimeType", "")) or ""
    stem = safe_path_component(original.stem if original.suffix else metadata["name"])
    return destination / f"{stem}--{metadata['id'][:8]}{extension}"


def import_file(service, metadata: dict, destination: Path) -> tuple[str, Path | None, str | None]:
    mime_type = metadata.get("mimeType", "")

    if mime_type.startswith("application/vnd.google-apps.") and mime_type not in GOOGLE_EXPORTS:
        return "skipped", None, f"Unsupported Google Workspace type: {mime_type}"

    if mime_type in GOOGLE_EXPORTS:
        export_config = GOOGLE_EXPORTS[mime_type]
        payload = download_request_bytes(
            service.files().export_media(
                fileId=metadata["id"], mimeType=export_config["export_mime"]
            )
        )
        output_path = local_file_path(destination, metadata, export_config["suffix"])
        if export_config["mode"] == "markdown":
            output_path.write_text(
                exported_text_markdown(
                    metadata,
                    payload.decode("utf-8", errors="replace"),
                    export_config.get("note"),
                )
            )
        else:
            output_path.write_bytes(payload)
        return "imported", output_path, export_config.get("note")

    payload = download_request_bytes(service.files().get_media(fileId=metadata["id"]))
    output_path = local_file_path(destination, metadata)
    output_path.write_bytes(payload)
    return "imported", output_path, None


def import_folder(
    service,
    folder_meta: dict,
    destination: Path,
    import_root: Path,
    manifest: list[dict],
) -> None:
    destination.mkdir(parents=True, exist_ok=True)

    for child in list_folder_children(service, folder_meta["id"]):
        try:
            metadata = resolve_shortcut(service, child)
            if metadata["mimeType"] == FOLDER_MIME:
                child_dir = destination / safe_path_component(metadata["name"])
                import_folder(service, metadata, child_dir, import_root, manifest)
                continue

            status, output_path, note = import_file(service, metadata, destination)
            relative_path = str(output_path.relative_to(import_root)) if output_path else None
            manifest.append(
                {
                    "name": metadata["name"],
                    "id": metadata["id"],
                    "mime_type": metadata["mimeType"],
                    "source_url": metadata.get("webViewLink"),
                    "status": status,
                    "path": relative_path,
                    "note": note,
                    "shortcut": metadata.get("shortcut"),
                }
            )
            if output_path:
                print(f"{status:8} {output_path}")
            else:
                print(f"{status:8} {metadata['name']} ({note})")
        except HttpError as exc:
            manifest.append(
                {
                    "name": child["name"],
                    "id": child["id"],
                    "mime_type": child["mimeType"],
                    "source_url": child.get("webViewLink"),
                    "status": "error",
                    "path": None,
                    "note": f"{exc.resp.status}: {exc.reason}",
                    "shortcut": None,
                }
            )
            print(f"error    {child['name']} ({exc.resp.status}: {exc.reason})")


def render_import_readme(
    folder_meta: dict,
    destination: Path,
    manifest: list[dict],
    command: str,
) -> str:
    counts = Counter(entry["status"] for entry in manifest)
    lines = [
        f"# Drive Import: {folder_meta['name']}",
        "",
        f"Source: {folder_meta.get('webViewLink', '')}",
        f"Drive folder ID: {folder_meta['id']}",
        f"Imported at: {timestamp()}",
        f"Local path: {destination}",
        "",
        "This directory is a raw mirror of shared Google Drive context.",
        "Promote distilled content into the normal client folders once it has been cleaned up.",
        "Reruns overwrite matching Drive IDs but do not prune files removed from Drive.",
        "",
        "## Summary",
        "",
        f"- Imported files: {counts.get('imported', 0)}",
        f"- Skipped files: {counts.get('skipped', 0)}",
        f"- Errors: {counts.get('error', 0)}",
        "",
        "## Re-run",
        "",
        "```bash",
        command,
        "```",
        "",
        "## Manifest",
        "",
        "- `manifest.json` contains the source IDs, URLs, statuses, and local paths.",
        "",
    ]
    return "\n".join(lines)


def resolve_destination(args: argparse.Namespace, folder_meta: dict) -> Path:
    if args.output_dir:
        base_dir = Path(args.output_dir).expanduser().resolve()
    elif args.client:
        client_dir = PROJECT_ROOT / "clients" / args.client
        if not client_dir.exists():
            raise SystemExit(f"Client directory not found: {client_dir}")
        base_dir = client_dir / "research" / "drive-imports"
    else:
        raise SystemExit("Provide either --client or --output-dir")

    folder_name = safe_path_component(args.name or folder_meta["name"])
    return base_dir / folder_name


def main() -> None:
    args = parse_args()
    folder_id = parse_drive_folder_id(args.folder)
    try:
        service, _ = get_google_services(scopes=DRIVE_IMPORT_SCOPES)
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing Google Drive dependencies. Run via "
            "`scripts/run-drive-import.sh` or install "
            "`google-api-python-client`, `google-auth-oauthlib`, and "
            "`google-auth-httplib2`."
        ) from exc
    folder_meta = resolve_shortcut(service, get_drive_metadata(service, folder_id))
    if folder_meta["mimeType"] != FOLDER_MIME:
        raise SystemExit(f"Expected a Drive folder, got {folder_meta['mimeType']}")

    destination = resolve_destination(args, folder_meta)
    destination.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []
    import_folder(service, folder_meta, destination, destination, manifest)

    manifest_path = destination / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    readme_path = destination / "README.md"
    command_parts = [
        "scripts/run-drive-import.sh",
        "--folder",
        folder_id,
    ]
    if args.client:
        command_parts.extend(["--client", args.client])
    else:
        command_parts.extend(["--output-dir", str(destination.parent)])
    if args.name:
        command_parts.extend(["--name", args.name])
    command = " ".join(shlex.quote(part) for part in command_parts)
    readme_path.write_text(render_import_readme(folder_meta, destination, manifest, command))

    counts = Counter(entry["status"] for entry in manifest)
    print("")
    print(f"Imported into: {destination}")
    print(
        f"Summary: {counts.get('imported', 0)} imported, "
        f"{counts.get('skipped', 0)} skipped, {counts.get('error', 0)} errors"
    )


if __name__ == "__main__":
    main()
