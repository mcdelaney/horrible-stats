FROM horrible_base

ADD horrible/ /app/horrible/
COPY main.py /app/
COPY file_updater.py /app/

WORKDIR "/app"
