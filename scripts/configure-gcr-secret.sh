#!/usr/bin/env bash
SECRETNAME="gcr-auth"

kubectl create secret docker-registry $SECRETNAME \
  --docker-server=https://gcr.io \
  --docker-username=_json_key \
  --docker-email=mcdelaney@gmail.com \
  --docker-password="$(cat dcs-storage-gcs.json)"


kubectl apply -f scripts/gcr-pull-local-svc-acct.yaml