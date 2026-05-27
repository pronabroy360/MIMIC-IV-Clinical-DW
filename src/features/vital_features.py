"""Vital feature helper SQL snippets."""

VITAL_FEATURE_TABLE = "gold_vital_features"


def vital_availability_columns() -> tuple[str, ...]:
    """Return first-24-hour vital availability flags."""
    return (
        "has_heart_rate_24h",
        "has_blood_pressure_24h",
        "has_resp_rate_24h",
        "has_temperature_24h",
        "has_spo2_24h",
    )
