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
def stats():
    stats = read_stats.main(max_parse=1000).to_html(table_id="stats")
    return HTMLResponse(stats)


@app.get("/fancy")
def fancy(request: Request):
    df = read_stats.main(max_parse=1000)
    context = {"request": request,
               "data": main.to_html(table_id="stats")}
    return templates.TemplateResponse("index.html", context)
