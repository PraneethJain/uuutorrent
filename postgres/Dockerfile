FROM postgres:16

# Update PostgreSQL configuration to enable pg_stat_statements
RUN echo "shared_preload_libraries = 'pg_stat_statements'" >> /usr/share/postgresql/postgresql.conf.sample && \
    echo "pg_stat_statements.max = 10000" >> /usr/share/postgresql/postgresql.conf.sample && \
    echo "pg_stat_statements.track = all" >> /usr/share/postgresql/postgresql.conf.sample && \
    echo "track_io_timing = on" >> /usr/share/postgresql/postgresql.conf.sample