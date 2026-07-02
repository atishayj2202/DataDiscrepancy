from typing import List
import streamlit as st
import pandas as pd
import altair as alt
from src.agents.base import Discrepancy
from src.streamlit.kpi import render_audit_donut

def render_quality_audit_findings():
    if not st.session_state.audit_run:
        st.info("Please click 'Run Quality Audit' in the sidebar to scan your dataset.")
    else:
        findings: List[Discrepancy] = st.session_state.discrepancies
        
        if not findings:
            st.success("🎉 No issues detected! Your dataset matches all active agent validation checks.")
        else:
            # Stats widgets
            high_count = sum(1 for f in findings if f.criticality == "High")
            med_count = sum(1 for f in findings if f.criticality == "Medium")
            low_count = sum(1 for f in findings if f.criticality == "Low")
            review_count = sum(1 for f in findings if f.review_needed)
            
            sc1, sc2, sc3, sc4, sc5 = st.columns(5)
            with sc1:
                st.metric("Total Issues", len(findings))
            with sc2:
                st.metric("High Criticality 🔴", high_count)
            with sc3:
                st.metric("Medium Criticality 🟡", med_count)
            with sc4:
                st.metric("Low Criticality 🔵", low_count)
            with sc5:
                st.metric("Requires Review 🟣", review_count)
            
            st.markdown("---")
            
            # Filters
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                filter_col = st.selectbox("Filter by Column", ["All"] + list(set(f.column for f in findings)), key="audit_filter_col")
            with fc2:
                filter_type = st.selectbox("Filter by Issue Type", ["All"] + list(set(f.issue_type for f in findings)), key="audit_filter_type")
            with fc3:
                filter_crit = st.selectbox("Filter by Criticality", ["All", "High", "Medium", "Low"], key="audit_filter_crit")
            
            # Apply filter
            filtered_findings = findings
            if filter_col != "All":
                filtered_findings = [f for f in filtered_findings if f.column == filter_col]
            if filter_type != "All":
                filtered_findings = [f for f in filtered_findings if f.issue_type == filter_type]
            if filter_crit != "All":
                filtered_findings = [f for f in filtered_findings if f.criticality == filter_crit]
            
            st.markdown(f"### 📋 Discrepancy Report ({len(filtered_findings)} issues filtered)")
            
            # View toggle Segmented Control
            group_view = st.radio(
                "Group Findings By:", 
                ["Issue Type (Standard)", "Dataset Column"], 
                horizontal=True,
                key="audit_group_view"
            )
            
            if group_view == "Issue Type (Standard)":
                unique_issue_types = sorted(list(set(f.issue_type for f in filtered_findings)))
                if unique_issue_types:
                    for issue_type in unique_issue_types:
                        issue_findings = [f for f in filtered_findings if f.issue_type == issue_type]
                        total_rows_affected = sum(len(f.row_indices) for f in issue_findings)
                        
                        expander_label = f"📁 {issue_type} — {len(issue_findings)} columns affected ({total_rows_affected} total rows affected)"
                        
                        with st.expander(expander_label):
                            table_rows = []
                            for f in issue_findings:
                                review_status = "🟣 Needs Review" if f.review_needed else "🟢 Deterministic"
                                table_rows.append({
                                    "Column": f.column,
                                    "Criticality": f.criticality,
                                    "Rows Affected": len(f.row_indices),
                                    "Example Value": str(f.example_value),
                                    "Remediation / Interpretation": f.interpretation,
                                    "Review Status": review_status
                                })
                            st.dataframe(
                                pd.DataFrame(table_rows), 
                                width="stretch", 
                                hide_index=True,
                                column_config={
                                    "Rows Affected": st.column_config.NumberColumn(format="%d"),
                                }
                            )
                            
                            # Display larger donut chart below the table
                            chart_data = {f.column: len(f.row_indices) for f in issue_findings}
                            st.altair_chart(render_audit_donut(chart_data, "Affected Columns Breakdown"), use_container_width=True)
                else:
                    st.info("No issues found matching the active filters.")
            else:
                # Column View
                unique_cols = sorted(list(set(f.column for f in filtered_findings)))
                if unique_cols:
                    for col in unique_cols:
                        col_findings = [f for f in filtered_findings if f.column == col]
                        total_rows_affected = len(set(idx for f in col_findings for idx in f.row_indices))
                        
                        expander_label = f"📁 {col} — {len(col_findings)} issue types detected ({total_rows_affected} unique rows affected)"
                        
                        with st.expander(expander_label):
                            table_rows = []
                            for f in col_findings:
                                review_status = "🟣 Needs Review" if f.review_needed else "🟢 Deterministic"
                                table_rows.append({
                                    "Issue Type": f.issue_type,
                                    "Criticality": f.criticality,
                                    "Rows Affected": len(f.row_indices),
                                    "Example Value": str(f.example_value),
                                    "Remediation / Interpretation": f.interpretation,
                                    "Review Status": review_status
                                })
                            st.dataframe(
                                pd.DataFrame(table_rows), 
                                width="stretch", 
                                hide_index=True,
                                column_config={
                                    "Rows Affected": st.column_config.NumberColumn(format="%d"),
                                }
                            )
                            
                            # Display larger donut chart below the table
                            chart_data = {f.issue_type: len(f.row_indices) for f in col_findings}
                            st.altair_chart(render_audit_donut(chart_data, "Issue Breakdown"), use_container_width=True)
                else:
                    st.info("No columns affected matching the active filters.")

def render_visualization():
    if not st.session_state.audit_run:
        st.info("Please click 'Run Quality Audit' in the sidebar to visualize findings.")
    else:
        findings: List[Discrepancy] = st.session_state.discrepancies
        if not findings:
            st.success("🎉 No issues detected! Nothing to visualize.")
        else:
            st.markdown("### 📈 Data Quality Visualization Dashboard")
            st.write("Visual insights into detected discrepancies across your dataset.")
            
            # Issue counts by criticality
            high_count = sum(1 for f in findings if f.criticality == "High")
            med_count = sum(1 for f in findings if f.criticality == "Medium")
            low_count = sum(1 for f in findings if f.criticality == "Low")
            
            # Grid of global stats charts
            vc1, vc2 = st.columns(2)
            
            with vc1:
                st.markdown("#### 🔴 Issue count by Criticality")
                crit_df = pd.DataFrame({
                    "Criticality": ["High 🔴", "Medium 🟡", "Low 🔵"],
                    "Count": [high_count, med_count, low_count]
                })
                crit_df = crit_df.sort_values(by="Count", ascending=False)
                
                bar = alt.Chart(crit_df).mark_bar().encode(
                    x=alt.X('Count:Q', title='Count'),
                    y=alt.Y('Criticality:N', sort='-x', title='Criticality'),
                    color=alt.Color('Criticality:N', scale=alt.Scale(domain=["High 🔴", "Medium 🟡", "Low 🔵"], range=["#ff4b4b", "#ffaa00", "#29b5e8"]), legend=None),
                    tooltip=['Criticality', 'Count']
                )
                text = bar.mark_text(align='left', baseline='middle', dx=3).encode(
                    text='Count:Q'
                )
                crit_chart = (bar + text).properties(height=120)
                st.altair_chart(crit_chart, use_container_width=True)
                
            with vc2:
                st.markdown("#### 📋 Issues by Column")
                col_series = pd.Series([f.column for f in findings])
                col_counts = col_series.value_counts().reset_index()
                col_counts.columns = ["Column", "Issues Found"]
                
                bar = alt.Chart(col_counts).mark_bar().encode(
                    x=alt.X('Issues Found:Q', title='Issues Found'),
                    y=alt.Y('Column:N', sort='-x', title='Column'),
                    tooltip=['Column', 'Issues Found']
                )
                text = bar.mark_text(align='left', baseline='middle', dx=3).encode(
                    text='Issues Found:Q'
                )
                col_chart = (bar + text).properties(height=max(120, len(col_counts) * 20))
                st.altair_chart(col_chart, use_container_width=True)
            
            st.markdown("#### 🔍 Issue Type Distribution")
            type_series = pd.Series([f.issue_type for f in findings])
            type_counts = type_series.value_counts().reset_index()
            type_counts.columns = ["Issue Type", "Count"]
            
            bar = alt.Chart(type_counts).mark_bar().encode(
                x=alt.X('Count:Q', title='Count'),
                y=alt.Y('Issue Type:N', sort='-x', title='Issue Type'),
                tooltip=['Issue Type', 'Count']
            )
            text = bar.mark_text(align='left', baseline='middle', dx=3).encode(
                text='Count:Q'
            )
            type_chart = (bar + text).properties(height=max(120, len(type_counts) * 25))
            st.altair_chart(type_chart, use_container_width=True)
            
            # Column Specific Visualization
            st.markdown("---")
            st.markdown("#### 🎯 Column-Level Quality Deep Dive")
            selected_col = st.selectbox("Select a column to analyze:", st.session_state.df.columns.tolist(), key="visual_select_col")
            
            # Find all discrepancies affecting this column
            col_findings = [f for f in findings if f.column == selected_col]
            
            # Calculate affected rows for this column
            affected_rows_indices = set()
            col_issue_counts = {}
            for f in col_findings:
                affected_rows_indices.update(f.row_indices)
                col_issue_counts[f.issue_type] = col_issue_counts.get(f.issue_type, 0) + len(f.row_indices)
            
            total_rows = len(st.session_state.df)
            num_affected = len(affected_rows_indices)
            num_clean = total_rows - num_affected
            clean_pct = (num_clean / total_rows) * 100
            
            # Columns for column-specific stats
            cc1, cc2 = st.columns([1, 2])
            with cc1:
                st.markdown(f"**Column Statistics:** `{selected_col}`")
                st.metric("Total Rows", total_rows)
                st.metric("Clean Rows", num_clean, delta=f"{clean_pct:.1f}%")
                st.metric("Discrepant Rows", num_affected, delta=f"-{(num_affected/total_rows)*100:.1f}%", delta_color="inverse")
            
            with cc2:
                st.markdown("**Clean vs Discrepant Rows**")
                ratio_df = pd.DataFrame({
                    "Status": ["Clean Rows", "Discrepant Rows"],
                    "Rows": [num_clean, num_affected]
                })
                
                bar = alt.Chart(ratio_df).mark_bar().encode(
                    x=alt.X('Rows:Q', title='Rows'),
                    y=alt.Y('Status:N', sort='-x', title='Status'),
                    color=alt.Color('Status:N', scale=alt.Scale(domain=["Clean Rows", "Discrepant Rows"], range=["#00cc96", "#ff4b4b"]), legend=None),
                    tooltip=['Status', 'Rows']
                )
                text = bar.mark_text(align='left', baseline='middle', dx=3).encode(
                    text='Rows:Q'
                )
                ratio_chart = (bar + text).properties(height=120)
                st.altair_chart(ratio_chart, use_container_width=True)
            
            # Show issue breakdown in this column
            if col_findings:
                st.markdown(f"**Discrepancies breakdown for `{selected_col}`:**")
                col_breakdown_df = pd.DataFrame({
                    "Issue Type": list(col_issue_counts.keys()),
                    "Rows Affected": list(col_issue_counts.values())
                })
                col_breakdown_df = col_breakdown_df.sort_values(by="Rows Affected", ascending=False)
                
                bar = alt.Chart(col_breakdown_df).mark_bar().encode(
                    x=alt.X('Rows Affected:Q', title='Rows Affected'),
                    y=alt.Y('Issue Type:N', sort='-x', title='Issue Type'),
                    tooltip=['Issue Type', 'Rows Affected']
                )
                text = bar.mark_text(align='left', baseline='middle', dx=3).encode(
                    text='Rows Affected:Q'
                )
                col_breakdown_chart = (bar + text).properties(height=max(120, len(col_breakdown_df) * 25))
                st.altair_chart(col_breakdown_chart, use_container_width=True)
            else:
                st.success(f"✨ Column `{selected_col}` is 100% clean! No discrepancies detected.")

def render_documentation():
    st.markdown("### 📚 System Documentation & Methodology")
    st.write("Detailed explanation of quality score formulas, criticality ratings, and agent algorithms.")
    
    doc_sec_a, doc_sec_b = st.tabs(["🧮 Score Calculation", "🚨 Severity & Definitions"])
    
    with doc_sec_a:
        st.markdown("#### 🧮 Data Quality Score Formula")
        st.write("The overall Data Quality Score is calculated out of 100 using a penalty-deduction model:")
        st.latex(r"\text{Quality Score} = 100 - (\text{P}_{\text{missing}} + \text{P}_{\text{duplicate}} + \text{P}_{\text{format}} + \text{P}_{\text{outlier}} + \text{P}_{\text{criticality}})")
        
        st.markdown("**Penalty Breakdown:**")
        st.markdown("""
        | Penalty Class | Max Deduction | Calculation Method |
        | :--- | :--- | :--- |
        | **Missing Values ($P_{\text{missing}}$)** | 15 Points | Proportional to the % of affected rows containing missing values. |
        | **Duplicates ($P_{\text{duplicate}}$)** | 15 Points | Proportional to the % of duplicate rows (exact & near-duplicates). |
        | **Format Inconsistency ($P_{\text{format}}$)** | 15 Points | Proportional to the % of rows deviating from dominant column formats. |
        | **Outliers & Anomalies ($P_{\text{outlier}}$)** | 15 Points | Proportional to the % of rows flagged as out-of-range or outliers. |
        | **Criticality ($P_{\text{criticality}}$)** | 40 Points | Deducts **4.0 points** for each High Criticality issue and **1.5 points** for each Medium Criticality issue. |
        """)
        
    with doc_sec_b:
        st.markdown("#### 🚨 Issue Criticality Classification")
        st.markdown("""
        | Criticality Level | Description / Severity | Example Issues |
        | :--- | :--- | :--- |
        | 🔴 **High** | Severe schema or integrity violations. Values cannot be cast or violate hard logical constraints. | Wrong Data Type, Clear Out-of-Range, Missing value levels $>30\%$. |
        | 🟡 **Medium** | Format deviations or statistical anomalies that affect analysis and modeling. | Format Inconsistency, Duplicate Records, Univariate Outliers ($Z\text{-score} > 3.0$). |
        | 🔵 **Low** | Cosmetic or presentation formatting anomalies that do not break parsing. | Whitespace & Encoding, Capitalization Variant Collisions (Casing). |
        | 🟣 **Requires Review** | Edge cases or candidate issues that require human/AI context to verify. | Near-Duplicate Record Candidates, Borderline Out-of-Range ($Z$-score $2.5$ to $3.5$). |
        """)
        
    st.markdown("---")
    st.markdown("#### 📁 Supported Issue Types & Remediation")
    
    with st.expander("1. ⚪ Missing / Null Values"):
        st.markdown("""
        * **Definition**: Empty cells, blank spaces, or common placeholder strings (like `"N/A"`, `"-"`, `"null"`, `"NaN"`).
        * **Detection Method**: Heuristic scanning for empty string matches and standard pandas null evaluations.
        * **Example**: An address field containing the string `"-"` or a numerical column containing `NaN`.
        * **Remediation**: Populate using standard default values, impute using statistical averages/medians, or drop rows if critical.
        """)
        
    with st.expander("2. 🔤 Wrong Data Type"):
        st.markdown("""
        * **Definition**: Column contains values that do not match the dominant inferred datatype of the column.
        * **Detection Method**: Infers majority column type (Integer, Decimal, Datetime, Boolean) using a $\ge 50\%$ majority vote, then flags values that fail to cast to that target type.
        * **Example**: A numeric age column containing the string `"twenty-five"`.
        * **Remediation**: Correct manual transcription errors or cast values to the appropriate standard type.
        """)
        
    with st.expander("3. 👥 Duplicate Records"):
        st.markdown("""
        * **Definition**: Complete duplicate rows existing across all columns of the dataset.
        * **Detection Method**: Strict row hashing and matching.
        * **Example**: Two identical invoice records with identical transaction IDs, timestamps, and amounts.
        * **Remediation**: De-duplicate the dataset by keeping the first occurrence.
        """)
        
    with st.expander("4. 👥 Near-Duplicate Candidates"):
        st.markdown("""
        * **Definition**: Multiple records that are extremely similar but have minor discrepancies (like typos in names or addresses).
        * **Detection Method**: Sorted adjacent comparison using `rapidfuzz.fuzz.token_sort_ratio` to compute token similarity.
        * **Example**: `"John Smith, Mumbai"` vs `"John Smith, Mumba"` (similarity $>85\%$).
        * **Remediation**: Investigate manually or call an LLM to determine the authoritative record, merging spelling variations.
        """)
        
    with st.expander("5. 🔣 Format Inconsistency"):
        st.markdown("""
        * **Definition**: A column contains values written in multiple differing format templates.
        * **Detection Method**: Converts strings to collapsed pattern templates (e.g. alphanumeric collapsed to `a` or `9`). Flags values that deviate from the dominant pattern ($\ge 50\%$ majority).
        * **Example**: Dates written as `12/01/2024` mixed with dates written as `2024-01-12`.
        * **Remediation**: Apply a standard parser (like datetime parsing with standard formats) to convert all rows to a unified format.
        """)
        
    with st.expander("6. 🌌 Whitespace & Encoding"):
        st.markdown("""
        * **Definition**: Invisible formatting issues like leading/trailing spaces, multiple spaces, or mojibake (corrupted characters).
        * **Detection Method**: Regular expression scans for non-standard character spreads or double spaces, and Latin-1 decoding validation.
        * **Example**: A city column containing `" Delhi "` or text containing garbled bytes like `Ã©`.
        * **Remediation**: Run a clean trim/strip function on string values and transcode character encodings.
        """)
        
    with st.expander("7. 📉 Out-of-Range Values"):
        st.markdown("""
        * **Definition**: Values that lie outside logical boundaries or configured bounds.
        * **Detection Method**: Cross-references against hard-coded constraints (e.g. Month 1-12) or custom rules set in the sidebar.
        * **Example**: An age column containing `312` or a month containing `-1`.
        * **Remediation**: Correct data input errors.
        """)
        
    with st.expander("8. 📈 Statistical Outliers (Deactivated)"):
        st.markdown("""
        * **Definition**: Univariate extreme values in a numerical column.
        * **Detection Method**: Combines standard box-plot Interquartile Range ($Q1 - 1.5 \times IQR$) and standard Z-score evaluations ($Z\text{-score} > 3.0$). (Note: Currently deactivated).
        * **Example**: A salary of `$250,000` when the mean is `$45,000` with a standard deviation of `$10,000`.
        * **Remediation**: Verify if these are genuine transactions/extremes or errors.
        """)
        
    with st.expander("9. 🤖 Multivariate Anomalies (Deactivated)"):
        st.markdown("""
        * **Definition**: Rows whose combination of values across multiple numeric columns is highly unusual, even if individual column values are normal.
        * **Detection Method**: Fits an unsupervised **Isolation Forest** model to find anomalies in multi-dimensional space. (Note: Currently deactivated).
        * **Example**: `Age = 12` and `Salary = $150,000`.
        * **Remediation**: Review the column-to-column relationship to check for logic flaws.
        """)
        
    st.markdown("---")
    st.markdown("#### ⚙️ Detection Algorithm Summary")
    st.markdown("""
    | Issue Type | Primary Detection Algorithm | Action Type |
    | :--- | :--- | :--- |
    | **Whitespace & Casing** | Regex & Case Variant Collisions | 🟢 Auto-Fixable |
    | **Format Inconsistency** | Character collapsing & Template majority voting ($\ge 50\%$) | 🟡 Deterministic |
    | **Out-of-Range** | Logical range boundaries & Tolerance buffers | 🔴 Confirmed / 🟣 Review |
    | **Statistical Outlier** | Standard Z-Score & Interquartile Range (IQR) (Deactivated) | 🟣 Requires Review |
    | **Multivariate Anomaly** | Isolation Forest (contamination = $2\%$) (Deactivated) | 🟣 Requires Review |
    """)

def render_more_tab():
    if not st.session_state.audit_run:
        st.info("Please click 'Run Quality Audit' in the sidebar to view further details.")
    else:
        more_option = st.selectbox(
            "Select Section to View:",
            ["🔍 Quality Audit Findings", "📈 Visualization", "📚 Documentation"],
            key="more_tabs_select"
        )
        
        if more_option == "🔍 Quality Audit Findings":
            render_quality_audit_findings()
        elif more_option == "📈 Visualization":
            render_visualization()
        elif more_option == "📚 Documentation":
            render_documentation()
