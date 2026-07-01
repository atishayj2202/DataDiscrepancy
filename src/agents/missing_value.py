from typing import List, Set
import pandas as pd
import numpy as np
from src.agents.base import BaseAgent, Discrepancy

class MissingValueAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Missing / Null Values",
            description="Identifies empty cells, blanks, None, NaN, and placeholder strings like 'N/A' or '-'.",
            ai_level="Rules Only"
        )
        # Valid non-applicable indicators (considered correct, not flagged)
        self.valid_na = {
            "na", "n/a", "nan", "none", "not applicable", "nil", "undefined"
        }

    def detect(self, df: pd.DataFrame, columns: List[str] = None, **kwargs) -> List[Discrepancy]:
        discrepancies = []
        target_cols = columns if columns is not None else df.columns.tolist()

        for col in target_cols:
            if col not in df.columns:
                continue

            series = df[col]
            null_indices = []
            incomplete_indices = []
            null_example = None
            incomplete_example = None

            for idx, val in enumerate(series):
                # Standard pandas / numpy nulls (NaN, None)
                if pd.isna(val) or val is None:
                    null_indices.append(idx)
                    if null_example is None:
                        null_example = "NaN/None"
                    continue
                
                # Check for string representation
                val_str = str(val)
                val_lower = val_str.lower().strip()
                
                # If it's a valid NA/NaN indicator, skip it
                if val_lower in self.valid_na:
                    continue

                # 1. Null Value: "null" (case-insensitive) or empty string "" (length 0)
                if val_lower == "null" or val_str == "":
                    null_indices.append(idx)
                    if null_example is None:
                        null_example = "Empty String" if val_str == "" else val_str
                
                # 2. Incomplete Records: Space (pure whitespace string of length > 0), "?", "-"
                elif val_str.strip() == "" and len(val_str) > 0:
                    incomplete_indices.append(idx)
                    if incomplete_example is None:
                        incomplete_example = "Whitespace Space(s)"
                elif val_str.strip() in ["?", "-"]:
                    incomplete_indices.append(idx)
                    if incomplete_example is None:
                        incomplete_example = f"'{val_str.strip()}'"

            # Add Null Value discrepancy if found
            if null_indices:
                total_rows = len(df)
                null_pct = (len(null_indices) / total_rows) * 100
                criticality = "High" if null_pct > 30.0 else "Medium" if null_pct > 5.0 else "Low"
                interpretation = (
                    f"Column '{col}' has {len(null_indices)} null value(s) ({null_pct:.2f}% of rows). "
                    f"Suggested action: Impute null values, check data entry interface, or mark as optional."
                )
                discrepancies.append(
                    Discrepancy(
                        column=col,
                        row_indices=null_indices,
                        issue_type="Null Value",
                        criticality=criticality,
                        example_value=null_example,
                        interpretation=interpretation,
                        review_needed=False
                    )
                )

            # Add Incomplete Records discrepancy if found
            if incomplete_indices:
                total_rows = len(df)
                inc_pct = (len(incomplete_indices) / total_rows) * 100
                criticality = "High" if inc_pct > 30.0 else "Medium" if inc_pct > 5.0 else "Low"
                interpretation = (
                    f"Column '{col}' has {len(incomplete_indices)} incomplete record placeholder(s) ({inc_pct:.2f}% of rows like space, ?, -). "
                    f"Suggested action: Correct placeholder entries or verify data collection methods."
                )
                discrepancies.append(
                    Discrepancy(
                        column=col,
                        row_indices=incomplete_indices,
                        issue_type="Incomplete Records",
                        criticality=criticality,
                        example_value=incomplete_example,
                        interpretation=interpretation,
                        review_needed=False
                    )
                )

        return discrepancies
