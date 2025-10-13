/**
 * Prerequisites checker
 */

import { execa } from 'execa';
import chalk from 'chalk';
import ora from 'ora';
import { displayError, displaySuccess, displayWarning } from './banner.js';

/**
 * Check if a command exists
 */
async function commandExists(command) {
  try {
    await execa('which', [command]);
    return true;
  } catch {
    return false;
  }
}

/**
 * Check Docker version
 */
async function checkDockerVersion() {
  try {
    const { stdout } = await execa('docker', ['--version']);
    const versionMatch = stdout.match(/Docker version (\d+)\.(\d+)/);
    if (versionMatch) {
      const major = parseInt(versionMatch[1]);
      const minor = parseInt(versionMatch[2]);
      if (major < 20 || (major === 20 && minor < 10)) {
        return { success: false, message: 'Docker version 20.10.0 or higher required' };
      }
    }
    return { success: true, version: stdout };
  } catch (error) {
    return { success: false, message: 'Failed to check Docker version' };
  }
}

/**
 * Check Docker Compose version
 */
async function checkDockerComposeVersion() {
  try {
    // Try new docker compose command first
    const { stdout } = await execa('docker', ['compose', 'version']);
    return { success: true, version: stdout };
  } catch {
    try {
      // Fallback to old docker-compose command
      const { stdout } = await execa('docker-compose', ['--version']);
      return { success: true, version: stdout, legacy: true };
    } catch {
      return { success: false, message: 'Docker Compose not found' };
    }
  }
}

/**
 * Check if Docker daemon is running
 */
async function checkDockerRunning() {
  try {
    await execa('docker', ['info']);
    return true;
  } catch {
    return false;
  }
}

/**
 * Check all prerequisites
 */
export async function checkPrerequisites(silent = false) {
  if (silent) {
    return await checkSilently();
  }

  const spinner = ora('Checking system prerequisites...').start();
  const results = {
    docker: false,
    dockerCompose: false,
    dockerRunning: false,
    node: false,
    git: false
  };

  // Check Node.js (already running, so it exists)
  results.node = true;
  const nodeVersion = process.version;

  // Check Git
  spinner.text = 'Checking Git...';
  results.git = await commandExists('git');

  // Check Docker
  spinner.text = 'Checking Docker...';
  const dockerCheck = await checkDockerVersion();
  results.docker = dockerCheck.success;

  // Check Docker Compose
  spinner.text = 'Checking Docker Compose...';
  const composeCheck = await checkDockerComposeVersion();
  results.dockerCompose = composeCheck.success;

  // Check if Docker daemon is running
  if (results.docker) {
    spinner.text = 'Checking Docker daemon...';
    results.dockerRunning = await checkDockerRunning();
  }

  spinner.stop();

  // Display results
  console.log(chalk.bold('\n📋 System Prerequisites:\n'));

  if (results.node) {
    displaySuccess(`Node.js ${nodeVersion} installed`);
  } else {
    displayError('Node.js not found');
  }

  if (results.git) {
    displaySuccess('Git installed');
  } else {
    displayWarning('Git not found (optional for version control)');
  }

  if (results.docker) {
    if (dockerCheck.version) {
      displaySuccess(`Docker installed: ${dockerCheck.version.trim()}`);
    } else {
      displaySuccess('Docker installed');
    }
  } else {
    displayError(dockerCheck.message || 'Docker not installed');
  }

  if (results.dockerCompose) {
    if (composeCheck.legacy) {
      displayWarning('Using legacy docker-compose (consider updating Docker)');
    } else {
      displaySuccess('Docker Compose installed');
    }
  } else {
    displayError('Docker Compose not installed');
  }

  if (results.dockerRunning) {
    displaySuccess('Docker daemon is running');
  } else if (results.docker) {
    displayError('Docker daemon is not running. Please start Docker.');
  }

  console.log();

  // Check if all required components are present
  const hasRequirements = results.docker && results.dockerCompose && results.dockerRunning;

  if (!hasRequirements) {
    console.log(chalk.yellow('⚠  Some requirements are missing.\n'));

    if (!results.docker) {
      console.log(chalk.gray('  Install Docker from: https://docs.docker.com/get-docker/'));
    }

    if (!results.dockerRunning && results.docker) {
      console.log(chalk.gray('  Start Docker Desktop or Docker daemon'));
    }

    console.log();
    return false;
  }

  return true;
}

/**
 * Silent check for prerequisites
 */
async function checkSilently() {
  const results = {
    docker: false,
    dockerCompose: false,
    dockerRunning: false
  };

  const dockerCheck = await checkDockerVersion();
  results.docker = dockerCheck.success;

  const composeCheck = await checkDockerComposeVersion();
  results.dockerCompose = composeCheck.success;

  if (results.docker) {
    results.dockerRunning = await checkDockerRunning();
  }

  return results.docker && results.dockerCompose && results.dockerRunning;
}