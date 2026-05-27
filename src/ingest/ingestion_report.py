"""Ingestion report generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.ingest.discover_files import FileInventoryEntry


@dataclass(frozen=True)
class IngestedTable:
    """A Bronze table load result."""

    module: str
    table: str
    bronze_table: str
    found: bool
    source_file: str | None
    row_count: int
    status: str


def write_ingestion_report(
    output_path: Path,
    inventory: list[FileInventoryEntry],
    loaded_tables: list[IngestedTable],
    mode: str,
) -> Path:
    """Write a private Markdown ingestion report with no row-level data."""
    output_path.mkdir(parents=True, exist_ok=True)
    report_path = output_path / "ingestion_report.md"
    loaded_by_key = {(row.module, row.table): row for row in loaded_tables}
    found = sum(1 for entry in inventory if entry.found)
    missing = sum(1 for entry in inventory if entry.expected and not entry.found)
    total_rows = sum(row.row_count for row in loaded_tables)

    lines = [
        "# Ingestion Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Mode: `{mode}`",
        "",
        "## Summary",
        "",
        f"- Found source files: {found}",
        f"- Missing expected files: {missing}",
        f"- Bronze rows loaded: {total_rows}",
        "",
        "## Table Inventory",
        "",
        "| module | table | bronze table | found | rows | status |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]

    for entry in inventory:
        loaded = loaded_by_key.get((entry.module, entry.table))
        rows = loaded.row_count if loaded else 0
        status = loaded.status if loaded else ("missing" if entry.expected else "not_loaded")
        lines.append(
            f"| {entry.module} | {entry.table} | {entry.bronze_table} | "
            f"{str(entry.found).lower()} | {rows} | {status} |"
        )

    lines.extend(
        [
            "",
            "No source rows, identifiers, timestamps, or patient-level examples are written to this report.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines))
    return report_path
