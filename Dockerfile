FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7-2020-03-01

COPY requirements.txt /tmp/

RUN pip install --no-cache-dir --user -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ADD static/mesh/ /app/static/mesh
ADD static/textures/ /app/static/textures
ADD static/images/ /app/static/images/
ADD static/css/ /app/static/css/
COPY static/index.html static/main-bundle.js /app/static/

ADD horrible/ /app/horrible/
COPY main.py prestart.sh file_updater.py /app/
