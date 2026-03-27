@echo off
REM Wrapper to run prepare_push.ps1 with ExecutionPolicy bypass (dry-run)
SET SCRIPT_DIR=%~dp0
SET PS_SCRIPT=%SCRIPT_DIR%prepare_push.ps1
echo Running prepare_push in dry-run mode (AutoUntrack, RunTests) with ExecutionPolicy Bypass...
powershell -ExecutionPolicy Bypass -NoProfile -File "%PS_SCRIPT%" -AutoUntrack -DryRun -RunTests
echo Done.
