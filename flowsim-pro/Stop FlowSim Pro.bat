@echo off
title Stop FlowSim Pro
echo Stopping FlowSim Pro processes on ports 8000 and 3000...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
  taskkill /F /PID %%a >nul 2>nul
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING"') do (
  taskkill /F /PID %%a >nul 2>nul
)

echo Done.
timeout /t 2 >nul
