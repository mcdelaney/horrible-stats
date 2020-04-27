#!/usr/bin/env bash

IMAGE_NAME="horrible_stats_db"
REPOS="localhost:32000"

echo "Building and deploying $IMAGE_NAME..."

echo "Building new image..."
docker build -t $REPOS/$IMAGE_NAME:latest database/

echo "Pushing latest image to GCR..."
docker push $REPOS/$IMAGE_NAME:latest

microk8s.kubectl apply -f deployment_db.yaml
