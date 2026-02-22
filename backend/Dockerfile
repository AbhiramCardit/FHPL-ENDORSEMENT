FROM python:3.12-slim

WORKDIR /app

# System deps for psycopg2, Pillow, Tesseract, and pg_isready
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    tesseract-ocr \
    postgresql-client \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Fix line endings (Windows → Unix) and make entrypoint executable
RUN dos2unix /app/entrypoint.sh && chmod +x /app/entrypoint.sh

EXPOSE 8000

# Use entrypoint that runs migrations before starting uvicorn
CMD ["/app/entrypoint.sh"]
