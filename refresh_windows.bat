@echo off
echo ====================================
echo Refresh Django Investment Tracker
echo ====================================
echo.

call venv\Scripts\activate

echo Updating requirements...
pip install -r requirements.txt
pip install django whitenoise
pip freeze > requirements.txt

echo Running migrations...
python manage.py migrate

echo Collecting static files...
python manage.py collectstatic --noinput --clear

echo.
echo ====================================
echo Refresh complete!
echo ====================================
pause