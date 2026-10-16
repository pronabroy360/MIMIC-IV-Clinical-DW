from __future__ import annotations

import pytest

pytest.importorskip("duckdb")

from src.core.config import WarehouseConfig
from src.core.db import connect, execute_sql_file
from src.core.paths import project_root
from src.ingest.load_demo import load_local_files
from src.research.config import feature_names, leakage_rules, validate_research_frame
from src.research.evaluate import _split_subjects
from src.research.seed import POPULATED_BRONZE_TABLES, seed_research_cohort
from src.transform.build_gold import build_gold


@pytest.fixture()
def research_config(tmp_path) -> WarehouseConfig:
    return WarehouseConfig(
        mode="demo",
        database_path=tmp_path / "research.duckdb",
        raw_data_path=tmp_path / "research-synthetic",
        outputs_private_path=tmp_path / "private",
        outputs_public_path=tmp_path / "public",
    )


@pytest.fixture()
def research_frame(research_config: WarehouseConfig):
    seed_research_cohort(research_config, patients=100, seed=9)
    load_local_files(research_config)
    build_gold(research_config)
    with connect(research_config) as con:
        execute_sql_file(con, project_root() / "sql/research/gold_research_index_admissions.sql")
        return con.execute("SELECT * FROM gold_research_index_admissions").fetchdf()


def test_research_source_has_extended_synthetic_tables(research_config: WarehouseConfig) -> None:
    seed_research_cohort(research_config, patients=100)
    assert (research_config.raw_data_path / "icu" / "inputevents.csv").exists()
    assert (research_config.raw_data_path / "hosp" / "procedures_icd.csv").exists()
    assert (research_config.raw_data_path / "hosp" / "services.csv").exists()
    assert "bronze_icu_inputevents" in POPULATED_BRONZE_TABLES


def test_research_grain_timing_and_outcome_rules(research_frame) -> None:
    assert len(research_frame) == 100
    assert research_frame["subject_id"].nunique() == 100
    assert (research_frame["prediction_time"] <= research_frame["index_dischtime"]).all()
    deaths = research_frame["in_hospital_mortality_flag"] == 1
    assert research_frame.loc[deaths, "urgent_readmitted_30d"].isna().all()
    validate_research_frame(research_frame)


def test_research_predictors_exclude_outcomes_and_splits_are_isolated(research_frame) -> None:
    predictors = set(feature_names("numeric") + feature_names("categorical"))
    assert len(feature_names("numeric")) == 69
    assert len(feature_names("categorical")) == 4
    assert len(predictors) == 73
    assert not predictors.intersection(leakage_rules()["forbidden_predictors"])
    assert predictors.isdisjoint(leakage_rules()["outcomes"])
    split = _split_subjects(research_frame)
    assert split.groupby("subject_id")["split"].nunique().eq(1).all()
    assert set(split["split"]) == {"train", "validation", "test"}
