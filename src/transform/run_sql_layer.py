"""Run SQL transformation layers."""

from __future__ import annotations

import logging
from pathlib import Path

from src.core.config import WarehouseConfig
from src.core.db import connect, execute_sql_file, row_count, table_exists
from src.core.paths import project_root

logger = logging.getLogger(__name__)


LAYER_DIRS = {
    "bronze": project_root() / "sql" / "bronze",
    "silver": project_root() / "sql" / "silver",
    "gold": project_root() / "sql" / "gold",
}

LAYER_FILE_ORDER = {
    "silver": [
        "silver_patients.sql",
        "silver_admissions.sql",
        "silver_transfers.sql",
        "silver_icustays.sql",
        "silver_diagnoses.sql",
        "silver_procedures.sql",
        "silver_labs.sql",
        "silver_microbiology.sql",
        "silver_medications.sql",
        "silver_provider_orders.sql",
        "silver_chart_events.sql",
        "silver_input_events.sql",
        "silver_output_events.sql",
        "silver_procedure_events.sql",
    ],
    "gold": [
        "gold_patient_summary.sql",
        "gold_admission_summary.sql",
        "gold_icu_stay_summary.sql",
        "gold_first_24h_features.sql",
        "gold_lab_features.sql",
        "gold_vital_features.sql",
        "gold_medication_features.sql",
        "gold_diagnosis_features.sql",
        "gold_mortality_model_dataset.sql",
    ],
}


def sql_files_for_layer(layer: str) -> list[Path]:
    """Return ordered SQL files for a layer."""
    if layer not in LAYER_DIRS:
        raise ValueError(f"Unknown SQL layer: {layer}")
    layer_dir = LAYER_DIRS[layer]
    order = LAYER_FILE_ORDER.get(layer)
    if not order:
        return sorted(layer_dir.glob("*.sql"))
    ordered_paths = [layer_dir / name for name in order if (layer_dir / name).exists()]
    ordered_names = {path.name for path in ordered_paths}
    extras = [path for path in sorted(layer_dir.glob("*.sql")) if path.name not in ordered_names]
    return ordered_paths + extras


def run_sql_layer(config: WarehouseConfig, layer: str) -> list[Path]:
    """Execute every SQL file for a layer and return the executed paths."""
    paths = sql_files_for_layer(layer)
    if not paths:
        logger.warning("No SQL files found for layer %s", layer)
        return []
    with connect(config) as con:
        for path in paths:
            logger.info("Executing %s", path.relative_to(project_root()))
            execute_sql_file(con, path)
    return paths


def profile_tables(config: WarehouseConfig, prefix: str | None = None) -> list[tuple[str, int]]:
    """Return row counts for all tables, optionally filtered by prefix."""
    with connect(config) as con:
        tables = [
            row[0]
            for row in con.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'main'
                ORDER BY table_name
                """
            ).fetchall()
        ]
        if prefix:
            tables = [table for table in tables if table.startswith(prefix)]
        return [(table, row_count(con, table) if table_exists(con, table) else 0) for table in tables]
