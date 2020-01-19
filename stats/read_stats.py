import argparse
import datetime
import json
import logging
from pathlib import Path, WindowsPath
from pprint import pprint
import re
import threading

from lupa import LuaRuntime
import pandas as pd


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
log.setLevel(level=logging.INFO)


def lua_tbl_to_py(lua_tbl) -> dict:
    """Coerce lua table to python object."""
    out = {}
    try:
        for k, v in lua_tbl.items():
            if k == b'names':
                out['names'] = ', '.join([val.decode() for val in dict(v).values()])
                continue
            if v and isinstance(v, (int, bytes, float, str)):
                out[k.decode()] = v
            else:
                out[k.decode()] = lua_tbl_to_py(v)
    except AttributeError:
        return lua_tbl
    return out


def parse_ts(path: Path) -> datetime:
    file = str(path.name)
    m = re.search("([A-z]{3}\ [0-9]{1,2}\,\ [0-9]{4}\ at\ [0-9]{2}\ [0-9]{2}\ [0-9]{2})", file)
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
        log.error(f"Error: {e} \n {result}")
        raise e

    result['session_ts'] = session_ts
    return result


def read_lua_table(file_path: Path) -> list:
    """Read a single json file, returning a dict."""
    log.info(f"Reading stats file at: {file_path}...")
    with file_path.open('r') as fp_:
        lua_code = " ".join([line for line in fp_])

    session_ts = parse_ts(file_path)
    lua_code = f"\n function() \r\n local {lua_code} return misStats end"

    thread_count = 1
    lua_funcs = [ LuaRuntime(encoding=None).eval(lua_code)
                  for _ in range(thread_count) ]

    results = [None]
    def read_tab_func(i, lua_func):
        results[i] = lua_func()

    threads = [ threading.Thread(target=read_tab_func, args=(i,lua_func))
                for i, lua_func in enumerate(lua_funcs) ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    result = lua_tbl_to_py(results[0])
    results = [result_to_flat_dict(res, session_ts) for res in result.values()]
    return results


def main(stats_path:Path, max_parse: int = 1) -> dict:
    """Parse a directory of Sl-Mod stats files, returning a pandas dataframe."""
    if not stats_path.exists():
        raise NotADirectoryError("Path does not exist!")
    results = []
    for i, stat in enumerate(stats_path.glob(pattern="*.lua")):
        try:
            stat_parsed = read_lua_table(stat)
            if len(stat_parsed) > 0:
                results.extend(stat_parsed)
            if i >= (max_parse-1):
                break
        except Exception as e:
            log.error(e)

    results = pd.DataFrame.from_records(results, index=None)
    results.fillna(0, inplace=True)
    return results


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stats-path',
                        default="C://Users/mcdel/Dropbox/dcs-stats/Mission Stats/",
                        type=WindowsPath, help='Path to stats file directory.')
    parser.add_argument('--max-parse', default=100, type=int,
                        help='Limit the number of files being parsed.')
    args = parser.parse_args()
    pprint(main(args.stats_path, args.max_parse))
