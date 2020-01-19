FROM gcr.io/dcs-analytics-257714/dcs_mapping_base:latest

COPY dcs-storage-gcs.json /app
COPY ./stats /app/stats
COPY main.py /app
