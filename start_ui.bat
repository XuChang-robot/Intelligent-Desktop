@echo off
REM Set UTF-8 encoding
chcp 65001 >nul

REM Start user interface
echo Starting user interface...
cd /d %~dp0
python ui/app.py
