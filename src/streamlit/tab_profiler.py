import streamlit as st
import pandas as pd

def render_profiler():
    if not st.session_state.get("profile"):
        st.info("Please upload a dataset to view its profile.")
        return
        
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
