#!/bin/bash
set -e

# Function to run SQL file
run_sql_file() {
    local file=$1
    echo "Running SQL file: $file"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$file"
}

# Create extensions if needed
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pg_trgm";
EOSQL

# Run all migration files in order
for migration in /docker-entrypoint-initdb.d/*.sql
do
    if [ -f "$migration" ]; then
        run_sql_file "$migration"
    fi
done

echo "Database initialization completed"
