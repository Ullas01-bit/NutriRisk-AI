"""
Root CLI entry point to run Exploratory Data Analysis (EDA) on NutriRisk AI dataset.

Usage:
    python eda.py
"""
import sys
import os
import pandas as pd

from nutririsk.ml.eda import generate_eda_report

if __name__ == "__main__":
    print("=" * 70)
    print("NutriRisk AI -- Exploratory Data Analysis (EDA) Suite")
    print("=" * 70)
    
    data_path = "data/dataset.csv" if os.path.exists("data/dataset.csv") else "data/synthetic_dataset.csv"
    data_label = "REAL" if os.path.exists("data/dataset.csv") else "SYNTHETIC"
    
    if not os.path.exists(data_path):
        print(f"\n[ERROR] No dataset found at '{data_path}'.")
        print("Please run 'python train.py' to generate the baseline dataset first.")
        sys.exit(1)
        
    print(f"Loading dataset from '{data_path}' ({data_label} mode)...")
    df = pd.read_csv(data_path)
    
    print("Computing feature engineering and generating 10 analytical plots...")
    results = generate_eda_report(df, output_dir="reports", data_source_label=data_label)
    
    print("-" * 70)
    print("EDA COMPLETED SUCCESSFULLY")
    print("-" * 70)
    print(f"  Plots Generated : {len(results['plots'])}")
    for p in results['plots']:
        print(f"    * {p}")
    print(f"  Narrative Summary: {results['summary_path']}")
    print("=" * 70)
