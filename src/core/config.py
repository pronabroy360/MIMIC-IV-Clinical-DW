"""YAML configuration loading."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - used only before dependencies are installed
    yaml = None

from src.core.paths import resolve_project_path


@dataclass(frozen=True)
class LLMConfig:
    """LLM assistant safety configuration."""

    allowed_tables: tuple[str, ...] = (
        "gold_patient_summary",
        "gold_admission_summary",
        "gold_icu_stay_summary",
        "gold_first_24h_features",
        "gold_lab_features",
        "gold_vital_features",
        "gold_diagnosis_features",
    )
    default_limit: int = 100


@dataclass(frozen=True)
class WarehouseConfig:
    """Runtime settings for a warehouse pipeline execution."""

    mode: str
    database_path: Path
    raw_data_path: Path | None = None
    public_mode: bool = True
    outputs_private_path: Path = Path("outputs/private")
    outputs_public_path: Path = Path("outputs/public")
    project_id: str | None = None
    hosp_dataset: str | None = None
    icu_dataset: str | None = None
    bronze_schema_policy: str = "lowercase_snake_case"
    pipeline_run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    llm: LLMConfig = field(default_factory=LLMConfig)


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_override(raw: dict[str, Any]) -> dict[str, Any]:
    """Apply optional environment overrides without requiring a .env loader."""
    merged = dict(raw)
    if os.getenv("MIMIC_DATABASE_PATH"):
        merged["database_path"] = os.environ["MIMIC_DATABASE_PATH"]
    if os.getenv("MIMIC_RAW_DATA_PATH"):
        merged["raw_data_path"] = os.environ["MIMIC_RAW_DATA_PATH"]
    if os.getenv("MIMIC_PUBLIC_MODE"):
        merged["public_mode"] = _as_bool(os.environ["MIMIC_PUBLIC_MODE"], True)
    if os.getenv("GOOGLE_CLOUD_PROJECT"):
        merged["project_id"] = os.environ["GOOGLE_CLOUD_PROJECT"]
    return merged


def _minimal_yaml_load(text: str) -> dict[str, Any]:
    """Parse this repo's simple YAML configs if PyYAML is unavailable."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    lines = [line.split("#", 1)[0].rstrip() for line in text.splitlines()]
    for raw_line in lines:
        if not raw_line.strip():
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if line.startswith("- "):
            if isinstance(parent, list):
                parent.append(_coerce_scalar(line[2:].strip()))
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value == "":
            next_container: dict[str, Any] | list[Any] = {}
            if isinstance(parent, dict):
                parent[key] = next_container
            stack.append((indent, next_container))
        else:
            if isinstance(parent, dict):
                parent[key] = _coerce_scalar(value)

        # Convert empty mappings that are followed by list items into lists.
        if stack and isinstance(stack[-1][1], dict):
            maybe_key = key if value == "" else None
            if maybe_key and any(
                next_line.startswith(" " * (indent + 2) + "- ")
                for next_line in lines[lines.index(raw_line) + 1 :]
            ):
                parent[maybe_key] = []
                stack[-1] = (indent, parent[maybe_key])
    return root


def _coerce_scalar(value: str) -> Any:
    value = value.strip().strip('"').strip("'")
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        return value


def load_config(config_path: str | Path) -> WarehouseConfig:
    """Load and normalize a warehouse YAML config."""
    path = Path(config_path)
    if not path.is_absolute():
        resolved = resolve_project_path(path)
        if resolved is not None:
            path = resolved
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    text = path.read_text()
    raw = yaml.safe_load(text) if yaml is not None else _minimal_yaml_load(text)
    raw = raw or {}
    raw = _env_override(raw)
    llm_raw = raw.get("llm") or {}
    llm = LLMConfig(
        allowed_tables=tuple(llm_raw.get("allowed_tables", LLMConfig().allowed_tables)),
        default_limit=int(llm_raw.get("default_limit", 100)),
    )

    mode = str(raw.get("mode", "demo"))
    database_path = resolve_project_path(raw.get("database_path", "data/processed/mimic_demo.duckdb"))
    raw_data_path = resolve_project_path(raw.get("raw_data_path"))
    outputs_private_path = resolve_project_path(raw.get("outputs_private_path", "outputs/private"))
    outputs_public_path = resolve_project_path(raw.get("outputs_public_path", "outputs/public"))

    assert database_path is not None
    assert outputs_private_path is not None
    assert outputs_public_path is not None

    return WarehouseConfig(
        mode=mode,
        database_path=database_path,
        raw_data_path=raw_data_path,
        public_mode=_as_bool(raw.get("public_mode"), True),
        outputs_private_path=outputs_private_path,
        outputs_public_path=outputs_public_path,
        project_id=raw.get("project_id"),
        hosp_dataset=raw.get("hosp_dataset"),
        icu_dataset=raw.get("icu_dataset"),
        bronze_schema_policy=str(raw.get("bronze_schema_policy", "lowercase_snake_case")),
        llm=llm,
    )
