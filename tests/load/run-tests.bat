@echo off
REM Run Load Tests Script (Windows)

echo ===============================================
echo   MLCF Load Testing Suite
echo ===============================================
echo.

REM Configuration
if "%BASE_URL%"=="" set BASE_URL=http://localhost:8000
set OUTPUT_DIR=results\%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set OUTPUT_DIR=%OUTPUT_DIR: =0%
set REPORT_DIR=%OUTPUT_DIR%\reports

REM Create output directories
mkdir "%OUTPUT_DIR%" 2>nul
mkdir "%REPORT_DIR%" 2>nul

echo Configuration:
echo   Base URL: %BASE_URL%
echo   Output Dir: %OUTPUT_DIR%
echo.

REM Check if k6 is installed
k6 version >nul 2>&1
if errorlevel 1 (
    echo Error: k6 is not installed
    echo Install from: https://k6.io/docs/get-started/installation/
    exit /b 1
)

echo OK: k6 found

REM Check if API is running
curl -s "%BASE_URL%/health/simple" >nul 2>&1
if errorlevel 1 (
    echo Error: API is not responding at %BASE_URL%
    echo Start the API with: scripts\start_api.bat
    exit /b 1
)

echo OK: API is running
echo.

REM Test selection
set TEST_TYPE=%1
if "%TEST_TYPE%"=="" set TEST_TYPE=baseline

if "%TEST_TYPE%"=="baseline" (
    echo Running Baseline Test
    echo.
    k6 run --out json="%OUTPUT_DIR%\baseline.json" --summary-export="%REPORT_DIR%\baseline_summary.json" -e BASE_URL=%BASE_URL% scenarios\baseline.js
) else if "%TEST_TYPE%"=="stress" (
    echo Running Stress Test (10k+ users)
    echo.
    k6 run --out json="%OUTPUT_DIR%\stress.json" --summary-export="%REPORT_DIR%\stress_summary.json" -e BASE_URL=%BASE_URL% scenarios\stress.js
) else if "%TEST_TYPE%"=="spike" (
    echo Running Spike Test
    echo.
    k6 run --out json="%OUTPUT_DIR%\spike.json" --summary-export="%REPORT_DIR%\spike_summary.json" -e BASE_URL=%BASE_URL% scenarios\spike.js
) else if "%TEST_TYPE%"=="journey" (
    echo Running User Journey Test
    echo.
    k6 run --out json="%OUTPUT_DIR%\journey.json" --summary-export="%REPORT_DIR%\journey_summary.json" -e BASE_URL=%BASE_URL% scenarios\user-journey.js
) else (
    echo Unknown test type: %TEST_TYPE%
    echo.
    echo Usage: run-tests.bat [test-type]
    echo.
    echo Test types:
    echo   baseline  - Basic performance test
    echo   stress    - Stress test (10k+ users)
    echo   spike     - Sudden traffic spike test
    echo   journey   - User journey scenarios
    exit /b 1
)

echo.
echo Results saved to: %OUTPUT_DIR%
echo.