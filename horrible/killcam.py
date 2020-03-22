import pandas as pd
import sqlite3
from typing import cast
from horrible.config import log

conn = sqlite3.connect("horrible/data/dcs.db")

# query = conn.execute(f"""WITH TMP AS (
#                 SELECT killer, target, weapon, kill.pilot,
#                     tar.target_name, weap.weapon_name, time_offset as impact_ts
#                 FROM impact
#                 INNER JOIN (SELECT id AS killer, COALESCE(pilot, name, type) AS pilot FROM object) kill
#                 USING (killer)
#                 INNER JOIN (SELECT id AS target, COALESCE(pilot, name) AS target_name FROM object) tar
#                 USING(target)
#                 INNER JOIN (SELECT id AS weapon, name AS weapon_name FROM object) weap
#                 USING (weapon)
#                 WHERE killer IS NOT NULL and target IS NOT NULL
#                 --AND target == 1158658
#                 --AND TARGET == 190978
#                 --AND killer == 73219 and target == 399106
#                 ORDER BY RANDOM()
#             )

#             SELECT killer, target, weapon, weap_time.weap_fire_time, pilot,
#                 target_name, weapon_name, impact_ts, weap_end_time
#             FROM tmp t
#             INNER JOIN (SELECT id as weapon,
#                         MIN(time_offset) as weap_fire_time,
#                         MAX(time_offset) AS weap_end_time
#                     FROM event
#                     WHERE id IN (SELECT weapon FROM tmp LIMIT 1)
#                     ) weap_time
#             USING (weapon)""")



async def get_kill(kill_id: int, db):

    query = await db.fetch_all(f"""WITH TMP AS (
                SELECT id as impact_id, killer, target, weapon, kill.pilot,
                    tar.target_name, weap.weapon_name, time_offset as impact_ts
                FROM impact
                INNER JOIN (SELECT id AS killer, COALESCE(pilot, name, type) AS pilot FROM object) kill
                USING (killer)
                INNER JOIN (SELECT id AS target, COALESCE(pilot, name) AS target_name FROM object) tar
                USING(target)
                INNER JOIN (SELECT id AS weapon, name AS weapon_name, type as weap_type
                            FROM object) weap
                USING (weapon)
                WHERE killer IS NOT NULL AND
                    target IS NOT NULL AND weapon IS NOT NULL
                    AND weap_type like ('%Missile%')
                    AND impact_dist < 50
            )

            SELECT killer, target, weapon, weap_time.weap_fire_time, pilot,
                target_name, weapon_name, impact_ts, weap_end_time, impact_id
            FROM tmp t
            INNER JOIN (SELECT id as weapon,
                        first_seen as weap_fire_time,
                        last_seen AS weap_end_time
                    FROM object
                    ) weap_time
            USING (weapon)
            ORDER BY random()
            """)

    killer_id, target_id, weapon_id, weap_fire_time, pilot, target_name, weapon_name, \
    impact_ts, weap_end_time, impact_id = list(query[0].values())

    log.info(f"Returing killcam for pilot: {pilot}, weapon: {weapon_name}, "
            f"target: {target_name} Weapon first ts {weap_fire_time}, "
            f"Impact TS: {impact_ts}")
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
    log.info(f'Total points returned: {points.shape[0]}...') # type: ignore

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
            subset = pd.read_sql(f"""SELECT v_coord, alt, u_coord, time_offset
                                    FROM object WHERE id = {id_val}""", conn)
            subset = cast(pd.DataFrame, pd.concat([subset, subset]))
            subset.reset_index(inplace=True)
        if subset.shape[0] <= 1:
            return

        subset.reset_index(inplace=True)
        # for var in ['v_coord', 'u_coord', 'alt']:
        #     subset[var] = subset[var].interpolate( # type: ignore
        #         method='linear', limit=50, limit_direction='both') # type: ignore

        subset = subset[['v_coord', 'alt', 'u_coord', 'time_offset']]
        subset = cast(pd.DataFrame, subset)
        subset.dropna(inplace=True)
        data[name] = subset.to_dict('split')

    log.info(f"Killer: {killer_id} -- Target: {target_id} -- "
            f"Weapon: {weapon_id} -- Min ts: {data['min_ts']}"
            f" Impact id: {impact_id}")
    log.info([len(data['killer']['data']), len(data['target']['data']),
            len(data['weapon']['data'])])
    return data
