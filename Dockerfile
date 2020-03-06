FROM horrible_base

ADD horrible/ /app/horrible/
COPY main.py /app/
COPY horrible/data/dcs.db /app/horrible/data/
RUN mkdir -p /app/cache/mission-stats
RUN mkdir -p /app/cache/mission-events
WORKDIR "/app"
