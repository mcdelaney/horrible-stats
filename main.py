from pathlib import Path
import urllib.parse

import databases
from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from starlette.requests import Request

from horrible.database import DATABASE_URL
from horrible import read_stats, killcam
from horrible.config import get_logger
from horrible.read_stats import process_tacview_file

# SW
from horrible.get_tacview_file import fetch_tacview_file
from horrible.mapping import create_map

db = databases.Database(DATABASE_URL, min_size=1, max_size=3)
log = get_logger('horrible')
MESHES = [str(p.name) for p in list(Path("static/mesh/").glob("*.obj"))]
# MESHES = [str(p.name) for p in list(Path("static/mesh/").glob("*.glb"))]
app = FastAPI(title="Stat-Server")


@app.on_event("startup")
async def database_connect():
    try:
        await db.connect()
        await db.execute("SET application_name to app_server")
        log.info('Startup complete...')
    except Exception as err:
        log.error(f"Could not conect to database at {db.url}!")
        raise err


@app.on_event("shutdown")
async def database_disconnect():
    try:
        log.info("Attempting database disconnect...")
        await db.disconnect()
    except Exception:
        log.error("Disconnect fail! Probably had no connection to start with!")


@app.get("/healthz")
def healthz():
    """Health-check endpoint.  Should return 200."""
    return "ok"


@app.get("/")
async def serve_index():
    return FileResponse("./static/index.html")

@app.get("/static/mesh")
async def serve_mesh(request: Request, obj_name: str):
    log.info(f"Looking up mesh for: {obj_name}")
    obj_name = obj_name.replace("F-14B", "F-14")
    obj_name = obj_name.replace("F-16C", "F-16")
    obj_name = obj_name.replace("F-4E", "F-4")
    obj_name = obj_name.replace("F-15C", "F-15")

    if obj_name in MESHES:
        return FileResponse(f"./static/mesh/{obj_name}")
    log.info(f"Direct match not found for {obj_name}")
    if not 'FixedWing' in obj_name:
        return FileResponse('./static/mesh/Missile.AIM-120C.obj')
    else:
        return FileResponse('./static/mesh/FixedWing.F-18C.obj')


@app.get("/static/images/{img_name}")
async def serve_mesh(img_name: str):
    return FileResponse(f"./static/images/{img_name}")

@app.get("/static/textures/{img_name}")
async def serve_texture(img_name: str):
    return FileResponse(f"./static/textures/{img_name}")


@app.get("/static/main-bundle.js")
async def serve_js():
    return FileResponse("./static/main-bundle.js")


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
    return data


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
    return data


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

#  SW
@app.get("/tacview")
async def tacview_detail(request: Request):
    """Return tacview download links."""
    data = await read_stats.query_tacview_files(db)
    return data

@app.get("/process_tacview")
async def process_tacview(filename: str):
    """Trigger processing of a tacview file."""
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

@app.get("/maps")
#async def mission_map(coordinates: list): # coordinates arg ?
async def mission_map(): # coordinates arg ?
    """Show theater map"""
    data = await create_map()
    return data

#  SW
@app.get("/get_tacview_file")
async def fetch_tview_file(filename: str):
    """ Ask the cloud server for a file or shareable link """
    data = await fetch_tacview_file(filename)
    return data # return filename