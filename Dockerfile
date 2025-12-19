# Multi-stage Dockerfile for Electoral Search
# Production-ready with security best practices

# Stage 1: Builder
FROM python:3.11-slim as builder

# Install Poetry
ENV POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

# Set working directory
WORKDIR /app

# Copy only dependency files first for better caching
COPY pyproject.toml ./

# Install dependencies (without dev dependencies)
RUN poetry install --only main --no-root --no-directory

# Stage 2: Runtime
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-ben \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Verify Tesseract installation
RUN tesseract --version && \
    tesseract --list-langs | grep ben

# Create non-root user for security
RUN groupadd -r electoral && \
    useradd -r -g electoral -u 1000 electoral && \
    mkdir -p /app /data /output && \
    chown -R electoral:electoral /app /data /output

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=electoral:electoral /app/.venv /app/.venv

# Copy application code
COPY --chown=electoral:electoral electoral_search ./electoral_search/
COPY --chown=electoral:electoral run.py ./
COPY --chown=electoral:electoral docker-entrypoint.sh ./

# Make entrypoint executable
USER root
RUN chmod +x /app/docker-entrypoint.sh
USER electoral

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create volumes for data
VOLUME ["/data", "/output"]

# Set default working directory for data
WORKDIR /data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import electoral_search; print('OK')" || exit 1

# Use entrypoint script
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["search", "--help"]

# Labels
LABEL maintainer="Debapriya Das" \
      version="2.0.0" \
      description="OCR-based search tool for Bengali electoral roll PDFs" \
      org.opencontainers.image.source="https://github.com/light-bringer/ecr-ocr-cli"
