.PHONY: help install format lint check mypy test run ci clean

# Default target
.DEFAULT_GOAL := help

help:
	@echo "Available commands:"
	@echo "  make install  - Install dependencies"
	@echo "  make format   - Format code with ruff"
	@echo "  make lint     - Lint code with ruff (auto-fix)"
	@echo "  make check    - Format + lint"
	@echo "  make mypy     - Type checking with mypy"
	@echo "  make test     - Run tests"
	@echo "  make ci       - Run all checks (check + mypy + test)"
	@echo "  make clean    - Remove cache files"

# Install dependencies
install:
	uv sync

# Format code with ruff
format:
	uv run ruff format src/

# Lint code with ruff
lint:
	uv run ruff check src/ --fix

# Format + lint
check: format lint

# Type checking with mypy
mypy:
	uv run mypy src/

# Run tests
test:
	uv run pytest tests/

# Run the application
run:
	uv run python -m src.entrypoints.main

# Run all checks (lint + type check + tests)
ci: check mypy test

# Clean cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
