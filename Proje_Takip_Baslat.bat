@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "VENV_PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    echo Proje icindeki Python ortami bulunamadi:
    echo %VENV_PYTHON%
    pause
    exit /b 1
)

pushd "%SCRIPT_DIR%"
"%VENV_PYTHON%" main.py
set "EXIT_CODE=%ERRORLEVEL%"
popd

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Program cikis kodu: %EXIT_CODE%
    pause
)

exit /b %EXIT_CODE%
