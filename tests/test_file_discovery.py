from __future__ import annotations

from pathlib import Path

from src.ingest.discover_files import discover_mimic_files


def test_file_discovery_detects_found_and_missing(tmp_path: Path) -> None:
    hosp = tmp_path / "hosp"
    hosp.mkdir()
    (hosp / "patients.csv").write_text("subject_id\n1\n")

    entries = discover_mimic_files(tmp_path)
    patients = next(entry for entry in entries if entry.module == "hosp" and entry.table == "patients")
    admissions = next(entry for entry in entries if entry.module == "hosp" and entry.table == "admissions")

    assert patients.found is True
    assert patients.path is not None
    assert admissions.found is False
