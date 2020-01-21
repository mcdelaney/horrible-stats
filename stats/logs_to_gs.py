import argparse
import gzip
import logging
from pathlib import Path

from utils import get_gcs_bucket

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
log.setLevel(level=logging.INFO)


def upload_files(local_path_glob: Path, remote_subdir: str, delete_files: bool):
    """Upload files to GCP bucket."""
    bucket = get_gcs_bucket()
    remote_subdir = Path(remote_subdir)
    for file in local_path_glob:
        try:
            log.info(f"Uploading {file.absolute()} to {remote_subdir}")
            gs_filename = f"{remote_subdir}/{file.name}"
            blob = bucket.blob(gs_filename)
            meta = bucket.get_blob(gs_filename)
            if blob.exists() and file.stat().st_mtime <= meta.updated.timestamp():
                log.info(f"Skipping file {file.name}...already uploaded")
            else:
                if blob.exists():
                    log.info("Updating file...has changed since last update...")
                log.info("Uploading file...")

                with file.open('rb') as fp_:
                    content = fp_.read()

                if '.zip' not in file.name:
                    log.info("File not compressed...zipping...")
                    content = gzip.compress(content)
                blob.content_type = "text/plain"
                blob.content_encoding = "gzip"
                blob.upload_from_string(content)

                if delete_files:
                    log.info("File uploaded...deleting...")
                    file.unlink()
        except PermissionError:
            log.info("File is open...skipping...")


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
    parser.add_argument("--env", default='stg', type=str,
                        help="Prod or stg.")
    args = parser.parse_args()
    if args.env != 'prod':
        args.remote_subdir = args.env + "/" + args.remote_subdir
        args.delete = False

    local_glob = args.local_path.glob(args.local_suffix)
    upload_files(local_glob, args.remote_subdir, args.delete)
