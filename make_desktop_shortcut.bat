@echo off
REM Creates a Desktop shortcut to dist\Playa\Playa.exe without an installer.
REM Run this AFTER build.bat has finished.

setlocal
set TARGET=%~dp0dist\Playa\Playa.exe
if not exist "%TARGET%" (
  echo Could not find "%TARGET%".
  echo Please run build.bat first.
  pause
  exit /b 1
)

powershell -NoProfile -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Playa.lnk');" ^
  "$s.TargetPath='%TARGET%';" ^
  "$s.WorkingDirectory='%~dp0dist\Playa';" ^
  "$s.IconLocation='%TARGET%,0';" ^
  "$s.Save()"

echo Desktop shortcut "Playa" created.
pause
