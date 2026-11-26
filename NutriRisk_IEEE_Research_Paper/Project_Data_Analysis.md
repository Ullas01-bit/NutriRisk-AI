# NutriRisk AI: Project Data Analysis & Empirical Technical Report

## 1. Executive Summary & Provenance
- **Project Title**: NutriRisk AI — An Artificial Intelligence Framework for Predictive Nutritional Risk Assessment and Early Malnutrition Stratification Using Machine Learning Based on Demographic Data.
- **Repository**: Root directory `D:\MAJOR PROJECT`
- **Data Source Verification**: `data/dataset.csv` contains $6{,}000$ verified records. Metadata in `data/dataset_metadata.json` confirms calibration against multi-national malnutrition surveys:
  - FAO Prevalence of Undernourishment statistics
  - Welthungerhilfe Global Hunger Index (GHI) datasets
  - WHO Child & Adult Anthropometric benchmarks
- **Target Variable**: `risk` — 3 Mutually Exclusive Clinical Classes:
  - **High Risk**: $2{,}195$ instances ($36.58\%$)
  - **Moderate Risk**: $2{,}103$ instances ($35.05\%$)
  - **Low Risk**: $1{,}702$ instances ($28.37\%$)
- **Data Quality**: Zero null or missing values across all 12 columns. Zero corrupt records.

---

## 2. Feature Schema & Engineering
| Column Name | Feature Type | Valid Clinical Domain | Description & Biological Meaning |
| :--- | :--- | :--- | :--- |
| `age` | Integer Numeric | $[18, 100]$ years | Chronological subject age |
| `sex` | Categorical | `["Female", "Male"]` | Biological sex |
| `height_cm` | Float Numeric | $[120.0, 220.0]$ cm | Standing height |
| `weight_kg` | Float Numeric | $[25.0, 250.0]$ kg | Total body mass |
| `bmi` | Engineered Numeric | $[10.0, 65.0]\;\text{kg/m}^2$ | Deterministic Body Mass Index: $\text{BMI} = \frac{\text{weight\_kg}}{(\text{height\_cm}/100)^2}$ |
| `food_groups` | Integer Numeric | $[1, 8]$ groups | Distinct food groups consumed in the preceding 24h |
| `meals_per_day` | Integer Numeric | $[1, 8]$ meals | Total meal consumption frequency |
| `activity` | Categorical | `["Low", "Moderate", "High"]` | Physical exertion tier |
| `income` | Categorical | `["Low", "Middle", "High"]` | Household socio-economic bracket |
| `education` | Categorical | `["None", "Primary", "Secondary", "Higher"]` | Educational attainment |
| `residence` | Categorical | `["Urban", "Rural"]` | Geographic settlement habitat |
| `recent_illness` | Categorical | `["No", "Yes"]` | Febrile or diarrheal illness in preceding 30 days |

---

## 3. Data-Leakage Prevention Architecture
All transformations are orchestrated via a Scikit-learn `ColumnTransformer` inside an immutable pipeline:
1. **Numerical Pipeline**:
   - `SimpleImputer(strategy='median')`
   - `StandardScaler()`
   - Fitted strictly on training folds ($N_{\text{train}} = 4{,}800$) to prevent validation/test leakage.
2. **Categorical Pipeline**:
   - `SimpleImputer(strategy='most_frequent')`
   - `OneHotEncoder(handle_unknown='ignore')`
   - Expands 6 categorical variables into 13 binary columns.
3. **Total Feature Dimensionality**: $6 \text{ (numeric)} + 13 \text{ (one-hot)} = 19 \text{ dimensions}$.

---

## 4. Benchmark Performance Metrics (Audit Grounding)
All metrics retrieved directly from `model/metrics.json` and `model/model_comparison.csv`:

### 4.1 Comparative Model Benchmark Table
| Classifier | 5-Fold CV Macro-F1 | Test Accuracy | Macro Precision | Macro Recall | Macro F1 | ROC-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **XGBoost (Champion)** | $0.7886 \pm 0.0163$ | **78.50%** | **79.10%** | **78.61%** | **78.83%** | **0.9241** |
| Gradient Boosting | **$0.7894 \pm 0.0151$** | 77.75% | 78.82% | 77.60% | 78.06% | 0.9237 |
| Random Forest | $0.7769 \pm 0.0098$ | 76.67% | 77.29% | 76.60% | 76.88% | 0.9140 |
| Decision Tree | $0.7468 \pm 0.0143$ | 74.17% | 75.87% | 74.15% | 74.71% | 0.8820 |
| Logistic Regression | $0.7084 \pm 0.0132$ | 70.67% | 70.87% | 70.68% | 70.77% | 0.8711 |

### 4.2 Champion XGBoost Confusion Matrix ($N_{\text{test}} = 1{,}200$)
```
                 Predicted Low   Predicted Mod   Predicted High   Total
Actual Low            276              63               1          340
Actual Moderate        48             302              71          421
Actual High             0              75             364          439
Total                 324             440             436        1,200
```
- **High-Risk Sensitivity (Recall)**: $364 / 439 = 82.92\%$
- **Low-Risk Sensitivity (Recall)**: $276 / 340 = 81.18\%$
- **Critical Misclassification Rate (High -> Low)**: **0 / 439 = 0.00%** (Safety Criterion Satisfied).

### 4.3 Feature Importance (Permutation Impact)
1. Dietary Diversity (`food_groups`): $+0.1739$
2. Chronological Age (`age`): $+0.1645$
3. Recent Illness (`recent_illness`): $+0.1072$
4. BMI (`height_cm` \& `weight_kg`): $+0.0906$
5. Household Income (`income`): $+0.0773$
6. Meal Frequency (`meals_per_day`): $+0.0655$
7. Residence (`residence`): $+0.0217$
8. Physical Activity (`activity`): $+0.0095$
9. Biological Sex (`sex`): $0.0000$
10. Education Level (`education`): $-0.0006$
