FROM python:3.11-slim

# Create a non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . ./

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production

# Create uploads directory (if using local storage)
RUN mkdir -p /app/uploads && chown appuser:appgroup /app/uploads

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
