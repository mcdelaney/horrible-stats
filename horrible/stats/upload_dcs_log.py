import datetime
from pathlib import Path
import logging
import gzip

from gcs import get_gcs_bucket

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
log.setLevel(level=logging.INFO)


if __name__ == '__main__':
    log.info("Uploading dcs.log to gcs...")
    file = Path("C://Users/mcdel/Saved Games/DCS.openbeta_server/Logs/dcs.log")
    gs_filename = f"dcs-log-files/dcs-{datetime.datetime.now()}.log"
    bucket = get_gcs_bucket()
    blob = bucket.blob(gs_filename)
    meta = bucket.get_blob(gs_filename)
    log.info("Uploading DCS log file...")
    with file.open('rb') as fp_:
        content = fp_.read()
    content = gzip.compress(content)
    blob.content_type = "text/plain"
    blob.content_encoding = "gzip"
    blob.upload_from_string(content)
    log.info("dcs.log uploaded successfully...")
