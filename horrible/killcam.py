import pandas as pd
import sqlite3
from typing import cast
from horrible.config import log
from datetime import timedelta

IMPACT_QUERY = f"""WITH TMP AS (
        SELECT
            id as impact_id, impact_dist,
            killer, killer_name, killer_type,
            target, target_name, target_type,
            weapon, weapon_name

        FROM impact
        INNER JOIN (SELECT id killer, pilot killer_name, name killer_type
                    FROM object) kill
        USING (killer)
        INNER JOIN (SELECT id target, pilot as target_name, name as target_type
                    FROM object) tar
        USING(target)
        INNER JOIN (SELECT id weapon, name AS weapon_name
                    FROM object
                    WHERE type like ('%Missile%') and NAME IS NOT NULL) weap
        USING (weapon)
        WHERE killer IS NOT NULL AND
            target IS NOT NULL AND weapon IS NOT NULL
            AND impact_dist < 10
    ),
    TMP2 as (
        SELECT start_time as kill_timestamp,
            killer_name, killer_type, killer as killer_id,
            target_name, target_type, target as target_id,
            weapon_name, weapon_type, weapon as weapon_id,
            impact_dist, impact_id,
            weapon_first_time, weapon_last_time
        FROM tmp t
        INNER JOIN (SELECT id as weapon,
                    first_seen as weapon_first_time,
                    last_seen AS weapon_last_time
                FROM object
                ) weap_time
        USING (weapon)
        INNER JOIN (select id as killer, session_id FROM object) sess1
        USING (killer)
        INNER JOIN (select session_id, start_time FROM session) sess2
        USING (session_id)
        LEFT JOIN (SELECT name AS weapon_name, category AS weapon_type
                   FROM weapon_types) weap_type
        USING (weapon_name)
    )
"""

async def get_all_kills(db):
    """Get a table of all kills."""
    query = await db.fetch_all(IMPACT_QUERY + " SELECT * FROM tmp2")
    data = pd.DataFrame.from_records(query, index=None)
    data.impact_dist = data.impact_dist.apply(lambda x: round(x, 2))
    data['weapon_first_time'] = data['weapon_first_time'].apply(lambda x: timedelta(seconds=x)) # type:ignore
    data['kill_timestamp'] = data['kill_timestamp'] + data['weapon_first_time'] # type:ignore
    data['kill_timestamp'] = data['kill_timestamp'].apply(  # type:ignore
        lambda x: str(x.replace(microsecond=0)))  # type:ignore
    data = data[[
        'kill_timestamp', 'killer_name', 'killer_type', 'weapon_name',
        'weapon_type', 'target_name', 'target_type', 'impact_dist', 'impact_id'
    ]]
    return data


async def get_kill(kill_id: int, db):
    try:
        if kill_id == -1:
            filter_clause = " WHERE weapon_type = 'Air-to-Air' ORDER BY random() "
        else:
            filter_clause = f"WHERE impact_id = {kill_id}"

        resp = await db.fetch_one(IMPACT_QUERY + f"SELECT * FROM tmp2 {filter_clause} limit 1")
        resp = dict(resp)

        # TODO Make sure that the entire lifespan of the weapon is captured.
        # Otherwise it will look like the weapon appears some distance from the killer.
        points = await db.fetch_all(
            f"""
            WITH lagged AS (
                SELECT lon, lat, alt, last_seen, u_coord, v_coord,
                    velocity_kts/0.514444 AS velocity_ms, id
                FROM obj_events
                WHERE id in ({resp['weapon_id']}, {resp['target_id']}, {resp['killer_id']})
                    AND  last_seen >= {resp['weapon_first_time']} AND
                    last_seen <= {resp['weapon_last_time']}
                    AND alive = TRUE
                ORDER BY updates
            )
            SELECT
                v_coord, alt, u_coord, last_seen AS time_offset, id
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
            subset = subset[['v_coord', 'alt', 'u_coord', 'time_offset']]
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
