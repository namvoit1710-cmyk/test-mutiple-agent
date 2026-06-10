# OpenCode Agents

Multi-agent system for automated software development using Docker containers.

## Architecture

- **orchestrator** - FastAPI server that manages agent workflows
- **planner** - Designs features and creates task breakdowns
- **be-engineer** - Implements backend code
- **fe-engineer** - Implements frontend code
- **reviewer** - Reviews code for quality and security
- **qc-engineer** - Writes and runs tests

## Quick Start

### 1. Setup Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your keys
# Required:
#   GOOGLE_GENERATIVE_AI_API_KEY=your_key_here
#   GITHUB_TOKEN=your_token_here
```

### 2. Build Images

```bash
# Build all agent images and orchestrator
./build-all.ps1    # Windows
# or
./build-all.sh     # Linux/Mac
```

### 3. Start Orchestrator

```bash
docker compose up -d
```

### 4. Verify

```bash
# Check health
curl http://localhost:8000/health

# List agents
curl http://localhost:8000/agents
```

## API Endpoints

### GET /health
Health check and agent list

**Response:**
```json
{
  "status": "ok",
  "agents": ["planner", "be-engineer", "fe-engineer", "reviewer", "qc-engineer"],
  "mode": "docker"
}
```

### GET /agents
List available agents

### POST /run
Run a single agent

**Request:**
```json
{
  "agent": "be-engineer",
  "prompt": "Add /users endpoint",
  "repo": "https://github.com/user/proj.git",
  "base_branch": "main",
  "create_pr": true,
  "pr_title": "feat: add users endpoint"
}
```

**Note:** `repo` is optional if `DEFAULT_REPO` env var is set. `base_branch` defaults to `"main"` or `DEFAULT_BASE_BRANCH` if set.

**Response:**
```json
{
  "agent": "be-engineer",
  "output": "...",
  "exit_code": 0,
  "branch": "agent/be-engineer/abc123",
  "pr": {
    "number": 42,
    "url": "https://github.com/user/proj/pull/42"
  }
}
```

### POST /pipeline
Run full TDD pipeline (planner → engineers → reviewer → qc)

**Request:**
```json
{
  "requirement_path": "/work/requirement.md",
  "repo": "https://github.com/user/proj.git",
  "base_branch": "main",
  "pr_title": "feat: implement feature X",
  "max_retries": 3
}
```

**Note:** `requirement_path` must be accessible inside the orchestrator container. `repo` is optional if `DEFAULT_REPO` env var is set.

**Workflow:**
1. Planner reads requirement → creates docs/tasks.md
2. For each task:
   - QC writes failing tests
   - Engineers implement (with retries)
   - Reviewer checks code
   - QC verifies tests pass
3. Commit + push + create PR

**Response:**
```json
{
  "status": "complete",
  "branch": "feature/todo-api-abc123",
  "tasks": [
    {"id": "T1", "status": "done", "attempts": 1, "final_result": "GREEN"},
    {"id": "T2", "status": "done", "attempts": 2, "final_result": "GREEN"}
  ],
  "pr": {
    "number": 43,
    "url": "https://github.com/user/proj/pull/43"
  }
}
```

## Environment Variables

| Variable | Description | Default | Mode |
|----------|-------------|---------|------|
| `GOOGLE_GENERATIVE_AI_API_KEY` | Google AI API key (required) | - | Both |
| `GITHUB_TOKEN` | GitHub token for clone/PR operations | - | Both |
| `WORK_ROOT` | Workspace path for repos/worktrees | `/work` | Both |
| `DOCKER_NETWORK` | Network name for agent containers | `opencode-agents_agents` | Docker |
| `DEFAULT_REPO` | Default repo URL (makes `repo` optional in requests) | - | Both |
| `DEFAULT_BASE_BRANCH` | Default base branch | `main` | Both |
| `OPENCODE_MODEL` | Model for agents | `google/gemma-4-31b-it` | Local |
| `OPENCODE_CMD` | Path to opencode binary | `opencode.cmd` | Local |

## Windows Notes

If Docker socket mounting fails on Windows, try:
```yaml
volumes:
  - //var/run/docker.sock:/var/run/docker.sock
```

Or use named pipe:
```yaml
volumes:
  - npipe:////./pipe/docker_engine:/var/run/docker.sock
```

## Development

### Local Mode (No Docker)
```bash
cd orchestrator
pip install -r requirements.txt
python local_server.py
```

### Adding New Agents
1. Create `agents/new-agent/` directory
2. Add `AGENT.md`, `Dockerfile`, `entrypoint.sh`
3. Add to `AGENTS` dict in `orchestrator/server.py`
4. Add to build scripts

## Troubleshooting

**Orchestrator can't spawn agents:**
- Check Docker socket is mounted: `docker exec opencode-orchestrator ls -la /var/run/docker.sock`
- Verify network exists: `docker network ls | grep agents`

**Agent images not found:**
- Build images first: `./build-all.ps1`
- Check: `docker images | grep opencode`

**Permission denied on git operations:**
- Verify `GITHUB_TOKEN` is set in `.env`
- Token needs `repo` scope for private repos

## License

MIT
