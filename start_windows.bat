@echo off
echo Starting Django Investment Tracker...
echo.
call venv\Scripts\activate
python manage.py runserver
pause
