#!/bin/bash
set -e

echo "🚀 Building Sentiment Analysis Lambda package..."

# Create build directory
BUILD_DIR="build"
rm -rf $BUILD_DIR dist
mkdir -p $BUILD_DIR

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt -t $BUILD_DIR

# Copy lambda code
echo "📄 Copying lambda function code..."
cp sentiment_final.py $BUILD_DIR/
cp lambda_handler.py $BUILD_DIR/
cp query_builder.py $BUILD_DIR/
cp websearch.py $BUILD_DIR/
cp video_ingestion.py $BUILD_DIR/
cp tiktok_discovery.py $BUILD_DIR/
cp text_content.py $BUILD_DIR/
cp sentiment_agent.py $BUILD_DIR/

# Create deployment package
echo "🗜️  Creating deployment package..."
cd $BUILD_DIR
zip -r ../dist/sentiment_lambda.zip .
cd ..

# Cleanup
echo "🧹 Cleaning up..."
rm -rf $BUILD_DIR

echo "✅ Done! Deployment package created: dist/sentiment_lambda.zip"