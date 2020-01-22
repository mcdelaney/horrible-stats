#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  CREATE TABLE IF NOT EXISTS mission_stat_files (
      id SERIAL,
      file_name VARCHAR(500) PRIMARY KEY,
      processed boolean DEFAULT FALSE,
      processed_at timestamp DEFAULT NULL,
      uploaded_at timestamp DEFAULT CURRENT_TIMESTAMP,
      errors INTEGER DEFAULT 0
  );

  CREATE TABLE IF NOT EXISTS mission_stats (
      file_name VARCHAR(500),
      session_start_time timestamp,
      record json
  );

EOSQL
