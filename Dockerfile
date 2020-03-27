FROM horrible_base

COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt
ADD static/ /app/static/
ADD horrible/ /app/horrible/
COPY main.py prestart.sh file_updater.py /app/

# WORKDIR "/app"
