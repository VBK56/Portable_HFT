#!/usr/bin/env bash
set -euo pipefail

echo "===================================="
echo " Setup Django Investment Tracker (Mac)"
echo "===================================="
echo

# перейти в папку скрипта
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# 1) Python и venv
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: Python3 not installed"; exit 1
fi

if [ ! -f "venv/bin/python" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi

echo "Activating virtual environment..."
# shellcheck disable=SC1091
source venv/bin/activate

# 2) Зависимости
echo "Upgrading pip..."
python -m pip install --upgrade pip >/dev/null 2>&1 || true

if [ -f "requirements.txt" ]; then
  echo "Installing requirements from requirements.txt..."
  pip install -r requirements.txt
fi

# Обязательные пакеты (подстраховка)
echo "Installing required packages (Django + WhiteNoise + DRF)..."
pip install django whitenoise djangorestframework

# По желанию: обновить requirements.txt
pip freeze > requirements.txt

# 3) Миграции
echo "Running migrations..."
python manage.py migrate

# 4) Создание суперпользователя (если нет)
echo "Ensuring default admin user exists..."
python manage.py shell -c "from django.contrib.auth import get_user_model; U=get_user_model(); \
    (U.objects.filter(username='admin').exists()) or U.objects.create_superuser('admin','', 'admin123')"

echo
echo "===================================="
echo " Setup complete!"
echo " Next: run Start.command"
echo " Default admin: admin / admin123 (temporary — change later)"
echo "===================================="