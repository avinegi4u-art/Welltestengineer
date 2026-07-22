@echo off
title FlowSim Pro
cd /d "%~dp0"

echo.
echo  FlowSim Pro — starting...
echo.

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  set PY=python
) else (
  where py >nul 2>nul
  if %ERRORLEVEL%==0 (
    set PY=py -3
  ) else (
    echo ERROR: Python not found.
    echo Install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure "Add python.exe to PATH" is checked.
    pause
    exit /b 1
  )
)

where npm >nul 2>nul
if not %ERRORLEVEL%==0 (
  echo ERROR: npm / Node.js not found.
  echo Install Node.js LTS from https://nodejs.org/
  pause
  exit /b 1
)

%PY% "%~dp0launch.py"
if errorlevel 1 (
  echo.
  echo Launcher failed. See messages above.
  pause
)
