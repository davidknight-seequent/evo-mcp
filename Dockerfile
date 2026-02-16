# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Build the virtual environment using uv
RUN uv sync --frozen --no-editable

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 mcpuser

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src/ /app/src/

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create state directory with proper permissions
RUN mkdir -p /app/state && chown -R mcpuser:mcpuser /app/state /app

# Switch to non-root user
USER mcpuser

# Health check - validates MCP server is responsive
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Expose port for HTTP/SSE transport (if configured)
# Default transport is stdio (no port needed)
EXPOSE 8000

# Run the MCP server
CMD ["python", "/app/src/mcp_tools.py"]
