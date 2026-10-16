"""Aggregate-only evaluation of an invented EHR teaching cohort."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.core.config import WarehouseConfig
from src.core.db import connect, row_count
from src.research.config import (
    feature_names, leakage_rules, predictor_availability, predictor_sources,
    validate_research_frame,
)

NUMERIC_FEATURES = feature_names("numeric")
CATEGORICAL_FEATURES = feature_names("categorical")
PREDICTORS = NUMERIC_FEATURES + CATEGORICAL_FEATURES
PREDICTOR_SOURCES = predictor_sources()
OUTCOMES = tuple(leakage_rules()["outcomes"])
FORBIDDEN_PREDICTORS = tuple(leakage_rules()["forbidden_predictors"])


@dataclass(frozen=True)
class Evaluation:
    task: str
    metric: str
    model: str
    validation_score: float
    selected: bool
    test_scores: dict[str, float] | None = None


def _model_pipeline(estimator):
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    preprocess = ColumnTransformer(
        [
            ("numeric", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), list(NUMERIC_FEATURES)),
            ("categorical", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("encode", OneHotEncoder(handle_unknown="ignore"))]), list(CATEGORICAL_FEATURES)),
        ]
    )
    return Pipeline([("preprocess", preprocess), ("model", estimator)])


def _classification_scores(y_true: pd.Series, predicted: np.ndarray, probabilities: np.ndarray | None, multiclass: bool = False) -> dict[str, float]:
    from sklearn.metrics import (
        average_precision_score, balanced_accuracy_score, brier_score_loss,
        f1_score, precision_score, recall_score, roc_auc_score,
    )

    if multiclass:
        return {
            "macro_f1": float(f1_score(y_true, predicted, average="macro", zero_division=0)),
            "balanced_accuracy": float(balanced_accuracy_score(y_true, predicted)),
        }
    y = y_true.astype(int)
    result = {
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "specificity": float(((y == 0) & (predicted == 0)).sum() / max(1, (y == 0).sum())),
    }
    if probabilities is not None:
        result["brier"] = float(brier_score_loss(y, probabilities))
        result["auroc"] = float(roc_auc_score(y, probabilities)) if y.nunique() > 1 else float("nan")
        result["auprc"] = float(average_precision_score(y, probabilities)) if int(y.sum()) else float("nan")
    return result


def _regression_scores(y_true: pd.Series, predicted: np.ndarray) -> dict[str, float]:
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    return {
        "mae": float(mean_absolute_error(y_true, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, predicted))),
        "r2": float(r2_score(y_true, predicted)) if len(y_true) > 1 else float("nan"),
    }


def _split_subjects(frame: pd.DataFrame) -> pd.DataFrame:
    """Assign patients once, so repeat admissions cannot cross splits."""
    unique_subjects = frame["subject_id"].dropna().unique()
    shuffled = np.random.default_rng(42).permutation(unique_subjects)
    first = int(0.7 * len(shuffled))
    second = int(0.85 * len(shuffled))
    mapping = {subject: "train" for subject in shuffled[:first]}
    mapping.update({subject: "validation" for subject in shuffled[first:second]})
    mapping.update({subject: "test" for subject in shuffled[second:]})
    frame = frame.copy()
    frame["split"] = frame["subject_id"].map(mapping)
    return frame


def _linear_attributions(pipeline) -> list[tuple[str, float, float]]:
    """Return aggregate linear coefficients and baseline-centred contribution magnitudes.

    This is a transparent SHAP-style additive attribution for linear models,
    not an invocation of the external SHAP package.
    """
    model = pipeline.named_steps["model"]
    if not hasattr(model, "coef_"):
        return []
    names = pipeline.named_steps["preprocess"].get_feature_names_out()
    coefficients = np.asarray(model.coef_)
    if coefficients.ndim == 2:
        coefficients = np.mean(np.abs(coefficients), axis=0)
    else:
        coefficients = np.abs(coefficients)
    return [(str(name), float(value), float(abs(value))) for name, value in zip(names, coefficients)]


def _repeated_cv_scores(frame: pd.DataFrame, target: str, criterion: str, estimator) -> list[float]:
    """Repeated development-set CV; the held-out test split remains untouched."""
    from sklearn.model_selection import RepeatedKFold, cross_val_score

    development = frame[frame["split"].isin(["train", "validation"])]
    scoring = {"mae": "neg_mean_absolute_error", "auprc": "average_precision", "macro_f1": "f1_macro"}[criterion]
    scores = cross_val_score(
        _model_pipeline(estimator), development[list(PREDICTORS)], development[target],
        cv=RepeatedKFold(n_splits=3, n_repeats=2, random_state=42), scoring=scoring, n_jobs=2,
    )
    return [float(-score if criterion == "mae" else score) for score in scores]


def _fit_tasks(frame: pd.DataFrame) -> tuple[list[Evaluation], dict[str, object]]:
    from sklearn.dummy import DummyClassifier, DummyRegressor
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.inspection import permutation_importance
    from sklearn.linear_model import ElasticNet, LogisticRegression

    specifications = (
        ("hospital_los_days", "mae", False, {
            "dummy_median": DummyRegressor(strategy="median"),
            "elastic_net": ElasticNet(alpha=0.05, l1_ratio=0.5, max_iter=3000, random_state=42),
            "random_forest": RandomForestRegressor(n_estimators=80, min_samples_leaf=5, random_state=42, n_jobs=2),
        }),
        ("in_hospital_mortality_flag", "auprc", False, {
            "dummy_prior": DummyClassifier(strategy="prior"),
            "logistic": LogisticRegression(max_iter=1500, class_weight="balanced", random_state=42),
            "random_forest": RandomForestClassifier(n_estimators=80, min_samples_leaf=5, random_state=42, n_jobs=2),
        }),
        ("urgent_readmitted_30d", "auprc", False, {
            "dummy_prior": DummyClassifier(strategy="prior"),
            "logistic": LogisticRegression(max_iter=1500, class_weight="balanced", random_state=42),
            "random_forest": RandomForestClassifier(n_estimators=80, min_samples_leaf=5, random_state=42, n_jobs=2),
        }),
        ("primary_disease_class", "macro_f1", True, {
            "dummy_frequent": DummyClassifier(strategy="most_frequent"),
            "logistic": LogisticRegression(max_iter=1500, random_state=42),
            "random_forest": RandomForestClassifier(n_estimators=80, min_samples_leaf=5, random_state=42, n_jobs=2),
        }),
    )
    records: list[Evaluation] = []
    details: dict[str, object] = {}
    for target, criterion, multiclass, estimators in specifications:
        eligible = frame[frame[target].notna() & (frame["prediction_time"] <= frame["index_dischtime"])].copy()
        train = eligible[eligible["split"] == "train"]
        validation = eligible[eligible["split"] == "validation"]
        test = eligible[eligible["split"] == "test"]
        if min(len(train), len(validation), len(test)) == 0 or train[target].nunique() < 2:
            details[target] = {"status": "insufficient eligible rows or classes", "rows": len(eligible)}
            continue
        fitted = {}
        validation_scores = {}
        for name, estimator in estimators.items():
            pipeline = _model_pipeline(estimator)
            pipeline.fit(train[list(PREDICTORS)], train[target])
            predicted = pipeline.predict(validation[list(PREDICTORS)])
            if target == "hospital_los_days":
                score = _regression_scores(validation[target], predicted)[criterion]
            elif multiclass:
                score = _classification_scores(validation[target], predicted, None, True)[criterion]
            else:
                positive = list(pipeline.classes_).index(1)
                probabilities = pipeline.predict_proba(validation[list(PREDICTORS)])[:, positive]
                score = _classification_scores(validation[target], predicted, probabilities)[criterion]
            fitted[name] = pipeline
            validation_scores[name] = score

        best = min(validation_scores, key=validation_scores.get) if criterion == "mae" else max(validation_scores, key=validation_scores.get)
        details[f"{target}_repeated_cv"] = _repeated_cv_scores(eligible, target, criterion, estimators[best])
        if best in {"elastic_net", "logistic"}:
            details[f"{target}_linear_attributions"] = _linear_attributions(fitted[best])
        if not best.startswith("dummy"):
            scoring = {
                "mae": "neg_mean_absolute_error",
                "auprc": "average_precision",
                "macro_f1": "f1_macro",
            }[criterion]
            importance = permutation_importance(
                fitted[best], validation[list(PREDICTORS)], validation[target],
                scoring=scoring, n_repeats=2, random_state=42, n_jobs=2,
            )
            details[f"{target}_importance"] = sorted(
                zip(PREDICTORS, importance.importances_mean),
                key=lambda pair: pair[1], reverse=True,
            )[:8]
        for name, score in validation_scores.items():
            test_scores = None
            if name == best:
                pipeline = fitted[name]
                predicted = pipeline.predict(test[list(PREDICTORS)])
                if target == "hospital_los_days":
                    test_scores = _regression_scores(test[target], predicted)
                    residuals = pd.DataFrame({"residual_days": test[target].to_numpy() - predicted})
                    residuals["residual_band"] = pd.cut(
                        residuals["residual_days"],
                        bins=[-float("inf"), -2, -1, -0.5, 0.5, 1, 2, float("inf")],
                        labels=["<-2", "-2 to -1", "-1 to -0.5", "-0.5 to 0.5", "0.5 to 1", "1 to 2", ">2"],
                    )
                    details["hospital_los_days_residuals"] = [
                        (str(band), int(len(group)), float(group["residual_days"].mean()))
                        for band, group in residuals.groupby("residual_band", observed=False)
                    ]
                elif multiclass:
                    test_scores = _classification_scores(test[target], predicted, None, True)
                else:
                    positive = list(pipeline.classes_).index(1)
                    probabilities = pipeline.predict_proba(test[list(PREDICTORS)])[:, positive]
                    test_scores = _classification_scores(test[target], predicted, probabilities)
                    if target == "in_hospital_mortality_flag":
                        details["mortality_subgroups"] = _subgroup_scores(test, predicted)
                    details[f"{target}_calibration"] = _calibration_bins(test[target], probabilities)
            records.append(Evaluation(target, criterion, name, float(score), name == best, test_scores))
        details[target] = {
            "status": "evaluated", "rows": len(eligible), "train": len(train),
            "validation": len(validation), "test": len(test), "selected": best,
        }
    return records, details


def _subgroup_scores(test: pd.DataFrame, predicted: np.ndarray) -> list[tuple[str, str, int, float, float, float]]:
    rows = []
    for column in ("gender", "race"):
        for value in sorted(test[column].dropna().unique()):
            mask = (test[column] == value).to_numpy()
            if mask.sum() < 20:
                continue
            true = test.loc[mask, "in_hospital_mortality_flag"].astype(int).to_numpy()
            subgroup_predictions = predicted[mask]
            prevalence = float(true.mean())
            sensitivity = float(((subgroup_predictions == 1) & (true == 1)).sum() / max(1, (true == 1).sum()))
            specificity = float(((subgroup_predictions == 0) & (true == 0)).sum() / max(1, (true == 0).sum()))
            rows.append((column, str(value), int(mask.sum()), prevalence, sensitivity, specificity))
    return rows


def _calibration_bins(y_true: pd.Series, probabilities: np.ndarray) -> list[tuple[int, float, float]]:
    ranked = pd.DataFrame({"label": y_true.astype(int).to_numpy(), "probability": probabilities})
    ranked["bin"] = pd.qcut(ranked["probability"].rank(method="first"), 5, labels=False)
    return [
        (int(len(group)), float(group["probability"].mean()), float(group["label"].mean()))
        for _, group in ranked.groupby("bin", sort=True)
    ]


def _fmt(value: float | int) -> str:
    return "n/a" if not np.isfinite(value) else f"{value:.3f}"


def _write_aggregate_artifacts(output_dir: Path, frame: pd.DataFrame, evaluations: list[Evaluation], details: dict[str, object], missing: dict[str, float]) -> None:
    """Persist aggregate tables and interactive charts without exporting rows or predictions."""
    import plotly.express as px

    output_dir.mkdir(parents=True, exist_ok=True)
    chart_dir = output_dir / "charts"
    chart_dir.mkdir(exist_ok=True)
    availability = predictor_availability()
    pd.DataFrame([{"predictor": name, "source": PREDICTOR_SOURCES[name], "availability": availability[name], "missing_rate": missing[name]} for name in PREDICTORS]).to_csv(output_dir / "research_feature_dictionary.csv", index=False)
    pd.DataFrame([{"task": item.task, "model": item.model, "validation_metric": item.metric, "validation_score": item.validation_score, "selected": item.selected} for item in evaluations]).to_csv(output_dir / "research_model_comparison.csv", index=False)
    pd.DataFrame([{"feature": name, "count": int(frame[name].sum()), "rate": float(frame[name].mean())} for name in ("diabetes_flag", "heart_failure_flag", "respiratory_failure_flag", "sepsis_proxy_flag", "vasopressor_first_24h_flag", "ventilation_procedure_flag")]).to_csv(output_dir / "research_comorbidity_interventions.csv", index=False)
    importance_rows = [
        {"task": task.removesuffix("_importance"), "predictor": predictor, "validation_score_decrease": decrease}
        for task, values in details.items() if task.endswith("_importance")
        for predictor, decrease in values
    ]
    importance = pd.DataFrame(importance_rows)
    importance.to_csv(output_dir / "research_feature_importance.csv", index=False)
    coefficient_rows = [
        {"task": task.removesuffix("_linear_attributions"), "transformed_feature": feature, "coefficient": coefficient, "shap_style_abs_contribution": contribution}
        for task, values in details.items() if task.endswith("_linear_attributions")
        for feature, coefficient, contribution in values
    ]
    coefficients = pd.DataFrame(coefficient_rows)
    coefficients.to_csv(output_dir / "research_linear_coefficients_shap_style.csv", index=False)
    cv_rows = [
        {"task": task.removesuffix("_repeated_cv"), "fold": fold, "score": score}
        for task, values in details.items() if task.endswith("_repeated_cv")
        for fold, score in enumerate(values, start=1)
    ]
    repeated_cv = pd.DataFrame(cv_rows)
    repeated_cv.to_csv(output_dir / "research_repeated_cv.csv", index=False)
    calibration_rows = []
    for target in ("in_hospital_mortality_flag", "urgent_readmitted_30d"):
        for bin_number, (rows, predicted, observed) in enumerate(details.get(f"{target}_calibration", []), start=1):
            calibration_rows.append({"task": target, "bin": bin_number, "rows": rows, "mean_predicted_risk": predicted, "observed_rate": observed})
    calibration = pd.DataFrame(calibration_rows)
    calibration.to_csv(output_dir / "research_calibration.csv", index=False)
    missing_frame = pd.DataFrame({"predictor": list(missing), "missing_rate": list(missing.values())})
    missing_frame.to_csv(output_dir / "research_missingness_summary.csv", index=False)
    age_bins = pd.cut(frame["age_at_admission"], bins=[18, 35, 50, 65, 80, 101], right=False).value_counts().sort_index().rename_axis("age_band").reset_index(name="index_admissions")
    age_bins.to_csv(output_dir / "research_age_distribution.csv", index=False)
    residuals = pd.DataFrame(details.get("hospital_los_days_residuals", []), columns=["residual_band", "rows", "mean_residual_days"])
    residuals.to_csv(output_dir / "research_los_residuals.csv", index=False)
    age_bins["age_band"] = age_bins["age_band"].astype(str)
    px.bar(age_bins, x="age_band", y="index_admissions", title="Invented cohort: age bands").write_html(chart_dir / "research_age_distribution.html", include_plotlyjs="cdn")
    px.bar(missing_frame, x="predictor", y="missing_rate", title="Model-input missingness", range_y=[0, 1]).update_layout(xaxis_tickangle=-45).write_html(chart_dir / "research_missingness.html", include_plotlyjs="cdn")
    models = pd.read_csv(output_dir / "research_model_comparison.csv")
    px.bar(models, x="model", y="validation_score", color="selected", facet_col="task", title="Validation model comparison").write_html(chart_dir / "research_model_comparison.html", include_plotlyjs="cdn")
    if not calibration.empty:
        px.line(calibration, x="mean_predicted_risk", y="observed_rate", color="task", markers=True, title="Aggregate calibration").write_html(chart_dir / "research_calibration.html", include_plotlyjs="cdn")
    if not importance.empty:
        px.bar(importance, x="predictor", y="validation_score_decrease", color="task", barmode="group", title="Validation permutation importance").update_layout(xaxis_tickangle=-45).write_html(chart_dir / "research_feature_importance.html", include_plotlyjs="cdn")
    if not coefficients.empty:
        display_coefficients = coefficients.assign(abs_coefficient=coefficients["coefficient"].abs()).sort_values("abs_coefficient", ascending=False).head(30)
        px.bar(display_coefficients, x="transformed_feature", y="shap_style_abs_contribution", color="task", title="Linear SHAP-style aggregate contributions").update_layout(xaxis_tickangle=-45).write_html(chart_dir / "research_linear_shap_style.html", include_plotlyjs="cdn")
    if not repeated_cv.empty:
        px.box(repeated_cv, x="task", y="score", points="all", title="Repeated 3-fold development-set cross-validation").write_html(chart_dir / "research_repeated_cv.html", include_plotlyjs="cdn")
    if not residuals.empty:
        px.bar(residuals, x="residual_band", y="rows", hover_data=["mean_residual_days"], title="LOS holdout residual distribution").write_html(chart_dir / "research_los_residuals.html", include_plotlyjs="cdn")
    interventions = pd.read_csv(output_dir / "research_comorbidity_interventions.csv")
    px.bar(interventions, x="feature", y="rate", title="Transparent derived feature prevalence", range_y=[0, 1]).update_layout(xaxis_tickangle=-45).write_html(chart_dir / "research_comorbidity_interventions.html", include_plotlyjs="cdn")


def run_research_evaluation(config: WarehouseConfig) -> Path:
    """Evaluate the synthetic cohort and write a public aggregate Markdown report."""
    if config.mode != "demo" or config.raw_data_path is None or "research-synthetic" not in config.raw_data_path.parts:
        raise ValueError("Research evaluation only writes public outputs for the isolated synthetic config")
    if set(PREDICTORS) & set(FORBIDDEN_PREDICTORS):
        raise AssertionError("A future outcome or identifier entered the predictor set")
    if set(PREDICTORS) != set(PREDICTOR_SOURCES):
        raise AssertionError("Every model predictor needs explicit source documentation")

    with connect(config) as con:
        frame = con.execute("SELECT * FROM gold_research_index_admissions").fetchdf()
        counts = {table: row_count(con, table) for table in (
            "silver_patients", "silver_admissions", "silver_icustays", "gold_research_index_admissions"
        )}
    if frame.empty:
        raise RuntimeError("The index admission table is empty; build the synthetic warehouse first")
    validate_research_frame(frame)
    frame = _split_subjects(frame)
    evaluations, details = _fit_tasks(frame)
    valid_time = int((frame["prediction_time"] <= frame["index_dischtime"]).sum())
    missing = {name: float(frame[name].isna().mean()) for name in PREDICTORS}
    mortality = int(frame["in_hospital_mortality_flag"].sum())
    readmission = int(frame["urgent_readmitted_30d"].sum())
    disease_counts = frame["primary_disease_class"].fillna("unmapped").value_counts().sort_index()
    gender_counts = frame["gender"].fillna("unknown").value_counts().sort_index()

    lines = [
        "# Synthetic Research Demonstration",
        "",
        "All records in this run were invented by this repository's deterministic generator. Results demonstrate software behavior only; they are not MIMIC-IV findings or clinical evidence.",
        "",
        "## Cohort flow and quality",
        "",
        "| Step | Rows |",
        "| --- | ---: |",
        f"| Patients | {counts['silver_patients']} |",
        f"| Hospital admissions, including follow-up | {counts['silver_admissions']} |",
        f"| ICU stays | {counts['silver_icustays']} |",
        f"| Index admissions, one per patient | {counts['gold_research_index_admissions']} |",
        f"| Index admissions with full observation window | {valid_time} |",
        f"| Index deaths | {mortality} |",
        f"| Urgent 30-day readmissions among survivors | {readmission} |",
        "",
        "## Aggregate cohort profile",
        "",
        f"Mean age at admission: {_fmt(float(frame['age_at_admission'].mean()))} years. Median hospital LOS: {_fmt(float(frame['hospital_los_days'].median()))} days.",
        "",
        "| Synthetic primary diagnosis class | Index admissions |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {label} | {count} |" for label, count in disease_counts.items())
    lines.extend(["", "| Synthetic gender category | Index admissions |", "| --- | ---: |"])
    lines.extend(f"| {label} | {count} |" for label, count in gender_counts.items())
    lines.extend([
        "",
        "## Prediction times and leakage audit",
        "",
        "- Grain: first hospital admission per synthetic patient.",
        "- Prediction time: 24 hours after ICU entry when an ICU stay exists; otherwise 24 hours after hospital admission.",
        "- Chart and lab predictors are restricted to the first 24 hours after ICU entry in `gold_first_24h_features`.",
        "- LOS, death, later admissions, discharge time, and primary discharge diagnosis are outcomes or audit fields; none is a model predictor.",
        "- Patients are assigned once to fixed train, validation, and test splits (70/15/15); model choice uses validation scores only.",
        "- The readmission target is null for index deaths and requires a later urgent admission within 30 days after discharge.",
        "",
        "## Feature dictionary and missingness",
        "",
        "| Predictor | Source | Availability | Missing rate |",
        "| --- | --- | --- | ---: |",
    ])
    for name in PREDICTORS:
        lines.append(f"| `{name}` | {PREDICTOR_SOURCES[name]} | {predictor_availability()[name]} | {_fmt(missing[name])} |")
    lines.extend(["", "## Model comparison", "", "| Task | Model | Validation metric | Score | Selected |", "| --- | --- | --- | ---: | --- |"])
    for item in evaluations:
        lines.append(f"| {item.task} | {item.model} | {item.metric} | {_fmt(item.validation_score)} | {'yes' if item.selected else ''} |")
    lines.extend(["", "## Repeated development-set cross-validation", "", "The six repeated 3-fold scores below use only the train and validation partitions; the test partition remains held out.", "", "| Task | Runs | Mean score | Standard deviation |", "| --- | ---: | ---: | ---: |"])
    for target in OUTCOMES:
        scores = details.get(f"{target}_repeated_cv", [])
        if scores:
            lines.append(f"| {target} | {len(scores)} | {_fmt(float(np.mean(scores)))} | {_fmt(float(np.std(scores)))} |")
    lines.extend(["", "## Linear coefficients and Shapley-style contributions", "", "Aggregate coefficient and baseline-centred linear contribution tables are saved in `research_linear_coefficients_shap_style.csv`. They describe model behavior on invented data and are not an external SHAP calculation.", ""])
    lines.extend(["", "## Selected model holdout results", ""])
    for item in evaluations:
        if not item.selected or item.test_scores is None:
            continue
        info = details[item.task]
        lines.append(f"### {item.task}: {item.model}")
        lines.append("")
        lines.append(f"Eligible rows: {info['rows']}; train: {info['train']}; validation: {info['validation']}; test: {info['test']}.")
        lines.append("")
        lines.append("| Metric | Test value |")
        lines.append("| --- | ---: |")
        for metric, value in item.test_scores.items():
            lines.append(f"| {metric} | {_fmt(value)} |")
        lines.append("")
        importance = details.get(f"{item.task}_importance")
        if importance:
            lines.extend(["Validation permutation importance (largest score decrease first):", "", "| Predictor | Score decrease |", "| --- | ---: |"])
            for predictor, decrease in importance:
                lines.append(f"| `{predictor}` | {_fmt(decrease)} |")
            lines.append("")
    for target in ("in_hospital_mortality_flag", "urgent_readmitted_30d"):
        bins = details.get(f"{target}_calibration")
        if bins:
            lines.extend([f"### {target} calibration", "", "| Bin | Rows | Mean predicted risk | Observed rate |", "| ---: | ---: | ---: | ---: |"])
            for index, (rows, predicted, observed) in enumerate(bins, start=1):
                lines.append(f"| {index} | {rows} | {_fmt(predicted)} | {_fmt(observed)} |")
            lines.append("")
    subgroup_rows = details.get("mortality_subgroups", [])
    if subgroup_rows:
        lines.extend(["### Mortality model subgroup check", "", "These synthetic subgroup figures are descriptive and do not establish fairness. Small positive counts make sensitivity unstable.", "", "| Group | Value | Rows | Outcome rate | Sensitivity | Specificity |", "| --- | --- | ---: | ---: | ---: | ---: |"])
        for group, value, rows, prevalence, sensitivity, specificity in subgroup_rows:
            lines.append(f"| {group} | {value} | {rows} | {_fmt(prevalence)} | {_fmt(sensitivity)} | {_fmt(specificity)} |")
        lines.append("")
    lines.extend([
        "## Interpretation limits", "",
        "The generator uses arbitrary invented patterns and a fixed random seed. Even high scores reflect those patterns, not clinical validity. Small subgroups and rare outcomes can produce unstable metrics. Linear SHAP-style values are baseline-centred coefficient magnitudes, not an external SHAP calculation. No patient-level predictions, identifiers, or records are exported by this report.", "",
    ])
    output = config.outputs_public_path / "aggregate_results" / "research_demo_summary.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_aggregate_artifacts(output.parent, frame, evaluations, details, missing)
    lines.extend(["Aggregate CSV tables and Plotly charts are saved beside this report; they contain only grouped results.", ""])
    output.write_text("\n".join(lines))
    return output
