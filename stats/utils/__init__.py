from pathlib import Path

from google.cloud import storage
from google.oauth2 import service_account


def get_gcs_bucket(bucket="horrible-server",
                   cred_path="~/dcs-storage-gcs.json"):
    credentials = service_account.Credentials.from_service_account_file(
        Path(cred_path).expanduser())

    client = storage.Client(credentials=credentials,
                            project=credentials.project_id)
    return client.get_bucket(bucket)
