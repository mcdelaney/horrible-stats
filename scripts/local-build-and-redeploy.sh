#!/usr/bin/env bash

IMAGE_NAME="horrible_stats"
GCP_PROJECT_ID="dcs-analytics-257714"
TAG=$(git log --pretty=format:'%h' -n 1)

echo "Building and deploying $IMAGE_NAME at hash $TAG..."

echo "Building new image..."
docker build -t gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:latest .

echo "Setting commit hash tag on latest image..."
docker tag gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:latest gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:$TAG

echo "Pushing commit hash image to GCR..."
docker push gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:$TAG

echo "Deploying new image to prod..."
kubectl set image deployment horrible-stats app=gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:$TAG -n horrible-stats

echo "Pushing latest image to GCR..."
docker push gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:latest

# kubectl delete deployment horrible-stats -n horrible-stats
# kubectl apply -f deployment.yaml
