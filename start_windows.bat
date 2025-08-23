@echo off
setlocal enabledelayedexpansion
title Investment Django - Windows Starter
chcp 65001 >NUL

echo ==============================
echo  Investment Django - Windows
echo ==============================

SET "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found.
    echo Run setup_windows.bat first!
    pause
    exit /b 1
)

call "venv\Scripts\activate"

echo Running migrations...
python manage.py migrate

echo Starting server window...
start "Django Server" cmd /k python manage.py runserver 0.0.0.0:8000

echo Waiting for server to start...
for /l %%i in (1,1,15) do (
    powershell -command "try {Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000 >$null; exit 0} catch {exit 1}" >nul 2>&1
    if !errorlevel! == 0 (
        goto OPEN_ADMIN
    )
    timeout /t 1 /nobreak >nul
)

:OPEN_ADMIN
echo Opening Django admin in browser...
start "" http://127.0.0.1:8000/admin


echo.
echo Server is running in the window titled "Django Server".
echo.
pause
