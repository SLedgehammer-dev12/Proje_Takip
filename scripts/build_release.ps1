Param(
    [string]$Version = "",
    [string]$Python = "python",
    [string]$OutputRoot = "release",
    [switch]$SkipZip
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

function Get-PyInstallerTreeDataArgs {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourceRoot,
        [Parameter(Mandatory = $true)]
        [string]$DestinationRoot
    )

    if (-not (Test-Path $SourceRoot)) {
        return @()
    }

    $entries = @()
    $sourceRootWithSeparator = ((Resolve-Path $SourceRoot).Path).TrimEnd([char[]]@('\', '/')) + [System.IO.Path]::DirectorySeparatorChar
    foreach ($file in Get-ChildItem -Path $SourceRoot -Recurse -File) {
        $relativePath = $file.FullName.Substring($sourceRootWithSeparator.Length)
        $relativeDir = Split-Path -Path $relativePath -Parent
        $targetDir = $DestinationRoot
        if ($relativeDir -and $relativeDir -ne ".") {
            $targetDir = Join-Path $DestinationRoot $relativeDir
        }
        $entries += "--add-data"
        $entries += (New-PyInstallerSourceDest -Source $file.FullName -Destination $targetDir)
    }

    return $entries
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

function Compress-ArchiveWithRetry {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourcePath,
        [Parameter(Mandatory = $true)]
        [string]$DestinationPath,
        [int]$MaxAttempts = 5,
        [int]$DelaySeconds = 5
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        try {
            & $Python (Join-Path $repoRoot "scripts/create_release_zip.py") $SourcePath $DestinationPath
            return
        } catch {
            if ($attempt -eq $MaxAttempts) {
                throw
            }
            Write-Host "Zip islemi deneme $attempt basarisiz oldu, $DelaySeconds saniye sonra tekrar denenecek..."
            Start-Sleep -Seconds $DelaySeconds
        }
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $repoRoot "config.py"

if (-not $Version) {
    $Version = Get-VersionFromConfig -ConfigPath $configPath
}

$releaseDir = Join-Path $repoRoot (Join-Path $OutputRoot $Version)
$notesPath = Join-Path $repoRoot ("docs/releases/{0}.md" -f $Version)
$distRoot = Join-Path $repoRoot (Join-Path "dist" $Version)
$buildRoot = Join-Path $repoRoot "build"
$bundleName = "ProjeTakip"
$bundleDir = Join-Path $distRoot $bundleName
$versionInfoFileName = "pyinstaller-version-info-{0}-{1}.txt" -f (($Version -replace '[^A-Za-z0-9._-]', '_')), $PID
$versionInfoPath = Join-Path $buildRoot $versionInfoFileName
$assetName = "ProjeTakip-{0}-windows-x64.zip" -f $Version
$assetPath = Join-Path $releaseDir $assetName
$checksumPath = Join-Path $releaseDir "SHA256SUMS"
$mainScript = Join-Path $repoRoot "main.py"
$ocrRuntimeRoot = Join-Path $repoRoot "ocr\\tesseract"
$ocrRuntimeExe = Join-Path $ocrRuntimeRoot "tesseract.exe"

if ($IsLinux -or $IsMacOS) {
    throw "Windows release paketi bu script ile sadece Windows ortaminda uretilmelidir."
}

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    throw "PyInstaller bulunamadi. requirements-dev.txt kurulumunu yapin."
}

New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
New-Item -ItemType Directory -Force -Path $buildRoot | Out-Null
New-VersionInfoFile -Version $Version -OutputPath $versionInfoPath

if (Test-Path $bundleDir) {
    Remove-Item -Recurse -Force $bundleDir
}

$pyinstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--noupx",
    "--windowed",
    "--name", $bundleName,
    "--distpath", $distRoot,
    "--version-file", $versionInfoPath,
    "--add-data", (New-PyInstallerSourceDest -Source (Join-Path $repoRoot "filigran.png") -Destination "."),
    "--add-data", (New-PyInstallerSourceDest -Source (Join-Path $repoRoot "DejaVuSans.ttf") -Destination "."),
    "--add-data", (New-PyInstallerSourceDest -Source (Join-Path $repoRoot "KULLANIM_KILAVUZU.md") -Destination "."),
    "--add-data", (New-PyInstallerSourceDest -Source (Join-Path $repoRoot "guncelleme_notlari.txt") -Destination "."),
    $mainScript
)

if (Test-Path $ocrRuntimeExe) {
    Write-Host "OCR runtime bundle edilecek: $ocrRuntimeRoot"
    $pyinstallerArgs += Get-PyInstallerTreeDataArgs -SourceRoot $ocrRuntimeRoot -DestinationRoot "ocr\\tesseract"
} elseif (Test-Path $ocrRuntimeRoot) {
    Write-Host "Uyari: OCR klasoru bulundu ancak tesseract.exe eksik oldugu icin bundle edilmiyor: $ocrRuntimeRoot"
}

Write-Host "PyInstaller build basliyor: $Version"
& pyinstaller @pyinstallerArgs

if (-not (Test-Path $bundleDir)) {
    throw "Build sonucu beklenen bundle dizini olusmadi: $bundleDir"
}

if (-not $SkipZip) {
    if (Test-Path $assetPath) {
        Remove-Item -Force $assetPath
    }
    Compress-ArchiveWithRetry -SourcePath $bundleDir -DestinationPath $assetPath
    & $Python (Join-Path $repoRoot "scripts/create_checksums.py") $assetPath --output $checksumPath | Out-Null
}

Write-Host ""
Write-Host "Hazirlanan dosyalar:"
if (-not $SkipZip) {
    Write-Host "  Asset    : $assetPath"
    Write-Host "  Checksum : $checksumPath"
} else {
    Write-Host "  Asset    : SkipZip nedeniyle uretilmedi"
}

if (Test-Path $notesPath) {
    Write-Host "  Notes    : $notesPath"
} else {
    Write-Host "  Notes    : docs/releases/$Version.md bulunamadi"
}

Write-Host ""
if (-not $SkipZip) {
    Write-Host "GitHub release komutu:"
    Write-Host "  gh release create $Version `"$assetPath`" `"$checksumPath`" --title `"$Version`" --notes-file `"$notesPath`""
}
