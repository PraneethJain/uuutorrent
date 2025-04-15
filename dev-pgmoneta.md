# Using pgMoneta for PostgreSQL Backup Management

Once your Docker Compose stack is running, pgMoneta will automatically manage your PostgreSQL backups according to the configuration.

## Key commands for interacting with pgMoneta

### Exec into the pgMoneta container

```bash
docker-compose exec pgmoneta bash
```

### Check pgMoneta status

```bash
pgmoneta-cli status
```

### List available backups

```bash
pgmoneta-cli list primary
```

### Trigger a manual backup

```bash
pgmoneta-cli backup primary
```

### View backup information

```bash
pgmoneta-cli info primary [BACKUP_ID]
```

### Verify a backup

```bash
pgmoneta-cli verify primary [BACKUP_ID]
```

### Restore from a backup (stop PostgreSQL first)

```bash
# First stop PostgreSQL
docker-compose stop postgres

# Then restore
pgmoneta-cli restore primary [BACKUP_ID]

# Start PostgreSQL again
docker-compose start postgres
```

## Backup Locations

The backups and WAL files are stored in Docker volumes:
- Base backups: `pgmoneta_backup` volume
- WAL archives: `pgmoneta_wal` volume

## Configuration

The pgMoneta configuration is located in `pgmoneta.conf`. Key settings include:

- `backup_directory`: Location for base backups
- `wal_directory`: Location for WAL archives
- `retention`: How many days to keep backups
- `base_backup_interval`: How often to take backups (1d = daily)
- `base_backup_time`: When to schedule backups (HH:MM format)

## Metrics

pgMoneta exposes Prometheus-compatible metrics on port 5001. You can add this to your Prometheus
configuration to monitor backup performance and status.

## Additional Configuration

For more complex configurations, refer to the [pgMoneta documentation](https://pgmoneta.github.io/).