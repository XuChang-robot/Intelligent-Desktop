@echo off
REM Set UTF-8 encoding
chcp 65001 >nul

REM Start MCP Server
echo Starting MCP Server...
cd /d %~dp0
python mcp_server/start_server.py
