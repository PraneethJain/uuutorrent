-- Enable pg_stat_statements extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Grant access to the uuutorrent_user
GRANT SELECT ON pg_stat_statements TO uuutorrent_user;

-- Create a view for simplified query stats
CREATE OR REPLACE VIEW query_stats AS
SELECT
    query,
    calls,
    total_exec_time,
    min_exec_time,
    max_exec_time,
    mean_exec_time,
    stddev_exec_time,
    rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC;

-- Grant access to the view
GRANT SELECT ON query_stats TO uuutorrent_user;