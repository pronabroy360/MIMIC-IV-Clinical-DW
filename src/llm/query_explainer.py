"""Human-readable aggregate query explanations."""

from __future__ import annotations


def explain_sql(sql: str) -> str:
    """Return a short non-clinical explanation of an aggregate SQL query."""
    lowered = sql.lower()
    if "group by" in lowered:
        return "This aggregate query groups warehouse records and computes summary statistics."
    if "count(" in lowered:
        return "This aggregate query counts records without displaying patient-level identifiers."
    if "avg(" in lowered:
        return "This aggregate query computes averages without displaying patient-level identifiers."
    return "This query returns aggregate warehouse results only."
