@echo off
echo Starting Django Investment Tracker...
echo.

if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run setup_windows.bat first
    pause
    exit /b 1
)

call venv\Scripts\activate

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in virtual environment
    pause
    exit /b 1
)

python manage.py collectstatic --noinput --clear
if errorlevel 1 (
    echo WARNING: Could not collect static files
    echo Continuing anyway...
    pause
)

echo Starting server on http://localhost:8000
echo Admin panel will open in browser...
echo Press Ctrl+C to stop
echo.

REM Открываем браузер через 3 секунды
start cmd /c "timeout /t 3 >nul && start http://localhost:8000/admin"

python manage.py runserver

echo.
echo Server stopped
pause
