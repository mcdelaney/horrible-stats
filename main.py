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
        self.columns = None
        self.data = None
        self.get_data()

    def get_data(self):
        df = read_stats.main(max_parse=1000)
        df.drop(labels=["id"], axis=1, inplace=True)
        self.data = df
        self.columns = list(df.columns)


app = StatServer()

# app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory='templates')

app.columns = list(read_stats.get_dataframe().columns)
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
    context = {"request": request,
               "data": app.data.to_html(table_id="stats", index=False)}
    return templates.TemplateResponse("index.html", context)


@app.get("/basic")
def stats_basic():
    app.data.to_html(table_id="stats", index=False)
    return HTMLResponse(stats)


@app.get("/json_data")
def json_data():
    return JSONResponse(content=app.data.to_json(orient="split", index=False))
