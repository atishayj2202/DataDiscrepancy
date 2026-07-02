import streamlit as st
import pandas as pd
from collections import defaultdict

def render_casing_inspector():
    if not st.session_state.audit_run:
        st.info("Please click 'Run Quality Audit' in the sidebar to inspect casing inconsistencies.")
    else:
        df = st.session_state.df
        findings = st.session_state.discrepancies
        casing_findings = [f for f in findings if f.issue_type == "Inconsistent Casing"]
        
        if not casing_findings:
            st.success("🎉 All columns have consistent casing!")
        else:
            selected_casing_col = st.selectbox(
                "Select Column with Inconsistent Casing:",
                [f.column for f in casing_findings],
                key="casing_col_select"
            )
            
            finding = next(f for f in casing_findings if f.column == selected_casing_col)
            
            # Run grouping logic to map incorrect variants to dominant one
            col_series = df[finding.column].astype(str)
            groups = defaultdict(lambda: defaultdict(list))
            for idx, val in col_series.items():
                stripped = val.strip()
                if stripped:
                    groups[stripped.lower()][stripped].append(idx)
                    
            casing_corrections = {}
            for lower_val, variants in groups.items():
                if len(variants) > 1:
                    total_group_count = sum(len(indices) for indices in variants.values())
                    dominant_variant = max(variants.keys(), key=lambda k: len(variants[k]))
                    dominant_count = len(variants[dominant_variant])
                    if (dominant_count / total_group_count) >= 0.50:
                        for variant in variants.keys():
                            if variant != dominant_variant:
                                casing_corrections[variant] = dominant_variant
                            
            rows_data = []
            for idx in finding.row_indices:
                current_val = col_series.loc[idx]
                expected_val = casing_corrections.get(current_val.strip(), "N/A")
                rows_data.append({
                    "Row Index": idx,
                    "Current Value": current_val,
                    "Correct (Expected) Value": expected_val
                })
            corrections_df = pd.DataFrame(rows_data)
            
            st.markdown(f"### 📋 Capitalization updates needed for `{finding.column}`")
            st.dataframe(corrections_df, width="stretch", hide_index=True)
            
            st.markdown("### 🔍 Full Rows detail")
            st.dataframe(df.loc[finding.row_indices], width="stretch")
