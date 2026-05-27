"""Generate a private aggregate pipeline report."""

from __future__ import annotations

from pathlib import Path

from src.core.config import WarehouseConfig
from src.transform.run_sql_layer import profile_tables


def generate_pipeline_report(config: WarehouseConfig) -> Path:
    """Write aggregate table counts for pipeline review."""
    config.outputs_private_path.mkdir(parents=True, exist_ok=True)
    path = config.outputs_private_path / "pipeline_report.md"
    rows = profile_tables(config)
    lines = [
        "# Pipeline Report",
        "",
        "| table | rows |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {table} | {count} |" for table, count in rows)
    lines.append("")
    lines.append("This report contains table-level row counts only.")
    lines.append("")
    path.write_text("\n".join(lines))
    return path
