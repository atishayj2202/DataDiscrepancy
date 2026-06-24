import streamlit as st
import pandas as pd
import numpy as np
import io
import time
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
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
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
    # Tabs
    tab_profile, tab_audit, tab_review = st.tabs([
        "📊 Dataset Profiler", 
        "🔍 Quality Audit Findings", 
        "🕵️‍♂️ Flagged for Review (No-AI)"
    ])
    
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
                    filter_col = st.selectbox("Filter by Column", ["All"] + list(set(f.column for f in findings)))
                with fc2:
                    filter_type = st.selectbox("Filter by Issue Type", ["All"] + list(set(f.issue_type for f in findings)))
                with fc3:
                    filter_crit = st.selectbox("Filter by Criticality", ["All", "High", "Medium", "Low"])
                
                # Apply filter
                filtered_findings = findings
                if filter_col != "All":
                    filtered_findings = [f for f in filtered_findings if f.column == filter_col]
                if filter_type != "All":
                    filtered_findings = [f for f in filtered_findings if f.issue_type == filter_type]
                if filter_crit != "All":
                    filtered_findings = [f for f in filtered_findings if f.criticality == filter_crit]
                
                st.markdown(f"### 📋 Discrepancy Report ({len(filtered_findings)} issues filtered)")
                
                # Render table with custom badges
                # Streamlit dataframe doesn't render raw HTML well unless we use markdown columns or a structured table.
                # Let's present it as a neat interactive DataFrame or build a table representation.
                table_rows = []
                for f in filtered_findings:
                    review_status = "🟣 Needs Review (No AI)" if f.review_needed else "🟢 Deterministic"
                    table_rows.append({
                        "Column": f.column,
                        "Issue Type": f.issue_type,
                        "Criticality": f.criticality,
                        "Rows Affected": len(f.row_indices),
                        "Example Value": str(f.example_value),
                        "Remediation / Interpretation": f.interpretation,
                        "Review Status": review_status
                    })
                
                if table_rows:
                    findings_df = pd.DataFrame(table_rows)
                    st.dataframe(
                        findings_df, 
                        width="stretch", 
                        hide_index=True,
                        column_config={
                            "Rows Affected": st.column_config.NumberColumn(format="%d"),
                        }
                    )
                    
                    # Highlight detail drawer / inspector
                    st.markdown("### 🔎 Row-Level Inspector")
                    selected_issue_idx = st.selectbox("Select an issue row to inspect affected rows:", range(len(filtered_findings)), format_func=lambda i: f"#{i+1}: {filtered_findings[i].column} - {filtered_findings[i].issue_type}")
                    
                    selected_issue = filtered_findings[selected_issue_idx]
                    
                    st.markdown(f"**Issue Description:** {selected_issue.interpretation}")
                    if selected_issue.review_needed:
                        st.warning(f"⚠️ **Review Notes:** {selected_issue.review_notes}")
                        
                    st.markdown(f"Showing rows affected (Indices: `{selected_issue.row_indices[:20]}`" + (f" + {len(selected_issue.row_indices)-20} more" if len(selected_issue.row_indices) > 20 else "") + "):")
                    st.dataframe(st.session_state.df.loc[selected_issue.row_indices].head(50).astype(str), width="stretch")

    # --- Tab 3: Flagged for Review (No-AI) ---
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

