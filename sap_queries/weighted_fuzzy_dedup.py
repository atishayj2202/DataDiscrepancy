import pandas as pd
import numpy as np

def transform(df: pd.DataFrame) -> pd.DataFrame:
    """
    SAP Datasphere Python Dataflow Entry Point.
    Advanced Algorithm: Cardinality-Weighted Column-by-Column Fuzzy Deduplication.
    """
    try:
        if df.empty:
            return df
            
        # ---------------------------------------------------------
        # PHASE 1: Convert to pure Python list of dicts
        # ---------------------------------------------------------
        try:
            records = df.to_dict('records')
            total_records = len(records)
        except Exception as e:
            raise RuntimeError(f"PHASE 1 ERROR (DataFrame Conversion): {str(e)}")
            
        # ---------------------------------------------------------
        # PHASE 2: Calculate Cardinality Weights & Block Data
        # ---------------------------------------------------------
        try:
            text_cols = [c for c in df.columns if c not in ('KUNNR', 'LAND1')]
            
            # 2a. Calculate dataset-wide cardinality for every column
            # (Higher cardinality = more unique values = higher weight when matching)
            col_weights = {}
            for c in text_cols:
                unique_vals = set(r.get(c, '') for r in records if pd.notnull(r.get(c)))
                # Normalize weight between ~0.0 and 1.0
                weight = len(unique_vals) / total_records if total_records > 0 else 1.0
                # Ensure no column has literally 0 weight
                col_weights[c] = max(weight, 0.05)
                
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
            raise RuntimeError(f"PHASE 2 ERROR (Data Prep & Cardinality Weighting): {str(e)}")
            
        edges = {}
        
        # ---------------------------------------------------------
        # PHASE 3: Weighted Column-by-Column Fuzzy Math
        # ---------------------------------------------------------
        try:
            for land1, block_records in blocks.items():
                n = len(block_records)
                for i in range(n):
                    for j in range(i + 1, n):
                        r1 = block_records[i]
                        r2 = block_records[j]
                        
                        weighted_sim_sum = 0.0
                        total_weight = 0.0
                        valid_comparison = True
                        
                        for c in text_cols:
                            t1 = r1[f'__{c}']
                            t2 = r2[f'__{c}']
                            w = col_weights[c]
                            
                            if abs(len(t1) - len(t2)) > 15:
                                valid_comparison = False
                                break
                                
                            if len(t1) == 0 and len(t2) == 0:
                                weighted_sim_sum += (1.0 * w)
                                total_weight += w
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
                            
                            # The 'Length of Change' impact is mathematically inherent here.
                            # A 1-char typo in a 3-char string = 0.66 sim (huge penalty).
                            # A 1-char typo in a 20-char string = 0.95 sim (minor penalty).
                            max_len = max(len(t1), len(t2))
                            sim = 1.0 - (dist / max_len)
                            
                            weighted_sim_sum += (sim * w)
                            total_weight += w
                            
                        if not valid_comparison or total_weight == 0:
                            continue
                            
                        # Final score is the cardinality-weighted average
                        composite_score = weighted_sim_sum / total_weight
                        
                        # Link valid pairs to graph
                        if composite_score > 0.75:
                            k1, k2 = r1['KUNNR_str'], r2['KUNNR_str']
                            if k1 not in edges: edges[k1] = []
                            if k2 not in edges: edges[k2] = []
                            edges[k1].append(k2)
                            edges[k2].append(k1)
        except Exception as e:
            raise RuntimeError(f"PHASE 3 ERROR (Weighted Fuzzy Math): {str(e)}")

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
                            
                        if suffix_len > 0:
                            c_part = c_text[:prefix_len] + " ... " + c_text[len(c_text)-suffix_len:]
                        else:
                            c_part = c_text[:prefix_len]
                            
                        u_part = r_text[prefix_len : len(r_text)-suffix_len]
                        
                        if c_part:
                            common_parts.append(c_part.strip())
                        if u_part:
                            # Tag the uncommon part with the specific field name!
                            uncommon_parts.append(f"{c}({u_part.strip()})")
                            
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
        if "PHASE" in str(general_e):
            raise general_e
        raise RuntimeError(f"UNKNOWN FATAL ERROR: {str(general_e)}")
