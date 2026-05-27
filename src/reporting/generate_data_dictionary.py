"""Generate an aggregate-safe data dictionary from DuckDB metadata."""

from __future__ import annotations

from pathlib import Path

from src.core.config import WarehouseConfig
from src.core.db import connect, get_columns


def generate_data_dictionary(config: WarehouseConfig) -> Path:
    """Write table/column metadata without row examples."""
    config.outputs_private_path.mkdir(parents=True, exist_ok=True)
    path = config.outputs_private_path / "data_dictionary.md"
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
        lines = ["# Data Dictionary", "", "No row-level examples are included.", ""]
        for table in tables:
            lines.append(f"## `{table}`")
            lines.append("")
            for column in get_columns(con, table):
                lines.append(f"- `{column}`")
            lines.append("")
    path.write_text("\n".join(lines))
    return path
