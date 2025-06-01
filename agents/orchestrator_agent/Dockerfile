FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required for PostgreSQL and RabbitMQ
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first for better caching
COPY agents/orchestrator_agent/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the common libraries and orchestrator code
# Note: We'll do this in docker-compose by mounting the correct directories

# Set environment variables
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO
ENV API_HOST=0.0.0.0
ENV API_PORT=8000

# Expose the API port
EXPOSE 8000

# Command to run the orchestrator
CMD ["python", "/app/agents/orchestrator_agent/main.py"]
