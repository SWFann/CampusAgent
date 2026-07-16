FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (better layer caching)
# Use locked dependencies for reproducibility (consistent with CI/Makefile)
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock

# Copy application source
COPY src/ ./src/

# Expose API port
EXPOSE 8000

# Run application with uvicorn
# APP_ENV=development is set via compose environment
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
