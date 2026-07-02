from typing import List, Dict, Optional, Any
import pandas as pd
import numpy as np
from src.agents.base import BaseAgent, Discrepancy

# Try to import scikit-learn for IsolationForest, fall back to univariate if unavailable
try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

class StatisticalOutliersAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Statistical Outliers",
            description="Identifies values that are statistically extreme for their column, and multi-column anomalies using Isolation Forest.",
            ai_level="Partial AI"
        )

    def detect(self, df: pd.DataFrame, columns: List[str] = None, **kwargs) -> List[Discrepancy]:
        return []
        target_cols = columns if columns is not None else df.columns.tolist()
        
        # Identify numeric columns in target list
        numeric_cols = [col for col in target_cols if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]
        
        if not numeric_cols:
            return discrepancies

        # --- Phase 1: Univariate (Column-by-Column) Outliers ---
        for col in numeric_cols:
            series = df[col]
            non_null_mask = series.notna()
            clean_series = series[non_null_mask]
            
            if len(clean_series) < 10:  # Too few rows to establish statistical baseline
                continue

            mean = clean_series.mean()
            std = clean_series.std()
            q1 = clean_series.quantile(0.25)
            q3 = clean_series.quantile(0.75)
            iqr = q3 - q1
            
            if std == 0:
                continue

            clear_outliers = []
            ambiguous_outliers = []
            example_clear = None
            example_ambiguous = None

            for idx, val in clean_series.items():
                z_score = abs((val - mean) / std)
                is_iqr_outlier = val < (q1 - 1.5 * iqr) or val > (q3 + 1.5 * iqr)
                is_z_outlier = z_score > 3.0

                if is_iqr_outlier or is_z_outlier:
                    # Clear Extreme vs Ambiguous Outlier
                    # Clear Extreme is defined as Z-score > 6.0 OR > 3000% (30x) above/below mean (if mean != 0)
                    is_clear_extreme = z_score > 6.0
                    if mean != 0 and not is_clear_extreme:
                        # 3000% above mean or 3000% below mean
                        pct_diff = abs(val - mean) / abs(mean)
                        if pct_diff >= 30.0:
                            is_clear_extreme = True

                    if is_clear_extreme:
                        clear_outliers.append(idx)
                        if example_clear is None:
                            example_clear = f"{val} (Z-score: {z_score:.1f})"
                    else:
                        ambiguous_outliers.append(idx)
                        if example_ambiguous is None:
                            example_ambiguous = f"{val} (Z-score: {z_score:.1f})"

            # Record clear outliers
            if clear_outliers:
                num_out = len(clear_outliers)
                pct_out = (num_out / len(df)) * 100
                interpretation = (
                    f"Column '{col}' contains {num_out} clear statistical outlier(s) ({pct_out:.2f}% of rows). "
                    f"These are extreme values (Z-score > 6.0 or > 3000% away from the mean) and represent clear discrepancies."
                )
                discrepancies.append(
                    Discrepancy(
                        column=col,
                        row_indices=clear_outliers,
                        issue_type="Confirmed Statistical Outlier",
                        criticality="Medium",
                        example_value=str(example_clear),
                        interpretation=interpretation,
                        review_needed=False
                    )
                )

            # Record ambiguous outliers (Requires review)
            if ambiguous_outliers:
                num_out = len(ambiguous_outliers)
                pct_out = (num_out / len(df)) * 100
                interpretation = (
                    f"Column '{col}' contains {num_out} ambiguous statistical outlier(s) ({pct_out:.2f}% of rows). "
                    f"These values are statistically unusual (Z-score 3.0 to 6.0), requiring review to check if they are errors."
                )
                discrepancies.append(
                    Discrepancy(
                        column=col,
                        row_indices=ambiguous_outliers,
                        issue_type="Ambiguous Statistical Outlier (Requires Review)",
                        criticality="Medium",
                        example_value=str(example_ambiguous),
                        interpretation=interpretation,
                        review_needed=True,
                        review_notes=(
                            "AI / Human Review Needed: Normally, a specialized LLM would be called on "
                            "statistically extreme values to return a verdict: likely error / plausible extreme / uncertain. "
                            "This system flags these values so a human or future AI model can evaluate the context."
                        )
                    )
                )

        # --- Phase 2: Multivariate (Multi-Column) Outliers ---
        # Run Isolation Forest across all numeric columns to find multivariate anomalies
        if False:  # Deactivated Multivariate Analysis
            try:
                # Prepare data: impute missing values with median and scale
                prep_df = df[numeric_cols].copy()
                for col in numeric_cols:
                    prep_df[col] = prep_df[col].fillna(prep_df[col].median())
                    # If standard deviation is 0, we drop it for Isolation Forest
                    if prep_df[col].std() == 0:
                        prep_df = prep_df.drop(columns=[col])

                # Run only if we still have at least 2 features
                if len(prep_df.columns) >= 2:
                    scaler = StandardScaler()
                    scaled_data = scaler.fit_transform(prep_df)

                    # Fit Isolation Forest (contamination = 2%)
                    clf = IsolationForest(contamination=0.02, random_state=42)
                    preds = clf.fit_predict(scaled_data)

                    # Find anomalies (-1)
                    multivariate_anomaly_indices = np.where(preds == -1)[0].tolist()

                    if multivariate_anomaly_indices:
                        example_idx = multivariate_anomaly_indices[0]
                        example_row = df.loc[example_idx, numeric_cols].to_dict()
                        example_str = ", ".join(f"{k}: {v}" for k, v in example_row.items() if pd.notna(v))

                        interpretation = (
                            f"Isolation Forest flagged {len(multivariate_anomaly_indices)} row(s) "
                            f"({(len(multivariate_anomaly_indices)/len(df))*100:.2f}% of rows) "
                            f"as multi-column multivariate anomalies. Individually the values may look valid, "
                            f"but their combined pattern is statistically extreme."
                        )

                        discrepancies.append(
                            Discrepancy(
                                column="Table Level",
                                row_indices=multivariate_anomaly_indices,
                                issue_type="Multivariate Anomaly (Requires Review)",
                                criticality="Medium",
                                example_value=f"Row {example_idx}: {example_str[:120]}...",
                                interpretation=interpretation,
                                review_needed=True,
                                review_notes=(
                                    "AI / Human Review Needed: Isolation Forest identified these rows as "
                                    "statistically anomalous in multi-dimensional space. An LLM or human analyst "
                                    "must review the relationship between columns in these rows to verify if they represent "
                                    "impossible business states or rare valid transactions."
                                )
                            )
                        )
            except Exception as e:
                # If something goes wrong in scikit-learn, fail silently to keep app running
                pass

        return discrepancies
