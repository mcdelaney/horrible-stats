import pandas as pd
from typing import cast, Dict
from horrible.config import get_logger
from horrible.read_stats import dict_to_js_datatable_friendly_fmt


log = get_logger('killcam')


async def get_all_kills(db) -> Dict:
    """Get a table of all kills."""
    log.info('Querying for all kills...')
    data = await db.fetch_all(
        """SELECT
            TO_CHAR(kill_timestamp, 'YYYY-MM-DD HH24:MI:SS') as kill_timestamp,
            killer_name, killer_type,
            weapon_name, weapon_type, target_name, target_type,
            impact_dist,
            kill_duration,
            impact_id as id
            FROM impact_comb
            WHERE weapon_type IS NOT NULL AND
                impact_dist <= 5 AND kill_duration > 1 AND
                kill_duration < 120
            ORDER BY kill_timestamp DESC
            LIMIT 2000""")
    log.info('Formatting and returning kills...')
    return dict_to_js_datatable_friendly_fmt(data)


async def get_kill(kill_id: int, db):
    """Return coordinates for a single kill-id."""
    if kill_id == -1:
        filter_clause = """
            WHERE weapon_type = 'Air-to-Air' AND
            impact_dist < 10 AND kill_duration > 10 AND kill_duration < 120
            ORDER BY random()
        """
    else:
        filter_clause = f"""WHERE impact_id = {kill_id}"""

    log.info(f'Looking up specs for kill: {kill_id}...')
    resp = await db.fetch_one(f"SELECT * FROM impact_comb {filter_clause} limit 1")
    key_dict = {k: v for k, v in zip([resp['target_id'], resp['weapon_id'], resp['killer_id']],
                                        ['target', 'weapon', 'killer'])}

    log.info(f"Collecting kill points from id: {resp['impact_id']} and session: {resp['session_id']}...")
    points = await db.fetch_all(
        f"""
        SELECT
            id, color, v_coord, alt, u_coord, roll, pitch, yaw, heading, last_seen as time_step
        FROM obj_events
        WHERE
            session_id = {resp['session_id']} AND
            last_seen >= {resp['weapon_first_time']-30} AND
            last_seen <= {resp['weapon_last_time']}
        ORDER BY updates
        """)

    log.info(f"Formatting {len(points)} points....")

    data = {
        'min_ts': points[0]['time_step'],
        'max_ts': points[-1]['time_step'],
        'impact_id': resp['impact_id'],
        'impact_dist': f"{round(resp['impact_dist'],2)}m",
        'killer': None,
        'target': None,
        'weapon': None,
        'other': []
    }

    for pt in points:
        rec = dict(pt)
        if rec['time_step'] < data['min_ts']:
            data['min_ts'] = rec['time_step']

        if rec['time_step'] > data['max_ts']:
            data['max_ts'] = rec['time_step']

        try:
            group = key_dict[rec['id']]
            rec['type'] = resp[group + "_type"] if group != 'weapon' else resp['weapon_name']
            rec['name'] = resp[group + "_name"]
            rec['cat'] = 'plane' if group != 'weapon' else 'weapon'
        except KeyError:
            group = "other"

        rec['coord'] = [rec.pop('v_coord'), rec.pop('alt'), rec.pop('u_coord')]
        rec['rot'] = [rec.pop('roll'), rec.pop('pitch'), rec.pop('yaw')]

        if group == 'other':
            data['other'].append(rec)
        else:
            if data[group] == None:
                for key in ['coord', 'rot', 'time_step', 'heading']:
                    rec[key] = [rec[key]]
                data[group] = rec
            else:
                for key in ['coord', 'rot', 'time_step', 'heading']:
                    data[group][key].append(rec[key])

    log.info(f"Killer: {data['killer']['id']} -- Target: {data['target']['id']} -- "
             f"Weapon: {data['weapon']['id']} -- Min ts: {data['min_ts']}"
             f" Impact id: {data['impact_id']} "
             f" Total other: {len(data['other'])}")
    return data
