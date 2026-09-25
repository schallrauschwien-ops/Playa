@echo off
REM Run Playa directly from source (for testing, no EXE build needed).
cd /d "%~dp0"

REM If we can write here, use a local venv; otherwise just use global Python
REM (works because the required packages are already installed system-wide).
type nul > "_playa_wtest.tmp" 2>nul
if not exist "_playa_wtest.tmp" goto useglobal
del "_playa_wtest.tmp" 2>nul

if not exist .venv (
  python -m venv .venv 2>nul
)
if not exist .venv\Scripts\activate.bat goto useglobal
call .venv\Scripts\activate.bat
python -c "import PySide6" 2>nul || pip install -r requirements.txt
python run.py
goto end

:useglobal
echo (Running with the global Python installation.)
python run.py

:end
