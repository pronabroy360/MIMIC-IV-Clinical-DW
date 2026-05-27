"""Build compact schema context from allowed warehouse tables."""

from __future__ import annotations

import duckdb

from src.core.db import get_columns, table_exists
from src.llm.sql_guardrails import DEFAULT_ALLOWED_TABLES


def build_schema_context(
    con: duckdb.DuckDBPyConnection,
    allowed_tables: set[str] | None = None,
) -> str:
    """Return a concise schema summary for prompt grounding."""
    allowed_tables = allowed_tables or DEFAULT_ALLOWED_TABLES
    lines: list[str] = []
    for table in sorted(allowed_tables):
        if not table_exists(con, table):
            continue
        columns = ", ".join(get_columns(con, table))
        lines.append(f"- {table}({columns})")
    return "\n".join(lines)
