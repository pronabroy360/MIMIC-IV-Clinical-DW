"""Lab feature helper SQL snippets."""

LAB_FEATURE_TABLE = "gold_lab_features"


def lab_feature_columns() -> tuple[str, ...]:
    """Return public aggregate lab feature columns."""
    return (
        "total_lab_events",
        "distinct_lab_tests",
        "abnormal_lab_rate",
        "lactate_measured_during_icu",
        "creatinine_measured_during_icu",
    )
