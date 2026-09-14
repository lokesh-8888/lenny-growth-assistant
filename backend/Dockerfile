# =============================================================================
# Stage 1: Build virtual environment and wheels
# =============================================================================
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# =============================================================================
# Stage 2: Lean runtime with non-root security
# =============================================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime utilities: curl (for healthcheck), git (for transcript archive cloning), and libpq5 (Postgres driver)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1

# Create non-root system user and group for security
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Pre-create data and scripts directories with proper ownership
RUN mkdir -p /app/data /app/scripts && \
    chown -R appuser:appgroup /app

# Copy application and script code
COPY --chown=appuser:appgroup app/ ./app/
COPY --chown=appuser:appgroup db/ ./db/
COPY --chown=appuser:appgroup scripts/ ./scripts/

# Container healthcheck targeting the granular /health endpoint
HEALTHCHECK --interval=10s --timeout=5s --retries=3 --start-period=5s \
    CMD curl -f http://localhost:8000/health || exit 1

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
