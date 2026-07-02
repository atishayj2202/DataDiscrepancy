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
        target_cols = columns if columns is not None else df.columns.tolist()
        
        # Group exact duplicates by matching values
        exact_groups = []
        exact_map = {}
        for idx, row in df.iterrows():
            # Build a tuple representation of target columns to hash and group
            val_tuple = tuple(str(row[col]) for col in target_cols)
            if val_tuple not in exact_map:
                exact_map[val_tuple] = []
            exact_map[val_tuple].append(idx)
            
        for val_tuple, indices in exact_map.items():
            if len(indices) > 1:
                exact_groups.append(indices)

        for g_idx, indices in enumerate(exact_groups):
            example_idx = indices[0]
            example_row = df.loc[example_idx, target_cols].to_dict()
            example_str = ", ".join(f"{k}: '{v}'" for k, v in example_row.items() if pd.notna(v))
            
            interpretation = (
                f"Found {len(indices)} rows in Group #{g_idx+1} that are exact duplicates of each other. "
                f"Suggested action: Keep one authoritative row and deduplicate the rest."
            )
            
            discrepancies.append(
                Discrepancy(
                    column="Table Level",
                    row_indices=indices,
                    issue_type="Exact Duplicate Records",
                    criticality="High",
                    example_value=f"Row {example_idx}: {example_str[:120]}...",
                    interpretation=interpretation,
                    review_needed=False
                )
            )

        # --- Phase 2: Near-Duplicates ---
        text_cols = [
            col for col in target_cols 
            if df[col].dtype == 'object' or isinstance(df[col].dtype, pd.CategoricalDtype)
        ]
        if not text_cols:
            text_cols = target_cols

        # Create row signatures
        signatures = []
        for idx, row in df.iterrows():
            sig_parts = []
            for col in text_cols:
                val = row[col]
                if pd.notna(val) and str(val).strip() != "":
                    sig_parts.append(str(val).strip().lower())
            signatures.append((idx, " ".join(sig_parts)))

        # Sort signatures alphabetically to place similar signatures near each other
        signatures.sort(key=lambda x: x[1])

        # Build adjacency list for similar signatures
        adj_list = {idx: set() for idx, _ in signatures}

        for i in range(len(signatures) - 1):
            idx1, sig1 = signatures[i]
            idx2, sig2 = signatures[i+1]

            if not sig1 or not sig2:
                continue

            # Skip if they have identical signature (exact duplicate, handled in Phase 1)
            if sig1 == sig2:
                continue

            # Compute similarity
            sim = fuzz.token_sort_ratio(sig1, sig2)
            if sim >= similarity_threshold:
                adj_list[idx1].add(idx2)
                adj_list[idx2].add(idx1)

        # Find connected components (groups of near-duplicates)
        near_groups = []
        visited = set()
        for idx, _ in signatures:
            if idx in visited or not adj_list[idx]:
                continue
            
            comp = []
            queue = [idx]
            visited.add(idx)
            while queue:
                curr = queue.pop(0)
                comp.append(curr)
                for neighbor in adj_list[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            if len(comp) > 1:
                near_groups.append(comp)

        for g_idx, indices in enumerate(near_groups):
            examples = []
            for idx in indices[:3]:
                row_vals = df.loc[idx, text_cols].to_dict()
                row_str = ", ".join(f"{k}: '{v}'" for k, v in row_vals.items() if pd.notna(v))
                examples.append(f"  - Row {idx}: {row_str[:80]}...")
            
            example_value = "\n".join(examples)
            interpretation = (
                f"Found a group of {len(indices)} near-duplicate records (similarity match). "
                f"Rules identified these candidates, but manual review is required to choose the authoritative record."
            )

            discrepancies.append(
                Discrepancy(
                    column="Table Level",
                    row_indices=indices,
                    issue_type="Near-Duplicate Records",
                    criticality="Medium",
                    example_value=example_value,
                    interpretation=interpretation,
                    review_needed=True,
                    review_notes=(
                        "Please manually review these rows to determine the primary record."
                    )
                )
            )

        return discrepancies
