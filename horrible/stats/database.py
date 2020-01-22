from starlette.config import Config
import databases

config = Config('.env')
DATABASE_URL = config('DATABASE_URL')

mission_stat_files = """CREATE TABLE IF NOT EXISTS mission_stat_files (
    id SERIAL,
    file_name VARCHAR(500) PRIMARY KEY,
    processed boolean DEFAULT FALSE,
    processed_at timestamp DEFAULT NULL,
    uploaded_at timestamp DEFAULT CURRENT_TIMESTAMP
)"""

mission_stats = """CREATE TABLE IF NOT EXISTS mission_stats (
    file_name VARCHAR(500),
    session_start_time timestamp,
    record json
)"""

db = databases.Database(DATABASE_URL)
