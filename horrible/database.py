import datetime
import logging
from pathlib import Path
import re
from typing import Optional

import databases
from starlette.config import Config
import sqlalchemy

metadata = sqlalchemy.MetaData()
logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)
LOG.setLevel(level=logging.INFO)


def parse_mission_stat_ts(path: str) -> Optional[datetime.datetime]:
    file_ = Path(path).name
    mat = re.search("([A-z]{3} [0-9]{1,2}, [0-9]{4} at [0-9]{2} [0-9]{2} [0-9]{2})",
                    file_)
    if mat:
        parsed = mat.group().replace("at ", "")
        return datetime.datetime.strptime(parsed, "%b %d, %Y %H %M %S")
    else:
        LOG.warning(f"Could not find timestamp in file path for {file_}!")
        return None


def parse_frametime_ts(path: str) -> datetime.datetime:
    file_ = Path(path).name
    file_ = file_.replace("fps_tracklog", "")
    file_ts = round(float(file_.replace(".log", "")), 2)
    return datetime.datetime.fromtimestamp(file_ts).replace(microsecond=0)


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


frametime_files = sqlalchemy.Table(
    "frametime_files",
    metadata,
    sqlalchemy.Column("file_name", sqlalchemy.String(), primary_key=True),
    sqlalchemy.Column("session_start_time", sqlalchemy.TIMESTAMP()),
    sqlalchemy.Column("processed", sqlalchemy.Boolean()),
    sqlalchemy.Column("processed_at", sqlalchemy.TIMESTAMP()),
    sqlalchemy.Column("errors", sqlalchemy.Integer)
)


frametimes = sqlalchemy.Table(
    "frametimes",
    metadata,
    sqlalchemy.Column("file_name", sqlalchemy.String(),
                      sqlalchemy.ForeignKey('frametime_files.file_name')),
    sqlalchemy.Column("frame_ts", sqlalchemy.TIMESTAMP()),
    sqlalchemy.Column("ts_fps", sqlalchemy.FLOAT())
)


file_format_ref = {
    'mission-stats/': parse_mission_stat_ts,
    'frametime/': parse_frametime_ts
}


config = Config('.env')
DATABASE_URL = config(
    'DATABASE_URL',
    default="postgresql://localhost:5432/dcs?user=prod&password=pwd")
db = databases.Database(DATABASE_URL)

