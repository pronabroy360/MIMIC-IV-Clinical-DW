"""Versioned, inspectable rules for the synthetic research workshop."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd
import yaml

from src.core.paths import project_root


def _read(name: str) -> dict:
    path = project_root() / "configs" / "research" / name
    return yaml.safe_load(path.read_text()) or {}


@lru_cache(maxsize=1)
def feature_definitions() -> dict:
    return _read("feature_definitions.yaml")


@lru_cache(maxsize=1)
def leakage_rules() -> dict:
    return _read("leakage_exclusions.yaml")


@lru_cache(maxsize=1)
def plausibility_ranges() -> dict:
    return _read("plausibility_ranges.yaml")


def feature_names(kind: str) -> tuple[str, ...]:
    return tuple(item["name"] for item in feature_definitions()[kind])


def predictor_sources() -> dict[str, str]:
    return {
        item["name"]: item["source"]
        for kind in ("numeric", "categorical")
        for item in feature_definitions()[kind]
    }


def predictor_availability() -> dict[str, str]:
    return {
        item["name"]: item["availability"]
        for kind in ("numeric", "categorical")
        for item in feature_definitions()[kind]
    }


def validate_research_frame(frame: pd.DataFrame) -> None:
    """Reject incorrect grain, leakage, timing, or invented-value range failures."""
    rules = leakage_rules()
    predictors = set(feature_names("numeric") + feature_names("categorical"))
    forbidden = set(rules["forbidden_predictors"])
    if predictors & forbidden:
        raise AssertionError("A forbidden audit field entered the predictor configuration")
    if frame["subject_id"].duplicated().any():
        raise AssertionError("Research model table must have one index admission per patient")
    if not (frame["prediction_time"] <= frame["index_dischtime"]).all():
        raise AssertionError("Prediction time must precede index discharge")
    death_rows = frame["in_hospital_mortality_flag"] == 1
    if frame.loc[death_rows, "urgent_readmitted_30d"].notna().any():
        raise AssertionError("Readmission target must be null for index deaths")
    for name, (lower, upper) in plausibility_ranges()["numeric"].items():
        values = frame[name].dropna()
        if not values.between(lower, upper).all():
            raise AssertionError(f"Synthetic plausibility range failed for {name}")
