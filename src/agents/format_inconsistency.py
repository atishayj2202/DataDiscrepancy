from typing import List, Dict, Tuple
import pandas as pd
from src.agents.base import BaseAgent, Discrepancy

class FormatInconsistencyAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Format Inconsistency",
            description="Identifies columns where values are written in multiple formats (e.g., dates as MM/DD/YYYY vs YYYY-MM-DD, mixed phone formats).",
            ai_level="Rules Only"
        )

    def _get_pattern(self, val: str) -> str:
        """
        Maps a string value to its collapsed character pattern template.
        Consecutive digits are collapsed into a single '9', and consecutive letters are collapsed into 'a'.
        For example: '01/02/2024' -> '9/9/9', 'ABC-123' -> 'a-9', '12' -> '9', '1' -> '9'.
        """
        res = []
        last_char_type = None  # None, 'digit', 'alpha', 'other'
        for char in val:
            if char.isdigit():
                if last_char_type != 'digit':
                    res.append('9')
                    last_char_type = 'digit'
            elif char.isalpha():
                if last_char_type != 'alpha':
                    res.append('a')
                    last_char_type = 'alpha'
            else:
                res.append(char)
                last_char_type = 'other'
        return "".join(res)

    def detect(self, df: pd.DataFrame, columns: List[str] = None, threshold: float = 0.70, **kwargs) -> List[Discrepancy]:
        discrepancies = []
        target_cols = columns if columns is not None else df.columns.tolist()

        for col in target_cols:
            if col not in df.columns:
                continue

            series = df[col]
            
            # Skip if column is already numeric in Pandas
            if pd.api.types.is_numeric_dtype(series):
                continue

            # Extract non-null, non-empty string values
            non_null_mask = series.notna() & (series.astype(str).str.strip() != "")
            non_null_vals = series[non_null_mask].astype(str)
            
            if len(non_null_vals) < 5:  # Not enough data to determine a format
                continue

            # Skip if the column is mostly numeric strings (e.g. serial numbers or amounts read as object)
            num_castable = 0
            for v in non_null_vals:
                # Remove commas and spaces commonly found in formatted numbers
                clean_v = v.replace(",", "").replace(" ", "").strip()
                try:
                    float(clean_v)
                    num_castable += 1
                except ValueError:
                    pass
            if (num_castable / len(non_null_vals)) > 0.90:
                continue

            # Compute pattern for each value
            patterns = [self._get_pattern(v) for v in non_null_vals]
            pattern_series = pd.Series(patterns, index=non_null_vals.index)
            
            pattern_counts = pattern_series.value_counts()
            if len(pattern_counts) <= 1:
                continue  # All values match the same pattern
                
            dominant_pattern = pattern_counts.index[0]
            dominant_count = pattern_counts.iloc[0]
            total_count = len(non_null_vals)
            dominant_pct = dominant_count / total_count

            # If the dominant pattern represents more than 'threshold' of the values,
            # we flag the rows that have a different pattern.
            if dominant_pct >= threshold:
                inconsistent_mask = pattern_series != dominant_pattern
                inconsistent_indices = pattern_series.index[inconsistent_mask].tolist()
                
                if inconsistent_indices:
                    example_idx = inconsistent_indices[0]
                    example_val = non_null_vals.loc[example_idx]
                    
                    num_inconsistent = len(inconsistent_indices)
                    inconsistent_pct = (num_inconsistent / len(df)) * 100
                    
                    # Find a sample value matching the dominant pattern
                    sample_dominant_val = non_null_vals[pattern_series == dominant_pattern].iloc[0]
                    
                    # Group counts of other formats for interpretation
                    other_patterns_summary = []
                    for pat, count in pattern_counts.items():
                        if pat == dominant_pattern:
                            continue
                        pct = (count / total_count) * 100
                        # Find a sample value matching this pattern
                        sample_val = non_null_vals[pattern_series == pat].iloc[0]
                        other_patterns_summary.append(f"'{sample_val}' (follows pattern '{pat}', {pct:.1f}% of rows)")
                    
                    other_summary_str = "; ".join(other_patterns_summary[:3])
                    if len(pattern_counts) > 4:
                        other_summary_str += "; etc."

                    interpretation = (
                        f"Column '{col}' shows format inconsistency. The dominant format pattern is "
                        f"'{dominant_pattern}' (representing {dominant_pct*100:.1f}% of values, e.g. '{sample_dominant_val}'). "
                        f"However, {num_inconsistent} row(s) ({inconsistent_pct:.2f}%) use alternative format patterns, "
                        f"such as: {other_summary_str}. Suggested action: Standardize formatting to match the dominant pattern."
                    )

                    discrepancies.append(
                        Discrepancy(
                            column=col,
                            row_indices=inconsistent_indices,
                            issue_type="Format Inconsistency",
                            criticality="Medium",
                            example_value=f"'{example_val}'",
                            interpretation=interpretation,
                            review_needed=False
                        )
                    )

        return discrepancies

