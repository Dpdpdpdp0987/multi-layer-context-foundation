@echo off
REM Start FastAPI server (Windows)

echo Starting Multi-Layer Context Foundation API...
echo =============================================
echo.

REM Check if virtual environment is activated
if not defined VIRTUAL_ENV (
    echo WARNING: Virtual environment not activated
    echo Run: venv\Scripts\activate
    exit /b 1
)

REM Check dependencies
echo Checking dependencies...
python -c "import fastapi" 2>nul
if errorlevel 1 (
    echo ERROR: FastAPI not installed
    echo Install: pip install fastapi uvicorn
    exit /b 1
)

echo OK: Dependencies installed
echo.

REM Check .env file
if not exist ".env" (
    echo WARNING: .env file not found
    echo Creating from .env.example...
    copy .env.example .env
    echo OK: Created .env file (please review and update)
)

echo.

REM Start API server
echo Starting API server...
echo =============================================
echo.

if "%1"=="--dev" (
    echo Running in development mode with auto-reload
    uvicorn mlcf.api.main:app --host 0.0.0.0 --port 8000 --reload
) else (
    echo Running in production mode
    uvicorn mlcf.api.main:app --host 0.0.0.0 --port 8000
)