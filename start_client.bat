@echo off
REM Set UTF-8 encoding
chcp 65001 >nul

REM Intelligent Desktop System - Client Startup Script
echo ====================================
echo Intelligent Desktop System - Client
echo ====================================
echo.

REM Check if Python is installed
echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python not found. Please install Python 3.8+ first.
    pause
    exit /b 1
)

echo [1/2] Checking dependencies...
pip show webview >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing dependencies...
    pip install pywebview websockets pyyaml python-dotenv
)

echo.
echo [2/2] Starting user interface...
cd /d %~dp0
python main_webview.py

echo.
echo Client closed
pause
