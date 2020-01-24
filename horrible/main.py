import logging

from fastapi import FastAPI
from starlette.responses import JSONResponse, RedirectResponse
from starlette.templating import Jinja2Templates
from starlette.requests import Request
import pandas as pd

from stats import read_stats
from stats.database import db, weapon_types, stat_files


logging.basicConfig(level=logging.INFO)
templates = Jinja2Templates(directory='templates')


class StatServer(FastAPI):
    def __init__(self, *kwargs, **args):
        FastAPI.__init__(self, "Stat_server")
        self.columns = []


app = StatServer()


@app.on_event("startup")
async def database_connect():
    try:
        await db.connect()
        await read_stats.sync_weapons()
        await read_stats.insert_gs_files_to_db()
        await read_stats.process_lua_records()
    except Exception as err:
        logging.error(f"Could not conect to database at {db.url}!")
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


@app.get("/stats_logs")
async def get_stats_logs(request: Request):
    await read_stats.sync_weapons()
    await read_stats.insert_gs_files_to_db()
    await read_stats.process_lua_records()
    context = {"request": request}
    return templates.TemplateResponse("stats_logs.html", context)


@app.get("/weapon_db")
async def get_weapon_db_logs(request: Request):
    context = {"request": request}
    return templates.TemplateResponse("weapon_db.html", context)


@app.get("/")
async def new_stats(request: Request):
    df = await read_stats.collect_recs_kv()
    context = {"request": request,
               "data": df.to_html(table_id="stats", index=False)}
    return templates.TemplateResponse("index.html", context)


@app.get("/weapons")
async def weapon_stats(request: Request):
    df = await read_stats.get_dataframe(subset=["weapons"])
    context = {"request": request,
               "data": df.to_html(table_id="stats", index=False)}
    return templates.TemplateResponse("weapons.html", context)


@app.get("/survivability")
async def suvival_stats(request: Request):
    df = await read_stats.get_dataframe(subset=["kills", "losses"])
    context = {"request": request,
               "data": df.to_html(table_id="stats", index=False)}
    return templates.TemplateResponse("survivability.html", context)


@app.get("/json_data")
async def json_data(request: Request, name: str):
    try:
        if name == "weapons_db":
            df = await db.fetch_all(query=weapon_types.select())
            df = pd.DataFrame.from_records(df, index=None)
        elif name == "stat_logs":
            df = await db.fetch_all(query=stat_files.select())
            df = pd.DataFrame.from_records(df, index=None)
            df['processed_at'] = df['processed_at'].apply(str)
            df['session_start_time'] = df['session_start_time'].apply(str)
        elif name == "overall":
            df = await read_stats.collect_recs_kv()
        else:
            pass
    except Exception as e:
        logging.error(e)
        df = pd.DataFrame()
    return JSONResponse(content=df.to_dict('split'))
