from stats import read_stats
from fastapi import FastAPI
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.requests import Request

app = FastAPI("Stat-Server")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory='templates')


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def stats(request: Request):
    df = read_stats.main(max_parse=1000)
    context = {"request": request,
               "data": df.to_html(table_id="stats", index=False)}
    return templates.TemplateResponse("index.html", context)


@app.get("/basic")
def stats_basic():
    stats = read_stats.main(max_parse=1000).to_html(table_id="stats",
                                                    index=False)
    return HTMLResponse(stats)


@app.get("/json_data")
def json_data():
    stats = read_stats.main(max_parse=1000).to_json(orient="split",
                                                    index=False)
    return stats
