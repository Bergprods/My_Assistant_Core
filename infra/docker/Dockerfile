# Use official Python runtime as a base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy and install dependencies
COPY pyproject.toml poetry.lock* ./
RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-root --no-dev

# Copy application code
COPY . .

# Expose application port (if applicable)
EXPOSE 8000

# Default command
CMD ["python", "cli.py"]
