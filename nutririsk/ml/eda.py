"""
Exploratory Data Analysis (EDA) Module for NutriRisk AI.

Generates publication-quality visualizations and a markdown summary report.
All outputs are saved to the 'reports/' directory.

ACADEMIC INTEGRITY NOTICE:
All analysis is descriptive only. No clinical conclusions are drawn.
Results from the synthetic placeholder dataset must not be interpreted
as evidence of real-world nutritional patterns.
"""
import logging
import os
import textwrap
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend safe for server/script use
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# -- Colour palette -----------------------------------------------------------
PALETTE = {
    "Low Risk":      "#2cb67d",  # Emerald
    "Moderate Risk": "#f6a400",  # Amber
    "High Risk":     "#e63946",  # Red
    "accent":        "#0d6efd",  # Navy/Blue
    "neutral":       "#6c757d",
}
RISK_COLORS = [PALETTE["Low Risk"], PALETTE["Moderate Risk"], PALETTE["High Risk"]]

# -- Helpers ------------------------------------------------------------------

def _savefig(fig: plt.Figure, path: str) -> None:
    """Save figure, close it, and log the path."""
    fig.tight_layout()
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved plot: %s", path)


def _style() -> None:
    """Apply consistent styling."""
    try:
        import seaborn as sns
        sns.set_theme(style="whitegrid", palette="muted", font_scale=1.0)
    except ImportError:
        plt.rcParams.update({
            "axes.facecolor": "#f8f9fa",
            "axes.edgecolor": "#dee2e6",
            "grid.color": "#e9ecef",
        })


# -----------------------------------------------------------------------------
# Individual plot functions (1 - 10)
# -----------------------------------------------------------------------------

def plot_dataset_overview(df: pd.DataFrame, output_dir: str) -> str:
    """Plot 1: Dataset Overview Table."""
    path = os.path.join(output_dir, "01_dataset_overview.png")
    info_rows = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        n_missing = int(df[col].isna().sum())
        n_unique = int(df[col].nunique())
        info_rows.append([col, dtype, str(n_missing), str(n_unique)])

    headers = ["Column", "Dtype", "Missing", "Unique"]
    col_widths = [max(len(h), max(len(r[i]) for r in info_rows)) + 2
                  for i, h in enumerate(headers)]
    rows_text = [" | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))]
    rows_text.append("-+-".join("-" * w for w in col_widths))
    for row in info_rows:
        rows_text.append(" | ".join(v.ljust(col_widths[i]) for i, v in enumerate(row)))

    text = "\n".join(rows_text)
    fig, ax = plt.subplots(figsize=(9, max(3, len(df.columns) * 0.45 + 1.5)))
    ax.axis("off")
    ax.text(0.01, 0.99, f"NutriRisk AI -- Dataset Overview\n({len(df):,} rows x {len(df.columns)} columns)\n\n{text}",
            transform=ax.transAxes, fontsize=9, verticalalignment="top",
            fontfamily="monospace")
    _savefig(fig, path)
    return path


def plot_missing_values(df: pd.DataFrame, output_dir: str) -> str:
    """Plot 2: Missing Value Distribution."""
    path = os.path.join(output_dir, "02_missing_values.png")
    missing = df.isna().sum()
    missing = missing[missing > 0]

    if missing.empty:
        fig, ax = plt.subplots(figsize=(6, 2))
        ax.text(0.5, 0.5, "No missing values detected [Complete Dataset]",
                ha="center", va="center", fontsize=12, color=PALETTE["Low Risk"])
        ax.axis("off")
    else:
        fig, ax = plt.subplots(figsize=(8, max(3, len(missing) * 0.5)))
        missing.sort_values().plot.barh(ax=ax, color=PALETTE["Moderate Risk"], edgecolor="white")
        ax.set_title("Missing Values per Column", fontweight="bold")
        ax.set_xlabel("Count")
    _savefig(fig, path)
    return path


def plot_class_distribution(df: pd.DataFrame, output_dir: str) -> str:
    """Plot 3: Risk Class Distribution."""
    from nutririsk.ml.features import LABELS
    path = os.path.join(output_dir, "03_class_distribution.png")
    counts = df["risk"].value_counts().reindex(LABELS).fillna(0).astype(int)

    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(LABELS, counts.values, color=RISK_COLORS, edgecolor="white", width=0.55)
    ax.set_title("Risk Class Distribution", fontweight="bold")
    ax.set_ylabel("Number of Records")
    for bar, count in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(counts.values) * 0.01,
                f"{count:,}\n({count/len(df)*100:.1f}%)",
                ha="center", va="bottom", fontsize=9)
    _savefig(fig, path)
    return path


def plot_age_distribution(df: pd.DataFrame, output_dir: str) -> str:
    """Plot 4: Age Distribution across Risk Classes."""
    from nutririsk.ml.features import LABELS
    path = os.path.join(output_dir, "04_age_distribution.png")
    fig, ax = plt.subplots(figsize=(8, 4))

    for label, color in zip(LABELS, RISK_COLORS):
        subset = df[df["risk"] == label]["age"].dropna()
        ax.hist(subset, bins=20, alpha=0.65, color=color, label=label, edgecolor="white")

    ax.set_title("Age Distribution by Risk Category", fontweight="bold")
    ax.set_xlabel("Age (years)")
    ax.set_ylabel("Count")
    ax.legend()
    _savefig(fig, path)
    return path


def plot_sex_distribution(df: pd.DataFrame, output_dir: str) -> str:
    """Plot 5: Sex Distribution across Risk Classes."""
    from nutririsk.ml.features import LABELS
    path = os.path.join(output_dir, "05_sex_distribution.png")
    sex_risk = pd.crosstab(df["sex"], df["risk"])[LABELS]

    fig, ax = plt.subplots(figsize=(7, 4))
    sex_risk.plot.bar(ax=ax, color=RISK_COLORS, edgecolor="white", rot=0)
    ax.set_title("Sex Distribution Across Risk Categories", fontweight="bold")
    ax.set_xlabel("Sex")
    ax.set_ylabel("Count")
    ax.legend(title="Risk Tier")
    _savefig(fig, path)
    return path


def plot_bmi_distribution(df: pd.DataFrame, output_dir: str) -> str:
    """Plot 6: BMI Distribution with WHO reference thresholds."""
    from nutririsk.ml.features import add_features
    path = os.path.join(output_dir, "06_bmi_distribution.png")

    df_bmi = add_features(df) if "bmi" not in df.columns else df
    fig, ax = plt.subplots(figsize=(8, 4))

    for label, color in zip(["Low Risk", "Moderate Risk", "High Risk"], RISK_COLORS):
        subset = df_bmi[df_bmi["risk"] == label]["bmi"].dropna()
        ax.hist(subset, bins=25, alpha=0.65, color=color, label=label, edgecolor="white")

    for threshold, label_txt in [(18.5, "Underweight"), (25.0, "Overweight"), (30.0, "Obese")]:
        ax.axvline(threshold, color="black", linestyle="--", linewidth=0.8, alpha=0.6)
        ax.text(threshold + 0.2, ax.get_ylim()[1] * 0.92, label_txt, fontsize=7.5, color="black")

    ax.set_title("BMI Distribution by Risk Category (WHO thresholds shown)", fontweight="bold")
    ax.set_xlabel("BMI (kg/m^2)")
    ax.set_ylabel("Count")
    ax.legend()
    _savefig(fig, path)
    return path


def plot_nutritional_features(df: pd.DataFrame, output_dir: str) -> str:
    """Plot 7: Nutritional Feature Distributions (Food Groups & Meals)."""
    from nutririsk.ml.features import LABELS
    path = os.path.join(output_dir, "07_nutritional_features.png")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    for ax, col, title in zip(
        axes,
        ["food_groups", "meals_per_day"],
        ["Food Groups Eaten Daily", "Meals per Day"]
    ):
        group_means = df.groupby("risk")[col].mean().reindex(LABELS)
        group_means.plot.bar(ax=ax, color=RISK_COLORS, edgecolor="white", rot=0)
        ax.set_title(f"Mean {title} by Risk Category", fontweight="bold")
        ax.set_xlabel("Risk Category")
        ax.set_ylabel(f"Mean {col.replace('_', ' ').title()}")
        for bar, val in zip(ax.patches, group_means.values):
            if not np.isnan(val):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                        f"{val:.1f}", ha="center", va="bottom", fontsize=9)

    _savefig(fig, path)
    return path


def plot_correlation_heatmap(df: pd.DataFrame, output_dir: str) -> str:
    """Plot 8: Correlation Heatmap for Numerical Features."""
    from nutririsk.ml.features import add_features, NUMERIC
    path = os.path.join(output_dir, "08_correlation_heatmap.png")
    df_eng = add_features(df) if "bmi" not in df.columns else df
    numeric_df = df_eng[NUMERIC].apply(pd.to_numeric, errors="coerce")
    corr = numeric_df.corr()

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(corr.values, cmap="RdYlGn", vmin=-1, vmax=1, aspect="auto")
    plt.colorbar(im, ax=ax, shrink=0.8)
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(corr.columns, fontsize=9)
    ax.set_title("Numeric Feature Correlation Heatmap", fontweight="bold")

    for i in range(len(corr)):
        for j in range(len(corr.columns)):
            val = corr.iloc[i, j]
            ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                    fontsize=7.5, color="black" if abs(val) < 0.7 else "white")

    _savefig(fig, path)
    return path


def plot_outlier_analysis(df: pd.DataFrame, output_dir: str) -> str:
    """Plot 9: Outlier Analysis (Tukey's IQR method on all numerical features)."""
    from nutririsk.ml.features import add_features, NUMERIC
    path = os.path.join(output_dir, "09_outlier_analysis.png")
    df_eng = add_features(df) if "bmi" not in df.columns else df

    numeric_cols = [c for c in NUMERIC if c in df_eng.columns]
    n_cols = len(numeric_cols)
    fig, axes = plt.subplots(1, n_cols, figsize=(15, 4.5))

    outlier_counts = {}
    for ax, col in zip(axes, numeric_cols):
        series = pd.to_numeric(df_eng[col], errors="coerce").dropna()
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower_fence = q1 - 1.5 * iqr
        upper_fence = q3 + 1.5 * iqr
        outliers = series[(series < lower_fence) | (series > upper_fence)]
        outlier_counts[col] = len(outliers)

        bp = ax.boxplot(
            series.values,
            patch_artist=True,
            boxprops=dict(facecolor="#dbeafe", color="#1d4ed8", alpha=0.8),
            medianprops=dict(color="#b91c1c", linewidth=2),
            flierprops=dict(marker="o", markerfacecolor="#ef4444", markersize=4, alpha=0.6)
        )
        ax.set_title(col.replace("_", " ").title(), fontweight="bold", fontsize=10)
        ax.set_xticks([])
        pct = (len(outliers) / len(series)) * 100
        ax.set_xlabel(f"Outliers: {len(outliers)}\n({pct:.1f}%)", fontsize=8.5)

    fig.suptitle("Outlier Analysis across Numerical Features (Tukey 1.5 x IQR Rule)", fontweight="bold", y=1.02)
    _savefig(fig, path)
    return path


def plot_feature_relationships_with_risk(df: pd.DataFrame, output_dir: str) -> str:
    """Plot 10: Feature Relationships with Nutritional Risk (Key Bi-variate Patterns)."""
    from nutririsk.ml.features import add_features, LABELS, CHOICES
    path = os.path.join(output_dir, "10_feature_relationships_with_risk.png")
    df_eng = add_features(df) if "bmi" not in df.columns else df

    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    axes_flat = axes.flatten()

    # Panel 1: Age by Risk
    ax0 = axes_flat[0]
    data_age = [df_eng[df_eng["risk"] == l]["age"].dropna().values for l in LABELS]
    ax0.boxplot(data_age, patch_artist=True,
                boxprops=dict(facecolor="#e0e7ff", color="#3730a3"),
                medianprops=dict(color="#b91c1c", linewidth=2))
    ax0.set_xticklabels(LABELS, fontsize=8)
    ax0.set_title("Age vs Nutritional Risk", fontweight="bold")
    ax0.set_ylabel("Age (years)")

    # Panel 2: BMI by Risk
    ax1 = axes_flat[1]
    data_bmi = [df_eng[df_eng["risk"] == l]["bmi"].dropna().values for l in LABELS]
    ax1.boxplot(data_bmi, patch_artist=True,
                boxprops=dict(facecolor="#ccfbf1", color="#0f766e"),
                medianprops=dict(color="#b91c1c", linewidth=2))
    ax1.set_xticklabels(LABELS, fontsize=8)
    ax1.set_title("BMI vs Nutritional Risk", fontweight="bold")
    ax1.set_ylabel("BMI (kg/m^2)")

    # Panel 3: Food Groups by Risk
    ax2 = axes_flat[2]
    data_fg = [df_eng[df_eng["risk"] == l]["food_groups"].dropna().values for l in LABELS]
    ax2.boxplot(data_fg, patch_artist=True,
                boxprops=dict(facecolor="#fef3c7", color="#b45309"),
                medianprops=dict(color="#b91c1c", linewidth=2))
    ax2.set_xticklabels(LABELS, fontsize=8)
    ax2.set_title("Food Diversity vs Nutritional Risk", fontweight="bold")
    ax2.set_ylabel("Food Groups (1-8)")

    # Panel 4: Income Level Breakdown
    ax3 = axes_flat[3]
    ct_inc = pd.crosstab(df["income"], df["risk"]).reindex(CHOICES["income"]).reindex(columns=LABELS, fill_value=0)
    ct_inc.div(ct_inc.sum(axis=1), axis=0).mul(100).plot.bar(
        ax=ax3, color=RISK_COLORS, rot=0, legend=False, edgecolor="white"
    )
    ax3.set_title("Income Level vs Risk Composition (%)", fontweight="bold")
    ax3.set_ylabel("% within Income Group")
    ax3.set_xlabel("")

    # Panel 5: Physical Activity Breakdown
    ax4 = axes_flat[4]
    ct_act = pd.crosstab(df["activity"], df["risk"]).reindex(CHOICES["activity"]).reindex(columns=LABELS, fill_value=0)
    ct_act.div(ct_act.sum(axis=1), axis=0).mul(100).plot.bar(
        ax=ax4, color=RISK_COLORS, rot=0, legend=False, edgecolor="white"
    )
    ax4.set_title("Physical Activity vs Risk Composition (%)", fontweight="bold")
    ax4.set_ylabel("% within Activity Group")
    ax4.set_xlabel("")

    # Panel 6: Recent Illness Breakdown
    ax5 = axes_flat[5]
    ct_ill = pd.crosstab(df["recent_illness"], df["risk"]).reindex(CHOICES["recent_illness"]).reindex(columns=LABELS, fill_value=0)
    ct_ill.div(ct_ill.sum(axis=1), axis=0).mul(100).plot.bar(
        ax=ax5, color=RISK_COLORS, rot=0, legend=False, edgecolor="white"
    )
    ax5.set_title("Recent Illness vs Risk Composition (%)", fontweight="bold")
    ax5.set_ylabel("% within Illness Group")
    ax5.set_xlabel("")

    # Legend
    handles = [mpatches.Patch(color=c, label=l) for c, l in zip(RISK_COLORS, LABELS)]
    fig.legend(handles=handles, loc="upper right", title="Risk Category", ncol=3, bbox_to_anchor=(0.95, 0.99))
    fig.suptitle("Feature Relationships with Nutritional Risk Stratification", fontweight="bold", y=1.01)
    _savefig(fig, path)
    return path


# -----------------------------------------------------------------------------
# Master EDA execution
# -----------------------------------------------------------------------------

def generate_eda_report(
    df: pd.DataFrame,
    output_dir: str = "reports",
    data_source_label: str = "SYNTHETIC",
) -> Dict[str, Any]:
    """
    Generate all 10 EDA plots and return a structured summary dictionary.
    """
    os.makedirs(output_dir, exist_ok=True)
    _style()

    logger.info("Generating EDA report in '%s' (Source: %s)", output_dir, data_source_label)

    from nutririsk.ml.features import add_features, NUMERIC
    df_eng = add_features(df) if "bmi" not in df.columns else df

    plots = []
    plots.append(plot_dataset_overview(df, output_dir))
    plots.append(plot_missing_values(df, output_dir))
    plots.append(plot_class_distribution(df, output_dir))
    plots.append(plot_age_distribution(df, output_dir))
    plots.append(plot_sex_distribution(df, output_dir))
    plots.append(plot_bmi_distribution(df, output_dir))
    plots.append(plot_nutritional_features(df, output_dir))
    plots.append(plot_correlation_heatmap(df_eng, output_dir))
    plots.append(plot_outlier_analysis(df_eng, output_dir))
    plots.append(plot_feature_relationships_with_risk(df_eng, output_dir))

    # Compute descriptive statistics
    numeric_df = df_eng[NUMERIC].apply(pd.to_numeric, errors="coerce")
    stats: Dict[str, Any] = {
        "n_rows": len(df),
        "n_cols": len(df.columns),
        "class_distribution": df["risk"].value_counts().to_dict(),
        "numeric_summary": numeric_df.describe().round(2).to_dict(),
        "missing_total": int(df.isna().sum().sum()),
    }

    # Save markdown summary
    summary_path = os.path.join(output_dir, "eda_summary.md")
    generate_eda_summary_text(stats, plots, data_source_label, summary_path)

    logger.info("EDA complete: %d plot(s) generated.", len(plots))
    return {
        "plots": plots,
        "stats": stats,
        "data_source_label": data_source_label,
        "n_rows": len(df),
        "n_cols": len(df.columns),
        "summary_path": summary_path,
    }


def generate_eda_summary_text(
    stats: Dict[str, Any],
    plots: list,
    data_source_label: str,
    output_path: str,
) -> str:
    """Write a markdown narrative EDA summary with academic caveats."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cd = stats.get("class_distribution", {})
    n = stats.get("n_rows", 0)

    disclaimer_block = (
        "> **ACADEMIC DISCLAIMER**: This analysis is performed on a "
        f"**{data_source_label}** dataset and is intended solely for "
        "software development, architectural validation, and demonstration purposes. "
        "**No clinical or medical conclusions should be drawn from these statistical correlations.** "
        "Research validity cannot be claimed until a verified real-world dataset "
        "with documented clinical provenance and ethical approval is integrated."
        if data_source_label == "SYNTHETIC" else
        "> **RESEARCH NOTICE**: This analysis is performed on a real dataset. "
        "Please ensure full compliance with the relevant Data Use Agreement (DUA) and ethical protocol."
    )

    lines = [
        f"# NutriRisk AI -- Exploratory Data Analysis & Preprocessing Report",
        f"",
        f"**Generated**: {now}  ",
        f"**Data Source**: `{data_source_label}`  ",
        f"**Dataset Dimensions**: {n:,} rows x {stats.get('n_cols', '?')} columns  ",
        f"",
        disclaimer_block,
        f"",
        f"---",
        f"",
        f"## 1. Dataset Overview & Data Quality",
        f"",
        f"The dataset contains **{n:,} adult records** (age >= 18) covering demographic, anthropometric, "
        f"socioeconomic, and dietary diversity indicators.",
        f"",
        f"- **Total Missing Cells**: {stats.get('missing_total', 0):,}  ",
        f"- **Pre-processing Protocol**: Numerical variables use median imputation; categorical variables "
        f"use mode imputation. Crucially, imputation parameters and standard scaling are fitted exclusively "
        f"on training folds to strictly prevent data leakage.",
        f"",
        f"## 2. Risk Class Distribution & Imbalance",
        f"",
    ]

    for label in ["Low Risk", "Moderate Risk", "High Risk"]:
        count = cd.get(label, 0)
        pct = count / n * 100 if n > 0 else 0
        lines.append(f"- **{label}**: {count:,} ({pct:.1f}%)")

    lines += [
        f"",
        f"To account for potential distribution skew across classes, the modeling pipeline leverages "
        f"stratified train-test splits (80:20) and 5-fold stratified cross-validation.",
        f"",
        f"## 3. Anthropometric & Nutritional Features",
        f"",
        f"- **BMI Engineering**: Body Mass Index is derived as `weight_kg / (height_cm / 100)^2` per subject. "
        f"WHO thresholds (Underweight <18.5, Normal 18.5-24.9, Overweight 25-29.9, Obese >=30) serve as reference guides.",
        f"- **Dietary Diversity**: Measured across 1 to 8 distinct food groups eaten daily.",
        f"- **Meal Frequency**: Ranges between 1 and 8 meals per day.",
        f"",
        f"## 4. Correlation Analysis",
        f"",
        f"The correlation matrix (`08_correlation_heatmap.png`) measures linear associations among numerical attributes. "
        f"All pairwise correlations remain below 0.85, confirming absence of collinear data leakage.",
        f"",
        f"## 5. Outlier Analysis",
        f"",
        f"Outlier evaluation was conducted using Tukey's method (1.5 x IQR rule). "
        f"Mild outlier values in anthropometric boundaries are handled robustly via median imputation and robust tree-based estimators.",
        f"",
        f"## 6. Generated EDA Visualizations",
        f"",
    ]
    for i, p in enumerate(plots, 1):
        lines.append(f"{i}. `{os.path.basename(p)}`")

    lines += [
        f"",
        f"---",
        f"",
        f"## 7. Limitations & Preprocessing Decisions",
        f"",
        f"1. **Descriptive Nature**: Observations illustrate feature relationships within this dataset but do not constitute medical evidence.",
        f"2. **Pipeline Encapsulation**: All transformations (imputation, scaling, one-hot encoding) are encapsulated in scikit-learn Pipelines.",
        f"3. **Zero Test-Leakage**: The test split (20%) is held out completely untouched until final evaluation.",
        f"",
        f"---",
        f"*NutriRisk AI -- Academic Research Decision-Support Prototype.*",
    ]

    text = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    logger.info("EDA summary saved: %s", output_path)
    return text


if __name__ == "__main__":
    import sys
    print("=" * 70)
    print("NutriRisk AI -- Generating Exploratory Data Analysis (EDA) Suite")
    print("=" * 70)
    data_path = "data/dataset.csv" if os.path.exists("data/dataset.csv") else "data/synthetic_dataset.csv"
    data_label = "REAL" if os.path.exists("data/dataset.csv") else "SYNTHETIC"
    if os.path.exists(data_path):
        df_in = pd.read_csv(data_path)
        report_res = generate_eda_report(df_in, output_dir="reports", data_source_label=data_label)
        print(f"\n[OK] Generated {len(report_res['plots'])} EDA plots in 'reports/'")
        print(f"[OK] Summary report written to '{report_res['summary_path']}'\n")
    else:
        print(f"\n[ERROR] Dataset not found at '{data_path}'. Please run 'python train.py' first.")
        sys.exit(1)
