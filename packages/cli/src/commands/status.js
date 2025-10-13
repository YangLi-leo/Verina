/**
 * Status command - Show status of Verina services
 */

import chalk from 'chalk';
import ora from 'ora';
import fs from 'fs-extra';
import path from 'path';
import { execa } from 'execa';
import { displaySuccess, displayError, displayWarning, displayInfo } from '../utils/banner.js';
import { getConfigDir, getConfigPath, getDataDir } from '../utils/paths.js';
import { checkPrerequisites } from '../utils/prerequisites.js';

/**
 * Get container status
 */
async function getContainerStatus() {
  try {
    const configDir = getConfigDir();
    const dockerComposePath = path.join(configDir, 'docker-compose.yml');

    if (!await fs.pathExists(dockerComposePath)) {
      return [];
    }

    const { stdout } = await execa('docker', [
      'compose',
      '-f', dockerComposePath,
      'ps',
      '--format', 'json'
    ], { cwd: configDir });

    if (!stdout) return [];

    // Parse JSON output (each line is a JSON object)
    const lines = stdout.trim().split('\n');
    const containers = lines
      .filter(line => line.trim())
      .map(line => {
        try {
          return JSON.parse(line);
        } catch {
          return null;
        }
      })
      .filter(Boolean);

    return containers;
  } catch {
    return [];
  }
}

/**
 * Check service health
 */
async function checkServiceHealth(url, service) {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    const response = await fetch(url, {
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    return {
      service,
      status: response.ok ? 'healthy' : 'unhealthy',
      statusCode: response.status
    };
  } catch (error) {
    return {
      service,
      status: 'unreachable',
      error: error.message
    };
  }
}

/**
 * Get directory size
 */
async function getDirectorySize(dir) {
  if (!await fs.pathExists(dir)) return 0;

  let totalSize = 0;
  const files = await fs.readdir(dir, { withFileTypes: true });

  for (const file of files) {
    const filePath = path.join(dir, file.name);
    if (file.isDirectory()) {
      totalSize += await getDirectorySize(filePath);
    } else {
      const stats = await fs.stat(filePath);
      totalSize += stats.size;
    }
  }

  return totalSize;
}

/**
 * Format file size
 */
function formatSize(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Status command handler
 */
export default async function statusCommand(options) {
  console.log(chalk.bold('\n📊 Verina Services Status\n'));

  const spinner = ora('Checking services...').start();

  try {
    // Check prerequisites
    spinner.text = 'Checking system prerequisites...';
    const prereqOk = await checkPrerequisites(true);

    // Get configuration
    const configPath = getConfigPath();
    const hasConfig = await fs.pathExists(configPath);

    // Get container status
    spinner.text = 'Checking container status...';
    const containers = await getContainerStatus();

    // Get data directory size
    const dataDir = getDataDir();
    const dataSize = await getDirectorySize(dataDir);

    spinner.stop();

    if (options.json) {
      // Output JSON format
      const status = {
        prerequisites: prereqOk,
        configured: hasConfig,
        containers: containers.map(c => ({
          name: c.Name,
          service: c.Service,
          state: c.State,
          status: c.Status
        })),
        dataSize: dataSize
      };

      console.log(JSON.stringify(status, null, 2));
      return;
    }

    // Display status report
    console.log(chalk.bold('System Status:\n'));

    // Prerequisites
    if (prereqOk) {
      displaySuccess('Docker is installed and running');
    } else {
      displayError('Docker prerequisites not met');
      await checkPrerequisites(false);
    }

    // Configuration
    if (hasConfig) {
      displaySuccess('API keys configured');
    } else {
      displayWarning('Not configured - run "verina init" to set up');
    }

    // Data
    displayInfo(`Data directory: ${dataDir}`);
    displayInfo(`Data size: ${formatSize(dataSize)}`);

    // Containers
    if (containers.length === 0) {
      console.log('\n' + chalk.bold('Services:\n'));
      displayWarning('No services running');
      console.log('\n' + chalk.gray('To start services:'), chalk.cyan('verina'));
    } else {
      console.log('\n' + chalk.bold('Running Services:\n'));

      for (const container of containers) {
        const icon = container.State === 'running' ? '✓' : '✗';
        const color = container.State === 'running' ? chalk.green : chalk.red;

        console.log(
          color(icon),
          chalk.white(container.Service?.padEnd(15) || 'unknown'),
          chalk.gray(container.State?.padEnd(10) || ''),
          chalk.dim(container.Status || '')
        );
      }

      // Check health endpoints
      console.log('\n' + chalk.bold('Service Health:\n'));

      const healthChecks = [
        { url: 'http://localhost:3000', service: 'Frontend' },
        { url: 'http://localhost:8000/health', service: 'Backend API' }
      ];

      for (const check of healthChecks) {
        const result = await checkServiceHealth(check.url, check.service);
        const icon = result.status === 'healthy' ? '✓' : '✗';
        const color = result.status === 'healthy' ? chalk.green : chalk.red;

        console.log(
          color(icon),
          chalk.white(check.service.padEnd(15)),
          chalk.gray(result.status)
        );
      }

      console.log('\n' + chalk.gray('To view logs:'), chalk.cyan('verina logs -f'));
      console.log(chalk.gray('To stop services:'), chalk.cyan('verina stop'));
    }

    console.log();

  } catch (error) {
    spinner.fail('Failed to check status');
    displayError(error.message);
    process.exit(1);
  }
}