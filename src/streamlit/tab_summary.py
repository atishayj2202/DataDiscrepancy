import streamlit as st
import pandas as pd
from src.streamlit.kpi import kpi_card, calculate_quality_score

def render_summary():
    if not st.session_state.audit_run:
        st.info("Please click 'Run Quality Audit' in the sidebar to view the quality summary dashboard.")
    else:
        df = st.session_state.df
        findings = st.session_state.discrepancies
        total_rows = len(df)
        
        # 1. Calculate score & rating & penalties
        score, rating, penalties = calculate_quality_score(df, findings)
        
        # Collect unique row indices per severity level
        low_rows = set()
        med_rows = set()
        high_rows = set()
        
        for f in findings:
            if f.criticality == "Low":
                low_rows.update(f.row_indices)
            elif f.criticality == "Medium":
                med_rows.update(f.row_indices)
            elif f.criticality == "High":
                high_rows.update(f.row_indices)
        
        # Calculate percentages
        low_pct = (len(low_rows) / total_rows * 100) if total_rows > 0 else 0
        med_pct = (len(med_rows) / total_rows * 100) if total_rows > 0 else 0
        high_pct = (len(high_rows) / total_rows * 100) if total_rows > 0 else 0
        
        # Unique overall impacted rows
        all_affected_rows = set()
        for f in findings:
            all_affected_rows.update(f.row_indices)
        affected_cnt = len(all_affected_rows)
        affected_pct = (affected_cnt / total_rows * 100) if total_rows > 0 else 0
        
        # Color for quality score KPI
        if rating == "EXCELLENT":
            score_color = "#00cc96"
        elif rating == "GOOD":
            score_color = "#ffaa00"
        elif rating == "MODERATE":
            score_color = "#ff6b00"
        else:
            score_color = "#ff4b4b"
            
        # Render 5 KPI Cards
        st.markdown("### 📊 Dataset Quality Overview")
        kpi_cols = st.columns(5)
        with kpi_cols[0]:
            kpi_card("Quality Score", f"{score} / 100", rating, score_color)
        with kpi_cols[1]:
            kpi_card("Impacted Rows", f"{affected_pct:.1f}%", f"{affected_cnt} / {total_rows} rows", "#ff6b00" if affected_cnt > 0 else "#00cc96")
        with kpi_cols[2]:
            kpi_card("Rows with Low Critical Issues", f"{low_pct:.1f}%", f"{len(low_rows)} / {total_rows} rows", "#29b5e8")
        with kpi_cols[3]:
            kpi_card("Rows with Medium Critical Issues", f"{med_pct:.1f}%", f"{len(med_rows)} / {total_rows} rows", "#ffaa00")
        with kpi_cols[4]:
            kpi_card("Rows with High Critical Issues", f"{high_pct:.1f}%", f"{len(high_rows)} / {total_rows} rows", "#ff4b4b")
            
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
        
        summary_table_data = []
        crit_order = {"High": 3, "Medium": 2, "Low": 1, "Clean": 0}
        
        for cat_name, cat_findings in categories.items():
            if cat_findings:
                highest_crit = "Low"
                for f in cat_findings:
                    if crit_order.get(f.criticality, 1) > crit_order.get(highest_crit, 1):
                        highest_crit = f.criticality
                
                crit_badge = f"🔴 {highest_crit}" if highest_crit == "High" else f"🟡 {highest_crit}" if highest_crit == "Medium" else f"🔵 {highest_crit}"
                
                cat_rows = set()
                for f in cat_findings:
                    cat_rows.update(f.row_indices)
                
                cat_cnt = len(cat_rows)
                cat_pct = (cat_cnt / total_rows * 100) if total_rows > 0 else 0
                cat_str = f"{cat_pct:.1f}% ({cat_cnt} / {total_rows})"
            else:
                crit_badge = "🟢 Clean"
                cat_str = "0.0% (0 / {})".format(total_rows)
                
            summary_table_data.append({
                "Error Type": cat_name,
                "Impacted Rows": cat_str,
                "Criticality": crit_badge
            })
            
        # SECTION B: Summary Table
        st.markdown("### 📋 Data Quality Error Summary")
        st.write("Summary breakdown of key discrepancy error types detected across the dataset.")
        
        summary_df = pd.DataFrame(summary_table_data)
        st.dataframe(summary_df, width="stretch", hide_index=True)
        
        # SECTION C: Interactive Drill Down
        st.markdown("### 🔍 Column Drill Down")
        st.write("Select an error category below to identify the specific columns where this issue resides.")
        
        drill_down_categories = [k for k in categories.keys() if k not in ["Duplicate Rows", "Near to Duplicate Rows"]]
        
        selected_cat = st.selectbox(
            "Choose error type to inspect columns:",
            drill_down_categories,
            key="summary_drill_down_select"
        )
        
        if selected_cat:
            cat_findings = categories[selected_cat]
            if not cat_findings:
                st.success(f"✨ No issues detected for category: **{selected_cat}**.")
            else:
                drill_rows = []
                for f in cat_findings:
                    drill_rows.append({
                        "Column": f.column,
                        "Issue Type": f.issue_type,
                        "Criticality": f"🔴 {f.criticality}" if f.criticality == "High" else f"🟡 {f.criticality}" if f.criticality == "Medium" else f"🔵 {f.criticality}",
                        "Rows Affected": len(f.row_indices),
                        "Example Value": str(f.example_value),
                        "Details": f.interpretation
                    })
                st.dataframe(
                    pd.DataFrame(drill_rows),
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Rows Affected": st.column_config.NumberColumn(format="%d"),
                    }
                )
