#!/usr/bin/env bash
echo "Creating registry..."

microk8s.kubectl create namespace horrible-stats
microk8s.kubectl create secret docker-registry "gcr-auth" --docker-server=https://gcr.io --docker-username=_json_key --docker-email=mcdelaney@gmail.com --docker-password="$(cat dcs-storage-gcs.json)"

microk8s.kubectl create secret generic dcs-storage-gcs --from-file dcs-storage-gcs.json

microk8s.kubectl apply -f scripts/gcr-pull-local-svc-acct.yaml

microk8s.kubectl config set-context --current --namespace horrible-stats