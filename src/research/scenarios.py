"""Deterministic, isolated quality scenarios for invented synthetic data only."""

from __future__ import annotations

import csv
import shutil
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from src.core.config import WarehouseConfig
from src.core.paths import project_root


def available_scenarios() -> dict[str, dict[str, object]]:
    raw = yaml.safe_load((project_root() / "configs/research/scenarios.yaml").read_text()) or {}
    return raw.get("scenarios", {})


def prepare_scenario(config: WarehouseConfig, scenario_name: str) -> WarehouseConfig:
    """Copy only the invented research source into an isolated scenario workspace."""
    scenarios = available_scenarios()
    if scenario_name not in scenarios:
        raise ValueError(f"Unknown scenario: {scenario_name}")
    if config.mode != "demo" or config.raw_data_path is None or "research-synthetic" not in config.raw_data_path.parts:
        raise ValueError("Scenarios only accept the isolated invented research source")
    source = config.raw_data_path.resolve()
    root = (config.outputs_private_path / "studies" / "scenarios" / scenario_name).resolve()
    if source == root:
        raise ValueError("Invalid synthetic scenario source")
    for candidate in config.raw_data_path.rglob("*"):
        if candidate.is_symlink():
            resolved = candidate.resolve()
            if resolved != source and source not in resolved.parents:
                raise ValueError("Synthetic scenario source contains a symlink outside its data root")
    target_raw = root / "raw" / "research-synthetic"
    if target_raw.exists():
        shutil.rmtree(target_raw)
    target_raw.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target_raw)
    mutation = str(scenarios[scenario_name]["mutation"])
    if mutation == "delay_lab_storetime":
        _delay_lab_storetime(target_raw / "hosp" / "labevents.csv", int(scenarios[scenario_name]["every_nth_lab"]))
    elif mutation == "duplicate_admission_key":
        _duplicate_first_data_row(target_raw / "hosp" / "admissions.csv")
    elif mutation == "remove_icu_intime":
        _blank_first_value(target_raw / "icu" / "icustays.csv", "intime")
    elif mutation == "impossible_spo2":
        _set_first_matching_value(target_raw / "icu" / "chartevents.csv", "itemid", "220277", "valuenum", "150")
        _set_first_matching_value(target_raw / "icu" / "chartevents.csv", "itemid", "220277", "value", "150")
    else:  # pragma: no cover - protected by checked-in registry
        raise ValueError(f"Unsupported scenario mutation: {mutation}")
    return replace(
        config,
        database_path=root / "scenario.duckdb",
        raw_data_path=target_raw,
        outputs_private_path=root / "private",
        outputs_public_path=root / "public",
    )


def _delay_lab_storetime(path: Path, every_nth: int) -> None:
    rows = list(csv.DictReader(path.open()))
    if not rows:
        return
    for index, row in enumerate(rows):
        if index % every_nth == 0 and row.get("charttime"):
            row["storetime"] = (datetime.fromisoformat(row["charttime"]) + timedelta(hours=30)).strftime("%Y-%m-%d %H:%M:%S")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _duplicate_first_data_row(path: Path) -> None:
    rows = list(csv.DictReader(path.open()))
    if not rows:
        return
    rows.append(dict(rows[0]))
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _blank_first_value(path: Path, column: str) -> None:
    rows = list(csv.DictReader(path.open()))
    if rows:
        rows[0][column] = ""
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def _set_first_matching_value(path: Path, match_column: str, match_value: str, column: str, value: str) -> None:
    rows = list(csv.DictReader(path.open()))
    for row in rows:
        if row.get(match_column) == match_value:
            row[column] = value
            break
    if rows:
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
