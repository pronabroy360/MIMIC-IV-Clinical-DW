"""Frozen-model paired comparison of a valid synthetic data perturbation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.core.config import WarehouseConfig
from src.core.db import connect
from src.research.contracts import StudySpec
from src.research.features import FEATURE_TABLE, build_prospective_feature_table
from src.research.tasks import task_definition


def _source_hash(config: WarehouseConfig) -> str:
    if config.raw_data_path is None:
        raise ValueError("A source path is required for integrity comparison")
    root = config.raw_data_path.resolve()
    digest = hashlib.sha256()
    for path in sorted(config.raw_data_path.rglob("*")):
        if path.is_file():
            resolved = path.resolve()
            if resolved != root and root not in resolved.parents:
                raise ValueError("Comparison source contains a symlink outside its data root")
            digest.update(path.relative_to(config.raw_data_path).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float] | None:
    if len(y) == 0 or len(np.unique(y)) < 2:
        return None
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
    return {
        "auroc": float(roc_auc_score(y, p)),
        "auprc": float(average_precision_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
    }


def _paired_bootstrap(y: np.ndarray, p_base: np.ndarray, p_scenario: np.ndarray, seed: int, replicates: int = 300) -> dict[str, object]:
    if len(y) < 2 or len(np.unique(y)) < 2:
        return {"status": "not_estimable", "reason": "paired eligible subset has one outcome class"}
    rng = np.random.default_rng(seed)
    diffs: dict[str, list[float]] = {"auroc": [], "auprc": [], "brier": []}
    for _ in range(replicates):
        idx = rng.integers(0, len(y), len(y))
        base = _metrics(y[idx], p_base[idx])
        changed = _metrics(y[idx], p_scenario[idx])
        if base is None or changed is None:
            continue
        for metric in diffs:
            diffs[metric].append(changed[metric] - base[metric])
    if not diffs["auroc"]:
        return {"status": "not_estimable", "reason": "bootstrap samples had one outcome class"}
    return {
        "status": "estimable", "unit": "paired eligible patient rows", "replicates": len(diffs["auroc"]),
        "scenario_minus_baseline_95_intervals": {
            metric: [float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))]
            for metric, values in diffs.items()
        },
    }


def compare_frozen_scenario(baseline_config: WarehouseConfig, scenario_config: WarehouseConfig, spec: StudySpec, output_path: Path | None = None) -> dict[str, object]:
    """Fit only on baseline development patients and compare same patients.

    Baseline and scenario partitions share a deterministic subject split. The
    estimator and preprocessing are fitted once on baseline training rows and
    are never refit on scenario or test data.
    """
    if baseline_config.mode != "demo" or scenario_config.mode != "demo":
        raise ValueError("Frozen comparisons only accept invented demo configurations")
    if baseline_config.raw_data_path is None or scenario_config.raw_data_path is None:
        raise ValueError("Both comparison inputs must have explicit synthetic sources")
    if "research-synthetic" not in baseline_config.raw_data_path.parts or "research-synthetic" not in scenario_config.raw_data_path.parts:
        raise ValueError("Both comparison inputs must come from the isolated research-synthetic source")
    baseline_hash_before = _source_hash(baseline_config)
    task = task_definition(spec.task_name)
    columns = list(task.numeric_features + task.categorical_features)
    frames = []
    for config in (baseline_config, scenario_config):
        with connect(config) as con:
            build_prospective_feature_table(con, spec)
            frame = con.execute(f"SELECT subject_id, stay_id, {task.target_column}, {', '.join(columns)} FROM {FEATURE_TABLE}").fetchdf()
        frames.append(frame)
    baseline, scenario = frames

    subject_ids = np.random.default_rng(spec.seed).permutation(baseline.subject_id.dropna().unique())
    train_end = int(spec.proportions[0] * len(subject_ids))
    validation_end = train_end + int(spec.proportions[1] * len(subject_ids))
    train_subjects = set(subject_ids[:train_end])
    test_subjects = set(subject_ids[validation_end:])
    train = baseline[baseline.subject_id.isin(train_subjects)]
    if train.empty or train[task.target_column].nunique() < 2:
        raise RuntimeError("baseline training partition has insufficient outcome classes")

    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    preprocess = ColumnTransformer([
        ("numeric", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), list(task.numeric_features)),
        ("categorical", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("encode", OneHotEncoder(handle_unknown="ignore"))]), list(task.categorical_features)),
    ])
    pipeline = Pipeline([("preprocess", preprocess), ("model", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=spec.seed))])
    pipeline.fit(train[columns], train[task.target_column])

    baseline_test = baseline[baseline.subject_id.isin(test_subjects)].set_index("stay_id", verify_integrity=True)
    scenario_test = scenario[scenario.subject_id.isin(test_subjects)].set_index("stay_id", verify_integrity=True)
    common = baseline_test.index.intersection(scenario_test.index)
    paired_base, paired_scenario = baseline_test.loc[common], scenario_test.loc[common]
    base_y = paired_base[task.target_column].to_numpy(dtype=int)
    scenario_y = paired_scenario[task.target_column].to_numpy(dtype=int)
    if not np.array_equal(base_y, scenario_y):
        raise ValueError("Scenario changed outcome labels; frozen input comparison requires invariant outcomes")
    p_base = pipeline.predict_proba(paired_base[columns])[:, 1]
    p_scenario = pipeline.predict_proba(paired_scenario[columns])[:, 1]
    result: dict[str, object] = {
        "schema_version": 1,
        "comparison": "frozen_model_paired_common_test_patients",
        "scenario_source_hash": _source_hash(scenario_config),
        "baseline_source_hash_before": baseline_hash_before,
        "baseline_source_hash_after": _source_hash(baseline_config),
        "baseline_test_eligible_rows": len(baseline_test),
        "scenario_test_eligible_rows": len(scenario_test),
        "common_test_rows": len(common),
        "baseline_only_test_rows": len(baseline_test.index.difference(scenario_test.index)),
        "scenario_only_test_rows": len(scenario_test.index.difference(baseline_test.index)),
        "outcome_labels_invariant_on_common_rows": True,
        "frozen_estimator_fit_partition": "baseline_train_only",
        "paired_baseline_metrics": _metrics(base_y, p_base),
        "paired_scenario_metrics": _metrics(scenario_y, p_scenario),
        "paired_uncertainty": _paired_bootstrap(base_y, p_base, p_scenario, spec.seed),
        "all_baseline_test_metrics": _metrics(baseline_test[task.target_column].to_numpy(dtype=int), pipeline.predict_proba(baseline_test[columns])[:, 1]) if len(baseline_test) else None,
        "all_scenario_test_metrics": _metrics(scenario_test[task.target_column].to_numpy(dtype=int), pipeline.predict_proba(scenario_test[columns])[:, 1]) if len(scenario_test) else None,
    }
    result["baseline_unchanged"] = result["baseline_source_hash_before"] == result["baseline_source_hash_after"]
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result
