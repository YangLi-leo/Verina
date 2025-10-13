/**
 * Init command - Configure API keys
 */

import chalk from 'chalk';
import prompts from 'prompts';
import fs from 'fs-extra';
import path from 'path';
import os from 'os';
import { displaySuccess, displayError, displayInfo, displayWarning } from '../utils/banner.js';
import { getConfigDir, getConfigPath } from '../utils/paths.js';

/**
 * Initialize configuration
 */
export default async function initCommand(options) {
  console.log(chalk.bold('\n🔧 Configure Verina\n'));

  const configPath = getConfigPath();
  let config = {};

  // Load existing config if available
  if (await fs.pathExists(configPath)) {
    if (options.reset) {
      const { confirm } = await prompts({
        type: 'confirm',
        name: 'confirm',
        message: 'Reset all configuration? This will delete your API keys.',
        initial: false
      });

      if (!confirm) {
        console.log(chalk.gray('Configuration reset cancelled.'));
        return;
      }
      config = {};
    } else {
      config = await fs.readJSON(configPath);
      displayInfo('Updating existing configuration...\n');
    }
  }

  console.log(chalk.gray('Configure your API keys for Verina services.\n'));
  console.log(chalk.gray('Get your API keys from:'));
  console.log(chalk.cyan('  • OpenRouter: ') + chalk.blue('https://openrouter.ai/keys'));
  console.log(chalk.cyan('  • Exa: ') + chalk.blue('https://exa.ai/'));
  console.log(chalk.cyan('  • E2B (Optional): ') + chalk.blue('https://e2b.dev/'));
  console.log();

  // Prompt for API keys
  const apiKeys = await prompts([
    {
      type: 'password',
      name: 'openrouter',
      message: 'OpenRouter API Key (Required):',
      initial: config.OPENROUTER_API_KEY || '',
      validate: value => value ? true : 'OpenRouter API key is required'
    },
    {
      type: 'password',
      name: 'exa',
      message: 'Exa API Key (Required):',
      initial: config.EXA_API_KEY || '',
      validate: value => value ? true : 'Exa API key is required'
    },
    {
      type: 'password',
      name: 'e2b',
      message: 'E2B API Key (Optional - for code execution & data analysis):',
      initial: config.E2B_API_KEY || '',
      hint: 'Press Enter to skip - Code execution features will be limited'
    }
  ]);

  // Check if user cancelled
  if (!apiKeys.openrouter || !apiKeys.exa) {
    displayError('Configuration cancelled. API keys are required.');
    process.exit(1);
  }

  // Update config with consistent key names
  config = {
    ...config,
    OPENROUTER_API_KEY: apiKeys.openrouter,
    EXA_API_KEY: apiKeys.exa,
    E2B_API_KEY: apiKeys.e2b || '',
    configuredAt: new Date().toISOString()
  };

  // Advanced settings
  const { advanced } = await prompts({
    type: 'confirm',
    name: 'advanced',
    message: 'Configure advanced settings?',
    initial: false
  });

  if (advanced) {
    const advancedSettings = await prompts([
      {
        type: 'select',
        name: 'defaultModel',
        message: 'Default AI Model:',
        choices: [
          { title: 'GPT-4 Turbo', value: 'openai/gpt-4-turbo-preview' },
          { title: 'GPT-3.5 Turbo', value: 'openai/gpt-3.5-turbo' },
          { title: 'Claude 3 Opus', value: 'anthropic/claude-3-opus' },
          { title: 'Claude 3 Sonnet', value: 'anthropic/claude-3-sonnet' }
        ],
        initial: 0
      },
      {
        type: 'number',
        name: 'frontendPort',
        message: 'Frontend port:',
        initial: config.frontendPort || 3000,
        min: 1024,
        max: 65535
      },
      {
        type: 'number',
        name: 'backendPort',
        message: 'Backend API port:',
        initial: config.backendPort || 8000,
        min: 1024,
        max: 65535
      },
      {
        type: 'confirm',
        name: 'autoOpen',
        message: 'Auto-open browser after starting?',
        initial: config.autoOpen !== false
      }
    ]);

    config = { ...config, ...advancedSettings };
  } else {
    // Set defaults if not configured
    config.defaultModel = config.defaultModel || 'openai/gpt-4-turbo-preview';
    config.frontendPort = config.frontendPort || 3000;
    config.backendPort = config.backendPort || 8000;
    config.autoOpen = config.autoOpen !== false;
  }

  // Save configuration
  try {
    await fs.ensureDir(getConfigDir());
    await fs.writeJSON(configPath, config, { spaces: 2 });

    console.log();
    displaySuccess('Configuration saved successfully!');
    displayInfo(`Config saved to: ${configPath}`);

    // Show warning if E2B key is not configured
    if (!config.E2B_API_KEY) {
      console.log();
      displayWarning('E2B API key not configured');
      console.log(chalk.yellow('  Note: Code execution and data analysis features will be limited.'));
      console.log(chalk.gray('  You can add it later by running:'), chalk.cyan('verina init'));
    }

    console.log('\n' + chalk.bold('✨ Verina is ready to use!\n'));
    console.log(chalk.gray('Start Verina with:'), chalk.cyan('verina'));
    console.log(chalk.gray('Or run:'), chalk.cyan('verina --help'), chalk.gray('for more options'));

  } catch (error) {
    displayError('Failed to save configuration');
    console.error(error);
    process.exit(1);
  }
}