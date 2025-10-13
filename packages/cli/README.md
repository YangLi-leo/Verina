# Verina CLI

<div align="center">

**🔭 Intelligent Search Engine - Local-first, Privacy-focused**

Launch AI-powered search and conversation with a single command

[Quick Start](#quick-start) • [Documentation](https://github.com/YangLi-leo/Verina) • [Issues](https://github.com/YangLi-leo/Verina/issues)

</div>

---

## What is Verina?

Verina is an **AI-powered intelligent search engine** that helps you:
- 🔍 **Deep Search** - Understands your questions, not just keywords
- 💬 **Smart Conversations** - Get information through natural dialogue
- 📚 **Workspace** - Saves all your search history and conversations
- 🔒 **Privacy First** - All data stored locally on your machine

**This CLI tool** lets you launch the entire service with just one command - no complex setup required.

---

## Quick Start

### 1️⃣ Install (One-time)

```bash
npm install -g verina
```

### 2️⃣ Configure API Keys (One-time)

```bash
verina init
```

You'll be prompted for:
- **OpenRouter API Key** (Required) - Powers AI conversations → [Get free key](https://openrouter.ai/keys)
- **Exa API Key** (Required) - Powers intelligent search → [Get free key](https://exa.ai/)
- **E2B API Key** (Optional) - Enables code execution → [Get key](https://e2b.dev/)

> 💡 **Tip**: Configure once, use forever. Keys are saved locally.

### 3️⃣ Start Verina

```bash
verina
```

That's it! Your browser will automatically open to `http://localhost:3000`.

### 4️⃣ Stop Verina

```bash
verina stop
```

---

## Requirements

Before installing, make sure you have:

| Software | Version | Purpose | Install |
|----------|---------|---------|---------|
| **Docker Desktop** | Latest | Runs service containers | [Download](https://docs.docker.com/get-docker/) |
| **Node.js** | 18.0.0+ | Runs the CLI tool | [Download](https://nodejs.org/) |

> ⚠️ **Docker Desktop must be running** before you start Verina.

---

## Common Commands

```bash
# Start services (default command)
verina
# or
verina start

# Stop services
verina stop

# Force stop and cleanup
verina stop --force

# Check service status
verina status

# View logs
verina logs
verina logs -f          # Follow logs in real-time

# Manage data
verina data --list      # Show data storage location
verina data --export /path/to/backup   # Export your data
verina data --import /path/to/backup   # Import data

# Update configuration
verina init             # Reconfigure API Keys
verina init --reset     # Reset all settings
```

---

## Data Storage

### 📁 Everything is Local

All your data is stored in the `~/.verina/` directory:

```
~/.verina/
├── config.json              # Your API keys (stored securely)
├── data/                   # All user data
│   ├── chats/             # Chat history
│   │   └── {session_id}/
│   │       ├── chat_history.json
│   │       └── workspace_*/
│   └── searches/          # Search history
├── docker-compose.yml      # Docker config (auto-generated)
└── .env                   # Environment variables (auto-generated)
```

### 🔒 Privacy Guarantee

- ✅ All data stays on your computer
- ✅ Nothing uploaded to the cloud
- ✅ You can export, delete, or backup anytime
- ✅ Stopping services doesn't delete your data

### 💾 Will My Data Persist?

**Yes!** Your data remains intact even if you:
- Stop services (`verina stop`)
- Restart your computer
- Uninstall the CLI tool

As long as `~/.verina/data/` exists, all your history will be automatically loaded next time you start Verina.

---

## FAQ

### Q1: First launch is slow?
**A:** The first launch downloads Docker images (~1-2 GB), taking 5-10 minutes. Subsequent starts take only 10-20 seconds.

### Q2: How do I update to the latest version?
```bash
npm install -g verina@latest
verina stop
verina  # Restart to pull latest images
```

### Q3: "Docker daemon is not running" error?
**A:** Docker Desktop isn't running. Launch Docker Desktop and wait for it to fully start before running `verina`.

### Q4: Port 3000 or 8000 already in use?
**A:** Current version doesn't support custom ports. Please stop other programs using these ports.

### Q5: How do I completely uninstall?
```bash
# 1. Stop services
verina stop --force

# 2. Uninstall CLI
npm uninstall -g verina

# 3. Delete data (optional - removes all history)
rm -rf ~/.verina/

# 4. Remove Docker images (optional)
docker rmi ghcr.io/yangli-leo/verina-backend:latest
docker rmi ghcr.io/yangli-leo/verina-frontend:latest
```

### Q6: Are my API keys safe?
**A:** API keys are stored in `~/.verina/config.json`, accessible only by your user account. Don't share this file.

### Q7: Can I use Verina on multiple computers?
**A:** Yes! Install and configure on each computer. To share history, use `verina data --export` on one machine and `--import` on another.

---

## Troubleshooting

### 🔧 Service Won't Start

```bash
# 1. Check system status
verina status

# 2. View detailed logs
verina logs

# 3. Restart services
verina stop
verina

# 4. Force rebuild
verina stop --force
verina
```

### 🔧 Docker Issues

```bash
# Check if Docker is running
docker ps

# If not working, restart Docker Desktop

# Clean up old containers
verina stop --force
docker system prune -a  # Warning: removes all unused Docker resources
```

### 🔧 Get Help

```bash
# View help
verina --help
verina [command] --help

# Report issues
# Visit https://github.com/YangLi-leo/Verina/issues
```

---

## Developer Mode

Want to contribute to Verina or debug the source code? Use development mode for a seamless experience with hot reload and live debugging.

### Quick Start for Developers

```bash
# 1. Clone the repository
git clone https://github.com/YangLi-leo/Verina.git
cd Verina

# 2. Configure API keys (one-time setup)
cp config/.env.example config/.env.development
# Edit config/.env.development with your API keys

# 3. Start development environment
verina dev
```

That's it! Your browser will open to `http://localhost:3000` with:
- ✅ **Hot Reload** - Frontend and backend auto-reload on code changes
- ✅ **Local Source** - Uses your local code, not Docker Hub images
- ✅ **Live Debugging** - Real-time logs and error messages
- ✅ **Full Stack** - Both frontend and backend running

### Development Features

When you run `verina dev`, it automatically:
- Checks if Docker is running
- Verifies ports 3000 and 8000 are available
- Finds your `docker-compose.yml` in `infrastructure/docker/`
- Loads your API keys from `config/.env.development`
- Builds Docker images from your local source code
- Starts both frontend and backend with hot reload enabled
- Opens your browser to `http://localhost:3000`

### Developing with Hot Reload

**Frontend Development:**
```bash
# Edit any file in frontend/
vim frontend/src/app/page.tsx

# Save → Browser automatically refreshes ✨
```

**Backend Development:**
```bash
# Edit any file in backend/
vim backend/src/routes/search.py

# Save → Backend automatically restarts ✨
```

### Useful Dev Commands

```bash
# Start development (default: foreground with logs)
verina dev

# Start in background
verina dev -d

# Rebuild images (after changing dependencies)
verina dev --build

# Show detailed build output
verina dev --verbose

# Build images in parallel (faster)
verina dev --parallel

# Stop development environment
verina stop
# or
docker compose -f infrastructure/docker/docker-compose.yml --profile web down
```

### Viewing Logs

```bash
# View all logs
docker compose -f infrastructure/docker/docker-compose.yml --profile web logs

# Follow logs in real-time
docker compose -f infrastructure/docker/docker-compose.yml --profile web logs -f

# View specific service logs
docker compose -f infrastructure/docker/docker-compose.yml logs backend
docker compose -f infrastructure/docker/docker-compose.yml logs frontend
```

### Project Structure

```
Verina/
├── config/
│   ├── .env.example           # Template for environment variables
│   └── .env.development       # Your API keys (git-ignored)
├── frontend/                  # Next.js frontend source
│   ├── src/
│   └── package.json
├── backend/                   # FastAPI backend source
│   ├── src/
│   └── requirements.txt
├── infrastructure/
│   ├── docker/
│   │   ├── docker-compose.yml      # Dev environment config
│   │   ├── Dockerfile.frontend     # Frontend container
│   │   └── Dockerfile.backend      # Backend container
│   └── scripts/
│       └── dev.sh                  # Alternative: shell script
└── packages/
    └── cli/                   # Verina CLI (this package)
```

### Troubleshooting Dev Mode

**Port already in use?**
```bash
# Check what's using the port
lsof -i :3000
lsof -i :8000

# Kill the process
kill -9 $(lsof -t -i:3000)
kill -9 $(lsof -t -i:8000)
```

**API keys not working?**
```bash
# Verify your config file exists
cat config/.env.development

# Make sure it has valid keys
OPENROUTER_API_KEY=sk-or-v1-xxxxx
EXA_API_KEY=xxxxx
E2B_API_KEY=xxxxx  # Optional
```

**Docker build fails?**
```bash
# Clean Docker cache and rebuild
docker system prune -a  # Warning: removes all unused images
verina dev --build --verbose
```

**Hot reload not working?**
```bash
# Make sure you're editing files in the correct directories:
# - frontend/ for frontend changes
# - backend/ for backend changes

# Check if containers are running
docker ps | grep verina

# Restart dev environment
verina stop
verina dev
```

### Development Workflow Example

```bash
# Day 1: Initial setup
git clone https://github.com/YangLi-leo/Verina.git
cd Verina
cp config/.env.example config/.env.development
# Edit config/.env.development with your API keys
verina dev  # First build takes 5-10 minutes

# Day 2+: Daily development
cd Verina
verina dev  # Starts in 10-20 seconds

# Make changes
vim frontend/src/app/search/page.tsx
# Browser auto-refreshes ✨

vim backend/src/agents/search_agent.py
# Backend auto-restarts ✨

# View logs
docker compose logs -f backend

# Stop when done
verina stop
```

### Alternative: Using dev.sh

If you prefer shell scripts, you can also use:
```bash
./infrastructure/scripts/dev.sh
```

Note: `dev.sh` only works on Unix-based systems (Mac/Linux). `verina dev` works on all platforms including Windows.

---

## More Resources

- 📖 [Full Documentation](https://github.com/YangLi-leo/Verina) - Architecture, API docs
- 💻 [Source Code](https://github.com/YangLi-leo/Verina) - View implementation
- 🐛 [Issue Tracker](https://github.com/YangLi-leo/Verina/issues) - Report bugs or request features
- 💬 [Discussions](https://github.com/YangLi-leo/Verina/discussions) - Community support

---

## License

Apache-2.0 © Li Yang

---

<div align="center">

**Find it useful? Give it a ⭐ Star!**

[GitHub](https://github.com/YangLi-leo/Verina) • [npm](https://www.npmjs.com/package/verina)

</div>
