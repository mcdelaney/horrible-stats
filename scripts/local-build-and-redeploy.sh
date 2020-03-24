#!/usr/bin/env bash

IMAGE_NAME="horrible_stats"
GCP_PROJECT_ID="dcs-analytics-257714"
TAG=$(git log --pretty=format:'%h' -n 1)

echo "Building base image..."
docker build -t horrible_base -f Dockerfile_base .
echo "Building and deploying $IMAGE_NAME at hash $TAG..."

echo "Building new image..."
docker build -t gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:latest .

echo "Setting commit hash tag on latest image..."
docker tag gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:latest gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:$TAG

echo "Pushing commit hash image to GCR..."
docker push gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:$TAG

echo "Deploying new image to prod..."
kubectl apply -f deployment.yaml
kubectl set image deployment stat-updater stat-updater=gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:$TAG -n horrible-stats
kubectl set image deployment event-updater event-updater=gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:$TAG -n horrible-stats
kubectl set image deployment app app=gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:$TAG -n horrible-stats

echo "Pushing latest image to GCR..."
docker push gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:latest

# kubectl delete deployment horrible-stats -n horrible-stats
