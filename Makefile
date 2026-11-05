# Every task runs in the locked environment through uv. `make check` is what CI runs.

PYTHON_VERSIONS := 3.11 3.12 3.13 3.14 3.15
PIP_AUDIT := pip-audit==2.10.1
TWINE := twine==7.0.0

.PHONY: help install sync lint format typecheck test coverage matrix build package audit check clean

help:  ## List the tasks
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-10s %s\n", $$1, $$2}'

install:  ## Install the locked development environment
	uv sync --locked

sync:  ## Regenerate the synchronous client from the asynchronous one
	uv run --locked python scripts/unasync.py

lint:  ## Ruff lint and format check, and the generated client is up to date
	uv run --locked ruff check .
	uv run --locked ruff format --check .
	uv run --locked python scripts/unasync.py --check

format:  ## Fix what Ruff can, and format
	uv run --locked ruff check --fix .
	uv run --locked ruff format .

typecheck:  ## mypy --strict over src, tests and scripts
	uv run --locked mypy

test:  ## Run the tests
	uv run --locked pytest

coverage:  ## Run the tests with branch coverage
	uv run --locked pytest --cov --cov-report=term-missing --cov-fail-under=95

matrix:  ## Run the tests on every supported Python
	@for version in $(PYTHON_VERSIONS); do \
		echo "== Python $$version"; \
		uv run --locked --isolated --python $$version pytest -q || exit 1; \
	done

build:  ## Build the sdist and wheel into dist/
	rm -rf dist
	uv build

package: build  ## Build, then check the artifacts
	uvx $(TWINE) check --strict dist/*
	uv run --locked python scripts/check_wheel.py dist

audit:  ## Audit every locked dependency for known vulnerabilities
	uv export --locked --all-groups --no-emit-project --format requirements.txt --output-file .audit-requirements.txt --quiet
	uvx $(PIP_AUDIT) --strict --require-hashes --disable-pip -r .audit-requirements.txt; status=$$?; rm -f .audit-requirements.txt; exit $$status

check: lint typecheck coverage package audit  ## Everything CI checks

clean:  ## Remove build and test output
	rm -rf dist .coverage .pytest_cache .mypy_cache .ruff_cache .audit-requirements.txt
