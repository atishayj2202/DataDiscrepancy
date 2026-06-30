import streamlit as st
import pandas as pd
import numpy as np
import io
import time
import altair as alt
from typing import Dict, List, Tuple, Any

from src.profiler import profile_dataset
from src.agents import (
    MissingValueAgent,
    WrongDataTypeAgent,
    DuplicateRecordsAgent,
    FormatInconsistencyAgent,
    OutOfRangeAgent,
    WhitespaceEncodingAgent,
    InconsistentCasingAgent,
    StatisticalOutliersAgent,
    Discrepancy
)

# Page configuration
st.set_page_config(
    page_title="Data Quality & Discrepancy Detection",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Helper functions for calculations and visualizations
def calculate_quality_score(df, findings) -> Tuple[int, str, Dict[str, float]]:
    # Calculate row count and total cells
    total_rows = len(df)
    
    # Initialize counts of affected rows
    missing_rows = set()
    duplicate_rows = set()
    format_rows = set()
    outlier_rows = set()
    
    high_count = 0
    med_count = 0
    
    for f in findings:
        if f.issue_type == "Missing Value":
            missing_rows.update(f.row_indices)
        elif "Duplicate" in f.issue_type:
            duplicate_rows.update(f.row_indices)
        elif f.issue_type == "Format Inconsistency":
            format_rows.update(f.row_indices)
        elif "Outlier" in f.issue_type or "Anomaly" in f.issue_type or "Range" in f.issue_type:
            outlier_rows.update(f.row_indices)
            
        if f.criticality == "High":
            high_count += 1
        elif f.criticality == "Medium":
            med_count += 1
            
    # Penalties based on percentages of rows affected
    p_missing = (len(missing_rows) / total_rows) * 15 if total_rows > 0 else 0
    p_duplicate = (len(duplicate_rows) / total_rows) * 15 if total_rows > 0 else 0
    p_format = (len(format_rows) / total_rows) * 15 if total_rows > 0 else 0
    p_outlier = (len(outlier_rows) / total_rows) * 15 if total_rows > 0 else 0
    
    # Criticality penalties
    p_criticality = (high_count * 4.0) + (med_count * 1.5)
    
    # Cap individual penalties
    p_missing = min(p_missing, 15.0)
    p_duplicate = min(p_duplicate, 15.0)
    p_format = min(p_format, 15.0)
    p_outlier = min(p_outlier, 15.0)
    p_criticality = min(p_criticality, 40.0)
    
    raw_score = 100.0 - (p_missing + p_duplicate + p_format + p_outlier + p_criticality)
    score = max(0, min(100, int(raw_score)))
    
    # Rating
    if score >= 90:
        rating = "EXCELLENT"
    elif score >= 75:
        rating = "GOOD"
    elif score >= 50:
        rating = "MODERATE"
    else:
        rating = "POOR"
        
    penalties = {
        "missing": p_missing,
        "duplicate": p_duplicate,
        "format": p_format,
        "outlier": p_outlier,
        "criticality": p_criticality
    }
    
    return score, rating, penalties

def kpi_card(title, value, subtitle, border_color="#29b5e8"):
    st.markdown(f"""
    <div class='glass-card' style='border-left: 5px solid {border_color}; padding: 15px; margin: 5px 0;'>
        <p style='margin: 0; font-size: 0.8rem; color: #888888; font-weight: 500; text-transform: uppercase;'>{title}</p>
        <h4 style='margin: 6px 0; font-family: Space Grotesk, sans-serif; font-size: 1.3rem; font-weight: 700;'>{value}</h4>
        <p style='margin: 0; font-size: 0.75rem; color: #666666;'>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

def render_mini_donut(data_dict, title):
    df_chart = pd.DataFrame({
        "Category": list(data_dict.keys()),
        "Rows": list(data_dict.values())
    })
    # Sort descending
    df_chart = df_chart.sort_values(by="Rows", ascending=False)
    chart = alt.Chart(df_chart).mark_arc(innerRadius=20, outerRadius=35).encode(
        theta=alt.Theta(field="Rows", type="quantitative"),
        color=alt.Color(field="Category", type="nominal", legend=alt.Legend(title=None, orient="right", labelFontSize=8)),
        tooltip=["Category", "Rows"]
    ).properties(
        width=180,
        height=80
    )
    return chart

def render_audit_donut(data_dict, title):
    df_chart = pd.DataFrame({
        "Category": list(data_dict.keys()),
        "Rows": list(data_dict.values())
    })
    # Sort descending
    df_chart = df_chart.sort_values(by="Rows", ascending=False)
    total = df_chart["Rows"].sum()
    df_chart["Percentage"] = (df_chart["Rows"] / total * 100).round(1) if total > 0 else 0
    df_chart["Label"] = df_chart["Category"] + " (" + df_chart["Percentage"].astype(str) + "%)"
    
    chart = alt.Chart(df_chart).mark_arc(innerRadius=35, outerRadius=55).encode(
        theta=alt.Theta(field="Rows", type="quantitative"),
        color=alt.Color(field="Label", type="nominal", legend=alt.Legend(title=title, orient="right", labelFontSize=10)),
        tooltip=["Category", "Rows", "Percentage"]
    ).properties(
        width=320,
        height=150
    )
    return chart

# Premium Custom CSS Injection
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Space+Grotesk:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .gradient-text {
        background: linear-gradient(135deg, #FF4B4B, #FF8F8F, #4A90E2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
    }
    
    .glass-card {
        background: rgba(128, 128, 128, 0.08);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .glass-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
    }
    
    .metric-badge {
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    .criticality-high {
        background-color: rgba(255, 75, 75, 0.15);
        color: #FF4B4B;
        border: 1px solid rgba(255, 75, 75, 0.3);
    }
    .criticality-medium {
        background-color: rgba(245, 166, 35, 0.15);
        color: #F5A623;
        border: 1px solid rgba(245, 166, 35, 0.3);
    }
    .criticality-low {
        background-color: rgba(74, 144, 226, 0.15);
        color: #4A90E2;
        border: 1px solid rgba(74, 144, 226, 0.3);
    }
    
    .status-badge {
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    .status-review {
        background-color: rgba(144, 19, 254, 0.15);
        color: #9013FE;
        border: 1px solid rgba(144, 19, 254, 0.3);
    }
    .status-det {
        background-color: rgba(80, 227, 194, 0.15);
        color: #50E3C2;
        border: 1px solid rgba(80, 227, 194, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session States
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None
if 'df' not in st.session_state:
    st.session_state.df = None
if 'profile' not in st.session_state:
    st.session_state.profile = None
if 'discrepancies' not in st.session_state:
    st.session_state.discrepancies = []
if 'audit_run' not in st.session_state:
    st.session_state.audit_run = False
if 'custom_limits' not in st.session_state:
    st.session_state.custom_limits = {}
if 'resolved_near_duplicates' not in st.session_state:
    st.session_state.resolved_near_duplicates = {}  # pair_key -> authoritative_idx
if 'resolved_borderline' not in st.session_state:
    st.session_state.resolved_borderline = {}  # (col, idx) -> "Valid" or "Error"

# App Header
st.markdown("<h1 class='gradient-text' style='margin-bottom:5px;'>🔍 Generalised Data Quality & Discrepancy Detection</h1>", unsafe_allow_html=True)
st.markdown("<p style='font-size: 1.1rem; color: #888; margin-top:0px; margin-bottom: 25px;'>Modular, rule-based data inspection engine operating locally without API budget overhead.</p>", unsafe_allow_html=True)

# Sidebar - File Upload and Settings
with st.sidebar:
    st.markdown("### 📤 Upload Dataset")
    uploaded_file = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx", "xls"])
    
    if uploaded_file is not None and uploaded_file != st.session_state.uploaded_file:
        st.session_state.uploaded_file = uploaded_file
        # Reset analysis state
        st.session_state.audit_run = False
        st.session_state.discrepancies = []
        st.session_state.resolved_near_duplicates = {}
        st.session_state.resolved_borderline = {}
        
        # Load file
        try:
            file_extension = uploaded_file.name.split('.')[-1]
            if file_extension in ['xlsx', 'xls']:
                st.session_state.df = pd.read_excel(uploaded_file)
            else:
                st.session_state.df = pd.read_csv(uploaded_file)
            # Run profile
            st.session_state.profile = profile_dataset(st.session_state.df)
            st.success(f"Successfully loaded: {uploaded_file.name}")
        except Exception as e:
            st.error(f"Error loading file: {e}")
            st.session_state.df = None
            st.session_state.profile = None

    if st.session_state.df is not None:
        st.markdown("---")
        st.markdown("### ⚙️ Engine Settings")
        
        # Duplicate records threshold
        sim_threshold = st.slider("Fuzzy duplicate similarity threshold (%)", 70, 100, 85, help="Minimum percentage similarity required to flag rows as near-duplicates.")
        
        # Select agents to run
        st.markdown("#### Active Quality Agents")
        agents_enabled = {
            "missing_value": st.checkbox("Missing / Null Values", value=True),
            "wrong_type": st.checkbox("Wrong Data Type", value=True),
            "duplicate": st.checkbox("Duplicate Records", value=True),
            "format_inconsistency": st.checkbox("Format Inconsistency", value=True),
            "out_of_range": st.checkbox("Out-of-Range Values", value=True),
            "whitespace": st.checkbox("Whitespace & Encoding", value=True),
            "casing": st.checkbox("Inconsistent Casing", value=True),
            "outliers": st.checkbox("Statistical Outliers", value=True)
        }
        
        # Custom limits config helper
        st.markdown("#### Config-Defined Limits (Out of Range)")
        numeric_columns = [col for col in st.session_state.df.columns if pd.api.types.is_numeric_dtype(st.session_state.df[col])]
        
        if numeric_columns:
            selected_limit_col = st.selectbox("Select column to apply limits", ["None"] + numeric_columns)
            if selected_limit_col != "None":
                col_min = float(st.session_state.df[selected_limit_col].min())
                col_max = float(st.session_state.df[selected_limit_col].max())
                
                # Input custom limits
                lim_min = st.number_input("Min Logical Bound", value=col_min, key=f"lim_min_{selected_limit_col}")
                lim_max = st.number_input("Max Logical Bound", value=col_max, key=f"lim_max_{selected_limit_col}")
                
                if st.button("Apply Logical Limits"):
                    st.session_state.custom_limits[selected_limit_col] = (lim_min, lim_max)
                    st.toast(f"Applied limits [{lim_min}, {lim_max}] to {selected_limit_col}!")
            
            # Show active custom limits
            if st.session_state.custom_limits:
                st.markdown("**Active Limits:**")
                for k, v in st.session_state.custom_limits.items():
                    st.markdown(f"- `{k}`: {v[0]} to {v[1]} " + f"<span style='cursor:pointer; color:#FF4B4B;' onclick=''>❌</span>", unsafe_allow_html=True)
                    # Simple clear button
                    if st.button(f"Clear {k} limits"):
                        del st.session_state.custom_limits[k]
                        st.rerun()

        st.markdown("---")
        # Run Audit Button
        if st.button("🚀 Run Quality Audit", width="stretch"):
            st.session_state.discrepancies = []
            
            df = st.session_state.df
            
            # Instantiate agents
            agents = []
            if agents_enabled["missing_value"]:
                agents.append(MissingValueAgent())
            if agents_enabled["wrong_type"]:
                agents.append(WrongDataTypeAgent())
            if agents_enabled["duplicate"]:
                agents.append(DuplicateRecordsAgent())
            if agents_enabled["format_inconsistency"]:
                agents.append(FormatInconsistencyAgent())
            if agents_enabled["out_of_range"]:
                agents.append(OutOfRangeAgent())
            if agents_enabled["whitespace"]:
                agents.append(WhitespaceEncodingAgent())
            if agents_enabled["casing"]:
                agents.append(InconsistentCasingAgent())
            if agents_enabled["outliers"]:
                agents.append(StatisticalOutliersAgent())
            
            findings: List[Discrepancy] = []
            
            # Status display block for progress
            status_container = st.container()
            with status_container:
                st.markdown("### ⚙️ Audit Progress")
                progress_bar = st.progress(0.0)
                status_list_placeholder = st.empty()
            
            completed_messages = []
            total_agents = len(agents)
            
            for idx, agent in enumerate(agents):
                # Update status for currently running agent
                status_list_placeholder.markdown(
                    "\n".join(completed_messages) + 
                    f"\n\n⏳ **Running:** `{agent.name}`..."
                )
                
                # Execute agent
                start_time = time.time()
                if isinstance(agent, DuplicateRecordsAgent):
                    res = agent.detect(df, similarity_threshold=sim_threshold)
                elif isinstance(agent, OutOfRangeAgent):
                    res = agent.detect(df, custom_limits=st.session_state.custom_limits)
                else:
                    res = agent.detect(df)
                
                duration = time.time() - start_time
                findings.extend(res)
                
                # Update progress bar
                progress_bar.progress((idx + 1) / total_agents)
                
                # Record completion status
                completed_messages.append(f"✅ `{agent.name}` completed in {duration:.2f}s (found {len(res)} issues)")
                
                # Small sleep for better visual experience of agent pipelines running
                time.sleep(0.1)

            # Final status update
            status_list_placeholder.markdown(
                "\n".join(completed_messages) + 
                "\n\n🎉 **All agents completed successfully!**"
            )
            
            # Rank findings by criticality (High first) then by rows affected (descending)
            def get_crit_val(crit: str) -> int:
                crit_map = {"High": 3, "Medium": 2, "Low": 1}
                return crit_map.get(crit, 0)
                
            findings.sort(key=lambda x: (get_crit_val(x.criticality), len(x.row_indices)), reverse=True)
            
            st.session_state.discrepancies = findings
            st.session_state.audit_run = True
            st.toast("Audit complete!", icon="✅")

# Main Panel layout
if st.session_state.df is None:
    # Landing page state
    st.markdown("""
    <div class='glass-card' style='text-align: center; padding: 40px; margin-top: 20px;'>
        <h2 style='font-family: Space Grotesk, sans-serif;'>Welcome to the Data Discrepancy Detection System</h2>
        <p style='color: #888; max-width: 600px; margin: 15px auto;'>
            Upload any CSV or Excel file in the sidebar to begin. 
            The system will profile your dataset, let you configure rule bounds, 
            and execute 8 deterministic/statistical quality agents to flag issues for human review.
        </p>
    </div>
    """, unsafe_allow_html=True)
else:
    # Define stable tabs visible at all times in the requested order
    tab_profile, tab_summary, tab_row_inspector, tab_audit, tab_visual, tab_review, tab_doc = st.tabs([
        "📊 Dataset Profiler",
        "📊 Summary",
        "🔍 Row Inspector",
        "🔍 Quality Audit Findings", 
        "📈 Visualization",
        "🕵️‍♂️ Flagged for Review (No-AI)",
        "📚 Documentation"
    ])
        
    # --- Tab: Summary ---
    with tab_summary:
        if not st.session_state.audit_run:
            st.info("Please click 'Run Quality Audit' in the sidebar to view the quality summary dashboard.")
        else:
            df = st.session_state.df
            findings = st.session_state.discrepancies
            
            # 1. Calculate score & rating & penalties
            score, rating, penalties = calculate_quality_score(df, findings)
            
            # Calculate impacted rows
            total_rows = len(df)
            all_affected_rows = set()
            missing_rows = set()
            duplicate_rows = set()
            format_rows = set()
            outlier_rows = set()
            
            high_count = sum(1 for f in findings if f.criticality == "High")
            med_count = sum(1 for f in findings if f.criticality == "Medium")
            low_count = sum(1 for f in findings if f.criticality == "Low")
            review_count = sum(1 for f in findings if f.review_needed)
            
            manual_review_rows = set()
            auto_fixable_rows = set()
            
            for f in findings:
                all_affected_rows.update(f.row_indices)
                if f.issue_type == "Missing Value":
                    missing_rows.update(f.row_indices)
                elif "Duplicate" in f.issue_type:
                    duplicate_rows.update(f.row_indices)
                elif f.issue_type == "Format Inconsistency":
                    format_rows.update(f.row_indices)
                elif "Outlier" in f.issue_type or "Anomaly" in f.issue_type or "Range" in f.issue_type:
                    outlier_rows.update(f.row_indices)
                    
                if f.review_needed:
                    manual_review_rows.update(f.row_indices)
                
                # Auto fixable: Whitespace, casing, and exact duplicates
                if f.issue_type in ["Whitespace & Encoding", "Inconsistent Casing"] or ("Duplicate" in f.issue_type and not f.review_needed):
                    auto_fixable_rows.update(f.row_indices)
            
            impacted_pct = (len(all_affected_rows) / total_rows * 100) if total_rows > 0 else 0
            auto_fix_pct = (len(auto_fixable_rows) / len(all_affected_rows) * 100) if all_affected_rows else 100
            
            # Trust mapping
            if score >= 90:
                trust = "Production Ready"
                trust_color = "#00cc96"
            elif score >= 75:
                trust = "High Confidence"
                trust_color = "#29b5e8"
            elif score >= 60:
                trust = "Moderate Confidence"
                trust_color = "#ffaa00"
            elif score >= 40:
                trust = "Low Confidence"
                trust_color = "#ff6b00"
            else:
                trust = "Not Suitable for ML"
                trust_color = "#ff4b4b"
                
            # Color for quality score
            if rating == "EXCELLENT":
                score_color = "#00cc96"
            elif rating == "GOOD":
                score_color = "#ffaa00"
            elif rating == "MODERATE":
                score_color = "#ff6b00"
            else:
                score_color = "#ff4b4b"
                
            # SECTION A: KPI Cards
            st.markdown("### 📊 Dataset Quality Overview")
            
            kpi_cols = st.columns(6)
            with kpi_cols[0]:
                kpi_card("Data Quality Score", f"{score} / 100", rating, score_color)
            with kpi_cols[1]:
                kpi_card("Rows Impacted", f"{impacted_pct:.1f}%", f"{len(all_affected_rows)} / {total_rows} rows", "#ff6b00")
            with kpi_cols[2]:
                kpi_card("Critical Issues", f"{high_count}", "Immediate Action" if high_count > 0 else "All Clear", "#ff4b4b" if high_count > 0 else "#00cc96")
            with kpi_cols[3]:
                kpi_card("Auto Fix Potential", f"{int(auto_fix_pct)}%", "Correctable Rows", "#00cc96")
            with kpi_cols[4]:
                kpi_card("Manual Review Required", f"{len(manual_review_rows)} Rows", "Human Action Needed", "#29b5e8")
            with kpi_cols[5]:
                kpi_card("Dataset Trust", trust, "Confidence Rating", trust_color)

            
            # Determine top columns and issues for summary
            col_counts = pd.Series([f.column for f in findings]).value_counts()
            top_col_str = f"'{col_counts.index[0]}'" if not col_counts.empty else "N/A"
            
            issue_type_counts = pd.Series([f.issue_type for f in findings]).value_counts()
            top_issue_str = f"'{issue_type_counts.index[0]}'" if not issue_type_counts.empty else "N/A"
            top_issue_pct = (issue_type_counts.iloc[0] / len(findings) * 100) if not issue_type_counts.empty else 0
            
            summary_bullets = [
                f"• Dataset quality score is <b>{score}/100</b> ({rating.capitalize()}).",
                f"• <b>{impacted_pct:.1f}%</b> of rows ({len(all_affected_rows)} rows) contain at least one quality discrepancy.",
                f"• Most column-specific discrepancies originate from column <b>{top_col_str}</b>.",
                f"• <b>{top_issue_str}</b> represents <b>{top_issue_pct:.1f}%</b> of all flagged discrepancies.",
                f"• <b>{int(auto_fix_pct)}%</b> of the rows with issues can be automatically corrected (formatting, whitespace, casing, exact duplicates).",
                f"• <b>{len(manual_review_rows)} rows</b> require manual investigation (borderline out-of-range, duplicate candidates, multivariate anomalies)."
            ]
            
            # Row with Executive Summary and Donut Chart
            r2_col1, r2_col2 = st.columns([3, 2])
            
            with r2_col1:
                st.markdown("### 📋 Executive Summary")
                st.markdown(f"""
                <div class='glass-card' style='padding: 20px; min-height: 380px; margin-bottom: 25px;'>
                    <p style='margin: 0 0 10px 0; font-size: 0.95rem; font-weight: 600; color: #888888;'>Key Insights:</p>
                    <div style='line-height: 1.6; font-size: 0.9rem;'>
                        {"<br>".join(summary_bullets)}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            with r2_col2:
                st.markdown("### 🍩 Issue Type Distribution")
                if len(findings) > 0:
                    type_series = pd.Series([f.issue_type for f in findings])
                    type_counts = type_series.value_counts().reset_index()
                    type_counts.columns = ["Issue Type", "Count"]
                    type_counts["Percentage"] = (type_counts["Count"] / type_counts["Count"].sum() * 100).round(1)
                    type_counts["Percentage Str"] = type_counts["Percentage"].astype(str) + "%"
                    type_counts_df = type_counts.copy()
                    
                    arc = alt.Chart(type_counts_df).mark_arc(innerRadius=60, outerRadius=90).encode(
                        theta=alt.Theta(field="Count", type="quantitative"),
                        color=alt.Color(field="Issue Type", type="nominal", legend=alt.Legend(orient="bottom", columns=2)),
                        tooltip=["Issue Type", "Count", "Percentage Str"]
                    )
                    
                    # Center text showing total issues count
                    total_issues = len(findings)
                    center_data = pd.DataFrame([{"text": f"{total_issues} Issues"}])
                    text = alt.Chart(center_data).mark_text(
                        align='center',
                        baseline='middle',
                        fontSize=14,
                        fontWeight='bold'
                    ).encode(
                        text='text:N'
                    )
                    
                    donut_chart = (arc + text).properties(
                        height=280
                    )
                    st.altair_chart(donut_chart, use_container_width=True)
                else:
                    st.info("No issues found to show distribution.")
                    
            # SECTION C: Issue Heatmap (Full Width)
            st.markdown("### 🗺️ Column vs. Issue Heatmap")
            st.write("Identifies which columns suffer from which specific issue categories.")
            
            all_columns = df.columns.tolist()
            all_issue_types = list(set(f.issue_type for f in findings))
            
            if all_issue_types:
                grid_data = []
                for col in all_columns:
                    col_findings = [f for f in findings if f.column == col]
                    for issue_type in all_issue_types:
                        matching = [f for f in col_findings if f.issue_type == issue_type]
                        if matching:
                            rows_affected = len(matching[0].row_indices)
                            pct = (rows_affected / total_rows) * 100 if total_rows > 0 else 0
                        else:
                            rows_affected = 0
                            pct = 0.0
                            
                        grid_data.append({
                            "Column": col,
                            "Issue Type": issue_type,
                            "Rows Affected": rows_affected,
                            "Percentage Affected": f"{pct:.1f}%"
                        })
                        
                heatmap_df = pd.DataFrame(grid_data)
                
                # Diverging red-to-green (reversed 'redyellowgreen' so green is clean/0 and red is high)
                heatmap_chart = alt.Chart(heatmap_df).mark_rect().encode(
                    x=alt.X('Issue Type:N', title='Issue Category', axis=alt.Axis(labelAngle=-45)),
                    y=alt.Y('Column:N', title='Dataset Column'),
                    color=alt.Color('Rows Affected:Q', title='Rows Affected', scale=alt.Scale(scheme='redyellowgreen', reverse=True)),
                    tooltip=['Column', 'Issue Type', 'Rows Affected', 'Percentage Affected']
                ).properties(
                    height=200 + (len(all_columns) * 15)
                )
                st.altair_chart(heatmap_chart, use_container_width=True)
            else:
                st.info("No issues detected to draw a heatmap.")
                
            # Row with Top Issues to Fix & Top Columns to Fix
            r3_col1, r3_col2 = st.columns(2)
            
            with r3_col1:
                # SECTION E: Top Issues to Fix
                st.markdown("### 🎯 Top Issues to Fix")
                st.write("Ranked by priority score (Criticality Weight × Rows Affected).")
                
                crit_weights = {"High": 3, "Medium": 2, "Low": 1}
                ranked_issues = []
                for f in findings:
                    weight = crit_weights.get(f.criticality, 1)
                    score_val = weight * len(f.row_indices)
                    ranked_issues.append({
                        "finding": f,
                        "priority_score": score_val
                    })
                
                ranked_issues.sort(key=lambda x: x["priority_score"], reverse=True)
                top_5_issues = ranked_issues[:5]
                
                if top_5_issues:
                    for item in top_5_issues:
                        f = item["finding"]
                        score_val = item["priority_score"]
                        crit_icon = "🔴" if f.criticality == "High" else "🟡" if f.criticality == "Medium" else "🔵"
                        st.markdown(f"""
                        <div class='glass-card' style='padding: 12px; margin: 8px 0; border-left: 4px solid {"#ff4b4b" if f.criticality == "High" else "#ffaa00" if f.criticality == "Medium" else "#29b5e8"};'>
                            <div style='display: flex; justify-content: space-between; align-items: center;'>
                                <span style='font-weight: 600; font-size: 0.9rem;'>{crit_icon} {f.column} - {f.issue_type}</span>
                                <span class='badge' style='background: rgba(255, 75, 75, 0.15); color: #ff4b4b; font-size: 0.75rem; padding: 2px 8px; border-radius: 4px;'>Score: {score_val}</span>
                            </div>
                            <p style='margin: 5px 0 0 0; font-size: 0.8rem; color: #888888;'>{len(f.row_indices)} rows affected • {f.criticality} Severity</p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.success("No issues to fix!")
                    
            with r3_col2:
                # SECTION F: Top Columns to Fix
                st.markdown("### 🏗️ Top Columns to Fix")
                st.write("Ranked by number of issue types + affected rows.")
                
                column_stats = {}
                for c in df.columns:
                    col_findings = [f for f in findings if f.column == c]
                    if col_findings:
                        num_types = len(col_findings)
                        affected_rows = set()
                        for f in col_findings:
                            affected_rows.update(f.row_indices)
                        num_affected = len(affected_rows)
                        metric = num_types + num_affected
                        column_stats[c] = {
                            "Column": c,
                            "Issue Types": num_types,
                            "Affected Rows": num_affected,
                            "Priority Metric": metric
                        }
                        
                top_cols = sorted(list(column_stats.values()), key=lambda x: x["Priority Metric"], reverse=True)
                top_cols_df = pd.DataFrame(top_cols).head(5)
                
                if not top_cols_df.empty:
                    col_chart = alt.Chart(top_cols_df).mark_bar().encode(
                        x=alt.X('Priority Metric:Q', title='Priority Metric (Issue Types + Affected Rows)'),
                        y=alt.Y('Column:N', sort='-x', title='Dataset Column'),
                        color=alt.Color('Priority Metric:Q', scale=alt.Scale(scheme='oranges'), legend=None),
                        tooltip=['Column', 'Issue Types', 'Affected Rows', 'Priority Metric']
                    ).properties(
                        height=200
                    )
                    st.altair_chart(col_chart, use_container_width=True)
                else:
                    st.success("All columns are completely clean!")

    # --- Tab 1: Dataset Profiler ---
    with tab_profile:
        summary = st.session_state.profile["summary"]
        cols_profile = st.session_state.profile["columns"]
        
        # Summary Row
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class='glass-card'>
                <p style='margin:0; font-size:0.9rem; color:#888;'>Total Rows</p>
                <h2 style='margin:5px 0 0 0; font-family:Space Grotesk;'>{summary['total_rows']:,}</h2>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class='glass-card'>
                <p style='margin:0; font-size:0.9rem; color:#888;'>Total Columns</p>
                <h2 style='margin:5px 0 0 0; font-family:Space Grotesk;'>{summary['total_columns']}</h2>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class='glass-card'>
                <p style='margin:0; font-size:0.9rem; color:#888;'>Estimated Memory Size</p>
                <h2 style='margin:5px 0 0 0; font-family:Space Grotesk;'>{summary['memory_usage']}</h2>
            </div>
            """, unsafe_allow_html=True)
            
        # Dataframe preview
        st.markdown("### 📋 Dataset Preview")
        st.dataframe(st.session_state.df.head(10).astype(str), width="stretch")
        
        # Column Profile Details Table
        st.markdown("### 🧬 Column Schema & Value Ranges")
        
        col_profile_data = []
        for c in cols_profile:
            col_profile_data.append({
                "Column Name": c["name"],
                "Simplified Type": c["simplified_type"],
                "Pandas Dtype": c["pandas_dtype"],
                "Missing Values %": f"{c['missing_pct']:.2f}% ({c['missing_count']})",
                "Cardinality (Unique)": c["cardinality"],
                "Min Value": c["min_value"],
                "Max Value": c["max_value"]
            })
        
        profile_df = pd.DataFrame(col_profile_data)
        st.dataframe(profile_df, width="stretch", hide_index=True)
        
        # Expanders for Top-N unique values
        st.markdown("### 🔝 Top 5 Value Distributions per Column")
        exp_cols = st.columns(3)
        for i, c in enumerate(cols_profile):
            with exp_cols[i % 3]:
                with st.expander(f"Distribution: {c['name']}"):
                    if not c["top_values"]:
                        st.write("No distinct values found or too sparse.")
                    else:
                        top_df = pd.DataFrame([
                            {"Value": k, "Count": v, "Percentage": f"{(v/summary['total_rows'])*100:.1f}%"}
                            for k, v in c["top_values"].items()
                        ])
                        st.dataframe(top_df, width="stretch", hide_index=True)

    # --- Tab 2: Quality Audit Findings ---
    with tab_audit:
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

    # --- Tab 3: Visualization ---
    with tab_visual:
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

    # --- Tab: Row Inspector ---
    with tab_row_inspector:
        if not st.session_state.audit_run:
            st.info("Please click 'Run Quality Audit' in the sidebar to inspect affected rows.")
        else:
            findings = st.session_state.discrepancies
            if not findings:
                st.success("🎉 No issues detected! Nothing to inspect.")
            else:
                st.markdown("### 🔎 Row-Level Inspector")
                st.write("Inspect the actual rows in the dataset affected by each quality issue.")
                
                # Issue selector dropdown
                selected_issue_idx = st.selectbox(
                    "Select an issue row to inspect:", 
                    range(len(findings)), 
                    format_func=lambda i: f"#{i+1}: {findings[i].column} - {findings[i].issue_type} ({len(findings[i].row_indices)} rows)",
                    key="row_inspector_select_issue"
                )
                
                selected_issue = findings[selected_issue_idx]
                
                # Issue Summary Card
                st.markdown(f"""
                <div class='glass-card' style='padding: 15px; margin-bottom: 20px; border-left: 5px solid {"#ff4b4b" if selected_issue.criticality == "High" else "#ffaa00" if selected_issue.criticality == "Medium" else "#29b5e8"};'>
                    <h4 style='margin: 0;'>{selected_issue.issue_type}</h4>
                    <p style='margin: 5px 0; font-size: 0.9rem; color: #888888;'>
                        <b>Column:</b> <code>{selected_issue.column}</code> | 
                        <b>Criticality:</b> <span style='color: {"#ff4b4b" if selected_issue.criticality == "High" else "#ffaa00" if selected_issue.criticality == "Medium" else "#29b5e8"}; font-weight: bold;'>{selected_issue.criticality}</span> | 
                        <b>Rows Affected:</b> {len(selected_issue.row_indices)}
                    </p>
                    <p style='margin: 10px 0 0 0; font-size: 0.85rem; line-height: 1.5; color: #666666;'>
                        <b>Description:</b> {selected_issue.interpretation}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
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

    # --- Tab: Documentation ---
    with tab_doc:
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
        
        # Accordion definitions
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
            
        with st.expander("8. 📈 Statistical Outliers"):
            st.markdown("""
            * **Definition**: Univariate extreme values in a numerical column.
            * **Detection Method**: Combines standard box-plot Interquartile Range ($Q1 - 1.5 \times IQR$) and standard Z-score evaluations ($Z\text{-score} > 3.0$).
            * **Example**: A salary of `$250,000` when the mean is `$45,000` with a standard deviation of `$10,000`.
            * **Remediation**: Verify if these are genuine transactions/extremes or errors.
            """)
            
        with st.expander("9. 🤖 Multivariate Anomalies"):
            st.markdown("""
            * **Definition**: Rows whose combination of values across multiple numeric columns is highly unusual, even if individual column values are normal.
            * **Detection Method**: Fits an unsupervised **Isolation Forest** model to find anomalies in multi-dimensional space.
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
        | **Statistical Outlier** | Standard Z-Score & Interquartile Range (IQR) | 🟣 Requires Review |
        | **Multivariate Anomaly** | Isolation Forest (contamination = $2\%$) | 🟣 Requires Review |
        | **Near-Duplicate** | Sorted-Adjacent RapidFuzz Token Match | 🟣 Requires Review |
        """)

    # --- Tab: Flagged for Review (No-AI) ---
    with tab_review:
        if not st.session_state.audit_run:
            st.info("Run Quality Audit first to discover issues requiring review.")
        else:
            review_findings = [f for f in st.session_state.discrepancies if f.review_needed]
            
            if not review_findings:
                st.success("✅ No issues require manual review in this dataset!")
            else:
                st.markdown("### 🕵️‍♂️ Flagged for Review (AI / Human Decision Needed)")
                st.info("Because AI connection is bypassed, the system flags borderline entries, outliers, or duplicate candidates. These require manual review to assess validity.")
                
                # Split review items by type
                near_dupe_findings = [f for f in review_findings if "Duplicate" in f.issue_type]
                borderline_findings = [f for f in review_findings if "Borderline" in f.issue_type]
                statistical_findings = [f for f in review_findings if "Multivariate" in f.issue_type or "Outlier" in f.issue_type]
                
                if near_dupe_findings:
                    st.markdown("#### 👥 Near-Duplicate Record Candidates")
                    for finding in near_dupe_findings:
                        indices = finding.row_indices
                        st.markdown(finding.interpretation)
                        # Display pairs
                        for i in range(0, len(indices), 2):
                            if i + 1 >= len(indices):
                                break
                            idx1 = indices[i]
                            idx2 = indices[i+1]
                            
                            st.markdown(f"**Duplicate Pair Candidate:** (Rows {idx1} and {idx2})")
                            st.dataframe(st.session_state.df.loc[[idx1, idx2]].astype(str), width="stretch")
                        st.markdown("---")

                if borderline_findings or statistical_findings:
                    st.markdown("#### 📈 Borderline Out-of-Range & Statistical Outliers")
                    
                    all_outlier_items = []
                    for f in borderline_findings + statistical_findings:
                        for row_idx in f.row_indices:
                            all_outlier_items.append((f.column, row_idx, f.issue_type, f.interpretation))
                            
                    if all_outlier_items:
                        st.write("The following borderline values or multivariate anomalies were flagged:")
                        
                        outlier_data = []
                        for col, row_idx, issue_type, interpretation in all_outlier_items:
                            val = st.session_state.df.at[row_idx, col] if col != "Table Level" else "Row Level"
                            outlier_data.append({
                                "Row Index": row_idx,
                                "Column": col,
                                "Value": val,
                                "Issue Type": issue_type,
                                "Details": interpretation
                            })
                        
                        st.dataframe(pd.DataFrame(outlier_data), width="stretch", hide_index=True)
