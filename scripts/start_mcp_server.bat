@echo off
REM Start MCP Context Server (Windows)

echo Starting Multi-Layer Context Foundation MCP Server...
echo ================================================
echo.

REM Check if virtual environment is activated
if not defined VIRTUAL_ENV (
    echo WARNING: Virtual environment not activated
    echo Run: venv\Scripts\activate
    exit /b 1
)

REM Check dependencies
echo Checking dependencies...
python -c "import mcp" 2>nul
if errorlevel 1 (
    echo ERROR: MCP not installed
    echo Install: pip install mcp
    exit /b 1
)

echo OK: Dependencies installed
echo.

REM Start server
echo Starting MCP server...
echo ================================================
echo.

if "%~1"=="" (
    echo Using default config
    python -m mlcf.mcp.server --config config/mcp_config.yaml
) else (
    echo Using config: %~1
    python -m mlcf.mcp.server --config "%~1"
)