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
    pip install --no-cache-dir --user --upgrade ./dist/tacview_client-0.1.79-cp37-cp37m-manylinux2014_x86_64.whl && \
    rm -rf /tmp/py-tac-view-client

COPY static/ /app/static
ADD horrible/ /app/horrible/
COPY main.py prestart.sh file_updater.py /app/
