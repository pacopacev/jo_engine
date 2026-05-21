@echo off
title Batch Production System
color 0A

echo ========================================
echo    BATCH PRODUCTION SYSTEM
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed!
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

REM Install required packages if missing
python -c "import pandas" >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    pip install pandas psycopg2-binary openpyxl -q
)

echo.
echo Starting Production System...
echo.

python batch_production_system.py interactive

pause