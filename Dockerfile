FROM horrible_base

ADD horrible/ /app/
RUN mkdir -p /app/cache/mission-stats
WORKDIR "/app"
