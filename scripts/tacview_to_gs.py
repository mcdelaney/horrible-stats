import argparse
import logging
from pathlib import Path

from google.cloud import storage
from google.oauth2 import service_account

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
log.setLevel(level=logging.INFO)

BUCKET = "horrible-server"


def upload_files(local_path_glob: Path, remote_subdir: str, delete_files: bool):
    """Upload files to GCP bucket."""
    remote_subdir = Path(remote_subdir)
    for file in local_path_glob:
        try:
            log.info(f"Uploading {file.absolute()} to {remote_subdir}")
            blob = bucket.blob(f"{remote_subdir}/{file.name}")
            if blob.exists():
                log.info(f"Skipping file {file.name}...already uploaded...")
            else:
                blob.upload_from_filename(str(file.absolute()))
                if delete_files:
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
    parser.add_argument("-d", "--delete", default=False, type=bool,
                        help="If set, files will be deleted after upload.")
    args = parser.parse_args()

    credentials = service_account.Credentials.from_service_account_file(
        "dcs-storage-gcs.json")

    client = storage.Client(credentials=credentials,
                            project=credentials.project_id)
    bucket = client.get_bucket(BUCKET)

    local_glob = args.local_path.glob(args.local_suffix)
    upload_files(local_glob, args.remote_subdir, args.delete)
