@echo off
REM =====================================================================
REM  Playa - Build script for Windows
REM  Produces  dist\Playa\Playa.exe  (with the palm icon embedded)
REM  Requires: Python 3.11 or 3.12 (64-bit) on PATH.
REM =====================================================================
cd /d "%~dp0"

type nul > "_playa_wtest.tmp" 2>nul
if not exist "_playa_wtest.tmp" goto cannot_write
del "_playa_wtest.tmp" 2>nul

echo.
echo [1/5] Creating virtual environment...
python -m venv .venv
call .venv\Scripts\activate.bat

echo.
echo [2/5] Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller pillow

echo.
echo [3/5] Generating application icon (assets\playa.ico)...
python make_icon.py

echo.
echo [4/5] Building EXE...
REM --collect-all bundles the data/DLLs of the audio packages (incl. the
REM ASIO-capable PortAudio DLL from sounddevice); --add-data bundles the
REM Lato fonts and icon under assets/.
pyinstaller --noconfirm --clean --windowed --name Playa ^
  --icon assets\playa.ico ^
  --add-data "assets;assets" ^
  --collect-all sounddevice ^
  --collect-all soundfile ^
  --collect-all soxr ^
  --collect-all keyboard ^
  --collect-all imageio_ffmpeg ^
  run.py

echo.
echo [5/5] Done.
echo Application:  dist\Playa\Playa.exe
echo.
echo To get a desktop shortcut you have two options:
echo   A) Build the installer: open installer\playa.iss in Inno Setup and click Compile.
echo   B) Quick shortcut without installer: run  make_desktop_shortcut.bat
echo.
pause
exit /b 0

:cannot_write
echo.
echo ============================================================
echo  STOP - cannot write in this folder:
echo    %cd%
echo.
echo  The folder is probably inside "C:\Program Files", where
echo  Windows blocks writing without admin rights.
echo.
echo  FIX: Move the whole "playa" folder to your Desktop:
echo    C:\Users\%USERNAME%\Desktop\playa
echo  and run build.bat again from there.
echo ============================================================
echo.
pause
exit /b 1
