"""Versioned, deterministic evaluation of the non-executing study assistant."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from src.research.assistant import draft_study


def evaluate_assistant(corpus_path: Path, output_path: Path | None = None) -> dict[str, object]:
    """Compare assistant response state with reviewed expected states."""
    corpus = yaml.safe_load(corpus_path.read_text()) or {}
    cases = corpus.get("cases", [])
    results = []
    for case in cases:
        actual = draft_study(str(case["question"]))
        results.append({
            "question": case["question"], "expected_status": case["expected_status"],
            "actual_status": actual["status"], "passed": actual["status"] == case["expected_status"],
        })
    summary = {"schema_version": 1, "case_count": len(results), "passed": sum(row["passed"] for row in results), "failed": sum(not row["passed"] for row in results), "results": results}
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2) + "\n")
    return summary
