# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for psycopg2 and matplotlib
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY templates/ templates/
COPY static/ static/

# Copy data file (fallback if database fails)
COPY materials13.csv .

# Copy ML models (bundled in container)
COPY models/ models/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Use gunicorn with optimized settings for Cloud Run
# 1 worker to minimize memory usage (512MB limit)
# Timeout set to 300s for Cloud Run
CMD exec gunicorn --bind :$PORT --workers 1 --threads 4 --timeout 300 app:app
