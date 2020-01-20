FROM horrible_base

COPY dcs-storage-gcs.json /app
COPY ./stats /app/stats
COPY main.py /app
