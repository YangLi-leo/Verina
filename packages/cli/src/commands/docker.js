/**
 * Docker command - Manage Docker containers and images
 */

import chalk from 'chalk';
import ora from 'ora';
import { execa } from 'execa';
import path from 'path';
import fs from 'fs-extra';
import { displaySuccess, displayError, displayInfo, displayWarning } from '../utils/banner.js';
import { getConfigDir } from '../utils/paths.js';

/**
 * Pull latest images from GitHub Container Registry
 */
async function pullImages() {
  const spinner = ora('Pulling latest images from GitHub Container Registry...').start();

  try {
    const images = [
      'ghcr.io/yangli-leo/verina-frontend:latest',
      'ghcr.io/yangli-leo/verina-backend:latest'
    ];

    for (const image of images) {
      spinner.text = `Pulling ${image}...`;
      await execa('docker', ['pull', image]);
    }

    spinner.succeed('Successfully pulled latest images');
    displaySuccess('Images are up to date');
  } catch (error) {
    spinner.fail('Failed to pull images');
    throw error;
  }
}

/**
 * Clean up Docker resources
 */
async function cleanDocker() {
  const spinner = ora('Cleaning Docker resources...').start();

  try {
    // Stop Verina containers
    spinner.text = 'Stopping Verina containers...';
    const configDir = getConfigDir();
    const composePath = path.join(configDir, 'docker-compose.yml');

    if (await fs.pathExists(composePath)) {
      await execa('docker', ['compose', '-f', composePath, 'down', '--volumes'], {
        cwd: configDir
      }).catch(() => {});
    }

    // Remove Verina containers
    spinner.text = 'Removing stopped containers...';
    const { stdout: containers } = await execa('docker', [
      'ps', '-a', '--filter', 'name=verina', '--format', '{{.ID}}'
    ]);

    if (containers) {
      const containerIds = containers.split('\n').filter(Boolean);
      if (containerIds.length > 0) {
        await execa('docker', ['rm', '-f', ...containerIds]);
      }
    }

    // Prune unused Docker objects
    spinner.text = 'Pruning unused Docker objects...';
    await execa('docker', ['system', 'prune', '-f']);

    spinner.succeed('Docker cleanup completed');
    displaySuccess('Removed stopped containers and unused objects');

    // Show disk space saved
    const { stdout: spaceInfo } = await execa('docker', ['system', 'df']);
    console.log('\n' + chalk.gray('Docker disk usage:'));
    console.log(spaceInfo);
  } catch (error) {
    spinner.fail('Cleanup failed');
    throw error;
  }
}

/**
 * Build Docker images locally (for development)
 */
async function buildImages() {
  const spinner = ora('Building Docker images...').start();

  try {
    // Check if in a project directory
    const dockerComposePath = path.join(process.cwd(), 'docker-compose.yml');

    if (!await fs.pathExists(dockerComposePath)) {
      spinner.fail('No docker-compose.yml found');
      displayError('This command must be run from a Verina project directory');
      displayInfo('For user mode, images are automatically pulled from GitHub');
      return;
    }

    spinner.text = 'Building images from local Dockerfiles...';
    await execa('docker', ['compose', 'build', '--no-cache'], {
      cwd: process.cwd(),
      stdio: 'inherit'
    });

    spinner.succeed('Images built successfully');
    displaySuccess('Local Docker images are ready');
  } catch (error) {
    spinner.fail('Build failed');
    throw error;
  }
}

/**
 * Show Docker info
 */
async function showInfo() {
  console.log(chalk.bold('\n🐳 Docker Information\n'));

  try {
    // Docker version
    const { stdout: version } = await execa('docker', ['version', '--format', '{{.Server.Version}}']);
    displayInfo(`Docker version: ${version}`);

    // List Verina images
    console.log('\n' + chalk.bold('Verina Images:'));
    const { stdout: images } = await execa('docker', [
      'images', '--filter', 'reference=*verina*', '--format', 'table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}'
    ]);

    if (images) {
      console.log(images);
    } else {
      console.log(chalk.gray('No Verina images found'));
    }

    // List Verina containers
    console.log('\n' + chalk.bold('Verina Containers:'));
    const { stdout: containers } = await execa('docker', [
      'ps', '-a', '--filter', 'name=verina', '--format', 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
    ]);

    if (containers) {
      console.log(containers);
    } else {
      console.log(chalk.gray('No Verina containers found'));
    }

    // Docker compose status
    const configDir = getConfigDir();
    const composePath = path.join(configDir, 'docker-compose.yml');

    if (await fs.pathExists(composePath)) {
      console.log('\n' + chalk.bold('Compose Status:'));
      try {
        const { stdout: composeStatus } = await execa('docker', [
          'compose', '-f', composePath, 'ps', '--format', 'table'
        ], { cwd: configDir });
        console.log(composeStatus || chalk.gray('No services running'));
      } catch {
        console.log(chalk.gray('No services running'));
      }
    }
  } catch (error) {
    displayError('Failed to get Docker info');
    throw error;
  }
}

/**
 * Docker command handler
 */
export async function dockerCommand(action) {
  console.log(chalk.bold('\n🐳 Docker Management\n'));

  try {
    switch (action) {
      case 'pull':
        await pullImages();
        break;

      case 'clean':
      case 'prune':
        await cleanDocker();
        break;

      case 'build':
        await buildImages();
        break;

      case 'info':
      case 'status':
        await showInfo();
        break;

      default:
        displayError(`Unknown action: ${action}`);
        console.log('\n' + chalk.gray('Available actions:'));
        console.log(chalk.cyan('  verina docker pull') + chalk.gray('   - Pull latest images'));
        console.log(chalk.cyan('  verina docker clean') + chalk.gray('  - Clean up Docker resources'));
        console.log(chalk.cyan('  verina docker build') + chalk.gray('  - Build images locally (dev mode)'));
        console.log(chalk.cyan('  verina docker info') + chalk.gray('   - Show Docker information'));
        break;
    }
  } catch (error) {
    displayError(error.message);
    if (error.stderr) {
      console.log(chalk.gray('\nError details:'));
      console.log(error.stderr);
    }
    process.exit(1);
  }
}