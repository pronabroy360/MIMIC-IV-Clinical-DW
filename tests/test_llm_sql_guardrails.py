from __future__ import annotations

from src.llm.sql_guardrails import validate_aggregate_sql


def test_guardrails_reject_destructive_sql() -> None:
    result = validate_aggregate_sql("DROP TABLE gold_patient_summary")
    assert not result.allowed
    assert any("DROP" in reason for reason in result.reasons)


def test_guardrails_reject_select_star() -> None:
    result = validate_aggregate_sql("SELECT * FROM gold_icu_stay_summary")
    assert not result.allowed
    assert any("SELECT *" in reason for reason in result.reasons)


def test_guardrails_allow_count_distinct_ids_without_projecting_ids() -> None:
    result = validate_aggregate_sql("SELECT count(DISTINCT subject_id) AS patients FROM gold_patient_summary")
    assert result.allowed
    assert result.sql is not None
    assert "LIMIT" in result.sql


def test_guardrails_reject_raw_identifier_projection() -> None:
    result = validate_aggregate_sql(
        "SELECT subject_id, count(*) AS n FROM gold_patient_summary GROUP BY subject_id"
    )
    assert not result.allowed
    assert any("subject_id" in reason for reason in result.reasons)
