#!/usr/bin/env pwsh
# run-agent.ps1 — Run agents using docker-compose with .env support
param(
    [Parameter(Position=0)]
    [ValidateSet('planner', 'fe-engineer', 'reviewer', 'qc-engineer')]
    [string]$Agent = 'planner',
    
    [Parameter(Position=1)]
    [string]$SpecFile = '',
    
    [switch]$Build,
    [switch]$NoBuild
)

$ErrorActionPreference = "Stop"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "OpenCode Agent Runner" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "[ERROR] .env file not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Create .env from .env.example and add your API key" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# Validate .env has API key
$envContent = Get-Content ".env" -Raw
if ($envContent -notmatch 'GOOGLE_GENERATIVE_AI_API_KEY=.+') {
    Write-Host "[ERROR] GOOGLE_GENERATIVE_AI_API_KEY not set in .env" -ForegroundColor Red
    Write-Host ""
    Write-Host "Edit .env and add your API key" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host "Agent: $Agent" -ForegroundColor Yellow
Write-Host ""

# Determine spec directory based on agent
$SPEC_DIR = "app/docs/spec"

# List available spec files if not provided
if ([string]::IsNullOrWhiteSpace($SpecFile)) {
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
    
    Write-Host "======================================" -ForegroundColor Cyan
    $userInput = Read-Host "Enter spec file name (without .md, or press Enter for 'hello-api')"
    
    if ([string]::IsNullOrWhiteSpace($userInput)) {
        $SpecFile = "hello-api.md"
        Write-Host "Using default: $SpecFile" -ForegroundColor Gray
    } else {
        if (-not $userInput.EndsWith(".md")) {
            $SpecFile = "$userInput.md"
        } else {
            $SpecFile = $userInput
        }
    }
    Write-Host ""
}

# Ensure .md extension
if (-not $SpecFile.EndsWith(".md")) {
    $SpecFile = "$SpecFile.md"
}

# Validate spec file exists BEFORE building
$specPath = "$SPEC_DIR/$SpecFile"
if (-not (Test-Path $specPath)) {
    Write-Host "[ERROR] Spec file not found: $specPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Available spec files:" -ForegroundColor Yellow
    Get-ChildItem -Path $SPEC_DIR -Filter "*.md" -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Host "  - $($_.Name)" -ForegroundColor Cyan
    }
    Write-Host ""
    exit 1
}

Write-Host "[OK] Spec file found: $specPath" -ForegroundColor Green
Write-Host ""

# Ask for custom prompt
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Prompt Configuration" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

$defaultPrompt = switch ($Agent) {
    'planner' { "Read the specification from $specPath and write an implementation plan to app/docs/plan/$SpecFile." }
    'fe-engineer' { "Read $specPath and implement in app/fe/src/." }
    'reviewer' { "Review code changes and create report at app/docs/review/$SpecFile." }
    'qc-engineer' { "Read $specPath and create tests in app/tests/." }
}

Write-Host "Default prompt:" -ForegroundColor Yellow
Write-Host "  $defaultPrompt" -ForegroundColor Gray
Write-Host ""

$customPrompt = Read-Host "Enter custom prompt (or press Enter to use default)"

if ([string]::IsNullOrWhiteSpace($customPrompt)) {
    $env:PROMPT = $defaultPrompt
    Write-Host "Using default prompt" -ForegroundColor Gray
} else {
    $env:PROMPT = $customPrompt
    Write-Host "Using custom prompt: $customPrompt" -ForegroundColor Green
}
Write-Host ""

# Build if requested
if ($Build) {
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host "Building $Agent Image" -ForegroundColor Cyan
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host ""
    
    docker-compose build $Agent
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "[ERROR] Build failed" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
    Write-Host "[OK] Image built successfully" -ForegroundColor Green
    Write-Host ""
}

# Determine output path for display
$outputPath = switch ($Agent) {
    'planner' { "app/docs/plan/$SpecFile" }
    'fe-engineer' { "app/fe/src/" }
    'reviewer' { "app/docs/review/$SpecFile" }
    'qc-engineer' { "app/tests/" }
}

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Running $Agent Agent" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Spec: $specPath" -ForegroundColor Gray
Write-Host "  Output: $outputPath" -ForegroundColor Gray
Write-Host "  Prompt: $env:PROMPT" -ForegroundColor Gray
Write-Host ""

# Run the agent
if ($NoBuild) {
    docker-compose run --rm $Agent
} else {
    docker-compose run --rm --build $Agent
}

$exitCode = $LASTEXITCODE

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
if ($exitCode -eq 0) {
    Write-Host "[SUCCESS] Agent completed successfully" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Agent failed with exit code: $exitCode" -ForegroundColor Red
    exit $exitCode
}
Write-Host "======================================" -ForegroundColor Cyan
