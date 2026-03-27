Param(
    [string]$RepoName = "proje_takip",
    [string]$Owner = "",
    [string]$Visibility = "private"
)

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "gh CLI not installed. Please install from https://cli.github.com/" -ForegroundColor Yellow
    exit 1
}

$ownerPrefix = if ($Owner) { "$Owner/" } else { "" }
gh repo create "${ownerPrefix}$RepoName" --$Visibility --source . --remote origin --push
Write-Host "Repository created and pushed to GitHub (private)." -ForegroundColor Green
