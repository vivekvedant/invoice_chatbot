FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH=/app/.venv/bin:$PATH \
    PYTHONPATH=/app/src

WORKDIR /app

# Install uv package manager globally
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Create virtual environment and install deps inside it
RUN uv sync --frozen --no-dev --no-install-project --python=/usr/local/bin/python3

# Copy application code
COPY src ./src
COPY start.sh ./start.sh
RUN chmod +x ./start.sh
EXPOSE 8000

# Run uvicorn using the virtual environment
CMD ["./start.sh"]