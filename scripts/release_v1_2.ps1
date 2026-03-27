<#
PowerShell release helper script for Proje_Takip v1.2
This script will:
  - Check git and working tree
  - Create a release branch 'release/v1.2'
  - Stage and commit changes (asks confirmation)
  - Tag the release with 'v1.2'
  - Push branch and tag to remote origin

Usage:
  Open Windows PowerShell in the repository root and run:
    .\scripts\release_v1_2.ps1

This script is interactive and will ask for confirmation before committing and pushing.
#>

set-StrictMode -Version Latest

function Check-GitInstalled {
    $git = Get-Command git -ErrorAction SilentlyContinue
    if (-not $git) { throw 'Git not found in PATH. Install Git and try again.' }
}

function Run-Checks {
    # Ensure we're in the repo root with .git
    if (-not (Test-Path -Path .git -PathType Container)) {
        throw "This script must be run from the repository root where .git folder exists."
    }

    # Show git status
    Write-Host "Git status:" -ForegroundColor Yellow
    git status --porcelain

    # Show untracked files potentially dangerous
    $untracked = git ls-files --others --exclude-standard
    if ($untracked) {
        Write-Host "Untracked files (these won't be committed unless you stage them):" -ForegroundColor Yellow
        $untracked | ForEach-Object { Write-Host "  $_" }
    }

    # Warn if DB or backup files are present in the working folder
    $suspicious = git ls-files | Where-Object { $_ -match '\\.db$' -or $_ -match 'veritabani_yedekleri' }
    if ($suspicious) {
        Write-Host "Warning: There are tracked DB or backup files in the repo:" -ForegroundColor Red
        $suspicious | ForEach-Object { Write-Host "  $_" }
        Write-Host "Please remove or ensure these files are not tracked before releasing." -ForegroundColor Red
        Read-Host "Press ENTER to continue anyway or Ctrl-C to abort"
    }
}

function Stage-And-Commit {
    param (
        [string]$Branch = 'release/v1.2',
        [string]$Message = "Release v1.2: fixes and polish"
    )

    # Create branch
    Write-Host "Switching to new branch: $Branch" -ForegroundColor Cyan
    git checkout -b $Branch

    # Stage changes - interactive by default
    Write-Host "Preparing to stage all changes (tracked+modified) ..." -ForegroundColor Cyan
    git add -A
    Write-Host "Staged changes:" -ForegroundColor Yellow
    git status --porcelain

    $ans = Read-Host "Do you want to continue and commit these changes? (yes/no)"
    if ($ans -ne 'yes') { throw "Release commit aborted by user." }

    git commit -m $Message
    Write-Host "Committed changes on branch $Branch." -ForegroundColor Green
}

function Tag-And-Push {
    param(
        [string]$Branch = 'release/v1.2',
        [string]$Tag = 'v1.2'
    )
    # Tag
    git tag -a $Tag -m "Release $Tag"
    # Push branch & tag
    git push origin $Branch
    git push origin $Tag
    Write-Host "Pushed branch and tag to origin." -ForegroundColor Green
}

try {
    Check-GitInstalled
    Run-Checks
    Stage-And-Commit -Branch 'release/v1.2' -Message 'Release v1.2: fixes and polish - auto-commit by script'
    Tag-And-Push -Branch 'release/v1.2' -Tag 'v1.2'
    Write-Host "Release v1.2 pushed. Create a PR on GitHub if needed." -ForegroundColor Green
} catch {
    Write-Host "Failed: $_" -ForegroundColor Red
    exit 1
}
