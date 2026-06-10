#!/usr/bin/env pwsh
# test-planner.ps1 — Test the planner agent with opencode
$ErrorActionPreference = "Stop"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Testing Planner Agent with OpenCode" -ForegroundColor Cyan
Write-Host "======================================`n" -ForegroundColor Cyan

# Determine workspace root (go up 3 levels from agents/planner/test/)
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$WORKSPACE = (Resolve-Path (Join-Path $SCRIPT_DIR "../../..")).Path
Write-Host "Workspace: $WORKSPACE`n" -ForegroundColor Gray

# Parse agent configuration files
$AGENT_MD = Join-Path $WORKSPACE "agents/planner/AGENT.md"
$PLANNER_MD = Join-Path $WORKSPACE "agents/planner/planner.md"

# Extract spec and plan paths from planner.md
Write-Host "Reading agent configuration..." -ForegroundColor Yellow
if (Test-Path $PLANNER_MD) {
    $plannerContent = Get-Content $PLANNER_MD -Raw
    
    # Extract from frontmatter description
    if ($plannerContent -match 'description:.*app/docs/spec/<name>\.md.*app/docs/plan/<name>\.md') {
        $SPEC_DIR = "app/docs/spec"
        $PLAN_DIR = "app/docs/plan"
    } else {
        $SPEC_DIR = "app/docs/spec"
        $PLAN_DIR = "app/docs/plan"
    }
    Write-Host "  ✓ Spec directory: $SPEC_DIR" -ForegroundColor Green
    Write-Host "  ✓ Plan directory: $PLAN_DIR`n" -ForegroundColor Green
} else {
    Write-Host "  ⚠ planner.md not found, using defaults`n" -ForegroundColor Yellow
    $SPEC_DIR = "app/docs/spec"
    $PLAN_DIR = "app/docs/plan"
}

# Display agent rules and expectations
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Planner Agent Rules & Expectations" -ForegroundColor Cyan
Write-Host "======================================`n" -ForegroundColor Cyan

if (Test-Path $AGENT_MD) {
    Write-Host "Signal Protocol:" -ForegroundColor Yellow
    Write-Host "  • Must emit 'PLAN_COMPLETE' after successful generation" -ForegroundColor White
    Write-Host "  • No PLAN_COMPLETE = spec missing, empty, or cannot decompose`n" -ForegroundColor White
}

if (Test-Path $PLANNER_MD) {
    $plannerContent = Get-Content $PLANNER_MD -Raw
    
    Write-Host "Path Boundaries:" -ForegroundColor Yellow
    Write-Host "  • CAN WRITE: $PLAN_DIR/*.md" -ForegroundColor Green
    Write-Host "  • FORBIDDEN: app/fe/, app/be/, src/, tests/, .pipeline-state.json`n" -ForegroundColor Red
    
    Write-Host "Planning Requirements:" -ForegroundColor Yellow
    Write-Host "  • Split tasks to smallest unit (1 action per step)" -ForegroundColor White
    Write-Host "  • Identify dependencies and risks" -ForegroundColor White
    Write-Host "  • Consider edge cases and error scenarios" -ForegroundColor White
    
    # Extract model info
    if ($plannerContent -match 'model:\s*(.+)') {
        Write-Host "  • Model: $($Matches[1])" -ForegroundColor White
    }
    if ($plannerContent -match 'temperature:\s*(.+)') {
        Write-Host "  • Temperature: $($Matches[1])`n" -ForegroundColor White
    }
}

# List available spec files
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Available Spec Files" -ForegroundColor Cyan
Write-Host "======================================`n" -ForegroundColor Cyan

$specPath = Join-Path $WORKSPACE $SPEC_DIR
$specFiles = Get-ChildItem -Path $specPath -Filter "*.md" -ErrorAction SilentlyContinue
if ($specFiles) {
    $specFiles | ForEach-Object { 
        Write-Host "  • $($_.Name)" -ForegroundColor Cyan
    }
    Write-Host ""
} else {
    Write-Host "  ⚠ No spec files found in $SPEC_DIR`n" -ForegroundColor Yellow
}

# Ask user for spec file name
Write-Host "======================================" -ForegroundColor Cyan
$userInput = Read-Host "Enter spec file name (without .md, or press Enter for 'hello-api')"

# Use default if empty
if ([string]::IsNullOrWhiteSpace($userInput)) {
    $SPEC_FILE = "hello-api.md"
    Write-Host "Using default: $SPEC_FILE" -ForegroundColor Gray
} else {
    # Add .md extension if not provided
    if (-not $userInput.EndsWith(".md")) {
        $SPEC_FILE = "$userInput.md"
    } else {
        $SPEC_FILE = $userInput
    }
}

$SPEC_PATH = "$SPEC_DIR/$SPEC_FILE"
$PLAN_PATH = "$PLAN_DIR/$SPEC_FILE"

Write-Host "`nConfiguration:" -ForegroundColor Yellow
Write-Host "  • Spec: $SPEC_PATH" -ForegroundColor White
Write-Host "  • Plan: $PLAN_PATH`n" -ForegroundColor White

# Step 1: Build base and planner images
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "[1/4] Building Docker images..." -ForegroundColor Yellow
Write-Host "======================================`n" -ForegroundColor Cyan
Write-Host "      → Building base image..." -ForegroundColor Gray
Push-Location $WORKSPACE
docker build -t opencode-base:latest agents/base/ -q

Write-Host "      → Building planner image..." -ForegroundColor Gray
docker build -f agents/planner/Dockerfile -t opencode-planner:latest agents/ -q
Pop-Location

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Docker build failed" -ForegroundColor Red
    exit 1
}
Write-Host "      ✓ Images built successfully`n" -ForegroundColor Green

# Step 2: Verify spec file exists
Write-Host "[2/4] Checking spec file..." -ForegroundColor Yellow
$fullSpecPath = Join-Path $WORKSPACE $SPEC_PATH
if (-not (Test-Path $fullSpecPath)) {
    Write-Host "✗ Spec file not found: $fullSpecPath" -ForegroundColor Red
    exit 1
}
Write-Host "      ✓ Found spec: $SPEC_PATH`n" -ForegroundColor Green

# Step 3: Clean previous plan output
Write-Host "[3/4] Cleaning previous plan output..." -ForegroundColor Yellow
$fullPlanPath = Join-Path $WORKSPACE $PLAN_PATH
if (Test-Path $fullPlanPath) {
    Remove-Item $fullPlanPath
    Write-Host "      ✓ Removed old plan file`n" -ForegroundColor Green
} else {
    Write-Host "      ✓ No previous plan file`n" -ForegroundColor Green
}

# Step 4: Run planner agent
Write-Host "[4/4] Running planner agent..." -ForegroundColor Yellow
Write-Host "      → Workspace: $WORKSPACE" -ForegroundColor Gray
Write-Host "      → Spec: $SPEC_PATH" -ForegroundColor Gray
Write-Host "      → Output: $PLAN_PATH" -ForegroundColor Gray
Write-Host "      → Waiting for PLAN_COMPLETE signal...`n" -ForegroundColor Gray

$env:PROMPT = "Read app/docs/spec/$SPEC_FILE and produce app/docs/plan/$SPEC_FILE."

# Create knowledge volume structure
$KNOWLEDGE_DIR = Join-Path $WORKSPACE "agents/planner"

# Run the container
docker run --rm `
    -v "${WORKSPACE}:/workspace" `
    -v "${KNOWLEDGE_DIR}:/opencode-knowledge" `
    -e PROMPT=$env:PROMPT `
    -e GOOGLE_API_KEY=$env:GOOGLE_API_KEY `
    opencode-planner:latest

$exitCode = $LASTEXITCODE

Write-Host "`n======================================" -ForegroundColor Cyan
Write-Host "Verification Results" -ForegroundColor Cyan
Write-Host "======================================`n" -ForegroundColor Cyan

# Step 5: Verify results
if ($exitCode -eq 0 -and (Test-Path $fullPlanPath)) {
    Write-Host "✓ SUCCESS: Plan generated" -ForegroundColor Green
    Write-Host "✓ Exit code: 0" -ForegroundColor Green
    Write-Host "✓ Plan file exists: $PLAN_PATH`n" -ForegroundColor Green
    
    # Check for PLAN_COMPLETE signal
    $output = Get-Content $fullPlanPath -Raw
    if ($output -match 'PLAN_COMPLETE') {
        Write-Host "✓ PLAN_COMPLETE signal found`n" -ForegroundColor Green
    } else {
        Write-Host "⚠ PLAN_COMPLETE signal NOT found (agent may have failed)`n" -ForegroundColor Yellow
    }
    
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host "Generated Plan Contents" -ForegroundColor Cyan
    Write-Host "======================================`n" -ForegroundColor Cyan
    Get-Content $fullPlanPath | Write-Host
    Write-Host "`n======================================" -ForegroundColor Cyan
    
    # Check for plan structure
    $content = Get-Content $fullPlanPath -Raw
    $hasStructure = $false
    $structureElements = @()
    
    if ($content -match "## Tasks") {
        $structureElements += "Tasks section"
        $hasStructure = $true
    }
    if ($content -match "## Implementation") {
        $structureElements += "Implementation section"
        $hasStructure = $true
    }
    if ($content -match "## Steps") {
        $structureElements += "Steps section"
        $hasStructure = $true
    }
    if ($content -match "## Overview|## Goal|## Requirements") {
        $structureElements += "Overview/Requirements"
        $hasStructure = $true
    }
    
    if ($hasStructure) {
        Write-Host "`n✓ Plan structure validated:" -ForegroundColor Green
        $structureElements | ForEach-Object { Write-Host "  • $_" -ForegroundColor White }
    } else {
        Write-Host "`n⚠ Plan may be incomplete (no standard sections found)" -ForegroundColor Yellow
    }
    
} elseif (Test-Path $fullPlanPath) {
    Write-Host "⚠ WARNING: Plan created but exit code non-zero ($exitCode)" -ForegroundColor Yellow
    Write-Host "======================================`n" -ForegroundColor Cyan
    Get-Content $fullPlanPath | Write-Host
} else {
    Write-Host "✗ FAILED: No plan generated" -ForegroundColor Red
    Write-Host "✗ Exit code: $exitCode" -ForegroundColor Red
    Write-Host "✗ Plan file missing: $PLAN_PATH" -ForegroundColor Red
    Write-Host "`nCheck the output above for errors" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n======================================" -ForegroundColor Cyan
Write-Host "Test Complete!" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
