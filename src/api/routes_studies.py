"""Typed aggregate-only research study endpoints."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.paths import project_root
from src.research.contracts import StudyValidationError, load_study_spec, validate_study_spec
from src.research.assistant import draft_study
from src.research.publication import verify_study_package
from src.research.study_service import preview_study, publish_run, run_status, run_study

router = APIRouter(prefix="/studies", tags=["studies"])
STUDY_DIR = project_root() / "configs" / "studies"


class StudyRequest(BaseModel):
    study_name: str
    minimum_age: int | None = None
    care_unit: str | None = None
    expected_dataset_snapshot: str | None = None


class StudyQuestion(BaseModel):
    question: str


def _spec(request: StudyRequest):
    name = request.study_name
    if not name.replace("_", "").isalnum():
        raise HTTPException(status_code=422, detail={"code": "invalid_study_name", "field": "study_name"})
    path = STUDY_DIR / f"{name}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail={"code": "unknown_study", "field": "study_name"})
    try:
        spec = load_study_spec(path)
        spec = replace(spec, minimum_age=request.minimum_age if request.minimum_age is not None else spec.minimum_age, care_unit=request.care_unit if request.care_unit else None)
        validate_study_spec(spec)
        return spec
    except StudyValidationError as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_study", "message": str(exc)}) from exc


@router.get("")
def list_studies() -> dict[str, list[str]]:
    return {"studies": sorted(path.stem for path in STUDY_DIR.glob("*.yaml"))}


@router.post("/assistant/draft")
def draft(request: StudyQuestion) -> dict[str, object]:
    """Draft a typed study interpretation; it never executes a query or study."""
    return draft_study(request.question)


@router.post("/validate")
def validate(request: StudyRequest) -> dict[str, object]:
    spec = _spec(request)
    return {"status": "validated", "study_id": spec.study_id, "definition_hash": spec.definition_hash}


@router.post("/preview")
def preview(request: StudyRequest) -> dict[str, object]:
    from src.api.main import get_config

    try:
        return preview_study(get_config(), _spec(request))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "study_unavailable", "message": str(exc)}) from exc


@router.post("/run")
def run(request: StudyRequest) -> dict[str, object]:
    from src.api.main import get_config

    try:
        config = get_config()
        spec = _spec(request)
        actual_snapshot = preview_study(config, spec)["dataset_snapshot"]
        if request.expected_dataset_snapshot and request.expected_dataset_snapshot != actual_snapshot:
            raise HTTPException(status_code=409, detail={"code": "stale_dataset_snapshot"})
        result = run_study(config, spec)
        return {"run_id": result["run_id"], "status": result["manifest"]["status"], "evaluation": result["evaluation"]}
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail={"code": "study_failed", "message": str(exc)}) from exc


@router.post("/runs/{run_id}/publish")
def publish(run_id: str) -> dict[str, object]:
    from src.api.main import get_config

    if not run_id.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(status_code=422, detail={"code": "invalid_run_id"})
    try:
        package = publish_run(get_config(), run_id)
        return {"run_id": run_id, "status": "published", "package": package.name, "verification": verify_study_package(package)}
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"code": "publish_failed", "message": str(exc)}) from exc


@router.get("/runs/{run_id}")
def status(run_id: str) -> dict[str, object]:
    from src.api.main import get_config

    if not run_id.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(status_code=422, detail={"code": "invalid_run_id"})
    try:
        return run_status(get_config(), run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": "unknown_run"}) from exc
