@echo off
echo ======================================================================
echo NutriRisk AI -- Starting Local Clinical Decision-Support Server
echo ======================================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Please run setup.bat first!
    pause
    exit /b 1
)

echo Open your web browser and navigate to:
echo.
echo     http://127.0.0.1:5000
echo.
echo NOTE: First registered user automatically becomes the Administrator.
echo To STOP the server, press Ctrl + C in this terminal window.
echo ======================================================================
echo.

venv\Scripts\python.exe app.py
pause
