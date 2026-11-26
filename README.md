# NutriRisk AI

**An Artificial Intelligence Framework for Predictive Nutritional Risk Assessment and Early Malnutrition Stratification Using Machine Learning Based on Demographic Data**

* **Target Audience:** Adults aged 18 and above
* **Scope:** Clinical decision-support prototype (not a standalone medical diagnosis tool)

---

## 1. Project Directory Structure

```text
MAJOR PROJECT/
├── app.py                      # Application entry point and server runner
├── train.py                    # Multi-algorithm ML trainer, CV evaluation, and serializer
├── features.py                 # Backward-compatible feature definitions and BMI logic
├── test_app.py                 # Automated integration and unit test runner
├── requirements.txt            # Python dependencies tested and pinned for Python 3.12
├── setup.bat                   # Automated Windows 1-click installation & verification
├── run.bat                     # Automated Windows 1-click server launch
├── train.bat                   # Automated Windows 1-click model retraining
├── README.md                   # Complete architectural and setup guide
│
├── nutririsk/                  # Core modular application package
│   ├── __init__.py             # Application factory (create_app)
│   ├── config.py               # Configuration constants, thresholds, advice mappings
│   ├── db.py                   # SQLite connection helpers and schema migration
│   │
│   ├── auth/                   # Authentication subsystem
│   │   ├── __init__.py
│   │   ├── routes.py           # /login, /register, /reset, /profile, /logout
│   │   └── utils.py            # Password hashing, @login_required, @admin_required
│   │
│   ├── ml/                     # Machine Learning engine
│   │   ├── __init__.py
│   │   ├── features.py         # Schemas, feature engineering (BMI), input boundary validation
│   │   ├── training.py         # 5-algorithm trainer (LR, DT, RF, GB, XGBoost)
│   │   ├── prediction.py       # Inference service and class probability computation
│   │   └── explainability.py   # Occlusion-based local feature attribution (XAI)
│   │
│   ├── routes/                 # Web presentation blueprints
│   │   ├── __init__.py
│   │   ├── main.py             # Landing page (/) and model benchmarks (/model)
│   │   ├── assessment.py       # Patient prediction (/predict), result breakdown (/result/<id>), history (/history)
│   │   ├── analytics.py        # Population distribution and timeline analytics (/analytics)
│   │   └── admin.py            # Administrative oversight and user directory (/admin)
│   │
│   ├── static/                 # Offline static assets (zero CDN dependencies)
│   │   ├── css/
│   │   │   ├── bootstrap.min.css # Offline Bootstrap 5
│   │   │   └── style.css       # Custom clinical teal styling
│   │   ├── js/
│   │   │   ├── bootstrap.bundle.min.js
│   │   │   ├── chart.umd.min.js  # Offline Chart.js
│   │   │   └── main.js
│   │   └── img/
│   │
│   └── templates/              # HTML5 Jinja2 Templates (Clean UTF-8, no mojibake)
│       ├── base.html           # Master layout with navbar, alerts, footer, and disclaimer
│       ├── home.html           # Project landing overview and objectives
│       ├── auth.html           # Login, registration, and password reset form
│       ├── profile.html        # User account metrics and profile editor
│       ├── predict.html        # Nutritional risk input form with range enforcement
│       ├── result.html         # Stratification level, confidence, class bars, XAI factors, advice
│       ├── history.html        # Searchable and filterable assessment records
│       ├── analytics.html      # Interactive Chart.js graphs (Risk, Age, Sex, Trends)
│       ├── model.html          # Preprocessing details, 5-model table, confusion matrix, importance
│       └── admin.html          # User directory, system activity audit logs
│
├── data/                       # Datasets directory
│   ├── synthetic_dataset.csv   # 6,000-row placeholder benchmark dataset
│   └── README.md               # Real dataset ingestion guide and feature dictionary
│
├── model/                      # Serialized ML artifacts
│   ├── model.joblib            # Trained scikit-learn / XGBoost pipeline + reference values
│   └── metrics.json            # Model evaluation metrics, confusion matrix, permutation scores
│
└── tests/                      # Automated test suite
    ├── __init__.py
    ├── test_app.py             # End-to-end route and access control integration tests
    └── test_ml.py              # Feature engineering and inference unit tests
```

---

## 2. Prerequisites & Compatibility

* **Operating System:** Windows 10 or Windows 11 (64-bit)
* **Python Runtime:** Python **3.10, 3.11, or 3.12** *(Recommended: Python 3.12)*
  > **Note on Python 3.15:** Experimental / pre-release builds of Python 3.15 are **not compatible** with pre-compiled wheels for `numpy` and `scikit-learn` C-extensions. Use Python 3.12.

---

## 3. Quick Start (Windows Automated Setup)

### Option A: One-Click Setup (Recommended for Beginners)
1. Double-click `setup.bat`.
   * It checks for Python 3.12.
   * It creates the isolated `venv` virtual environment.
   * It installs all dependencies from `requirements.txt`.
   * It initializes `nutririsk.db` without overwriting existing data.
   * It checks and verifies the machine learning model artifacts.
   * It executes the automated test suite.
2. Double-click `run.bat` to start the application.
3. Open your browser and go to:
   ```text
   http://127.0.0.1:5000
   ```

---

### Option B: Manual Setup via PowerShell / Command Prompt

```powershell
# 1. Create a Python 3.12 virtual environment
py -3.12 -m venv venv

# 2. Activate the virtual environment
.\venv\Scripts\Activate.ps1

# 3. Upgrade pip and install pinned dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Initialize SQLite database tables
python -c "from nutririsk import create_app; create_app()"

# 5. Run the model training pipeline (generates model/model.joblib & model/metrics.json)
python train.py

# 6. Execute the automated test suite
python test_app.py

# 7. Start the Flask development server
python app.py
```

---

## 4. How to Use the Application

1. **First-Time Registration:**
   * Navigate to `http://127.0.0.1:5000/register`.
   * Register your first account. **The first registered user is automatically assigned the `admin` role.**
2. **Perform an Assessment:**
   * Go to **Assess** (`/predict`).
   * Enter subject details (Age 18–100, Height, Weight, Food Groups 1–8, Meals per Day, Lifestyle factors).
   * Click **Assess Nutritional Risk**.
3. **View Explainable Results:**
   * Inspect the **Stratified Risk Level** (Low, Moderate, High).
   * Review the **Class Probability** breakdown.
   * Examine the **Explainable AI (XAI)** factor attribution table showing which indicators actively pushed the prediction toward risk ($\uparrow$) versus protective factors ($\downarrow$).
4. **Batch Patient Screening (CSV Upload):**
   * Go to **Batch Screening** (`/batch`).
   * Download the provided sample CSV template (`/batch/sample-template`).
   * Upload a multi-patient CSV dataset (up to 5 MB) for bulk evaluation.
   * Review the automated summary KPI cards, validation exclusions, and interactive patient stratification table.
5. **Inspect Analytics & History:**
   * Review all saved records under **History** (`/history`) with keyword and category filters.
   * View population charts (Doughnut, Bar, Pie, Line) under **Analytics** (`/analytics`).
6. **Admin Console:**
   * Admins can navigate to **Admin Console** (`/admin`) to inspect all registered user accounts and system activity audit logs.

---

## 5. Stopping the Application

To shut down the web server:
* Click inside the terminal window running `app.py` or `run.bat`.
* Press `Ctrl + C`.

---

## 6. How to Integrate a Real Clinical / Demographic Dataset

1. Prepare your empirical dataset (e.g. from Kaggle, NFHS-5, DHS, or NHANES) as a CSV file.
2. Ensure columns match the schema:
   `age, sex, height_cm, weight_kg, food_groups, meals_per_day, activity, income, education, residence, recent_illness, risk`
3. Save the file directly to:
   ```text
   data/dataset.csv
   ```
4. Double-click `train.bat` (or execute `python train.py`).
5. The pipeline automatically loads the real dataset, trains all 5 algorithms, evaluates cross-validation metrics, updates `model/metrics.json`, and deploys the best performing model.

---

## 7. Machine Learning Algorithms Compared

| Algorithm | Type | Test Accuracy | Macro-F1 | ROC-AUC | 5-Fold CV F1 |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Logistic Regression** | Linear Baseline | 67.00% | 0.6470 | 0.8470 | 0.6410 |
| **Decision Tree** | Non-linear Tree | 68.60% | 0.6770 | 0.8210 | 0.6690 |
| **Random Forest** | Bagging Ensemble | 72.10% | 0.7100 | 0.8770 | 0.7040 |
| **Gradient Boosting** | Boosting Ensemble | 73.80% | 0.7270 | 0.8960 | 0.7110 |
| **XGBoost** | Optimized Gradient Boosting | **74.00%** | **0.7315** | **0.8910** | **0.7135** |

*Evaluation conducted on 80:20 stratified split with 5-fold cross validation. Deployed winner selected by macro-averaged F1-score.*
