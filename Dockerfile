# FairGuard ETL Pipeline — Docker image
# Runs the full LDA corpus indexer (Skill 1) and agency concentration scan (Skill 3)
#
# Build:
#   docker build -t fairguard-etl .
#
# Run (mount data + output volumes):
#   docker run --rm \
#     -v $(pwd)/data:/app/data \
#     -v $(pwd)/output:/app/output \
#     fairguard-etl
#
# Run sample build (fast validation):
#   docker run --rm \
#     -v $(pwd)/data:/app/data \
#     -v $(pwd)/output:/app/output \
#     -e SAMPLE=1 \
#     fairguard-etl

FROM python:3.11-slim AS base

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy source
COPY scripts/ ./scripts/
COPY notes/ ./notes/

# Entrypoint
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

VOLUME ["/app/data", "/app/output"]

ENV DATA_ROOT=/app/data
ENV OUTPUT_ROOT=/app/output

ENTRYPOINT ["./docker-entrypoint.sh"]
