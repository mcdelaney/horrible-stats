import pandas as pd
import sqlite3
from typing import cast
from horrible.config import log
from datetime import timedelta


async def get_all_kills(db):
    """Get a table of all kills."""
    query = await db.fetch_all(f"""WITH TMP AS (
                    SELECT id as impact_id, killer, target, weapon, kill.killer_name,
                        tar.target_name, weap.weapon_name
                    FROM impact
                    INNER JOIN (SELECT id AS killer, COALESCE(pilot, name, type) AS killer_name FROM object) kill
                    USING (killer)
                    INNER JOIN (SELECT id AS target, COALESCE(pilot, name) AS target_name FROM object) tar
                    USING(target)
                    INNER JOIN (SELECT id AS weapon, name AS weapon_name, type as weap_type
                                FROM object) weap
                    USING (weapon)
                    WHERE killer IS NOT NULL AND
                        target IS NOT NULL AND weapon IS NOT NULL AND weapon_name is not nULL
                        AND weap_type like ('%Missile%')
                        AND impact_dist < 50
                )

                SELECT start_time as kill_timestamp,
                    weap_time.weap_fire_time, killer_name,
                    target_name, weapon_name, impact_id, weapon_type
                FROM tmp t
                INNER JOIN (SELECT id as weapon,
                            first_seen as weap_fire_time,
                            last_seen AS weap_end_time
                        FROM object
                        ) weap_time
                USING (weapon)
                INNER JOIN (select id as killer, session_id FROM object) sess1
                USING (killer)
                INNER JOIN (select session_id, start_time FROM session) sess2
                USING (session_id)
                LEFT JOIN (select name as weapon_name, category as weapon_type FROM weapon_types) weap_type
                USING (weapon_name)
                """)

    data = pd.DataFrame.from_records(query, index=None)
    data['weap_fire_time'] = data['weap_fire_time'].apply(lambda x: timedelta(seconds=x)) # type:ignore
    data['kill_timestamp'] = data['kill_timestamp'] + data['weap_fire_time'] # type:ignore
    data['kill_timestamp'] = data['kill_timestamp'].apply(  # type:ignore
        lambda x: str(x.replace(microsecond=0)))  # type:ignore
    data = data[['kill_timestamp', 'killer_name', 'weapon_name', 'target_name',
                 'weapon_type', 'impact_id']]
    return data


async def get_kill(kill_id: int, db):
    try:
        if kill_id == -1:
            filter_clause = " WHERE weapon_type = 'Air-to-Air' ORDER BY random() "
        else:
            filter_clause = f"WHERE impact_id = {kill_id}"

        query = await db.fetch_all(f"""WITH TMP AS (
                    SELECT id as impact_id, killer, target, weapon, kill.pilot,
                        tar.target_name, weap.weapon_name, time_offset as impact_ts, weapon_type
                    FROM impact
                    INNER JOIN (SELECT id AS killer, COALESCE(pilot, name, type) AS pilot FROM object) kill
                    USING (killer)
                    INNER JOIN (SELECT id AS target, COALESCE(pilot, name) AS target_name FROM object) tar
                    USING(target)
                    INNER JOIN (SELECT id AS weapon, name AS weapon_name, type as weap_type
                                FROM object) weap
                    USING (weapon)
                    LEFT JOIN (select name as weapon_name, category as weapon_type FROM weapon_types) weap_type
                    USING (weapon_name)
                    WHERE
                        killer IS NOT NULL AND
                        target IS NOT NULL AND weapon IS NOT NULL
                        AND weap_type like ('%Missile%')
                        AND impact_dist < 5
                )

                SELECT killer, target, weapon, weap_time.weap_fire_time, pilot,
                    target_name, weapon_name, impact_ts, weap_end_time, impact_id
                FROM (SELECT * FROM tmp {filter_clause}) t
                INNER JOIN (SELECT id as weapon,
                            first_seen as weap_fire_time,
                            last_seen AS weap_end_time
                        FROM object
                        ) weap_time
                USING (weapon)

                LIMIT 1
                """)

        killer_id, target_id, weapon_id, weap_fire_time, pilot, target_name, weapon_name, \
        impact_ts, weap_end_time, impact_id = list(query[0].values())

        # TODO Make sure that the entire lifespan of the weapon is captured.
        # Otherwise it will look like the weapon appears some distance from the killer.
        points = await db.fetch_all(
            f"""
            WITH lagged AS (
                SELECT lon, lat, alt, last_seen, u_coord, v_coord,
                    velocity_kts/0.514444 AS velocity_ms, id
                FROM obj_events
                WHERE id in ({weapon_id}, {target_id}, {killer_id})
                    AND  last_seen >= {weap_fire_time} AND
                    last_seen <= {weap_end_time}
                    AND alive = TRUE
                ORDER BY updates
            )
            SELECT
                v_coord, alt, u_coord, last_seen AS time_offset, id
            FROM lagged
            """)
        points = [dict(p) for p in points]
        points = pd.DataFrame.from_records(points, index=None)
        log.info(f'Total points returned: {points.shape[0]}...id: {impact_id}...') # type: ignore

        times = pd.DataFrame({'time_offset': [points.time_offset.min(), # type: ignore
                                            points.time_offset.max()]}) # type: ignore

        data = {
                'weapon_id': weapon_id,
                'min_ts': times['time_offset'].min(), # type: ignore
                'killer_id': killer_id,
                'target_id': target_id,
                'target_name': target_name,
                'weapon_name': weapon_name,
                'pilot_name': pilot,
                'impact_id': impact_id
        }

        for id_val, name in zip([target_id, weapon_id, killer_id],
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

        log.info(f"Killer: {killer_id} -- Target: {target_id} -- "
                f"Weapon: {weapon_id} -- Min ts: {data['min_ts']}"
                f" Impact id: {impact_id}")
        log.info([len(data['killer']['data']), len(data['target']['data']),
                len(data['weapon']['data'])])
    except Exception as err:
        log.error(err)
        raise err
    return data
