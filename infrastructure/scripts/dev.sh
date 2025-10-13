#!/bin/bash
# Verina Docker Development Environment
# Start all services in Docker containers with hot reload

set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Starting Verina development environment...${NC}"

# Verify prerequisites
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo "Please install Docker Desktop: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not available${NC}"
    exit 1
fi

# Check if running from project root
if [ ! -f "README.md" ] || [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo -e "${RED}Error: Run this script from project root${NC}"
    exit 1
fi

# Check for configuration
if [ ! -f "config/.env.development" ]; then
    echo -e "${YELLOW}Creating config/.env.development from template...${NC}"
    cp .env.example config/.env.development
    echo -e "${YELLOW}⚠️  Please edit config/.env.development with your API keys${NC}"
    echo ""
fi

# Check if ports are available
echo -e "${GREEN}Checking port availability...${NC}"

if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${RED}Error: Port 3000 is already in use${NC}"
    echo "Please stop the service using port 3000:"
    lsof -i :3000 | grep LISTEN
    echo ""
    echo "You can kill it with: kill -9 \$(lsof -t -i:3000)"
    exit 1
fi

if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${RED}Error: Port 8000 is already in use${NC}"
    echo "Please stop the service using port 8000:"
    lsof -i :8000 | grep LISTEN
    echo ""
    echo "You can kill it with: kill -9 \$(lsof -t -i:8000)"
    exit 1
fi

echo -e "${GREEN}✓ Ports 3000 and 8000 are available${NC}"
echo ""

# Start services
echo -e "${GREEN}Starting Docker containers...${NC}"
cd infrastructure/docker

docker compose --profile web up --build

echo -e "${GREEN}✅ Development environment stopped${NC}"
