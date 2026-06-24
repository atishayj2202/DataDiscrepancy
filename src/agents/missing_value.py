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
        # Common placeholder representations of null values
        self.placeholders: Set[str] = {
            "n/a", "na", "null", "none", "nan", "-", "?", "", "empty", "nil"
        }

    def detect(self, df: pd.DataFrame, columns: List[str] = None, **kwargs) -> List[Discrepancy]:
        discrepancies = []
        target_cols = columns if columns is not None else df.columns.tolist()

        for col in target_cols:
            if col not in df.columns:
                continue

            series = df[col]
            missing_indices = []
            example_val = None

            for idx, val in enumerate(series):
                is_missing = False
                
                # Check for standard pandas / numpy nulls
                if pd.isna(val) or val is None:
                    is_missing = True
                    current_val_str = "NaN/None"
                else:
                    # Check for string placeholder representations
                    val_str = str(val).strip()
                    if val_str.lower() in self.placeholders:
                        is_missing = True
                        current_val_str = f"'{val}'"

                if is_missing:
                    missing_indices.append(idx)
                    if example_val is None:
                        example_val = current_val_str

            num_missing = len(missing_indices)
            if num_missing > 0:
                total_rows = len(df)
                missing_pct = (num_missing / total_rows) * 100

                # Determine criticality based on percentage
                # flag if null% > 5% (Medium) or > 30% (High), otherwise Low.
                if missing_pct > 30.0:
                    criticality = "High"
                elif missing_pct > 5.0:
                    criticality = "Medium"
                else:
                    criticality = "Low"

                interpretation = (
                    f"Column '{col}' has {num_missing} missing value(s) ({missing_pct:.2f}% of rows). "
                    f"Suggested action: Impute missing values, check data source, or mark as optional."
                )

                discrepancies.append(
                    Discrepancy(
                        column=col,
                        row_indices=missing_indices,
                        issue_type="Missing / Null Values",
                        criticality=criticality,
                        example_value=example_val,
                        interpretation=interpretation,
                        review_needed=False
                    )
                )

        return discrepancies
