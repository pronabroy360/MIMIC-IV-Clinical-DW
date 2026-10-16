"""Shared study validation, preview, execution, and publication service."""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd

from src.core.config import WarehouseConfig
from src.core.db import connect
from src.research.cohorts import cohort_flow
from src.research.contracts import StudySpec, load_study_spec
from src.research.features import FEATURE_TABLE, build_prospective_feature_table, feature_audit
from src.research.interpretation import linear_attribution_summary, verify_linear_additivity
from src.research.publication import publish_study_package
from src.research.tasks import task_definition
from src.research.timing import timing_audit


def _code_revision() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def load_and_validate(path: str | Path) -> StudySpec:
    """Public validation entry point used consistently by all adapters."""
    return load_study_spec(path)


def preview_study(config: WarehouseConfig, spec: StudySpec) -> dict[str, object]:
    """Compile a study and return aggregate flow and timing evidence."""
    with connect(config) as con:
        return {
            "study_id": spec.study_id,
            "definition_hash": spec.definition_hash,
            "cohort_flow": cohort_flow(con, spec),
            "timing_audit": timing_audit(con, spec),
            "dataset_snapshot": _dataset_snapshot(con),
        }


def _dataset_snapshot(con) -> str:
    rows = con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main' AND table_name LIKE 'silver_%' ORDER BY table_name"
    ).fetchall()
    payload = json.dumps(rows, default=str, separators=(",", ":"))
    import hashlib
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _split_frame(frame: pd.DataFrame, seed: int, proportions: tuple[float, float, float]) -> pd.DataFrame:
    subjects = np.random.default_rng(seed).permutation(frame["subject_id"].dropna().unique())
    train_end = int(proportions[0] * len(subjects))
    validation_end = train_end + int(proportions[1] * len(subjects))
    mapping = {subject: "train" for subject in subjects[:train_end]}
    mapping.update({subject: "validation" for subject in subjects[train_end:validation_end]})
    mapping.update({subject: "test" for subject in subjects[validation_end:]})
    result = frame.copy()
    result["split"] = result.subject_id.map(mapping)
    return result


def _bootstrap_binary_metrics(target: pd.Series, probability: np.ndarray, seed: int, replicates: int = 200) -> dict[str, object]:
    """Return patient-row bootstrap intervals, or an explicit reason when unavailable."""
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

    y = np.asarray(target)
    if len(y) < 2 or len(np.unique(y)) < 2:
        return {"status": "not_estimable", "reason": "test partition has one outcome class"}
    rng = np.random.default_rng(seed)
    values: dict[str, list[float]] = {"auroc": [], "auprc": [], "brier": []}
    for _ in range(replicates):
        index = rng.integers(0, len(y), len(y))
        sample_y, sample_p = y[index], probability[index]
        if len(np.unique(sample_y)) < 2:
            continue
        values["auroc"].append(float(roc_auc_score(sample_y, sample_p)))
        values["auprc"].append(float(average_precision_score(sample_y, sample_p)))
        values["brier"].append(float(brier_score_loss(sample_y, sample_p)))
    if not values["auroc"]:
        return {"status": "not_estimable", "reason": "bootstrap samples had one outcome class"}
    return {
        "status": "estimable", "unit": "eligible patient rows", "replicates": len(values["auroc"]),
        "intervals_95": {metric: [float(np.quantile(scores, 0.025)), float(np.quantile(scores, 0.975))] for metric, scores in values.items()},
    }


def _evaluate(frame: pd.DataFrame, spec: StudySpec) -> tuple[pd.DataFrame, dict[str, object], pd.DataFrame]:
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
    from sklearn.model_selection import RepeatedStratifiedKFold, cross_val_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    task = task_definition(spec.task_name)
    feature_columns = list(task.numeric_features + task.categorical_features)
    frame = _split_frame(frame, spec.seed, spec.proportions)
    train = frame[frame.split == "train"]
    validation = frame[frame.split == "validation"]
    test = frame[frame.split == "test"]
    if min(len(train), len(validation), len(test)) == 0 or train[task.target_column].nunique() < 2:
        raise RuntimeError("insufficient eligible rows or outcome classes for study evaluation")
    preprocessing = ColumnTransformer([
        ("numeric", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), list(task.numeric_features)),
        ("categorical", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("encode", OneHotEncoder(handle_unknown="ignore"))]), list(task.categorical_features)),
    ])
    pipeline = Pipeline([("preprocess", preprocessing), ("model", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=spec.seed))])
    pipeline.fit(train[feature_columns], train[task.target_column])
    validation_probability = pipeline.predict_proba(validation[feature_columns])[:, 1]
    test_probability = pipeline.predict_proba(test[feature_columns])[:, 1]
    cv = RepeatedStratifiedKFold(n_splits=spec.cv_folds, n_repeats=spec.cv_repeats, random_state=spec.seed)
    development = pd.concat([train, validation], ignore_index=True)
    cv_scores = cross_val_score(pipeline, development[feature_columns], development[task.target_column], cv=cv, scoring="average_precision", n_jobs=2)
    summary = {
        "target": task.target_column,
        "selection_partition": "validation",
        "stability_partition": "train_plus_validation",
        "locked_test_partition": "test",
        "train_rows": len(train), "validation_rows": len(validation), "test_rows": len(test),
        "test_auroc": float(roc_auc_score(test[task.target_column], test_probability)),
        "test_auprc": float(average_precision_score(test[task.target_column], test_probability)),
        "test_brier": float(brier_score_loss(test[task.target_column], test_probability)),
        "validation_auprc": float(average_precision_score(validation[task.target_column], validation_probability)),
        "development_cv_auprc_mean": float(np.mean(cv_scores)),
        "development_cv_auprc_std": float(np.std(cv_scores)),
        "test_bootstrap_uncertainty": _bootstrap_binary_metrics(test[task.target_column], test_probability, spec.seed),
        "linear_additivity_verified": verify_linear_additivity(pipeline, test, feature_columns),
    }
    models = pd.DataFrame([{"model": "logistic_regression", **summary}])
    attribution = linear_attribution_summary(pipeline, test, feature_columns)
    return models, summary, attribution


def run_study(config: WarehouseConfig, spec: StudySpec) -> dict[str, object]:
    """Execute a validated synthetic study and persist private aggregate artifacts."""
    if config.mode != "demo" or config.raw_data_path is None or "research-synthetic" not in config.raw_data_path.parts:
        raise ValueError("The study service only accepts the isolated invented research dataset")
    run_id = f"{spec.study_id}-{uuid4().hex[:8]}"
    run_dir = config.outputs_private_path / "studies" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    manifest: dict[str, object] = {
        "schema_version": 1, "run_id": run_id, "study_id": spec.study_id,
        "definition_hash": spec.definition_hash, "dataset_origin": "synthetic_invented",
        "status": "running", "created_at": datetime.now(timezone.utc).isoformat(),
        "code_revision": _code_revision(), "python": platform.python_version(),
        "study_definition": spec.canonical_dict(),
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    try:
        with connect(config) as con:
            snapshot = _dataset_snapshot(con)
            flow = cohort_flow(con, spec)
            timing = timing_audit(con, spec)
            build_prospective_feature_table(con, spec)
            audit = feature_audit(con, spec)
            frame = con.execute(f"SELECT * FROM {FEATURE_TABLE}").fetchdf()
        models, evaluation, attribution = _evaluate(frame, spec)
        pd.DataFrame(flow).to_csv(run_dir / "cohort_flow.csv", index=False)
        pd.DataFrame(timing).to_csv(run_dir / "timing_audit.csv", index=False)
        pd.DataFrame(audit).to_csv(run_dir / "feature_audit.csv", index=False)
        models.to_csv(run_dir / "model_comparison.csv", index=False)
        attribution.to_csv(run_dir / "linear_attributions.csv", index=False)
        quality = {"status": "pass", "blocking_failures": [], "feature_table": FEATURE_TABLE}
        (run_dir / "quality_summary.json").write_text(json.dumps(quality, indent=2, sort_keys=True) + "\n")
        (run_dir / "evaluation_summary.json").write_text(json.dumps(evaluation, indent=2, sort_keys=True) + "\n")
        (run_dir / "README.md").write_text(
            "# Synthetic prospective ICU mortality study\n\n"
            "All rows were generated by this repository. This package contains aggregate evidence only. "
            "It demonstrates software behavior and cannot support clinical conclusions.\n"
        )
        manifest.update({"status": "succeeded", "dataset_snapshot": snapshot, "completed_at": datetime.now(timezone.utc).isoformat()})
    except Exception as exc:
        manifest.update({"status": "failed", "error": str(exc), "completed_at": datetime.now(timezone.utc).isoformat()})
        (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        raise
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return {"run_id": run_id, "run_dir": run_dir, "manifest": manifest, "evaluation": evaluation}


def publish_run(config: WarehouseConfig, run_id: str) -> Path:
    """Publish the aggregate-only package for a successful local synthetic run."""
    return publish_study_package(config.outputs_private_path / "studies" / run_id, config.outputs_public_path / "studies")


def run_status(config: WarehouseConfig, run_id: str) -> dict[str, object]:
    """Return sanitized run state without exposing local output paths."""
    manifest_path = config.outputs_private_path / "studies" / run_id / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(run_id)
    manifest = json.loads(manifest_path.read_text())
    allowed = ("run_id", "study_id", "definition_hash", "dataset_origin", "dataset_snapshot", "status", "created_at", "completed_at", "code_revision", "python")
    return {key: manifest[key] for key in allowed if key in manifest}
