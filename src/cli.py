"""Command-line interface for the MIMIC-IV warehouse."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from src.core.config import WarehouseConfig, load_config
from src.core.db import connect, execute_sql_file, row_count
from src.core.logging import configure_logging
from src.core.paths import project_root
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
from src.research.evaluate import run_research_evaluation
from src.research.evaluate_assistant import evaluate_assistant
from src.research.comparison import compare_frozen_scenario
from src.research.seed import POPULATED_BRONZE_TABLES, seed_research_cohort
from src.research.publication import verify_study_package
from src.research.scenarios import available_scenarios, prepare_scenario
from src.research.sites import evaluate_site_transferability, prepare_simulated_site
from src.research.study_service import load_and_validate, preview_study, publish_run, run_study
from src.transform.build_bronze import build_bronze
from src.transform.build_gold import build_gold
from src.transform.build_silver import build_silver
from src.transform.run_sql_layer import profile_tables
from src.validation.validate_date_ranges import validate_date_ranges
from src.validation.validate_keys import validate_keys
from src.validation.validate_row_counts import validate_row_counts
from src.validation.validate_research_quality import validate_invented_physiology_ranges, validate_source_key_uniqueness
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
        results.extend(validate_source_key_uniqueness(con))
        results.extend(validate_invented_physiology_ranges(con))
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


def cmd_research_demo(args: argparse.Namespace) -> int:
    """Build and evaluate a wholly invented, isolated teaching cohort."""
    config = _load_config_arg(args)
    seed_research_cohort(config, patients=args.patients, seed=args.seed)
    ingest(config)
    with connect(config) as con:
        bronze_tables = [
            row[0] for row in con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main' AND table_name LIKE 'bronze_%'"
            ).fetchall()
        ]
        unexpected = [
            table for table in bronze_tables
            if table not in POPULATED_BRONZE_TABLES and row_count(con, table) > 0
        ]
    if unexpected:
        raise ValueError(
            "Research demo database contains non-synthetic Bronze rows: "
            + ", ".join(sorted(unexpected))
        )
    build_gold(config)
    with connect(config) as con:
        execute_sql_file(con, project_root() / "sql/research/gold_research_index_admissions.sql")
    results, validation_report = run_validation(config)
    failures = [result for result in results if result.status == "fail"]
    if failures:
        print(f"Research demo validation failed: {validation_report}", file=sys.stderr)
        return 1
    summary = run_research_evaluation(config)
    print(f"Synthetic research summary: {summary}")
    print(f"Validation report: {validation_report}")
    return 0


def _load_study_arg(args: argparse.Namespace):
    return load_and_validate(args.study)


def cmd_study_validate(args: argparse.Namespace) -> int:
    spec = _load_study_arg(args)
    print(f"Study validated: {spec.study_id}")
    print(f"Definition hash: {spec.definition_hash}")
    return 0


def cmd_study_preview(args: argparse.Namespace) -> int:
    result = preview_study(_load_config_arg(args), _load_study_arg(args))
    print(json.dumps(result, indent=2, default=str))
    return 0


def cmd_study_run(args: argparse.Namespace) -> int:
    config = _load_config_arg(args)
    build_gold(config)
    result = run_study(config, _load_study_arg(args))
    print(f"Study succeeded: {result['run_id']}")
    print(json.dumps(result["evaluation"], indent=2, default=str))
    return 0


def cmd_study_package(args: argparse.Namespace) -> int:
    package = publish_run(_load_config_arg(args), args.run_id)
    print(f"Published aggregate package: {package}")
    print(json.dumps(verify_study_package(package), indent=2))
    return 0


def cmd_study_scenario(args: argparse.Namespace) -> int:
    config = _load_config_arg(args)
    scenario_config = prepare_scenario(config, args.scenario)
    ingest(scenario_config)
    build_gold(scenario_config)
    results, report = run_validation(scenario_config)
    failures = [result for result in results if result.status == "fail"]
    print(f"Scenario validation report: {report}")
    if failures:
        print(f"Scenario blocked by {len(failures)} quality failure(s).")
        return 1
    result = run_study(scenario_config, _load_study_arg(args))
    print(f"Scenario study succeeded: {result['run_id']}")
    return 0


def cmd_study_compare(args: argparse.Namespace) -> int:
    baseline_config = _load_config_arg(args)
    spec = _load_study_arg(args)
    ingest(baseline_config)
    build_gold(baseline_config)
    scenario_config = prepare_scenario(baseline_config, args.scenario)
    ingest(scenario_config)
    build_gold(scenario_config)
    quality, report = run_validation(scenario_config)
    failures = [result for result in quality if result.status == "fail"]
    if failures:
        print(f"Scenario blocked by {len(failures)} quality failure(s): {report}")
        return 1
    output = baseline_config.outputs_public_path / "studies" / f"scenario_comparison_{args.scenario}.json"
    result = compare_frozen_scenario(baseline_config, scenario_config, spec, output)
    print(f"Frozen-model scenario comparison: {output}")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["baseline_unchanged"] else 1


def cmd_study_transferability(args: argparse.Namespace) -> int:
    config = _load_config_arg(args)
    spec = _load_study_arg(args)
    site_a = prepare_simulated_site(config, "site_a", seed=41)
    site_b = prepare_simulated_site(config, "site_b", seed=43)
    result = evaluate_site_transferability(site_a, site_b, spec)
    output = config.outputs_public_path / "studies" / "simulated_site_transferability.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"Transferability report: {output}")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_study_assistant_eval(args: argparse.Namespace) -> int:
    config = _load_config_arg(args)
    corpus = project_root() / "configs/research/assistant_evaluation.yaml"
    output = config.outputs_public_path / "studies" / "assistant_evaluation.json"
    summary = evaluate_assistant(corpus, output)
    print(f"Assistant evaluation: {output}")
    print(json.dumps(summary, indent=2))
    return 1 if summary["failed"] else 0


def _run_codeindex_cli(*cli_args: str, cwd: Path | None = None) -> int:
    """
    Run vendored `codeindex` CLI via `python -m codeindex.cli`.

    The repo vendors a clean copy under `vendor/codeindex_src`.
    """
    root = project_root()
    codeindex_vendor_root = root / "vendor" / "codeindex_src"
    if not codeindex_vendor_root.exists():
        print(
            "Missing vendored dependency: vendor/codeindex_src. Restore it from the vendored source checkout.\n",
            file=sys.stderr,
        )
        return 1

    # Ensure `import codeindex` works from vendored source.
    # Use subprocess via stdlib to avoid adding dependencies.
    import subprocess

    env = dict(**os.environ)
    env["PYTHONPATH"] = str(codeindex_vendor_root)

    cmd = [sys.executable, "-m", "codeindex.cli", *cli_args]
    proc = subprocess.run(cmd, cwd=str(cwd or root), env=env)
    return int(proc.returncode)


def cmd_build_code_index(args: argparse.Namespace) -> int:
    root = project_root()

    # Our earlier custom CLI used --index-path as an index.json target.
    # Keep that meaning: if supplied, treat it as `<root>/codeindex.json` output.
    # The symbol index goes to the same directory as `symbolindex.json`.
    codeindex_out: Path = (
        Path(args.index_path).resolve() if getattr(args, "index_path", None) else (root / "codeindex.json")
    )
    codeindex_out.parent.mkdir(parents=True, exist_ok=True)
    symbol_out = codeindex_out.parent / "symbolindex.json"

    rc = _run_codeindex_cli(
        "analyze",
        str(root),
        "--output",
        str(codeindex_out),
    )
    if rc != 0:
        return rc

    rc = _run_codeindex_cli(
        "symbols",
        str(root),
        "--output",
        str(symbol_out),
    )
    if rc != 0:
        return rc

    print(f"codeindex.json written to: {codeindex_out}")
    print(f"symbolindex.json written to: {symbol_out}")
    return 0


def cmd_mcp_codeindex(args: argparse.Namespace) -> int:
    """
    Start `codeindex serve --mcp` which provides MCP tools over stdio JSON-RPC.
    """
    root = project_root()
    # MCP discovers both indexes upward from its current working directory.
    index_path = Path(args.index_path).resolve() if args.index_path else root / "codeindex.json"
    return _run_codeindex_cli("serve", "--mcp", "--repo", str(root), cwd=index_path.parent)


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
        "research-demo": cmd_research_demo,
        "study-validate": cmd_study_validate,
        "study-preview": cmd_study_preview,
        "study-run": cmd_study_run,
        "study-package": cmd_study_package,
        "study-scenario": cmd_study_scenario,
        "study-compare": cmd_study_compare,
        "study-transferability": cmd_study_transferability,
        "study-assistant-eval": cmd_study_assistant_eval,
        "build-code-index": cmd_build_code_index,
        "mcp-codeindex": cmd_mcp_codeindex,
    }
    for name, handler in commands.items():
        subparser = subparsers.add_parser(name)
        default_config = (
            "configs/research_synthetic.duckdb.yaml"
            if name == "research-demo" else "configs/demo.duckdb.yaml"
        )
        subparser.add_argument("--config", default=default_config)
        subparser.set_defaults(handler=handler)
        if name == "seed-synthetic":
            subparser.add_argument(
                "--force",
                action="store_true",
                help="Overwrite existing local demo CSVs with synthetic data",
            )
        if name == "profile":
            subparser.add_argument("--prefix", default=None)
        if name == "research-demo":
            subparser.add_argument("--patients", type=int, default=1000)
            subparser.add_argument("--seed", type=int, default=42)
        if name in {"study-validate", "study-preview", "study-run", "study-scenario", "study-compare", "study-transferability"}:
            subparser.add_argument("--study", default="configs/studies/icu_mortality_24h.yaml")
        if name == "study-package":
            subparser.add_argument("--run-id", required=True)
        if name in {"study-scenario", "study-compare"}:
            subparser.add_argument("--scenario", choices=sorted(available_scenarios()), required=True)
        if name in {"build-code-index", "mcp-codeindex"}:
            subparser.add_argument(
                "--index-path",
                default=None,
                help="Optional path to index.json (build-code-index writes it; mcp-codeindex reads it).",
            )
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
