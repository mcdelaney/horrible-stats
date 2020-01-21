from stats import read_stats
from fastapi import FastAPI
from starlette.responses import HTMLResponse, JSONResponse
from starlette.staticfiles import StaticFiles, FileResponse
from starlette.templating import Jinja2Templates
from starlette.requests import Request
import logging

logging.basicConfig(level=logging.INFO)


class StatServer(FastAPI):
    def __init__(self, *kwargs, **args):
        FastAPI.__init__(self, "Stat_server")
        self.columns = []

app = StatServer()

# app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory='templates')

# app.columns = list(read_stats.get_dataframe().columns)
logging.info(f"Columns: {app.columns}")

@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/ajax")
def ajax(request: Request):
    context = {'request': request, "columns": app.columns}
    return templates.TemplateResponse("ajax.html", context)


@app.get("/")
def stats(request: Request):
    df = read_stats.get_dataframe()
    app.columns = list(df.columns)
    context = {"request": request,
               "data": df.to_html(table_id="stats", index=False)}
    return templates.TemplateResponse("index.html", context)

@app.get("/new")
def new_stats(request: Request):
    df = read_stats.get_dataframe()
    app.columns = list(df.columns)
    context = {"request": request,
               "data": df.to_html(table_id="stats", index=False)}
    return templates.TemplateResponse("index_new.html", context)


@app.get("/basic")
def stats_basic():
    df = read_stats.get_dataframe()
    app.columns = list(df.columns)

    df.to_html(table_id="stats", index=False)
    return HTMLResponse(stats)


@app.get("/json_data")
def json_data():
    df = read_stats.get_dataframe()
    app.columns = list(df.columns)
    return JSONResponse(content=df.to_json(orient="split", index=False))
