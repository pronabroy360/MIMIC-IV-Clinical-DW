"""Key and relationship validation checks."""

from __future__ import annotations

import duckdb

from src.core.db import table_exists
from src.validation.validation_report import ValidationResult


def _count(con: duckdb.DuckDBPyConnection, sql: str) -> int:
    return int(con.execute(sql).fetchone()[0])


def validate_keys(con: duckdb.DuckDBPyConnection) -> list[ValidationResult]:
    """Validate primary keys and core relationships."""
    results: list[ValidationResult] = []
    required = ("silver_patients", "silver_admissions", "silver_icustays")
    if not all(table_exists(con, table) for table in required):
        return [ValidationResult("key_checks_ready", "warn", "Core Silver tables are not all present", "warn")]

    duplicate_patients = _count(
        con,
        """
        SELECT COUNT(*)
        FROM (
            SELECT subject_id
            FROM silver_patients
            GROUP BY subject_id
            HAVING COUNT(*) > 1
        )
        """,
    )
    results.append(
        ValidationResult(
            "unique_patients",
            "pass" if duplicate_patients == 0 else "fail",
            f"Duplicate subject_id groups: {duplicate_patients}",
        )
    )

    duplicate_admissions = _count(
        con,
        """
        SELECT COUNT(*)
        FROM (
            SELECT hadm_id
            FROM silver_admissions
            GROUP BY hadm_id
            HAVING COUNT(*) > 1
        )
        """,
    )
    results.append(
        ValidationResult(
            "unique_admissions",
            "pass" if duplicate_admissions == 0 else "fail",
            f"Duplicate hadm_id groups: {duplicate_admissions}",
        )
    )

    duplicate_stays = _count(
        con,
        """
        SELECT COUNT(*)
        FROM (
            SELECT stay_id
            FROM silver_icustays
            GROUP BY stay_id
            HAVING COUNT(*) > 1
        )
        """,
    )
    results.append(
        ValidationResult(
            "unique_icustays",
            "pass" if duplicate_stays == 0 else "fail",
            f"Duplicate stay_id groups: {duplicate_stays}",
        )
    )

    orphan_admissions = _count(
        con,
        """
        SELECT COUNT(*)
        FROM silver_admissions a
        LEFT JOIN silver_patients p ON a.subject_id = p.subject_id
        WHERE p.subject_id IS NULL
        """,
    )
    results.append(
        ValidationResult(
            "admissions_link_to_patients",
            "pass" if orphan_admissions == 0 else "fail",
            f"Admissions without patient: {orphan_admissions}",
        )
    )

    orphan_stays = _count(
        con,
        """
        SELECT COUNT(*)
        FROM silver_icustays i
        LEFT JOIN silver_admissions a ON i.hadm_id = a.hadm_id
        WHERE a.hadm_id IS NULL
        """,
    )
    results.append(
        ValidationResult(
            "icustays_link_to_admissions",
            "pass" if orphan_stays == 0 else "warn",
            f"ICU stays without admission: {orphan_stays}",
            "warn" if orphan_stays else "error",
        )
    )
    return results
