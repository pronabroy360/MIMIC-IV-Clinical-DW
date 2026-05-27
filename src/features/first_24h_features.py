"""First-24-hour feature build helper."""

from __future__ import annotations

from src.core.config import WarehouseConfig
from src.transform.build_gold import build_gold


def build_first_24h_features(config: WarehouseConfig) -> None:
    """Build Gold features that enforce ICU first-24-hour windows."""
    build_gold(config)
