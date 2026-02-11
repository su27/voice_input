@echo off
cd /d "%~dp0"
set PATH=%PATH%;%CD%\.venv\Lib\site-packages\nvidia\cublas\bin;%CD%\.venv\Lib\site-packages\nvidia\cudnn\bin
.venv\Scripts\python.exe main.py
pause
