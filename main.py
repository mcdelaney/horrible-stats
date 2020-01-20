from stats import read_stats
from fastapi import FastAPI
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles


app = FastAPI("Stat-Server")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/healthz")
def healthz():
    return "ok"

@app.get("/")
def stats():
    stats = read_stats.main(max_parse=1000).to_html()
    return HTMLResponse(stats)
