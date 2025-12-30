@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   Quendoo MCP Server Installer
echo ========================================
echo.

REM Check if Python is installed
echo [1/6] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

python --version
echo Python found!
echo.

REM Get installation directory
set "INSTALL_DIR=%~dp0"
echo [2/6] Installation directory: %INSTALL_DIR%
echo.

REM Install dependencies
echo [3/6] Installing Python dependencies...
python -m pip install --upgrade pip
python -m pip install -r "%INSTALL_DIR%requirements.txt"
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies installed successfully!
echo.

REM Find Python executable path
echo [4/6] Finding Python executable...
for /f "tokens=*" %%i in ('where python') do (
    set "PYTHON_PATH=%%i"
    goto :found_python
)
:found_python
echo Python path: %PYTHON_PATH%
echo.

REM Get Quendoo API Key from user
echo [5/6] Quendoo API Key Setup
echo.
set /p API_KEY="Enter your Quendoo API Key (or press Enter to skip): "
echo.

if not "%API_KEY%"=="" (
    echo Saving API key...
    python "%INSTALL_DIR%api_key_manager.py" set "%API_KEY%"
    echo API key saved successfully!
    echo.
)

REM Setup Claude Desktop configuration
echo [6/6] Configuring Claude Desktop...

set "CLAUDE_CONFIG=%APPDATA%\Claude\claude_desktop_config.json"
set "CLAUDE_DIR=%APPDATA%\Claude"

REM Create Claude directory if it doesn't exist
if not exist "%CLAUDE_DIR%" (
    mkdir "%CLAUDE_DIR%"
)

REM Escape backslashes for JSON
set "PYTHON_PATH_JSON=%PYTHON_PATH:\=\\%"
set "INSTALL_DIR_JSON=%INSTALL_DIR:\=\\%"
set "SERVER_PATH_JSON=%INSTALL_DIR_JSON%server_simple.py"

REM Create or update config file
echo { > "%CLAUDE_CONFIG%"
echo   "mcpServers": { >> "%CLAUDE_CONFIG%"
echo     "quendoo-pms": { >> "%CLAUDE_CONFIG%"
echo       "command": "%PYTHON_PATH_JSON%", >> "%CLAUDE_CONFIG%"
echo       "args": ["%SERVER_PATH_JSON%"] >> "%CLAUDE_CONFIG%"
echo     } >> "%CLAUDE_CONFIG%"
echo   } >> "%CLAUDE_CONFIG%"
echo } >> "%CLAUDE_CONFIG%"

echo Claude Desktop configuration updated!
echo Config file: %CLAUDE_CONFIG%
echo.

echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Restart Claude Desktop (close all windows and reopen)
echo 2. You should see "Quendoo PMS MCP server" available
echo.

if "%API_KEY%"=="" (
    echo NOTE: You skipped API key setup.
    echo To set it up later, tell Claude:
    echo   "Set my Quendoo API key to: YOUR_KEY_HERE"
    echo.
)

echo To verify installation:
echo   1. Open Claude Desktop
echo   2. Ask: "Check my Quendoo API key status"
echo   3. Ask: "Show me availability for March 2025"
echo.

pause
