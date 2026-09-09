@echo off
title Stop Veyra
echo ======================================================================
echo           Stopping Veyra Backend and Frontend Servers
echo ======================================================================
echo.

echo Stopping Django backend (port 8000)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo Terminating PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo Stopping Vite frontend (port 5173)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do (
    echo Terminating PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo All OpenWES services have been stopped.
timeout /t 3
