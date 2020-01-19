import argparse
import logging
from pathlib import Path

from google.cloud import storage
from google.oauth2 import service_account

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
log.setLevel(level=logging.INFO)

BUCKET = "horrible-server"

local_path_glob = Path("../Saved Games/DCS.openbeta_server/Logs/FrameTimeExport").glob("*")
remote_subdir = "frametime"
delete_files = False
file = list(local_path_glob)[0]

def upload_files(local_path_glob: Path, remote_subdir: str, delete_files: bool):
    """Upload files to GCP bucket."""
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
                try:
                    # TODO
                    # Write only the new bytes of the file if it's open
                    fopen_test = file.open('w+')
                    fopen_test.close()
                    fopen = False
                except Exception as e:
                    log.error(e)
                    log.error("File is already open in another process!")
                    fopen = True
                    # continue
                log.info("Uploading file...")
                blob.upload_from_filename(str(file.absolute()))
                if delete_files and not fopen:
                    log.info("File uploaded...deleting...")
                    file.unlink()
        except PermissionError:
            log.info("File is open...skipping...")


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-path", type=Path,
                        help="Path to local directory holding files.")
    parser.add_argument("--local-suffix", type=str,
                        help="Regex pattern for local files being uploaded.")
    parser.add_argument("--remote-subdir", type=str,
                        help="Name of remote bucket destination subdir.")
    parser.add_argument("--delete", action="store_true",
                        help="If set, files will be deleted after upload.")
    args = parser.parse_args()

    credentials = service_account.Credentials.from_service_account_file(
        Path("~/dcs-storage-gcs.json").expanduser())

    client = storage.Client(credentials=credentials,
                            project=credentials.project_id)
    bucket = client.get_bucket(BUCKET)

    local_glob = args.local_path.glob(args.local_suffix)
    upload_files(local_glob, args.remote_subdir, args.delete)
