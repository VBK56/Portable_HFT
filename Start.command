#!/usr/bin/env bash
set -euo pipefail

# перейти в папку скрипта
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# venv (на всякий случай)
if [ ! -f "venv/bin/python" ]; then
  echo "[START] No venv found. Creating..."
  python3 -m venv venv
fi
# shellcheck disable=SC1091
source "venv/bin/activate"

# Быстрые миграции (если есть — применятся, если нет — просто пройдут)
echo "[START] Running migrations..."
python manage.py migrate

# Запуск сервера в фоне
echo "[START] Launching server..."
python manage.py runserver 0.0.0.0:8000 & SERVER_PID=$!

# Умное ожидание готовности и автозапуск браузера
echo "[START] Waiting for server to be ready..."
for i in {1..20}; do
  if curl -sSf http://127.0.0.1:8000/ >/dev/null; then
    open "http://127.0.0.1:8000/admin"
    break
  fi
  sleep 1
done

# Держим окно, пока сервер работает
wait $SERVER_PID