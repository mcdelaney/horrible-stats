import asyncio

# from tacview_client import db as tac_db
from horrible.database import (db, stat_files, frametime_files,
                               tacview_files, event_files)
from horrible import read_stats
from horrible.config import log


async def do_job(prefix, table):
    """Run specified job."""
    log.info("Connecting to database...")
    await db.connect()
    log.info(f'Starting update job for {prefix}...')
    await read_stats.sync_gs_files_with_db(prefix, table, db)
    if prefix != "tacview":
        log.info("Processing new records...")
        await read_stats.process_lua_records(prefix)
    log.info('Job complete...disconnecting...')
    await db.disconnect()
    log.info('Exiting...')


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
    if args.prefix == 'mission-events':
        table = event_files
    elif args.prefix == 'mission-stats':
        table = stat_files
    elif args.prefix == 'frametime':
        table = frametime_files
    elif args.prefix == 'tacview':
        table = tacview_files
    else:
        raise NotImplementedError(args.prefix)
    while True:
        asyncio.run(do_job(args.prefix, table))
        log.info(f'Sleeping for {args.interval}')
        asyncio.run(asyncio.sleep(args.interval))
