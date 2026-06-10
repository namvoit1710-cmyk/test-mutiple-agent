#!/usr/bin/env bash
# build-all.sh — Build base image and all agent images
# Build context is always agents/ so Dockerfiles can COPY _shared/ and <agent>/ siblings.
set -euo pipefail

echo "==> Building base image..."
docker build -t opencode-base:latest agents/base/

for agent in planner be-engineer fe-engineer reviewer qc-engineer; do
  echo "==> Building agent: $agent"
  docker build \
    -f "agents/${agent}/Dockerfile" \
    -t "opencode-${agent}:latest" \
    agents/
done


# ---------------------------------------------------------------------------
# Run an agent manually for testing
#
#   docker run --rm \
#     --env-file .env \
#     --network opencode-agents_agents \
#     -e PROMPT="Read app/docs/spec/requirement.md and produce app/docs/plan/requirement.md." \
#     -v /absolute/path/to/worktree:/workspace \
#     opencode-planner:latest
#
# Replace opencode-planner with any agent image (opencode-be-engineer, etc.)
# and adjust PROMPT and the worktree volume mount to suit your test case.
# ---------------------------------------------------------------------------
