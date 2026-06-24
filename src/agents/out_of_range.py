from typing import List, Dict, Tuple, Optional, Any
import pandas as pd
import numpy as np
from src.agents.base import BaseAgent, Discrepancy

class OutOfRangeAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Out-of-Range Values",
            description="Detects numeric values outside logical boundaries or statistical expectations.",
            ai_level="Partial AI"
        )
        # Default heuristic logical limits based on common column name matches
        self.default_limits: Dict[str, Tuple[float, float]] = {
            "age": (0, 120),
            "percentage": (0, 100),
            "pct": (0, 100),
            "probability": (0, 1),
            "prob": (0, 1),
            "month": (1, 12),
            "hour": (0, 23),
            "minute": (0, 59),
            "second": (0, 59),
            "day": (1, 31)
        }

    def _get_logical_limits(self, col_name: str, custom_limits: Optional[Dict[str, Tuple[float, float]]] = None) -> Optional[Tuple[float, float]]:
        """
        Retrieves logical limits for a column based on custom limits or default heuristics.
        """
        if custom_limits and col_name in custom_limits:
            return custom_limits[col_name]
            
        col_lower = col_name.lower().strip()
        for key, limits in self.default_limits.items():
            if key in col_lower:
                return limits
        return None

    def detect(self, df: pd.DataFrame, columns: List[str] = None, custom_limits: Dict[str, Tuple[float, float]] = None, **kwargs) -> List[Discrepancy]:
        discrepancies = []
        target_cols = columns if columns is not None else df.columns.tolist()

        for col in target_cols:
            if col not in df.columns:
                continue

            series = df[col]
            
            # Check if column is numeric. If not, skip it.
            if not pd.api.types.is_numeric_dtype(series):
                continue
                
            # Filter out null values
            non_null_mask = series.notna()
            clean_series = series[non_null_mask]
            
            if len(clean_series) < 5:  # Not enough data for statistical limits
                continue

            logical_limits = self._get_logical_limits(col, custom_limits)
            
            clear_violators = []
            borderline_violators = []
            example_clear = None
            example_border = None

            if logical_limits:
                # --- Logical Limits Check ---
                min_limit, max_limit = logical_limits
                range_width = max_limit - min_limit
                # Define borderline tolerance as 5% of the range
                tolerance = 0.05 * range_width if range_width > 0 else 1.0
                
                for idx, val in clean_series.items():
                    if val < min_limit or val > max_limit:
                        # Check if it's borderline
                        is_borderline = (
                            (min_limit - tolerance <= val < min_limit) or
                            (max_limit < val <= max_limit + tolerance)
                        )
                        if is_borderline:
                            borderline_violators.append(idx)
                            if example_border is None:
                                example_border = f"{val} (Limit: {min_limit}-{max_limit})"
                        else:
                            clear_violators.append(idx)
                            if example_clear is None:
                                example_clear = f"{val} (Limit: {min_limit}-{max_limit})"
            else:
                # --- Statistical Limits Check (IQR & Z-score combined) ---
                q1 = clean_series.quantile(0.25)
                q3 = clean_series.quantile(0.75)
                iqr = q3 - q1
                
                iqr_lower = q1 - 1.5 * iqr
                iqr_upper = q3 + 1.5 * iqr
                iqr_border_lower = q1 - 3.0 * iqr
                iqr_border_upper = q3 + 3.0 * iqr
                
                mean = clean_series.mean()
                std = clean_series.std()
                
                if std > 0:
                    # Let's check each value
                    for idx, val in clean_series.items():
                        z_score = abs((val - mean) / std)
                        
                        # We flag if it violates either IQR or Z-score > 3
                        is_out_iqr = val < iqr_lower or val > iqr_upper
                        is_out_z = z_score > 3.0
                        
                        if is_out_iqr or is_out_z:
                            # Classify as borderline vs clear
                            # Clear violation if Z-score > 4.5 or value is way outside IQR bounds (3.0 * IQR)
                            is_clear_violation = (z_score > 4.5) or (val < iqr_border_lower) or (val > iqr_border_upper)
                            
                            if is_clear_violation:
                                clear_violators.append(idx)
                                if example_clear is None:
                                    example_clear = f"{val} (Z-score: {z_score:.1f})"
                            else:
                                borderline_violators.append(idx)
                                if example_border is None:
                                    example_border = f"{val} (Z-score: {z_score:.1f})"

            # Register clear out-of-range discrepancies
            if clear_violators:
                num_viol = len(clear_violators)
                viol_pct = (num_viol / len(df)) * 100
                
                interpretation = (
                    f"Column '{col}' contains {num_viol} value(s) ({viol_pct:.2f}% of rows) "
                    f"that are clear logical or statistical out-of-range violations. "
                )
                if logical_limits:
                    interpretation += f"These values violate the configured limits of [{logical_limits[0]}, {logical_limits[1]}]."
                else:
                    interpretation += "These values are extreme outliers (Z-score > 4.5 or way outside IQR bounds)."

                discrepancies.append(
                    Discrepancy(
                        column=col,
                        row_indices=clear_violators,
                        issue_type="Clear Out-of-Range",
                        criticality="High",
                        example_value=str(example_clear),
                        interpretation=interpretation,
                        review_needed=False
                    )
                )

            # Register borderline out-of-range discrepancies (Requires Review)
            if borderline_violators:
                num_viol = len(borderline_violators)
                viol_pct = (num_viol / len(df)) * 100
                
                interpretation = (
                    f"Column '{col}' contains {num_viol} value(s) ({viol_pct:.2f}% of rows) "
                    f"that are borderline out-of-range. "
                    f"Review is needed to assess: is this a genuine extreme or a data entry error?"
                )

                discrepancies.append(
                    Discrepancy(
                        column=col,
                        row_indices=borderline_violators,
                        issue_type="Borderline Out-of-Range (Requires Review)",
                        criticality="High",
                        example_value=str(example_border),
                        interpretation=interpretation,
                        review_needed=True,
                        review_notes=(
                            "AI / Human Review Needed: Normally, a specialized LLM would be called on "
                            "borderline out-of-range values to cross-reference with context (e.g., check other "
                            "columns or text notes) to assess if this value represents a genuine extreme (e.g. high billing) "
                            "or a typographic entry error (e.g. double zero entry). "
                            "Please manually verify these values."
                        )
                    )
                )

        return discrepancies
