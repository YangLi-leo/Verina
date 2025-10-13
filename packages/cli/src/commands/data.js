/**
 * Data command - Manage local data
 */

import chalk from 'chalk';
import fs from 'fs-extra';
import path from 'path';
import os from 'os';
import ora from 'ora';
import { execa } from 'execa';
import { displaySuccess, displayError, displayInfo, displayWarning } from '../utils/banner.js';

/**
 * Get data directory
 */
function getDataDir() {
  return path.join(os.homedir(), '.verina', 'data');
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
 * Data command handler
 */
export default async function dataCommand(options) {
  console.log(chalk.bold('\n💾 Manage Local Data\n'));

  const dataDir = getDataDir();
  await fs.ensureDir(dataDir);

  // List data info
  if (options.list) {
    const spinner = ora('Analyzing data directory...').start();

    try {
      const totalSize = await getDirectorySize(dataDir);
      const files = await fs.readdir(dataDir);

      spinner.stop();
      console.log(chalk.bold('Data Information:\n'));
      console.log(`  📁 Location: ${chalk.cyan(dataDir)}`);
      console.log(`  📊 Total Size: ${chalk.yellow(formatSize(totalSize))}`);
      console.log(`  📄 Items: ${chalk.green(files.length)}`);

      if (files.length > 0) {
        console.log('\n' + chalk.gray('  Contents:'));
        for (const file of files.slice(0, 10)) {
          const filePath = path.join(dataDir, file);
          const stats = await fs.stat(filePath);
          const icon = stats.isDirectory() ? '📁' : '📄';
          console.log(`    ${icon} ${file}`);
        }
        if (files.length > 10) {
          console.log(chalk.gray(`    ... and ${files.length - 10} more items`));
        }
      }
    } catch (error) {
      spinner.fail('Failed to analyze data directory');
      displayError(error.message);
    }
    return;
  }

  // Clean up all data
  if (options.clean) {
    // First show current data size
    const totalSize = await getDirectorySize(dataDir);
    console.log(chalk.yellow(`Current data size: ${formatSize(totalSize)}\n`));

    const { confirm } = await prompts({
      type: 'confirm',
      name: 'confirm',
      message: 'Remove all local data? This action cannot be undone!',
      initial: false
    });

    if (!confirm) {
      console.log(chalk.gray('Cleanup cancelled.'));
      return;
    }

    const spinner = ora('Cleaning up data...').start();

    try {
      // Remove all contents but keep the data directory itself
      const files = await fs.readdir(dataDir);
      for (const file of files) {
        await fs.remove(path.join(dataDir, file));
      }

      spinner.succeed('Cleanup completed');
      displaySuccess('All local data has been removed');
      displayInfo('Data directory is now empty');
    } catch (error) {
      spinner.fail('Cleanup failed');
      displayError(error.message);
    }
    return;
  }

  // Export data
  if (options.export) {
    const exportPath = path.resolve(options.export);
    const spinner = ora(`Exporting data to ${exportPath}...`).start();

    try {
      await fs.ensureDir(exportPath);

      // Create archive name with timestamp
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const archiveName = `verina-data-${timestamp}.tar.gz`;
      const archivePath = path.join(exportPath, archiveName);

      // Create tar.gz archive
      await execa('tar', ['-czf', archivePath, '-C', os.homedir(), '.verina/data']);

      spinner.succeed('Data exported successfully');
      displaySuccess(`Archive created: ${archivePath}`);

      const archiveStats = await fs.stat(archivePath);
      displayInfo(`Archive size: ${formatSize(archiveStats.size)}`);
    } catch (error) {
      spinner.fail('Export failed');
      displayError(error.message);
    }
    return;
  }

  // Import data
  if (options.import) {
    const importPath = path.resolve(options.import);

    if (!await fs.pathExists(importPath)) {
      displayError(`File not found: ${importPath}`);
      return;
    }

    const { confirm } = await prompts({
      type: 'confirm',
      name: 'confirm',
      message: 'Import will overwrite existing data. Continue?',
      initial: false
    });

    if (!confirm) {
      console.log(chalk.gray('Import cancelled.'));
      return;
    }

    const spinner = ora('Importing data...').start();

    try {
      // Backup existing data first
      const backupDir = path.join(dataDir, '..', 'backup');
      await fs.ensureDir(backupDir);
      const backupTimestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const backupPath = path.join(backupDir, `backup-${backupTimestamp}`);

      if (await fs.pathExists(dataDir)) {
        await fs.copy(dataDir, backupPath);
        displayInfo(`Backup created: ${backupPath}`);
      }

      // Extract archive
      await execa('tar', ['-xzf', importPath, '-C', os.homedir()]);

      spinner.succeed('Data imported successfully');
      displaySuccess('Your data has been restored');
    } catch (error) {
      spinner.fail('Import failed');
      displayError(error.message);
    }
    return;
  }

  // Default: Show data summary
  console.log(chalk.bold('Data Summary:\n'));

  const totalSize = await getDirectorySize(dataDir);
  const files = await fs.readdir(dataDir);

  displayInfo(`Location: ${dataDir}`);
  displayInfo(`Total size: ${chalk.yellow(formatSize(totalSize))}`);
  displayInfo(`Total items: ${files.length}`);

  console.log('\n' + chalk.gray('Available commands:'));
  console.log(chalk.cyan('  verina data --list') + chalk.gray('     View detailed info'));
  console.log(chalk.cyan('  verina data --clean') + chalk.gray('    Clean all data'));
  console.log(chalk.cyan('  verina data --export') + chalk.gray('   Export data to archive'));
  console.log(chalk.cyan('  verina data --import') + chalk.gray('   Import data from archive'));
}