@echo off
setlocal
cd /d "%~dp0"
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed.
  pause
  exit /b 1
)
py noipa_organizer.py
if errorlevel 1 pause
