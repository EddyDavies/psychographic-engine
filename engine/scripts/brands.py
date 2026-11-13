"""Locate brand folders at the repo root.

A top-level folder is a brand when it holds both `brand/` and `avatars/`.
`engine/` and dot-directories are never brands.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_NOT_BRANDS = {"engine"}


def _is_brand(path: Path) -> bool:
    return (
        path.is_dir()
        and not path.name.startswith(".")
        and path.name not in _NOT_BRANDS
        and (path / "brand").is_dir()
        and (path / "avatars").is_dir()
    )


def find_brands(root: Path = REPO_ROOT) -> list[Path]:
    """Return every brand folder directly under root, sorted by name."""
    return sorted(path for path in root.iterdir() if _is_brand(path))


def brand_dir(name: str) -> Path:
    """Return REPO_ROOT/name, or exit with the list of known brands."""
    path = REPO_ROOT / name
    if _is_brand(path):
        return path
    found = ", ".join(p.name for p in find_brands()) or "none"
    raise SystemExit(
        f"Error: '{name}' is not a brand folder (needs brand/ and avatars/ under {path}). "
        f"Brands found: {found}"
    )
