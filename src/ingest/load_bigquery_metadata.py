"""BigQuery metadata placeholder.

The project intentionally avoids storing or requiring cloud credentials in the
public repository. This module records the configured BigQuery datasets and
creates the same empty Bronze placeholders used by local modes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.core.config import WarehouseConfig
from src.ingest.load_demo import ensure_all_expected_bronze_tables


def load_bigquery_metadata(config: WarehouseConfig) -> Path:
    """Write private BigQuery configuration metadata and placeholder tables."""
    ensure_all_expected_bronze_tables(config)
    config.outputs_private_path.mkdir(parents=True, exist_ok=True)
    report_path = config.outputs_private_path / "bigquery_metadata_report.md"
    report_path.write_text(
        "\n".join(
            [
                "# BigQuery Metadata Report",
                "",
                f"Generated: {datetime.now(timezone.utc).isoformat()}",
                f"Project ID: `{config.project_id or 'not configured'}`",
                f"Hosp dataset: `{config.hosp_dataset or 'not configured'}`",
                f"ICU dataset: `{config.icu_dataset or 'not configured'}`",
                "",
                "No credentials or row-level data are stored by this report.",
                "",
            ]
        )
    )
    return report_path
