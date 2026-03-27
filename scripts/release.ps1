Param(
    [string]$Version = "",
    [string]$ReleaseNotesFile = "",
    [string[]]$AssetPaths = @(),
    [string]$Remote = "origin",
    [string]$Branch = "main",
    [switch]$SkipGitPush
)

$ErrorActionPreference = "Stop"

function Get-VersionFromConfig {
    param([string]$ConfigPath)

    $content = Get-Content -Path $ConfigPath -Raw -Encoding UTF8
    $match = [regex]::Match($content, 'APP_VERSION\s*=\s*"([^"]+)"')
    if (-not $match.Success) {
        throw "APP_VERSION config.py içinden okunamadı."
    }
    return $match.Groups[1].Value
}

$repoRoot = Split-Path -Parent $PSScriptRoot

if (-not $Version) {
    $Version = Get-VersionFromConfig -ConfigPath (Join-Path $repoRoot "config.py")
}

if (-not $ReleaseNotesFile) {
    $candidate = Join-Path $repoRoot ("docs/releases/{0}.md" -f $Version)
    if (Test-Path $candidate) {
        $ReleaseNotesFile = $candidate
    } else {
        $ReleaseNotesFile = Join-Path $repoRoot "guncelleme_notlari.txt"
    }
}

if (-not $SkipGitPush) {
    git -C $repoRoot push $Remote $Branch
    git -C $repoRoot rev-parse $Version *> $null
    if ($LASTEXITCODE -ne 0) {
        git -C $repoRoot tag -a $Version -m "Release $Version"
    }
    git -C $repoRoot push $Remote $Version
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "gh CLI bulunamadı. GitHub release için gh kurun veya release'i manuel oluşturun."
}

$releaseArgs = @("release", "view", $Version)
gh @releaseArgs *> $null
$releaseExists = ($LASTEXITCODE -eq 0)

if ($releaseExists) {
    $uploadArgs = @("release", "upload", $Version, "--clobber")
    foreach ($asset in $AssetPaths) {
        if (Test-Path $asset) {
            $uploadArgs += $asset
        }
    }
    if ($uploadArgs.Count -gt 4) {
        gh @uploadArgs
    }
    Write-Host "Release zaten mevcut. Asset'ler guncellendi: $Version"
    exit 0
}

$createArgs = @("release", "create", $Version, "--title", $Version, "--notes-file", $ReleaseNotesFile)
foreach ($asset in $AssetPaths) {
    if (Test-Path $asset) {
        $createArgs += $asset
    }
}

gh @createArgs
Write-Host "GitHub release hazir: $Version"
