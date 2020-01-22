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

from stats.gcs_config import get_gcs_bucket
from stats.database import db

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
log.setLevel(level=logging.INFO)


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
        log.info(f"Inserting stat file: {stat_file.name}")
        try:
            await db.execute(f"""INSERT INTO mission_stat_files
                       (file_name) VALUES ('{stat_file.name}')""")
        except asyncpg.exceptions.UniqueViolationError:
            pass


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


def parse_ts(path: Path) -> datetime.datetime:
    file = Path(path.name).name
    m = re.search("([A-z]{3} [0-9]{1,2}, [0-9]{4} at [0-9]{2} [0-9]{2} [0-9]{2})",
                  file)
    parsed = m.group().replace("at ", "")
    return datetime.datetime.strptime(parsed, "%b %d, %Y %H %M %S")


def result_to_flat_dict(result: dict, session_ts: datetime.datetime) -> dict:
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

    result['session_start_time'] = str(session_ts)
    return result


def read_lua_table(stat: Path) -> List:
    """Read a single json file, returning a dict."""
    with stat.open('r') as fp_:
        file_contents = " ".join([f for f in fp_.readlines()])
    if file_contents == "placeholder":
        return
    session_ts = parse_ts(stat)
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
    results = [result_to_flat_dict(res, session_ts) for res in result.values()]
    return results


async def process_lua_records() -> NoReturn:
    """Parse a directory of Sl-Mod stats files, returning a pandas dataframe."""
    bucket = get_gcs_bucket()
    query = """SELECT file_name
                FROM mission_stat_files
                WHERE processed = FALSE
            """
    async for stat in db.iterate(query):
        try:
            log.info(f"Handing {stat['file_name']}")
            if stat['file_name'] == "mission-stats/":
                continue
            local_path = Path(f"cache/{stat['file_name']}")
            local_path.parent.mkdir(parents=True, exist_ok=True)
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
                await db.execute(f"""INSERT INTO mission_stats
                                (file_name, session_start_time, record)
                                    VALUES ('{stat['file_name']}',
                                        '{stat_parsed[0]["session_start_time"]}',
                                        '{json.dumps(stat_parsed)}')
                                    """)

            log.info("Marking record as processed...")
            await db.execute(f"""UPDATE mission_stat_files
                             SET processed = TRUE,
                             processed_at = CURRENT_TIMESTAMP
                                WHERE file_name = '{stat['file_name']}'
                                """)

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


async def collect_recs_from_db(check_all_exists: bool = False,
                               process_new: bool = False) -> pd.DataFrame:
    if check_all_exists:
        await insert_gs_files_to_db()
    if process_new:
        await process_lua_records()
    data = []

    async for rec in db.iterate("SELECT record FROM mission_stats"):
        data.extend(json.loads(rec['record']))
    data = pd.DataFrame.from_records(data, index=None)
    return data


def compute_metrics(results: pd.DataFrame) -> pd.DataFrame:
    """Compute additional metrics, reorder columns, and sort."""
    grouper = results.groupby(["pilot"])
    # count = results[["pilot", "session_start_time"]].\
    #     groupby(["pilot"]).agg(['count']).\
    #     reset_index()
    # count.columns = ["pilot", "total_sessions"]
    results = grouper.sum().reset_index()
    # results = pd.merge(results, count, how='left', on='pilot')

    results['losses__total_deaths'] = results['losses__crash'] + results["losses__pilotDeath"]
    results["kills__A/A Kill Ratio"] = results["kills__Planes__total"]/results["losses__total_deaths"]
    results["kills__A/A Kill Ratio"] = results["kills__A/A Kill Ratio"].round(1)

    # results["weapons__Prob_Hit"] = results["weapons__A/A Kill Ratio"].round(1)

    results = results.replace([np.inf, -np.inf], np.nan)

    prio_cols = ["pilot",
                 # "total_sessions",
                 "kills__A/A Kill Ratio",
                 "kills__Planes__total",
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
    df = await collect_recs_from_db()
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
    return df


# if __name__ == '__main__':
#     import argparse
#     parser = argparse.ArgumentParser()
#     parser.add_argument('--max-parse', default=100, type=int,
#                         help='Limit the number of files being parsed.')
#     args = parser.parse_args()
#     collect_recs_from_db(args.max_parse).to_html()
