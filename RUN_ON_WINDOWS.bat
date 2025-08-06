@echo off
REM Batch script to run Polarion tests on Windows with connection diagnostics

echo ========================================
echo Polarion Test Runner for Windows
echo ========================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and add to PATH
    pause
    exit /b 1
)

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo No virtual environment found. Using system Python.
)

REM Load environment variables
if exist ".env" (
    echo Loading .env file...
) else (
    echo ERROR: .env file not found!
    echo Please create .env file with Polarion configuration
    pause
    exit /b 1
)

echo.
echo ========================================
echo Step 1: Running Connection Diagnostics
echo ========================================
echo.

python scripts\diagnose_connection.py
if errorlevel 1 (
    echo.
    echo ========================================
    echo Connection diagnostics failed!
    echo ========================================
    echo.
    echo Common solutions:
    echo 1. Add Polarion hostname to C:\Windows\System32\drivers\etc\hosts
    echo 2. Connect to VPN if Polarion is internal
    echo 3. Check firewall settings
    echo.
    echo Would you like to continue anyway? (y/n)
    set /p continue=
    if not "%continue%"=="y" (
        pause
        exit /b 1
    )
)

echo.
echo ========================================
echo Step 2: Testing Polarion Connection
echo ========================================
echo.

python scripts\test_polarion_connection.py
if errorlevel 1 (
    echo.
    echo Connection test failed!
    echo Please fix connection issues before running tests.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Step 3: Running Tests
echo ========================================
echo.
echo Select test option:
echo 1. Run all tests
echo 2. Run discovery tests only
echo 3. Run integration tests only
echo 4. Run specific test file
echo 5. Exit
echo.

set /p choice=Enter choice (1-5): 

if "%choice%"=="1" (
    echo Running all tests...
    python run_tests.py --env production --coverage
) else if "%choice%"=="2" (
    echo Running discovery tests...
    pytest tests\moduletest\test_discovery.py -v
) else if "%choice%"=="3" (
    echo Running integration tests...
    pytest -m integration -v
) else if "%choice%"=="4" (
    set /p testfile=Enter test file path: 
    echo Running %testfile%...
    pytest %testfile% -v
) else if "%choice%"=="5" (
    echo Exiting...
    exit /b 0
) else (
    echo Invalid choice!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Tests completed!
echo ========================================
echo.
echo Check results in:
echo - HTML Report: test_reports\latest\report.html
echo - Logs: test_reports\latest\logs\pytest.log
echo.

pause