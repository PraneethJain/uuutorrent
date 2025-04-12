FROM alpine:latest

RUN apk add --no-cache git

RUN git clone https://github.com/pgexporter/pgexporter.git /pgexporter

WORKDIR /pgexporter
RUN apk add --no-cache \
    bash \
    build-base \
    cmake \
    make \
    postgresql-dev \
    zlib-dev \
    zstd-dev \
    lz4-dev \
    bzip2-dev \
    openssl-dev \
    yaml-dev

# Build pgexporter
RUN ./autogen.sh && \
    ./configure --prefix=/usr && \
    make && \
    make install

# Create master key and user
RUN echo "pgexporter" | pgexporter-admin master-key && \
    printf "pgexporter\npgexporter\npgexporter\n" | pgexporter-admin -f /etc/pgexporter/pgexporter_users.conf user add

# Configure pgexporter
EXPOSE 5002

CMD ["pgexporter", "-c", "/etc/pgexporter/pgexporter.conf", "-u", "/etc/pgexporter/pgexporter_users.conf"]