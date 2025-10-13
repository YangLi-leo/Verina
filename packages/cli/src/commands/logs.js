/**
 * Logs command - Show logs from Verina services
 */

import chalk from 'chalk';
import path from 'path';
import fs from 'fs-extra';
import { execa } from 'execa';
import { displayError, displayInfo, displayWarning } from '../utils/banner.js';
import { getConfigDir } from '../utils/paths.js';

/**
 * Logs command handler
 */
export default async function logsCommand(service, options) {
  console.log(chalk.bold('\n📜 Verina Service Logs\n'));

  try {
    // Get config directory
    const configDir = getConfigDir();
    const dockerComposePath = path.join(configDir, 'docker-compose.yml');

    if (!await fs.pathExists(dockerComposePath)) {
      displayWarning('No Verina configuration found');
      displayError('Please start Verina first with: verina start');
      process.exit(1);
    }

    // Build docker-compose logs command
    const args = ['compose', '-f', dockerComposePath, 'logs'];

    // Add lines limit
    if (options.lines) {
      args.push('--tail', options.lines);
    }

    // Add since filter
    if (options.since) {
      args.push('--since', options.since);
    }

    // Add until filter
    if (options.until) {
      args.push('--until', options.until);
    }

    // Add follow flag
    if (options.follow) {
      args.push('-f');
    }

    // Add specific service if provided
    if (service) {
      args.push(service);
      displayInfo(`Showing logs for service: ${chalk.cyan(service)}`);
    } else {
      displayInfo('Showing logs for all services');
    }

    if (options.follow) {
      console.log(chalk.gray('\nFollowing logs (Ctrl+C to stop)...\n'));
    } else {
      console.log();
    }

    // Execute docker-compose logs
    const subprocess = execa('docker', args, {
      cwd: configDir,
      stdio: 'inherit'
    });

    // Handle graceful shutdown for follow mode
    if (options.follow) {
      process.on('SIGINT', () => {
        subprocess.kill('SIGTERM');
        console.log('\n' + chalk.gray('Stopped following logs'));
        process.exit(0);
      });
    }

    await subprocess;

    if (!options.follow) {
      console.log('\n' + chalk.gray('To follow logs in real-time, use:'), chalk.cyan('verina logs -f'));
    }

  } catch (error) {
    displayError('Failed to retrieve logs');

    if (error.message.includes('no such service')) {
      displayError(`Service "${service}" not found`);
      console.log('\n' + chalk.gray('Available services:'));
      console.log(chalk.cyan('  - frontend'));
      console.log(chalk.cyan('  - backend'));
      console.log(chalk.cyan('  - database'));
    } else {
      displayError(error.message);
    }

    process.exit(1);
  }
}