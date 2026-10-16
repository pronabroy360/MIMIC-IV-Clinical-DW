"""Signed, baseline-centred linear-model interpretation utilities."""

from __future__ import annotations

import numpy as np
import pandas as pd


def linear_attribution_summary(pipeline, frame: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Aggregate signed coefficients and exact linear contributions on model scale.

    For binary logistic models contributions are on log-odds. For regression
    models they are on the outcome scale. The intercept plus each transformed
    feature contribution reconstructs the model's linear decision function.
    """
    model = pipeline.named_steps["model"]
    if not hasattr(model, "coef_"):
        return pd.DataFrame(columns=["feature", "coefficient", "mean_contribution", "mean_abs_contribution", "output_scale"])
    transformed = pipeline.named_steps["preprocess"].transform(frame[features])
    if hasattr(transformed, "toarray"):
        transformed = transformed.toarray()
    coefficients = np.asarray(model.coef_)
    if coefficients.ndim == 2:
        if coefficients.shape[0] != 1:
            return pd.DataFrame(columns=["feature", "coefficient", "mean_contribution", "mean_abs_contribution", "output_scale"])
        coefficients = coefficients[0]
    contributions = np.asarray(transformed) * coefficients
    names = pipeline.named_steps["preprocess"].get_feature_names_out()
    scale = "log_odds" if hasattr(model, "predict_proba") else "outcome"
    return pd.DataFrame({
        "feature": names,
        "coefficient": coefficients,
        "mean_contribution": contributions.mean(axis=0),
        "mean_abs_contribution": np.abs(contributions).mean(axis=0),
        "output_scale": scale,
    })


def verify_linear_additivity(pipeline, frame: pd.DataFrame, features: list[str], tolerance: float = 1e-9) -> bool:
    """Verify the documented intercept-plus-contribution relationship."""
    model = pipeline.named_steps["model"]
    if not hasattr(model, "coef_") or np.asarray(model.coef_).ndim != 1:
        return True
    transformed = pipeline.named_steps["preprocess"].transform(frame[features])
    if hasattr(transformed, "toarray"):
        transformed = transformed.toarray()
    reconstructed = float(model.intercept_[0]) + np.asarray(transformed) @ np.asarray(model.coef_)
    return bool(np.allclose(reconstructed, pipeline.decision_function(frame[features]), atol=tolerance))
