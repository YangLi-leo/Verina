/**
 * Path utilities
 */

import path from 'path';
import fs from 'fs-extra';
import { fileURLToPath } from 'url';
import os from 'os';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Get project root directory
 */
export async function getProjectRoot() {
  // First check current directory
  let currentPath = process.cwd();

  // Look for docker-compose.yml or verina.config.json
  while (currentPath !== path.parse(currentPath).root) {
    if (await fs.pathExists(path.join(currentPath, 'docker-compose.yml')) ||
        await fs.pathExists(path.join(currentPath, 'docker-compose.yaml')) ||
        await fs.pathExists(path.join(currentPath, 'verina.config.json'))) {
      return currentPath;
    }

    // Check parent directory
    const parentPath = path.dirname(currentPath);
    if (parentPath === currentPath) break;
    currentPath = parentPath;
  }

  // If not found, return current directory
  return process.cwd();
}

/**
 * Find docker-compose file
 */
export async function findDockerCompose(projectRoot) {
  const possiblePaths = [
    path.join(projectRoot, 'docker-compose.yml'),
    path.join(projectRoot, 'docker-compose.yaml'),
    path.join(projectRoot, 'compose.yml'),
    path.join(projectRoot, 'compose.yaml'),
    path.join(projectRoot, 'infrastructure', 'docker-compose.yml'),
    path.join(projectRoot, 'infrastructure', 'docker-compose.yaml')
  ];

  for (const filePath of possiblePaths) {
    if (await fs.pathExists(filePath)) {
      return filePath;
    }
  }

  return null;
}

/**
 * Get Verina config directory
 */
export function getConfigDir() {
  const configDir = path.join(os.homedir(), '.verina');
  fs.ensureDirSync(configDir);
  return configDir;
}

/**
 * Get config file path
 */
export function getConfigPath() {
  return path.join(getConfigDir(), 'config.json');
}

/**
 * Get cache directory
 */
export function getCacheDir() {
  const cacheDir = path.join(getConfigDir(), 'cache');
  fs.ensureDirSync(cacheDir);
  return cacheDir;
}

/**
 * Get logs directory
 */
export function getLogsDir() {
  const logsDir = path.join(getConfigDir(), 'logs');
  fs.ensureDirSync(logsDir);
  return logsDir;
}

/**
 * Get sessions directory
 */
export function getSessionsDir() {
  const sessionsDir = path.join(getConfigDir(), 'sessions');
  fs.ensureDirSync(sessionsDir);
  return sessionsDir;
}

/**
 * Get data directory
 */
export function getDataDir() {
  const dataDir = path.join(getConfigDir(), 'data');
  fs.ensureDirSync(dataDir);
  return dataDir;
}

/**
 * Resolve a path relative to project root
 */
export async function resolveProjectPath(relativePath) {
  const projectRoot = await getProjectRoot();
  return path.join(projectRoot, relativePath);
}

/**
 * Check if running in a Verina project
 */
export async function isVerinaProject() {
  const projectRoot = await getProjectRoot();
  const dockerCompose = await findDockerCompose(projectRoot);
  return dockerCompose !== null;
}