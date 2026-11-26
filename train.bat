@echo off
echo ======================================================================
echo NutriRisk AI -- Retrain Machine Learning Models
echo ======================================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Please run setup.bat first!
    pause
    exit /b 1
)

echo Training all 5 algorithms (Logistic Regression, Decision Tree,
echo Random Forest, Gradient Boosting, XGBoost)...
echo.
venv\Scripts\python.exe train.py
echo.
pause
