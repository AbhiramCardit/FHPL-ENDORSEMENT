#!/bin/bash
set -e

# This script runs automatically on FIRST PostgreSQL container boot
# (only when the data volume is empty / freshly created).
#
# Environment variables POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB
# are set by docker-compose via .env file. PostgreSQL's entrypoint already
# creates the user and database from these vars BEFORE this script runs.

echo "=== Custom DB Initialisation ==="

# Create required extensions
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pg_trgm";
EOSQL

echo "=== Extensions created successfully ==="

# Run any .sql migration files if they exist in our custom location
if ls /docker-entrypoint-initdb.d/*.sql 1> /dev/null 2>&1; then
    for migration in /docker-entrypoint-initdb.d/*.sql; do
        echo "Running SQL file: $migration"
        psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$migration"
    done
fi

echo "=== Database initialisation completed ==="
