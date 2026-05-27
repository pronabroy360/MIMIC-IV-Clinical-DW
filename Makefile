SYSTEM_PYTHON ?= python3
VENV ?= .venv
PYTHON ?= $(VENV)/bin/python

.PHONY: setup seed-synthetic localstack-check ingest-demo ingest-localstack run-localstack build-bronze build-silver build-gold validate profile run-all dashboard api test llm-demo llm-eval ml-baseline demo-pack report precommit-install precommit-run ci

setup:
	$(SYSTEM_PYTHON) -m venv $(VENV)
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

seed-synthetic:
	$(PYTHON) -m src.cli seed-synthetic --config configs/demo.duckdb.yaml --force

localstack-check:
	$(PYTHON) -m src.cli localstack-check --config configs/localstack.s3.yaml.example

ingest-demo:
	$(PYTHON) -m src.cli ingest --config configs/demo.duckdb.yaml

ingest-localstack:
	$(PYTHON) -m src.cli ingest --config configs/localstack.s3.yaml.example

run-localstack:
	$(PYTHON) -m src.cli run-all --config configs/localstack.s3.yaml.example

build-bronze:
	$(PYTHON) -m src.cli build-bronze --config configs/demo.duckdb.yaml

build-silver:
	$(PYTHON) -m src.cli build-silver --config configs/demo.duckdb.yaml

build-gold:
	$(PYTHON) -m src.cli build-gold --config configs/demo.duckdb.yaml

validate:
	$(PYTHON) -m src.cli validate --config configs/demo.duckdb.yaml

profile:
	$(PYTHON) -m src.cli profile --config configs/demo.duckdb.yaml

run-all:
	$(PYTHON) -m src.cli run-all --config configs/demo.duckdb.yaml

dashboard:
	$(VENV)/bin/streamlit run dashboard/streamlit_app.py

api:
	$(VENV)/bin/uvicorn src.api.main:app --reload

test:
	$(VENV)/bin/pytest tests/

llm-demo:
	$(PYTHON) -m src.cli llm-demo --config configs/demo.duckdb.yaml

llm-eval:
	$(PYTHON) -m src.cli llm-eval --config configs/demo.duckdb.yaml

ml-baseline:
	$(PYTHON) -m src.cli ml-baseline --config configs/demo.duckdb.yaml

demo-pack:
	$(PYTHON) -m src.cli demo-pack --config configs/demo.duckdb.yaml

report:
	$(PYTHON) -m src.cli report --config configs/demo.duckdb.yaml

precommit-install:
	$(VENV)/bin/pre-commit install

precommit-run:
	$(VENV)/bin/pre-commit run --all-files

ci:
	$(MAKE) setup
	$(MAKE) seed-synthetic
	$(MAKE) run-all
	$(MAKE) test
	$(MAKE) llm-demo
	$(MAKE) llm-eval
	$(MAKE) ml-baseline
