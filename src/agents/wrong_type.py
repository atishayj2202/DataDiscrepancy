from typing import List, Optional, Tuple, Any
import pandas as pd
import numpy as np
from src.agents.base import BaseAgent, Discrepancy

class WrongDataTypeAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Wrong Data Type",
            description="Detects values that do not match the inferred expected data type of the column.",
            ai_level="Rules Only"
        )
        self.skip_values = {
            "", "null", "?", "-", "na", "n/a", "nan", "none", "not applicable", "nil", "undefined"
        }

    def _infer_value_type(self, val: Any) -> str:
        """
        Classifies a single non-null value into one of: 'bool', 'int', 'float', 'datetime', 'str'.
        """
        if pd.isna(val) or val is None:
            return "null"

        # If it is already a python type
        if isinstance(val, bool):
            return "bool"
        if isinstance(val, (int, np.integer)):
            return "int"
        if isinstance(val, (float, np.floating)):
            # Check if it has a fractional part
            if val.is_integer():
                return "int"
            return "float"
        if isinstance(val, (pd.Timestamp, np.datetime64)):
            return "datetime"

        # Parse string representation
        val_str = str(val).strip()
        val_lower = val_str.lower()

        # Check for boolean
        if val_lower in {"true", "false", "yes", "no"}:
            return "bool"

        # Check for integer
        try:
            int(val_str)
            return "int"
        except ValueError:
            pass

        # Check for float
        try:
            float(val_str)
            return "float"
        except ValueError:
            pass

        # Check for datetime
        # Simple heuristic to avoid parsing arbitrary small numbers or words as datetimes
        if any(char in val_str for char in ["-", "/", ":"]) or len(val_str) >= 8:
            try:
                # Use pandas to_datetime
                pd.to_datetime(val_str, errors='raise', format='mixed')
                return "datetime"
            except (ValueError, TypeError, OverflowError):
                pass

        return "str"

    def _can_cast_to(self, val: Any, target_type: str) -> bool:
        """
        Checks if a value can be cast to the target type.
        """
        if pd.isna(val) or val is None:
            return True  # Nulls are handled by the Missing Value Agent
            
        val_str = str(val).strip()
        
        if target_type == "bool":
            return val_str.lower() in {"true", "false", "yes", "no", "1", "0", "y", "n", "t", "f"}
            
        if target_type == "int":
            try:
                # Handle strings with decimals that represent integers e.g. "25.0"
                f_val = float(val_str)
                return f_val.is_integer()
            except ValueError:
                return False
                
        if target_type == "float":
            try:
                float(val_str)
                return True
            except ValueError:
                return False
                
        if target_type == "datetime":
            try:
                pd.to_datetime(val_str, errors='raise', format='mixed')
                return True
            except (ValueError, TypeError, OverflowError):
                return False
                
        return True

    def detect(self, df: pd.DataFrame, columns: List[str] = None, **kwargs) -> List[Discrepancy]:
        discrepancies = []
        target_cols = columns if columns is not None else df.columns.tolist()

        for col in target_cols:
            if col not in df.columns:
                continue

            # We focus on object/string columns, or numeric columns that might be read as object due to mixed types.
            # If a column is purely int64 or float64 in pandas, it won't have type mismatches (they are already cast).
            series = df[col]
            
            # Step 1: Infer types for non-null values
            non_null_mask = series.apply(lambda x: not pd.isna(x) and str(x).lower().strip() not in self.skip_values)
            non_null_vals = series[non_null_mask]
            if len(non_null_vals) == 0:
                continue

            type_counts = {"bool": 0, "int": 0, "float": 0, "datetime": 0, "str": 0}
            for val in non_null_vals:
                t = self._infer_value_type(val)
                if t in type_counts:
                    type_counts[t] += 1

            # Step 2: Determine majority type
            total_non_null = len(non_null_vals)
            
            # We want to see which type is most common.
            # We treat numeric types (int and float) together for determining "numeric" priority.
            num_numeric = type_counts["int"] + type_counts["float"]
            
            inferred_type = "str"
            max_count = type_counts["str"]

            if type_counts["bool"] > max_count:
                inferred_type = "bool"
                max_count = type_counts["bool"]
                
            if type_counts["datetime"] > max_count:
                inferred_type = "datetime"
                max_count = type_counts["datetime"]
                
            if num_numeric > max_count:
                # If it's numeric, choose Decimal (float) if integers and decimals have a small difference in count
                # (e.g. if float count is > 0 and the absolute difference is less than 80% of the sum).
                # This ensures Amount/Price columns are correctly classified as Decimal even if they contain many whole numbers.
                if type_counts["float"] > 0 and abs(type_counts["int"] - type_counts["float"]) / num_numeric < 0.8:
                    inferred_type = "float"
                elif type_counts["int"] >= type_counts["float"]:
                    inferred_type = "int"
                else:
                    inferred_type = "float"
                max_count = num_numeric

            # If the majority type represents >= 50% of the non-null data and it's not a general string type,
            # we flag the remaining minority that cannot be cast.
            if inferred_type != "str" and (max_count / total_non_null) >= 0.50:
                wrong_indices = []
                example_val = None

                for idx, val in enumerate(series):
                    # Skip nulls, empty strings, and placeholders
                    if pd.isna(val) or str(val).lower().strip() in self.skip_values:
                        continue

                    # If this value cannot be cast to the inferred type
                    if not self._can_cast_to(val, inferred_type):
                        wrong_indices.append(idx)
                        if example_val is None:
                            example_val = str(val)

                if wrong_indices:
                    type_labels = {
                        "int": "Integer",
                        "float": "Decimal Number (Float)",
                        "datetime": "Date/Time",
                        "bool": "Boolean"
                    }
                    expected_label = type_labels.get(inferred_type, inferred_type)
                    num_wrong = len(wrong_indices)
                    wrong_pct = (num_wrong / len(df)) * 100

                    interpretation = (
                        f"Column '{col}' is inferred to be of type '{expected_label}' "
                        f"({(max_count/total_non_null)*100:.1f}% values match). "
                        f"However, {num_wrong} row(s) ({wrong_pct:.2f}%) contain values that cannot be cast to this type. "
                        f"Suggested action: Standardize these values or correct manual entry errors."
                    )

                    discrepancies.append(
                        Discrepancy(
                            column=col,
                            row_indices=wrong_indices,
                            issue_type="Wrong Data Type",
                            criticality="High",
                            example_value=example_val,
                            interpretation=interpretation,
                            review_needed=False
                        )
                    )

        return discrepancies
