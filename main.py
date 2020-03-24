from pathlib import Path
import urllib.parse
from typing import cast

from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
import pandas as pd
from starlette.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
from starlette.requests import Request
from tacview_client import db as tac_db
from horrible.database import (db, weapon_types, stat_files,
                               frametime_files, event_files)
from horrible import read_stats, killcam
from horrible.config import log


templates = Jinja2Templates(directory='horrible/templates')
app = FastAPI(title="Stat-Server")
app.mount("/static",
          StaticFiles(directory="horrible/static", html=True),
          name="static")


@app.on_event("startup")
async def database_connect():
    try:
        await db.connect()
        await read_stats.sync_weapons()
        tac_db.create_tables()
    except Exception as err:
        log.error(f"Could not conect to database at {db.url}!")
        raise err


@app.on_event("shutdown")
async def database_disconnect():
    await db.disconnect()


@app.get("/healthz")
def healthz():
    """Health-check endpoint.  Should return 200."""
    return "ok"


@app.get("/resync_file/")
async def resync_file(request: Request, file_name: str):
    """Delete a previously processed file from the database, triggering a re-sync."""
    stat_file_name = Path(urllib.parse.unquote(file_name))
    if 'mission-stats' in file_name:
        log.info(f"Attempting to resync stats-file: {stat_file_name}...")
        log.info(f"Deleting filename: {stat_file_name} from database...")
        async with db.transaction():
            await db.execute(f"""DELETE FROM mission_stats
                WHERE file_name = '{stat_file_name}'""")
            await db.execute(f"""DELETE FROM mission_stat_files
                WHERE file_name = '{stat_file_name}'""")
            if stat_file_name.exists():
                stat_file_name.unlink()
            else:
                log.warning("Local cached copy of file not found!")
    return "ok"


@app.get("/stat_logs")
async def get_stat_logs(request: Request):
    """Get a json dictionary of mission-stat file status data."""
    try:
        data_recs = await db.fetch_all(query=stat_files.select())
        data = pd.DataFrame.from_records(data_recs, index=None)
        # Convert datetimes into strings because json cant serialize them otherwise.
        data[[
            'processed_at',
            'session_start_time',
            'session_last_update',
        ]] = data[[
            'processed_at',
            'session_start_time',
            'session_last_update',
        ]].astype(str)  # type: ignore
        # Make sure columns are correctly ordered.
        # This table will render incorrectly if we dont... I don't know why.
        data = data[[
            "file_name", "session_start_time", 'session_last_update', 'file_size_kb',
            "processed", "processed_at", "errors"
        ]]
        return data
    # .to_dict('split') # type: ignore
    except Exception as e:
        log.error(e)
        return {}


@app.get("/event_logs")
async def get_event_logs(request: Request):
    """Get a json dictionary of mission-event file status data."""
    try:
        data_recs = await db.fetch_all(query=event_files.select())
        data = pd.DataFrame.from_records(data_recs, index=None)
        # Convert datetimes into strings because json cant serialize them otherwise.
        data[[
            'processed_at',
            'session_start_time',
            'session_last_update',
        ]] = data[[
            'processed_at',
            'session_start_time',
            'session_last_update',
        ]].astype(str)  # type: ignore
        # Make sure columns are correctly ordered.
        # This table will render incorrectly if we dont... I don't know why.
        data = data[[
            "file_name", "session_start_time", 'session_last_update',
            'file_size_kb', "processed", "processed_at", "errors"
        ]]
        return data.to_dict('split')  # type: ignore
    except Exception as e:
        log.error(e)
        return {}


@app.get("/frametime_logs")
async def get_frametime_logs(request: Request):
    """Get a json dictionary of mission-stat file status data."""
    data_recs = await db.fetch_all(frametime_files.select())
    data = pd.DataFrame.from_records(data_recs, index=None)
    # Convert datetimes into strings because json cant serialize them otherwise.
    data[[
        'processed_at',
        'session_start_time',
        'session_last_update',
    ]] = data[[
        'processed_at',
        'session_start_time',
        'session_last_update',
    ]].astype(str)  # type: ignore
    # Make sure columns are correctly ordered.
    # This table will render incorrectly if we dont... I don't know why.
    data = data[[
        "file_name", "session_start_time", 'session_last_update', "processed",
        'file_size_kb', "processed_at", "errors"
    ]]
    return data.to_dict('split')  # type: ignore


# @app.get("/frametime_charts")
# async def get_frametime_charts(request: Request, pctile: int = 50):
#     """Get a dataframe of frametime records."""
#     files = await db.fetch_one(frametime_files.select().order_by(
#         sa.desc(sa.text("session_start_time"))))
#     log.info("Looking up most recent log file...")
#     data = read_stats.read_frametime(filename=files['file_name'],
#                                      pctile=pctile)
#     return JSONResponse(content=data)


@app.get("/weapon_db")
async def get_weapon_db_logs(request: Request):
    """Get a json dictionary of categorized weapons used for groupings."""
    data = await db.fetch_all(query=weapon_types.select())
    content = {"data": [], "columns": list(data[0].keys())}
    for row in data:
        content['data'].append(list(row.values()))
    return content


@app.get("/overall")
async def get_overall_stats(request: Request):
    """Get a json dictionary of grouped statistics as key-value pairs."""
    data = await read_stats.calculate_overall_stats(grouping_cols=['pilot'])
    data = data.to_dict('split')
    return data


@app.get("/session_performance")
async def get_session_perf_stats(request: Request):
    """Get a json dictionary of grouped statistics as key-value pairs."""
    data = await read_stats.calculate_overall_stats(
        grouping_cols=['session_start_date', 'pilot'])
    data.sort_values(by=['session_start_date', 'A/A Kills'],
                     ascending=False,
                     inplace=True)
    data = data.to_dict('split')
    return data


@app.get("/")
async def serve_homepage(request: Request):
    """Serve the index.html template."""
    with open("horrible/static/index.html", mode='r') as fp_:
        page = fp_.read()
    return HTMLResponse(page)


@app.get("/weapons")
async def weapon_stats(request: Request):
    """Return a rendered template with a table displaying per-weapon stats."""
    data = await read_stats.get_dataframe(subset=["weapons"])
    return data.to_dict('split')


@app.get("/kills")
async def kill_detail(request: Request):
    """Return a rendered template showing kill/loss statistics."""
    data = await read_stats.get_dataframe(subset=["kills"])
    return data.to_dict("split")


@app.get("/losses")
async def loss_detail(request: Request):
    """Return a rendered template showing kill/loss statistics."""
    data = await read_stats.get_dataframe(subset=["losses"])
    return data.to_dict("split")


@app.get("/tacview")
async def tacview_detail(request: Request):
    """Return tacview download links."""
    data = await read_stats.query_tacview_files(db)
    return data


@app.get("/process_tacview/")
async def process_tacview(filename: str):
    """Trigger processing of a tacview file."""
    # tasks.add_task(read_stats.process_tacview_file,
    #                      urllib.parse.unquote(filename))
    return "ok"

@app.get("/events")
async def event_detail(request: Request):
    """Return SlMod event records."""
    data = await read_stats.read_events()
    data.to_dict("split")


@app.get("/raw_cats/")
async def raw_cats(request: Request, pilot: str = None):
    """Return a rendered template showing kill/loss statistics."""
    data = await read_stats.collect_recs_kv()
    if pilot:
        data = cast(pd.DataFrame,
                    data.query(f"pilot == '{urllib.parse.unquote(pilot)}'"))
        data.reset_index(drop=True, inplace=True)

    data = data.groupby([
        'session_start_date', 'equipment', 'stat_group', 'key_orig',
        'category', 'metric'], as_index=False).sum()
    data.sort_values(by=['session_start_date'], ascending=False, inplace=True)
    return HTMLResponse(content=data.to_html())


@app.get("/tacview_kills")
async def tacview_kills(request: Request):
    """Get a list of tacview kills."""
    data = await killcam.get_all_kills(db)
    data.to_dict("split") # type: ignore


@app.get("/killcam")
async def serve_killcam(request: Request):
    """Serve the index.html template."""
    with open("horrible/static/killcam.html", mode='r') as fp_:
        page = fp_.read()
    return HTMLResponse(page)


@app.get("/kill_coords")
async def get_kill_coords(request: Request, kill_id: int):
    """Get Points Preceeding kill."""
    # pilot = urllib.parse.unquote(kill_id)
    data = await killcam.get_kill(kill_id, db)
    if not data:
        return JSONResponse(status_code=500)
    return data
