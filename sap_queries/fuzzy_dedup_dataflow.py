import pandas as pd
import traceback

def transform(df: pd.DataFrame) -> pd.DataFrame:
    """
    SAP Datasphere Python Dataflow Entry Point.
    Instrumented with granular try-except blocks to trace exactly where Datasphere is failing.
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
            raise RuntimeError(f"PHASE 1 ERROR (DataFrame Conversion): {str(e)}\n{traceback.format_exc()}") from e
            
        # ---------------------------------------------------------
        # PHASE 2: Pure Python Data Prep & Blocking
        # ---------------------------------------------------------
        try:
            blocks = {}
            for r in records:
                kunnr = str(r.get('KUNNR', ''))
                land1 = str(r.get('LAND1', ''))
                
                # Build text string to compare
                text_parts = [str(v) for k, v in r.items() if k not in ('KUNNR', 'LAND1') and pd.notnull(v)]
                text = " ".join(text_parts).upper()
                
                # Clean massive spaces
                text = " ".join(text.split())
                r['__WholeText'] = text
                r['KUNNR_str'] = kunnr
                
                if land1 not in blocks:
                    blocks[land1] = []
                blocks[land1].append(r)
        except Exception as e:
            raise RuntimeError(f"PHASE 2 ERROR (Data Prep & Blocking): {str(e)}\n{traceback.format_exc()}") from e
            
        edges = {}
        
        # ---------------------------------------------------------
        # PHASE 3: Fuzzy Math & Candidate Pairs
        # ---------------------------------------------------------
        try:
            for land1, block_records in blocks.items():
                n = len(block_records)
                for i in range(n):
                    for j in range(i + 1, n):
                        r1 = block_records[i]
                        r2 = block_records[j]
                        
                        t1 = r1['__WholeText']
                        t2 = r2['__WholeText']
                        
                        if abs(len(t1) - len(t2)) > 15:
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
                        sim = 1.0 - (dist / max_len) if max_len > 0 else 0.0
                        
                        # Link valid pairs to graph
                        if sim > 0.75:
                            k1, k2 = r1['KUNNR_str'], r2['KUNNR_str']
                            if k1 not in edges: edges[k1] = []
                            if k2 not in edges: edges[k2] = []
                            edges[k1].append(k2)
                            edges[k2].append(k1)
        except Exception as e:
            raise RuntimeError(f"PHASE 3 ERROR (Fuzzy Math & Edge Generation): {str(e)}\n{traceback.format_exc()}") from e

        # ---------------------------------------------------------
        # PHASE 4: Inline Graph Traversal (DFS)
        # ---------------------------------------------------------
        try:
            visited = set()
            clusters = {}
            cluster_texts = {}
            
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
                    
                    # Find the "Master" text of this cluster for diff extraction
                    centroid_text = ""
                    for rec in records:
                        if rec['KUNNR_str'] == cluster_id:
                            centroid_text = rec['__WholeText']
                            break
                            
                    for member in component:
                        clusters[member] = cluster_id
                        cluster_texts[member] = centroid_text
        except Exception as e:
            raise RuntimeError(f"PHASE 4 ERROR (Graph DFS Traversal): {str(e)}\n{traceback.format_exc()}") from e

        # ---------------------------------------------------------
        # PHASE 5: Output Extraction & Filtering
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
                    
                r_text = r['__WholeText']
                c_text = cluster_texts.get(kunnr, r_text)
                
                # INLINE DIFF EXTRACTION
                if c_text == r_text:
                    c_part, u_part = c_text, ""
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
                    
                # Truncate and assign
                output_rows.append({
                    'KUNNR': kunnr,
                    'Cluster_ID': cid,
                    'CommonPart': c_part.strip()[:64],
                    'UncommonPart': u_part.strip()[:64]
                })
        except Exception as e:
            raise RuntimeError(f"PHASE 5 ERROR (Diff Extraction & Filtering): {str(e)}\n{traceback.format_exc()}") from e
            
        # ---------------------------------------------------------
        # PHASE 6: Final DataFrame Formatting
        # ---------------------------------------------------------
        try:
            final_df = pd.DataFrame(output_rows)
            if final_df.empty:
                return pd.DataFrame(columns=['KUNNR', 'Cluster_ID', 'CommonPart', 'UncommonPart'])
                
            return final_df.sort_values(['Cluster_ID', 'KUNNR']).reset_index(drop=True)
        except Exception as e:
            raise RuntimeError(f"PHASE 6 ERROR (Final DataFrame Generation): {str(e)}\n{traceback.format_exc()}") from e

    except Exception as general_e:
        # Absolute fallback to ensure errors aren't silently swallowed
        if "PHASE" in str(general_e):
            raise general_e
        raise RuntimeError(f"UNKNOWN FATAL ERROR: {str(general_e)}\n{traceback.format_exc()}") from general_e
