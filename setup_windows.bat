@echo off
python -m venv venv
call venv\Scriptsctivate
pip install -r requirements.txt
python manage.py migrate
echo Setup complete!
