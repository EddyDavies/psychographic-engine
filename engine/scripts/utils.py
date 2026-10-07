from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parent.parent))
ENV_PATH = PROJECT_ROOT / ".env"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
IMAGE_MODEL = "google/gemini-3.1-flash-image-preview"
IMAGE_SIZE = "1K"
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
DELAY_BETWEEN_IMAGES = 3
RETRY_ATTEMPTS = 3
RETRY_DELAY = 5

RECOMPOSE_PROMPTS = {
    "9:16": (
        "Recompose this image for vertical portrait (9:16) format. "
        "Keep everything exactly as it is, including products, text overlays, logos, "
        "and the overall visual feel. Do not cut off any product or copy."
    ),
    "1:1": (
        "Recompose this image for square (1:1) format. "
        "Keep everything exactly as it is, including products, text overlays, logos, "
        "and the overall visual feel. Do not cut off any product or copy."
    ),
}

_ENV_CACHE: dict[str, str] | None = None


def load_env_file(path: Path = ENV_PATH) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    return values


def get_env(name: str, default: str | None = None) -> str | None:
    global _ENV_CACHE
    if _ENV_CACHE is None:
        _ENV_CACHE = load_env_file()
    return os.environ.get(name) or _ENV_CACHE.get(name, default)


def require_env(name: str) -> str:
    value = get_env(name)
    if value:
        return value
    raise RuntimeError(f"{name} not found in environment or {ENV_PATH}")


def image_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    return "image/jpeg"


def encode_image(path: str | Path) -> str:
    file_path = Path(path)
    encoded = base64.b64encode(file_path.read_bytes()).decode()
    return f"data:{image_mime_type(file_path)};base64,{encoded}"


def extract_image_bytes(result: dict) -> bytes | None:
    choices = result.get("choices", [])
    if not choices:
        return None

    message = choices[0].get("message", {})
    images = message.get("images", [])
    for image in images:
        url = image.get("image_url", {}).get("url", "")
        if url.startswith("data:image"):
            return base64.b64decode(url.split(",", 1)[1])

    content = message.get("content", "")
    if isinstance(content, list):
        for block in content:
            if block.get("type") != "image_url":
                continue
            url = block.get("image_url", {}).get("url", "")
            if url.startswith("data:image"):
                return base64.b64decode(url.split(",", 1)[1])

    if isinstance(content, str) and len(content) > 100 and not content.startswith("{"):
        try:
            payload = content.split(",", 1)[1] if content.startswith("data:image") else content
            return base64.b64decode(payload)
        except Exception:
            return None

    return None


def openrouter_headers(api_key: str | None = None) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key or require_env('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/client-customer-psychographics",
        "X-OpenRouter-Title": "Client Customer Psychographics",
    }


def recompose(
    data_url: str,
    aspect_ratio: str,
    api_key: str | None = None,
    model: str = IMAGE_MODEL,
) -> bytes | None:
    import httpx

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": RECOMPOSE_PROMPTS[aspect_ratio]},
                ],
            }
        ],
        "modalities": ["image", "text"],
        "image_config": {
            "aspect_ratio": aspect_ratio,
            "image_size": IMAGE_SIZE,
        },
    }

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            response = httpx.post(
                OPENROUTER_URL,
                json=payload,
                headers=openrouter_headers(api_key),
                timeout=180,
            )
            response.raise_for_status()
            image_bytes = extract_image_bytes(response.json())
            if image_bytes:
                return image_bytes
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429 and attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY * attempt)
                continue
            raise
        except httpx.HTTPError:
            if attempt >= RETRY_ATTEMPTS:
                raise

        time.sleep(RETRY_DELAY)

    return None


DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def load_manifest(manifest_path: Path) -> list[dict]:
    return json.loads(manifest_path.read_text())


def get_drive_service():
    """Build a Drive v3 service.

    On Cloud Run (or when GOOGLE_APPLICATION_CREDENTIALS points to a SA key),
    uses Application Default Credentials.  Locally without a SA key, falls back
    to the interactive OAuth consent flow using GOOGLE_CLIENT_ID / SECRET so
    that `ad_set_builder.py --upload` keeps working for the team.
    """
    from googleapiclient.discovery import build
    import google_auth_httplib2
    import httplib2

    creds = _resolve_drive_credentials()
    http = google_auth_httplib2.AuthorizedHttp(creds, http=httplib2.Http(timeout=300))
    return build("drive", "v3", http=http)


_DRIVE_TOKEN_PATH = PROJECT_ROOT / ".gdrive-token.json"


def _resolve_drive_credentials():
    """Try ADC first, then fall back to interactive OAuth."""
    import google.auth
    from google.auth.exceptions import DefaultCredentialsError

    # 1. Try Application Default Credentials (Cloud Run SA, SA key file, gcloud ADC)
    try:
        creds, _ = google.auth.default(scopes=DRIVE_SCOPES)
        return creds
    except DefaultCredentialsError:
        pass

    # 2. Fall back to interactive OAuth (local dev)
    client_id = get_env("GOOGLE_CLIENT_ID")
    client_secret = get_env("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "Drive credentials not found. Either:\n"
            "  - Set GOOGLE_APPLICATION_CREDENTIALS to a service account key with Drive access, or\n"
            "  - Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env for interactive OAuth, or\n"
            "  - Run: gcloud auth application-default login --scopes=https://www.googleapis.com/auth/drive.file"
        )

    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if _DRIVE_TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(_DRIVE_TOKEN_PATH), DRIVE_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_config = {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost"],
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, DRIVE_SCOPES)
            creds = flow.run_local_server(port=0)
        _DRIVE_TOKEN_PATH.write_text(creds.to_json())

    return creds


DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
TOKEN_PATH = PROJECT_ROOT / ".gdrive-token.json"


def get_google_credentials(scopes: list[str] | None = None) -> "Credentials":
    """Authenticate with the requested Drive scopes and return credentials."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    requested_scopes = scopes or DRIVE_SCOPES

    creds = None
    if TOKEN_PATH.exists():
        stored = Credentials.from_authorized_user_file(str(TOKEN_PATH), requested_scopes)
        if stored.has_scopes(requested_scopes):
            creds = stored

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_config(
                build_google_oauth_client_config(), requested_scopes
            )
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())

    return creds


def get_google_services(scopes: list[str] | None = None) -> tuple["Resource", None]:
    """Authenticate and return (drive_service, None).

    Second element kept for call-site compatibility but is always None.
    """
    from googleapiclient.discovery import build
    import google_auth_httplib2
    import httplib2

    creds = get_google_credentials(scopes)
    http = google_auth_httplib2.AuthorizedHttp(creds, http=httplib2.Http(timeout=300))
    drive = build("drive", "v3", http=http)
    return drive, None


def json_dump(data: object, path: Path) -> None:
    path.write_text(json.dumps(data, indent=2))
