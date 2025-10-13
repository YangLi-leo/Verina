/**
 * Dev command - Start Verina in development mode
 */

import chalk from 'chalk';
import ora from 'ora';
import fs from 'fs-extra';
import path from 'path';
import { execa } from 'execa';
import open from 'open';
import findProcess from 'find-process';
import { displaySuccess, displayError, displayWarning, displayInfo } from '../utils/banner.js';
import { checkPrerequisites } from '../utils/prerequisites.js';

/**
 * Check if a port is in use
 */
async function isPortInUse(port) {
  try {
    const list = await findProcess('port', port);
    return list.length > 0;
  } catch (error) {
    // If find-process fails, assume port is free
    return false;
  }
}

/**
 * Find docker-compose file in project
 */
async function findLocalDockerCompose() {
  const possiblePaths = [
    'infrastructure/docker/docker-compose.yml',
    'infrastructure/docker/docker-compose.yaml',
    'docker-compose.yml',
    'docker-compose.yaml',
    'compose.yml',
    'compose.yaml'
  ];

  for (const filePath of possiblePaths) {
    const fullPath = path.join(process.cwd(), filePath);
    if (await fs.pathExists(fullPath)) {
      return fullPath;
    }
  }

  return null;
}

/**
 * Check if current directory is a Verina project
 */
async function isVerinaProject() {
  // Check for typical Verina project structure
  const indicators = [
    'packages/cli',
    'frontend',
    'backend',
    '.github',
    'infrastructure'
  ];

  for (const indicator of indicators) {
    if (await fs.pathExists(path.join(process.cwd(), indicator))) {
      return true;
    }
  }

  return false;
}

/**
 * Dev command handler
 */
export default async function devCommand(options) {
  console.log(chalk.bold('\n🔧 Starting Verina in Development Mode\n'));

  // Check prerequisites
  const prereqOk = await checkPrerequisites(true);
  if (!prereqOk) {
    displayError('System prerequisites not met. Run "verina status" for details.');
    process.exit(1);
  }

  const spinner = ora('Checking development environment...').start();

  try {
    // Check if this is a Verina project
    const isVerina = await isVerinaProject();
    if (!isVerina) {
      spinner.fail('Not a Verina project');
      console.log();
      displayWarning('Development mode requires the Verina source code.');
      console.log('\n' + chalk.gray('To use development mode:'));
      console.log(chalk.cyan('  1. Clone the Verina repository:'));
      console.log(chalk.gray('     git clone https://github.com/YangLi-leo/Verina.git'));
      console.log(chalk.cyan('  2. Navigate to the project directory:'));
      console.log(chalk.gray('     cd Verina'));
      console.log(chalk.cyan('  3. Run development mode:'));
      console.log(chalk.gray('     verina dev'));
      console.log();
      console.log(chalk.gray('Or use user mode instead:'), chalk.cyan('verina'));
      process.exit(1);
    }

    // Check for local docker-compose file
    const dockerComposePath = await findLocalDockerCompose();

    if (!dockerComposePath) {
      spinner.fail('No docker-compose.yml found');
      console.log();
      displayError('Could not find docker-compose.yml in expected locations');
      displayInfo('Expected locations:');
      displayInfo('  - infrastructure/docker/docker-compose.yml');
      displayInfo('  - docker-compose.yml (project root)');
      process.exit(1);
    }

    spinner.text = 'Checking port availability...';

    // Check if ports are available
    const port3000InUse = await isPortInUse(3000);
    const port8000InUse = await isPortInUse(8000);

    if (port3000InUse) {
      spinner.fail('Port 3000 is already in use');
      displayError('Cannot start frontend - port 3000 is occupied');
      console.log(chalk.gray('\nTo find what\'s using the port:'));
      console.log(chalk.cyan('  lsof -i :3000'));
      console.log(chalk.gray('\nTo kill the process:'));
      console.log(chalk.cyan('  kill -9 $(lsof -t -i:3000)'));
      process.exit(1);
    }

    if (port8000InUse) {
      spinner.fail('Port 8000 is already in use');
      displayError('Cannot start backend - port 8000 is occupied');
      console.log(chalk.gray('\nTo find what\'s using the port:'));
      console.log(chalk.cyan('  lsof -i :8000'));
      console.log(chalk.gray('\nTo kill the process:'));
      console.log(chalk.cyan('  kill -9 $(lsof -t -i:8000)'));
      process.exit(1);
    }

    spinner.succeed('✓ Ports 3000 and 8000 are available');
    spinner.start(`Found docker-compose at: ${dockerComposePath}`);
    spinner.succeed(`Found docker-compose at: ${dockerComposePath}`);
    displayInfo('Using local Docker configuration for development');

    // Check for environment configuration
    spinner.text = 'Checking environment configuration...';
    const envDevPath = path.join(process.cwd(), 'config', '.env.development');
    const envPath = path.join(process.cwd(), '.env');

    let envFileToUse = null;

    if (await fs.pathExists(envDevPath)) {
      envFileToUse = envDevPath;
      spinner.succeed('Environment configuration found');
      displayInfo(`Using development config: ${chalk.cyan('config/.env.development')}`);

      // Check if API keys are configured
      const envContent = await fs.readFile(envDevPath, 'utf-8');
      if (!envContent.includes('OPENROUTER_API_KEY=') || envContent.includes('OPENROUTER_API_KEY=your_')) {
        console.log();
        displayWarning('API keys may not be configured in config/.env.development');
        console.log(chalk.gray('  Get your keys from:'));
        console.log(chalk.blue('  - OpenRouter: https://openrouter.ai/keys'));
        console.log(chalk.blue('  - Exa: https://exa.ai/'));
        console.log(chalk.blue('  - E2B (optional): https://e2b.dev/'));
        console.log();
      }
    } else if (await fs.pathExists(envPath)) {
      envFileToUse = envPath;
      spinner.succeed('Environment configuration found');
      displayInfo(`Using environment file: ${chalk.cyan('.env')}`);
    } else {
      spinner.fail('No environment configuration found');
      displayError('Required environment file not found');
      displayInfo('Expected: config/.env.development or .env');
      console.log();
      console.log(chalk.gray('To create one:'));
      console.log(chalk.cyan('  cp config/.env.example config/.env.development'));
      console.log(chalk.cyan('  # Edit config/.env.development with your API keys'));
      process.exit(1);
    }

    // Build Docker images locally
    console.log();
    spinner.start('Building Docker images from local source...');
    spinner.text = 'Building Docker images (this may take a few minutes)...';

    const buildArgs = [
      'compose',
      '-f', dockerComposePath
    ];

    // Add env file for build context
    if (envFileToUse) {
      buildArgs.push('--env-file', envFileToUse);
    }

    // Add profile for web (frontend + backend)
    buildArgs.push('--profile', 'web');
    buildArgs.push('build');

    if (!options.build) {
      // Skip --no-cache for faster builds unless explicitly requested
      // buildArgs.push('--no-cache');
    }

    if (options.parallel) {
      buildArgs.push('--parallel');
    }

    await execa('docker', buildArgs, {
      cwd: process.cwd(),
      stdio: options.verbose ? 'inherit' : 'pipe'
    });

    spinner.succeed('Docker images built successfully');

    // Start services with the correct env file
    spinner.start('Starting development services...');

    const startArgs = [
      'compose',
      '-f', dockerComposePath
    ];

    // Add env file if found
    if (envFileToUse) {
      startArgs.push('--env-file', envFileToUse);
    }

    // Add profile for web (frontend + backend)
    startArgs.push('--profile', 'web');
    startArgs.push('up');

    if (options.detached) {
      startArgs.push('-d');
    }

    if (options.build) {
      startArgs.push('--build');
    }

    if (options.detached) {
      await execa('docker', startArgs, { cwd: process.cwd() });
      spinner.succeed('Development services started');

      console.log('\n' + chalk.bold('🚀 Verina Development Mode Running!\n'));
      displaySuccess('Frontend: ' + chalk.cyan('http://localhost:3000'));
      displaySuccess('Backend API: ' + chalk.cyan('http://localhost:8000'));
      displaySuccess('API Docs: ' + chalk.cyan('http://localhost:8000/docs'));

      console.log('\n' + chalk.yellow('Development Features:'));
      console.log(chalk.gray('  • Hot reload enabled'));
      console.log(chalk.gray('  • Debug logging active'));
      console.log(chalk.gray('  • Using local source code'));

      if (options.open !== false) {
        console.log();
        displayInfo('Opening browser...');
        await open('http://localhost:3000');
      }

      console.log('\n' + chalk.gray('Useful commands:'));
      console.log(chalk.cyan('  docker compose logs -f') + chalk.gray('     # View logs'));
      console.log(chalk.cyan('  docker compose down') + chalk.gray('        # Stop services'));
      console.log(chalk.cyan('  verina stop') + chalk.gray('                # Stop with verina CLI'));
      console.log(chalk.cyan('  verina dev --build') + chalk.gray('        # Rebuild and start'));
    } else {
      // Run in foreground
      spinner.stop();
      console.log(chalk.gray('\nRunning in foreground mode. Press Ctrl+C to stop.\n'));

      const subprocess = execa('docker', startArgs, {
        cwd: process.cwd(),
        stdio: 'inherit'
      });

      // Handle graceful shutdown
      process.on('SIGINT', async () => {
        console.log('\n' + chalk.yellow('Shutting down development services...'));
        subprocess.kill('SIGTERM');
        await execa('docker', ['compose', '-f', dockerComposePath, '--profile', 'web', 'down'], {
          cwd: process.cwd()
        });
        displaySuccess('Development services stopped');
        process.exit(0);
      });

      await subprocess;
    }
  } catch (error) {
    spinner.fail('Failed to start development mode');
    displayError(error.message);

    if (error.stderr) {
      console.log(chalk.gray('\nError details:'));
      console.log(error.stderr);
    }

    console.log('\n' + chalk.gray('Troubleshooting:'));
    console.log(chalk.cyan('  1.') + chalk.gray(' Ensure Docker Desktop is running'));
    console.log(chalk.cyan('  2.') + chalk.gray(' Check config/.env.development exists and has API keys'));
    console.log(chalk.cyan('  3.') + chalk.gray(' Verify you\'re in the Verina project root'));
    console.log(chalk.cyan('  4.') + chalk.gray(' Run with --verbose for detailed output: verina dev --verbose'));
    console.log(chalk.cyan('  5.') + chalk.gray(' Check logs: docker compose logs'));

    process.exit(1);
  }
}
