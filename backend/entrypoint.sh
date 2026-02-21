#!/bin/bash
set -e

echo "=== Backend Startup ==="

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL at ${POSTGRES_SERVER:-localhost}:${POSTGRES_PORT:-5432}..."
while ! pg_isready -h "${POSTGRES_SERVER:-localhost}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-endorsements_user}" -q 2>/dev/null; do
    echo "  PostgreSQL not ready yet, retrying in 2s..."
    sleep 2
done
echo "PostgreSQL is ready!"

# Run Alembic migrations automatically
echo "Running Alembic migrations..."
alembic upgrade head
echo "Migrations complete!"

# Start the application
echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
