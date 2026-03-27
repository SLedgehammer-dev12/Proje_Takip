param(
    [string]$Remote = 'origin',
    [string]$Branch = 'main',
    [switch]$Push,
    [switch]$AutoUntrack,
    [switch]$DryRun,
    [switch]$RunTests
)

Write-Host "Repository push hazırlığı başlatılıyor..."

function Check-GitClean {
    $status = git status --porcelain
    if ($status) {
        Write-Host "Uyarı: Çalışma alanınız temiz değil (değişiklikler, staged veya unstaged). Lütfen önce commit veya stash yapın."
        git status
        return $false
    }
    return $true
}

if (-not (Check-GitClean)) { exit 1 }

# Detect tracked DB and test artifacts
$tracked = git ls-files | Select-String -Pattern 'projeler.db|veritabani_yedekleri|test_output.txt' -SimpleMatch
if ($tracked) {
    Write-Host "Repo halen takipte olan veritabanı veya test dosyaları içeriyor:";
    $tracked | ForEach-Object { Write-Host " - $_" }
    if ($AutoUntrack) {
        Write-Host "AutoUntrack etkin: untrack işlemi başlatılıyor (DryRun=$DryRun)..."
        $untrackArgs = @('-Remote', $Remote, '-Branch', $Branch)
        if ($Push) { $untrackArgs += '-Push' }
        if ($DryRun) { $untrackArgs += '-DryRun' }
        & .\scripts\untrack_and_push.ps1 @untrackArgs
    } else {
        Write-Host "Lütfen 'scripts/untrack_and_push.ps1' betiğini çalıştırın veya bu komutu '-AutoUntrack' ile yeniden çalıştırın."
        exit 2
    }
}

# Run pre-commit checks
Write-Host "Pre-commit kontrolleri çalıştırılıyor..."
try { pre-commit run --all-files } catch { Write-Host "pre-commit çalıştırılamadı; öncelikle pre-commit install yapın (setup_dev_env.ps1 çalıştırıldıysa önceden kurulmuş olmalı)." }

if ($RunTests) {
    Write-Host "Testler çalıştırılıyor (pytest)..."
    try { pytest } catch { Write-Host "pytest çalıştırılamadı veya testler başarısız." }
}

Write-Host "Son adımlar: commit ve (opsiyonel) push işlemleri";
if ($DryRun) {
    Write-Host "DRY RUN: Komut gerçek commit/push adımlarını çalıştırmayacak. Değişiklikler aşağıda gösterilmiştir.";
    git status --porcelain
} else {
    Write-Host "Değişikliklerin commit edilmesi (git add -A && git commit)
    Eğer commit yapılacak bir değişiklik yoksa, commit atılmayacaktır.";
    git add -A
    git commit -m "Repo temizliği: DB ve test çıktı dosyaları takibi kaldırılarak .gitignore güncellendi" 2>$null | Out-Null
}

if ($Push -and -not $DryRun) {
    Write-Host "Push işlemi başlatılıyor: $Remote/$Branch";
    git push $Remote $Branch
}

Write-Host "Prepare push script tamamlandı.";
