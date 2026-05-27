from __future__ import annotations

from src.core.config import load_config


def test_load_demo_config() -> None:
    config = load_config("configs/demo.duckdb.yaml")
    assert config.mode == "demo"
    assert config.database_path.name == "mimic_demo.duckdb"
    assert "gold_icu_stay_summary" in config.llm.allowed_tables
