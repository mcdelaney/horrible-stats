import logging

from fastapi import FastAPI
from starlette.responses import JSONResponse, RedirectResponse
from starlette.templating import Jinja2Templates
from starlette.requests import Request

from stats import read_stats
from stats.database import db


logging.basicConfig(level=logging.INFO)
templates = Jinja2Templates(directory='templates')


class StatServer(FastAPI):
    def __init__(self, *kwargs, **args):
        FastAPI.__init__(self, "Stat_server")
        self.columns = []


app = StatServer()


@app.on_event("startup")
async def database_connect():
    await db.connect()


@app.on_event("shutdown")
def database_disconnect():
    db.close()


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/check_db_files")
async def check_db_files(request: Request):
    await read_stats.insert_gs_files_to_db()
    await read_stats.process_lua_records()
    response = RedirectResponse(url='/')
    return response


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
