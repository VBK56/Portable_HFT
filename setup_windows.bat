@echo off
echo ====================================
echo Setup Django Investment Tracker
echo ====================================
echo.
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not installed or not in PATH
    echo Please install Python from python.org
    pause
    exit /b 1
)

echo Creating virtual environment...
python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate

echo Installing packages...
pip install -r requirements.txt

echo Running migrations...
python manage.py migrate

echo.
echo Setup complete!
echo Next steps:
echo 1. python manage.py createsuperuser
echo 2. python manage.py runserver
pause
