# Build Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Builder stage for Python dependencies
FROM python:3.12-alpine AS builder

# Set build arguments
ARG PIP_NO_CACHE_DIR=1
ARG PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apk add --no-cache --virtual .build-deps \
    build-base \
    python3-dev \
    && rm -rf /var/cache/apk/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies in a virtual environment
# Note: AI dependencies moved to ai-service/
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip wheel && \
    /opt/venv/bin/pip install -r requirements.txt && \
    rm -rf /var/cache/apk/*

# Final stage
FROM python:3.12-alpine

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies (including Typst and standard utils)
RUN apk add --no-cache \
    curl \
    ca-certificates \
    typst

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY ./app /app/app

# Copy built frontend if needed (assuming FastAPI serves it from app/static/frontend)
# Adjust the destination path as per your FastAPI setup
COPY --from=frontend-builder /frontend/dist /app/app/static/frontend

# Create a non-root user
RUN addgroup -S app && \
    adduser -S -G app app && \
    chown -R app:app /app

USER app

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
