#!/bin/bash

# MBTI Service Docker Runner
# This script builds, runs, and tests the MBTI service

set -e

SERVICE_NAME="mbti-service"
PORT="5000"
IMAGE_TAG="$SERVICE_NAME:latest"

echo "🧠 MBTI Service Docker Runner"
echo "================================"

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  build       Build the Docker image"
    echo "  run         Run the service container"
    echo "  test        Test the running service"
    echo "  stop        Stop the service container"
    echo "  restart     Restart the service"
    echo "  logs        Show service logs"
    echo "  clean       Stop and remove container and image"
    echo "  all         Build, run, and test (default)"
    echo ""
}

# Function to build the image
build_image() {
    echo "🔨 Building Docker image..."
    docker build -t $IMAGE_TAG .
    echo "✅ Image built successfully: $IMAGE_TAG"
}

# Function to run the container
run_container() {
    echo "🚀 Starting MBTI service container..."
    
    # Stop existing container if running
    if docker ps -q -f name=$SERVICE_NAME | grep -q .; then
        echo "⚠️  Stopping existing container..."
        docker stop $SERVICE_NAME
        docker rm $SERVICE_NAME
    fi
    
    # Run new container
    docker run -d \
        --name $SERVICE_NAME \
        -p $PORT:5000 \
        --restart unless-stopped \
        $IMAGE_TAG
    
    echo "✅ Service started on port $PORT"
    echo "📡 Service URL: http://localhost:$PORT"
    
    # Wait for service to be ready
    echo "⏳ Waiting for service to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
            echo "✅ Service is ready!"
            return 0
        fi
        sleep 1
        echo -n "."
    done
    
    echo "❌ Service failed to start or is not responding"
    return 1
}

# Function to test the service
test_service() {
    echo "🧪 Testing MBTI service..."
    
    # Check if service is running
    if ! curl -s http://localhost:$PORT/health > /dev/null; then
        echo "❌ Service is not responding at http://localhost:$PORT"
        return 1
    fi
    
    # Run the comprehensive test script
    if [ -f "test_mbti_service.py" ]; then
        python test_mbti_service.py http://localhost:$PORT
    else
        echo "⚠️  Test script not found, running basic curl tests..."
        
        # Basic health check
        echo "Testing health endpoint..."
        curl -s http://localhost:$PORT/health | python -m json.tool
        
        # Basic prediction test
        echo -e "\nTesting prediction endpoint..."
        curl -s -X POST http://localhost:$PORT/predict \
            -H "Content-Type: application/json" \
            -d '{"text": "I love meeting new people and solving complex problems collaboratively."}' \
            | python -m json.tool
    fi
}

# Function to show logs
show_logs() {
    echo "📋 Service logs:"
    docker logs $SERVICE_NAME
}

# Function to stop the service
stop_service() {
    echo "🛑 Stopping MBTI service..."
    if docker ps -q -f name=$SERVICE_NAME | grep -q .; then
        docker stop $SERVICE_NAME
        docker rm $SERVICE_NAME
        echo "✅ Service stopped"
    else
        echo "⚠️  Service is not running"
    fi
}

# Function to clean up everything
clean_all() {
    echo "🧹 Cleaning up..."
    
    # Stop and remove container
    if docker ps -aq -f name=$SERVICE_NAME | grep -q .; then
        docker stop $SERVICE_NAME 2>/dev/null || true
        docker rm $SERVICE_NAME 2>/dev/null || true
    fi
    
    # Remove image
    if docker images -q $IMAGE_TAG | grep -q .; then
        docker rmi $IMAGE_TAG
    fi
    
    echo "✅ Cleanup complete"
}

# Function to restart the service
restart_service() {
    stop_service
    run_container
}

# Main script logic
case "${1:-all}" in
    build)
        build_image
        ;;
    run)
        run_container
        ;;
    test)
        test_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    logs)
        show_logs
        ;;
    clean)
        clean_all
        ;;
    all)
        build_image
        run_container
        test_service
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        echo "❌ Unknown command: $1"
        show_usage
        exit 1
        ;;
esac

echo ""
echo "🎉 Operation completed!" 