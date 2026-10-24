# Dockerfile for AgentGuard API
# Uses a minimal Python 3.11 Slim image

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and seeds (seed DB will be mounted at runtime)
COPY api/ ./api/
COPY seeds/ ./seeds/

EXPOSE 8888

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8888"]
