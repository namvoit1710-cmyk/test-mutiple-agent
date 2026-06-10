#!/usr/bin/env pwsh
# run-test-compose.ps1 — Test the planner agent using docker-compose
$ErrorActionPreference = "Stop"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Testing Planner Agent (Docker Compose)" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Determine workspace root (go up 3 levels from agents/planner/test/)
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$WORKSPACE = (Resolve-Path (Join-Path $SCRIPT_DIR "../../..")).Path
Push-Location $WORKSPACE

Write-Host "Workspace: $WORKSPACE" -ForegroundColor Gray
Write-Host ""

# Check if .env exists
$envFile = ".\.env"
if (-not (Test-Path $envFile)) {
    Write-Host "[ERROR] .env file not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please create .env from .env.example and add your API key" -ForegroundColor Yellow
    Write-Host ""
    Pop-Location
    exit 1
}

# Load and validate .env
Write-Host "Loading .env configuration..." -ForegroundColor Yellow
$envContent = Get-Content $envFile -Raw
if ($envContent -notmatch 'GOOGLE_GENERATIVE_AI_API_KEY=.+') {
    Write-Host "[ERROR] GOOGLE_GENERATIVE_AI_API_KEY not set in .env" -ForegroundColor Red
    Write-Host ""
    Write-Host "Edit .env and add your API key:" -ForegroundColor Yellow
    Write-Host "  GOOGLE_GENERATIVE_AI_API_KEY=your-key-here" -ForegroundColor White
    Write-Host ""
    Write-Host "Get your key at: https://aistudio.google.com/app/apikey" -ForegroundColor Gray
    Write-Host ""
    Pop-Location
    exit 1
}
Write-Host "  [OK] .env file loaded" -ForegroundColor Green
Write-Host ""

# Parse agent configuration files
$PLANNER_MD = "agents/planner/planner.md"
if (Test-Path $PLANNER_MD) {
    $plannerContent = Get-Content $PLANNER_MD -Raw
    $SPEC_DIR = "app/docs/spec"
    $PLAN_DIR = "app/docs/plan"
    
    Write-Host "Agent Configuration:" -ForegroundColor Yellow
    if ($plannerContent -match 'model:\s*(.+)') {
        Write-Host "  - Model: $($Matches[1])" -ForegroundColor White
    }
    if ($plannerContent -match 'temperature:\s*(.+)') {
        Write-Host "  - Temperature: $($Matches[1])" -ForegroundColor White
    }
    Write-Host ""
}

# List available spec files
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Available Spec Files" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

$specFiles = Get-ChildItem -Path $SPEC_DIR -Filter "*.md" -ErrorAction SilentlyContinue
if ($specFiles) {
    $specFiles | ForEach-Object { 
        Write-Host "  - $($_.Name)" -ForegroundColor Cyan
    }
    Write-Host ""
} else {
    Write-Host "  [WARN] No spec files found in $SPEC_DIR" -ForegroundColor Yellow
    Write-Host ""
}

# Ask user for spec file name
Write-Host "======================================" -ForegroundColor Cyan
$userInput = Read-Host "Enter spec file name (without .md, or press Enter for 'hello-api')"

if ([string]::IsNullOrWhiteSpace($userInput)) {
    $SPEC_FILE = "hello-api.md"
    Write-Host "Using default: $SPEC_FILE" -ForegroundColor Gray
} else {
    if (-not $userInput.EndsWith(".md")) {
        $SPEC_FILE = "$userInput.md"
    } else {
        $SPEC_FILE = $userInput
    }
}

$SPEC_PATH = "$SPEC_DIR/$SPEC_FILE"
$PLAN_PATH = "$PLAN_DIR/$SPEC_FILE"

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  - Spec: $SPEC_PATH" -ForegroundColor White
Write-Host "  - Plan: $PLAN_PATH" -ForegroundColor White
Write-Host ""

# Verify spec file exists BEFORE building
$fullSpecPath = $SPEC_PATH
if (-not (Test-Path $fullSpecPath)) {
    Write-Host "[ERROR] Spec file not found: $fullSpecPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Available spec files:" -ForegroundColor Yellow
    Get-ChildItem -Path $SPEC_DIR -Filter "*.md" | ForEach-Object {
        Write-Host "  - $($_.Name)" -ForegroundColor Cyan
    }
    Write-Host ""
    Pop-Location
    exit 1
}
Write-Host "[OK] Spec file found: $SPEC_PATH" -ForegroundColor Green
Write-Host ""

# Ask for custom prompt
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Prompt Configuration" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

$defaultPrompt = "Read the specification from $SPEC_PATH and write an implementation plan to $PLAN_PATH."

Write-Host "Default prompt:" -ForegroundColor Yellow
Write-Host "  $defaultPrompt" -ForegroundColor Gray
Write-Host ""

$customPrompt = Read-Host "Enter custom prompt (or press Enter to use default)"

if ([string]::IsNullOrWhiteSpace($customPrompt)) {
    $env:PROMPT = $defaultPrompt
    Write-Host "Using default prompt" -ForegroundColor Gray
} else {
    $env:PROMPT = $customPrompt
    Write-Host "Using custom prompt" -ForegroundColor Green
}
Write-Host ""

# Clean previous plan output
$fullPlanPath = $PLAN_PATH
if (Test-Path $fullPlanPath) {
    Remove-Item $fullPlanPath
    Write-Host "[OK] Removed old plan file" -ForegroundColor Green
    Write-Host ""
}

# Build images using docker-compose
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Building Images (Docker Compose)" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

docker-compose build planner

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Docker build failed" -ForegroundColor Red
    Pop-Location
    exit 1
}
Write-Host ""
Write-Host "[OK] Images built successfully" -ForegroundColor Green
Write-Host ""

# Run planner agent using docker-compose
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Running Planner Agent" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Prompt: $env:PROMPT" -ForegroundColor Gray
Write-Host ""

docker-compose run --rm planner

$exitCode = $LASTEXITCODE

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Verification Results" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Verify results
if ($exitCode -eq 0 -and (Test-Path $fullPlanPath)) {
    Write-Host "[SUCCESS] Plan generated" -ForegroundColor Green
    Write-Host "[OK] Exit code: 0" -ForegroundColor Green
    Write-Host "[OK] Plan file exists: $PLAN_PATH" -ForegroundColor Green
    Write-Host ""
    
    # Check for PLAN_COMPLETE signal
    $output = Get-Content $fullPlanPath -Raw
    if ($output -match 'PLAN_COMPLETE') {
        Write-Host "[OK] PLAN_COMPLETE signal found" -ForegroundColor Green
    } else {
        Write-Host "[WARN] PLAN_COMPLETE signal NOT found" -ForegroundColor Yellow
    }
    Write-Host ""
    
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host "Generated Plan Contents" -ForegroundColor Cyan
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host ""
    Get-Content $fullPlanPath | Write-Host
    Write-Host ""
    Write-Host "======================================" -ForegroundColor Cyan
    
    # Check for plan structure
    $content = Get-Content $fullPlanPath -Raw
    $hasStructure = $false
    $structureElements = @()
    
    if ($content -match "## Tasks") { $structureElements += "Tasks section"; $hasStructure = $true }
    if ($content -match "## Implementation") { $structureElements += "Implementation section"; $hasStructure = $true }
    if ($content -match "## Steps") { $structureElements += "Steps section"; $hasStructure = $true }
    if ($content -match "## Overview|## Goal|## Requirements") { $structureElements += "Overview/Requirements"; $hasStructure = $true }
    
    if ($hasStructure) {
        Write-Host ""
        Write-Host "[OK] Plan structure validated:" -ForegroundColor Green
        $structureElements | ForEach-Object { Write-Host "  - $_" -ForegroundColor White }
    } else {
        Write-Host ""
        Write-Host "[WARN] Plan may be incomplete (no standard sections found)" -ForegroundColor Yellow
    }
    
} elseif (Test-Path $fullPlanPath) {
    Write-Host "[WARN] Plan created but exit code non-zero ($exitCode)" -ForegroundColor Yellow
    Write-Host ""
    Get-Content $fullPlanPath | Write-Host
} else {
    Write-Host "[ERROR] No plan generated" -ForegroundColor Red
    Write-Host "[ERROR] Exit code: $exitCode" -ForegroundColor Red
    Write-Host "[ERROR] Plan file missing: $PLAN_PATH" -ForegroundColor Red
    Write-Host ""
    Pop-Location
    exit 1
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Test Complete!" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

Pop-Location
