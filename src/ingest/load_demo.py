"""Local CSV/GZ ingestion for MIMIC-IV demo and full local modes."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from src.core.config import WarehouseConfig
from src.core.db import (
    add_missing_columns,
    connect,
    ensure_empty_table,
    quote_ident,
    row_count,
    sql_literal,
)
from src.ingest.discover_files import (
    EXPECTED_TABLES,
    FileInventoryEntry,
    discover_mimic_files,
    expected_bronze_schema,
    to_snake_case,
)
from src.ingest.ingestion_report import IngestedTable, write_ingestion_report

logger = logging.getLogger(__name__)


def _describe_csv(con: duckdb.DuckDBPyConnection, path: Path) -> list[str]:
    describe_sql = (
        "DESCRIBE SELECT * FROM read_csv_auto("
        f"{sql_literal(path)}, header=true, union_by_name=true, ignore_errors=true)"
    )
    return [row[0] for row in con.execute(describe_sql).fetchall()]


def _unique_normalized_columns(columns: list[str]) -> list[tuple[str, str]]:
    normalized: list[tuple[str, str]] = []
    seen: dict[str, int] = {}
    for source in columns:
        target = to_snake_case(source) or "unnamed"
        if target in seen:
            seen[target] += 1
            target = f"{target}_{seen[target]}"
        else:
            seen[target] = 0
        normalized.append((source, target))
    return normalized


def _load_csv_to_bronze(
    con: duckdb.DuckDBPyConnection,
    entry: FileInventoryEntry,
    pipeline_run_id: str,
) -> int:
    assert entry.path is not None
    source_columns = _describe_csv(con, entry.path)
    select_columns = []
    for source, target in _unique_normalized_columns(source_columns):
        select_columns.append(f"{quote_ident(source)} AS {quote_ident(target)}")
    select_columns.extend(
        [
            f"{sql_literal(entry.path.name)} AS source_file",
            "current_timestamp AS loaded_at",
            f"{sql_literal(entry.module)} AS source_module",
            f"{sql_literal(pipeline_run_id)} AS pipeline_run_id",
        ]
    )

    con.execute(
        f"""
        CREATE OR REPLACE TABLE {quote_ident(entry.bronze_table)} AS
        SELECT {", ".join(select_columns)}
        FROM read_csv_auto(
            {sql_literal(entry.path)},
            header=true,
            union_by_name=true,
            ignore_errors=true
        )
        """
    )
    add_missing_columns(
        con,
        entry.bronze_table,
        expected_bronze_schema(entry.module, entry.table),
    )
    return row_count(con, entry.bronze_table)


def ensure_all_expected_bronze_tables(config: WarehouseConfig) -> None:
    """Ensure placeholder Bronze tables exist for all expected tables."""
    with connect(config) as con:
        for module, tables in EXPECTED_TABLES.items():
            for table in tables:
                ensure_empty_table(
                    con,
                    f"bronze_{module}_{table}",
                    expected_bronze_schema(module, table),
                )


def load_local_files(config: WarehouseConfig) -> Path:
    """Load available MIMIC-IV CSV/GZ files into Bronze tables."""
    inventory = discover_mimic_files(config.raw_data_path)
    loaded_tables: list[IngestedTable] = []

    config.outputs_private_path.mkdir(parents=True, exist_ok=True)
    config.database_path.parent.mkdir(parents=True, exist_ok=True)

    if config.raw_data_path is None or not config.raw_data_path.exists():
        logger.warning(
            "Raw data path is missing: %s. Creating empty Bronze placeholders.",
            config.raw_data_path,
        )

    with connect(config) as con:
        for entry in inventory:
            ensure_empty_table(
                con,
                entry.bronze_table,
                expected_bronze_schema(entry.module, entry.table),
            )

            if not entry.found:
                loaded_tables.append(
                    IngestedTable(
                        module=entry.module,
                        table=entry.table,
                        bronze_table=entry.bronze_table,
                        found=False,
                        source_file=None,
                        row_count=row_count(con, entry.bronze_table),
                        status="missing_placeholder",
                    )
                )
                continue

            try:
                rows = _load_csv_to_bronze(con, entry, config.pipeline_run_id)
                status = "loaded"
                logger.info("Loaded %s rows into %s", rows, entry.bronze_table)
            except Exception as exc:  # pragma: no cover - surfaced in report and logs
                logger.exception("Failed to load %s", entry.path)
                rows = row_count(con, entry.bronze_table)
                status = f"load_failed: {exc}"

            loaded_tables.append(
                IngestedTable(
                    module=entry.module,
                    table=entry.table,
                    bronze_table=entry.bronze_table,
                    found=True,
                    source_file=entry.path.name if entry.path else None,
                    row_count=rows,
                    status=status,
                )
            )

    return write_ingestion_report(
        config.outputs_private_path,
        inventory,
        loaded_tables,
        mode=config.mode,
    )
