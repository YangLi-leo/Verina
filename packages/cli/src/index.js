#!/usr/bin/env node

/**
 * Verina CLI
 * Intelligent search engine for you
 */

import { Command } from 'commander';
import chalk from 'chalk';
import { createRequire } from 'module';

// Import commands
import startCommand from './commands/start.js';
import stopCommand from './commands/stop.js';
import statusCommand from './commands/status.js';
import logsCommand from './commands/logs.js';
import initCommand from './commands/init.js';
import dataCommand from './commands/data.js';

// Utils
import { displayBanner } from './utils/banner.js';

const require = createRequire(import.meta.url);
const packageJson = require('../package.json');

const program = new Command();

// Display banner
displayBanner();

// Configure CLI
program
  .name('verina')
  .description('Intelligent search engine for you')
  .version(packageJson.version, '-v, --version')
  .helpOption('-h, --help');

// Default action - Start Verina
program
  .action(async () => {
    // Default command: start services
    await startCommand({ detached: true, port: '3000', apiPort: '8000', open: true });
  });

// Init command - Configure API keys
program
  .command('init')
  .description('Configure API keys')
  .option('--reset', 'Reset configuration')
  .action(initCommand);

// Stop command
program
  .command('stop')
  .description('Stop services')
  .option('-f, --force', 'Force stop and remove containers')
  .action(stopCommand);

// Logs command
program
  .command('logs [service]')
  .description('View logs')
  .option('-f, --follow', 'Follow log output')
  .option('-n, --lines <lines>', 'Number of lines to show', '100')
  .action(logsCommand);

// Data command - Manage local data
program
  .command('data')
  .description('Manage local data')
  .option('--list', 'List data directories')
  .option('--clean', 'Clean up old data')
  .option('--export <path>', 'Export data to path')
  .option('--import <path>', 'Import data from path')
  .action(dataCommand);

// Status command
program
  .command('status')
  .description('Check service status')
  .option('--json', 'Output as JSON')
  .action(statusCommand);

// Dev command - Development mode
program
  .command('dev')
  .description('Start in development mode (requires local project)')
  .option('-d, --detached', 'Run in background')
  .option('-b, --build', 'Force rebuild images')
  .option('--no-open', 'Don\'t open browser')
  .option('--verbose', 'Show detailed output')
  .option('--parallel', 'Build images in parallel')
  .action(async (options) => {
    const { default: devCommand } = await import('./commands/dev.js');
    await devCommand(options);
  });

// Docker command - Advanced Docker operations
program
  .command('docker <action>')
  .description('Docker operations (build, pull, clean)')
  .action(async (action) => {
    const { dockerCommand } = await import('./commands/docker.js');
    await dockerCommand(action);
  });

// Help text
program
  .addHelpText('after', `
${chalk.gray('Examples:')}
  ${chalk.cyan('verina')}              Start Verina (default)
  ${chalk.cyan('verina init')}         Configure API keys
  ${chalk.cyan('verina stop')}         Stop services
  ${chalk.cyan('verina logs -f')}      Follow logs
  ${chalk.cyan('verina data --list')} View local data
  ${chalk.cyan('verina status')}       Check service status
  ${chalk.cyan('verina dev')}          Start development mode

${chalk.gray('Documentation:')}
  ${chalk.blue('https://github.com/YangLi-leo/Verina')}
`);

// Parse arguments
program.parse(process.argv);