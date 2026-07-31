import pandas as pd
import difflib
import re
from collections import defaultdict

def levenshtein_distance(s1, s2):
    """Algorithm 1: Standard Edit Distance."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def jaccard_bigram_similarity(s1, s2):
    """Algorithm 2: Jaccard N-Gram Similarity."""
    if not s1 or not s2: return 0.0
    b1 = set([s1[i:i+2] for i in range(len(s1)-1)]) if len(s1) > 1 else set([s1])
    b2 = set([s2[i:i+2] for i in range(len(s2)-1)]) if len(s2) > 1 else set([s2])
    intersection = b1.intersection(b2)
    union = b1.union(b2)
    if not union: return 0.0
    return len(intersection) / len(union)

def calculate_composite_score(t1, t2):
    """Calculates a composite fuzzy score using 3 different algorithms."""
    if not t1 or not t2: return 0.0
    if abs(len(t1) - len(t2)) > 15: return 0.0 # Fast fail for wildly different strings
    
    # Algorithm 1: Levenshtein (Normalized)
    max_len = max(len(t1), len(t2))
    lev_sim = 1.0 - (levenshtein_distance(t1, t2) / max_len)
    
    # Algorithm 2: Jaccard Bigram
    jac_sim = jaccard_bigram_similarity(t1, t2)
    
    # Algorithm 3: Ratcliff/Obershelp Pattern Matching (Built-in)
    seq_sim = difflib.SequenceMatcher(None, t1, t2).ratio()
    
    # Composite Score (Equal Weights)
    return (lev_sim + jac_sim + seq_sim) / 3.0

def extract_diff_parts(centroid_text, record_text):
    """Uses difflib to extract exactly which parts match and which parts differ."""
    if centroid_text == record_text:
        return centroid_text, ""
        
    s = difflib.SequenceMatcher(None, centroid_text, record_text)
    common = []
    uncommon = []
    
    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if tag == 'equal':
            common.append(record_text[j1:j2])
        else:
            if j1 != j2:
                uncommon.append(record_text[j1:j2])
                
    return " ... ".join(common).strip(), " | ".join(uncommon).strip()

def transform(df: pd.DataFrame) -> pd.DataFrame:
    """
    SAP Datasphere Python Dataflow Entry Point.
    Uses Pandas vectorized operations for max performance.
    """
    if df.empty:
        return df
        
    # Ensure required columns exist
    if 'KUNNR' not in df.columns or 'LAND1' not in df.columns:
        raise ValueError("DataFrame must contain KUNNR (ID) and LAND1 (Blocking Key) columns.")
        
    # 1. Vectorized Data Prep
    # Concatenate all non-key columns into a single text block for comparison
    text_cols = [c for c in df.columns if c not in ['KUNNR', 'LAND1']]
    df['__WholeText'] = df[text_cols].fillna('').astype(str).agg(' '.join, axis=1)
    df['__WholeText'] = df['__WholeText'].str.upper().apply(lambda x: re.sub(r'\s+', ' ', x).strip())
    
    # 2. Vectorized Blocking via Pandas Self-Merge
    # Instantly pairs all records within the same country code
    df_pairs = pd.merge(
        df[['KUNNR', 'LAND1', '__WholeText']], 
        df[['KUNNR', 'LAND1', '__WholeText']], 
        on='LAND1', 
        suffixes=('_1', '_2')
    )
    
    # 3. Filter duplicate candidate pairs and self-joins
    df_pairs = df_pairs[df_pairs['KUNNR_1'] < df_pairs['KUNNR_2']].copy()
    
    edges = defaultdict(list)
    nodes = set(df['KUNNR'])
    
    # 4. Multi-Algorithm Scoring
    if not df_pairs.empty:
        # Apply the composite scoring function across the paired dataframe
        df_pairs['CompositeScore'] = df_pairs.apply(
            lambda row: calculate_composite_score(row['__WholeText_1'], row['__WholeText_2']), 
            axis=1
        )
        
        # Filter strictly for pairs with > 75% composite similarity
        valid_pairs = df_pairs[df_pairs['CompositeScore'] > 0.75]
        
        # Extract pairs to standard python for fast DFS graph traversal
        for _, row in valid_pairs.iterrows():
            edges[row['KUNNR_1']].append(row['KUNNR_2'])
            edges[row['KUNNR_2']].append(row['KUNNR_1'])
            
    # 5. Fast Graph Traversal (DFS)
    visited = set()
    clusters = {}
    
    for node in nodes:
        if node not in visited:
            component = []
            stack = [node]
            while stack:
                curr = stack.pop()
                if curr not in visited:
                    visited.add(curr)
                    component.append(curr)
                    stack.extend(edges.get(curr, []))
            
            cluster_id = min(component)
            for member in component:
                clusters[member] = cluster_id
                
    df['Cluster_ID'] = df['KUNNR'].map(clusters)
    
    # 6. Extract Common and Uncommon parts
    # Find the "Master" record text for each cluster
    centroid_texts = df[df['KUNNR'] == df['Cluster_ID']].set_index('Cluster_ID')['__WholeText'].to_dict()
    
    def get_diffs(row):
        c_id = row['Cluster_ID']
        r_text = row['__WholeText']
        c_text = centroid_texts.get(c_id, r_text)
        return extract_diff_parts(c_text, r_text)
        
    # Apply the diff extractor to generate the final display columns
    df[['CommonPart', 'UncommonPart']] = df.apply(
        lambda row: pd.Series(get_diffs(row)), axis=1
    )
    
    # 7. Final Formatting & Datatype Enforcement
    # Ensure KUNNR and Cluster_ID are standard strings to match SAP schema
    df['KUNNR'] = df['KUNNR'].astype(str)
    df['Cluster_ID'] = df['Cluster_ID'].astype(str)
    
    # Enforce strict 64-character limit for the preview strings
    df['CommonPart'] = df['CommonPart'].astype(str).str.slice(0, 64)
    df['UncommonPart'] = df['UncommonPart'].astype(str).str.slice(0, 64)
    
    # 8. Final Filtering
    # Only return rows that are part of a cluster with > 1 record (i.e., drop all unique records)
    df = df[df.groupby('Cluster_ID')['Cluster_ID'].transform('count') > 1]
    
    final_cols = ['KUNNR', 'Cluster_ID', 'CommonPart', 'UncommonPart']
    return df[final_cols].sort_values(['Cluster_ID', 'KUNNR']).reset_index(drop=True)
