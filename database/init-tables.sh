#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL

  CREATE TABLE IF NOT EXISTS weapon_types (
      name varchar(500) PRIMARY KEY,
      category VARCHAR(500),
      type varchar(500)
  );

  CREATE TABLE IF NOT EXISTS mission_stat_files (
      file_name VARCHAR(500) PRIMARY KEY,
      session_start_time TIMESTAMP,
      processed boolean DEFAULT FALSE,
      processed_at timestamp DEFAULT NULL,
      uploaded_at timestamp DEFAULT date_trunc('second', CURRENT_TIMESTAMP),
      errors INTEGER DEFAULT 0
  );

  CREATE TABLE IF NOT EXISTS mission_stats (
      file_name VARCHAR(500) REFERENCES mission_stat_files(file_name),
      pilot varchar(500),
      pilot_id INTEGER,
      record json
  );

  CREATE TABLE IF NOT EXISTS frametime_files (
      file_name VARCHAR(500) PRIMARY KEY,
      session_start_time TIMESTAMP,
      processed boolean DEFAULT FALSE,
      processed_at timestamp DEFAULT NULL,
      uploaded_at timestamp DEFAULT date_trunc('second', CURRENT_TIMESTAMP),
      errors INTEGER DEFAULT 0
  );

  CREATE TABLE IF NOT EXISTS frametimes (
      file_name VARCHAR(500) REFERENCES frametime_files(file_name),
      frame_ts TIMESTAMP,
      ts_fps INT
  );

EOSQL
