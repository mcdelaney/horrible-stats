import datetime
import logging
from pathlib import Path
import re
from typing import NoReturn

import asyncpg
from google.cloud import storage
import sqlalchemy as sa

from . import db, file_format_ref

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
log.setLevel(level=logging.INFO)


def get_gcs_bucket(bucket="horrible-server"):
    """Initialize a client object and return a bucket."""
    client = storage.Client()
    return client.get_bucket(bucket)


async def sync_gs_files_with_db(bucket_prefix: str, table: sa.Table) -> NoReturn:
    """Ensure all gs files are in database."""
    bucket = get_gcs_bucket()
    stats_list = bucket.client.list_blobs(bucket, prefix=bucket_prefix)
    files = await db.fetch_all(f"SELECT file_name FROM {table.name}")
    files = [file["file_name"] for file in files]
    for stat_file in stats_list:
        if stat_file.name in files:
            log.debug(f"File: {stat_file.name} already recorded...")
            continue

        if stat_file.name == bucket_prefix:
            continue

        try:
            log.info(f"Inserting stat file: {stat_file.name}")
            file_ts = file_format_ref[bucket_prefix](stat_file.name)
            await db.execute(table.insert(),
                             {'file_name': stat_file.name,
                              'session_start_time': file_ts,
                              'processed': False,
                              'processed_at': None,
                              'errors': 0})
        except asyncpg.exceptions.UniqueViolationError:
            log.error("File already has been inserted!")
            raise asyncpg.exceptions.UniqueViolationError
