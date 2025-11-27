## ------------------------------- Builder Stage ------------------------------ ## 
FROM python:3.10-bookworm AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpoppler-cpp-dev \
    libleptonica-dev \
    libtesseract-dev \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set up the UV environment path correctly
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

COPY ./pyproject.toml .

RUN uv sync

## ----------------------------- Production Stage ----------------------------- ##
FROM python:3.10-slim

# Install only runtime dependencies (removed -dev packages)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m appuser

USER appuser

WORKDIR /app

# Copy app and .venv from builder
COPY /src src
COPY --from=builder /app/.venv .venv

# Set up environment variables for production
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 7860

# Start the Flask app via gunicorn
# Increased timeout for document processing workloads
CMD ["sh", "-c", "gunicorn -w 4 -b 0.0.0.0:7860 --timeout 120 --access-logfile - src.document_processor_flask_api:app"]