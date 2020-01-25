import logging

from fastapi import FastAPI, BackgroundTasks
from starlette.responses import JSONResponse, RedirectResponse
from starlette.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
from starlette.requests import Request
import pandas as pd

from stats import read_stats
from stats.database import db, weapon_types, stat_files


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
log.setLevel(level=logging.INFO)


templates = Jinja2Templates(directory='templates')
app = FastAPI("Stat-Server")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def database_connect():
    try:
        await db.connect()
        await read_stats.sync_weapons()
        await read_stats.insert_gs_files_to_db()
        await read_stats.process_lua_records()
    except Exception as err:
        log.error(f"Could not conect to database at {db.url}!")
        raise err


@app.on_event("shutdown")
def database_disconnect():
    db.close()


@app.get("/healthz")
def healthz():
    """Health-check endpoint.  Should return 200."""
    return "ok"


@app.get("/resync_stat_file")
async def resync_stat_file(request: Request, file_name: str):
    """Delete a previously processed file from the database, triggering a re-sync."""
    async with db.transaction():
        await db.execute(
            f"""DELETE FROM mission_stats
            WHERE file_name = '{file_name}'""")
        await db.execute(
            f"""DELETE FROM mission_stat_files
            WHERE file_name = '{file_name}'""")
    return RedirectResponse("/stats_logs")


@app.get("/stat_logs")
async def get_stat_logs(request: Request):
    """Get a json dictionary of mission-stat file status data."""
    tasks = BackgroundTasks()
    tasks.add_task(read_stats)
    data = await db.fetch_all(query=stat_files.select())
    data = pd.DataFrame.from_records(data, index=None)
    # Convert datetimes into strings because json cant serialize them otherwise.
    data['processed_at'] = data['processed_at'].apply(str)
    data['session_start_time'] = data['session_start_time'].apply(str)
    # Make sure columns are correctly ordered.
    # This table will render incorrectly if we dont... I don't know why.
    data = data[["file_name", "session_start_time", "processed",
                 "processed_at", "errors"]]
    data = data.to_dict('split')
    return JSONResponse(content=data)


@app.get("/weapon_db")
async def get_weapon_db_logs(request: Request):
    """Get a json dictionary of categorized weapons used for groupings."""
    df = await db.fetch_all(query=weapon_types.select())
    df = {"data": [list(d.values()) for d in df]}
    return JSONResponse(content=df)


@app.get("/overall")
async def get_overall_stats(request: Request):
    """Get a json dictionary of grouped statistics as key-value pairs."""
    data = await read_stats.collect_recs_kv()
    data = data.to_dict('split')
    return JSONResponse(content=data)


@app.get("/")
async def serve_homepage(request: Request):
    """Serve the index.html template."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/weapons")
async def weapon_stats(request: Request):
    """Return a rendered template with a table displaying per-weapon stats."""
    df = await read_stats.get_dataframe(subset=["weapons"])
    context = {"request": request,
               "data": df.to_html(table_id="stats", index=False)}
    return templates.TemplateResponse("weapons.html", context)


@app.get("/survivability")
async def suvival_stats(request: Request):
    """Return a rendered template showing kill/loss statistics."""
    df = await read_stats.get_dataframe(subset=["kills", "losses"])
    context = {"request": request,
               "data": df.to_html(table_id="stats", index=False)}
    return templates.TemplateResponse("survivability.html", context)


# @app.get("/json_data")
# async def json_data(request: Request, name: str):
#     try:
#         if name == "weapon_db":
#             df = await db.fetch_all(query=weapon_types.select())
#             df = {"data": [list(d.values()) for d in df]}
#         elif name == "stat_logs":
#             df = await db.fetch_all(query=stat_files.select())
#             df = pd.DataFrame.from_records(df, index=None)
#             df['processed_at'] = df['processed_at'].apply(str)
#             df['session_start_time'] = df['session_start_time'].apply(str)
#             df = df[["file_name", "session_start_time", "processed",
#                      "processed_at", "errors"]]
#             df = df.to_dict('split')
#         elif name == "overall":
#             df = await read_stats.collect_recs_kv()
#             df = df.to_dict('split')
#         else:
#             pass
#     except Exception as e:
#         log.error(e)
#         df = pd.DataFrame()
#     return JSONResponse(content=df)
