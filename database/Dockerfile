FROM postgres:16-alpine

# Copy init script to the Docker entrypoint directory
# PostgreSQL auto-runs *.sh and *.sql files in this directory on FIRST boot
COPY ./scripts/init-db.sh /docker-entrypoint-initdb.d/01-init-db.sh

# Copy helper scripts
COPY ./scripts/wait-for-db.sh /usr/local/bin/

# Make scripts executable and fix line endings (Windows → Unix)
RUN apk add --no-cache bash curl dos2unix \
    && dos2unix /docker-entrypoint-initdb.d/01-init-db.sh \
    && dos2unix /usr/local/bin/wait-for-db.sh \
    && chmod +x /docker-entrypoint-initdb.d/01-init-db.sh \
    && chmod +x /usr/local/bin/wait-for-db.sh
