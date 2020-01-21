from google.cloud import storage


def get_gcs_bucket(bucket="horrible-server"):
    """Initialize a client object and return a bucket."""
    client = storage.Client()
    return client.get_bucket(bucket)
