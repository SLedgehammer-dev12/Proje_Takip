# create_snapshot.ps1
# Creates a local backup branch and annotated tag for a snapshot of the repository.
# Usage: powershell -ExecutionPolicy Bypass ./scripts/create_snapshot.ps1

param(
    [switch]$PushToRemote,
    [string]$RemoteName = 'origin'
)

$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$branch = "backup/manual-$ts"
$tag = "pre-change-manual-$ts"

Write-Host "Creating snapshot branch: $branch"

# Create new branch from current HEAD
git checkout -b $branch
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to create branch $branch"
    exit 1
}

# Create annotated tag pointing to this commit
git tag -a $tag -m "Manual pre-change snapshot $ts"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to create tag $tag"
    exit 1
}

Write-Host "Snapshot created: $branch (tag: $tag)"

if ($PushToRemote) {
    git remote | Select-String $RemoteName | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Pushing branch and tag to $RemoteName..."
        git push $RemoteName $branch
        git push $RemoteName $tag
    } else {
        Write-Warning "Remote $RemoteName is not configured. Add with: git remote add <name> <url>"
    }
}

Write-Host "Done. To revert to this snapshot: git checkout $branch"