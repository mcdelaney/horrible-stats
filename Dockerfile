FROM horrible_base

COPY stats templates /app/
# COPY ./templates /app/templates
COPY main.py /app
