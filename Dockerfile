# Multi-stage Dockerfile for Vajra Weather Tracking & Downscaling Platform
FROM python:3.11-slim as backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system geospatial and weather dependencies (eccodes for GRIB2, geos for Shapely)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgeos-dev \
    libproj-dev \
    libeccodes-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY vajra/ ./vajra/
COPY configs/ ./configs/
COPY pyproject.toml .

EXPOSE 8000

CMD ["uvicorn", "vajra.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
