"""Aggregate-only research package publishing and checksum verification."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ALLOWED_ARTIFACTS = frozenset({
    "manifest.json", "cohort_flow.csv", "feature_audit.csv", "timing_audit.csv",
    "quality_summary.json", "model_comparison.csv", "evaluation_summary.json",
    "linear_attributions.csv", "README.md",
})


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def publish_study_package(private_run_dir: Path, public_root: Path) -> Path:
    """Publish only allowlisted aggregate artifacts after checking run success."""
    manifest = json.loads((private_run_dir / "manifest.json").read_text())
    if manifest.get("status") != "succeeded":
        raise ValueError("Only successful runs can be published")
    if manifest.get("dataset_origin") != "synthetic_invented":
        raise ValueError("This publisher accepts invented synthetic study runs only")
    destination = public_root / private_run_dir.name
    staging = public_root / f".{private_run_dir.name}.staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)
    for name in ALLOWED_ARTIFACTS:
        source = private_run_dir / name
        if source.exists():
            shutil.copy2(source, staging / name)
    checksums = {
        path.name: _sha256(path)
        for path in sorted(staging.iterdir())
        if path.is_file()
    }
    (staging / "checksums.json").write_text(json.dumps(checksums, indent=2, sort_keys=True) + "\n")
    if destination.exists():
        shutil.rmtree(destination)
    staging.rename(destination)
    return destination


def verify_study_package(package_dir: Path) -> dict[str, object]:
    """Return package checksum verification status."""
    expected = json.loads((package_dir / "checksums.json").read_text())
    mismatches = [
        name for name, digest in expected.items()
        if not (package_dir / name).exists() or _sha256(package_dir / name) != digest
    ]
    return {"valid": not mismatches, "mismatches": mismatches, "files": sorted(expected)}
