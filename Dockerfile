FROM horrible_base

COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt

COPY ./stats /app/stats
COPY ./static /app/static
COPY ./templates /app/templates
COPY main.py /app
