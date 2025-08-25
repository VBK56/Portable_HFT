@echo off
echo ====================================
echo Reinstalling Django Investment Tracker
echo ====================================
echo.

echo Removing old installation...
if exist "venv" (
    rmdir /s /q venv
    echo Old venv removed
)

if exist "db.sqlite3" (
    del db.sqlite3
    echo Old database removed
)

echo.
echo Starting fresh installation...
echo.
call setup_windows.bat