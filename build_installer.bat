@echo off
REM =====================================================================
REM  Playa - ONE-CLICK installer build for Windows
REM
REM  Produces a single distributable file:  installer\Setup\Playa-Setup.exe
REM  That Setup.exe installs Playa, adds Start-Menu + Desktop shortcuts,
REM  and registers a proper UNINSTALLER in Windows "Apps & Features".
REM
REM  Requirements (install once):
REM    1) Python 3.11 or 3.12 (64-bit)  -> https://www.python.org/downloads/
REM       (tick "Add Python to PATH" during install)
REM    2) Inno Setup 6 (free)           -> https://jrsoftware.org/isdl.php
REM  =====================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

REM --- Guard: verify we can actually write in this folder ---
type nul > "_playa_wtest.tmp" 2>nul
if not exist "_playa_wtest.tmp" goto cannot_write
del "_playa_wtest.tmp" 2>nul

echo.
echo ========================================================
echo  Playa - building distributable installer
echo ========================================================

echo.
echo [1/5] Creating virtual environment...
if not exist .venv ( python -m venv .venv )
call .venv\Scripts\activate.bat

echo.
echo [2/5] Installing dependencies...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
pip install pyinstaller pillow

echo.
echo [3/5] Generating application icon...
python make_icon.py

echo.
echo [4/5] Building the EXE (this can take a minute)...
rmdir /s /q build dist 2>nul
REM  Gebaut wird ueber Playa.spec, NICHT ueber Schalter in dieser Zeile.
REM  Die Spec macht dasselbe wie die frueheren --collect-all-Schalter und
REM  sortiert zusaetzlich die ASIO-Fassung der PortAudio-DLL aus. Wird hier
REM  an der Spec vorbeigebaut, landet ASIO wieder im Paket.
pyinstaller --noconfirm --clean Playa.spec
if not exist dist\Playa\Playa.exe (
  echo.
  echo ERROR: the EXE build failed. Scroll up to see the error.
  pause
  exit /b 1
)

echo.
echo [5/5] Compiling the installer with Inno Setup...
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
where iscc >nul 2>nul && set "ISCC=iscc"

if "!ISCC!"=="" goto no_inno

"!ISCC!" installer\playa.iss
if exist installer\Setup\Playa-Setup.exe (
  echo.
  echo ========================================================
  echo  DONE!  Your distributable installer is here:
  echo     installer\Setup\Playa-Setup.exe
  echo.
  echo  Send that one file to anyone. It installs Playa and
  echo  can be uninstalled via Windows "Apps and Features".
  echo ========================================================
) else (
  echo.
  echo The installer compile step did not produce the file.
  echo Check the messages above.
)
echo.
pause
exit /b 0

:cannot_write
echo.
echo ============================================================
echo  STOP - cannot write in this folder:
echo    %cd%
echo.
echo  This is usually because the folder is inside
echo  "C:\Program Files", where Windows blocks writing
echo  without administrator rights.
echo.
echo  FIX: Move the whole "playa" folder to a normal location
echo  such as your Desktop, for example:
echo.
echo    C:\Users\%USERNAME%\Desktop\playa
echo.
echo  Then run build_installer.bat again from there.
echo.
echo  Note: building must happen in a normal folder. The
echo  finished Playa-Setup.exe is what later installs Playa
echo  into Program Files for you.
echo ============================================================
echo.
pause
exit /b 1

:no_inno
echo.
echo --------------------------------------------------------
echo  Inno Setup was not found.
echo  The app itself is ready at:  dist\Playa\Playa.exe
echo.
echo  To get the distributable Setup.exe:
echo    1^) Install Inno Setup 6 ^(free^): https://jrsoftware.org/isdl.php
echo    2^) Run build_installer.bat again.
echo --------------------------------------------------------
echo.
pause
exit /b 0
