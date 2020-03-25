FROM horrible_base

ADD static/ /app/static/
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

ADD horrible/ /app/horrible/
COPY main.py file_updater.py /app/

WORKDIR "/app"
