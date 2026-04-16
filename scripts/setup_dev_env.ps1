Param(
    [string]$VenvName = ".venv"
)

Write-Host "Creating Python venv and installing dev dependencies..."
python -m venv $VenvName
& $VenvName\Scripts\Activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt

Write-Host "Installing pre-commit hooks..."
pre-commit install

Write-Host "Setup complete. Activate your virtualenv with `.\\$VenvName\\Scripts\\Activate` and run `pre-commit run --all-files`"
