from abc import ABC, abstractmethod
from typing import List, Optional, Any
import pandas as pd
from dataclasses import dataclass

@dataclass
class Discrepancy:
    column: str  # Column name, or "Table Level"
    row_indices: List[int]  # 0-based indices of rows that are affected
    issue_type: str  # E.g., "Missing / Null Values"
    criticality: str  # "Low", "Medium", "High"
    example_value: str  # Example of the issue, e.g. "twenty-five" or "N/A"
    interpretation: str  # A friendly suggested explanation or remediation
    review_needed: bool = False  # Set to True if this requires AI / Human review
    review_notes: Optional[str] = None  # Notes detailing the review required

class BaseAgent(ABC):
    def __init__(self, name: str, description: str, ai_level: str):
        self.name = name
        self.description = description
        self.ai_level = ai_level  # "Rules Only", "Partial AI", "Full AI"

    @abstractmethod
    def detect(self, df: pd.DataFrame, **kwargs) -> List[Discrepancy]:
        """
        Analyze the dataframe and return a list of detected discrepancies.
        """
        pass
