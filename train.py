"""
Training pipeline CLI entry point for NutriRisk AI.
Run directly using: python train.py

What this script does
---------------------
1. Validates the dataset schema before training begins
2. Prints a data quality summary
3. Trains 5 ML models with 5-fold cross-validation
4. Selects and serializes the best model
5. Prints a clear results table with CV mean ± std

Artifacts produced
------------------
  model/model.joblib         — Best model pipeline (used by the web app)
  model/metrics.json         — Full evaluation metrics (used by /model page)
  model/training_config.json — Hyperparameters, versions, seeds, split ratios
  model/model_comparison.csv — Side-by-side metrics table for all 5 models
"""
import sys

# Ensure UTF-8 output handling on Windows consoles where possible
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from nutririsk.ml.training import train_and_evaluate

if __name__ == "__main__":
    print("=" * 70)
    print("NutriRisk AI -- Machine Learning Model Training & Evaluation")
    print("=" * 70)
    try:
        metrics = train_and_evaluate(
            data_path="data/dataset.csv",
            synthetic_path="data/synthetic_dataset.csv",
            model_save_path="model/model.joblib",
            metrics_save_path="model/metrics.json"
        )
        print("\n" + "-" * 70)
        print("  TRAINING COMPLETE")
        print("-" * 70)
        print(f"  Data Source   : {metrics.get('data_source_label', 'UNKNOWN')}")
        print(f"  Dataset Rows  : {metrics['n_rows']:,}  "
              f"(Train: {metrics['n_train']:,} | Test: {metrics['n_test']:,})")
        print(f"  Best Model    : {metrics['best']}")
        print()

        # Print all model results sorted by F1 descending
        print(f"  {'Model':<22} {'Acc':>6} {'F1':>7} {'AUC':>7} {'CV F1 mean+-std':>16}")
        print(f"  {'-'*22} {'-'*6} {'-'*7} {'-'*7} {'-'*16}")
        sorted_models = sorted(
            metrics["models"].items(),
            key=lambda kv: kv[1]["f1"],
            reverse=True
        )
        for name, res in sorted_models:
            marker = " [BEST]" if name == metrics["best"] else ""
            cv_mean = res.get("cv_f1_mean", res.get("cv_f1", 0))
            cv_std  = res.get("cv_f1_std", 0)
            print(
                f"  {name:<22} {res['accuracy']:>6.3f} {res['f1']:>7.4f} "
                f"{res['roc_auc']:>7.4f} {cv_mean:.4f}+-{cv_std:.4f}{marker}"
            )

        print()
        print("  Artifacts saved:")
        print("    model/model.joblib         -- Serialized pipeline")
        print("    model/metrics.json         -- Evaluation metrics")
        print("    model/training_config.json -- Hyperparameters & versions")
        print("    model/model_comparison.csv -- All-model comparison table")
        print("-" * 70)

        if metrics.get("data_source_label") == "SYNTHETIC":
            print()
            print("  [!] WARNING: Model trained on SYNTHETIC placeholder data.")
            print("      Results do NOT reflect real-world nutritional risk patterns.")
            print("      Replace data/dataset.csv with a validated research dataset")
            print("      and retrain before any academic or research use.")
        print()

    except Exception as e:
        print(f"\n[ERROR] Training failed: {e}")
        print("\nCommon fixes:")
        print("  • Ensure your virtual environment is activated: venv\\Scripts\\activate")
        print("  • Ensure all dependencies are installed: pip install -r requirements.txt")
        print("  • If using a real dataset, ensure 'data/dataset.csv' passes schema validation.")
        sys.exit(1)
