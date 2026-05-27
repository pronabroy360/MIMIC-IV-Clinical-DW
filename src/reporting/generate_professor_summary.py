"""Generate a concise professor-facing summary artifact."""

from __future__ import annotations

from pathlib import Path

from src.core.config import WarehouseConfig


SUMMARY_TEXT = """# Professor Outreach Summary

This project implements a reproducible clinical data warehouse for MIMIC-IV
structured EHR research. It demonstrates local DuckDB ingestion, SQL-based
Bronze/Silver/Gold modeling, cohort templates, first-24-hour feature
engineering, validation checks, aggregate dashboards, FastAPI endpoints, and a
privacy-preserving natural-language query layer.

The repository is designed for public review without including restricted
MIMIC-IV data. Demo mode supports the openly accessible MIMIC-IV demo files,
while full local mode is reserved for credentialed PhysioNet users who comply
with the Data Use Agreement.
"""


def generate_professor_summary(config: WarehouseConfig) -> Path:
    """Write the professor-facing project summary."""
    config.outputs_public_path.mkdir(parents=True, exist_ok=True)
    path = config.outputs_public_path / "professor_summary.md"
    path.write_text(SUMMARY_TEXT)
    return path
