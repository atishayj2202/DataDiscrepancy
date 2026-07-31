import json
import re
from collections import defaultdict

def levenshtein_distance(s1, s2):
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

def get_blocking_keys(text):
    """
    Generates multiple blocking keys to ensure high recall.
    If a typo occurs at the start of a word, the suffix or consonant key will catch it.
    """
    keys = []
    clean_text = re.sub(r'[^A-Z0-9]', '', text)
    
    if len(clean_text) >= 3:
        keys.append(f"PRE_{clean_text[:3]}")  # Prefix block
        keys.append(f"SUF_{clean_text[-3:]}") # Suffix block
        
    # Consonant Skeleton (Strip vowels)
    consonants = re.sub(r'[AEIOU]', '', clean_text)
    if len(consonants) >= 3:
        keys.append(f"CON_{consonants[:4]}")  # First 4 consonants
        
    if not keys:
        keys.append(f"ALL_{clean_text}")
        
    return keys

def fuzzy_deduplicate(records, threshold_pct=0.15):
    """
    Most Accurate & Reliable Fuzzy Deduplication Dataflow Function.
    """
    blocks = defaultdict(list)
    edges = defaultdict(list)
    nodes = set()
    
    # 1. Data Preparation & Multi-Pass Blocking
    for r in records:
        # Safely handle explicit None values returned from database
        col1 = r.get('Col1') or ""
        col2 = r.get('Col2') or ""
        col3 = r.get('Col3') or ""
        
        text = f"{col1}|{col2}|{col3}".upper()
        # Remove massive spaces
        text = re.sub(r'\s+', ' ', text).strip()
        r['__WholeText'] = text
        nodes.add(r['ID'])
        
        b_keys = get_blocking_keys(text)
        for bk in b_keys:
            blocks[bk].append(r)
            
    # 2. Find Valid Pairs within Blocks
    processed_pairs = set()
    
    for block_key, block_records in blocks.items():
        n = len(block_records)
        for i in range(n):
            for j in range(i + 1, n):
                r1 = block_records[i]
                r2 = block_records[j]
                
                # Ensure we don't process the same pair multiple times if they share multiple blocks
                pair_id = tuple(sorted([r1['ID'], r2['ID']]))
                if pair_id in processed_pairs:
                    continue
                processed_pairs.add(pair_id)
                
                t1, t2 = r1['__WholeText'], r2['__WholeText']
                
                if abs(len(t1) - len(t2)) > 5:
                    continue
                    
                dist = levenshtein_distance(t1, t2)
                if dist <= threshold_pct * max(len(t1), len(t2)):
                    edges[r1['ID']].append(r2['ID'])
                    edges[r2['ID']].append(r1['ID'])
                    
    # 3. Find Connected Components (DFS Graph Traversal)
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
                
    # 4. Final Output Formatting
    output = []
    for r in records:
        text = r.pop('__WholeText')
        r['Cluster_ID'] = clusters[r['ID']]
        r['WholeRecordText'] = text
        output.append(r)
        
    output.sort(key=lambda x: (x['Cluster_ID'], x['ID']))
    return output
