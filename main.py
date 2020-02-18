import logging

from fastapi import FastAPI, BackgroundTasks
from starlette.responses import JSONResponse, RedirectResponse, HTMLResponse
from starlette.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
from starlette.requests import Request
import pandas as pd
from pathlib import Path
import sqlalchemy as sa
import urllib.parse
from typing import Optional

from horrible.database import db, weapon_types, stat_files, frametime_files
from horrible import read_stats

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
log.setLevel(level=logging.INFO)
consoleHandler = logging.StreamHandler()
log.addHandler(consoleHandler)

templates = Jinja2Templates(directory='horrible/templates')
app = FastAPI(title="Stat-Server")
app.mount("/main",
          StaticFiles(directory="horrible/static", html=True),
          name="static")


@app.on_event("startup")
async def database_connect():
    try:
        await db.connect()
        await read_stats.update_all_logs_and_stats(db)
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


@app.get("/check_db_files")
async def check_db_files(request: Request):
    """Trigger db update."""
    await read_stats.update_all_logs_and_stats(db)
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

            # local_cache = Path("horrible/data/" + file_name)
            if stat_file_name.exists():
                stat_file_name.unlink()
            else:
                log.warning("Local cached copy of file not found!")

        await read_stats.update_all_logs_and_stats(db)
    return "ok"


@app.get("/stat_logs")
async def get_stat_logs(request: Request):
    """Get a json dictionary of mission-stat file status data."""
    tasks = BackgroundTasks()
    tasks.add_task(read_stats.update_all_logs_and_stats)
    try:
        data_recs = await db.fetch_all(query=stat_files.select())
        data = pd.DataFrame.from_records(data_recs, index=None)
        # Convert datetimes into strings because json cant serialize them otherwise.
        data[['processed_at', 'session_start_time'
              ]] = data[['processed_at',
                         'session_start_time']].astype(str)  # type: ignore
        # Make sure columns are correctly ordered.
        # This table will render incorrectly if we dont... I don't know why.
        data = data[[
            "file_name", "session_start_time", "processed", "processed_at",
            "errors"
        ]]
        return JSONResponse(content=data.to_dict('split'))  # type: ignore
    except Exception as e:
        log.error(e)
        return JSONResponse(content={})


@app.get("/frametime_logs")
async def get_frametime_logs(request: Request):
    """Get a json dictionary of mission-stat file status data."""
    data_recs = await db.fetch_all(frametime_files.select())
    data = pd.DataFrame.from_records(data_recs, index=None)
    # Convert datetimes into strings because json cant serialize them otherwise.
    data[['processed_at',
          'session_start_time']] = data[['processed_at', 'session_start_time'
                                         ]].astype(str)  # type: ignore
    # Make sure columns are correctly ordered.
    # This table will render incorrectly if we dont... I don't know why.
    data = data[[
        "file_name", "session_start_time", "processed", "processed_at",
        "errors"
    ]]
    return JSONResponse(content=data.to_dict('split'))  # type: ignore


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
    return JSONResponse(content=content)


@app.get("/overall")
async def get_overall_stats(request: Request):
    """Get a json dictionary of grouped statistics as key-value pairs."""
    data = await read_stats.calculate_overall_stats(grouping_cols=['pilot'])
    data = data.to_dict('split')
    return JSONResponse(content=data)


@app.get("/session_performance")
async def get_session_perf_stats(request: Request):
    """Get a json dictionary of grouped statistics as key-value pairs."""
    data = await read_stats.calculate_overall_stats(
        grouping_cols=['session_date', 'pilot'])
    data.sort_values(by=['session_date', 'A/A Kills'], ascending=False, inplace=True)
    data = data.to_dict('split')
    return JSONResponse(content=data)


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
    return JSONResponse(content=data.to_dict('split'))


@app.get("/kills")
async def kill_detail(request: Request):
    """Return a rendered template showing kill/loss statistics."""
    data = await read_stats.get_dataframe(subset=["kills"])
    return JSONResponse(content=data.to_dict("split"))


@app.get("/losses")
async def loss_detail(request: Request):
    """Return a rendered template showing kill/loss statistics."""
    data = await read_stats.get_dataframe(subset=["losses"])
    return JSONResponse(content=data.to_dict("split"))


@app.get("/raw_cats/")
async def raw_cats(request: Request, pilot: str = None):
    """Return a rendered template showing kill/loss statistics."""
    data = await read_stats.collect_recs_kv()

    if pilot:
        data = data.query(f"pilot == '{urllib.parse.unquote(pilot)}'")
        data.reset_index(drop=True, inplace=True)

    data = data.groupby(
        ['session_date', 'equipment', 'stat_group', 'key_orig', 'category', 'metric'],
        as_index=False).sum()
    data.sort_values(by=['session_date'], ascending=False, inplace=True)
    return HTMLResponse(content=data.to_html())
