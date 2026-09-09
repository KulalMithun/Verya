@echo off
setlocal enabledelayedexpansion

title Veyra Launcher
echo ======================================================================
echo           VEYRA - Open Warehouse Execution System
echo ======================================================================
echo.

cd /d "%~dp0"

:: 1. Check Python virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at .venv.
    echo Please create the virtual environment first.
    pause
    exit /b 1
)

set VENV_PYTHON="%~dp0.venv\Scripts\python.exe"

:: 2. Check and run migrations
echo [*] Checking database migrations...
%VENV_PYTHON% src\backend\InvenTree\manage.py migrate --noinput
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Migration check reported non-zero status, continuing...
)

echo.
echo [1/3] Launching Veyra Django Backend (Port 8000)...
start "Veyra Backend (Django :8000)" cmd /k "title Veyra Backend (Port 8000) && cd /d "%~dp0" && "%~dp0.venv\Scripts\python.exe" src\backend\InvenTree\manage.py runserver 0.0.0.0:8000"

echo [2/3] Launching Veyra Vite Frontend (Port 5173)...
start "Veyra Frontend (Vite :5173)" cmd /k "title Veyra Frontend (Port 5173) && cd /d "%~dp0\src\frontend" && npx yarn dev --host 0.0.0.0"

echo [3/3] Waiting for servers to initialize...
timeout /t 6 /nobreak >nul

echo.
echo Launching Veyra in your default browser...
start http://localhost:5173/

echo.
echo ======================================================================
echo  Veyra is successfully running!
echo ----------------------------------------------------------------------
echo  - Dashboard:    http://localhost:5173/
echo  - Login Page:   http://localhost:5173/login
echo  - Operator HUD:  http://localhost:5173/openwes/operator
echo  - Supervisor:   http://localhost:5173/openwes/supervisor
echo  - Backend API:  http://localhost:8000/api/openwes/
echo ----------------------------------------------------------------------
echo  Demo Credentials:
echo  - Admin / Manager:  admin / inventree
echo  - Zone A Operator:  op_rajesh / openwes2026
echo  - Voice Operator:   op_priya / openwes2026
echo  - Supervisor:       op_deepa / openwes2026
echo ======================================================================
echo.
echo Note: If prompted to log in, enter username 'admin' and password 'inventree'.
echo To stop Veyra, run stop.bat or close the two spawned windows.
echo.
pause
