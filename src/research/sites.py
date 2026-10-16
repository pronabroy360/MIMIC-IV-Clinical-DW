"""Invented two-site transferability experiment with isolated source workspaces."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from src.core.config import WarehouseConfig
from src.core.db import connect
from src.ingest.load_demo import load_local_files
from src.research.features import FEATURE_TABLE, build_prospective_feature_table
from src.research.scenarios import _delay_lab_storetime
from src.research.seed import seed_research_cohort
from src.research.tasks import task_definition
from src.transform.build_gold import build_gold


def prepare_simulated_site(config: WarehouseConfig, site_id: str, seed: int) -> WarehouseConfig:
    """Create a deterministic invented site with a documented measurement shift."""
    if site_id not in {"site_a", "site_b"}:
        raise ValueError("site_id must be site_a or site_b")
    root = config.outputs_private_path / "studies" / "sites" / site_id
    site = replace(
        config,
        database_path=root / "site.duckdb",
        raw_data_path=root / "raw" / "research-synthetic",
        outputs_private_path=root / "private",
        outputs_public_path=root / "public",
    )
    seed_research_cohort(site, patients=600, seed=seed)
    if site_id == "site_b":
        _delay_lab_storetime(site.raw_data_path / "hosp" / "labevents.csv", every_nth=3)
    load_local_files(site)
    build_gold(site)
    return site


def evaluate_site_transferability(site_a: WarehouseConfig, site_b: WarehouseConfig, spec) -> dict[str, float | int | str]:
    """Fit only on site A and evaluate unchanged preprocessing/model on site B."""
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    task = task_definition(spec.task_name)
    features = list(task.numeric_features + task.categorical_features)
    frames = []
    for config, site_id in ((site_a, "site_a"), (site_b, "site_b")):
        with connect(config) as con:
            build_prospective_feature_table(con, spec)
            frame = con.execute(f"SELECT * FROM {FEATURE_TABLE}").fetchdf()
        frame["site_id"] = site_id
        frames.append(frame)
    a, b = frames
    split = np.random.default_rng(spec.seed).permutation(a.index)
    train = a.loc[split[: int(len(split) * 0.7)]]
    test_a = a.loc[split[int(len(split) * 0.85):]]
    b_split = np.random.default_rng(spec.seed + 1).permutation(b.index)
    calibration_b = b.loc[b_split[: int(len(b_split) * 0.2)]]
    test_b = b.loc[b_split[int(len(b_split) * 0.2):]]
    preprocess = ColumnTransformer([
        ("numeric", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), list(task.numeric_features)),
        ("categorical", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("encode", OneHotEncoder(handle_unknown="ignore"))]), list(task.categorical_features)),
    ])
    pipeline = Pipeline([("preprocess", preprocess), ("model", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=spec.seed))])
    pipeline.fit(train[features], train[task.target_column])
    def scores(frame, prefix: str):
        probability = pipeline.predict_proba(frame[features])[:, 1]
        target = frame[task.target_column]
        return {
            f"{prefix}_rows": len(frame),
            f"{prefix}_prevalence": float(target.mean()),
            f"{prefix}_auroc": float(roc_auc_score(target, probability)),
            f"{prefix}_auprc": float(average_precision_score(target, probability)),
            f"{prefix}_brier": float(brier_score_loss(target, probability)),
        }
    result = scores(test_a, "site_a_test")
    result.update(scores(test_b, "site_b_test"))
    result["site_b_calibration_rows"] = len(calibration_b)
    result["site_b_mean_available_lab_events_24h"] = float(test_b.lab_event_count_24h.mean())
    result["site_a_mean_available_lab_events_24h"] = float(test_a.lab_event_count_24h.mean())
    if calibration_b[task.target_column].nunique() < 2:
        result["site_b_recalibration_status"] = "not_estimable_one_class_calibration_partition"
        return result
    calibrator = LogisticRegression(random_state=spec.seed)
    calibrator.fit(
        pipeline.predict_proba(calibration_b[features])[:, 1].reshape(-1, 1),
        calibration_b[task.target_column],
    )
    recalibrated_probability = calibrator.predict_proba(
        pipeline.predict_proba(test_b[features])[:, 1].reshape(-1, 1)
    )[:, 1]
    result["site_b_recalibration_status"] = "platt_scaling_on_disjoint_site_b_calibration_partition"
    result["site_b_recalibrated_brier"] = float(brier_score_loss(test_b[task.target_column], recalibrated_probability))
    result["site_b_recalibrated_auroc"] = float(roc_auc_score(test_b[task.target_column], recalibrated_probability))
    result["site_b_recalibrated_auprc"] = float(average_precision_score(test_b[task.target_column], recalibrated_probability))
    return result
