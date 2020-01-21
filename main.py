from stats import read_stats
from fastapi import FastAPI
from starlette.responses import HTMLResponse, JSONResponse
from starlette.staticfiles import StaticFiles, FileResponse
from starlette.templating import Jinja2Templates
from starlette.requests import Request
import logging

logging.basicConfig(level=logging.INFO)
templates = Jinja2Templates(directory='templates')


class StatServer(FastAPI):
    def __init__(self, *kwargs, **args):
        FastAPI.__init__(self, "Stat_server")
        self.columns = None
        self.data = None

    def get_data(self):
        if not self.data:
            df = read_stats.main(max_parse=1000)
            df.drop(labels=["id"], axis=1, inplace=True)
            self.data = df
            self.columns = list(df.columns)
        return self.data

app = StatServer()



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
               "data": app.get_data().to_html(table_id="stats", index=False)}
    return templates.TemplateResponse("index.html", context)


@app.get("/basic")
def stats_basic():
    stats = app.get_data().to_html(table_id="stats", index=False)
    return HTMLResponse(stats)


@app.get("/json_data")
def json_data():
    return JSONResponse(content=app.get_data().to_json(orient="split", index=False))
