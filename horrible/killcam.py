import pandas as pd
from typing import cast, List
from horrible.config import log
from datetime import timedelta


async def get_all_kills(db) -> List:
    """Get a table of all kills."""
    data = []
    query = await db.fetch_all("""SELECT *,
                               (weapon_last_time - weapon_first_time) kill_duration
                               FROM impact_comb""")
    for rec in query:
        tmp = {
            'kill_timestamp': (
                rec['kill_timestamp'] + timedelta(seconds=rec['weapon_first_time'])
                ).replace(microsecond=0),
            'killer_name': rec['killer_name'],
            'killer_type': rec['killer_type'],
            'weapon_name': rec['weapon_name'],
            'weapon_type': rec['weapon_type'],
            'target_name': rec['target_name'],
            'target_type': rec['target_type'],
            'impact_dist': round(rec['impact_dist'], 2),
            'kill_duration': round(rec['kill_duration'], 2),
            'impact_id': rec['impact_id'],
        }
        data.append(tmp)
    return pd.DataFrame.from_records(data, index=None).to_dict('split')


async def get_kill(kill_id: int, db):
    """Return coordinates for a single kill-id."""
    try:
        if kill_id == -1:
            filter_clause = " WHERE weapon_type = 'Air-to-Air' ORDER BY random() "
        else:
            filter_clause = f"WHERE impact_id = {kill_id}"

        resp = await db.fetch_one(f"SELECT * FROM impact_comb {filter_clause} limit 1")
        resp = dict(resp)

        # TODO Make sure that the entire lifespan of the weapon is captured.
        # Otherwise it will look like the weapon appears some distance from the killer.
        points = await db.fetch_all(
            f"""
            WITH lagged AS (
                SELECT lon, lat, alt, last_seen, u_coord, v_coord,
                    velocity_kts/0.514444 AS velocity_ms, yaw, pitch, roll, id
                FROM obj_events
                WHERE id in ({resp['weapon_id']}, {resp['target_id']}, {resp['killer_id']})
                    AND  last_seen >= {resp['weapon_first_time']} AND
                    last_seen <= {resp['weapon_last_time']}
                    --AND alive = TRUE
                ORDER BY updates
            )
            SELECT
                lat, lon, v_coord, alt, u_coord, last_seen AS time_offset, yaw, pitch, roll, id
            FROM lagged
            """)
        points = [dict(p) for p in points]
        points = pd.DataFrame.from_records(points, index=None)
        log.info(f"Total points returned: {points.shape[0]}...id: {resp['impact_id']}...") # type: ignore

        times = pd.DataFrame({'time_offset': [points.time_offset.min(), # type: ignore
                                            points.time_offset.max()]}) # type: ignore

        data = {
            'min_ts': times['time_offset'].min(),  # type: ignore
            'killer_id': resp['killer_id'],
            'killer_name': resp['killer_name'],
            'killer_type': resp['killer_type'],
            'weapon_id': resp['weapon_id'],
            'weapon_name': resp['weapon_name'],
            'target_id': resp['target_id'],
            'target_name': resp['target_name'],
            'target_type': resp['target_type'],
            'impact_id': resp['impact_id']
        }

        for id_val, name in zip([resp['target_id'], resp['weapon_id'], resp['killer_id']],
                                ['target', 'weapon', 'killer']):
            subset = cast(pd.DataFrame, points.query(f"id=={id_val}"))
            if subset.shape[0] <= 1:
                log.error(f"Error on id: {id_val}...No rows")
            if subset.shape[0] <= 1:
                return
            subset.reset_index(inplace=True)
            subset = subset[['v_coord', 'alt', 'u_coord', 'pitch', 'roll', 'yaw', 'time_offset']]
            subset = cast(pd.DataFrame, subset)
            subset.dropna(inplace=True)
            data[name] = subset.to_dict('split')

        log.info(f"Killer: {resp['killer_id']} -- Target: {resp['target_id']} -- "
                f"Weapon: {resp['weapon_id']} -- Min ts: {data['min_ts']}"
                f" Impact id: {resp['impact_id']}")
        log.info([len(data['killer']['data']), len(data['target']['data']),
                len(data['weapon']['data'])])
    except Exception as err:
        log.error(err)
        raise err
    return data
