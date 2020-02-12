import asyncio
import argparse
import gzip
import logging
from pathlib import Path

import requests

from horrible.database import db
from horrible.gcs import get_gcs_bucket

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
log.setLevel(level=logging.INFO)


async def upload_files(local_path_glob, remote_subdir: str, delete_files: bool, db):
    """Upload files to GCP bucket."""
    bucket = get_gcs_bucket()
    for file_ in local_path_glob:
        try:
            log.debug(f"Processing {file_.absolute()}...")
            gs_filename = f"{remote_subdir}/{file_.name}"
            blob = bucket.blob(gs_filename)
            meta = bucket.get_blob(gs_filename)
            if blob.exists() and file_.stat().st_mtime <= meta.updated.timestamp():
                log.debug(f"Skipping file {file_.name}...already uploaded")
            else:
                if blob.exists():
                    log.info("Updating file...has changed since last update...")
                log.info(f"Uploading file {file_.absolute()} to {remote_subdir}...")

                with file_.open('rb') as fp_:
                    content = fp_.read()

                if '.zip' not in file_.name:
                    log.info("File not compressed...zipping...")
                    content = gzip.compress(content)
                blob.content_type = "text/plain"
                blob.content_encoding = "gzip"
                blob.upload_from_string(content)

                if delete_files:
                    log.info("File uploaded...deleting...")
                    file_.unlink()
        except Exception as e:
            log.error(e)
            log.info("File is open...skipping...")
    requests.get("http://ahorribleserver.com/check_db_files")
    # await sync_gs_files_with_db("mission-stats", stat_files, db)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-path", type=Path,
                        help="Path to local directory holding files.")
    parser.add_argument("--local-suffix", type=str,
                        help="Regex pattern for local files being uploaded.")
    parser.add_argument("--remote-subdir", type=str,
                        help="Name of remote bucket destination subdir.")
    parser.add_argument("--delete", action="store_true",
                        help="If set, files will be deleted after upload.")
    parser.add_argument("--env", default='prod', type=str,
                        help="Prod or stg.")
    args = parser.parse_args()

    if args.env != 'prod':
        args.remote_subdir = args.env + "/" + args.remote_subdir
        args.delete = False

    local_glob = args.local_path.glob(args.local_suffix)
    asyncio.run(upload_files(local_glob, args.remote_subdir, args.delete, db))
