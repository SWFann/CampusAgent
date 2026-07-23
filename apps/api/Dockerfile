FROM python:3.11-slim

WORKDIR /app

# Install the exact uv-locked production dependencies into /app/.venv.
# This remains fully isolated inside the image and never touches host Python.
COPY --from=ghcr.io/astral-sh/uv:0.11.29 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev

# Copy application source
COPY src/ ./src/

# Expose API port
EXPOSE 8000

# Run application with uvicorn
# APP_ENV=development is set via compose environment
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
