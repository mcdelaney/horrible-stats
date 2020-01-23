import asyncpg
import json
import datetime
from typing import List, Dict, NoReturn
import logging
from pathlib import Path
import re
import threading
import traceback

from lupa import LuaRuntime
import numpy as np
import pandas as pd
import sqlalchemy as sa

from stats.gcs_config import get_gcs_bucket
from stats.database import db, weapon_types, stat_files, mission_stats


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
log.setLevel(level=logging.INFO)


async def sync_weapons() -> NoReturn:
    if await db.execute(weapon_types.count()) == 0:
        weapons = pd.read_csv("data/weapon-db.csv").to_dict('records')
        query = weapon_types.insert()
        await db.execute_many(query, values=weapons)


async def insert_gs_files_to_db() -> NoReturn:
    """Ensure all gs files are in database."""
    bucket = get_gcs_bucket()
    stats_list = bucket.client.list_blobs(bucket, prefix="mission-stats/")
    files = await db.fetch_all("SELECT file_name FROM mission_stat_files")
    files = [file["file_name"] for file in files]
    for stat_file in stats_list:
        if stat_file.name in files:
            log.info(f"File: {stat_file.name} already recorded...")
            continue
        if stat_file.name == "mission-stats/":
            continue

        try:
            log.info(f"Inserting stat file: {stat_file.name}")
            await db.execute(stat_files.insert(),
                             {'file_name': stat_file.name,
                              'session_start_time': parse_ts(stat_file.name)})
        except asyncpg.exceptions.UniqueViolationError:
            log.error("File already has been inserted!")
            raise asyncpg.exceptions.UniqueViolationError


def lua_tbl_to_py(lua_tbl) -> Dict:
    """Coerce lua table to python object."""
    flatten_these = ['names', 'friendlyKills', 'friendlyHits']
    out = {}
    try:
        for k, v in lua_tbl.items():
            match_key = [flat_k for flat_k in flatten_these if flat_k == k.decode()]
            if match_key:
                try:
                    out[match_key[0]] = ', '.join([val.decode()
                                                   for val in dict(v).values()])
                except Exception:
                    pass
                continue
            if v and isinstance(v, (int, bytes, float, str)):
                out[k.decode()] = v
            else:
                out[k.decode()] = lua_tbl_to_py(v)

        # rename names to pilot.
        if "names" in out.keys():
            out['pilot'] = out.pop('names')

    except AttributeError:
        return lua_tbl
    return out


def parse_ts(path: str) -> datetime.datetime:
    file = Path(path).name
    m = re.search("([A-z]{3} [0-9]{1,2}, [0-9]{4} at [0-9]{2} [0-9]{2} [0-9]{2})",
                  file)
    parsed = m.group().replace("at ", "")
    return datetime.datetime.strptime(parsed, "%b %d, %Y %H %M %S")


def result_to_flat_dict(result: dict) -> dict:
    """Flatten nested keys for DataFrame."""
    try:
        for k in list(result.keys()):
            if isinstance(result[k], dict):
                subdict = result.pop(k)
                for subkey, v in subdict.items():
                    if isinstance(v, dict):
                        for sub_sub_key, val in v.items():
                            # This is gross but it's never nested more than 2 levels.
                            result[f"{k}__{subkey}__{sub_sub_key}"] = val
                    elif isinstance(v, list):
                        result[f"{k}__{subkey}"] = ", ".join(v)
                    else:
                        result[f"{k}__{subkey}"] = v
    except Exception as e:
        raise e

    return result


def read_lua_table(stat: Path) -> List:
    """Read a single json file, returning a dict."""
    with stat.open('r') as fp_:
        file_contents = " ".join([f for f in fp_.readlines()])
    if file_contents == "placeholder":
        return

    lua_code = f"\n function() \r\n local {file_contents} return misStats end"

    thread_count = 1
    lua_funcs = [LuaRuntime(encoding=None).eval(lua_code)
                 for _ in range(thread_count)]

    results = [None]

    def read_tab_func(i, lua_func):
        results[i] = lua_func()

    threads = [threading.Thread(target=read_tab_func, args=(i, lua_func))
               for i, lua_func in enumerate(lua_funcs)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    result = lua_tbl_to_py(results[0])
    results = []
    for res in result.values():
        tmp = result_to_flat_dict(res)
        results.append({'file_name': str(stat),
                        'pilot': tmp['pilot'],
                        'record': tmp})
    return results


async def process_lua_records() -> NoReturn:
    """Parse a directory of Sl-Mod stats files, returning a pandas dataframe."""
    Path("mission-stats").mkdir(parents=True, exist_ok=True)
    bucket = get_gcs_bucket()
    stats_files = await db.fetch_all(stat_files.select(sa.text("processed=FALSE")))
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
                             processed_at = CURRENT_TIMESTAMP
                             WHERE file_name = '{stat['file_name']}'
                                """)
            try:
                for stat in stat_parsed:
                    for key, value in stat.items():
                        log.error(f"{key}: {value}")
            except Exception:
                log.error("Could not print table state...")
                pass


async def collect_stat_recs() -> pd.DataFrame:
    data = []
    async for rec in db.iterate("""SELECT record, files.session_start_time
                                FROM mission_stats
                                LEFT JOIN mission_stat_files files
                                USING (file_name)
                                """):
        tmp = json.loads(rec['record'])
        tmp['session_stat_time'] = rec['session_start_time']
        data.append(tmp)
    data = pd.DataFrame.from_records(data, index=None)
    return data


async def collect_recs_kv() -> pd.DataFrame:
    """Collect records and convert to kv."""
    data = []
    weapons = await db.fetch_all(weapon_types.select())
    weapons = pd.DataFrame.from_records(weapons, index=None)
    weapons['stat_type'] = weapons['name']
    weapons.drop(labels=['type', 'name'], axis=1, inplace=True)

    async for rec in db.iterate("""SELECT pilot, record,
                                    files.session_start_time
                                FROM mission_stats
                                LEFT JOIN mission_stat_files files
                                USING (file_name)
                                """):
        recs = json.loads(rec['record'])
        recs.pop('pilot')
        recs.pop('id')

        tmp = pd.DataFrame({"key": list(recs.keys()),
                            "value": list(recs.values())},
                           columns=["key", "value"], index=None)
        tmp['pilot'] = rec['pilot']
        tmp['session_start_time'] = rec['session_start_time']
        tmp = tmp[tmp.value != ""]
        tmp['value'] = tmp.value.astype(int)
        tmp["stat_group"] = tmp.key.apply(lambda x: x.split("__")[0])
        tmp["stat_type"] = tmp.key.apply(lambda x: "__".join(x.split("__")[1:-1]))
        tmp["stat_sub_type"] = tmp.key.apply(lambda x: "__".join(x.split("__")[-1:]))
        tmp["key"] = tmp.key.apply(lambda x: "__".join(x.split("__")[1:]))
        tmp = tmp[["session_start_time", "pilot", "stat_group", "stat_type",
                   "stat_sub_type", "key", "value"]]
        data.append(tmp)

    data = pd.concat(data)
    data = data.merge(weapons, how='left', on='stat_type')
    data["category"] = data.category.combine_first(data.stat_type)
    data['category'] = data.category.apply(lambda x: "total" if x == "" else x)
    data = data.groupby([ "stat_group", "stat_sub_type", 'category'
                         ], as_index=False).sum()
    return data


def compute_metrics(results: pd.DataFrame) -> pd.DataFrame:
    """Compute additional metrics, reorder columns, and sort."""
    grouper = results.groupby(["pilot"])
    results = grouper.sum().reset_index()

    results['losses__total_deaths'] = results['losses__crash'] + results["losses__pilotDeath"]
    results["kills__A/A Kill Ratio"] = results["kills__Planes__total"]/results["losses__total_deaths"]
    results["kills__A/A Kill Ratio"] = results["kills__A/A Kill Ratio"].round(1)
    results["kills__A/A Kills Total"] = results["kills__Planes__total"]
    results.drop(labels=["kills__Planes__total"], axis=1, inplace=True)

    # results["weapons__Prob_Hit"] = results["weapons__A/A Kill Ratio"].round(1)

    results = results.replace([np.inf, -np.inf], np.nan)

    prio_cols = ["pilot",
                 # "total_sessions",
                 "kills__A/A Kill Ratio",
                 "kills__A/A Kills Total",
                 "losses__total_deaths",
                 "kills__Ground Units__total",
                 "losses__pilotDeath",
                 "losses__eject",
                 "losses__crash",
                 "kills__Ships__total",
                 "kills__Buildings__total"]

    for i, col in enumerate(prio_cols):
        try:
            tmp = results[col]
            results.drop(labels=[col], axis=1, inplace=True)
            results.insert(i, col, tmp)
        except KeyError:
            log.error(f"Key {col} not in cols:")
            for c in results.columns:
                log.error(f"\t{c}")

    results.fillna(0, inplace=True)
    results = results.sort_values(by="kills__A/A Kill Ratio", ascending=False)
    return results


def format_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Format a dataframe for display in HTML."""
    not_ints = ['kills__A/A Kill Ratio']
    for c in df.columns:
        if "times__" in c:
            df[c] = df[c].apply(lambda x: int(round(x/60)))

    to_int_cols = []
    for c in df.columns:
        if any([x in c for x in ['weapons__', 'kills__', 'losses__']]) and \
         c not in not_ints:
            to_int_cols.append(c)
    if to_int_cols:
        df[to_int_cols] = df[to_int_cols].applymap(int)

    cleaned_cols = [c.replace("__", "_").replace("_", " ") for c in df.columns]
    df.columns = cleaned_cols
    return df


def get_subset(df: pd.DataFrame, subset_name: List) -> pd.DataFrame:
    """Summarise by user, returning weapons columns only."""
    drop_cols = []
    for col in df.columns:
        if col != "pilot" and not any([f"{s}__" in col for s in subset_name]):
            drop_cols.append(col)
    df.drop(labels=drop_cols, axis=1, inplace=True)

    for sub in subset_name:
        df.columns = [c.replace(f"{sub}__", "") for c in df.columns]

    return df


async def get_dataframe(subset: str = None, user_name: str = None) -> pd.DataFrame:
    """Get stats in dataframe format suitable for HTML display."""
    df = await collect_stat_recs()
    if df.empty:
        return pd.DataFrame()

    try:
        df = compute_metrics(df)
    except Exception as e:
        log.error(f"Error computing metric!\n\r{e}\n\t{df}")
        raise e

    if user_name:
        df = df[df['pilot'] == user_name]

    df.drop(labels=["id"], axis=1, inplace=True)
    df = df[df.sum(axis=1) != 0.0]

    if subset:
        df = get_subset(df, subset)

    df = format_cols(df)
    df = df.loc[:, (df != 0).any(axis=0)]
    return df