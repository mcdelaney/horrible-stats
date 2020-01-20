from stats import read_stats
from fastapi import FastAPI
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles, FileResponse
from starlette.templating import Jinja2Templates
from starlette.requests import Request

app = FastAPI("Stat-Server")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory='templates')



def get_dataframe():
    df = read_stats.main(max_parse=1000)
    df.drop(labels=["id"], axis=1, inplace=True)
    return df


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/ajax")
def ajax(request: Request):
    return FileResponse(path="static/ajax.html")


@app.get("/")
def stats(request: Request):
    df = get_dataframe()
    context = {"request": request,
               "data": df.to_html(table_id="stats", index=False)}
    return templates.TemplateResponse("index.html", context)


@app.get("/basic")
def stats_basic():
    df = get_dataframe()
    df.to_html(table_id="stats", index=False)
    return HTMLResponse(stats)


@app.get("/json_data")
def json_data():
    stats = read_stats.main(max_parse=1000).to_json(orient="split",
                                                    index=False)
    return stats
