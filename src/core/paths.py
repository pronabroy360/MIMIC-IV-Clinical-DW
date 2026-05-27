"""Project path helpers."""

from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    """Return the repository root."""
    return Path(__file__).resolve().parents[2]


def resolve_project_path(path: str | Path | None) -> Path | None:
    """Resolve a path relative to the repository root unless it is absolute."""
    if path is None:
        return None
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    return project_root() / candidate
