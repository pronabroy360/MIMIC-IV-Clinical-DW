"""Diagnosis feature helper SQL snippets."""

DIAGNOSIS_FEATURE_TABLE = "gold_diagnosis_features"


def diagnosis_proxy_columns() -> tuple[str, ...]:
    """Return transparent diagnosis proxy feature names."""
    return (
        "sepsis_diagnosis_proxy_flag",
        "heart_failure_flag",
        "respiratory_failure_flag",
        "renal_dysfunction_proxy_flag",
        "diabetes_flag",
        "pneumonia_flag",
    )
