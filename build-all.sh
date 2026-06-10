#!/usr/bin/env bash
# build-all.sh — Build base image, all agent images, and orchestrator
set -euo pipefail

echo "==> Building base image..."
docker build -t opencode-base:latest agents/base/

for agent in planner be-engineer fe-engineer reviewer qc-engineer; do
  echo "==> Building agent: $agent"
  docker build -t "opencode-${agent}:latest" "agents/${agent}/"
done

echo "==> Building orchestrator..."
docker compose build orchestrator

echo ""
echo "Done. Start with:  docker compose up -d"
echo "Then try:          ./cli/myagent list"
