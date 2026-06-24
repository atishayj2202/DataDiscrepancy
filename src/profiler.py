from typing import Dict, Any, List
import pandas as pd
import numpy as np

def format_memory_size(bytes_size: int) -> str:
    """
    Formats memory size in bytes to a human-readable string.
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.2f} TB"

def get_simplified_type(series: pd.Series) -> str:
    """
    Returns a clean, user-friendly description of the column's data type.
    """
    if pd.api.types.is_bool_dtype(series):
        return "Boolean"
    elif pd.api.types.is_integer_dtype(series):
        return "Integer"
    elif pd.api.types.is_float_dtype(series):
        return "Decimal (Float)"
    elif pd.api.types.is_datetime64_any_dtype(series):
        return "Date/Time"
    else:
        return "Text/Categorical"

def profile_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Scans the dataset to compute summary metrics and column-level profile statistics.
    """
    total_rows = len(df)
    total_cols = len(df.columns)
    
    # Calculate total memory usage of the dataframe
    try:
        memory_bytes = df.memory_usage(deep=True).sum()
        memory_str = format_memory_size(memory_bytes)
    except Exception:
        memory_str = "Unknown"

    columns_profile = []
    
    for col in df.columns:
        series = df[col]
        
        # Calculate nulls (standard pandas nulls + empty strings)
        null_count = int(series.isna().sum())
        empty_str_count = int((series == "").sum()) if series.dtype == 'object' else 0
        total_missing = null_count + empty_str_count
        missing_pct = (total_missing / total_rows) * 100 if total_rows > 0 else 0
        
        # Calculate unique values
        num_unique = int(series.nunique(dropna=True))
        
        # Get top-5 unique values with counts
        try:
            top_vals = series.value_counts(dropna=True).head(5).to_dict()
            # Convert keys to strings to ensure JSON compatibility and clean display
            top_vals_clean = {str(k): int(v) for k, v in top_vals.items()}
        except Exception:
            top_vals_clean = {}

        # Min and Max values (for numeric and datetime columns)
        min_val = "N/A"
        max_val = "N/A"
        
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
            # Dropna to avoid getting nan for min/max
            clean_series = series.dropna()
            if not clean_series.empty:
                raw_min = clean_series.min()
                raw_max = clean_series.max()
                # Format datetime nicely
                if isinstance(raw_min, pd.Timestamp):
                    min_val = raw_min.strftime('%Y-%m-%d %H:%M:%S')
                    max_val = raw_max.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    min_val = str(raw_min)
                    max_val = str(raw_max)

        columns_profile.append({
            "name": col,
            "pandas_dtype": str(series.dtype),
            "simplified_type": get_simplified_type(series),
            "missing_count": total_missing,
            "missing_pct": missing_pct,
            "cardinality": num_unique,
            "min_value": min_val,
            "max_value": max_val,
            "top_values": top_vals_clean
        })

    return {
        "summary": {
            "total_rows": total_rows,
            "total_columns": total_cols,
            "memory_usage": memory_str
        },
        "columns": columns_profile
    }
