from collections import defaultdict
from typing import List, Dict
import pandas as pd
from src.agents.base import BaseAgent, Discrepancy

class InconsistentCasingAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Inconsistent Casing",
            description="Identifies values written in different capitalizations in the same column (e.g., 'mumbai', 'Mumbai', 'MUMBAI').",
            ai_level="Rules Only"
        )

    def detect(self, df: pd.DataFrame, columns: List[str] = None, **kwargs) -> List[Discrepancy]:
        discrepancies = []
        target_cols = columns if columns is not None else df.columns.tolist()

        for col in target_cols:
            if col not in df.columns:
                continue

            series = df[col]
            
            # Check only string/object columns
            if not (series.dtype == 'object' or pd.api.types.is_string_dtype(series)):
                continue

            # Filter non-null and non-empty values
            non_null_mask = series.notna() & (series.astype(str).str.strip() != "")
            clean_series = series[non_null_mask].astype(str)

            if len(clean_series) == 0:
                continue

            # Group values by their lowercase representation
            # Map: lowercase_value -> {original_value: [indices]}
            groups = defaultdict(lambda: defaultdict(list))
            for idx, val in clean_series.items():
                stripped = val.strip()
                groups[stripped.lower()][stripped].append(idx)

            inconsistent_indices = []
            example_val = None
            total_cases_flagged = 0

            # Find groups with capitalization collisions
            for lower_val, variants in groups.items():
                if len(variants) > 1:
                    total_group_count = sum(len(indices) for indices in variants.values())
                    # Find the dominant casing variant
                    dominant_variant = max(variants.keys(), key=lambda k: len(variants[k]))
                    dominant_count = len(variants[dominant_variant])
                    
                    # Only flag if dominant variant is >= 50% of the group
                    if (dominant_count / total_group_count) >= 0.50:
                        # All other variants are inconsistent
                        for variant, indices in variants.items():
                            if variant != dominant_variant:
                                inconsistent_indices.extend(indices)
                                total_cases_flagged += len(indices)
                                if example_val is None:
                                    example_val = f"'{variant}' (expected '{dominant_variant}')"

            if inconsistent_indices:
                num_affected = len(inconsistent_indices)
                pct_affected = (num_affected / len(df)) * 100
                
                interpretation = (
                    f"Column '{col}' has {num_affected} row(s) ({pct_affected:.2f}%) with inconsistent casing. "
                    f"Example: {example_val}. Suggested action: Standardize all entries to the dominant casing format."
                )

                discrepancies.append(
                    Discrepancy(
                        column=col,
                        row_indices=sorted(inconsistent_indices),
                        issue_type="Inconsistent Casing",
                        criticality="Low",
                        example_value=str(example_val),
                        interpretation=interpretation,
                        review_needed=False
                    )
                )

        return discrepancies
