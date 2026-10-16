"""Typed, non-executing study-question drafting for the research workflow."""

from __future__ import annotations


def draft_study(question: str) -> dict[str, object]:
    """Return a reviewed-study draft or a clear clarification/unsupported state."""
    normalized = question.lower().strip()
    if not normalized:
        return {"status": "needs_clarification", "unresolved_fields": ["research question"]}
    mortality_terms = ("mortality", "death", "die")
    icu_terms = ("icu", "intensive care")
    if any(term in normalized for term in mortality_terms) and any(term in normalized for term in icu_terms):
        return {
            "status": "draft",
            "study_name": "icu_mortality_24h",
            "interpretation": "Prospective synthetic ICU mortality after a 24-hour observation window.",
            "unresolved_fields": [],
            "requires_review": True,
        }
    if "sepsis" in normalized or "readmission" in normalized:
        return {
            "status": "needs_clarification",
            "unresolved_fields": ["validated phenotype definition", "outcome ascertainment window"],
            "requires_review": True,
        }
    return {
        "status": "unsupported",
        "unresolved_fields": ["supported study template"],
        "requires_review": True,
    }
