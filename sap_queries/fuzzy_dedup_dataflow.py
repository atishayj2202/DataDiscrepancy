import pandas as pd
import numpy as np

def transform(df: pd.DataFrame) -> pd.DataFrame:
    """
    SAP Datasphere Python Dataflow Entry Point.
    Basic Algorithm: Column-by-Column average Levenshtein similarity.
    """
    try:
        if df.empty:
            return df
            
        # ---------------------------------------------------------
        # PHASE 1: Convert to pure Python list of dicts
        # ---------------------------------------------------------
        try:
            records = df.to_dict('records')
        except Exception as e:
            raise RuntimeError(f"PHASE 1 ERROR (DataFrame Conversion): {str(e)}")
            
        # ---------------------------------------------------------
        # PHASE 2: Column-by-Column Data Prep & Blocking
        # ---------------------------------------------------------
        try:
            # Dynamically identify all text columns
            text_cols = [c for c in df.columns if c not in ('KUNNR', 'LAND1')]
            blocks = {}
            
            for r in records:
                kunnr = str(r.get('KUNNR', ''))
                land1 = str(r.get('LAND1', ''))
                
                # Clean each text column individually
                for c in text_cols:
                    val = str(r.get(c, '')) if pd.notnull(r.get(c)) else ''
                    val = " ".join(val.upper().split())
                    r[f'__{c}'] = val
                    
                r['KUNNR_str'] = kunnr
                
                if land1 not in blocks:
                    blocks[land1] = []
                blocks[land1].append(r)
        except Exception as e:
            raise RuntimeError(f"PHASE 2 ERROR (Data Prep & Blocking): {str(e)}")
            
        edges = {}
        
        # ---------------------------------------------------------
        # PHASE 3: Column-by-Column Fuzzy Math
        # ---------------------------------------------------------
        try:
            for land1, block_records in blocks.items():
                n = len(block_records)
                for i in range(n):
                    for j in range(i + 1, n):
                        r1 = block_records[i]
                        r2 = block_records[j]
                        
                        col_sims = []
                        valid_comparison = True
                        
                        for c in text_cols:
                            t1 = r1[f'__{c}']
                            t2 = r2[f'__{c}']
                            
                            # CRITICAL FIX: If BOTH are empty, completely ignore this column (don't score it as 100%!)
                            if len(t1) == 0 and len(t2) == 0:
                                continue
                                
                            # If only ONE is empty, it's a 0% match for this column
                            if len(t1) == 0 or len(t2) == 0:
                                col_sims.append(0.0)
                                continue
                            
                            # Fast fail if any column is wildly different in length
                            if abs(len(t1) - len(t2)) > 15:
                                col_sims.append(0.0)
                                continue
                                
                            # INLINE LEVENSHTEIN ALGORITHM
                            s1, s2 = t1, t2
                            if len(s1) < len(s2):
                                s1, s2 = s2, s1
                            if len(s2) == 0:
                                dist = len(s1)
                            else:
                                previous_row = list(range(len(s2) + 1))
                                for idx, c1 in enumerate(s1):
                                    current_row = [idx + 1]
                                    for jdx, c2 in enumerate(s2):
                                        insertions = previous_row[jdx + 1] + 1
                                        deletions = current_row[jdx] + 1
                                        substitutions = previous_row[jdx] + (c1 != c2)
                                        current_row.append(min(insertions, deletions, substitutions))
                                    previous_row = current_row
                                dist = previous_row[-1]
                            
                            max_len = max(len(t1), len(t2))
                            sim = 1.0 - (dist / max_len)
                            col_sims.append(sim)
                            
                        # Average similarity across all VALID columns
                        avg_sim = sum(col_sims) / len(col_sims) if col_sims else 0.0
                        
                        # Link valid pairs to graph (Threshold increased to 85%)
                        if avg_sim >= 0.85:
                            k1, k2 = r1['KUNNR_str'], r2['KUNNR_str']
                            if k1 not in edges: edges[k1] = []
                            if k2 not in edges: edges[k2] = []
                            edges[k1].append(k2)
                            edges[k2].append(k1)
        except Exception as e:
            raise RuntimeError(f"PHASE 3 ERROR (Fuzzy Math & Edge Generation): {str(e)}")

        # ---------------------------------------------------------
        # PHASE 4: Inline Graph Traversal (DFS)
        # ---------------------------------------------------------
        try:
            visited = set()
            clusters = {}
            cluster_centroids = {}
            
            for r in records:
                node = r['KUNNR_str']
                if node not in visited:
                    component = []
                    stack = [node]
                    while stack:
                        curr = stack.pop()
                        if curr not in visited:
                            visited.add(curr)
                            component.append(curr)
                            if curr in edges:
                                stack.extend(edges[curr])
                    
                    cluster_id = min(component)
                    
                    # Store the entire master record of this cluster for diff extraction
                    centroid_rec = None
                    for rec in records:
                        if rec['KUNNR_str'] == cluster_id:
                            centroid_rec = rec
                            break
                            
                    for member in component:
                        clusters[member] = cluster_id
                        cluster_centroids[member] = centroid_rec
        except Exception as e:
            raise RuntimeError(f"PHASE 4 ERROR (Graph DFS Traversal): {str(e)}")

        # ---------------------------------------------------------
        # PHASE 5: Field-Level Diff Extraction
        # ---------------------------------------------------------
        try:
            output_rows = []
            
            # Calculate cluster sizes manually to filter unique records
            cluster_sizes = {}
            for c in clusters.values():
                cluster_sizes[c] = cluster_sizes.get(c, 0) + 1
                
            for r in records:
                kunnr = r['KUNNR_str']
                cid = clusters.get(kunnr, kunnr)
                
                # Only process rows that belong to a cluster with > 1 record
                if cluster_sizes.get(cid, 1) <= 1:
                    continue 
                    
                c_rec = cluster_centroids.get(kunnr, r)
                
                common_parts = []
                uncommon_parts = []
                
                # INLINE FIELD-LEVEL DIFF EXTRACTION
                for c in text_cols:
                    r_text = r[f'__{c}']
                    c_text = c_rec[f'__{c}']
                    
                    if c_text == r_text:
                        if r_text:
                            common_parts.append(r_text)
                    else:
                        prefix_len = 0
                        for c1, c2 in zip(c_text, r_text):
                            if c1 == c2: prefix_len += 1
                            else: break
                            
                        suffix_len = 0
                        for c1, c2 in zip(reversed(c_text[prefix_len:]), reversed(r_text[prefix_len:])):
                            if c1 == c2: suffix_len += 1
                            else: break
                            
                        # Mathematically inject '...' where the typo occurred
                        if suffix_len > 0 and prefix_len > 0:
                            c_part = c_text[:prefix_len] + " ... " + c_text[len(c_text)-suffix_len:]
                        elif prefix_len > 0:
                            c_part = c_text[:prefix_len] + " ..."
                        elif suffix_len > 0:
                            c_part = "... " + c_text[len(c_text)-suffix_len:]
                        else:
                            c_part = "..."
                            
                        c_diff = c_text[prefix_len : len(c_text)-suffix_len]
                        r_diff = r_text[prefix_len : len(r_text)-suffix_len]
                        
                        if c_part != "...":
                            common_parts.append(c_part.strip())
                            
                        # Show BOTH sides of the change! e.g. NAME1(LE -> EL)
                        uncommon_parts.append(f"{c}({c_diff.strip()} -> {r_diff.strip()})")
                            
                # Format with | separators and truncate to 250 characters max
                output_rows.append({
                    'KUNNR': kunnr,
                    'Cluster_ID': cid,
                    'CommonPart': " | ".join(common_parts)[:250],
                    'UncommonPart': " | ".join(uncommon_parts)[:250]
                })
        except Exception as e:
            raise RuntimeError(f"PHASE 5 ERROR (Diff Extraction & Filtering): {str(e)}")
            
        # ---------------------------------------------------------
        # PHASE 6: Final DataFrame Formatting
        # ---------------------------------------------------------
        try:
            final_df = pd.DataFrame(output_rows)
            if final_df.empty:
                return pd.DataFrame(columns=['KUNNR', 'Cluster_ID', 'CommonPart', 'UncommonPart'])
                
            return final_df.sort_values(['Cluster_ID', 'KUNNR']).reset_index(drop=True)
        except Exception as e:
            raise RuntimeError(f"PHASE 6 ERROR (Final DataFrame Generation): {str(e)}")

    except Exception as general_e:
        # Absolute fallback to ensure errors aren't silently swallowed
        if "PHASE" in str(general_e):
            raise general_e
        raise RuntimeError(f"UNKNOWN FATAL ERROR: {str(general_e)}")
