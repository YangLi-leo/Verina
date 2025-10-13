/**
 * Banner display utility
 */

import chalk from 'chalk';
import figlet from 'figlet';
import gradient from 'gradient-string';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);
const packageJson = require('../../package.json');

export function displayBanner() {
  const art = figlet.textSync('Verina', { font: 'ANSI Shadow' });

  console.log();
  // 红→黄→绿渐变（亮色版）
  console.log(gradient(['#FF5555', '#FFFF55', '#55FF55']).multiline(art));
  console.log();
  console.log(chalk.yellow('    🔭  ') + chalk.white('Intelligent Search Engine'));
  console.log(chalk.gray(`        v${packageJson.version}`));
  console.log();
}

export function displayWelcome() {
  console.log(chalk.gray('→ Type'), chalk.cyan('verina --help'), chalk.gray('for available commands'));
  console.log();
}

export function displaySuccess(message) {
  console.log(chalk.green('✓'), chalk.white(message));
}

export function displayError(message) {
  console.log(chalk.red('✗'), chalk.white(message));
}

export function displayInfo(message) {
  console.log(chalk.blue('ℹ'), chalk.white(message));
}

export function displayWarning(message) {
  console.log(chalk.yellow('⚠'), chalk.white(message));
}