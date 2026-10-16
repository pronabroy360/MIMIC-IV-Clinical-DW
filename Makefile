SYSTEM_PYTHON ?= python3
VENV ?= .venv
PYTHON ?= $(VENV)/bin/python

.PHONY: setup seed-synthetic research-demo study-validate study-preview study-run study-scenario study-transferability study-assistant-eval localstack-check ingest-demo ingest-localstack run-localstack build-bronze build-silver build-gold validate profile run-all dashboard api test llm-demo llm-eval ml-baseline demo-pack report precommit-install precommit-run ci

setup:
	$(SYSTEM_PYTHON) -m venv $(VENV)
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

seed-synthetic:
	$(PYTHON) -m src.cli seed-synthetic --config configs/demo.duckdb.yaml --force

research-demo:
	$(PYTHON) -m src.cli research-demo --config configs/research_synthetic.duckdb.yaml

study-validate:
	$(PYTHON) -m src.cli study-validate --config configs/research_synthetic.duckdb.yaml

study-preview:
	$(PYTHON) -m src.cli study-preview --config configs/research_synthetic.duckdb.yaml

study-run:
	$(PYTHON) -m src.cli study-run --config configs/research_synthetic.duckdb.yaml

study-scenario:
	$(PYTHON) -m src.cli study-scenario --config configs/research_synthetic.duckdb.yaml --scenario delayed_labs

study-transferability:
	$(PYTHON) -m src.cli study-transferability --config configs/research_synthetic.duckdb.yaml

study-assistant-eval:
	$(PYTHON) -m src.cli study-assistant-eval --config configs/research_synthetic.duckdb.yaml

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
	$(MAKE) research-demo
	$(MAKE) study-validate
	$(MAKE) study-run
	$(MAKE) study-assistant-eval
	$(MAKE) test
	$(MAKE) llm-demo
	$(MAKE) llm-eval
	$(MAKE) ml-baseline
