#!/bin/bash
# Clean Docker containers, volumes, and cached build layers
# Use this to completely reset the development environment

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🧹 Cleaning Verina Docker environment...${NC}"

cd infrastructure/docker

# Stop and remove containers, volumes, and networks
docker compose --profile web down -v

# Remove dangling images
docker image prune -f

echo -e "${GREEN}✅ Docker environment cleaned${NC}"
echo ""
echo "Cache and build artifacts removed. Run ./infrastructure/scripts/dev.sh to restart."
