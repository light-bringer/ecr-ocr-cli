# Makefile for electoral-search project
# Provides convenient shortcuts for common tasks

.PHONY: help install test lint format check clean run build docker-build docker-run docker-compose-up

# Default target
help:
	@echo "Electoral Search - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install dependencies with Poetry"
	@echo "  make install-dev    Install with development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test           Run tests with coverage"
	@echo "  make test-verbose   Run tests with verbose output"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format         Format code with Black"
	@echo "  make lint           Run Ruff linter"
	@echo "  make typecheck      Run mypy type checker"
	@echo "  make security       Run Bandit security scanner"
	@echo "  make check          Run all quality checks"
	@echo ""
	@echo "Development:"
	@echo "  make run            Run the application"
	@echo "  make shell          Activate Poetry shell"
	@echo "  make clean          Remove build artifacts and cache"
	@echo ""
	@echo "Build:"
	@echo "  make build          Build distribution packages"
	@echo "  make publish        Publish to PyPI (requires credentials)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   Build Docker image"
	@echo "  make docker-run     Run Docker container"
	@echo "  make docker-compose-up    Start with Docker Compose"
	@echo "  make docker-compose-down  Stop Docker Compose"
	@echo "  make docker-validate      Validate Docker container"

install:
	poetry install

install-dev:
	poetry install --with dev

test:
	poetry run pytest

test-verbose:
	poetry run pytest -v

format:
	poetry run black electoral_search/ tests/

lint:
	poetry run ruff check electoral_search/

typecheck:
	poetry run mypy electoral_search/

security:
	poetry run bandit -r electoral_search/

check: format lint typecheck security
	@echo "✅ All quality checks passed!"

run:
	@echo "Usage: poetry run electoral-search search <directory> --names-file <file>"
	@echo "Example: poetry run electoral-search search ./pdfs --names-file names.txt"

shell:
	poetry shell

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf dist/ build/ *.egg-info htmlcov/ .coverage
	@echo "✨ Cleaned build artifacts and cache"

build:
	poetry build

publish:
	poetry publish

# Docker commands
docker-build:
	docker build -t electoral-search:latest .

docker-run:
	@echo "Example: docker run -v \$$(pwd)/pdfs:/data:ro electoral-search search /data --names-file /names.txt"
	@echo "See DOCKER.md for complete usage"

docker-compose-up:
	docker-compose up -d

docker-compose-down:
	docker-compose down

docker-validate:
	docker run electoral-search validate

docker-shell:
	docker run -it electoral-search bash

docker-clean:
	docker-compose down -v
	docker rmi electoral-search:latest 2>/dev/null || true
