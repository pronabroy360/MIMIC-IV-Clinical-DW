"""Validation result model and report writer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class ValidationResult:
    """One validation check result."""

    check: str
    status: str
    detail: str
    severity: str = "error"

    @property
    def passed(self) -> bool:
        return self.status == "pass"


def write_validation_report(results: list[ValidationResult], output_dir: Path) -> Path:
    """Write a private Markdown validation report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "validation_report.md"
    passed = sum(1 for result in results if result.status == "pass")
    failed = sum(1 for result in results if result.status == "fail")
    warnings = sum(1 for result in results if result.status == "warn")

    lines = [
        "# Validation Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Summary",
        "",
        f"- Passed: {passed}",
        f"- Failed: {failed}",
        f"- Warnings: {warnings}",
        "",
        "## Checks",
        "",
        "| check | status | severity | detail |",
        "| --- | --- | --- | --- |",
    ]
    for result in results:
        detail = result.detail.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {result.check} | {result.status} | {result.severity} | {detail} |")

    lines.append("")
    lines.append("This report contains aggregate quality checks only.")
    lines.append("")
    path.write_text("\n".join(lines))
    return path
