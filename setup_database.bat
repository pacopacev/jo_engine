@echo off
title Setup Production Database
color 0A

echo ========================================
echo    SETUP PRODUCTION DATABASE
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

REM Install required packages
echo Installing required packages...
pip install pandas psycopg2-binary openpyxl -q

echo.
echo Creating database schema...
echo.

REM Run the SQL script (you need to run this in DBeaver or psql)
echo Please run the following SQL in DBeaver to create the database schema:
echo.
echo ========================================
type database_schema.sql
echo ========================================
echo.
echo After running the SQL, press any key to continue...

pause

echo.
echo Database setup complete!
echo.
pause