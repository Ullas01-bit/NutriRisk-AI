@echo off
setlocal
echo ======================================================================
echo NutriRisk AI -- Launching Standalone Desktop Application Mode
echo ======================================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Please run setup.bat first!
    pause
    exit /b 1
)

:: Check if server is already responding on port 5000
netstat -ano | findstr :5000 | findstr LISTENING >nul
if %errorlevel% neq 0 (
    echo [*] Starting NutriRisk AI backend server...
    start /b "" venv\Scripts\python.exe app.py
    timeout /t 2 /nobreak >nul
) else (
    echo [*] NutriRisk AI backend server is already active on port 5000.
)

echo [*] Opening NutriRisk AI in standalone App Window...

:: Try Edge in App mode (installed on all Windows systems)
where msedge >nul 2>&1
if %errorlevel% equ 0 (
    start msedge --app=http://127.0.0.1:5000 --window-size=1280,820
    goto launched
)

:: Fallback to Chrome in App mode
where chrome >nul 2>&1
if %errorlevel% equ 0 (
    start chrome --app=http://127.0.0.1:5000 --window-size=1280,820
    goto launched
)

:: Generic browser fallback
start http://127.0.0.1:5000

:launched
echo [OK] NutriRisk AI App Window launched successfully!
echo To stop the backend when done, close the server process or terminal.
echo ======================================================================
timeout /t 3 /nobreak >nul
