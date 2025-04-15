FROM alpine:latest AS builder

# Install build dependencies
RUN apk add --no-cache \
    git \
    gcc \
    cmake \
    make \
    postgresql-dev \
    zlib-dev \
    zstd-dev \
    lz4-dev \
    bzip2-dev \
    libpq-dev \
    musl-dev \
    libev-dev \
    py3-docutils \
    pandoc \
    doxygen \
    graphviz \
    openssl-dev \
    yaml-dev

# Clone the repository
RUN git clone https://github.com/pgexporter/pgexporter.git /src

WORKDIR /src

# Build pgexporter
RUN mkdir -p build && \
    cd build && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr/local/ -DMAN_INSTALL=OFF .. && \
    make -j$(nproc) && \
    make install

# Second stage - runtime image
FROM alpine:latest

# Install runtime dependencies
RUN apk add --no-cache \
    postgresql \
    postgresql-client \
    bash \
    ca-certificates \
    libev \
    yaml \
    bzip2 \
    bzip2-dev \
    libpq \
    zstd \
    lz4-libs

# Create pgexporter user
RUN adduser -D -s /bin/sh pgexporter

# Create necessary directories
RUN mkdir -p /etc/pgexporter /pgexporter
WORKDIR /pgexporter

# Copy binaries from builder
COPY --from=builder /usr/local/bin/pgexporter /usr/local/bin/pgexporter-cli /usr/local/bin/pgexporter-admin /usr/local/bin/
COPY --from=builder /usr/local/lib/libpgexporter.so* /usr/local/lib/

# Set permissions
RUN chown -R pgexporter:pgexporter /pgexporter /etc/pgexporter
RUN chmod +x /usr/local/bin/pgexporter /usr/local/bin/pgexporter-cli /usr/local/bin/pgexporter-admin

# Configure the application
EXPOSE 5002

# Switch to pgexporter user
USER pgexporter

# Create master key and user
RUN echo "pgexporter" | /usr/local/bin/pgexporter-admin master-key && \
    printf "pgexporter\npgexporter\npgexporter\n" | /usr/local/bin/pgexporter-admin -f /etc/pgexporter/pgexporter_users.conf user add

# Set the entrypoint
CMD ["/usr/local/bin/pgexporter", "-c", "/etc/pgexporter/pgexporter.conf", "-u", "/etc/pgexporter/pgexporter_users.conf"]