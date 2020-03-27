import datetime
import logging
from pathlib import Path
import re
from typing import Optional
import pytz

from starlette.config import Config
import sqlalchemy


logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)
LOG.setLevel(level=logging.INFO)

config = Config('.env')
DATABASE_URL = config(
    'DATABASE_URL',
    default="postgresql://localhost:5432/dcs?user=prod&password=pwd")

metadata = sqlalchemy.MetaData()


def create_tables():
    """ensure tables are created."""
    try:
        eng = sqlalchemy.create_engine(DATABASE_URL)
        metadata.bind = eng
        metadata.create_all()
    except Exception as err:
        LOG.error(err)


def convert_to_utc(ts):
    if ts > datetime.datetime(2020, 3, 20, 1, 1, 1):
        tzone = pytz.timezone('US/Mountain')
    else:
        tzone = pytz.timezone('US/Eastern')
    localized = tzone.localize(ts)
    utc_time = localized.astimezone(pytz.utc)
    return utc_time


def parse_mission_stat_ts(path: str) -> Optional[datetime.datetime]:
    file_ = Path(path).name
    mat = re.search("([A-z]{3} [0-9]{1,2}, [0-9]{4} at [0-9]{2} [0-9]{2} [0-9]{2})",
                    file_)
    if mat:
        parsed = mat.group().replace("at ", "")
        ts = datetime.datetime.strptime(parsed, "%b %d, %Y %H %M %S")
        ts = ts.replace(microsecond=0)
        ts = convert_to_utc(ts)
        return ts
    else:
        LOG.warning(f"Could not find timestamp in file path for {file_}!")
        return None


def parse_frametime_ts(path: str) -> datetime.datetime:
    file_ = Path(path).name
    file_ = file_.replace("fps_tracklog", "")
    file_ts = round(float(file_.replace(".log", "")), 2)
    ts =  datetime.datetime.fromtimestamp(file_ts)
    ts = ts.replace(microsecond=0)
    ts = convert_to_utc(ts)
    return ts


def parse_tacview_prefix(line):
    fmt = 'tacview/Tacview-%Y%m%d-%H%M%S'
    try:
        ts = datetime.datetime.strptime(line, fmt)
    except ValueError as v:
        if len(v.args) > 0 and v.args[0].startswith('unconverted data remains: '):
            line = line[:-(len(v.args[0]) - 26)]
            ts = datetime.datetime.strptime(line, fmt)
        else:
            raise
    ts = ts.replace(microsecond=0)
    ts = ts.replace(tzinfo=pytz.utc)
    return ts


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
    sqlalchemy.Column("session_start_time", sqlalchemy.TIMESTAMP(timezone=True)),
    sqlalchemy.Column("session_last_update", sqlalchemy.TIMESTAMP()),
    sqlalchemy.Column("file_size_kb", sqlalchemy.Float()),
    sqlalchemy.Column("processed", sqlalchemy.Boolean()),
    sqlalchemy.Column("process_start", sqlalchemy.TIMESTAMP()),
    sqlalchemy.Column("process_end", sqlalchemy.TIMESTAMP()),
    sqlalchemy.Column("errors", sqlalchemy.Integer),
    sqlalchemy.Column("error_msg", sqlalchemy.String()),
)


mission_stats = sqlalchemy.Table(
    "mission_stats",
    metadata,
    sqlalchemy.Column("file_name", sqlalchemy.String(),
                      sqlalchemy.ForeignKey('mission_stat_files.file_name')),
    sqlalchemy.Column("pilot", sqlalchemy.String()),
    sqlalchemy.Column("pilot_id", sqlalchemy.Integer),
    sqlalchemy.Column("record", sqlalchemy.JSON())
)

event_files = sqlalchemy.Table(
    "mission_event_files",
    metadata,
    sqlalchemy.Column("file_name", sqlalchemy.String(), primary_key=True),
    sqlalchemy.Column("session_start_time", sqlalchemy.TIMESTAMP(timezone=True)),
    sqlalchemy.Column("session_last_update", sqlalchemy.TIMESTAMP()),
    sqlalchemy.Column("file_size_kb", sqlalchemy.Float()),
    sqlalchemy.Column("processed", sqlalchemy.Boolean()),
    sqlalchemy.Column("process_start", sqlalchemy.TIMESTAMP()),
    sqlalchemy.Column("process_end", sqlalchemy.TIMESTAMP()),
    sqlalchemy.Column("errors", sqlalchemy.Integer),
    sqlalchemy.Column("error_msg", sqlalchemy.String()),
)


mission_events = sqlalchemy.Table(
    "mission_events",
    metadata,
    sqlalchemy.Column("file_name", sqlalchemy.String(),
                      sqlalchemy.ForeignKey('mission_event_files.file_name')),
    sqlalchemy.Column("record", sqlalchemy.JSON())
)


frametime_files = sqlalchemy.Table(
    "frametime_files", metadata,
    sqlalchemy.Column("file_name", sqlalchemy.String(), primary_key=True),
    sqlalchemy.Column("session_start_time", sqlalchemy.TIMESTAMP(timezone=True)),
    sqlalchemy.Column("session_last_update", sqlalchemy.TIMESTAMP()),
    sqlalchemy.Column("file_size_kb", sqlalchemy.Float()),
    sqlalchemy.Column("processed", sqlalchemy.Boolean()),
    sqlalchemy.Column("process_start", sqlalchemy.TIMESTAMP()),
    sqlalchemy.Column("process_end", sqlalchemy.TIMESTAMP()),
    sqlalchemy.Column("errors", sqlalchemy.Integer))


tacview_files = sqlalchemy.Table(
    "tacview_files", metadata,
    sqlalchemy.Column("file_name", sqlalchemy.String(), primary_key=True),
    sqlalchemy.Column("session_start_time", sqlalchemy.TIMESTAMP(timezone=True)),
    sqlalchemy.Column("session_last_update", sqlalchemy.TIMESTAMP()),
    sqlalchemy.Column("file_size_kb", sqlalchemy.Float()),
    sqlalchemy.Column("processed", sqlalchemy.Boolean()),
    sqlalchemy.Column("process_start", sqlalchemy.TIMESTAMP()),
    sqlalchemy.Column("process_end", sqlalchemy.TIMESTAMP()),
    sqlalchemy.Column("errors", sqlalchemy.Integer))


frametimes = sqlalchemy.Table(
    "frametimes",
    metadata,
    sqlalchemy.Column("file_name", sqlalchemy.String(),
                      sqlalchemy.ForeignKey('frametime_files.file_name')),
    sqlalchemy.Column("frame_ts", sqlalchemy.TIMESTAMP()),
    sqlalchemy.Column("ts_fps", sqlalchemy.FLOAT())
)


file_format_ref = {
    'mission-stats': parse_mission_stat_ts,
    'frametime': parse_frametime_ts,
    'mission-events': parse_mission_stat_ts,
    'tacview': parse_tacview_prefix
}


