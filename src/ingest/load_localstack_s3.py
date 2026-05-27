"""Ingest MIMIC-style CSV objects from LocalStack S3 into Bronze DuckDB tables."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from src.core.config import WarehouseConfig
from src.core.db import add_missing_columns, connect, ensure_empty_table, quote_ident, row_count, sql_literal
from src.ingest.discover_files import EXPECTED_TABLES, FileInventoryEntry, expected_bronze_schema
from src.ingest.ingestion_report import IngestedTable, write_ingestion_report

logger = logging.getLogger(__name__)


def _s3_uri(config: WarehouseConfig, module: str, table: str, suffix: str) -> str:
    assert config.localstack_bucket is not None
    prefix = config.localstack_prefix.strip("/")
    return f"s3://{config.localstack_bucket}/{prefix}/{module}/{table}{suffix}"


def _configure_s3(con: duckdb.DuckDBPyConnection, config: WarehouseConfig) -> None:
    if not config.localstack_endpoint:
        raise ValueError("localstack_endpoint is required for localstack mode")
    con.execute("INSTALL httpfs")
    con.execute("LOAD httpfs")
    con.execute(f"SET s3_endpoint={sql_literal(config.localstack_endpoint)}")
    con.execute(f"SET s3_region={sql_literal(config.localstack_region)}")
    con.execute(f"SET s3_access_key_id={sql_literal(config.localstack_access_key)}")
    con.execute(f"SET s3_secret_access_key={sql_literal(config.localstack_secret_key)}")
    con.execute(f"SET s3_use_ssl={'true' if config.localstack_use_ssl else 'false'}")
    con.execute(f"SET s3_url_style={sql_literal(config.localstack_url_style)}")


def _load_one(
    con: duckdb.DuckDBPyConnection,
    config: WarehouseConfig,
    module: str,
    table: str,
    pipeline_run_id: str,
) -> tuple[bool, int, str]:
    bronze_table = f"bronze_{module}_{table}"
    for suffix in (".csv.gz", ".csv"):
        uri = _s3_uri(config, module, table, suffix)
        try:
            con.execute(
                f"""
                CREATE OR REPLACE TABLE {quote_ident(bronze_table)} AS
                SELECT
                    * ,
                    {sql_literal(uri)} AS source_file,
                    current_timestamp AS loaded_at,
                    {sql_literal(module)} AS source_module,
                    {sql_literal(pipeline_run_id)} AS pipeline_run_id
                FROM read_csv_auto(
                    {sql_literal(uri)},
                    header=true,
                    union_by_name=true,
                    ignore_errors=true
                )
                """
            )
            add_missing_columns(con, bronze_table, expected_bronze_schema(module, table))
            rows = row_count(con, bronze_table)
            return True, rows, "loaded"
        except Exception:
            continue
    return False, row_count(con, bronze_table), "missing_placeholder"


def load_localstack_s3(config: WarehouseConfig) -> Path:
    """Load expected MIMIC tables from LocalStack S3 into Bronze."""
    if not config.localstack_bucket:
        raise ValueError("localstack_bucket is required for localstack mode")

    loaded_tables: list[IngestedTable] = []
    config.outputs_private_path.mkdir(parents=True, exist_ok=True)
    config.database_path.parent.mkdir(parents=True, exist_ok=True)

    with connect(config) as con:
        _configure_s3(con, config)
        for module, tables in EXPECTED_TABLES.items():
            for table in tables:
                bronze_table = f"bronze_{module}_{table}"
                ensure_empty_table(con, bronze_table, expected_bronze_schema(module, table))
                found, rows, status = _load_one(con, config, module, table, config.pipeline_run_id)
                if found:
                    logger.info("Loaded %s rows into %s", rows, bronze_table)
                loaded_tables.append(
                    IngestedTable(
                        module=module,
                        table=table,
                        bronze_table=bronze_table,
                        found=found,
                        source_file=(
                            f"s3://{config.localstack_bucket}/{config.localstack_prefix}/{module}/{table}.csv*"
                            if found
                            else None
                        ),
                        row_count=rows,
                        status=status,
                    )
                )

    inventory: list[FileInventoryEntry] = []
    for row in loaded_tables:
        inventory.append(
            FileInventoryEntry(
                module=row.module,
                table=row.table,
                path=Path(row.source_file) if row.source_file else None,
                found=row.found,
                expected=True,
            )
        )
    return write_ingestion_report(config.outputs_private_path, inventory, loaded_tables, mode=config.mode)
