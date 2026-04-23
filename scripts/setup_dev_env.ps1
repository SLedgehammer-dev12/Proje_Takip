Param(
    [string]$VenvName = ".venv"
)

$utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::InputEncoding = $utf8
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "Creating Python venv and installing dev dependencies..."
python -m venv $VenvName
& $VenvName\Scripts\Activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt

Write-Host "Installing pre-commit hooks..."
pre-commit install

Write-Host "Setup complete. Activate your virtualenv with `.\\$VenvName\\Scripts\\Activate`, then dot-source `.\\scripts\\use_utf8_terminal.ps1` and run `pre-commit run --all-files`"
