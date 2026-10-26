# syntax=docker.io/docker/dockerfile:1.7

# Build stage: frontend
FROM node:22.14-alpine AS frontend-builder

WORKDIR /app/frontend

# Install dependencies
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

# Copy source and build
COPY frontend/ ./
RUN npm run build

# Build stage: backend dependencies
FROM python:3.12.10-alpine AS backend-deps

# Install uv and build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    cargo

COPY --from=ghcr.io/astral-sh/uv:0.6.10 /uv /uvx /usr/local/bin/

WORKDIR /app/backend

# Copy dependency files
COPY backend/pyproject.toml backend/uv.lock ./

# Install production dependencies only
RUN uv sync --frozen --no-dev --no-install-project --no-cache \
    && rm -rf .venv/lib/python3.12/site-packages/uvloop \
    && rm -rf .venv/lib/python3.12/site-packages/watchfiles \
    && find .venv -type f -name '*.pyc' -delete \
    && find .venv -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true \
    && find .venv -type d -name 'tests' -exec rm -rf {} + 2>/dev/null || true \
    && find .venv -type d -name 'test' -exec rm -rf {} + 2>/dev/null || true

# Runtime stage
FROM python:3.12.10-alpine AS runtime

# Install runtime dependencies
RUN apk add --no-cache \
    ca-certificates \
    curl \
    libffi \
    openssl

# Create non-root user
RUN addgroup -S openseat && adduser -S -G openseat -u 10001 openseat

WORKDIR /app

# Copy backend dependencies from build stage
COPY --from=backend-deps --chown=openseat:openseat /app/backend/.venv /app/backend/.venv

# Copy backend application
COPY --chown=openseat:openseat backend/ /app/backend/

# Copy built frontend from build stage
COPY --from=frontend-builder --chown=openseat:openseat /app/frontend/dist /app/frontend/dist

# Create entrypoint script
RUN <<EOF
cat > /app/entrypoint.sh <<'SCRIPT'
#!/bin/sh
set -e

# Run migrations
cd /app/backend
/app/backend/.venv/bin/alembic upgrade head

# Start application
exec /app/backend/.venv/bin/uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8080 \
    --workers 1
SCRIPT
chmod +x /app/entrypoint.sh
EOF

# Switch to non-root user
USER openseat

# Expose port
EXPOSE 8080

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/healthz || exit 1

# OCI labels
LABEL org.opencontainers.image.title="OpenSeat" \
      org.opencontainers.image.description="Booking and waitlist app for small workshops" \
      org.opencontainers.image.source="https://github.com/maxxqcty/openseat" \
      org.opencontainers.image.revision="" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.licenses="MIT"

# Entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]