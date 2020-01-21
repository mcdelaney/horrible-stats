import logging

from fastapi import FastAPI
from starlette.responses import JSONResponse
from starlette.templating import Jinja2Templates
from starlette.requests import Request
from starlette.config import Config

from stats import read_stats
from stats.database import db, mission_stats, mission_stat_files


logging.basicConfig(level=logging.INFO)
templates = Jinja2Templates(directory='templates')

config = Config('.env')


class StatServer(FastAPI):
    def __init__(self, *kwargs, **args):
        FastAPI.__init__(self, "Stat_server")
        self.columns = []


app = StatServer()


@app.on_event("startup")
async def database_connect():
    await db.connect()
    await db.execute(query=mission_stats)
    await db.execute(query=mission_stat_files)


@app.on_event("shutdown")
def database_disconnect():
    db.close()


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/check_db_files")
async def check_db_files():
    await read_stats.insert_gs_files_to_db()
    await read_stats.process_lua_records()
    return 200


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
async def json_data():
    df = await read_stats.get_dataframe()
    return JSONResponse(content=df.to_json(orient="split", index=False))
