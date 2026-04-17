# syntax=docker/dockerfile:1
# Build Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Builder stage for Python dependencies
FROM python:3.12-slim AS builder

# Install uv for fast dependency installation
RUN pip install uv

# Copy requirements and install into venv
COPY requirements.txt .
ENV VIRTUAL_ENV=/opt/venv PATH="/opt/venv/bin:$PATH"
RUN python -m venv /opt/venv && \
    uv pip install --no-cache -r requirements.txt

# Final stage
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PATH="/opt/venv/bin:$PATH"

# Install minimal runtime dependencies
# - curl/ca-certificates: for healthchecks and downloads
# - libmagic1: for python-magic file type detection
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY ./app /app/app

# Copy built frontend
COPY --from=frontend-builder /frontend/dist /app/app/static/frontend

# Create a non-root user
RUN groupadd -r app && \
    useradd -r -g app app && \
    chown -R app:app /app

USER app

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
