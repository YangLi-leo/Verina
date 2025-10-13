/**
 * Generate docker-compose configuration for Verina CLI users
 */

/**
 * Generate docker-compose.yml content
 * @param {Object} config - Configuration object
 * @param {string} config.dataDir - Path to data directory
 * @param {string} config.envFile - Path to environment file
 * @param {string} config.registry - Docker registry (default: ghcr.io)
 * @param {string} config.owner - GitHub repository owner
 * @param {string} config.version - Image version (default: latest)
 * @returns {string} docker-compose.yml content
 */
export function generateDockerCompose(config) {
  const {
    dataDir,
    envFile,
    registry = 'ghcr.io',
    owner = 'yangli-leo',
    version = 'latest'
  } = config;

  return `version: '3.8'

services:
  backend:
    image: ${registry}/${owner}/verina-backend:${version}
    container_name: verina-backend
    ports:
      - "8000:8000"
      - "9222:9222"
    volumes:
      - ${dataDir}:/app/data
    env_file:
      - ${envFile}
    environment:
      - DATA_BASE_DIR=/app/data
      - ENVIRONMENT=production
      - PYTHONUNBUFFERED=1
    # Chrome requires increased shared memory and security settings
    shm_size: '2gb'
    security_opt:
      - seccomp:unconfined
    cap_add:
      - SYS_ADMIN
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - verina-network

  frontend:
    image: ${registry}/${owner}/verina-frontend:${version}
    container_name: verina-frontend
    ports:
      - "3000:3000"
    environment:
      - BACKEND_URL=http://backend:8000
      - NEXT_PUBLIC_API_URL=http://localhost:8000
      - NODE_ENV=production
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - verina-network

networks:
  verina-network:
    driver: bridge
    name: verina-network
`;
}
