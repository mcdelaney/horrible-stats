import logging

from fastapi import FastAPI
from starlette.responses import JSONResponse, RedirectResponse
from starlette.templating import Jinja2Templates
from starlette.requests import Request
import pandas as pd

from stats import read_stats
from stats.database import db, DATABASE_URL


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
    except Exception as err:
        logging.error(f"Could not conect to database at {DATABASE_URL}!")
        raise err


@app.on_event("shutdown")
def database_disconnect():
    db.close()


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/stats_logs")
async def get_stats_logs(request: Request):
    await read_stats.insert_gs_files_to_db()
    await read_stats.process_lua_records()
    records = await db.fetch_all(
        query="""SELECT file_name, processed, processed_at, uploaded_at, errors
                FROM mission_stat_files
                ORDER BY uploaded_at DESC
                """)
    records = [dict(r) for r in records]
    records = pd.DataFrame.from_records(records, index=None)
    context = {"request": request,
               "data": records.to_html(table_id="stats", index=False)}
    return templates.TemplateResponse("stats_logs.html", context)


@app.get("/old")
async def stats(request: Request):
    df = await read_stats.get_dataframe()
    context = {"request": request,
               "data": df.to_html(table_id="stats", index=False)}
    return templates.TemplateResponse("index_old.html", context)


@app.get("/")
async def new_stats(request: Request):
    df = await read_stats.get_dataframe()
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
async def json_data(request: Request):
    df = await read_stats.get_dataframe()
    return JSONResponse(content=df.to_json(orient="split", index=False))
