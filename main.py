from pathlib import Path
import urllib.parse
from typing import cast

import databases
from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
from starlette.requests import Request

from horrible.database import DATABASE_URL
from horrible import read_stats, killcam
from horrible.config import get_logger

db = databases.Database(DATABASE_URL)
log = get_logger('horrible')

app = FastAPI(title="Stat-Server")
app.mount("/static",
          StaticFiles(directory="static"),
          name="static")


@app.on_event("startup")
async def database_connect():
    try:
        await db.connect()
        log.info('Startup complete...')
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


@app.get("/")
async def serve_index():
    return FileResponse("./static/index.html")


@app.get("/static/js/main.js")
async def serve_js():
    return FileResponse("./static/js/main.js")

@app.get("/static/css/main.css")
async def serve_css():
    return FileResponse("./static/css/main.css")

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
        data = await db.fetch_all("""SELECT
        file_name, session_start_time, session_last_update, processed,
        file_size_kb, process_start, errors
        FROM mission_stat_files
        """)
        return read_stats.dict_to_js_datatable_friendly_fmt(data)
    except Exception as e:
        log.error(e)
        return {}


@app.get("/event_logs")
async def get_event_logs(request: Request):
    """Get a json dictionary of mission-event file status data."""
    try:
        data = await db.fetch_all("""SELECT
        file_name, session_start_time, session_last_update, processed,
        file_size_kb, process_start, errors
        FROM mission_event_files
        """)
        return read_stats.dict_to_js_datatable_friendly_fmt(data)
    except Exception as e:
        log.error(e)
        return {}


@app.get("/frametime_logs")
async def get_frametime_logs(request: Request):
    """Get a json dictionary of mission-stat file status data."""
    data = await db.fetch_all("""SELECT
        file_name, session_start_time, session_last_update, processed,
        file_size_kb, process_start, errors
        FROM frametime_files
        """
    )
    return read_stats.dict_to_js_datatable_friendly_fmt(data)

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
    data = await db.fetch_all('SELECT * FROM weapon_types')
    content = {"data": [], "columns": list(data[0].keys())}
    for row in data:
        content['data'].append(list(row.values()))
    return content


@app.get("/overall")
async def get_overall_stats(request: Request):
    """Get a json dictionary of grouped statistics as key-value pairs."""
    data = await read_stats.calculate_overall_stats(grouping_cols=['pilot'], db=db)
    data = data.to_dict('split')
    return JSONResponse(content=data)


@app.get("/session_performance")
async def get_session_perf_stats(request: Request):
    """Get a json dictionary of grouped statistics as key-value pairs."""
    data = await read_stats.calculate_overall_stats(
        grouping_cols=['session_start_date', 'pilot'],
        db=db)
    data.sort_values(by=['session_start_date', 'A/A Kills'],
                     ascending=False,
                     inplace=True)
    data = data.to_dict('split')
    return JSONResponse(content=data)


# @app.get("/")
# async def serve_homepage(request: Request):
#     """Serve the index.html template."""
#     with open("static/index.html", mode='r') as fp_:
#         page = fp_.read()
#     return HTMLResponse(page)


@app.get("/weapons")
async def weapon_stats(request: Request):
    """Return a rendered template with a table displaying per-weapon stats."""
    data = await read_stats.get_dataframe(db, subset=["weapons"])
    return data.to_dict('split')


@app.get("/kills")
async def kill_detail(request: Request):
    """Return a rendered template showing kill/loss statistics."""
    data = await read_stats.get_dataframe(db, subset=["kills"])
    return data.to_dict("split")


@app.get("/losses")
async def loss_detail(request: Request):
    """Return a rendered template showing kill/loss statistics."""
    data = await read_stats.get_dataframe(db, subset=["losses"])
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
    data = await read_stats.read_events(db)
    return data.to_dict("split")


@app.get("/tacview_kills")
async def tacview_kills(request: Request):
    """Get a list of tacview kills."""
    data = await killcam.get_all_kills(db)
    return data


@app.get("/kill_coords")
async def get_kill_coords(request: Request, kill_id: int):
    """Get Points Preceeding kill."""
    # pilot = urllib.parse.unquote(kill_id)
    data = await killcam.get_kill(kill_id, db)
    if not data:
        return JSONResponse(status_code=500)
    return JSONResponse(content=data)
