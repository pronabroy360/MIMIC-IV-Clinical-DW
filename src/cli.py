"""Command-line interface for the MIMIC-IV warehouse."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.core.config import WarehouseConfig, load_config
from src.core.db import connect
from src.core.logging import configure_logging
from src.ingest.check_localstack import check_localstack_sources
from src.ingest.load_bigquery_metadata import load_bigquery_metadata
from src.ingest.load_demo import load_local_files
from src.ingest.load_full_local import load_full_local
from src.ingest.load_localstack_s3 import load_localstack_s3
from src.ingest.seed_synthetic import seed_synthetic_demo_data
from src.llm.evaluate_sql import run_sql_evaluation
from src.llm.nl_to_sql import answer_question
from src.ml.train_baseline import train_logistic_baseline, write_baseline_outputs
from src.reporting.generate_data_dictionary import generate_data_dictionary
from src.reporting.generate_pipeline_report import generate_pipeline_report
from src.reporting.generate_professor_summary import generate_professor_summary
from src.transform.build_bronze import build_bronze
from src.transform.build_gold import build_gold
from src.transform.build_silver import build_silver
from src.transform.run_sql_layer import profile_tables
from src.validation.validate_date_ranges import validate_date_ranges
from src.validation.validate_keys import validate_keys
from src.validation.validate_row_counts import validate_row_counts
from src.validation.validate_schema import validate_schema
from src.validation.validation_report import ValidationResult, write_validation_report


DEMO_QUESTIONS = [
    "How many patients are in the dataset?",
    "How many hospital admissions exist?",
    "How many ICU stays exist?",
    "What is the average ICU length of stay?",
    "What is the average hospital length of stay?",
    "What are the most common admission types?",
    "What are the most common discharge locations?",
    "What are the most frequent diagnosis groups?",
    "What are the most common lab tests?",
    "What percentage of ICU stays have lactate measured in the first 24 hours?",
    "What percentage of ICU stays have creatinine measured in the first 24 hours?",
    "What is the mortality rate among first ICU stays?",
    "What is the average ICU LOS by care unit?",
    "What diagnosis groups are associated with longer LOS?",
    "What is the feature completeness of first-24-hour vitals?",
    "What is the feature completeness of first-24-hour labs?",
    "How many patients have multiple ICU stays?",
    "How many admissions include procedures?",
    "How many admissions include microbiology events?",
    "What are the aggregate characteristics of the adult first ICU stay cohort?",
]


def _load_config_arg(args: argparse.Namespace) -> WarehouseConfig:
    return load_config(args.config)


def ingest(config: WarehouseConfig) -> Path:
    """Run configured ingestion mode."""
    if config.mode == "bigquery":
        return load_bigquery_metadata(config)
    if config.mode == "localstack":
        return load_localstack_s3(config)
    if config.mode == "full_local":
        return load_full_local(config)
    return load_local_files(config)


def run_validation(config: WarehouseConfig) -> tuple[list[ValidationResult], Path]:
    """Run all validation checks and write a report."""
    with connect(config) as con:
        results: list[ValidationResult] = []
        results.extend(validate_schema(con))
        results.extend(validate_keys(con))
        results.extend(validate_date_ranges(con))
        results.extend(validate_row_counts(con))
    report_path = write_validation_report(results, config.outputs_private_path)
    return results, report_path


def cmd_ingest(args: argparse.Namespace) -> int:
    config = _load_config_arg(args)
    report = ingest(config)
    print(f"Ingestion complete. Report: {report}")
    return 0


def cmd_localstack_check(args: argparse.Namespace) -> int:
    config = _load_config_arg(args)
    report = check_localstack_sources(config)
    print(f"LocalStack readiness report: {report}")
    return 0


def cmd_seed_synthetic(args: argparse.Namespace) -> int:
    config = _load_config_arg(args)
    raw_path = seed_synthetic_demo_data(config, overwrite=args.force)
    print(f"Synthetic demo CSVs ready under: {raw_path}")
    print("Run `make run-all` to rebuild the warehouse from the synthetic files.")
    return 0


def cmd_build_bronze(args: argparse.Namespace) -> int:
    config = _load_config_arg(args)
    executed = build_bronze(config)
    print(f"Bronze layer ready. SQL files executed: {len(executed)}")
    return 0


def cmd_build_silver(args: argparse.Namespace) -> int:
    config = _load_config_arg(args)
    executed = build_silver(config)
    print(f"Silver layer ready. SQL files executed: {len(executed)}")
    return 0


def cmd_build_gold(args: argparse.Namespace) -> int:
    config = _load_config_arg(args)
    executed = build_gold(config)
    print(f"Gold layer ready. SQL files executed: {len(executed)}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    config = _load_config_arg(args)
    results, report = run_validation(config)
    failures = [result for result in results if result.status == "fail"]
    print(f"Validation report: {report}")
    print(f"Passed: {sum(r.status == 'pass' for r in results)}")
    print(f"Warnings: {sum(r.status == 'warn' for r in results)}")
    print(f"Failures: {len(failures)}")
    return 1 if failures else 0


def cmd_profile(args: argparse.Namespace) -> int:
    config = _load_config_arg(args)
    rows = profile_tables(config, prefix=args.prefix)
    for table, count in rows:
        print(f"{table}\t{count}")
    return 0


def cmd_run_all(args: argparse.Namespace) -> int:
    config = _load_config_arg(args)
    ingest_report = ingest(config)
    # build_gold() already builds silver and bronze through layered builders.
    build_gold(config)
    results, validation_report = run_validation(config)
    generate_pipeline_report(config)
    failures = [result for result in results if result.status == "fail"]
    print(f"Ingestion report: {ingest_report}")
    print(f"Validation report: {validation_report}")
    print(f"Pipeline complete with {len(failures)} validation failure(s).")
    return 1 if failures else 0


def cmd_llm_demo(args: argparse.Namespace) -> int:
    config = _load_config_arg(args)
    build_gold(config)
    with connect(config) as con:
        allowed_tables = set(config.llm.allowed_tables)
        for question in DEMO_QUESTIONS:
            result = answer_question(
                con,
                question,
                config.outputs_private_path,
                allowed_tables=allowed_tables,
                default_limit=config.llm.default_limit,
            )
            status = "allowed" if result["allowed"] else "rejected"
            print(f"{status}: {question}")
    print(f"Private LLM query log: {config.outputs_private_path / 'llm_query_log.jsonl'}")
    return 0


def cmd_llm_eval(args: argparse.Namespace) -> int:
    config = _load_config_arg(args)
    build_gold(config)
    with connect(config) as con:
        comparison_path, summary_path = run_sql_evaluation(
            con,
            output_private_dir=config.outputs_private_path,
            output_public_dir=config.outputs_public_path / "aggregate_results",
            allowed_tables=set(config.llm.allowed_tables),
            default_limit=config.llm.default_limit,
        )
    print(f"Public comparison file: {comparison_path}")
    print(f"Public summary file: {summary_path}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    config = _load_config_arg(args)
    data_dictionary = generate_data_dictionary(config)
    pipeline_report = generate_pipeline_report(config)
    professor_summary = generate_professor_summary(config)
    print(f"Data dictionary: {data_dictionary}")
    print(f"Pipeline report: {pipeline_report}")
    print(f"Professor summary: {professor_summary}")
    return 0


def cmd_ml_baseline(args: argparse.Namespace) -> int:
    config = _load_config_arg(args)
    build_gold(config)
    result = train_logistic_baseline(config)
    csv_path, md_path = write_baseline_outputs(config, result)
    print(f"ML baseline metrics CSV: {csv_path}")
    print(f"ML baseline metrics summary: {md_path}")
    return 0


def cmd_demo_pack(args: argparse.Namespace) -> int:
    config = _load_config_arg(args)
    seed_synthetic_demo_data(config, overwrite=True)
    ingest(config)
    build_gold(config)
    run_validation(config)
    generate_data_dictionary(config)
    generate_pipeline_report(config)
    generate_professor_summary(config)
    with connect(config) as con:
        run_sql_evaluation(
            con,
            output_private_dir=config.outputs_private_path,
            output_public_dir=config.outputs_public_path / "aggregate_results",
            allowed_tables=set(config.llm.allowed_tables),
            default_limit=config.llm.default_limit,
        )
    try:
        baseline = train_logistic_baseline(config)
        write_baseline_outputs(config, baseline)
    except RuntimeError as exc:
        print(f"ML baseline skipped: {exc}")
    print(f"Demo pack generated under: {config.outputs_public_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MIMIC-IV clinical warehouse CLI")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    subparsers = parser.add_subparsers(dest="command", required=True)

    commands = {
        "seed-synthetic": cmd_seed_synthetic,
        "localstack-check": cmd_localstack_check,
        "ingest": cmd_ingest,
        "build-bronze": cmd_build_bronze,
        "build-silver": cmd_build_silver,
        "build-gold": cmd_build_gold,
        "validate": cmd_validate,
        "profile": cmd_profile,
        "run-all": cmd_run_all,
        "llm-demo": cmd_llm_demo,
        "llm-eval": cmd_llm_eval,
        "ml-baseline": cmd_ml_baseline,
        "demo-pack": cmd_demo_pack,
        "report": cmd_report,
    }
    for name, handler in commands.items():
        subparser = subparsers.add_parser(name)
        subparser.add_argument("--config", default="configs/demo.duckdb.yaml")
        subparser.set_defaults(handler=handler)
        if name == "seed-synthetic":
            subparser.add_argument(
                "--force",
                action="store_true",
                help="Overwrite existing local demo CSVs with synthetic data",
            )
        if name == "profile":
            subparser.add_argument("--prefix", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(verbose=args.verbose)
    try:
        return int(args.handler(args))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
