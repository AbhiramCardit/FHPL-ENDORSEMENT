FROM postgres:16-alpine

# Copy scripts to a custom location
COPY ./scripts/init-db.sh /scripts/
COPY ./scripts/wait-for-db.sh /usr/local/bin/

# Make scripts executable
RUN chmod +x /scripts/init-db.sh \
    && chmod +x /usr/local/bin/wait-for-db.sh

# Install required tools
RUN apk add --no-cache bash curl
