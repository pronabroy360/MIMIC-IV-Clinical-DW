"""Validate LocalStack S3 source availability for expected MIMIC tables."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb

from src.core.config import WarehouseConfig
from src.core.db import connect, sql_literal
from src.ingest.discover_files import EXPECTED_TABLES


@dataclass(frozen=True)
class LocalStackCheckResult:
    module: str
    table: str
    found: bool
    uri: str | None
    note: str


def _configure_s3(con: duckdb.DuckDBPyConnection, config: WarehouseConfig) -> None:
    if not config.localstack_endpoint:
        raise ValueError("localstack_endpoint is required for localstack mode")
    if not config.localstack_bucket:
        raise ValueError("localstack_bucket is required for localstack mode")
    con.execute("INSTALL httpfs")
    con.execute("LOAD httpfs")
    con.execute(f"SET s3_endpoint={sql_literal(config.localstack_endpoint)}")
    con.execute(f"SET s3_region={sql_literal(config.localstack_region)}")
    con.execute(f"SET s3_access_key_id={sql_literal(config.localstack_access_key)}")
    con.execute(f"SET s3_secret_access_key={sql_literal(config.localstack_secret_key)}")
    con.execute(f"SET s3_use_ssl={'true' if config.localstack_use_ssl else 'false'}")
    con.execute(f"SET s3_url_style={sql_literal(config.localstack_url_style)}")


def _s3_uri(config: WarehouseConfig, module: str, table: str, suffix: str) -> str:
    assert config.localstack_bucket is not None
    prefix = config.localstack_prefix.strip("/")
    return f"s3://{config.localstack_bucket}/{prefix}/{module}/{table}{suffix}"


def _probe_uri(con: duckdb.DuckDBPyConnection, uri: str) -> tuple[bool, str]:
    try:
        con.execute(
            f"""
            SELECT 1
            FROM read_csv_auto(
                {sql_literal(uri)},
                header=true,
                union_by_name=true,
                ignore_errors=true
            )
            LIMIT 1
            """
        ).fetchall()
        return True, "ok"
    except Exception as exc:
        return False, str(exc).splitlines()[0][:300]


def _write_report(results: list[LocalStackCheckResult], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "localstack_readiness_report.md"

    found_count = sum(1 for row in results if row.found)
    total = len(results)
    missing_count = total - found_count

    lines = [
        "# LocalStack Source Readiness Report",
        "",
        f"- Checked tables: `{total}`",
        f"- Available source objects: `{found_count}`",
        f"- Missing source objects: `{missing_count}`",
        "",
        "## Module Summary",
        "",
        "| Module | Found | Missing |",
        "| --- | ---: | ---: |",
    ]
    for module in sorted(EXPECTED_TABLES):
        module_rows = [row for row in results if row.module == module]
        module_found = sum(1 for row in module_rows if row.found)
        lines.append(f"| {module} | {module_found} | {len(module_rows) - module_found} |")

    lines.extend(
        [
            "",
            "## Table Checks",
            "",
            "| Module | Table | Found | URI | Note |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in results:
        lines.append(
            f"| {row.module} | {row.table} | {'yes' if row.found else 'no'} | "
            f"{row.uri or '-'} | {row.note.replace('|', '/')} |"
        )

    path.write_text("\n".join(lines) + "\n")
    return path


def check_localstack_sources(config: WarehouseConfig) -> Path:
    """Probe expected LocalStack S3 CSV objects and write a readiness report."""
    if config.mode != "localstack":
        raise ValueError("LocalStack readiness check requires mode=localstack")

    results: list[LocalStackCheckResult] = []
    with connect(config) as con:
        _configure_s3(con, config)
        for module, tables in EXPECTED_TABLES.items():
            for table in tables:
                final_found = False
                final_uri: str | None = None
                final_note = "not found"
                for suffix in (".csv.gz", ".csv"):
                    uri = _s3_uri(config, module, table, suffix)
                    found, note = _probe_uri(con, uri)
                    if found:
                        final_found = True
                        final_uri = uri
                        final_note = "ok"
                        break
                    final_note = note
                results.append(
                    LocalStackCheckResult(
                        module=module,
                        table=table,
                        found=final_found,
                        uri=final_uri,
                        note=final_note,
                    )
                )
    return _write_report(results, config.outputs_private_path)
