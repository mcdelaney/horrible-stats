FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7-2020-03-01

COPY requirements.txt /tmp/

RUN pip install --no-cache-dir --upgrade setuptools wheel poetry pip && \
    pip install --no-cache-dir --user -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    git clone https://github.com/mcdelaney/py-tacview-client /tmp/py-tacview-client && \
    cd /tmp/py-tacview-client/ && \
    python -m poetry install && \
    python -m poetry build && \
    pip install --no-cache-dir --user --upgrade ./dist/tacview_client-0.1.77-cp37-cp37m-manylinux2014_x86_64.whl

COPY static/ /app/static
# ADD static/textures/ /app/static/textures
# ADD static/images/ /app/static/images/
# ADD static/css/ /app/static/css/
COPY static/index.html static/main-bundle.js /app/static/

ADD horrible/ /app/horrible/
COPY main.py prestart.sh file_updater.py /app/
