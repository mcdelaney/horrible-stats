import json
from pathlib import Path
import os

import asyncpg

from horrible.gcs import get_gcs_bucket
from horrible.config import get_logger

from google.cloud import storage

log = get_logger('statreader')

########################################################################


def list_blobs(bucket_name):
    """Lists all the blobs in the bucket."""
    #bucket_name = "your-bucket-name"

    storage_client = storage.Client()

    # Note: Client.list_blobs requires at least package version 1.17.0.
    blobs = storage_client.list_blobs(bucket_name)

    for blob in blobs:
        log.info(f'Blob Name: {blob.name}')

def download_blob(bucket_name, source_blob_name, destination_file_name):
    """Downloads a blob from the bucket."""
    # bucket_name = "your-bucket-name"
    # source_blob_name = "storage-object-name"
    # destination_file_name = "local/path/to/file"

    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)

    log.info(
        "Blob {} downloaded to {}.".format(
            source_blob_name, destination_file_name
        )
    )

async def fetch_tacview_file(filename) -> str:
    """fetch a single tacview file."""

# filename = tacview/some_tacview_file.acmi
# sample filename = Tacview-20200309-175947-DCS-Operation HorribleFox v3.txt.acmi

# 1. get a list of the files from GCS
# 2. find GCS the file we want 
# 3.# give it to the browser server and trigger a download somehow


    bucket = 'horrible-server' # the GCS bucket "horrible-server"

    #list_blobs(bucket) #1. list all blobs in bucket (all files in GCS)

    remote_filename = filename # tacview/some_tacview_file.acmi

    local_filename = 'horrible/' + filename # horrible/tacview/filename.acmi

    # create the tacview folder if not present
    local_path = Path('horrible').joinpath('/tacview') # The local path to the server files horrible/tacview/
    local_path.parent.mkdir(exist_ok=True, parents=True) # create a directory on the app server
    log.info(f"Created folder: {local_path}") # should make a "tacview" folder

    local_filename = local_filename.replace(" ", "_") # parse the name to add underscores instead of spaces

    log.info(f'Attempting to download file... {remote_filename}')
    try:
        download_blob(bucket, remote_filename, local_filename) #2. download the tv file to the local_path
        log.info(f'GCS Bucket: {bucket} GCS File: {remote_filename} App server File: {local_filename}')
        log.info(f'Downloaded file to... {local_filename}')
    except:
        log.info('An error occurred')

    return local_filename #3. return local filename to browser?