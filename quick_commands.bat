@echo off
title Quick Production Commands
color 0F

echo ========================================
echo    QUICK PRODUCTION COMMANDS
echo ========================================
echo.
echo 1. Create Job Order
echo 2. Scan Barcode
echo 3. Check Progress
echo 4. List Active Jobs
echo 5. Exit
echo.

set /p choice="Select option (1-5): "

if "%choice%"=="1" (
    set /p product="Product MA Number: "
    set /p qty="Quantity: "
    set /p deadline="Deadline (YYYY-MM-DD): "
    python batch_production_system.py create-job %product% %qty% %deadline%
)

if "%choice%"=="2" (
    set /p barcode="Barcode: "
    echo.
    echo Stations: Cutting, CNC Milling, Assembling, Qualified
    set /p station="Station: "
    set /p user="Operator: "
    python batch_production_system.py scan %barcode% "%station%" %user%
)

if "%choice%"=="3" (
    set /p barcode="Barcode: "
    python batch_production_system.py progress %barcode%
)

if "%choice%"=="4" (
    python batch_production_system.py active
)

if "%choice%"=="5" (
    exit
)

pause