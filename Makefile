.PHONY: help install install-dev test test-cov lint format type-check clean build publish docs

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install: ## Install the package
	pip install -e .

install-dev: ## Install the package with dev dependencies
	pip install -e ".[dev,docs]"

test: ## Run tests
	pytest

test-cov: ## Run tests with coverage
	pytest --cov=sqlalchemy-seedify --cov-report=term-missing --cov-report=html

lint: ## Run linters
	ruff check src tests
	black --check src tests

format: ## Format code
	black src tests
	ruff check src tests --fix

type-check: ## Run type checking
	mypy src

clean: ## Clean build artifacts
	rm -rf build dist *.egg-info
	rm -rf .pytest_cache .coverage htmlcov
	rm -rf .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

build: clean ## Build distribution packages
	python -m build

publish-test: build ## Publish to TestPyPI
	python -m twine upload --repository testpypi dist/*

publish: build ## Publish to PyPI
	python -m twine upload dist/*

docs: ## Build documentation
	mkdocs build

docs-serve: ## Serve documentation locally
	mkdocs serve

pre-commit: ## Run pre-commit hooks
	pre-commit run --all-files

setup-pre-commit: ## Install pre-commit hooks
	pre-commit install

check: lint type-check test ## Run all checks

all: format check ## Format and run all checks