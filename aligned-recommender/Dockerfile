FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements_service.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements_service.txt

# Copy the service code
COPY mbti_service.py .

# Create a non-root user
RUN useradd -m -u 1000 mbtiuser && chown -R mbtiuser:mbtiuser /app
USER mbtiuser

# Expose port
EXPOSE 5000

# Health check using Python instead of curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# Run the application
CMD ["python", "mbti_service.py"] 