import pandas as pd
from typing import cast, Dict
from horrible.config import get_logger
from datetime import timedelta
from horrible.read_stats import dict_to_js_datatable_friendly_fmt


log = get_logger('killcam')


async def get_all_kills(db) -> Dict:
    """Get a table of all kills."""
    log.info('Querying for all kills...')
    data = await db.fetch_all(
        """SELECT
            DATE_TRUNC('SECOND',
                (kill_timestamp +
                    weapon_first_time*interval '1 second')) kill_timestamp,
            killer_name, killer_type,
            weapon_name, weapon_type, target_name, target_type,
            round(cast(impact_dist as numeric), 2) impact_dist,
            ROUND(cast(weapon_last_time - weapon_first_time as numeric), 2) kill_duration,
            impact_id
            FROM impact_comb
            WHERE weapon_type IS NOT NULL AND
                impact_dist <= 5 and cast(impact_dist as numeric) > 2
            ORDER BY kill_timestamp DESC""")
    log.info('Formatting and returning kills...')
    return dict_to_js_datatable_friendly_fmt(data)


async def get_kill(kill_id: int, db):
    """Return coordinates for a single kill-id."""
    try:
        if kill_id == -1:
            filter_clause = " WHERE weapon_type = 'Air-to-Air' ORDER BY random() "
        else:
            filter_clause = f"WHERE impact_id = {kill_id}"
        log.info(f'Looking up specs for kill: {kill_id}...')
        resp = await db.fetch_one(f"SELECT * FROM impact_comb {filter_clause} limit 1")
        resp = dict(resp)

        # TODO Make sure that the entire lifespan of the weapon is captured.
        # Otherwise it will look like the weapon appears some distance from the killer.
        log.info("Collecting kill points...")
        points = await db.fetch_all(
            f"""
            SELECT lon, lat, alt, last_seen as time_offset,
                u_coord, v_coord, yaw, pitch, roll, id, heading
            FROM obj_events
            WHERE id in ({resp['weapon_id']}, {resp['target_id']}, {resp['killer_id']})
                AND  last_seen >= {resp['weapon_first_time']} AND
                last_seen <= {resp['weapon_last_time']}
                --AND alive = TRUE
            ORDER BY updates
            """)
        log.info('Formatting data....')
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
            subset = subset[['v_coord', 'alt', 'u_coord', 'roll', 'pitch', 'yaw',
                             'heading', 'time_offset']]
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
