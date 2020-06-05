import asyncio
from asyncio import CancelledError
import os
from pathlib import Path
import signal
import sys

import asyncpg
import databases
from tacview_client import serve_file, client
import uvloop

from horrible.database import (DATABASE_URL, stat_files, frametime_files,
                               tacview_files, event_files)
from horrible import read_stats, gcs
from horrible.config import get_logger

log = get_logger('file_updater')

#SW Table names
TABLE_KEY = {
    'mission-events': event_files,
    'mission-stats': stat_files,
    'frametime': frametime_files,
    'tacview': tacview_files,
}


async def update_files(prefix, table):
    """Run specified job."""
    try:
        log.info("Connecting to database...")
        db = databases.Database(DATABASE_URL, min_size=1, max_size=2)
        await db.connect()
        await db.execute(f"SET application_name to {prefix.replace('-', '_')}")
        log.info(f'Starting update job for {prefix}...')
        await read_stats.sync_gs_files_with_db(prefix, table, db)
        if prefix == "tacview":
            pass
        # SW
        else:
            log.info("Processing new records...")
            await read_stats.process_lua_records(prefix, db)
        log.info('Job complete...disconnecting...')
        await db.disconnect()
        log.info('Exiting...')
        exit_status = 0
    except CancelledError:
        exit_status = -1
    return exit_status


async def proc_tac():
    await update_files("tacview", tacview_files)
    con = await asyncpg.connect(DATABASE_URL)
    await con.execute("SET application_name = tacview_reader;")
    rec  = await con.fetchval(
                """WITH tmp as (
                    SELECT file_name
                    FROM tacview_files
                    WHERE processed = FALSE AND
                        process_start IS NULL AND
                        session_start_time NOT IN (
                            SELECT start_time
                            FROM session
                            WHERE status IN ('In Progress', 'Success'))
            )
            UPDATE tacview_files SET process_start = CURRENT_TIMESTAMP
            WHERE file_name = (SELECT file_name
                                FROM tmp
                                ORDER BY session_start_time DESC
                                LIMIT 1)
            returning file_name
    """)
    if not rec:
        await con.close()
        return
    bucket = gcs.get_gcs_bucket()
    log.info(f"Parsing {rec}")
    local_path = Path('horrible').joinpath(rec)
    local_path.parent.mkdir(exist_ok=True, parents=True)
    blob = bucket.get_blob(rec)
    log.info(f"Downloading blob object to file: {local_path}....")
    fp_ = local_path.open('wb')
    blob.download_to_file(fp_)
    fp_.close()

    log.info("Download complete...creating server task...")
    server = asyncio.create_task(serve_file.serve_file(local_path, 5555))

    reader = asyncio.create_task(
        client.consumer(host='127.0.0.1', port=5555,
                        max_iters=None,
                        dsn=os.getenv("TACVIEW_DSN"),
                        batch_size=100000))
    try:
        await asyncio.gather(reader)
        log.info('Reader complete...updating database...')
        await con.execute(f"""UPDATE tacview_files
                            SET processed = TRUE,
                            process_end = CURRENT_TIMESTAMP
                            WHERE file_name = $1""", rec)
        await con.execute("ANALYZE object; ANALYZE event; ANALYZE impact;")
        log.info('File processed successfully!')

        exit_status = 0
    except CancelledError:
        reader.cancel()
        exit_status = -1
    except Exception as err:
        log.error(err)
        await con.execute(f"""UPDATE tacview_files
                    SET processed = FALSE,
                    process_end = CURRENT_TIMESTAMP,
                    errors = 1
                    WHERE file_name = $1""", rec)
        exit_status = 0
    finally:
        log.info('Canceling fileserver...')
        server.cancel()
        await con.close()
    return exit_status


async def shutdown(signal, loop):
    log.info(f"Received exit signal {signal.name}...")
    tasks = [t for t in asyncio.all_tasks() if t is not
             asyncio.current_task()]

    for task in tasks:
        task.cancel()

    log.info("Cancelling outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', required=True,
                        choices=['mission-events', 'frametime',
                                 'mission-stats', 'tacview'],
                        help='Prefix of the GCS subdirectory that '
                            'should be updated')
    parser.add_argument('--interval', type=int, default=120,
                        help='Number of seconds between updates.')
    args = parser.parse_args()

    table = TABLE_KEY[args.prefix]
    uvloop.install()
    loop = asyncio.get_event_loop()
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for sig in signals:
        loop.add_signal_handler(
            sig, lambda sig=sig: asyncio.create_task(shutdown(sig, loop)))

    while True:
        if args.prefix == 'tacview':
            task = loop.create_task(proc_tac())
        else:
            task = loop.create_task(update_files(args.prefix, table))
        result = loop.run_until_complete(asyncio.gather(task))
        log.info(result)
        if result and result[0] == -1:
            sys.exit(1)
        log.info(f'Sleeping for {args.interval}')
        loop.run_until_complete(asyncio.gather(asyncio.sleep(args.interval)))
