FROM horrible_base

ADD horrible/ /app/horrible/
COPY main.py /app/
COPY horrible/data/dcs.db /app/horrible/data/

WORKDIR "/app"
