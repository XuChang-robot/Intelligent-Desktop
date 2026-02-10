---
name: "intelligent-desktop-system"
description: "Generates an intelligent desktop system with PyQt6 UI, MCP client-server architecture, and AI-powered task execution. Invoke when user wants to create or regenerate the complete intelligent desktop system project."
---

# Intelligent Desktop System

This skill generates a complete intelligent desktop system with the following features:

## Project Structure

```
Intelligent_Desktop/
├── ui/
│   ├── pyqt_app.py          # Main application logic
│   ├── pyqt_main_window.py  # Main window UI
│   └── __init__.py
├── mcp_client/
│   ├── client.py            # MCP client implementation
│   ├── llm.py               # LLM client
│   └── __init__.py
├── mcp_server/
│   ├── start_server.py      # MCP server startup
│   └── sandbox.py           # Sandbox for code execution
├── config/
│   └── config.py            # Configuration
├── main_pyqt.py             # Application entry point
├── start.bat                # Windows startup script
└── requirements.txt         # Dependencies
```

## Core Features

1. **Modern PyQt6 UI**:
   - Chat interface with message bubbles
   - Interactive confirmation dialogs embedded in chat
   - Task history display
   - Model selection dropdown

2. **MCP Client-Server Architecture**:
   - Streamable HTTP communication
   - Skill-based task execution
   - Elicitation callback mechanism for user confirmation

3. **AI-Powered Task Execution**:
   - Python code execution
   - LLM integration for intent parsing
   - Task planning and execution

4. **User Interaction**:
   - Natural language command processing
   - Interactive confirmation for sensitive operations
   - Real-time system status updates

## Usage

1. **Start the system**:
   - Run `start.bat` on Windows
   - This starts both MCP server and UI

2. **Interact with the system**:
   - Type commands in the input field
   - Click "Send" or press Enter
   - Confirm sensitive operations when prompted

3. **Monitor tasks**:
   - Task history is displayed in the lower window
   - System status is shown in the status bar

## Technical Details

- **Python 3.8+** required
- **Dependencies**:
  - PyQt6
  - websockets
  - pyyaml
  - python-dotenv
  - httpx

- **MCP Protocol**:
  - Uses FastMCP with streamable-http
  - Session-based communication

- **Security**:
  - Sandboxed code execution
  - User confirmation for sensitive operations
  - Input validation

## Example Commands

- "Delete the 'test' folder on desktop"
- "Create a Python script to calculate factorial"
- "Check system status"

This skill generates the complete project structure with all necessary files and configurations, ready to run out-of-the-box.