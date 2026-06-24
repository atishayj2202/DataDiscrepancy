from typing import List, Optional, Dict, Set
import pandas as pd
import numpy as np
from src.agents.base import BaseAgent, Discrepancy
from rapidfuzz import fuzz

class DuplicateRecordsAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Duplicate Records",
            description="Identifies identical rows (exact duplicates) and similar rows (near-duplicates) that may represent the same entity.",
            ai_level="Partial AI"
        )

    def detect(self, df: pd.DataFrame, columns: List[str] = None, similarity_threshold: float = 85.0, **kwargs) -> List[Discrepancy]:
        discrepancies = []
        if len(df) <= 1:
            return discrepancies

        # --- Phase 1: Exact Duplicates ---
        # We look across all columns or the specified columns
        target_cols = columns if columns is not None else df.columns.tolist()
        
        # Check for exact duplicates
        exact_dup_mask = df.duplicated(subset=target_cols, keep=False)
        exact_dup_indices = df.index[exact_dup_mask].tolist()
        
        if exact_dup_indices:
            # Group exact duplicates to show as example
            # We can find one example row representation
            example_idx = exact_dup_indices[0]
            example_row = df.loc[example_idx, target_cols].to_dict()
            example_str = ", ".join(f"{k}: '{v}'" for k, v in example_row.items() if pd.notna(v))
            
            interpretation = (
                f"Found {len(exact_dup_indices)} rows that are exact duplicates "
                f"based on the inspected columns. Suggested action: Deduplicate these rows."
            )
            
            discrepancies.append(
                Discrepancy(
                    column="Table Level",
                    row_indices=exact_dup_indices,
                    issue_type="Exact Duplicate Records",
                    criticality="Medium",
                    example_value=f"Row {example_idx}: {example_str[:120]}...",
                    interpretation=interpretation,
                    review_needed=False
                )
            )

        # --- Phase 2: Near-Duplicates ---
        # Near duplicates normally require AI to resolve authoritativeness.
        # We find candidates by concatenating text fields, sorting them, and comparing adjacent rows.
        # This keeps the comparison O(N log N) instead of O(N^2).
        
        # Select columns to construct the text signature
        # We prefer string and categorical columns
        text_cols = [
            col for col in target_cols 
            if df[col].dtype == 'object' or isinstance(df[col].dtype, pd.CategoricalDtype)
        ]
        
        # If there are no text columns, fall back to all target columns
        if not text_cols:
            text_cols = target_cols

        # Create row signatures
        signatures = []
        for idx, row in df.iterrows():
            # Combine non-null text columns into a single normalized string
            sig_parts = []
            for col in text_cols:
                val = row[col]
                if pd.notna(val) and str(val).strip() != "":
                    sig_parts.append(str(val).strip().lower())
            signatures.append((idx, " ".join(sig_parts)))

        # Sort signatures alphabetically to place similar signatures near each other
        signatures.sort(key=lambda x: x[1])

        near_dup_groups = []
        visited_indices: Set[int] = set()

        for i in range(len(signatures) - 1):
            idx1, sig1 = signatures[i]
            idx2, sig2 = signatures[i+1]

            # Skip if either is empty
            if not sig1 or not sig2:
                continue

            # Skip if they are part of exact duplicates (handled in phase 1) or already grouped
            if idx1 in visited_indices or idx2 in visited_indices:
                continue
                
            # If the signatures are identical, it is an exact duplicate (already handled)
            if sig1 == sig2:
                continue

            # Compute similarity
            sim = fuzz.token_sort_ratio(sig1, sig2)
            if sim >= similarity_threshold:
                # We found a near-duplicate pair
                near_dup_groups.append((idx1, idx2, sim))
                visited_indices.add(idx1)
                visited_indices.add(idx2)

        if near_dup_groups:
            # Let's register a discrepancy for near-duplicates
            # We can create a consolidated report, or one discrepancy per pair.
            # Showing them grouped together is very nice.
            all_near_dup_indices = []
            for idx1, idx2, _ in near_dup_groups:
                all_near_dup_indices.extend([idx1, idx2])

            # Provide one or two pairs as examples
            examples = []
            for idx1, idx2, sim in near_dup_groups[:3]:
                row1_vals = df.loc[idx1, text_cols].to_dict()
                row2_vals = df.loc[idx2, text_cols].to_dict()
                row1_str = ", ".join(f"{k}: '{v}'" for k, v in row1_vals.items() if pd.notna(v))
                row2_str = ", ".join(f"{k}: '{v}'" for k, v in row2_vals.items() if pd.notna(v))
                examples.append(f"Pair (Sim {sim:.0f}%):\n  - Row {idx1}: {row1_str[:80]}...\n  - Row {idx2}: {row2_str[:80]}...")

            example_value = "\n".join(examples)
            interpretation = (
                f"Found {len(near_dup_groups)} pairs of near-duplicate records (similarity >= {similarity_threshold}%). "
                f"Rules identified these candidates, but AI is required to decide which record is authoritative."
            )

            discrepancies.append(
                Discrepancy(
                    column="Table Level",
                    row_indices=all_near_dup_indices,
                    issue_type="Near-Duplicate Records",
                    criticality="Medium",
                    example_value=example_value,
                    interpretation=interpretation,
                    review_needed=True,
                    review_notes=(
                        "AI Resolution Bypassed: Normally, a specialized LLM would be called on "
                        "each near-duplicate pair to determine 'Which row is authoritative?' based on "
                        "recency, completeness, and context. Bypassed due to API key budget constraints. "
                        "Please manually review these rows to determine the primary record."
                    )
                )
            )

        return discrepancies
