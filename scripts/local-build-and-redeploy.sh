#!/usr/bin/env bash
set -e
npx webpack --config webpack.config.js --mode=development

IMAGE_NAME="horrible_stats"
REPOS_ID="localhost:32000"
TAG=$(date +"%s")

echo "Building $IMAGE_NAME at hash $TAG..."
docker build -t $REPOS_ID/$IMAGE_NAME:latest .

echo "Setting commit hash tag on latest image..."
docker tag $REPOS_ID/$IMAGE_NAME:latest $REPOS_ID/$IMAGE_NAME:$TAG

echo "Pushing commit hash image to GCR..."
docker push $REPOS_ID/$IMAGE_NAME:$TAG

echo "Deploying new image to prod..."
microk8s.kubectl set image deployment stat-updater stat-updater=$REPOS_ID/$IMAGE_NAME:$TAG -n horrible-stats
microk8s.kubectl set image deployment event-updater event-updater=$REPOS_ID/$IMAGE_NAME:$TAG -n horrible-stats
microk8s.kubectl set image deployment tacview-updater tacview-updater=$REPOS_ID/$IMAGE_NAME:$TAG -n horrible-stats
microk8s.kubectl set image deployment app app=$REPOS_ID/$IMAGE_NAME:$TAG -n horrible-stats

echo "Pushing latest image to Repo..."
docker push $REPOS_ID/$IMAGE_NAME:latest > /dev/null 2>&1 &
