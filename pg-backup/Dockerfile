FROM postgres:16

# Install cron
RUN apt-get update && apt-get install -y \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Create backup directory
RUN mkdir -p /backups && \
    chmod 777 /backups

# Create backup script
COPY backup.sh /backup.sh
RUN chmod +x /backup.sh

# Add crontab entry
RUN echo "0 3 * * * /backup.sh >> /var/log/cron.log 2>&1" > /etc/cron.d/pg-backup && \
    chmod 0644 /etc/cron.d/pg-backup && \
    crontab /etc/cron.d/pg-backup

# Create log file
RUN touch /var/log/cron.log

# Run cron in foreground
CMD cron && tail -f /var/log/cron.log