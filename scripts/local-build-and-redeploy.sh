#!/usr/bin/env bash
IMAGE_NAME="horrible_stats"
GCP_PROJECT_ID="dcs-analytics-257714"

docker build -t gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:latest .
docker push gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:latest
# kubectl delete deployment horrible-stats --namespace horrible-stats
# kubectl apply -f deployment.yaml
