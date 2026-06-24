import re
from typing import List
import pandas as pd
from src.agents.base import BaseAgent, Discrepancy

class WhitespaceEncodingAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Whitespace & Encoding Errors",
            description="Detects leading/trailing spaces, consecutive spaces, and garbled text (encoding errors/mojibake).",
            ai_level="Rules Only"
        )
        # Regex to detect common UTF-8 bytes incorrectly decoded as Latin-1 / Windows-1252
        # E.g., Ã©, Ã¡, â€œ, â€ 
        self.mojibake_pattern = re.compile(r'[\u00c2-\u00df][\u0080-\u00bf]')

    def _detect_issues(self, val: str) -> List[str]:
        issues = []
        if val != val.strip():
            issues.append("leading/trailing whitespace")
        if "  " in val:
            issues.append("consecutive double spaces")
            
        # Check for encoding errors / mojibake
        if "\ufffd" in val or "ï¿½" in val:
            issues.append("unicode replacement character (possible encoding corruption)")
        elif self.mojibake_pattern.search(val):
            issues.append("mojibake signature (possible UTF-8 decoded as Latin-1)")
            
        return issues

    def detect(self, df: pd.DataFrame, columns: List[str] = None, **kwargs) -> List[Discrepancy]:
        discrepancies = []
        target_cols = columns if columns is not None else df.columns.tolist()

        for col in target_cols:
            if col not in df.columns:
                continue

            series = df[col]
            
            # Run only on object / string columns
            if not (series.dtype == 'object' or pd.api.types.is_string_dtype(series)):
                continue

            # Filter non-null, non-empty values
            non_null_mask = series.notna() & (series.astype(str) != "")
            clean_series = series[non_null_mask].astype(str)

            if len(clean_series) == 0:
                continue

            affected_indices = []
            example_val = None
            issue_descriptions = []

            for idx, val in clean_series.items():
                issues = self._detect_issues(val)
                if issues:
                    affected_indices.append(idx)
                    if example_val is None:
                        example_val = f"'{val}'"
                        issue_descriptions = issues

            if affected_indices:
                num_affected = len(affected_indices)
                pct_affected = (num_affected / len(df)) * 100
                
                issues_summary = ", ".join(issue_descriptions)
                interpretation = (
                    f"Column '{col}' has {num_affected} row(s) ({pct_affected:.2f}%) with "
                    f"whitespace or encoding errors. Common issue: {issues_summary}. "
                    f"Suggested action: Strip whitespaces, collapse spaces, or re-encode dataset."
                )

                discrepancies.append(
                    Discrepancy(
                        column=col,
                        row_indices=affected_indices,
                        issue_type="Whitespace & Encoding Errors",
                        criticality="Low",
                        example_value=str(example_val),
                        interpretation=interpretation,
                        review_needed=False
                    )
                )

        return discrepancies
