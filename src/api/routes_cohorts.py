"""Cohort summary endpoints."""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException

from src.core.db import connect
from src.core.paths import project_root

router = APIRouter(prefix="/cohorts", tags=["cohorts"])


COHORT_DIR = project_root() / "sql" / "cohorts"


@router.get("")
def list_cohorts() -> dict[str, list[str]]:
    """List available cohort SQL templates."""
    return {"cohorts": sorted(path.stem for path in COHORT_DIR.glob("*.sql"))}


@router.get("/{cohort_name}/summary")
def cohort_summary(cohort_name: str) -> dict[str, object]:
    """Execute a privacy-safe aggregate cohort SQL template."""
    from src.api.main import get_config

    if not re.fullmatch(r"[a-zA-Z0-9_]+", cohort_name):
        raise HTTPException(status_code=400, detail="Invalid cohort name")
    path = COHORT_DIR / f"{cohort_name}.sql"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Unknown cohort")
    with connect(get_config()) as con:
        rows = con.execute(path.read_text()).fetchdf().to_dict(orient="records")
    return {"cohort": cohort_name, "summary": rows}
