"""Typed contracts for reproducible, aggregate-only research studies."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from src.core.paths import project_root
from src.research.tasks import task_definition


class StudyValidationError(ValueError):
    """A study definition violates a supported research contract."""


@dataclass(frozen=True)
class StudySpec:
    """Narrow, versioned study contract accepted by the local study service."""

    study_id: str
    question: str
    minimum_age: int
    first_stay: str
    care_unit: str | None
    require_alive_at_prediction: bool
    require_in_icu_at_prediction: bool
    horizon_hours: int
    require_available_by_prediction: bool
    unknown_availability: str
    task_name: str
    task_version: int
    feature_set: str
    registry_version: int
    seed: int
    proportions: tuple[float, float, float]
    cv_folds: int
    cv_repeats: int
    publication_minimum_cell_count: int
    required_origin: str

    def canonical_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def definition_hash(self) -> str:
        payload = json.dumps(self.canonical_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


def load_study_spec(path: str | Path) -> StudySpec:
    """Load and validate the supported subset of the study YAML schema."""
    raw = yaml.safe_load(Path(path).read_text()) or {}
    if raw.get("schema_version") != 1:
        raise StudyValidationError("schema_version must be 1")
    cohort = raw.get("cohort") or {}
    prediction = raw.get("prediction") or {}
    task = raw.get("task") or {}
    features = raw.get("features") or {}
    evaluation = raw.get("evaluation") or {}
    publication = raw.get("publication") or {}
    dataset = raw.get("dataset") or {}
    proportions = tuple(float(value) for value in evaluation.get("proportions", []))
    spec = StudySpec(
        study_id=str(raw.get("study_id", "")),
        question=str(raw.get("question", "")),
        minimum_age=int(cohort.get("minimum_age", 0)),
        first_stay=str(cohort.get("first_stay", "")),
        care_unit=str(cohort["care_unit"]) if cohort.get("care_unit") else None,
        require_alive_at_prediction=bool(cohort.get("require_alive_at_prediction")),
        require_in_icu_at_prediction=bool(cohort.get("require_in_icu_at_prediction")),
        horizon_hours=int(prediction.get("horizon_hours", 0)),
        require_available_by_prediction=bool(prediction.get("require_available_by_prediction")),
        unknown_availability=str(prediction.get("unknown_availability", "")),
        task_name=str(task.get("name", "")),
        task_version=int(task.get("version", 0)),
        feature_set=str(features.get("set", "")),
        registry_version=int(features.get("registry_version", 0)),
        seed=int(evaluation.get("seed", 0)),
        proportions=proportions,  # type: ignore[arg-type]
        cv_folds=int((evaluation.get("cv") or {}).get("folds", 0)),
        cv_repeats=int((evaluation.get("cv") or {}).get("repeats", 0)),
        publication_minimum_cell_count=int(publication.get("minimum_cell_count", 0)),
        required_origin=str(dataset.get("required_origin", "")),
    )
    validate_study_spec(spec)
    _validate_feature_registry(spec)
    return spec


def _validate_feature_registry(spec: StudySpec) -> None:
    """Ensure the checked-in registry agrees with the executable task contract."""
    registry_path = project_root() / "configs/research/prospective_feature_registry.yaml"
    registry = yaml.safe_load(registry_path.read_text()) or {}
    task = task_definition(spec.task_name)
    registry_features = {str(feature.get("name")) for feature in registry.get("features", [])}
    required_measurements = {
        name for name in task.numeric_features
        if name not in {"age_at_admission", "chart_event_count_24h", "lab_event_count_24h"}
    }
    issues: list[str] = []
    if registry.get("version") != spec.registry_version:
        issues.append("feature registry version does not match the study definition")
    if registry.get("feature_set") != spec.feature_set:
        issues.append("feature registry set does not match the study definition")
    if registry.get("task") != spec.task_name:
        issues.append("feature registry task does not match the study definition")
    if not required_measurements.issubset(registry_features):
        issues.append("feature registry omits an executable prospective measurement")
    if issues:
        raise StudyValidationError("; ".join(issues))


def validate_study_spec(spec: StudySpec) -> None:
    """Reject unsupported choices before database execution."""
    issues: list[str] = []
    if not spec.study_id or not spec.question:
        issues.append("study_id and question are required")
    if spec.minimum_age < 18:
        issues.append("minimum_age must be at least 18")
    if spec.first_stay != "first_icu_per_patient":
        issues.append("only first_icu_per_patient is supported")
    if spec.care_unit is not None and (len(spec.care_unit) > 80 or not all(char.isalnum() or char in " _-/" for char in spec.care_unit)):
        issues.append("care_unit contains unsupported characters")
    if spec.horizon_hours != 24:
        issues.append("only a 24-hour prediction horizon is supported")
    if not spec.require_alive_at_prediction:
        issues.append("the supported prospective study requires survival at prediction time")
    if not spec.require_in_icu_at_prediction:
        issues.append("the supported prospective study requires ICU presence at prediction time")
    if not spec.require_available_by_prediction or spec.unknown_availability != "exclude":
        issues.append("prospective features require known availability by prediction time")
    if spec.task_name != "death_after_prediction_before_hospital_discharge" or spec.task_version != 1:
        issues.append("unsupported task definition")
    if spec.feature_set != "prospective_icu_24h_v1" or spec.registry_version != 3:
        issues.append("unsupported prospective feature registry")
    if len(spec.proportions) != 3 or abs(sum(spec.proportions) - 1.0) > 1e-9:
        issues.append("evaluation proportions must contain three values summing to 1")
    if spec.cv_folds < 2 or spec.cv_repeats < 1:
        issues.append("cross-validation needs at least two folds and one repeat")
    if spec.publication_minimum_cell_count < 1:
        issues.append("publication minimum cell count must be positive")
    if spec.required_origin != "synthetic_invented":
        issues.append("this local study service accepts invented synthetic data only")
    if issues:
        raise StudyValidationError("; ".join(issues))
