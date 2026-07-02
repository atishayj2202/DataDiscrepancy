import streamlit as st
import pandas as pd
import numpy as np

def render_row_inspector():
    if not st.session_state.audit_run:
        st.info("Please click 'Run Quality Audit' in the sidebar to inspect affected rows.")
    else:
        findings = st.session_state.discrepancies
        if not findings:
            st.success("🎉 No issues detected! Nothing to inspect.")
        else:
            st.markdown("### 🔎 Row-Level Inspector")
            st.write("Inspect the actual rows in the dataset affected by each quality issue.")
            
            # Classify findings into categories
            categories = {
                "Duplicate Rows": [],
                "Near to Duplicate Rows": [],
                "Inconsistent Casing": [],
                "Data Entry Error (Low)": [],
                "Data Entry Error (Medium)": [],
                "Data Entry Error (High)": [],
                "Incomplete Records": []
            }
            
            for f in findings:
                if f.issue_type in ["Null Value", "Incomplete Records"]:
                    categories["Incomplete Records"].append(f)
                elif f.issue_type == "Exact Duplicate Records":
                    categories["Duplicate Rows"].append(f)
                elif f.issue_type == "Near-Duplicate Records":
                    categories["Near to Duplicate Rows"].append(f)
                elif f.issue_type == "Inconsistent Casing":
                    categories["Inconsistent Casing"].append(f)
                elif f.issue_type in ["Clear Out-of-Range", "Borderline Out-of-Range (Requires Review)", 
                                       "Ambiguous Statistical Outlier (Requires Review)", "Confirmed Statistical Outlier", 
                                       "Wrong Data Type", "Format Inconsistency"]:
                    if f.criticality == "High":
                        categories["Data Entry Error (High)"].append(f)
                    elif f.criticality == "Medium":
                        categories["Data Entry Error (Medium)"].append(f)
                    else:
                        categories["Data Entry Error (Low)"].append(f)
                elif f.issue_type == "Whitespace & Encoding":
                    val_str = str(f.example_value).strip()
                    if val_str in ["?", "-"] or not val_str:
                        categories["Incomplete Records"].append(f)
                    else:
                        categories["Incomplete Records"].append(f)
                else:
                    if f.issue_type not in ["Null Value", "Incomplete Records"]:
                        if f.criticality == "High":
                            categories["Data Entry Error (High)"].append(f)
                        elif f.criticality == "Medium":
                            categories["Data Entry Error (Medium)"].append(f)
                        else:
                            categories["Data Entry Error (Low)"].append(f)
            
            # Filter categories that have findings
            active_categories = {k: v for k, v in categories.items() if len(v) > 0}
            
            if not active_categories:
                st.info("No active discrepancy categories detected.")
            else:
                # 1. Select Category
                selected_cat = st.selectbox(
                    "Choose Error Type to inspect:",
                    list(active_categories.keys()),
                    key="row_inspector_cat_select"
                )
                
                cat_findings = active_categories[selected_cat]
                
                # 2. Select Column & Issue Type to inspect
                options_map = {
                    f"{f.column} — {f.issue_type} ({len(f.row_indices)} rows)": f 
                    for f in cat_findings
                }
                sorted_options = sorted(list(options_map.keys()))
                
                selected_option = st.selectbox(
                    "Select Column & Issue Type to inspect:",
                    sorted_options,
                    key="row_inspector_col_select"
                )
                
                # Find the finding matching this selection
                selected_issue = options_map[selected_option]
                
                # Minimal format description (without description details card)
                st.markdown(f"**Selected Issue:** {selected_issue.issue_type} | **Column:** `{selected_issue.column}` | **Criticality:** {selected_issue.criticality} | **Rows Affected:** `{len(selected_issue.row_indices)}`")
                st.markdown("---")
            
                # Search within rows
                search_query = st.text_input("🔍 Search within affected rows (regex supported):", "", key="row_inspector_search")
                
                # Get the slice of affected rows
                affected_df = st.session_state.df.loc[selected_issue.row_indices]
                
                # Filter by search query
                if search_query:
                    mask = affected_df.astype(str).apply(
                        lambda row: row.str.contains(search_query, case=False, regex=True).any(), 
                        axis=1
                    )
                    affected_df = affected_df[mask]
                
                total_matching = len(affected_df)
                st.markdown(f"📊 **Rows matching search:** `{total_matching}` / `{len(selected_issue.row_indices)}` total affected rows")
                
                # Pagination
                page_size = 15
                num_pages = max(1, int(np.ceil(total_matching / page_size)))
                
                # Render pagination inputs side-by-side with download button
                col_pag1, col_pag2 = st.columns([1, 1])
                with col_pag1:
                    page_num = st.number_input("Page", min_value=1, max_value=num_pages, value=1, step=1, key="row_inspector_page")
                with col_pag2:
                    csv_data = affected_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Affected Rows as CSV",
                        data=csv_data,
                        file_name=f"{selected_issue.column}_{selected_issue.issue_type}_affected_rows.csv",
                        mime="text/csv",
                        key="download_affected_rows"
                    )
                
                start_idx = (page_num - 1) * page_size
                end_idx = start_idx + page_size
                
                st.dataframe(affected_df.iloc[start_idx:end_idx].astype(str), width="stretch")
