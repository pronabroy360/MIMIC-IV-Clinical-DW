"""Train a simple mortality baseline on aggregate-safe Gold features."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from src.core.config import WarehouseConfig
from src.core.db import connect


@dataclass(frozen=True)
class BaselineResult:
    """Aggregate model evaluation metrics."""

    model_name: str
    split_rows_train: int
    split_rows_test: int
    auroc: float
    auprc: float
    f1: float
    precision: float
    recall: float
    brier_score: float


FEATURE_COLUMNS = [
    "age_at_admission",
    "heart_rate_mean",
    "sbp_mean",
    "dbp_mean",
    "mbp_mean",
    "resp_rate_mean",
    "temperature_mean",
    "spo2_mean",
    "wbc_mean",
    "hemoglobin_mean",
    "platelet_mean",
    "creatinine_mean",
    "bun_mean",
    "sodium_mean",
    "potassium_mean",
    "glucose_mean",
    "lactate_mean",
    "chart_event_count_24h",
    "lab_event_count_24h",
    "input_event_count_24h",
    "output_event_count_24h",
    "procedure_event_count_24h",
]


def _fetch_training_data(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    selected = ", ".join(FEATURE_COLUMNS + ["hospital_mortality_flag", "subject_id"])
    df = con.execute(
        f"""
        SELECT {selected}
        FROM gold_mortality_model_dataset
        WHERE hospital_mortality_flag IS NOT NULL
        """
    ).fetchdf()
    return df


def _split_by_subject(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    subjects = sorted(df["subject_id"].dropna().unique().tolist())
    split = max(1, int(len(subjects) * 0.8))
    train_subjects = set(subjects[:split])
    train_df = df[df["subject_id"].isin(train_subjects)].copy()
    test_df = df[~df["subject_id"].isin(train_subjects)].copy()
    if test_df.empty:
        test_df = train_df.tail(max(1, len(train_df) // 5)).copy()
        train_df = train_df.drop(test_df.index)
    return train_df, test_df


def train_logistic_baseline(config: WarehouseConfig) -> BaselineResult:
    """Train a logistic regression baseline and return aggregate metrics."""
    try:
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import (
            average_precision_score,
            brier_score_loss,
            f1_score,
            precision_score,
            recall_score,
            roc_auc_score,
        )
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "scikit-learn is required for ml-baseline. Install via `pip install scikit-learn`."
        ) from exc

    with connect(config) as con:
        df = _fetch_training_data(con)

    if df.empty or df["hospital_mortality_flag"].nunique() < 2:
        raise RuntimeError(
            "Not enough class diversity in gold_mortality_model_dataset to train baseline."
        )

    train_df, test_df = _split_by_subject(df)
    if train_df.empty or test_df.empty:
        raise RuntimeError("Unable to create non-empty train/test splits.")

    X_train = train_df[FEATURE_COLUMNS]
    X_test = test_df[FEATURE_COLUMNS]
    keep_cols = [column for column in FEATURE_COLUMNS if not X_train[column].isna().all()]
    if not keep_cols:
        raise RuntimeError("No usable feature columns found after null filtering.")
    X_train = X_train[keep_cols]
    X_test = X_test[keep_cols]
    y_train = train_df["hospital_mortality_flag"].astype(int)
    y_test = test_df["hospital_mortality_flag"].astype(int)

    imputer = SimpleImputer(strategy="median")
    X_train_i = imputer.fit_transform(X_train)
    X_test_i = imputer.transform(X_test)

    model = LogisticRegression(max_iter=1000, random_state=42)
    model.fit(X_train_i, y_train)
    probs = model.predict_proba(X_test_i)[:, 1]
    preds = (probs >= 0.5).astype(int)

    auroc = float("nan")
    if y_test.nunique() >= 2:
        auroc = float(roc_auc_score(y_test, probs))

    auprc = float("nan")
    if int(y_test.sum()) > 0:
        auprc = float(average_precision_score(y_test, probs))

    return BaselineResult(
        model_name="logistic_regression",
        split_rows_train=int(len(train_df)),
        split_rows_test=int(len(test_df)),
        auroc=auroc,
        auprc=auprc,
        f1=float(f1_score(y_test, preds, zero_division=0)),
        precision=float(precision_score(y_test, preds, zero_division=0)),
        recall=float(recall_score(y_test, preds, zero_division=0)),
        brier_score=float(brier_score_loss(y_test, probs)),
    )


def write_baseline_outputs(config: WarehouseConfig, result: BaselineResult) -> tuple[Path, Path]:
    """Write aggregate baseline metrics to public output files."""
    out_dir = config.outputs_public_path / "aggregate_results"
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / "ml_baseline_metrics.csv"
    md_path = out_dir / "ml_baseline_metrics.md"

    pd.DataFrame(
        [
            {
                "model_name": result.model_name,
                "split_rows_train": result.split_rows_train,
                "split_rows_test": result.split_rows_test,
                "auroc": result.auroc,
                "auprc": result.auprc,
                "f1": result.f1,
                "precision": result.precision,
                "recall": result.recall,
                "brier_score": result.brier_score,
            }
        ]
    ).to_csv(csv_path, index=False)

    auroc_text = "nan (single-class test split)" if np.isnan(result.auroc) else f"{result.auroc:.4f}"
    auprc_text = "nan (no positive labels in test split)" if np.isnan(result.auprc) else f"{result.auprc:.4f}"
    md_path.write_text(
        "\n".join(
            [
                "# ML Baseline Metrics",
                "",
                "- Model: logistic_regression",
                f"- Train rows: {result.split_rows_train}",
                f"- Test rows: {result.split_rows_test}",
                f"- AUROC: {auroc_text}",
                f"- AUPRC: {auprc_text}",
                f"- F1: {result.f1:.4f}",
                f"- Precision: {result.precision:.4f}",
                f"- Recall: {result.recall:.4f}",
                f"- Brier score: {result.brier_score:.4f}",
                "",
                "This baseline is for research demonstration only and is not clinical decision support.",
                "",
            ]
        )
    )
    return csv_path, md_path
