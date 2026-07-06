import streamlit as st
import pandas as pd
from collections import defaultdict

def render_data_entry_inspector():
    if not st.session_state.audit_run:
        st.info("Please click 'Run Quality Audit' in the sidebar to inspect data entry errors.")
    else:
        df = st.session_state.df
        findings = st.session_state.discrepancies
        
        # Exclude other major categories to capture all "Data Entry" issues
        exclude_types = [
            "Null Value",
            "Incomplete Records",
            "Exact Duplicate Records",
            "Near-Duplicate Records",
            "Inconsistent Casing"
        ]
        data_entry_findings = [f for f in findings if f.issue_type not in exclude_types]
        
        if not data_entry_findings:
            st.success("🎉 No Data Entry Errors (wrong types, format inconsistencies, or out-of-range values) detected in this dataset!")
        else:
            # Group findings by column name
            grouped_findings = defaultdict(list)
            for f in data_entry_findings:
                grouped_findings[f.column].append(f)
                
            st.markdown("### ✍️ Data Entry Error Inspector")
            st.write("Inspect details for wrong data types, format inconsistencies, and out-of-range values grouped by column.")
            
            # Rank columns based of severity (minimum criticality value) and then by affected row count descending
            criticality_order = {"High": 0, "Medium": 1, "Low": 2}
            
            def get_column_rank_key(col_name):
                col_findings = grouped_findings[col_name]
                col_severity = min(criticality_order.get(f.criticality, 3) for f in col_findings)
                unique_rows = set(idx for f in col_findings for idx in f.row_indices)
                col_row_count = len(unique_rows)
                return (col_severity, -col_row_count, col_name)
                
            sorted_cols = sorted(list(grouped_findings.keys()), key=get_column_rank_key)
            
            # Dropdown selection for Column Name (with "All Columns" option)
            options = ["All Columns"] + sorted_cols
            selected_col = st.selectbox(
                "Select Column Name with Data Entry Errors:",
                options,
                key="data_entry_col_select"
            )
            
            def render_column_data_entry(col_name):
                col_findings = grouped_findings[col_name]
                
                # Rank all issues of this column based on criticality (High > Medium > Low)
                col_findings = sorted(col_findings, key=lambda f: criticality_order.get(f.criticality, 3))
                
                st.markdown(f"### 📋 Audit Findings for Column `{col_name}`")
                
                for idx, finding in enumerate(col_findings):
                    # Header mapping
                    icon_map = {
                        "Wrong Data Type": "🚫 Wrong Data Type Error",
                        "Format Inconsistency": "🔣 Format Inconsistency Error",
                        "Clear Out-of-Range": "📉 Clear Out-of-Range Value Deviation",
                        "Borderline Out-of-Range (Requires Review)": "📉 Borderline Out-of-Range Value Deviation"
                    }
                    finding_header = icon_map.get(finding.issue_type, finding.issue_type)
                    
                    st.markdown(f"#### {idx+1}. {finding_header} (Criticality: **{finding.criticality}**)")
                    
                    # Show basic details separated by "|" & ":"
                    num_rows = len(finding.row_indices)
                    if finding.issue_type == "Wrong Data Type":
                        expected_type = "Unknown"
                        if "inferred to be of type '" in finding.interpretation:
                            parts = finding.interpretation.split("inferred to be of type '")
                            if len(parts) > 1:
                                expected_type = parts[1].split("'")[0]
                        details_str = f"Rows Affected: {num_rows} | Expected Standard: {expected_type}"
                        
                    elif finding.issue_type == "Format Inconsistency":
                        dominant_pattern = "Unknown"
                        if "dominant format pattern is '" in finding.interpretation:
                            parts = finding.interpretation.split("dominant format pattern is '")
                            if len(parts) > 1:
                                dominant_pattern = parts[1].split("'")[0]
                        details_str = f"Rows Affected: {num_rows} | Expected Format: {dominant_pattern}"
                        
                    elif finding.issue_type == "Clear Out-of-Range":
                        limits = "Statistical Limits (Z-Score/IQR)"
                        if "violate the configured limits of " in finding.interpretation:
                            parts = finding.interpretation.split("violate the configured limits of ")
                            if len(parts) > 1:
                                limits = parts[1].split(".")[0]
                        details_str = f"Rows Affected: {num_rows} | Allowed Range: {limits}"
                        
                    elif finding.issue_type == "Borderline Out-of-Range (Requires Review)":
                        details_str = f"Rows Affected: {num_rows} | Review Needed: Borderline Out-of-Range"
                        
                    else:
                        # Generic case for whitespace, encoding, or custom issues
                        expected_desc = "Clean Value"
                        if "whitespace" in finding.issue_type.lower():
                            expected_desc = "No leading/trailing spaces"
                        elif "encoding" in finding.issue_type.lower():
                            expected_desc = "Standard text symbols"
                        details_str = f"Rows Affected: {num_rows} | Target State: {expected_desc}"
                    
                    st.markdown(f"`{details_str}`")
                    
                    # Fetch affected rows for this finding
                    affected_df = df.loc[finding.row_indices].astype(str)
                    
                    # Rename the column header to include the warning icon
                    highlighted_header = f"⚠️ {col_name}"
                    display_df = affected_df.rename(columns={col_name: highlighted_header})
                    
                    # Styling helper with custom color per issue type
                    def style_target_col(x):
                        style_df = pd.DataFrame('', index=x.index, columns=x.columns)
                        if highlighted_header in x.columns:
                            if finding.issue_type == "Clear Out-of-Range":
                                # Light Red highlight style
                                style_df[highlighted_header] = 'background-color: rgba(255, 75, 75, 0.15); font-weight: bold; color: #ff4b4b;'
                            elif finding.issue_type == "Borderline Out-of-Range (Requires Review)":
                                # Light Yellow highlight style
                                style_df[highlighted_header] = 'background-color: rgba(255, 170, 0, 0.15); font-weight: bold; color: #ffaa00;'
                            else:
                                # Default Soft Blue highlight style
                                style_df[highlighted_header] = 'background-color: rgba(41, 181, 232, 0.15); font-weight: bold; color: #29b5e8;'
                        return style_df
                        
                    st.dataframe(display_df.style.apply(style_target_col, axis=None), width="stretch")
                    st.markdown("---")

            if selected_col == "All Columns":
                for col in sorted_cols:
                    render_column_data_entry(col)
            else:
                render_column_data_entry(selected_col)
