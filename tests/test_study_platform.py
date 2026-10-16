from __future__ import annotations

import json
from pathlib import Path
from dataclasses import replace

import pytest

pytest.importorskip("duckdb")
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

import src.api.main as api_main
from src.core.config import WarehouseConfig
from src.core.db import connect
from src.ingest.load_demo import load_local_files
from src.research.contracts import StudyValidationError, load_study_spec, validate_study_spec
from src.research.assistant import draft_study
from src.research.evaluate_assistant import evaluate_assistant
from src.research.features import FEATURE_TABLE, build_prospective_feature_table
from src.research.publication import publish_study_package, verify_study_package
from src.research.seed import seed_research_cohort
from src.research.study_service import preview_study
from src.research.tasks import task_definition
from src.transform.build_gold import build_gold
from src.validation.validate_research_quality import validate_source_key_uniqueness


@pytest.fixture()
def study_config(tmp_path) -> WarehouseConfig:
    return WarehouseConfig(
        mode="demo",
        database_path=tmp_path / "study.duckdb",
        raw_data_path=tmp_path / "research-synthetic",
        outputs_private_path=tmp_path / "private",
        outputs_public_path=tmp_path / "public",
    )


@pytest.fixture()
def prepared_study(study_config: WarehouseConfig):
    seed_research_cohort(study_config, patients=100, seed=17)
    load_local_files(study_config)
    build_gold(study_config)
    spec = load_study_spec("configs/studies/icu_mortality_24h.yaml")
    return study_config, spec


def test_timed_feature_builder_excludes_late_available_labs(prepared_study) -> None:
    config, spec = prepared_study
    with connect(config) as con:
        con.execute("UPDATE silver_labs SET storetime = charttime + INTERVAL '30 hours'")
        build_prospective_feature_table(con, spec)
        total, with_labs = con.execute(
            f"SELECT count(*), count(*) FILTER (WHERE lab_event_count_24h > 0) FROM {FEATURE_TABLE}"
        ).fetchone()
        columns = {row[1] for row in con.execute(f"PRAGMA table_info('{FEATURE_TABLE}')").fetchall()}
    assert total > 0
    assert with_labs == 0
    assert "diabetes_flag" not in columns
    assert "ventilation_procedure_flag" not in columns


def test_first_icu_stay_and_post_prediction_events_cannot_change_features(prepared_study) -> None:
    config, spec = prepared_study
    with connect(config) as con:
        build_prospective_feature_table(con, spec)
        before = con.execute(
            f"SELECT heart_rate_mean FROM {FEATURE_TABLE} ORDER BY stay_id LIMIT 1"
        ).fetchone()[0]
        subject_id, hadm_id, stay_id, prediction_time = con.execute(
            f"SELECT subject_id, hadm_id, stay_id, prediction_time FROM {FEATURE_TABLE} ORDER BY stay_id LIMIT 1"
        ).fetchone()
        con.execute(
            "INSERT INTO silver_chart_events (subject_id, hadm_id, stay_id, charttime, storetime, chart_label, valuenum) "
            "VALUES (?, ?, ?, ? + INTERVAL '1 hour', ? + INTERVAL '1 hour', 'Heart Rate', 999)",
            [subject_id, hadm_id, stay_id, prediction_time, prediction_time],
        )
        con.execute(
            "INSERT INTO silver_icustays (subject_id, hadm_id, stay_id, intime, outtime, first_careunit) "
            "VALUES (?, ?, ?, ? + INTERVAL '2 days', ? + INTERVAL '3 days', 'MICU')",
            [subject_id, hadm_id, stay_id + 999999, prediction_time, prediction_time],
        )
        build_prospective_feature_table(con, spec)
        after = con.execute(
            f"SELECT heart_rate_mean FROM {FEATURE_TABLE} WHERE stay_id = ?", [stay_id]
        ).fetchone()[0]
        selected_rows = con.execute(
            f"SELECT count(*) FROM {FEATURE_TABLE} WHERE subject_id = ?", [subject_id]
        ).fetchone()[0]
    assert before == after
    assert selected_rows == 1


def test_preview_has_monotone_cohort_flow_and_task_excludes_coding_features(prepared_study) -> None:
    config, spec = prepared_study
    preview = preview_study(config, spec)
    counts = [row["icu_stays"] for row in preview["cohort_flow"]]
    assert counts == sorted(counts, reverse=True)
    task = task_definition(spec.task_name)
    assert "diagnosis_codes" in task.excluded_feature_families
    assert "procedure_codes" in task.excluded_feature_families


def test_prospective_contract_rejects_relaxed_survival_or_icu_eligibility(prepared_study) -> None:
    _, spec = prepared_study
    with pytest.raises(StudyValidationError, match="survival"):
        validate_study_spec(replace(spec, require_alive_at_prediction=False))
    with pytest.raises(StudyValidationError, match="ICU presence"):
        validate_study_spec(replace(spec, require_in_icu_at_prediction=False))


def test_publication_package_is_allowlisted_and_checksum_verified(tmp_path) -> None:
    private_run = tmp_path / "private-run"
    private_run.mkdir()
    (private_run / "manifest.json").write_text(json.dumps({"status": "succeeded", "dataset_origin": "synthetic_invented"}))
    (private_run / "cohort_flow.csv").write_text("step,icu_stays\neligible,20\n")
    (private_run / "raw_records.csv").write_text("subject_id\n1\n")
    package = publish_study_package(private_run, tmp_path / "public")
    assert not (package / "raw_records.csv").exists()
    assert verify_study_package(package)["valid"]
    (package / "cohort_flow.csv").write_text("changed")
    assert not verify_study_package(package)["valid"]


def test_study_api_validates_registered_study(monkeypatch: pytest.MonkeyPatch, prepared_study) -> None:
    config, _ = prepared_study
    monkeypatch.setattr(api_main, "get_config", lambda: config)
    client = TestClient(api_main.app)
    response = client.post("/studies/validate", json={"study_name": "icu_mortality_24h"})
    assert response.status_code == 200
    assert response.json()["status"] == "validated"
    invalid = client.post("/studies/validate", json={"study_name": "not-a-study"})
    assert invalid.status_code == 422
    overridden = client.post("/studies/validate", json={"study_name": "icu_mortality_24h", "minimum_age": 60})
    assert overridden.status_code == 200
    assert overridden.json()["definition_hash"] != response.json()["definition_hash"]


def test_source_duplicate_quality_gate_runs_before_silver_dedup(prepared_study) -> None:
    config, _ = prepared_study
    with connect(config) as con:
        con.execute("INSERT INTO bronze_hosp_admissions SELECT * FROM bronze_hosp_admissions LIMIT 1")
        results = validate_source_key_uniqueness(con)
    assert any(result.check == "bronze_unique_admission_keys" and result.status == "fail" for result in results)


def test_assistant_drafts_only_supported_question_and_requests_clarification() -> None:
    supported = draft_study("How does ICU mortality change after the first 24 hours?")
    ambiguous = draft_study("Can you predict sepsis in the ICU?")
    unsupported = draft_study("Forecast staffing needs next month")
    assert supported["status"] == "draft"
    assert ambiguous["status"] == "needs_clarification"
    assert unsupported["status"] == "unsupported"


def test_versioned_assistant_corpus_passes() -> None:
    summary = evaluate_assistant(Path("configs/research/assistant_evaluation.yaml"))
    assert summary["failed"] == 0
    assert summary["passed"] == summary["case_count"]
