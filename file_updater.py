import asyncio
from asyncio import CancelledError
from pathlib import Path
import os
import subprocess
import signal
import asyncpg
import uvloop
import sys
from multiprocessing import Process
from tacview_client import serve_file, client
from horrible.database import (DATABASE_URL, db, stat_files, frametime_files,
                               tacview_files, event_files)
from horrible import read_stats, gcs
from horrible.config import log



class SigTermWatcher:
  exit_now = False
  def __init__(self):
    signal.signal(signal.SIGINT, self.managed_shutdown)
    signal.signal(signal.SIGTERM, self.managed_shutdown)

  def managed_shutdown(self,signum, frame):
    self.exit_now = True


async def update_files(prefix, table):
    """Run specified job."""
    try:
        log.info("Connecting to database...")
        await db.connect()
        log.info(f'Starting update job for {prefix}...')
        await read_stats.sync_gs_files_with_db(prefix, table, db)
        if prefix == "tacview":
            pass
        else:
            log.info("Processing new records...")
            await read_stats.process_lua_records(prefix)
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
                    LIMIT 1
            )
            UPDATE tacview_files SET process_start = CURRENT_TIMESTAMP
            WHERE file_name = (SELECT file_name FROM tmp)
            returning file_name
    """)
    if not rec:
        return
    await con.close()
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
        con = await asyncpg.connect(DATABASE_URL)
        await con.execute(f"""UPDATE tacview_files
                            SET processed = TRUE,
                            process_end = CURRENT_TIMESTAMP
                            WHERE file_name = $1""", rec)
        log.info('File processed successfully!')
        exit_status = 0
    except CancelledError:
        reader.cancel()
        exit_status = -1
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

    table_key = {
        'mission-events': event_files,
        'mission-stats': stat_files,
        'frametime': frametime_files,
        'tacview': tacview_files,
    }
    table = table_key[args.prefix]
    # while not sig_watcher.exit_now:
    uvloop.install()
    loop = asyncio.get_event_loop()
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for sig in signals:
        loop.add_signal_handler(
            sig, lambda sig=sig: asyncio.create_task(shutdown(sig, loop)))

    while True:
        if args.prefix == 'tacview':
            task = loop.create_task(proc_tac())
            # task = asyncio.create_task(proc_tac())
        else:
            task = loop.create_task(update_files(args.prefix, table))
            # task = asyncio.create_task(update_files(args.prefix, table))
            # asyncio.run(proc_tac())
        result = loop.run_until_complete(asyncio.gather(task))
        log.info(result)
        if result and result[0] == -1:
            sys.exit(1)
        log.info(f'Sleeping for {args.interval}')
        loop.run_until_complete(asyncio.gather(asyncio.sleep(args.interval)))
