# InvestmentDjango Portable

Локальный портативный запуск Django-приложения без установки глобальных зависимостей.

## Состав
- **Windows:** `setup_windows.bat`, `start_windows.bat`, `reinstall_windows.bat`
- **macOS:** `Setup.command`, `Start.command` *(опционально: `Stop.command`)*
- Код: `tracker/`, `investments/`, `templates/` (кастом), `static/` (пользовательские ассеты), `manage.py`, `requirements.txt`

> В поставке **нет**: `venv/`, `db.sqlite3`, `staticfiles/` — они создаются/собираются при запуске.

---

## Быстрый старт

### Windows
1. Двойной клик **`setup_windows.bat`** *(один раз)*  
   – создаст venv, установит зависимости, применит миграции, создаст админа.  
2. Двойной клик **`start_windows.bat`** *(каждый запуск)*  
   – поднимет сервер и откроет браузер.  
3. Остановка сервера — закрыть окно **“Django Server”** или `Ctrl+C` внутри него.

### macOS
1. Двойной клик **`Setup.command`** *(один раз)*  
   – создаст venv, установит зависимости, применит миграции, создаст админа.  
2. Двойной клик **`Start.command`** *(каждый запуск)*  
   – поднимет сервер и автоматически откроет браузер.  
3. Остановка сервера — закрыть окно `Start.command` (он корректно погасит сервер), либо двойной клик **`Stop.command`** (если есть).

---

## Доступ
- Админ-панель: http://127.0.0.1:8000/admin  
- Логин: **`admin`**  
- Пароль: **`admin123`** *(временный — смените сразу после входа!)*

---

## Частые вопросы / проблемы

### «Файл загружен из неизвестного источника»
macOS может блокировать запуск `.command`. Кликните правой кнопкой по файлу → **Open** → Open.  
При необходимости снимите карантин:
```bash
xattr -dr com.apple.quarantine .




InvestmentDjango Portable

Local portable launch of a Django application without installing global dependencies.

Contents
		Windows: setup_windows.bat, start_windows.bat, reinstall_windows.bat
		macOS: Setup.command, Start.command (optional: Stop.command)
		Source code: tracker/, investments/, templates/ (custom), static/ (user assets), manage.py, requirements.txt

The package does not include: venv/, db.sqlite3, staticfiles/ — these are created automatically during setup.



Quick Start

Windows
	1.	Double-click setup_windows.bat (one-time only)
 creates a virtual environment, installs dependencies, runs migrations, and creates the default admin user.
	2.	Double-click start_windows.bat (each launch)
 starts the server and opens the browser automatically.
	3.	To stop the server — close the “Django Server” window or press Ctrl+C inside it.

macOS
	1.	Double-click Setup.command (one-time only)
 creates a virtual environment, installs dependencies, runs migrations, and creates the default admin user.
	2.	Double-click Start.command (each launch)
 starts the server and automatically opens the browser.
	3.	To stop the server — simply close the Start.command window (it will terminate the server), or double-click Stop.command if provided.



Access
	•	Admin panel: http://127.0.0.1:8000/admin
	•	Username: admin
	•	Password: admin123 (temporary — change immediately after first login!)