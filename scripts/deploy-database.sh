#!/usr/bin/env bash

IMAGE_NAME="horrible_stats_db"
GCP_PROJECT_ID="dcs-analytics-257714"

echo "Building and deploying $IMAGE_NAME..."

echo "Building new image..."
docker build -t gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:latest database/

echo "Pushing latest image to GCR..."
docker push gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:latest

kubectl apply -f deployment_db.yaml
kubectl apply -f service.yaml
