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
            # Rank columns by row counts affected (descending)
            casing_columns = list(set(f.column for f in casing_findings))
            sorted_casing_cols = sorted(
                casing_columns,
                key=lambda col: (-sum(len(f.row_indices) for f in casing_findings if f.column == col), col)
            )
            
            # 1. Ask for Column Name in drop down (with "All Columns" option)
            options = ["All Columns"] + sorted_casing_cols
            selected_casing_col = st.selectbox(
                "Select Column Name with Inconsistent Casing:",
                options,
                key="casing_col_select"
            )
            
            def render_column_casing_groups(col_name):
                # Run grouping logic to identify casing collision groups
                col_series = df[col_name].astype(str)
                groups = defaultdict(lambda: defaultdict(list))
                for idx, val in col_series.items():
                    stripped = val.strip()
                    if stripped:
                        groups[stripped.lower()][stripped].append(idx)
                
                st.markdown(f"### 📋 Capitalization Update Groups for `{col_name}`")
                st.write("Each group shows the correct capitalization standard and the list of inconsistent records requiring update.")
                
                collision_groups_found = 0
                for lower_val, variants in groups.items():
                    if len(variants) > 1:
                        total_group_count = sum(len(indices) for indices in variants.values())
                        dominant_variant = max(variants.keys(), key=lambda k: len(variants[k]))
                        dominant_count = len(variants[dominant_variant])
                        
                        # Only show if dominant standard has >= 50% threshold representation
                        if (dominant_count / total_group_count) >= 0.50:
                            incorrect_row_indices = []
                            for variant, indices in variants.items():
                                if variant != dominant_variant:
                                    incorrect_row_indices.extend(indices)
                                    
                            if incorrect_row_indices:
                                collision_groups_found += 1
                                
                                # First Line: Correct Casing in medium size and bold
                                st.markdown(f"#### 🔤 Correct Casing: **{dominant_variant}**")
                                
                                # Fetch inconsistent rows
                                group_df = df.loc[incorrect_row_indices]
                                
                                # Styling helper to highlight and bold the selected casing column
                                def style_column(x):
                                    style_df = pd.DataFrame('', index=x.index, columns=x.columns)
                                    style_df[col_name] = 'background-color: rgba(41, 181, 232, 0.15); font-weight: bold; color: #ffaa00;'
                                    return style_df
                                    
                                st.dataframe(group_df.style.apply(style_column, axis=None), width="stretch")
                                st.markdown("---")
                
                if collision_groups_found == 0:
                    st.info(f"No capitalization groups in column `{col_name}` met the 50% dominant casing requirement.")

            if selected_casing_col == "All Columns":
                for col in sorted_casing_cols:
                    render_column_casing_groups(col)
            else:
                render_column_casing_groups(selected_casing_col)
