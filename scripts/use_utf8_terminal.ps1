Param()

$utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::InputEncoding = $utf8
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "UTF-8 terminal profile applied for this session."
Write-Host "PowerShell OutputEncoding:" $OutputEncoding.WebName
Write-Host "PYTHONUTF8=" $env:PYTHONUTF8
Write-Host "PYTHONIOENCODING=" $env:PYTHONIOENCODING
