import collections
import json
import logging
from pathlib import Path
import re
import threading
import traceback
from typing import Dict, List, Optional, Any

import asyncpg
import numpy as np
from lupa import LuaRuntime
import pandas as pd
import sqlalchemy as sa

from horrible.database import (db, frametime_files, mission_stats, stat_files,
                               weapon_types)
from horrible.gcs import get_gcs_bucket, sync_gs_files_with_db

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
log.setLevel(level=logging.INFO)
consoleHandler = logging.StreamHandler()
log.addHandler(consoleHandler)


async def update_all_logs_and_stats(db) -> None:
    """Sync weapon db, gs stats files, and process any new records."""
    log.info("Syncing log files and updating stats...")
    await sync_weapons()
    await sync_gs_files_with_db('mission-stats/', stat_files, db)
    await sync_gs_files_with_db('frametime/', frametime_files, db)
    await process_lua_records()
    log.info("All log and stats files updated...")


def pctile(n):
    def percentile_(x):
        return np.percentile(x, n)

    percentile_.__name__ = 'percentile_%s' % n
    return percentile_


# def read_frametime(filename: str, pctile: int = 50) -> Dict:
#     """Given a google-storage blob, return a dataframe with frametime stats."""
#     Path("frametimes").mkdir(parents=True, exist_ok=True)
#     local_file = Path('frametimes').joinpath(Path(filename).name)
#     if not local_file.exists():
#         bucket = get_gcs_bucket()
#         log.info(f"Downloading file: {filename} to location: {local_file}...")
#         log.info(f"{str(filename)==str(local_file)}")
#         blob = bucket.get_blob(str(filename))
#         with local_file.open('wb') as fp_:
#             blob.download_to_file(fp_)
#         log.info("File downloaded successfully...")
#     else:
#         log.info("File exists in local cache...")

#     with local_file.open('rb') as fp_:
#         raw_text = fp_.read().decode().split()
#     rec = np.array(raw_text, dtype=np.float)
#     fps = float(1) / (rec[1:, ] - rec[:-1])
#     fps = fps.astype(pd.Int64Dtype)

#     tstamp_fps = np.stack([fps, rec[1:, ]], axis=1)
#     df = pd.DataFrame(tstamp_fps, columns=['fps', 'tstamp'])

#     df['tstamp'] = pd.to_datetime(df['tstamp'], unit='s')
#     dfgroup = df.groupby(pd.Grouper(key='tstamp', freq='1s'))

#     max = 5000
#     # nrows = len(dfgroup.groups)
#     nrows = max
#     out = {
#         'labels': [None] * nrows,
#         'data': [None] * nrows,
#         'points': [None] * nrows,
#         'name': f"FPS: {pctile} Percentile"
#     }
#     i = 0
#     max_it = 50
#     for group, data in dfgroup:
#         ptile = int(np.percentile(data.fps, pctile))
#         tstamp = group.strftime("%Y-%M-%d %H:%m:%S")
#         out['labels'][i] = tstamp
#         out['data'][i] = {'x': i, 'y': ptile}
#         out['points'][i] = ptile
#         i += 1
#         if i >= max_it:
#             break
#     return out


async def sync_weapons() -> None:
    """Sync contents of data/weapons-db.csv with database."""
    weapons = pd.read_csv("horrible/data/weapon-db.csv").to_dict('records')

    current_weapons = await db.fetch_all(query=weapon_types.select())
    current_weapons = [weapon['name'] for weapon in current_weapons]

    for record in weapons:
        if record['name'] in current_weapons:
            continue
        query = weapon_types.insert()
        await db.execute(query, values=record)
        log.info(f"New weapon added to database: {record['name']}...")


def lua_tbl_to_py(lua_tbl: Dict) -> Dict:
    """Coerce lua table to python object."""
    flatten_these = ['names', 'friendlyKills', 'friendlyHits']
    out = {}
    try:
        for k, v in lua_tbl.items():
            match_key = [
                flat_k for flat_k in flatten_these if flat_k == k.decode()
            ]
            if match_key:
                try:
                    out[match_key[0]] = ', '.join(
                        [val.decode() for val in dict(v).values()])
                except Exception:
                    pass
                continue

            if v and isinstance(v, (int, bytes, float, str)):
                out[k.decode()] = v  # type:ignore
            else:
                out[k.decode()] = lua_tbl_to_py(v)  # type:ignore

        # rename names to pilot.
        if "names" in out.keys():
            out['pilot'] = out.pop('names')

    except AttributeError:
        return lua_tbl
    return out


def result_to_flat_dict(record: collections.MutableMapping,
                        parent: str = '',
                        sep: str = '__') -> Dict:
    items: List = []
    for k, v in record.items():
        if not parent or k.startswith('weapon'):
            new_key = k
        else:
            new_key = f"{parent}{sep}{k}"

        if isinstance(v, collections.MutableMapping):
            items.extend(result_to_flat_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def read_lua_table(stat: Path) -> Optional[List]:
    """Read a single json file, returning a dict."""
    with stat.open('r') as fp_:
        file_contents = " ".join([f for f in fp_.readlines()])
    if file_contents == "placeholder":
        return None

    lua_code = f"\n function() \r\n local {file_contents} return misStats end"

    thread_count = 1
    lua_funcs = [
        LuaRuntime(encoding=None).eval(lua_code) for _ in range(thread_count)
    ]

    results: List[Dict] = [{}]

    def read_tab_func(i, lua_func):
        results[i] = lua_func()

    threads = [
        threading.Thread(target=read_tab_func, args=(i, lua_func))
        for i, lua_func in enumerate(lua_funcs)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    result = lua_tbl_to_py(results[0])
    results_out = []
    for res in result.values():
        tmp = result_to_flat_dict(res)
        entry = {
            'file_name': str(stat),
            'pilot': tmp.pop('pilot'),
            'pilot_id': tmp.pop('id'),
            'record': tmp
        }
        results_out.append(entry)
    return results_out


async def process_lua_records() -> None:
    """Parse a directory of Sl-Mod stats files, returning a pandas dataframe."""
    Path("mission-stats").mkdir(parents=True, exist_ok=True)
    bucket = get_gcs_bucket()
    stats_files = await db.fetch_all(
        stat_files.select(sa.text("processed=FALSE")))
    for stat in stats_files:
        try:
            log.info(f"Handing {stat['file_name']}")
            if stat['file_name'] == "mission-stats/":
                continue
            local_path = Path(f"{stat['file_name']}")
            if local_path.exists():
                log.info("Cached file found...skipping download...")
            else:
                log.info(f"Downloading {stat['file_name']} to {local_path}...")
                try:
                    blob = bucket.get_blob(stat['file_name'])
                    blob.download_to_filename(local_path)
                except Exception as e:
                    log.error(f"Error downloading file! {e}")
                    raise ValueError("File could not be downloaded")

            stat_parsed = read_lua_table(local_path)
            log.info("Dumping record to database...")
            if stat_parsed:
                insert = mission_stats.insert()
                await db.execute_many(insert, stat_parsed)

            log.info("Marking record as processed...")
            await db.execute(f"""UPDATE mission_stat_files
                             SET processed = TRUE,
                             processed_at = date_trunc('second', CURRENT_TIMESTAMP)
                                WHERE file_name = '{stat['file_name']}'
                                """)
            log.info("Record processing complete...")

        except Exception as err:
            log.error(f"Error handling file: \n\t{stat['file_name']}\n\t{err}")
            traceback.print_tb(err.__traceback__)
            await db.execute(f"""UPDATE mission_stat_files
                             SET errors = (
                                SELECT errors+1 as err
                                FROM mission_stat_files
                                WHERE file_name = '{stat['file_name']}'
                             ),
                             processed_at = CURRENT_TIMESTAMP,
                             error_msg = '{str(err)}'
                             WHERE file_name = '{stat['file_name']}'
                                """)


def format_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Format a dataframe for display in HTML."""
    not_ints = ['kills__A/A Kill Ratio']
    for c in df.columns:
        if "times__" in c:
            df[c] = df[c].apply(lambda x: int(round(x / 60)))

    to_int_cols = []
    for c in df.columns:
        if (any([x in c for x in ['weapons__', 'kills__', 'losses__']])
                and c not in not_ints):
            to_int_cols.append(c)
    if to_int_cols:
        df[to_int_cols] = df[to_int_cols].applymap(int)

    cleaned_cols = [c.replace("__", "_").replace("_", " ") for c in df.columns]
    df.columns = cleaned_cols
    return df


async def collect_stat_recs() -> pd.DataFrame:
    data = []
    async for rec in db.iterate(
            """SELECT record, pilot, files.session_start_time
                                    FROM mission_stats
                                    LEFT JOIN mission_stat_files files
                                    USING (file_name)
                                """):
        tmp = json.loads(rec['record'])
        tmp['session_stat_time'] = rec['session_start_time']
        tmp['pilot'] = rec['pilot']
        data.append(tmp)
    df = pd.DataFrame.from_records(data, index=None)
    return df


def parse_rec_keys(field_key: str) -> Optional[Dict]:
    """Extract fields from concatenated dict key."""
    cats: Dict[str, Optional[str]]
    matches = re.match("^(times)__(\w.*)__(kills)__(\w.*)__([A-z].*)$",
                       field_key)
    if matches:
        # eg: times__JF-17__kills__Planes__total
        # times/actions per airframe
        cats = {
            'category': matches.groups()[3],  # eg planes
            'metric': matches.groups()[4],  # eg: total
            'stat_group': matches.groups()[2],  # eg kills
            'equipment': matches.groups()[1],  # eg F/A-18C
        }
        return cats

    matches = re.match("^(times)__(\w.*)__(actions)__(\w.*)__([A-z].*)$",
                       field_key)
    if matches:
        # eg: times__JF-17__actions__losses__pilotDeath
        # times/actions per airframe
        cats = {
            'category': matches.groups()[4],  # eg losses
            'metric': 'total',  # eg: eject
            'stat_group': matches.groups()[3],  # eg actions
            'equipment': matches.groups()[1],  # eg F/A-18C
        }
        return cats

    matches = re.match("^(times)__(\w.*)__(losses)__(\w.*)__([A-z].*)$",
                       field_key)
    if matches:
        # eg: times__JF-17__actions__losses__pilotDeath
        # times/actions per airframe
        cats = {
            'category': matches.groups()[4],  # eg losses
            'metric': 'total',  # eg: eject
            'stat_group': matches.groups()[2],  # eg actions
            'equipment': matches.groups()[1],  # eg F/A-18C
        }
        return cats

    matches = re.match("^(weapons)__(\w.*)__([A-z].*)$", field_key)
    if matches:
        # eg: weapons__Mk-20 Rockeye__kills
        # weapons
        cats = {
            'category': None,
            'metric': matches.groups()[2],  # eg: shot, numHits
            'stat_group': matches.groups()[0],  # eg: weapons
            'equipment': matches.groups()[1],  #eg: AIM-120C
        }
        if cats['metric'] == 'gun' or cats['metric'] == 'hit':
            # These are always wrong.
            return None
        return cats

    matches = re.match("^(losses)__(\w.*)__([A-z].*)$", field_key)
    if matches:
        # losses
        cats = {
            'category': matches.groups()[1],
            'metric': matches.groups()[2],  # eg: shot, numHits
            'stat_group': matches.groups()[0],  # eg: weapons
            'equipment': "N/A",  #eg: AIM-120C
        }
        return cats

    matches = re.match("^(kills)__(\w.*)__([A-z].*)$", field_key)
    if matches:
        # losses
        cats = {
            'category': matches.groups()[1],
            'metric': matches.groups()[2],  # eg: shot, numHits
            'stat_group': matches.groups()[0],  # eg: weapons
            'equipment': "N/A",  #eg: AIM-120C
        }
        return cats

    matches = re.match("^(times)__(\w.*)__([A-z].*)$", field_key)
    if matches:
        #eg: times__AV8BNA__total
        # times air/total
        cats = {
            'category': matches.groups()[0],
            'metric': matches.groups()[2],  # eg: shot, total/inair
            'stat_group': 'usage',
            'equipment': matches.groups()[1],  #eg: AIM-120C
        }
        return cats

    matches = re.match("^(PvP)__(\w.*)$", field_key)
    if matches:
        # old format losses only
        cats = {
            'category': matches.groups()[0],  #
            'metric': matches.groups()[1],  # eg: shot, numHits
            'stat_group': matches.groups()[0],  # eg: weapons
            'equipment': 'N/A',
        }
        return cats

    matches = re.match("^([A-z]*)__(\w.*)$", field_key)
    if matches:
        # old format losses only
        cats = {
            'category': matches.groups()[1],  # eg: pilotdeath
            'metric': "total",
            'stat_group': matches.groups()[0],  # eg: losses
            'equipment': 'N/A',
        }

        return cats

    if field_key in ['lastJoin', 'friendlyHits', 'friendlyKills']:
        return None

    raise ValueError(f"Could not parse: {field_key}")
    # return {'category': None, 'metric': None,
    #         'stat_group': None, 'equipment': None}


async def collect_recs_kv() -> pd.DataFrame:
    """Collect records and convert to kv."""
    weapon_recs = await db.fetch_all(weapon_types.select())
    weapons = pd.DataFrame.from_records(weapon_recs, index=None)
    weapons.rename({
        'name': 'equipment',
        'category': 'weapon_cat'
    },
                   axis=1,
                   inplace=True)

    query = """SELECT pilot, record, files.session_start_time
                FROM mission_stats
                LEFT JOIN mission_stat_files files
                USING (file_name)
            """

    data_row_dicts: List[Dict] = []
    async for rec in db.iterate(query=query):
        rec_elements = json.loads(rec['record'])
        for key, value in rec_elements.items():
            parsed_rec = parse_rec_keys(key)
            if parsed_rec and value != "" and parsed_rec['category'] != "crash":
                parsed_rec['value'] = int(value)
                parsed_rec['key_orig'] = key
                parsed_rec['pilot'] = rec['pilot']
                parsed_rec['session_start_time'] = rec['session_start_time']
                data_row_dicts.append(parsed_rec)

    data = pd.DataFrame.from_records(data_row_dicts, index=None)
    data['session_date'] = data['session_start_time'].dt.date
    data = data.merge(weapons, how='left', on='equipment')
    data["category"] = data.category.combine_first(data.weapon_cat)
    data.value = data.apply(
        lambda x: 0
        if x['category'] == 'Gun' and x['metric'] == 'kills' else x['value'],
        axis=1)
    return data


async def all_category_grouped() -> pd.DataFrame:
    """Calculate percentage hit/kill per user, per weapon category."""
    data = await collect_recs_kv()
    data = data.groupby(["pilot", "category", 'stat_type', 'metric'],
                        as_index=False).sum()
    return data


async def calculate_overall_stats(grouping_cols: List) -> pd.DataFrame:
    """Calculate per-user/category/sub-type metrics."""
    df = await collect_recs_kv()
    # df = df[~df['metric'].isin(['hit', 'crash', 'inAir'])]
    df = df[~df['metric'].isin(['hit', 'crash'])]

    df = df.groupby(grouping_cols + ["category", "metric"],
                    as_index=False).sum()

    df['col'] = df[['category', 'metric']].apply(lambda x: ' '.join(x), axis=1)
    df.drop(labels=['category', 'metric'], axis=1, inplace=True)

    df = df.pivot_table(index=grouping_cols, columns="col", values="value")
    df.fillna(0, inplace=True)
    df.reset_index(level=grouping_cols, inplace=True)
    df["Total Losses"] = df['pilotDeath total'] + df['eject total']
    tmp = ((
        df['Air-to-Air kills']
        #  + df['Gun kills']
    ) / df['Total Losses']).round(2)
    df.insert(1, "A/A Kill Ratio", tmp)

    df["A/A P(Kill)"] = ((df['Air-to-Air kills'] / df['Air-to-Air shot']) *
                         100).round(1)
    df["A/A P(Hit)"] = ((df['Air-to-Air numHits'] / df['Air-to-Air shot']) *
                        100).round(1)

    df["A/G Dropped"] = df['Air-to-Surface shot'] + df['Bomb shot']
    df["A/G Kills"] = df['Air-to-Surface kills'] + df['Bomb kills']
    df["A/G numHits"] = df['Air-to-Surface numHits'] + df['Bomb numHits']

    df["A/G P(Hit)"] = ((df['A/G numHits'] / df['A/G Dropped']) * 100).round(1)
    df["A/G P(Kill)"] = ((df['A/G Kills'] / df['A/G Dropped']) * 100).round(1)

    df["Gun P(Hit)"] = ((df['Gun numHits'] / df['Gun shot']) * 100).round(1)
    # df["Gun P(Kill)"] = ((df['Gun kills'] / df['Gun shot']) * 100).round(1)

    drop_cols = [
        "pilotDeath total",
        "crash total",
        "eject total",
        "Air-to-Air numHits",
        "Gun numHits",
        "Bomb numHits",
        "Air-to-Surface shot",
        "Air-to-Surface numHits",
        "Air-to-Surface kills",
        "Bomb shot",
        "Gun gun",
        # "Bomb kills", "Air-to-Air kills", "A/G Kills", "Gun kills",
    ]
    df.drop([d for d in drop_cols if d in df.columns], axis=1, inplace=True)

    df.fillna(0, inplace=True)
    df = df.replace([np.inf, -np.inf], 0)
    df.columns = [c.replace('numHits', 'Hits') for c in df.columns.values]
    df.columns = [c.replace('Air-to-Air', 'A/A') for c in df.columns]
    df.columns = [c.replace(' shot', ' Shot') for c in df.columns]
    df.columns = [c.replace(' kills', ' Kills') for c in df.columns]

    try:
        df['session_date'] = df['session_date'].apply(str)
    except KeyError:
        pass

    reorder_vars = grouping_cols
    cols_out = [c for c in df.columns if c not in reorder_vars]
    cols_out.sort()
    reorder_vars.extend(cols_out)
    df = df[reorder_vars]

    return df


async def get_dataframe(subset: Optional[List] = None,
                        user_name: Optional[str] = None) -> pd.DataFrame:
    """Get stats in dataframe format suitable for HTML display."""
    stat_data = await collect_recs_kv()
    if stat_data.empty:
        return pd.DataFrame()

    try:
        if user_name:
            log.info(f"Filtering data for user = {user_name}")
            stat_data = stat_data.query(f"pilot == '{user_name}'")

        if subset:
            stat_data = stat_data[stat_data.stat_group.isin(subset)]

        if not subset or subset[0] == 'weapons':
            idx_key = ['pilot', 'category', 'equipment']
            col_key = ['metric']
        elif subset[0] == 'losses':
            idx_key = ['pilot', 'equipment']
            col_key = ['category', 'metric', 'stat_group']
        else:
            idx_key = ['pilot', 'equipment']
            col_key = ['category', 'metric', 'stat_group']

        stat_data['key'] = stat_data[col_key].apply(
            lambda x: '__'.join(x.map(str)), axis=1)

        stat_data = stat_data.pivot_table(index=idx_key,
                                          fill_value=0,
                                          aggfunc=sum,
                                          columns='key',
                                          values="value")
        stat_data.reset_index(level=idx_key, inplace=True)
        stat_data = stat_data.loc[:, (stat_data != 0).any(axis=0)]
        return stat_data
    except Exception as e:
        log.error(f"Error computing metric!\n\r{e}\n\t{stat_data}")
        raise e
