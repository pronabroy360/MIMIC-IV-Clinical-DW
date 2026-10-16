"""Task-specific target and prospective feature contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskDefinition:
    name: str
    target_column: str
    numeric_features: tuple[str, ...]
    categorical_features: tuple[str, ...]
    excluded_feature_families: tuple[str, ...]


PROSPECTIVE_ICU_MORTALITY = TaskDefinition(
    name="death_after_prediction_before_hospital_discharge",
    target_column="death_after_prediction_flag",
    numeric_features=(
        "age_at_admission", "heart_rate_mean", "sbp_mean", "dbp_mean", "resp_rate_mean",
        "temperature_mean", "spo2_mean", "wbc_mean", "hemoglobin_mean", "platelet_mean",
        "creatinine_mean", "bun_mean", "sodium_mean", "potassium_mean", "glucose_mean",
        "lactate_mean", "chart_event_count_24h", "lab_event_count_24h",
        "vasopressor_first_24h_flag",
    ),
    categorical_features=("gender", "admission_type", "first_careunit"),
    excluded_feature_families=(
        "diagnosis_codes", "procedure_codes", "discharge_outcomes", "whole_stay_summaries",
        "identifiers", "future_events", "site_identifier",
    ),
)


def task_definition(name: str) -> TaskDefinition:
    if name != PROSPECTIVE_ICU_MORTALITY.name:
        raise ValueError(f"Unknown research task: {name}")
    return PROSPECTIVE_ICU_MORTALITY
