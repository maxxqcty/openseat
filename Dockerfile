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

# Install production dependencies only. Keep each cleanup command separate:
# `&& ... || true` would swallow a failed `uv sync` and could ship a broken venv.
RUN set -eu; \
    uv sync --frozen --no-dev --no-install-project --no-cache; \
    rm -rf .venv/lib/python3.12/site-packages/uvloop; \
    rm -rf .venv/lib/python3.12/site-packages/watchfiles; \
    find .venv -type f -name '*.pyc' -delete; \
    find .venv -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true; \
    find .venv -type d -name 'tests' -exec rm -rf {} + 2>/dev/null || true; \
    find .venv -type d -name 'test' -exec rm -rf {} + 2>/dev/null || true

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

# Copy only the application files. Copying all of `backend/` would also copy a
# developer's host `.venv` if `.dockerignore` ever regresses.
COPY --chown=openseat:openseat backend/app /app/backend/app
COPY --chown=openseat:openseat backend/migrations /app/backend/migrations
COPY --chown=openseat:openseat backend/alembic.ini /app/backend/alembic.ini
COPY --chown=openseat:openseat backend/pyproject.toml /app/backend/pyproject.toml

# Copy built frontend from build stage
COPY --from=frontend-builder --chown=openseat:openseat /app/frontend/dist /app/frontend/dist

# Create entrypoint script
RUN <<EOF
cat > /app/entrypoint.sh <<'SCRIPT'
#!/bin/sh
set -e

# Make the virtualenv's console scripts (alembic, uvicorn) resolvable.
export PATH="/app/backend/.venv/bin:$PATH"
cd /app/backend

# A platform may pass a one-off command as arguments (for example a release
# step). Run it and exit with its status so a failed migration fails the deploy
# instead of starting the server.
if [ "$#" -eq 1 ]; then
    # One argument may be a whole command line, e.g. "alembic upgrade head".
    exec sh -c "$1"
fi
if [ "$#" -gt 1 ]; then
    exec "$@"
fi

# Run migrations, then start the application. Render injects PORT (10000);
# Compose and other local runs fall back to 8080.
alembic upgrade head
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8080}" \
    --workers 1
SCRIPT
chmod +x /app/entrypoint.sh
EOF

# Switch to non-root user
USER openseat

# Expose port (Render sets PORT at runtime)
EXPOSE 8080
ENV PORT=8080

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f "http://localhost:${PORT}/healthz" || exit 1

# OCI labels
ARG APP_VERSION=0.1.0
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="OpenSeat" \
      org.opencontainers.image.description="Booking and waitlist app for small workshops" \
      org.opencontainers.image.source="https://github.com/maxxqcty/openseat" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.licenses="MIT"

# Entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]