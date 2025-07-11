# SmartCharge Helper PVPC - MCP Server
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Create app directory and non-root user
WORKDIR /app
RUN useradd --create-home --shell /bin/bash mcp && \
    chown -R mcp:mcp /app

# Copy application code
COPY smartcharge_helper_pvpc/ ./smartcharge_helper_pvpc/

# Set ownership and switch to non-root user
RUN chown -R mcp:mcp /app
USER mcp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import smartcharge_helper_pvpc; print('OK')" || exit 1

# MCP servers communicate via stdio
CMD ["python", "-m", "smartcharge_helper_pvpc"]
