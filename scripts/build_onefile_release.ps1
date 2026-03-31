Param(
    [string]$Version = "",
    [string]$Python = "python"
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

function New-PyInstallerSourceDest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Source,
        [Parameter(Mandatory = $true)]
        [string]$Destination
    )

    return "$Source`:$Destination"
}

function New-VersionInfoFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Version,
        [Parameter(Mandatory = $true)]
        [string]$OutputPath
    )

    $numericVersion = ($Version -replace '^[^\d]*', '')
    $parts = @($numericVersion -split '\.')
    while ($parts.Count -lt 4) {
        $parts += "0"
    }
    $parts = $parts | Select-Object -First 4
    $versionTuple = ($parts -join ', ')
    $versionString = ($parts -join '.')

    $content = @"
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($versionTuple),
    prodvers=($versionTuple),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'BOTAS'),
          StringStruct('FileDescription', 'Proje Takip Sistemi'),
          StringStruct('FileVersion', '$versionString'),
          StringStruct('InternalName', 'ProjeTakip'),
          StringStruct('OriginalFilename', 'ProjeTakip.exe'),
          StringStruct('ProductName', 'Proje Takip Sistemi'),
          StringStruct('ProductVersion', '$versionString')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"@

    Set-Content -Path $OutputPath -Value $content -Encoding UTF8
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $repoRoot "config.py"

if (-not $Version) {
    $Version = Get-VersionFromConfig -ConfigPath $configPath
}

$releaseDir = Join-Path $repoRoot (Join-Path "release" $Version)
$distRoot = Join-Path $repoRoot (Join-Path "dist" ("{0}_onefile" -f $Version))
$buildRoot = Join-Path $repoRoot "build"
$assetName = "ProjeTakip-{0}-windows-x64.exe" -f $Version
$distAssetPath = Join-Path $distRoot $assetName
$releaseAssetPath = Join-Path $releaseDir $assetName
$checksumPath = Join-Path $releaseDir "SHA256SUMS"
$versionInfoPath = Join-Path $buildRoot ("pyinstaller-version-info-onefile-{0}-{1}.txt" -f (($Version -replace '[^A-Za-z0-9._-]', '_')), $PID)
$mainScript = Join-Path $repoRoot "main.py"
if ($IsLinux -or $IsMacOS) {
    throw "Bu script sadece Windows ortamında kullanılmalıdır."
}

$pythonExe = $Python
if ($pythonExe -eq "python") {
    $localPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
    if (Test-Path $localPython) {
        $pythonExe = $localPython
    }
}

& $pythonExe -m PyInstaller --version *> $null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller bulunamadı. requirements-dev.txt kurulumunu yapın."
}

New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
New-Item -ItemType Directory -Force -Path $distRoot | Out-Null
New-Item -ItemType Directory -Force -Path $buildRoot | Out-Null
New-VersionInfoFile -Version $Version -OutputPath $versionInfoPath

if (Test-Path $distAssetPath) {
    Remove-Item -Force $distAssetPath
}
if (Test-Path $releaseAssetPath) {
    Remove-Item -Force $releaseAssetPath
}

$pyInstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--noupx",
    "--windowed",
    "--onefile",
    "--icon", (Join-Path $repoRoot "app_icon.ico"),
    "--name", ([System.IO.Path]::GetFileNameWithoutExtension($assetName)),
    "--distpath", $distRoot,
    "--workpath", (Join-Path $buildRoot ("pyinstaller-onefile-{0}" -f ($Version -replace '[^A-Za-z0-9._-]', '_'))),
    "--version-file", $versionInfoPath,
    "--add-data", (New-PyInstallerSourceDest -Source (Join-Path $repoRoot "app_icon.ico") -Destination "."),
    "--add-data", (New-PyInstallerSourceDest -Source (Join-Path $repoRoot "filigran.png") -Destination "."),
    "--add-data", (New-PyInstallerSourceDest -Source (Join-Path $repoRoot "DejaVuSans.ttf") -Destination "."),
    "--add-data", (New-PyInstallerSourceDest -Source (Join-Path $repoRoot "KULLANIM_KILAVUZU.md") -Destination "."),
    "--add-data", (New-PyInstallerSourceDest -Source (Join-Path $repoRoot "guncelleme_notlari.txt") -Destination "."),
    $mainScript
)

Write-Host "PyInstaller one-file build baslıyor: $Version"
& $pythonExe -m PyInstaller @pyInstallerArgs
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build başarısız oldu."
}

if (-not (Test-Path $distAssetPath)) {
    throw "Beklenen one-file asset oluşmadı: $distAssetPath"
}

Copy-Item -Path $distAssetPath -Destination $releaseAssetPath -Force
& $pythonExe (Join-Path $repoRoot "scripts/create_checksums.py") $releaseAssetPath --output $checksumPath | Out-Null

Write-Host ""
Write-Host "Hazırlanan dosyalar:"
Write-Host "  Dist asset : $distAssetPath"
Write-Host "  Release    : $releaseAssetPath"
Write-Host "  Checksum   : $checksumPath"
Write-Host ""
Write-Host "GitHub release komutu:"
Write-Host "  python .\release\upload_release.py --version $Version"
