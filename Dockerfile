FROM horrible_base

ADD horrible/ /app/horrible/
COPY main.py /app/
RUN mkdir -p /app/cache/mission-stats
WORKDIR "/app"
