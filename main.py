import logging
from pathlib import Path
import urllib.parse
from typing import cast
import sqlite3

from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
import pandas as pd
from starlette.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
from starlette.requests import Request

from horrible.database import db, weapon_types, stat_files, frametime_files, event_files
from horrible import read_stats


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
log.setLevel(level=logging.INFO)
consoleHandler = logging.StreamHandler()
log.addHandler(consoleHandler)

conn = sqlite3.connect("horrible/data/dcs.db")
templates = Jinja2Templates(directory='horrible/templates')
app = FastAPI(title="Stat-Server")
app.mount("/main",
          StaticFiles(directory="horrible/static", html=True),
          name="static")


@app.on_event("startup")
async def database_connect():
    try:
        await db.connect()
        tasks = BackgroundTasks()
        tasks.add_task(read_stats.update_all_logs_and_stats)
    except Exception as err:
        log.error(f"Could not conect to database at {db.url}!")
        raise err


@app.on_event("shutdown")
async def database_disconnect():
    await db.disconnect()


@app.get("/healthz")
def healthz():
    """Health-check endpoint.  Should return 200."""
    return "ok"


@app.get("/check_db_files")
async def check_db_files(request: Request):
    """Trigger db update."""
    await read_stats.update_all_logs_and_stats(db)
    return RedirectResponse('/')


@app.get("/resync_file/")
async def resync_file(request: Request, file_name: str):
    """Delete a previously processed file from the database, triggering a re-sync."""
    stat_file_name = Path(urllib.parse.unquote(file_name))
    if 'mission-stats' in file_name:
        log.info(f"Attempting to resync stats-file: {stat_file_name}...")
        log.info(f"Deleting filename: {stat_file_name} from database...")
        async with db.transaction():
            await db.execute(f"""DELETE FROM mission_stats
                WHERE file_name = '{stat_file_name}'""")
            await db.execute(f"""DELETE FROM mission_stat_files
                WHERE file_name = '{stat_file_name}'""")

            if stat_file_name.exists():
                stat_file_name.unlink()
            else:
                log.warning("Local cached copy of file not found!")

        await read_stats.update_all_logs_and_stats(db)
    return "ok"


@app.get("/stat_logs")
async def get_stat_logs(request: Request):
    """Get a json dictionary of mission-stat file status data."""
    tasks = BackgroundTasks()
    tasks.add_task(read_stats.update_all_logs_and_stats)
    try:
        data_recs = await db.fetch_all(query=stat_files.select())
        data = pd.DataFrame.from_records(data_recs, index=None)
        # Convert datetimes into strings because json cant serialize them otherwise.
        data[['processed_at', 'session_start_time'
              ]] = data[['processed_at',
                         'session_start_time']].astype(str)  # type: ignore
        # Make sure columns are correctly ordered.
        # This table will render incorrectly if we dont... I don't know why.
        data = data[[
            "file_name", "session_start_time", "processed", "processed_at",
            "errors"
        ]]
        return JSONResponse(content=data.to_dict('split'))  # type: ignore
    except Exception as e:
        log.error(e)
        return JSONResponse(content={})


@app.get("/event_logs")
async def get_event_logs(request: Request):
    """Get a json dictionary of mission-event file status data."""
    tasks = BackgroundTasks()
    tasks.add_task(read_stats.update_all_logs_and_stats)
    try:
        data_recs = await db.fetch_all(query=event_files.select())
        data = pd.DataFrame.from_records(data_recs, index=None)
        # Convert datetimes into strings because json cant serialize them otherwise.
        data[['processed_at', 'session_start_time'
              ]] = data[['processed_at',
                         'session_start_time']].astype(str)  # type: ignore
        # Make sure columns are correctly ordered.
        # This table will render incorrectly if we dont... I don't know why.
        data = data[[
            "file_name", "session_start_time", "processed", "processed_at",
            "errors"
        ]]
        return JSONResponse(content=data.to_dict('split'))  # type: ignore
    except Exception as e:
        log.error(e)
        return JSONResponse(content={})


@app.get("/frametime_logs")
async def get_frametime_logs(request: Request):
    """Get a json dictionary of mission-stat file status data."""
    data_recs = await db.fetch_all(frametime_files.select())
    data = pd.DataFrame.from_records(data_recs, index=None)
    # Convert datetimes into strings because json cant serialize them otherwise.
    data[['processed_at',
          'session_start_time']] = data[['processed_at', 'session_start_time'
                                         ]].astype(str)  # type: ignore
    # Make sure columns are correctly ordered.
    # This table will render incorrectly if we dont... I don't know why.
    data = data[[
        "file_name", "session_start_time", "processed", "processed_at",
        "errors"
    ]]
    return JSONResponse(content=data.to_dict('split'))  # type: ignore


# @app.get("/frametime_charts")
# async def get_frametime_charts(request: Request, pctile: int = 50):
#     """Get a dataframe of frametime records."""
#     files = await db.fetch_one(frametime_files.select().order_by(
#         sa.desc(sa.text("session_start_time"))))
#     log.info("Looking up most recent log file...")
#     data = read_stats.read_frametime(filename=files['file_name'],
#                                      pctile=pctile)
#     return JSONResponse(content=data)


@app.get("/weapon_db")
async def get_weapon_db_logs(request: Request):
    """Get a json dictionary of categorized weapons used for groupings."""
    data = await db.fetch_all(query=weapon_types.select())
    content = {"data": [], "columns": list(data[0].keys())}
    for row in data:
        content['data'].append(list(row.values()))
    return JSONResponse(content=content)


@app.get("/overall")
async def get_overall_stats(request: Request):
    """Get a json dictionary of grouped statistics as key-value pairs."""
    data = await read_stats.calculate_overall_stats(grouping_cols=['pilot'])
    data = data.to_dict('split')
    return JSONResponse(content=data)


@app.get("/session_performance")
async def get_session_perf_stats(request: Request):
    """Get a json dictionary of grouped statistics as key-value pairs."""
    data = await read_stats.calculate_overall_stats(
        grouping_cols=['session_date', 'pilot'])
    data.sort_values(by=['session_date', 'A/A Kills'], ascending=False, inplace=True)
    data = data.to_dict('split')
    return JSONResponse(content=data)


@app.get("/")
async def serve_homepage(request: Request):
    """Serve the index.html template."""
    with open("horrible/static/index.html", mode='r') as fp_:
        page = fp_.read()
    return HTMLResponse(page)


@app.get("/weapons")
async def weapon_stats(request: Request):
    """Return a rendered template with a table displaying per-weapon stats."""
    data = await read_stats.get_dataframe(subset=["weapons"])
    return JSONResponse(content=data.to_dict('split'))


@app.get("/kills")
async def kill_detail(request: Request):
    """Return a rendered template showing kill/loss statistics."""
    data = await read_stats.get_dataframe(subset=["kills"])
    return JSONResponse(content=data.to_dict("split"))


@app.get("/losses")
async def loss_detail(request: Request):
    """Return a rendered template showing kill/loss statistics."""
    data = await read_stats.get_dataframe(subset=["losses"])
    return JSONResponse(content=data.to_dict("split"))


@app.get("/tacview")
async def tacview_detail(request: Request):
    """Return tacview download links."""
    data = pd.DataFrame()
    return JSONResponse(content=data.to_dict("split"))


@app.get("/events")
async def event_detail(request: Request):
    """Return SlMod event records."""
    data = await read_stats.read_events()
    return JSONResponse(content=data.to_dict("split"))


@app.get("/raw_cats/")
async def raw_cats(request: Request, pilot: str = None):
    """Return a rendered template showing kill/loss statistics."""
    data = await read_stats.collect_recs_kv()

    if pilot:
        data = cast(pd.DataFrame,
                    data.query(f"pilot == '{urllib.parse.unquote(pilot)}'"))
        data.reset_index(drop=True, inplace=True)

    data = data.groupby(
        ['session_date', 'equipment', 'stat_group', 'key_orig', 'category', 'metric'],
        as_index=False).sum()
    data.sort_values(by=['session_date'], ascending=False, inplace=True)
    return HTMLResponse(content=data.to_html())


@app.get("/killcam")
async def serve_killcam(request: Request):
    """Serve the index.html template."""
    with open("horrible/static/killcam.html", mode='r') as fp_:
        page = fp_.read()
    return HTMLResponse(page)


@app.get("/kill_coords")
async def get_kill_coords(request: Request, pilot: str, sec_offset: int):
    """Get Points Preceeding kill."""
    pilot = urllib.parse.unquote(pilot)

    query = conn.execute(
        f"""WITH TMP AS (
                SELECT killer, target, weapon, kill.pilot,
                    tar.target_name, weap.weapon_name, time_offset as impact_ts
                FROM impact
                INNER JOIN (SELECT id AS killer, COALESCE(pilot, name, type) AS pilot FROM object) kill
                USING (killer)
                INNER JOIN (SELECT id AS target, COALESCE(pilot, name) AS target_name FROM object) tar
                USING(target)
                INNER JOIN (SELECT id AS weapon, name AS weapon_name FROM object) weap
                USING (weapon)
                WHERE killer IS NOT NULL and target IS NOT NULL
                --AND target == 1158658
                --AND TARGET == 190978
                --AND killer == 73219 and target == 399106
                ORDER BY RANDOM()
            )

            SELECT killer, target, weapon, weap_time.weap_fire_time, pilot,
                target_name, weapon_name, impact_ts, weap_end_time
            FROM tmp t
            INNER JOIN (SELECT id as weapon,
                        MIN(time_offset) as weap_fire_time,
                        MAX(time_offset) AS weap_end_time
                    FROM event
                    WHERE id IN (SELECT weapon FROM tmp LIMIT 1)
                    ) weap_time
            USING (weapon)""")

    killer_id, target_id, weapon_id, weap_fire_time, pilot, target_name, weapon_name, \
     impact_ts, weap_end_time = query.fetchone()
    # val = query.fetchone()
    # log.info(val)

    log.info(f"Returing killcam for pilot: {pilot}, weapon: {weapon_name}, "
             f"target: {target_name} Weapon first ts {weap_fire_time}, "
             f"Impact TS: {impact_ts}")
    # TODO Make sure that the entire lifespan of the weapon is captured.
    # Otherwise it will look like the weapon appears some distance from the killer.
    points = pd.read_sql(
        f"""
        WITH lagged AS (
            SELECT lon, lat, alt, time_offset, u_coord, v_coord,
                velocity_kts/0.514444 AS velocity_ms, id
            FROM obj_events
            WHERE id in ({weapon_id}, {target_id}, {killer_id})
                AND  time_offset >= {weap_fire_time} AND
                time_offset <= {weap_end_time}
                AND alive = 1
            ORDER BY updates
        )
        SELECT
            v_coord, alt, u_coord, time_offset, id
        FROM lagged
        """, conn)

    log.info(f'Total points returned: {points.shape[0]}...')
    points = cast(pd.DataFrame, points)

    times = pd.DataFrame({'time_offset': [points.time_offset.min(),
                                          points.time_offset.max()]})

    data = {
            'weapon_id': weapon_id,
            'min_ts': times['time_offset'].min(),
            'killer_id': killer_id,
            'target_id': target_id,
            'target_name': target_name,
            'weapon_name': weapon_name,
            'pilot_name': pilot,
    }

    for id_val, name in zip([target_id, weapon_id, killer_id],
                            ['target', 'weapon', 'killer']):
        subset = cast(pd.DataFrame, points.query(f"id=={id_val}"))
        if subset.shape[0] <= 1:
            subset = pd.read_sql(f"""SELECT v_coord, alt, u_coord, time_offset
                                     FROM object WHERE id = {id_val}""", conn)
            subset = cast(pd.DataFrame, pd.concat([subset, subset]))
            subset.reset_index(inplace=True)
        if subset.shape[0] <= 1:
            return JSONResponse(status_code=500)

        subset.reset_index(inplace=True)
        for var in ['v_coord', 'u_coord', 'alt']:
            subset[var] = subset[var].interpolate(
                method='linear', limit=50, limit_direction='both')

        subset = subset[['v_coord', 'alt', 'u_coord', 'time_offset']]
        subset = cast(pd.DataFrame, subset)
        subset.dropna(inplace=True)
        data[name] = subset.to_dict('split')

    log.info(f"Killer: {killer_id} -- Target: {target_id} -- "
             f"Weapon: {weapon_id} -- Min ts: {data['min_ts']}")
    log.info([len(data['killer']['data']), len(data['target']['data']),
              len(data['weapon']['data'])])
    return JSONResponse(content=data)
