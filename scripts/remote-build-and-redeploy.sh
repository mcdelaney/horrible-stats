#!/usr/bin/env bash
set -e
npx webpack --config webpack.config.js --mode=production

IMAGE_NAME="horrible_stats"
GCP_PROJECT_ID="dcs-analytics-257714"
TAG=$(date +"%s")

echo "Building $IMAGE_NAME at hash $TAG..."
docker buildx build -t gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:latest .

echo "Setting commit hash tag on latest image..."
docker tag gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:latest gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:$TAG

echo "Pushing commit hash image to GCR..."
docker push gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:$TAG

echo "Deploying new image to prod..."
kubectl set image deployment stat-updater stat-updater=gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:$TAG -n horrible-stats
kubectl set image deployment event-updater event-updater=gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:$TAG -n horrible-stats
kubectl set image deployment tacview-updater tacview-updater=gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:$TAG -n horrible-stats
kubectl set image deployment app app=gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:$TAG -n horrible-stats

echo "Pushing latest image to GCR..."
docker push gcr.io/$GCP_PROJECT_ID/$IMAGE_NAME:latest > /dev/null 2>&1 &
