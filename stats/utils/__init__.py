from pathlib import Path

from google.cloud import storage
from google.oauth2 import service_account


def get_gcs_bucket(bucket="horrible-server"):
    client = storage.Client()
    return client.get_bucket(bucket)
