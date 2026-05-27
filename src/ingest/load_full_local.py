"""Full local MIMIC-IV ingestion wrapper."""

from __future__ import annotations

from pathlib import Path

from src.core.config import WarehouseConfig
from src.ingest.load_demo import load_local_files


def load_full_local(config: WarehouseConfig) -> Path:
    """Load credentialed full local files using the same local CSV/GZ loader."""
    return load_local_files(config)
