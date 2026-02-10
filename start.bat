@echo off
REM Set UTF-8 encoding
chcp 65001 >nul

REM Intelligent Desktop System Startup Script
echo ====================================
echo Intelligent Desktop System
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

echo [1/3] Checking dependencies...
pip show PyQt6 >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing dependencies...
    pip install PyQt6 websockets pyyaml python-dotenv
)

echo.
echo [2/3] Starting MCP Server...
start "MCP Server" cmd /k "chcp 65001 >nul && cd /d %~dp0 && python mcp_server/start_server.py"

echo Waiting for MCP Server to start...
ping 127.0.0.1 -n 4 >nul

echo.
echo [3/3] Starting user interface...
python main_pyqt.py

echo.
echo System closed
pause
