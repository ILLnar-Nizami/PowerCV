# AI Service Docker image
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY ai-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ai-service/ .

# Create non-root user
RUN groupadd --system app && \
    useradd --system --gid app --home-dir /app --shell /bin/bash app && \
    chown -R app:app /app

USER app

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
