import asyncio
import argparse
import gzip
import logging
from pathlib import Path
import urllib.parse

from google.auth.transport.requests import AuthorizedSession
from google.resumable_media import requests, common
from google.cloud import storage

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
log.setLevel(level=logging.INFO)
consoleHandler = logging.StreamHandler()
log.addHandler(consoleHandler)



class GCSObjectStreamUpload(object):
    def __init__(
            self, 
            client: storage.Client,
            bucket_name: str,
            blob_name: str,
            chunk_size: int=256 * 1024
        ):
        self._client = client
        self._bucket = self._client.bucket(bucket_name)
        self._blob = self._bucket.blob(blob_name)

        self._buffer = b''
        self._buffer_size = 0
        self._chunk_size = chunk_size
        self._read = 0

        self._transport = AuthorizedSession(
            credentials=self._client._credentials
        )
        self._request = None  # type: requests.ResumableUpload

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, *_):
        if exc_type is None:
            self.stop()

    def start(self):
        url = (
            f'https://www.googleapis.com/upload/storage/v1/b/'
            f'{self._bucket.name}/o?uploadType=resumable'
        )
        self._request = requests.ResumableUpload(
            upload_url=url, chunk_size=self._chunk_size
        )
        self._request.initiate(
            transport=self._transport,
            # content_type='application/octet-stream',
            content_type='text/plain',
            stream=self,
            stream_final=False,
            metadata={'name': self._blob.name},
        )

    def stop(self):
        self._request.transmit_next_chunk(self._transport)

    def write(self, data: bytes) -> int:
        data_len = len(data)
        self._buffer_size += data_len
        self._buffer += data
        del data
        while self._buffer_size >= self._chunk_size:
            try:
                self._request.transmit_next_chunk(self._transport)
            except common.InvalidResponse:
                self._request.recover(self._transport)
        return data_len

    def read(self, chunk_size: int) -> bytes:
        # I'm not good with efficient no-copy buffering so if this is
        # wrong or there's a better way to do this let me know! :-)
        to_read = min(chunk_size, self._buffer_size)
        memview = memoryview(self._buffer)
        self._buffer = memview[to_read:].tobytes()
        self._read += to_read
        self._buffer_size -= to_read
        return memview[:to_read].tobytes()

    def tell(self) -> int:
        return self._read
    
    

async def upload_files(local_path_glob, remote_subdir: str, delete_files: bool):
    """Upload files to GCP bucket."""
    client = storage.Client()
    bucket = client.get_bucket('horrible-server')
    for file_ in local_path_glob:
        try:
            log.debug(f"Processing {file_.absolute()}...")
            gs_filename = f"{remote_subdir}/{file_.name}"
            blob = bucket.blob(gs_filename)
            meta = bucket.get_blob(gs_filename)
            if blob.exists() and file_.stat().st_mtime <= meta.updated.timestamp():
                log.info(f"Skipping file {file_.name}...already uploaded")
            else:
                if blob.exists():
                    log.info("Updating file...has changed since last update...")
                log.info(f"Uploading file {file_.absolute()} to {remote_subdir}...")

                with file_.open('rb') as fp_:
                    content = fp_.read()

                if '.zip' not in file_.name:
                    log.info("File not compressed...zipping...")
                    content = gzip.compress(content)
                log.info("Compression complete...uploading...")
                
                start_byte = 0
                end_byte = 0
                i = 0

                with GCSObjectStreamUpload(client=client, bucket_name='horrible-server', blob_name=gs_filename) as s:
                    chunks = len(content) // s._chunk_size
                    log.info('Starting upload...')
                    
                    end_byte += s._chunk_size
                    data = content[start_byte:end_byte]
                    while data:
                        log.info(f'Writing chunk {i} of {chunks}...')
                        s.write(data)
                        
                        start_byte = end_byte
                        end_byte += s._chunk_size
                        i += 1
                        data = content[start_byte:end_byte]                        

                # blob.content_type = "text/plain"
                # blob.content_encoding = "gzip"
                # tries = 0
                # while tries <= 2:
                #     try:
                #         blob.upload_from_string(content)
                #         break
                #     except Exception as err:
                #         log.error(err)
                #         tries += 1

                if delete_files:
                    log.info("File uploaded...deleting...")
                    file_.unlink()
        except Exception as e:
            log.error(e)
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
    parser.add_argument("--env", default='prod', type=str,
                        help="Prod or stg.")
    args = parser.parse_args()

    if args.env != 'prod':
        args.remote_subdir = args.env + "/" + args.remote_subdir
        args.delete = False
    log.info(f"Local path: {args.local_path}...")
    local_glob = args.local_path.glob(args.local_suffix)
    asyncio.run(upload_files(local_glob, args.remote_subdir, args.delete))
