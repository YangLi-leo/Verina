/**
 * Start command - Start Verina services
 */

import chalk from 'chalk';
import ora from 'ora';
import { execa } from 'execa';
import open from 'open';
import path from 'path';
import fs from 'fs-extra';
import { displaySuccess, displayError, displayInfo } from '../utils/banner.js';
import { checkPrerequisites } from '../utils/prerequisites.js';
import { getConfigDir, getConfigPath, getDataDir } from '../utils/paths.js';
import { generateDockerCompose } from '../templates/docker-compose.js';

/**
 * Wait for service to be ready
 */
async function waitForService(url, maxRetries = 30, interval = 2000) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return true;
      }
    } catch (error) {
      // Service not ready yet
    }
    await new Promise(resolve => setTimeout(resolve, interval));
  }
  return false;
}

/**
 * Start command handler
 */
export default async function startCommand(options) {
  console.log(chalk.bold('\n🚀 Starting Verina Services\n'));

  // Check prerequisites
  const prereqOk = await checkPrerequisites(true);
  if (!prereqOk) {
    displayError('System prerequisites not met. Run "verina status" for details.');
    process.exit(1);
  }

  const spinner = ora('Preparing to start services...').start();

  try {
    // Get directories
    const configDir = getConfigDir();
    const dataDir = getDataDir();
    const configPath = getConfigPath();

    // Check if config exists
    if (!await fs.pathExists(configPath)) {
      spinner.fail('Configuration not found');
      displayError('Please run "verina init" first to configure API keys.');
      process.exit(1);
    }

    // Create .env file from config.json
    spinner.text = 'Preparing environment...';
    const envPath = path.join(configDir, '.env');
    const config = await fs.readJSON(configPath);

    // Generate .env content from config
    const envContent = `OPENROUTER_API_KEY=${config.OPENROUTER_API_KEY || ''}
EXA_API_KEY=${config.EXA_API_KEY || ''}
E2B_API_KEY=${config.E2B_API_KEY || ''}
DATA_BASE_DIR=/app/data
ENVIRONMENT=production
`;
    await fs.writeFile(envPath, envContent);

    // Generate docker-compose.yml
    spinner.text = 'Generating Docker configuration...';
    const composeContent = generateDockerCompose({
      dataDir,
      envFile: envPath,
      registry: 'ghcr.io',
      owner: 'yangli-leo',
      version: options.version || 'latest'
    });

    const composePath = path.join(configDir, 'docker-compose.yml');
    await fs.writeFile(composePath, composeContent);

    // Pull Docker images from ghcr.io
    spinner.text = 'Pulling Docker images from GitHub Container Registry...';
    const pullArgs = [
      'compose',
      '-f', composePath,
      'pull'
    ];

    await execa('docker', pullArgs, { cwd: configDir });

    // Start services
    spinner.text = 'Starting Docker containers...';
    const startArgs = [
      'compose',
      '-f', composePath,
      'up',
      options.detached ? '-d' : '--abort-on-container-exit'
    ];

    if (options.detached) {
      await execa('docker', startArgs, { cwd: configDir });
      spinner.succeed('Services started in detached mode');

      // Wait for services to be ready
      const frontendUrl = `http://localhost:${options.port || 3000}`;
      const backendUrl = `http://localhost:${options.apiPort || 8000}`;

      spinner.start('Waiting for services to be ready...');

      const frontendReady = await waitForService(frontendUrl);
      const backendReady = await waitForService(`${backendUrl}/health`);

      if (frontendReady && backendReady) {
        spinner.succeed('All services are ready');

        console.log('\n' + chalk.bold('🎉 Verina is running!\n'));
        displaySuccess(`Frontend: ${chalk.cyan(frontendUrl)}`);
        displaySuccess(`Backend API: ${chalk.cyan(backendUrl)}`);
        displaySuccess(`API Docs: ${chalk.cyan(`${backendUrl}/docs`)}`);
        displayInfo(`Data directory: ${chalk.gray(dataDir)}`);

        // Open browser if not disabled
        if (options.open !== false) {
          console.log();
          displayInfo('Opening browser...');
          await open(frontendUrl);
        }

        console.log('\n' + chalk.gray('To stop services, run:'), chalk.cyan('verina stop'));
        console.log(chalk.gray('To view logs, run:'), chalk.cyan('verina logs -f'));
      } else {
        spinner.fail('Services failed to start properly');
        displayError('Please check the logs with: verina logs');
        process.exit(1);
      }
    } else {
      // Run in foreground
      spinner.stop();
      console.log(chalk.gray('\nRunning in foreground mode. Press Ctrl+C to stop.\n'));

      const subprocess = execa('docker', startArgs, {
        cwd: configDir,
        stdio: 'inherit'
      });

      // Handle graceful shutdown
      process.on('SIGINT', async () => {
        console.log('\n' + chalk.yellow('Shutting down services...'));
        subprocess.kill('SIGTERM');
        await execa('docker', ['compose', '-f', composePath, 'down'], {
          cwd: configDir
        });
        displaySuccess('Services stopped');
        process.exit(0);
      });

      await subprocess;
    }
  } catch (error) {
    spinner.fail('Failed to start services');
    displayError(error.message);

    if (error.stderr) {
      console.log(chalk.gray('\nError details:'));
      console.log(error.stderr);
    }

    console.log('\n' + chalk.gray('For more information:'));
    console.log(chalk.cyan('  verina logs'));
    console.log(chalk.cyan('  verina status'));
    process.exit(1);
  }
}
