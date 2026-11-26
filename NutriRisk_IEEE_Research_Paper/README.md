# NutriRisk AI: IEEE Research Paper Package

## Paper Title
**“An Artificial Intelligence Framework for Predictive Nutritional Risk Assessment and Early Malnutrition Stratification Using Machine Learning Based on Demographic Data”**

This repository contains the complete, publication-grade IEEE Conference research paper package for the **NutriRisk AI** major project. All empirical findings, architectures, preprocessing steps, and experimental metrics are directly grounded in the production codebase.

---

## 📁 Package Contents

```
NutriRisk_IEEE_Research_Paper/
│
├── main.tex                       # Complete IEEEtran LaTeX source code
├── references.bib                 # Verified academic citations (BibTeX format)
├── IEEEtran.cls                   # Official IEEE Conference document class
├── README.md                      # Overleaf instructions and package overview
├── NutriRisk_Research_Paper.pdf   # Publication-ready rendered IEEE 2-column PDF
├── Overleaf_Project.zip           # 1-Click ready-to-upload Overleaf archive
│
└── figures/                       # High-resolution (300 DPI) publication diagrams
    ├── fig01_system_architecture.png       # Four-tier system architecture
    ├── fig02_nutririsk_workflow.png        # Operational triage workflow
    ├── fig03_preprocessing_pipeline.png    # Scikit-learn ColumnTransformer
    ├── fig04_training_pipeline.png         # 5-fold CV & model selection
    ├── fig05_prediction_stratification.png # Dual XAI & TreeSHAP engine
    ├── fig06_database_er.png               # Relational SQLite schema (ERD)
    ├── fig07_user_interaction.png          # Authenticated sequence diagram
    ├── fig08_model_comparison.png          # 5-algorithm benchmark bar chart
    ├── fig09_confusion_matrix.png          # XGBoost 3x3 confusion matrix
    └── fig10_roc_curves.png                # Multiclass One-vs-Rest ROC curves
```

---

## 🚀 How to Compile on Overleaf (1-Click Guide)

1. **Download the Archive**:
   - Locate `Overleaf_Project.zip` in this folder.
2. **Log into Overleaf**:
   - Navigate to [https://www.overleaf.com](https://www.overleaf.com).
3. **Upload the Project**:
   - Click **`New Project`** -> **`Upload Project`**.
   - Drag and drop `Overleaf_Project.zip` or select it from your file browser.
4. **Compile**:
   - Overleaf will automatically detect `main.tex` and `IEEEtran.cls`.
   - Click the green **`Recompile`** button.
   - The two-column IEEE formatted research paper will compile cleanly with all figures, tables, and mathematical equations.

---

## 🔬 Key Empirical Results Documented in the Paper

- **Dataset Size**: $N = 6{,}000$ adult records calibrated against global nutritional surveys (FAO, WHO, Global Hunger Index).
- **Split Ratio**: $80\%$ Training ($4{,}800$ instances) / $20\%$ Holdout Testing ($1{,}200$ instances) via stratified sampling.
- **Model Benchmark**:
  - **XGBoost (Champion)**: Accuracy = **$78.50\%$**, Macro-Precision = **$79.10\%$**, Macro-Recall = **$78.61\%$**, Macro-F1 = **$78.83\%$**, ROC-AUC = **$0.9241$**, 5-Fold CV F1 = $0.7886 \pm 0.0163$.
  - **Gradient Boosting**: Accuracy = $77.75\%$, Macro-F1 = $78.06\%$, ROC-AUC = $0.9237$.
  - **Random Forest**: Accuracy = $76.67\%$, Macro-F1 = $76.88\%$, ROC-AUC = $0.9140$.
  - **Decision Tree**: Accuracy = $74.17\%$, Macro-F1 = $74.71\%$, ROC-AUC = $0.8820$.
  - **Logistic Regression**: Accuracy = $70.67\%$, Macro-F1 = $70.77\%$, ROC-AUC = $0.8711$.
- **Critical Clinical Safety**:
  - **$0\%$ Critical False Negative Rate**: Exactly $0$ High-Risk patients misclassified as Low-Risk ($\mathbf{C}_{2,0} = 0$).
- **Top Predictive Drivers (Permutation Importance)**:
  1. Dietary Diversity ($17.39\%$)
  2. Chronological Age ($16.45\%$)
  3. Recent Acute Illness ($10.72\%$)
  4. BMI ($9.06\%$)
  5. Household Income ($7.73\%$)
  6. Meal Frequency ($6.55\%$)
