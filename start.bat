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
pip show webview >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing dependencies...
    pip install pywebview websockets pyyaml python-dotenv
)

echo.
echo [2/3] Starting MCP Server...
start "MCP Server" cmd /k "chcp 65001 >nul && cd /d %~dp0 && python mcp_server/start_server.py"

echo Waiting for MCP Server to start...
REM MCP 8001
set "SERVER_PORT=8001"
set "MAX_WAIT=10"
set "WAIT_COUNT=0"

:CHECK_SERVER
netstat -an | findstr :%SERVER_PORT% | findstr LISTENING >nul
if %errorlevel% equ 0 (
    echo MCP Server started successfully!
    goto SERVER_STARTED
)

ping 127.0.0.1 -n 2 >nul
set /a WAIT_COUNT+=1

if %WAIT_COUNT% geq %MAX_WAIT% (
    echo Error: MCP Server failed to start within %MAX_WAIT% seconds.
    echo Please check the server logs for errors.
    pause
    exit /b 1
)

echo Waiting for MCP Server... (%WAIT_COUNT%/%MAX_WAIT%)
goto CHECK_SERVER

:SERVER_STARTED
echo.
echo [3/3] Starting user interface...
python main_webview.py

echo.
echo System closed
pause
