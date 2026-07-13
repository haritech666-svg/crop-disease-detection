#!/bin/bash

echo "=========================================="
echo "   Crop Disease Detector - Build Script   "
echo "=========================================="

# Variables — change these to your DockerHub username
DOCKERHUB_USERNAME="your_dockerhub_username"
IMAGE_NAME="crop-disease-detector"
IMAGE_TAG="v1.0"

echo ""
echo "Step 1: Building Docker image..."
docker build -t $IMAGE_NAME:$IMAGE_TAG .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed!"
    exit 1
fi
echo "✅ Docker image built successfully!"

echo ""
echo "Step 2: Tagging image for DockerHub..."
docker tag $IMAGE_NAME:$IMAGE_TAG $DOCKERHUB_USERNAME/$IMAGE_NAME:$IMAGE_TAG
docker tag $IMAGE_NAME:$IMAGE_TAG $DOCKERHUB_USERNAME/$IMAGE_NAME:latest
echo "✅ Image tagged!"

echo ""
echo "Step 3: Logging into DockerHub..."
docker login

echo ""
echo "Step 4: Pushing to DockerHub..."
docker push $DOCKERHUB_USERNAME/$IMAGE_NAME:$IMAGE_TAG
docker push $DOCKERHUB_USERNAME/$IMAGE_NAME:latest

if [ $? -ne 0 ]; then
    echo "❌ Push to DockerHub failed!"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ BUILD COMPLETE!"
echo "Image: $DOCKERHUB_USERNAME/$IMAGE_NAME:$IMAGE_TAG"
echo "DockerHub: https://hub.docker.com/r/$DOCKERHUB_USERNAME/$IMAGE_NAME"
echo "=========================================="