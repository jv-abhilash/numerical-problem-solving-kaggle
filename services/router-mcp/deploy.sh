#!/bin/bash
# Deployment script for MCP Router Service

set -e  # Exit on error

echo "========================================="
echo "MCP Router Service Deployment"
echo "========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check prerequisites
echo "Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker found${NC}"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose found${NC}"

# Check NVIDIA Docker runtime
if ! docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
    echo -e "${YELLOW}⚠ Warning: NVIDIA Docker runtime not available or no GPU detected${NC}"
    echo -e "${YELLOW}  The service will run on CPU (slower)${NC}"
else
    echo -e "${GREEN}✓ NVIDIA GPU support available${NC}"
fi

echo ""

# Create .env if not exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file from .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created${NC}"
    echo -e "${YELLOW}  Please edit .env file if you want to configure API key or other settings${NC}"
    echo ""
fi

# Create logs directory
mkdir -p logs
echo -e "${GREEN}✓ Logs directory created${NC}"

echo ""
echo "Building Docker image..."
docker-compose build

echo ""
echo "Starting service..."
docker-compose up -d

echo ""
echo "Waiting for service to be healthy..."
timeout=180  # 3 minutes
elapsed=0
interval=5

while [ $elapsed -lt $timeout ]; do
    if docker-compose ps | grep -q "healthy"; then
        echo -e "${GREEN}✓ Service is healthy and ready!${NC}"
        break
    fi
    echo "Waiting... ($elapsed/$timeout seconds)"
    sleep $interval
    elapsed=$((elapsed + interval))
done

if [ $elapsed -ge $timeout ]; then
    echo -e "${RED}✗ Service failed to become healthy within $timeout seconds${NC}"
    echo ""
    echo "Checking logs:"
    docker-compose logs --tail=50
    exit 1
fi

echo ""
echo "========================================="
echo "Service Status"
echo "========================================="
docker-compose ps

echo ""
echo "========================================="
echo "Service Information"
echo "========================================="
SERVER_IP=$(hostname -I | awk '{print $1}')
echo -e "Service URL:     ${GREEN}http://${SERVER_IP}:7001${NC}"
echo -e "Health Check:    ${GREEN}http://${SERVER_IP}:7001/health${NC}"
echo -e "API Docs:        ${GREEN}http://${SERVER_IP}:7001/docs${NC}"
echo -e "Server Info:     ${GREEN}http://${SERVER_IP}:7001/info${NC}"
echo ""

# Test the service
echo "Testing service..."
response=$(curl -s http://localhost:7001/health)
if echo "$response" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Service test successful${NC}"
    echo "Response: $response"
else
    echo -e "${RED}✗ Service test failed${NC}"
    echo "Response: $response"
fi

echo ""
echo "========================================="
echo "Useful Commands"
echo "========================================="
echo "View logs:        docker-compose logs -f"
echo "Stop service:     docker-compose stop"
echo "Restart service:  docker-compose restart"
echo "Remove service:   docker-compose down"
echo "Remove all:       docker-compose down -v"
echo ""

echo -e "${GREEN}Deployment complete!${NC}"
