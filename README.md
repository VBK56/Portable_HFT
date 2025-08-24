# InvestmentDjango Portable

Portable local deployment of the Django application without installing global dependencies.

## 📥 Download

### Option 1: GitHub Clone
```bash
git clone https://github.com/VBK56/Portable_HFT.git
cd Portable_HFT
```

### Option 2: Direct Download
- **Latest Release:** [Download ZIP v1.1.0](https://github.com/VBK56/Portable_HFT/archive/refs/tags/v1.1.0.zip)
- **Source Code:** [Download ZIP](https://github.com/VBK56/Portable_HFT/archive/refs/heads/main.zip)

### Option 3: Local Archive
If you have the local archive: `InvestmentDjango-Portable-v1.1.0.zip`
- Extract the archive
- Follow the setup instructions below

---

## Contents
- **Windows:** `setup_windows.bat`, `start_windows.bat`, `reinstall_windows.bat`
- **macOS:** `Setup.command`, `Start.command` *(optional: `Stop.command`)*
- Code: `tracker/`, `investments/`, `templates/` (custom), `static/` (user assets), `manage.py`, `requirements.txt`

> The package **does not include**: `venv/`, `db.sqlite3`, `staticfiles/` — they are created during setup and start.

---

## Quick Start

### Windows
1. Double-click **`setup_windows.bat`** *(one time only)*  
   – creates a virtual environment, installs dependencies, runs migrations, creates an admin user.  
2. Double-click **`start_windows.bat`** *(every launch)*  
   – starts the server in a separate window and opens the browser.  
3. To stop the server — close the **“Django Server”** window or press `Ctrl+C` inside it.

### macOS
1. Double-click **`Setup.command`** *(one time only)*  
   – creates a virtual environment, installs dependencies, runs migrations, creates an admin user.  
2. Double-click **`Start.command`** *(every launch)*  
   – starts the server and automatically opens the browser.  
3. To stop the server — close the `Start.command` window (it will gracefully stop the server),  
   or double-click **`Stop.command`** (if available).

---

## Access
- Admin panel: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)  
- Login: **`admin`**  
- Password: **`admin123`** *(temporary — change it immediately after login!)*

---

## Common Issues

### “File downloaded from an unknown source”
macOS may block `.command` files. To unblock:  
Right-click → **Open** → Confirm.  

If needed, remove quarantine via Terminal:
```bash
xattr -dr com.apple.quarantine .
```