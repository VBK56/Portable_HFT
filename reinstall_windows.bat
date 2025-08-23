@echo off
echo ====================================
echo Reinstall Django Investment Tracker
echo ====================================
echo.

REM --- Удаляем старое окружение ---
if exist venv (
    echo Removing old virtual environment...
    rmdir /s /q venv
)

REM --- Удаляем базу SQLite ---
if exist db.sqlite3 (
    echo Removing old database...
    del db.sqlite3
)

REM --- Запуск основного setup ---
call setup_windows.bat