@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"
title Veyra - Build Standalone Executable

echo ======================================================================
echo           VEYRA - Building Standalone Windows Executable (.exe)
echo ======================================================================
echo.

set "BUILD_SCRIPT=build.py"
if not exist "%BUILD_SCRIPT%" (
    if exist "build_exe.py" set "BUILD_SCRIPT=build_exe.py"
)

if exist ".venv\Scripts\python.exe" (
    echo [*] Virtual environment detected at .venv
    echo [*] Launching builder using virtual environment Python...
    ".venv\Scripts\python.exe" "%BUILD_SCRIPT%" %*
) else (
    echo [*] Virtual environment not found, falling back to system Python...
    python "%BUILD_SCRIPT%" %*
)

if %ERRORLEVEL% equ 0 (
    echo.
    echo [*] Build completed successfully.
) else (
    echo.
    echo [ERROR] Build failed with exit code %ERRORLEVEL%.
)

echo.
pause
