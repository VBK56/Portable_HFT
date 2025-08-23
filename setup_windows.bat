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
if errorlevel 1 (
    echo ERROR: Failed to create venv
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate
if errorlevel 1 (
    echo ERROR: Failed to activate venv
    pause
    exit /b 1
)

echo Installing packages...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install packages
    pause
    exit /b 1
)

echo Installing required packages (Django + WhiteNoise)...
pip install django whitenoise
if errorlevel 1 (
    echo ERROR: Failed to install Django/WhiteNoise
    pause
    exit /b 1
)

echo Freezing requirements...
pip freeze > requirements.txt

echo Running migrations...
python manage.py migrate
if errorlevel 1 (
    echo ERROR: Failed to run migrations
    pause
    exit /b 1
)

echo.
echo Creating admin user (default credentials)...
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', '', 'admin123')"
if errorlevel 1 (
    echo ERROR: Failed to create admin user
    pause
    exit /b 1
)

echo.
echo ====================================
echo   DEFAULT ADMIN CREATED
echo   Username: admin
echo   Password: admin123
echo.
echo   !!! IMPORTANT !!!
echo   This is a TEMPORARY password.
echo   Please log in to Django admin
echo   and change it immediately.
echo ====================================
echo.
echo ====================================
echo Setup complete!
echo Next run: start_windows.bat
echo ====================================

REM --- Автоматически открываем страницу админки ---

pause