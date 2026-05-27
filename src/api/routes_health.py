"""Health endpoint."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Return API health."""
    return {"status": "ok", "service": "mimic-iv-clinical-data-warehouse"}
