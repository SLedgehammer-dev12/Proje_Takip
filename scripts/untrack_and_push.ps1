param(
    [string]$Remote = 'origin',
    [string]$Branch = 'main',
    [switch]$Push,
    [switch]$DryRun
)

Write-Host "Veritabanı dosyalarını git takibinden çıkarma işlemi başlıyor..."

$filesToUntrack = @("projeler.db", "veritabani_yedekleri", "test_output.txt")

# Ensure .gitignore contains the right patterns
$gitignorePath = ".gitignore"
$patternsToAdd = @("projeler.db", "*.db", "veritabani_yedekleri/", "*.db-journal", "*.sqlite", "*.sqlite3")
if (Test-Path $gitignorePath) {
    $gitignoreContent = Get-Content $gitignorePath -ErrorAction SilentlyContinue
    $added = $false
    foreach ($p in $patternsToAdd) {
        if (-not ($gitignoreContent -contains $p)) {
            Add-Content -Path $gitignorePath -Value $p
            $added = $true
            Write-Host ".gitignore'a eklenen desen: $p"
        }
    }
    if ($added) {
        Write-Host ".gitignore dosyasına yeni desenler eklendi. Dosya staged edildi.";
        git add .gitignore 2>$null | Out-Null
    }
} else {
    Write-Host ".gitignore bulunamadı, yeni bir tane oluşturuluyor..."
    foreach ($p in $patternsToAdd) { Add-Content -Path $gitignorePath -Value $p }
    git add .gitignore 2>$null | Out-Null
}

foreach ($f in $filesToUntrack) {
    if (Test-Path $f) {
        Write-Host "git rm --cached $f"
        if (-not $DryRun) {
            git rm --cached $f -r -f 2>$null | Out-Null
        } else {
            Write-Host "DRY RUN: $f untrack edilmedi; -DryRun parametresi aktif."
        }
    } else {
        Write-Host "$f bulunamadı — atlandı"
    }
}

Write-Host "Değişiklikler commit ediliyor..."
if (-not $DryRun) {
    try { git add .gitignore 2>$null | Out-Null } catch { }
    git commit -m "Çalışma zamanı veritabanı ve yedekleri repodan kaldırıldı" 2>$null | Out-Null
} else {
    Write-Host "DRY RUN: Commit atılmayacak. Mevcut staged değişiklikleri görmek için git status --porcelain çalıştırılıyor:";
    git status --porcelain
}

if ($Push) {
    Write-Host "Push işlemi istenmiş: $Remote/$Branch"
    if ($DryRun) {
        Write-Host "DRY RUN: Push yapılmayacak. -Push ile gerçek push yapılabilir."
    } else {
        Write-Host "Lütfen push öncesi remote branch'ınıza dikkat edin. Push ediliyor..."
        git push $Remote $Branch
    }
    if ($LASTEXITCODE -eq 0) { Write-Host "Başarıyla pushlandı." }
    else { Write-Host "Push hatası: $LASTEXITCODE" }
} else {
    Write-Host "Push yapılmadı. Push etmek isterseniz -Push parametresini kullanın (örn: .\scripts\untrack_and_push.ps1 -Push)."
}
