from stats import read_stats
from fastapi import FastAPI
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

templates = Jinja2Templates(directory='templates')
app = FastAPI("Stat-Server")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/templates", Jinja2Templatestemplates = Jinja2Templates(directory='templates'))



@app.get("/healthz")
def healthz():
    return "ok"

@app.get("/")
def stats():
    stats = read_stats.main(max_parse=1000).to_html(table_id="stats")
    return HTMLResponse(stats)


@app.get("/fancy")
def fancy():
    context = {"data": read_stats.main(max_parse=1000).to_html(table_id="stats")}
    return templates.TemplateResponse("index.html", context)
