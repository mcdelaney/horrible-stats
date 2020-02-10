#!/usr/bin/env bash

docker build -t horrible_stats . && \
  docker run  -d -p 80:80 horrible_stats
