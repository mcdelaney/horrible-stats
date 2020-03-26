FROM horrible_base

ADD static/ /app/static/
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

RUN pip install --no-cache-dir --upgrade tacview-client>=0.1.37

ADD horrible/ /app/horrible/
COPY main.py file_updater.py /app/

WORKDIR "/app"
