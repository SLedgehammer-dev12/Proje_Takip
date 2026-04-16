# Remove runtime DB files and backup directories from git tracking without deleting local copies.
param(
    [switch]$PurgeHistory
)

Write-Host "Git takibinden veritabanı ve yedek klasörleri kaldırılıyor (yerel dosyalar korunuyor)..."
git rm --cached projeler.db -f 2>$null | Out-Null ;
git rm -r --cached veritabani_yedekleri -f 2>$null | Out-Null ;
git commit -m "Çalışma zamanı veritabanı ve yedek dosyaları repodan kaldırıldı" ;

if ($PurgeHistory) {
    Write-Host "Geçmişten temizleme (history purge) isteği alındı - dikkat: gelişmiş ve tehlikeli bir işlemdir."
    Write-Host "Lütfen BFG veya git-filter-repo kurup elle çalıştırın; bu script sadece uyarı gösterir. BFG örneği:"
    Write-Host "bfg --delete-files \"*.db\""
}
