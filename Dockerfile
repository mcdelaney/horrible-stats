FROM horrible_base

ADD horrible/ /app/horrible/
COPY main.py file_updater.py /app/

WORKDIR "/app"
