#!/usr/bin/env bash
echo "Creating registry..."
docker run -d -p 5000:5000 --restart=always --name registry registry:2

SECRETNAME="gcr-auth"
kubectl create secret docker-registry "gcr-auth" --docker-server=https://gcr.io --docker-username=_json_key --docker-email=mcdelaney@gmail.com --docker-password="$(cat dcs-storage-gcs.json)"

kubectl create secret generic dcs-storage-gcs --from-file dcs-storage-gcs.json

kubectl apply -f scripts/gcr-pull-local-svc-acct.yaml
kubectl create namespace horrible-stats
kubectl config set-context --current --namespace horrible-stats