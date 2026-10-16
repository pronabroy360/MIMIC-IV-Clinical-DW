"""DuckDB utility functions used by pipeline modules."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import duckdb

from src.core.config import WarehouseConfig


def quote_ident(identifier: str) -> str:
    """Safely quote a DuckDB identifier."""
    return '"' + identifier.replace('"', '""') + '"'


def sql_literal(value: str | Path) -> str:
    """Safely quote a SQL string literal."""
    return "'" + str(value).replace("'", "''") + "'"


def connect(config: WarehouseConfig | str | Path, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection and ensure the parent directory exists."""
    database_path = Path(config.database_path if isinstance(config, WarehouseConfig) else config)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(database_path), read_only=read_only)
    con.execute("SET threads TO 4")
    return con


def table_exists(con: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    """Return whether a table or view exists in the main schema."""
    return bool(
        con.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'main' AND table_name = ?
            """,
            [table_name],
        ).fetchone()[0]
    )


def get_columns(con: duckdb.DuckDBPyConnection, table_name: str) -> list[str]:
    """Return column names for a table, or an empty list if absent."""
    if not table_exists(con, table_name):
        return []
    return [row[1] for row in con.execute(f"PRAGMA table_info({quote_ident(table_name)})").fetchall()]


def ensure_empty_table(
    con: duckdb.DuckDBPyConnection, table_name: str, columns: dict[str, str]
) -> None:
    """Create an empty table with the requested schema if it does not exist."""
    column_sql = ",\n    ".join(f"{quote_ident(name)} {dtype}" for name, dtype in columns.items())
    con.execute(f"CREATE TABLE IF NOT EXISTS {quote_ident(table_name)} ({column_sql})")


def add_missing_columns(
    con: duckdb.DuckDBPyConnection, table_name: str, columns: dict[str, str]
) -> None:
    """Add nullable columns that are expected by downstream SQL."""
    existing = set(get_columns(con, table_name))
    for name, dtype in columns.items():
        if name not in existing:
            con.execute(f"ALTER TABLE {quote_ident(table_name)} ADD COLUMN {quote_ident(name)} {dtype}")


def row_count(con: duckdb.DuckDBPyConnection, table_name: str) -> int:
    """Return a table row count, treating absent tables as zero."""
    if not table_exists(con, table_name):
        return 0
    return int(con.execute(f"SELECT COUNT(*) FROM {quote_ident(table_name)}").fetchone()[0])


def execute_sql_file(con: duckdb.DuckDBPyConnection, path: Path) -> None:
    """Execute a SQL file."""
    con.execute(path.read_text())


def execute_sql_files(con: duckdb.DuckDBPyConnection, paths: Iterable[Path]) -> None:
    """Execute SQL files in order."""
    for path in paths:
        execute_sql_file(con, path)
