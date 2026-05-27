# Quick Start Guide

## One-Time Setup

### Linux/Mac

Copy and paste this into your terminal:

```bash
chmod +x setup.sh && ./setup.sh
```

Or manually:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Windows (Command Prompt)

```cmd
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

---

## Running the Tests

### Test Pixoo64 Connection

**Linux/Mac:**
```bash
source venv/bin/activate
python test_pixoo.py
```

**Windows:**
```cmd
venv\Scripts\activate
python test_pixoo.py
```

### Test LMS Connection

**Linux/Mac:**
```bash
source venv/bin/activate
python test_lms.py
```

**Windows:**
```cmd
venv\Scripts\activate
python test_lms.py
```

---

## Running the Service

### Linux/Mac

Quick way (using script):
```bash
chmod +x run.sh && ./run.sh
```

Or manually:
```bash
source venv/bin/activate
python lms_pixoo_service.py
```

### Windows (PowerShell)

```powershell
venv\Scripts\Activate.ps1
python lms_pixoo_service.py
```

### Windows (Command Prompt)

```cmd
venv\Scripts\activate
python lms_pixoo_service.py
```

---

## Configuration Checklist

Before running, make sure to update these settings:

1. **In `test_pixoo.py`:**
   - [ ] Set `PIXOO_IP` to your Pixoo64's IP address

2. **In `lms_pixoo_service.py`:**
   - [ ] Set `pixoo_host` to your Pixoo64's IP address
   - [ ] Set `lms_host` if LMS is not on localhost
   - [ ] Set `lms_port` if not using default (9000)

3. **In `test_lms.py`:**
   - [ ] Set `LMS_HOST` if LMS is not on localhost
   - [ ] Set `LMS_PORT` if not using default (9000)

---

## Stopping the Service

Press `Ctrl+C` in the terminal

---

## Deactivating Virtual Environment

```bash
deactivate
```

---

## Troubleshooting

**"venv/bin/activate: No such file or directory"**
- Run setup first: `./setup.sh`

**"Permission denied: ./setup.sh"**
- Make executable: `chmod +x setup.sh`

**"python3: command not found"**
- Try `python` instead of `python3`
- Ensure Python 3.8+ is installed

**Windows: "Activate.ps1 cannot be loaded"**
- Run PowerShell as Administrator
- Execute: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`