import json
from collections import defaultdict

def levenshtein_distance(s1, s2):
    """
    Calculates the Edit Distance between two strings using only standard Python.
    """
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

def fuzzy_deduplicate(records, threshold_pct=0.10):
    """
    Main Dataflow Function.
    Takes a list of record dictionaries and assigns a 'Cluster_ID' to group near-duplicates.
    """
    blocks = defaultdict(list)
    edges = defaultdict(list)
    nodes = set()
    
    # 1. Data Preparation & Blocking
    for r in records:
        # Concatenate columns (Modify keys based on your actual data flow schema)
        text = f"{r.get('Col1', '')}|{r.get('Col2', '')}|{r.get('Col3', '')}".upper().strip()
        r['__WholeText'] = text
        
        # Blocking Key: Group by the first 2 characters to prevent O(N^2) explosion
        # Using only 2 characters ensures we don't miss typos that happen early in the string!
        blocking_key = text[:2]
        blocks[blocking_key].append(r)
        nodes.add(r['ID'])
        
    # 2. Find Valid Pairs within Blocks
    for block_key, block_records in blocks.items():
        n = len(block_records)
        for i in range(n):
            for j in range(i + 1, n):
                r1 = block_records[i]
                r2 = block_records[j]
                t1, t2 = r1['__WholeText'], r2['__WholeText']
                
                # Fast Length Filter before running heavy Levenshtein math
                if abs(len(t1) - len(t2)) > 5:
                    continue
                    
                # Proportional Edit Distance Check
                dist = levenshtein_distance(t1, t2)
                if dist <= threshold_pct * max(len(t1), len(t2)):
                    # Valid match found! Create a bidirectional edge for the graph
                    edges[r1['ID']].append(r2['ID'])
                    edges[r2['ID']].append(r1['ID'])
                    
    # 3. Find Connected Components (DFS Graph Traversal)
    visited = set()
    clusters = {}
    
    for node in nodes:
        if node not in visited:
            # Start a new cluster group
            component = []
            stack = [node]
            while stack:
                curr = stack.pop()
                if curr not in visited:
                    visited.add(curr)
                    component.append(curr)
                    stack.extend(edges.get(curr, []))
            
            # The lowest ID in the connected component becomes the official Cluster ID
            cluster_id = min(component)
            for member in component:
                clusters[member] = cluster_id
                
    # 4. Final Output Formatting
    output = []
    for r in records:
        # Clean up temporary fields and attach the final Cluster_ID
        text = r.pop('__WholeText')
        r['Cluster_ID'] = clusters[r['ID']]
        r['WholeRecordText'] = text
        output.append(r)
        
    # Sort output for readability (optional)
    output.sort(key=lambda x: (x['Cluster_ID'], x['ID']))
    return output

# ==========================================
# LOCAL TESTING
# ==========================================
if __name__ == "__main__":
    sample_data = [
        {'ID': 1, 'Col1': 'Apple', 'Col2': 'Inc', 'Col3': '123 Main St'},
        {'ID': 2, 'Col1': 'Apple', 'Col2': 'Inc.', 'Col3': '123 Main St'},
        {'ID': 3, 'Col1': 'Appel', 'Col2': 'Inc', 'Col3': '123 Main St'}, # Typo
        {'ID': 4, 'Col1': 'Banana', 'Col2': 'Corp', 'Col3': '456 West Dr'},
        {'ID': 5, 'Col1': 'Bannana', 'Col2': 'Corp', 'Col3': '456 West Dr'}, # Typo
        {'ID': 6, 'Col1': 'Orange', 'Col2': 'LLC', 'Col3': '789 East Blvd'},
    ]
    
    print("Running Pure Python Fuzzy Deduplication...")
    results = fuzzy_deduplicate(sample_data)
    
    print("\nResults:")
    print(f"{'Cluster_ID':<12} | {'ID':<5} | {'WholeRecordText'}")
    print("-" * 50)
    for row in results:
        print(f"{row['Cluster_ID']:<12} | {row['ID']:<5} | {row['WholeRecordText']}")
