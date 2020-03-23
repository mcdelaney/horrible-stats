FROM horrible_base

ADD horrible/ /app/horrible/
COPY main.py /app/

WORKDIR "/app"
