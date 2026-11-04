FROM python:3.11-slim

WORKDIR /app

# Install system libraries needed for PyTorch & OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production

EXPOSE 8500

CMD ["uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8500"]
