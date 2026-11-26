@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo NutriRisk AI -- Automated Windows Setup & Verification
echo ======================================================================
echo.

:: 1. Check Python installation
echo [1/6] Checking Python installation...
py -3.12 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=py -3.12"
    echo Found Python 3.12 via Python Launcher.
) else (
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        set "PY_CMD=python"
        echo Found default system Python.
    ) else (
        echo [ERROR] Python is not found on your system PATH.
        echo Please install Python 3.10, 3.11, or 3.12 from python.org (ensure 'Add Python to PATH' is checked).
        pause
        exit /b 1
    )
)

:: 2. Create Virtual Environment
echo.
echo [2/6] Checking virtual environment (venv)...
if not exist "venv\Scripts\python.exe" (
    echo Creating new virtual environment in 'venv' folder...
    %PY_CMD% -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
) else (
    echo Virtual environment already exists.
)

:: 3. Install Dependencies
echo.
echo [3/6] Installing / updating required dependencies...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Dependency installation encountered an issue.
    pause
    exit /b 1
)

:: 4. Initialize Database & Safe Migrations
echo.
echo [4/6] Checking SQLite database and schema migrations...
venv\Scripts\python.exe init_db.py
if %errorlevel% neq 0 (
    echo [ERROR] Database initialization encountered an error.
    pause
    exit /b 1
)

:: 5. Check ML Model Artifacts
echo.
echo [5/6] Checking machine learning model artifacts...
if not exist "model\model.joblib" (
    echo No trained model found. Checking for training dataset...
    if exist "data\dataset.csv" (
        echo Real dataset found at data\dataset.csv. Training models...
        venv\Scripts\python.exe train.py
    ) else if exist "data\synthetic_dataset.csv" (
        echo Training on placeholder benchmark dataset (data\synthetic_dataset.csv)...
        venv\Scripts\python.exe train.py
    ) else (
        echo [WARNING] No dataset found in data\ folder. Model training skipped.
    )
) else (
    echo Model artifact 'model\model.joblib' exists. Skipping re-training.
)

:: 6. Run Automated Tests
echo.
echo [6/6] Running system verification tests...
venv\Scripts\python.exe test_app.py
if %errorlevel% neq 0 (
    echo [WARNING] Some tests did not pass. Please check the logs above.
) else (
    echo All verification tests passed successfully!
)

echo.
echo ======================================================================
echo Setup Complete! To start the application, double-click run.bat
echo or run: venv\Scripts\python.exe app.py
echo ======================================================================
pause
