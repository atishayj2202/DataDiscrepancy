import pandas as pd
import numpy as np

def transform(df: pd.DataFrame) -> pd.DataFrame:
    """
    MOCK SAP Datasphere Python Dataflow Entry Point.
    Completely ignores input data and returns a hardcoded Pandas DataFrame.
    Used exclusively to test if the Datasphere environment accepts the output schema.
    """
    
    # 5-6 hardcoded rows formatted exactly as the main script would output them
    mock_data = [
        {
            'KUNNR': '10001', 
            'Cluster_ID': '10001', 
            'CommonPart': 'APPLE INC ... US', 
            'UncommonPart': ''
        },
        {
            'KUNNR': '10002', 
            'Cluster_ID': '10001', 
            'CommonPart': 'APPLE INC ... US', 
            'UncommonPart': '.'
        },
        {
            'KUNNR': '20001', 
            'Cluster_ID': '20001', 
            'CommonPart': 'MICROSOFT CORP ... DE', 
            'UncommonPart': ''
        },
        {
            'KUNNR': '20002', 
            'Cluster_ID': '20001', 
            'CommonPart': 'MICROSOFT CORP ... DE', 
            'UncommonPart': 'PORATION'
        },
        {
            'KUNNR': '30001', 
            'Cluster_ID': '30001', 
            'CommonPart': 'WALMART ... CA', 
            'UncommonPart': ' INC'
        },
        {
            'KUNNR': '30002', 
            'Cluster_ID': '30001', 
            'CommonPart': 'WALMART ... CA', 
            'UncommonPart': ' CORP'
        }
    ]
    
    final_df = pd.DataFrame(mock_data)
    
    # Enforce strictly identical datatypes as the main script
    final_df['KUNNR'] = final_df['KUNNR'].astype(str)
    final_df['Cluster_ID'] = final_df['Cluster_ID'].astype(str)
    final_df['CommonPart'] = final_df['CommonPart'].astype(str)
    final_df['UncommonPart'] = final_df['UncommonPart'].astype(str)
    
    return final_df
