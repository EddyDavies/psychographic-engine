from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import boto3

from utils import get_env, require_env

UPLOAD_EXTENSIONS = {".png", ".md", ".json"}
KNOWLEDGE_EXTENSIONS = {".md", ".json", ".jpg", ".jpeg", ".png"}
KNOWLEDGE_DIRS = (
    "angles",
    "avatars",
    "brand",
    "concepts",
    "emails",
    "offers",
    "products",
    "research",
    "strategy",
    "testing",
)

CONTENT_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".json": "application/json",
    ".md": "text/markdown",
}


def get_r2_client():
    account_id = require_env("CF_ACCOUNT_ID")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=require_env("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=require_env("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
    )


def get_bucket_name() -> str:
    return get_env("R2_BUCKET_NAME") or "ad-review"


def _resolve_bucket(bucket_name: str | None) -> str:
    return bucket_name if bucket_name is not None else get_bucket_name()


def _file_md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_etag(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip('"')


def _list_objects(client, bucket_name: str, prefix: str) -> dict[str, dict[str, object]]:
    objects: dict[str, dict[str, object]] = {}
    kwargs: dict[str, object] = {"Bucket": bucket_name, "Prefix": prefix}
    while True:
        response = client.list_objects_v2(**kwargs)
        for item in response.get("Contents") or []:
            key = item["Key"]
            objects[key] = {
                "etag": _normalize_etag(item.get("ETag")),
                "size": int(item.get("Size", 0)),
            }
        if not response.get("IsTruncated"):
            break
        kwargs["ContinuationToken"] = response["NextContinuationToken"]
    return objects


def _delete_keys(client, bucket_name: str, keys: list[str], dry_run: bool = False) -> int:
    if dry_run or not keys:
        return len(keys)
    deleted = 0
    for index in range(0, len(keys), 1000):
        chunk = keys[index : index + 1000]
        client.delete_objects(
            Bucket=bucket_name,
            Delete={"Objects": [{"Key": key} for key in chunk], "Quiet": True},
        )
        deleted += len(chunk)
    return deleted


def _upload_path(client, bucket_name: str, path: Path, key: str, dry_run: bool = False) -> None:
    if dry_run:
        return
    content_type = CONTENT_TYPES.get(path.suffix.lower())
    extra_args = {"ContentType": content_type} if content_type else None
    client.upload_file(str(path), bucket_name, key, ExtraArgs=extra_args)


def upload_batch(batch_dir: Path, bucket_name: str | None = None) -> int:
    bucket_name = _resolve_bucket(bucket_name)
    client = get_r2_client()
    prefix = f"batches/{batch_dir.name}/"
    count = 0
    for file_path in batch_dir.iterdir():
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in UPLOAD_EXTENSIONS:
            continue
        key = f"{prefix}{file_path.name}"
        content_type = CONTENT_TYPES.get(file_path.suffix.lower())
        extra_args = {"ContentType": content_type} if content_type else None
        client.upload_file(str(file_path), bucket_name, key, ExtraArgs=extra_args)
        count += 1
    print(f"Uploaded {count} files to r2://{bucket_name}/{prefix}")
    return count


def _upload_dir(client, bucket_name: str, local_dir: Path, r2_prefix: str, extensions: set[str]) -> int:
    count = 0
    for file_path in local_dir.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in extensions:
            continue
        relative = file_path.relative_to(local_dir)
        key = f"{r2_prefix}/{relative}"
        content_type = CONTENT_TYPES.get(file_path.suffix.lower())
        extra_args = {"ContentType": content_type} if content_type else None
        client.upload_file(str(file_path), bucket_name, key, ExtraArgs=extra_args)
        count += 1
    return count


def _upload_files(client, bucket_name: str, local_dir: Path, r2_prefix: str, extensions: set[str]) -> int:
    count = 0
    for file_path in local_dir.iterdir():
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in extensions:
            continue
        key = f"{r2_prefix}/{file_path.name}"
        content_type = CONTENT_TYPES.get(file_path.suffix.lower())
        extra_args = {"ContentType": content_type} if content_type else None
        client.upload_file(str(file_path), bucket_name, key, ExtraArgs=extra_args)
        count += 1
    return count


def collect_knowledge_files(
    client_dir: Path,
    prompts_dir: Path,
    client_name: str,
) -> dict[str, Path]:
    local_objects: dict[str, Path] = {}

    for file_path in sorted(client_dir.iterdir()):
        if not file_path.is_file() or file_path.suffix.lower() not in KNOWLEDGE_EXTENSIONS:
            continue
        local_objects[f"knowledge/{client_name}/{file_path.name}"] = file_path

    for dirname in KNOWLEDGE_DIRS:
        local_dir = client_dir / dirname
        if not local_dir.is_dir():
            continue
        for file_path in sorted(local_dir.rglob("*")):
            if not file_path.is_file() or file_path.suffix.lower() not in KNOWLEDGE_EXTENSIONS:
                continue
            relative = file_path.relative_to(local_dir).as_posix()
            local_objects[f"knowledge/{client_name}/{dirname}/{relative}"] = file_path

    for file_path in sorted(prompts_dir.rglob("*")):
        if not file_path.is_file() or file_path.suffix.lower() not in KNOWLEDGE_EXTENSIONS:
            continue
        relative = file_path.relative_to(prompts_dir).as_posix()
        local_objects[f"knowledge/prompts/{relative}"] = file_path

    return local_objects


def sync_knowledge(
    client_dir: Path,
    prompts_dir: Path,
    client_name: str,
    bucket_name: str | None = None,
    *,
    delete: bool = False,
    dry_run: bool = False,
) -> dict[str, int]:
    bucket_name = _resolve_bucket(bucket_name)
    client = get_r2_client()
    local_objects = collect_knowledge_files(client_dir, prompts_dir, client_name)
    remote_objects = _list_objects(client, bucket_name, f"knowledge/{client_name}/")
    remote_objects.update(_list_objects(client, bucket_name, "knowledge/prompts/"))

    upload_keys: list[str] = []
    for key, file_path in local_objects.items():
        remote = remote_objects.get(key)
        if remote is None:
            upload_keys.append(key)
            continue
        remote_size = int(remote.get("size", -1))
        remote_etag = _normalize_etag(remote.get("etag"))
        if remote_size != file_path.stat().st_size or remote_etag != _file_md5(file_path):
            upload_keys.append(key)

    delete_keys = sorted(set(remote_objects) - set(local_objects)) if delete else []

    for key in upload_keys:
        _upload_path(client, bucket_name, local_objects[key], key, dry_run=dry_run)

    deleted = _delete_keys(client, bucket_name, delete_keys, dry_run=dry_run)
    skipped = len(local_objects) - len(upload_keys)

    action = "Planned" if dry_run else "Synced"
    print(
        f"{action} knowledge files for r2://{bucket_name}/knowledge/ "
        f"(uploaded: {len(upload_keys)}, deleted: {deleted}, unchanged: {skipped})"
    )

    return {
        "uploaded": len(upload_keys),
        "deleted": deleted,
        "unchanged": skipped,
    }


def upload_knowledge(
    client_dir: Path,
    prompts_dir: Path,
    client_name: str,
    bucket_name: str | None = None,
) -> int:
    stats = sync_knowledge(client_dir, prompts_dir, client_name, bucket_name=bucket_name)
    return stats["uploaded"]


def list_batches(bucket_name: str | None = None) -> list[str]:
    bucket_name = _resolve_bucket(bucket_name)
    client = get_r2_client()
    prefixes: list[str] = []
    kwargs: dict = {"Bucket": bucket_name, "Prefix": "batches/", "Delimiter": "/"}
    while True:
        response = client.list_objects_v2(**kwargs)
        for p in response.get("CommonPrefixes") or []:
            prefixes.append(p["Prefix"].rstrip("/").split("/")[-1])
        if not response.get("IsTruncated"):
            break
        kwargs["ContinuationToken"] = response["NextContinuationToken"]
    return sorted(prefixes)


def write_job_status(status: str, bucket_name: str | None = None, **extra) -> None:
    bucket_name = _resolve_bucket(bucket_name)
    client = get_r2_client()
    payload = {
        "status": status,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        **extra,
    }
    client.put_object(
        Bucket=bucket_name,
        Key="job-status.json",
        Body=json.dumps(payload).encode(),
        ContentType="application/json",
    )
