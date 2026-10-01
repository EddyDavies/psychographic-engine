#!/usr/bin/env python3
"""Sync local knowledge base to R2 for ad generation."""

import argparse
import time
from pathlib import Path

from r2 import collect_knowledge_files, sync_knowledge
from utils import PROJECT_ROOT


def build_snapshot(client_dir: Path, prompts_dir: Path, client_name: str) -> dict[str, tuple[int, int]]:
    snapshot: dict[str, tuple[int, int]] = {}
    for key, path in collect_knowledge_files(client_dir, prompts_dir, client_name).items():
        stat = path.stat()
        snapshot[key] = (stat.st_mtime_ns, stat.st_size)
    return snapshot


def main():
    parser = argparse.ArgumentParser(description="Sync knowledge base to R2")
    parser.add_argument("--client", required=True, help="Client name (e.g. acme)")
    parser.add_argument("--bucket", help="Override target R2 bucket")
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete remote knowledge files that no longer exist locally",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without uploading or deleting anything",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch the local knowledge and prompt files and sync on changes",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Polling interval in seconds when --watch is enabled",
    )
    args = parser.parse_args()

    client_dir = PROJECT_ROOT / "clients" / args.client
    prompts_dir = PROJECT_ROOT / "prompts"

    if not client_dir.is_dir():
        raise SystemExit(f"Client directory not found: {client_dir}")
    if not prompts_dir.is_dir():
        raise SystemExit(f"Prompts directory not found: {prompts_dir}")

    stats = sync_knowledge(
        client_dir,
        prompts_dir,
        args.client,
        bucket_name=args.bucket,
        delete=args.delete,
        dry_run=args.dry_run,
    )
    print(
        f"Sync summary: uploaded={stats['uploaded']} "
        f"deleted={stats['deleted']} unchanged={stats['unchanged']}"
    )

    if not args.watch:
        return

    print(f"Watching knowledge files for {args.client} (interval: {args.interval:.1f}s)")
    previous = build_snapshot(client_dir, prompts_dir, args.client)

    try:
        while True:
            time.sleep(args.interval)
            current = build_snapshot(client_dir, prompts_dir, args.client)
            if current == previous:
                continue

            changed = len(set(previous) ^ set(current))
            if not changed:
                changed = sum(1 for key in current if current[key] != previous.get(key))
            print(f"Detected changes in {changed} knowledge file(s); syncing...")
            stats = sync_knowledge(
                client_dir,
                prompts_dir,
                args.client,
                bucket_name=args.bucket,
                delete=args.delete,
                dry_run=args.dry_run,
            )
            print(
                f"Sync summary: uploaded={stats['uploaded']} "
                f"deleted={stats['deleted']} unchanged={stats['unchanged']}"
            )
            previous = current
    except KeyboardInterrupt:
        print("\nStopped watch mode.")


if __name__ == "__main__":
    main()
