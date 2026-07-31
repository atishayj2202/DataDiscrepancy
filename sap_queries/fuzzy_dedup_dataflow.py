import pandas as pd
import re
from collections import defaultdict

def levenshtein_distance(s1, s2):
    """Algorithm 1: Standard Edit Distance (Thread-Safe)."""
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
    """Algorithm 2: Jaccard N-Gram Similarity (Thread-Safe)."""
    if not s1 or not s2: return 0.0
    b1 = set([s1[i:i+2] for i in range(len(s1)-1)]) if len(s1) > 1 else set([s1])
    b2 = set([s2[i:i+2] for i in range(len(s2)-1)]) if len(s2) > 1 else set([s2])
    intersection = b1.intersection(b2)
    union = b1.union(b2)
    if not union: return 0.0
    return len(intersection) / len(union)

def calculate_composite_score(t1, t2):
    """Calculates a composite fuzzy score using 2 thread-safe algorithms."""
    if not t1 or not t2: return 0.0
    if abs(len(t1) - len(t2)) > 15: return 0.0 
    
    max_len = max(len(t1), len(t2))
    lev_sim = 1.0 - (levenshtein_distance(t1, t2) / max_len)
    jac_sim = jaccard_bigram_similarity(t1, t2)
    
    return (lev_sim + jac_sim) / 2.0

def extract_diff_parts(centroid_text, record_text):
    """
    Ultra-simple, thread-safe function to find common and uncommon parts.
    Finds the exact matching prefix and suffix, and extracts the differing middle.
    """
    if centroid_text == record_text:
        return centroid_text, ""
        
    # Find matching prefix
    prefix_len = 0
    for c1, c2 in zip(centroid_text, record_text):
        if c1 == c2: prefix_len += 1
        else: break
        
    # Find matching suffix
    suffix_len = 0
    for c1, c2 in zip(reversed(centroid_text[prefix_len:]), reversed(record_text[prefix_len:])):
        if c1 == c2: suffix_len += 1
        else: break
        
    # Build Common Part string
    if suffix_len > 0:
        c_part = centroid_text[:prefix_len] + " ... " + centroid_text[len(centroid_text)-suffix_len:]
    else:
        c_part = centroid_text[:prefix_len]
        
    # Uncommon Part is whatever is left in the record text
    u_part = record_text[prefix_len : len(record_text)-suffix_len]
    
    return c_part.strip(), u_part.strip()

def transform(df: pd.DataFrame) -> pd.DataFrame:
    """
    SAP Datasphere Python Dataflow Entry Point.
    Simplified and explicitly thread-safe.
    """
    if df.empty:
        return df
        
    if 'KUNNR' not in df.columns or 'LAND1' not in df.columns:
        raise ValueError("DataFrame must contain KUNNR (ID) and LAND1 (Blocking Key) columns.")
        
    # 1. Vectorized Data Prep
    text_cols = [c for c in df.columns if c not in ['KUNNR', 'LAND1']]
    df['__WholeText'] = df[text_cols].fillna('').astype(str).agg(' '.join, axis=1)
    df['__WholeText'] = df['__WholeText'].str.upper().apply(lambda x: re.sub(r'\s+', ' ', x).strip())
    
    # 2. Vectorized Blocking via Pandas Self-Merge
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
    
    # 4. Thread-Safe Multi-Algorithm Scoring
    if not df_pairs.empty:
        df_pairs['CompositeScore'] = df_pairs.apply(
            lambda row: calculate_composite_score(row['__WholeText_1'], row['__WholeText_2']), 
            axis=1
        )
        
        valid_pairs = df_pairs[df_pairs['CompositeScore'] > 0.75]
        
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
    
    # 6. Extract Common and Uncommon parts (Thread-Safe)
    centroid_texts = df[df['KUNNR'] == df['Cluster_ID']].set_index('Cluster_ID')['__WholeText'].to_dict()
    
    def get_diffs(row):
        c_id = row['Cluster_ID']
        r_text = row['__WholeText']
        c_text = centroid_texts.get(c_id, r_text)
        return extract_diff_parts(c_text, r_text)
        
    df[['CommonPart', 'UncommonPart']] = df.apply(
        lambda row: pd.Series(get_diffs(row)), axis=1
    )
    
    # 7. Final Formatting & Datatype Enforcement
    df['KUNNR'] = df['KUNNR'].astype(str)
    df['Cluster_ID'] = df['Cluster_ID'].astype(str)
    df['CommonPart'] = df['CommonPart'].astype(str).str.slice(0, 64)
    df['UncommonPart'] = df['UncommonPart'].astype(str).str.slice(0, 64)
    
    # 8. Final Filtering (Drop unique records)
    df = df[df.groupby('Cluster_ID')['Cluster_ID'].transform('count') > 1]
    
    final_cols = ['KUNNR', 'Cluster_ID', 'CommonPart', 'UncommonPart']
    return df[final_cols].sort_values(['Cluster_ID', 'KUNNR']).reset_index(drop=True)
