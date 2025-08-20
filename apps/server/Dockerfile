FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv via pip (more reliable in Docker)
RUN pip install uv

# Create a non-root user
RUN useradd -m -u 1000 appuser

# Copy project configuration files from the server directory
COPY --chown=appuser:appuser apps/server/pyproject.toml .

# Copy the app directory first (needed for editable install)
COPY --chown=appuser:appuser apps/server/app/ ./app/

# Install dependencies using uv with pyproject.toml
RUN uv pip install --system -e .

# Copy startup script
COPY --chown=appuser:appuser apps/server/startup.sh .

# Copy .env file from project root (if it exists)
COPY --chown=appuser:appuser .env* ./

# Make startup script executable and switch to appuser
RUN chmod +x startup.sh
USER appuser

# Expose port
EXPOSE 8000

# Run the startup script
CMD ["./startup.sh"]