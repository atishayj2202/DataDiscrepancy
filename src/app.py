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
    Discrepancy
)
from src.streamlit import (
    render_profiler,
    render_summary,
    render_row_inspector,
    render_casing_inspector,
    render_duplicates_inspector,
    render_more_tab
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
            "casing": st.checkbox("Inconsistent Casing", value=True)
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
            
            # Override criticalities based on the specified categories map
            for f in findings:
                if f.issue_type in ["Null Value", "Incomplete Records"]:
                    f.criticality = "Medium"
                elif f.issue_type == "Exact Duplicate Records":
                    f.criticality = "High"
                elif f.issue_type == "Near-Duplicate Records":
                    f.criticality = "Medium"
                elif f.issue_type == "Inconsistent Casing":
                    f.criticality = "Low"
                elif f.issue_type in ["Clear Out-of-Range", "Borderline Out-of-Range (Requires Review)", 
                                       "Ambiguous Statistical Outlier (Requires Review)", "Confirmed Statistical Outlier", 
                                       "Multivariate Anomaly (Requires Review)"]:
                    f.criticality = "High"
                elif f.issue_type in ["Wrong Data Type", "Format Inconsistency"]:
                    f.criticality = "Medium"
                elif f.issue_type == "Whitespace & Encoding":
                    f.criticality = "Medium"

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
    tab_profile, tab_summary, tab_row_inspector, tab_casing, tab_review, tab_more = st.tabs([
        "📊 Dataset Profiler",
        "📊 Summary",
        "🔍 Row Inspector",
        "🔤 Inconsistent Casing Inspector",
        "👯 Duplicate & Near-Duplicate Records Inspector",
        "➕ More ▾"
    ])

    # --- Tab: Dataset Profiler ---
    with tab_profile:
        render_profiler()

    # --- Tab: Summary ---
    with tab_summary:
        render_summary()

    # --- Tab: Row Inspector ---
    with tab_row_inspector:
        render_row_inspector()

    # --- Tab: Inconsistent Casing Inspector ---
    with tab_casing:
        render_casing_inspector()

    # --- Tab: Duplicate & Near-Duplicate Records Inspector ---
    with tab_review:
        render_duplicates_inspector()

    # --- Tab: More ▾ ---
    with tab_more:
        render_more_tab()
