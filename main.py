from stats import read_stats
from fastapi import FastAPI
from starlette.responses import HTMLResponse, JSONResponse
from starlette.templating import Jinja2Templates
from starlette.requests import Request
import logging

logging.basicConfig(level=logging.INFO)
templates = Jinja2Templates(directory='templates')


class StatServer(FastAPI):
    def __init__(self, *kwargs, **args):
        FastAPI.__init__(self, "Stat_server")
        self.columns = []


app = StatServer()
# app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/old")
def stats(request: Request):
    df = read_stats.get_dataframe()
    context = {"request": request,
               "data": df.to_html(table_id="stats", index=False)}
    return templates.TemplateResponse("index.html", context)


@app.get("/")
def new_stats(request: Request):
    df = read_stats.get_dataframe()
    context = {"request": request,
               "data": df.to_html(table_id="stats", index=False)}
    return templates.TemplateResponse("index_new.html", context)


@app.get("/weapons")
def weapon_stats(request: Request):
    df = read_stats.get_dataframe(subset="weapons")
    context = {"request": request,
               "data": df.to_html(table_id="stats", index=False)}
    return templates.TemplateResponse("index_new.html", context)


@app.get("/json_data")
def json_data():
    df = read_stats.get_dataframe()
    return JSONResponse(content=df.to_json(orient="split", index=False))
