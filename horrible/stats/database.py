import databases
from starlette.config import Config
import sqlalchemy

metadata = sqlalchemy.MetaData()

weapon_types = sqlalchemy.Table(
    "weapon_types",
    metadata,
    sqlalchemy.Column("name", sqlalchemy.String(), primary_key=True),
    sqlalchemy.Column("category", sqlalchemy.String()),
    sqlalchemy.Column("type", sqlalchemy.String()),
)


stat_files = sqlalchemy.Table(
    "mission_stat_files",
    metadata,
    sqlalchemy.Column("file_name", sqlalchemy.String(), primary_key=True),
    sqlalchemy.Column("session_start_time", sqlalchemy.TIMESTAMP()),
    sqlalchemy.Column("processed", sqlalchemy.Boolean()),
    sqlalchemy.Column("processed_at", sqlalchemy.TIMESTAMP()),
    sqlalchemy.Column("errors", sqlalchemy.Integer)
)


mission_stats = sqlalchemy.Table(
    "mission_stats",
    metadata,
    sqlalchemy.Column("file_name", sqlalchemy.String(),
                      sqlalchemy.ForeignKey('mission_stat_files.file_name')),
    sqlalchemy.Column("pilot", sqlalchemy.String()),
    sqlalchemy.Column("record", sqlalchemy.JSON())
)


config = Config('.env')
DATABASE_URL = config('DATABASE_URL')
db = databases.Database(DATABASE_URL)
