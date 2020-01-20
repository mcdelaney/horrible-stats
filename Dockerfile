FROM horrible_base

COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt

COPY ./static /app/static
COPY ./stats /app/stats
COPY ./templates /app/templates
COPY main.py /app
