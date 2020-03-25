import asyncio
from pathlib import Path
import subprocess
import signal
import asyncpg

from horrible.database import (DATABASE_URL, db, stat_files, frametime_files,
                               tacview_files, event_files)
from horrible import read_stats, gcs
from horrible.config import log


async def do_job(prefix, table):
    """Run specified job."""
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


async def proc_tac():
    """Get an unprocess file and pass it to tacview-client."""
    con = await asyncpg.connect(DATABASE_URL)
    rec  = await con.fetchval(
                """SELECT file_name
                FROM tacview_files
                WHERE processed = FALSE AND
                    DATE_TRUNC('sec',session_start_time) NOT IN (
                        SELECT DATE_TRUNC('sec',(start_time - interval '5h'))
                        FROM session
                        WHERE status IN ('In Progress', 'Success')
                )
                """)
    await con.close()
    bucket = gcs.get_gcs_bucket()
    log.info(f"Parsing {rec}")
    local_path = Path('horrible').joinpath(rec)
    local_path.parent.mkdir(exist_ok=True, parents=True)
    blob = bucket.get_blob(rec)
    log.info(f"Downloading blob object to file: {local_path}....")
    blob.download_to_file(local_path.open('wb'))
    subprocess.run(["tacview", "client",
                    "--host", "127.0.0.1",
                    "--port", '5555',
                    "--filename", str(local_path.absolute()),
                    "--batch_size", '100000',
                    ])

    log.info('File processed...Marking as success')
    con = await asyncpg.connect(DATABASE_URL)
    await con.execute(f"""UPDATE tacview_files
                        SET processed = TRUE,
                        processed_at = date_trunc('second', CURRENT_TIMESTAMP)
                        WHERE file_name = $1""", rec)
    await con.close()
    log.info('File processed successfully!')


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

    while True:
        asyncio.run(do_job(args.prefix, table))
        if args.prefix == 'tacview':
            asyncio.run(proc_tac())
        log.info(f'Sleeping for {args.interval}')
        asyncio.run(asyncio.sleep(args.interval))
