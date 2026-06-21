@echo off
cd /d "C:\managementv2"
call "env\Scripts\activate.bat"

:: Starts the Python app in the background
start pythonw app.py
:: Waits 3 seconds for the Python server to initialize
timeout /t 3 /nobreak >nul
@echo off