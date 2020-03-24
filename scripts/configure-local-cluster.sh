#!/usr/bin/env bash

SECRETNAME="gcr-auth"
kubectl create secret docker-registry $SECRETNAME \
  --docker-server=https://gcr.io \
  --docker-username=_json_key \
  --docker-email=mcdelaney@gmail.com \
  --docker-password="$(cat dcs-storage-gcs.json)"

kubectl create secret generic dcs-storage-gcs --from-file dcs-storage-gcs.json

kubectl apply -f scripts/gcr-pull-local-svc-acct.yaml
kubectl create namespace horrible-stats
kubectl config set-context --current --namespace horrible-stats