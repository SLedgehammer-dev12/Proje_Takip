param(
    [string]$venvPath = ".venv"
)

Write-Host "Sanal ortam oluşturuluyor: $venvPath..."
python -m venv $venvPath ;
Write-Host "Sanal ortam aktive ediliyor..."
& "$venvPath\Scripts\Activate.ps1" ;
Write-Host "pip güncelleniyor..."
python -m pip install --upgrade pip ;
Write-Host "Gerekli paketler kuruluyor..."
python -m pip install -r "requirements/requirements.txt" ;
Write-Host "Kurulum tamamlandı. Uygulamayı çalıştırmak için:\n  & \"$venvPath\Scripts\Activate.ps1\" ; python main.py"
