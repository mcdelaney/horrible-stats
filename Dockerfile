FROM horrible_base

COPY ./stats /app/stats
COPY ./templates  /app/templates
COPY main.py /app
