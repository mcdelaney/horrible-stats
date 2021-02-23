from typing import Dict
from horrible.config import get_logger
from horrible.read_stats import dict_to_js_datatable_friendly_fmt

log = get_logger('killcam')


async def get_all_kills(db) -> Dict:
    """Get a table of all kills."""
    log.info('Querying for all kills...')
    data = await db.fetch_all("""SELECT
            TO_CHAR(kill_timestamp, 'YYYY-MM-DD HH24:MI:SS') as kill_timestamp,
        killer_name, killer_type,
        weapon_name, weapon_type, target_name, target_type,
        impact_dist,
        kill_duration,
        impact_id as id
        FROM impacts_valid
        WHERE weapon_type IS NOT NULL AND
            impact_dist <= 5 AND kill_duration > 1 AND
            kill_duration < 120 AND
            ((killer_name in (SELECT DISTINCT pilot FROM mission_stats)) OR
            (target_name in (SELECT DISTINCT pilot FROM mission_stats)))
        ORDER BY kill_timestamp DESC
    """)
    log.info('Formatting and returning kills...')
    return dict_to_js_datatable_friendly_fmt(data)


async def get_kill(kill_id: int, db):
    """Return coordinates for a single kill-id."""
    if kill_id == -1:

        filter_clause = """
            WHERE
                weapon_type = 'Air-to-Air' AND
                impact_dist < 10 AND kill_duration > 10 AND kill_duration < 120
            ORDER BY random()
        """
    else:
        filter_clause = f"""WHERE impact_id = {kill_id}"""

    log.info(f'Looking up specs for kill: {kill_id}...')
    resp = await db.fetch_one(
        f"SELECT * FROM impacts_valid {filter_clause} limit 1")
    log.info(resp)
    key_dict = {
        k: v
        for k, v in
        zip([resp['target_id'], resp['weapon_id'], resp['killer_id']],
            ['target', 'weapon', 'killer'])
    }

    log.info(
        f"""Getting points from id: {resp['impact_id']} and session: {resp['session_id']}
        with time range: {resp['weapon_first_time']-30} - {resp['weapon_last_time']+10}..."""
    )

    points_query = f"""
        WITH TMP AS (
            SELECT
                id, session_id,
                ARRAY_AGG(ARRAY[v_coord, alt, u_coord] ORDER BY last_seen) coord,
                ARRAY_AGG(ARRAY[roll, pitch, yaw] ORDER BY last_seen) rot,
                ARRAY_AGG(heading ORDER BY last_seen) heading,
                ARRAY_AGG(last_seen ORDER BY last_seen) time_step
            FROM (
                SELECT *
                FROM obj_events
                WHERE
                    session_id = {resp['session_id']} AND
            		type in ('Weapon+Missile', 'Air+FixedWing') AND
                    last_seen >= {resp['weapon_first_time']-30} AND
                    last_seen <= {resp['weapon_last_time']+10}
                ORDER BY updates
                ) upd
            GROUP BY id, session_id
            )
        SELECT *
        FROM tmp t
        INNER JOIN (SELECT id, name, name as type, color, session_id, type as cat
                    FROM object) obj
        USING (id, session_id)
        """

    points = await db.fetch_all(points_query)
    data = {
        'min_ts': None,
        'max_ts': None,
        'impact_id': resp['impact_id'],
        'impact_dist': f"{round(resp['impact_dist'],2)}m",
        'killer': None,
        'target': None,
        'weapon': None,
        'other': []
    }

    for pt in points:
        rec = dict(pt)

        if not data['min_ts'] or rec['time_step'][0] < data['min_ts']:
            data['min_ts'] = rec['time_step'][0]

        if not data['max_ts'] or rec['time_step'][-1] > data['max_ts']:
            data['max_ts'] = rec['time_step'][-1]

        try:
            group = key_dict[rec['id']]
            rec['type'] = resp[
                group + "_type"] if group != 'weapon' else resp['weapon_name']
            rec['name'] = resp[group + "_name"]
            data[group] = rec
        except KeyError:
            data['other'].append(rec)

    # min_killer = data['killer']['coord'][0]
    # for obj in ['killer', 'target', 'weapon']:
    #     for i in range(len(data[obj]['coord'])):
    #         data[obj]['coord'][i][0] -= min_killer[0]
    #         data[obj]['coord'][i][1] -= min_killer[1]
    #         data[obj]['coord'][i][2] -= min_killer[2]
    #     log.info(data[obj]['coord'][-1])

    # for i in range(len(data['other']['coord'])):
    #     data['other']['coord'][i][0] -= min_killer[0]
    #     data['other']['coord'][i][1] -= min_killer[1]
    #     data['other']['coord'][i][2] -= min_killer[2]

    # log.info(min_killer)

    log.info(f"Killer: {data['killer']['id']}")
    log.info(f"Target: {data['target']['id']} -- ")
    log.info(f"Weapon: {data['weapon']['id']} -- Min ts: {data['min_ts']}")
    log.info(f" Impact id: {data['impact_id']} ")
    log.info(f" Total other: {len(data['other'])}")

    return data
