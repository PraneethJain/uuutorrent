#!/bin/bash

# Set variables
BACKUP_DIR="/backups"
POSTGRES_HOST="postgres"
POSTGRES_PORT="5432"
POSTGRES_USER="uuutorrent_user"
POSTGRES_DB="uuutorrent"
DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/${POSTGRES_DB}_${DATE}.sql.gz"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Create backup using pg_dump instead of pg_basebackup
# pg_dump doesn't require replication permissions
echo "Starting backup at $(date)"
pg_dump -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER $POSTGRES_DB | gzip > $BACKUP_FILE

# Check if backup was successful
if [ $? -eq 0 ]; then
    echo "Backup successfully created: $BACKUP_FILE"
    
    # Clean up old backups (keep last 7 days)
    find $BACKUP_DIR -name "${POSTGRES_DB}_*.sql.gz" -type f -mtime +7 -delete
    echo "Old backups cleaned up."
else
    echo "Backup failed!"
fi

echo "Backup process completed at $(date)"