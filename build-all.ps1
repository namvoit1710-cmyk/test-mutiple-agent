# build-all.ps1 — Build base image and all agent images
# Build context is always agents/ so Dockerfiles can COPY _shared/ and <agent>/ siblings.
$ErrorActionPreference = "Stop"

Write-Host "==> Building base image..." -ForegroundColor Cyan
docker build -t opencode-base:latest agents/base/

$agents = @("planner", "be-engineer", "fe-engineer", "reviewer", "qc-engineer")
foreach ($agent in $agents) {
    Write-Host "==> Building agent: $agent" -ForegroundColor Cyan
    docker build `
        -f "agents/$agent/Dockerfile" `
        -t "opencode-$agent`:latest" `
        agents/
}
