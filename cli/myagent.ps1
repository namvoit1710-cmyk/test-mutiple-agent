# myagent.ps1 — OpenCode multi-agent CLI
# Usage: .\myagent.ps1 <command> [args...]

param(
    [Parameter(Position=0)] [string] $Command = "help",
    [Parameter(Position=1)] [string] $Arg1,
    [Parameter(Position=2)] [string] $Arg2,
    [Parameter(Position=3)] [string] $Arg3,
    [Parameter(Position=4)] [string] $Arg4,
    [Parameter(Position=5)] [string] $Arg5
)

$Orch = if ($env:ORCHESTRATOR_URL) { $env:ORCHESTRATOR_URL } else { "http://localhost:8000" }

function Invoke-Post($Body) {
    $response = Invoke-RestMethod -Uri "$Orch/run" -Method Post `
        -ContentType "application/json" -Body $Body
    $response | ConvertTo-Json -Depth 10
}

function Invoke-Get($Path) {
    $response = Invoke-RestMethod -Uri "$Orch$Path" -Method Get
    $response | ConvertTo-Json -Depth 10
}

switch ($Command) {

    "list" {
        Invoke-Get "/agents"
    }

    "health" {
        Invoke-Get "/health"
    }

    "run" {
        # myagent.ps1 run <agent> "<prompt>"
        $agent  = $Arg1
        $prompt = $Arg2
        if (-not $agent -or -not $prompt) {
            Write-Host "Usage: myagent.ps1 run <agent> `"<prompt>`"" -ForegroundColor Red
            exit 1
        }
        $body = @{ agent = $agent; prompt = $prompt } | ConvertTo-Json
        Invoke-Post $body
    }

    "branch" {
        # myagent.ps1 branch <agent> <repo> <base-branch> "<prompt>"
        $agent  = $Arg1
        $repo   = $Arg2
        $base   = $Arg3
        $prompt = $Arg4
        if (-not $agent -or -not $repo -or -not $base -or -not $prompt) {
            Write-Host "Usage: myagent.ps1 branch <agent> <repo> <base-branch> `"<prompt>`"" -ForegroundColor Red
            exit 1
        }
        $body = @{
            agent        = $agent
            prompt       = $prompt
            repo         = $repo
            base_branch  = $base
            create_pr    = $false
        } | ConvertTo-Json
        Invoke-Post $body
    }

    "pr" {
        # myagent.ps1 pr <agent> <repo> <base-branch> "<prompt>" ["pr title"]
        $agent  = $Arg1
        $repo   = $Arg2
        $base   = $Arg3
        $prompt = $Arg4
        $title  = $Arg5
        if (-not $agent -or -not $repo -or -not $base -or -not $prompt) {
            Write-Host "Usage: myagent.ps1 pr <agent> <repo> <base-branch> `"<prompt>`" [`"title`"]" -ForegroundColor Red
            exit 1
        }
        $body = @{
            agent        = $agent
            prompt       = $prompt
            repo         = $repo
            base_branch  = $base
            create_pr    = $true
            pr_title     = if ($title) { $title } else { $null }
        } | ConvertTo-Json
        Invoke-Post $body
    }

    default {
        Write-Host @"
myagent.ps1 — OpenCode multi-agent CLI

  list                                                       list agents
  health                                                     orchestrator health
  run    <agent> "<prompt>"                                  no repo (planner)
  branch <agent> <repo> <base> "<prompt>"                   worktree + push branch
  pr     <agent> <repo> <base> "<prompt>" ["title"]         worktree + push + open PR

Examples:
  .\myagent.ps1 run planner "Design TODO API with auth"

  .\myagent.ps1 pr be-engineer https://github.com/me/proj.git main ``
    "Add /users CRUD endpoint with tests" ``
    "feat(users): add CRUD endpoint"

  .\myagent.ps1 branch fe-engineer https://github.com/me/proj.git main ``
    "Add login form component"

Environment:
  ORCHESTRATOR_URL    default http://localhost:8000
"@ -ForegroundColor Yellow
    }
}
