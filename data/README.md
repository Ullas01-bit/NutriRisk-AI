# NutriRisk AI — Dataset Architecture & Integration Guide

## 1. Overview & Research Compliance Notice

> **IMPORTANT ACADEMIC ETHICS REQUIREMENT:**  
> Synthetic training data must **never** be presented or claimed as real clinical evidence in project reports, reviews, or viva presentations.  
> The included `synthetic_dataset.csv` is an academic algorithmic placeholder (6,000 samples) designed for development, feature testing, and validation of the end-to-end multi-model ML pipeline. Real-world validation requires empirical demographic/nutritional surveys.

---

## 2. Feature Schema & Data Dictionary

| Column Name | Type | Allowed Range / Categories | Description |
| :--- | :--- | :--- | :--- |
| `age` | Integer | 18 – 100 | Age of the individual in years (Adult cohort scope). |
| `sex` | String | `Female`, `Male` | Biological sex. |
| `height_cm` | Float | 120.0 – 220.0 cm | Standing body height measured in centimeters. |
| `weight_kg` | Float | 25.0 – 250.0 kg | Body weight measured in kilograms. |
| `food_groups` | Integer | 1 – 8 | Dietary diversity score based on daily consumption across standard nutritional food groups. |
| `meals_per_day`| Integer | 1 – 8 | Frequency of primary meals consumed daily. |
| `activity` | String | `Low`, `Moderate`, `High` | Self-reported physical activity intensity. |
| `income` | String | `Low`, `Middle`, `High` | Household socioeconomic income bracket. |
| `education` | String | `None`, `Primary`, `Secondary`, `Higher` | Highest attained educational level. |
| `residence` | String | `Urban`, `Rural` | Geographic residential classification. |
| `recent_illness`| String | `No`, `Yes` | Acute illness, infection, or fever in the prior 2 weeks. |
| `risk` | String | `Low Risk`, `Moderate Risk`, `High Risk` | **Target Variable**: Multi-class stratified nutritional risk category. |

---

## 3. How to Plug in a Real Dataset

1. Prepare your collected real-world survey dataset (e.g. from Kaggle, NFHS-5, DHS, or NHANES) as a CSV file.
2. Ensure the column names match the 12 fields defined above.
3. Save the file directly to:
   ```text
   data/dataset.csv
   ```
4. Run the training script from the project root:
   ```bash
   python train.py
   ```
5. The pipeline will automatically detect `data/dataset.csv`, bypass the synthetic generator, re-train all 5 algorithms using 5-fold cross validation, select the highest macro-F1 model, and update `model/metrics.json` and `model/model.joblib`.
