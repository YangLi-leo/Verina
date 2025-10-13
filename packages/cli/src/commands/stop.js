/**
 * Stop command - Stop Verina services
 */

import chalk from 'chalk';
import ora from 'ora';
import path from 'path';
import fs from 'fs-extra';
import { execa } from 'execa';
import { displaySuccess, displayError, displayWarning } from '../utils/banner.js';
import { getConfigDir } from '../utils/paths.js';

/**
 * Stop command handler
 */
export default async function stopCommand(options) {
  console.log(chalk.bold('\n🛑 Stopping Verina Services\n'));

  const spinner = ora('Stopping services...').start();

  try {
    // Find all running Verina containers (both User and Dev mode)
    spinner.text = 'Finding Verina containers...';
    const { stdout: allContainers } = await execa('docker', [
      'ps',
      '-a',
      '--filter', 'name=verina',
      '--format', '{{.Names}}'
    ]);

    if (!allContainers.trim()) {
      spinner.succeed('No Verina services are running');
      process.exit(0);
    }

    const containerNames = allContainers.trim().split('\n');
    spinner.text = `Found ${containerNames.length} container(s)...`;

    // Try to stop using User mode docker-compose first
    const configDir = getConfigDir();
    const userComposePath = path.join(configDir, 'docker-compose.yml');

    if (await fs.pathExists(userComposePath)) {
      spinner.text = 'Stopping User mode services...';

      if (options.force) {
        await execa('docker', [
          'compose',
          '-f', userComposePath,
          'down',
          '--volumes',
          '--remove-orphans'
        ], { cwd: configDir }).catch(() => {});
      } else {
        await execa('docker', [
          'compose',
          '-f', userComposePath,
          'stop'
        ], { cwd: configDir }).catch(() => {});
      }
    }

    // Try to stop Dev mode if in project directory
    const devComposePath = path.join(process.cwd(), 'infrastructure', 'docker', 'docker-compose.yml');
    if (await fs.pathExists(devComposePath)) {
      spinner.text = 'Stopping Dev mode services...';

      if (options.force) {
        await execa('docker', [
          'compose',
          '-f', devComposePath,
          'down',
          '--volumes'
        ], { cwd: process.cwd() }).catch(() => {});
      } else {
        await execa('docker', [
          'compose',
          '-f', devComposePath,
          'stop'
        ], { cwd: process.cwd() }).catch(() => {});
      }
    }

    // Fallback: Stop any remaining Verina containers directly
    spinner.text = 'Stopping remaining containers...';
    const { stdout: remainingContainers } = await execa('docker', [
      'ps',
      '-q',
      '--filter', 'name=verina'
    ]);

    if (remainingContainers.trim()) {
      const ids = remainingContainers.trim().split('\n');
      await execa('docker', ['stop', ...ids]);

      if (options.force) {
        await execa('docker', ['rm', '-f', ...ids]);
      }
    }

    if (options.force) {
      spinner.succeed('All Verina services stopped and removed');
      displaySuccess('Containers and volumes cleaned up');
    } else {
      spinner.succeed('All Verina services stopped');
      displaySuccess('Containers preserved. Use --force to remove them.');
    }

    console.log('\n' + chalk.gray('To restart services, run:'), chalk.cyan('verina'));

  } catch (error) {
    spinner.fail('Failed to stop services');
    displayError(error.message);

    if (error.stderr) {
      console.log(chalk.gray('\nError details:'));
      console.log(error.stderr);
    }

    // Suggest force stop
    if (!options.force) {
      console.log('\n' + chalk.yellow('Try force stopping with:'), chalk.cyan('verina stop --force'));
    }

    process.exit(1);
  }
}