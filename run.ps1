param(
    [string]$RepoDir = "$PSScriptRoot"
)

if (!(Test-Path "$RepoDir\.venv")) {
    Write-Host "no venv found in $RepoDir\.venv, to je bída."
    exit 1
}

$venv = "$RepoDir\.venv\Scripts\activate.ps1"

if (!(Test-Path $venv)) {
    Write-Host "cannot activate venv, fakt smutné."
    exit 1
}

# frontend window
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "`"$venv; python -m http.server 5500`""

# backend window
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "`"$venv; uvicorn main:app --reload`""
