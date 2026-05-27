"""Medication feature helper SQL snippets."""

MEDICATION_FEATURE_TABLE = "gold_medication_features"


def medication_proxy_columns() -> tuple[str, ...]:
    """Return transparent medication proxy feature names."""
    return ("vasopressor_name_proxy_flag", "antibiotic_name_proxy_flag")
