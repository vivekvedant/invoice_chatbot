#!/usr/bin/env make

.PHONY: help install dev test lint format clean run docs type-check security

help:
	@echo "Invoice Chatbot Backend — Makefile"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  install        Install dependencies from uv.lock"
	@echo "  dev            Install dev dependencies"
	@echo "  test           Run core tests (models, config, cache_manager)"
	@echo "  test-all       Run all tests"
	@echo "  test-cov       Run tests with coverage report"
	@echo "  lint           Run ruff linter check"
	@echo "  format         Format code with ruff"
	@echo "  format-check   Check code formatting without changes"
	@echo "  type-check     Run mypy type checker"
	@echo "  security       Run bandit security audit"
	@echo "  clean          Remove cache and build artifacts"
	@echo "  run            Run FastAPI app (requires services)"
	@echo "  help           Show this help message"
	@echo ""

install:
	uv sync

dev:
	uv sync --dev

test:
	PYTHONPATH=$(PWD) uv run pytest tests/test_models.py tests/test_config.py tests/test_cache_manager.py -v

test-all:
	PYTHONPATH=$(PWD) uv run pytest tests/ -v

test-cov:
	PYTHONPATH=$(PWD) uv run pytest tests/test_models.py tests/test_config.py tests/test_cache_manager.py \
		--cov=src --cov-report=html --cov-report=term-missing

lint:
	uv run ruff check src/

format:
	uv run ruff format src/

format-check:
	uv run ruff format src/ --check

type-check:
	uv run mypy src/ --ignore-missing-imports

security:
	uv run bandit -r src/ -ll

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "coverage.xml" -delete
	find . -type f -name ".coverage" -delete
	@echo "✓ Cache and build artifacts cleaned"

run:
	@echo "Running API + Indexer (see logs in ./logs)."
	@bash ./scripts/run_services.sh

stop:
	@echo "Stopping services if running..."
	@if [ -f ./run/api.pid ]; then \
		pkill -F ./run/api.pid || true; \
		rm -f ./run/api.pid; \
	fi
	@if [ -f ./run/indexer.pid ]; then \
		pkill -F ./run/indexer.pid || true; \
		rm -f ./run/indexer.pid; \
	fi

check: lint type-check test
	@echo "✓ All checks passed"

all: install lint type-check test
	@echo "✓ Full build completed"

.DEFAULT_GOAL := help
