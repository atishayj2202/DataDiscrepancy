from typing import Tuple, Dict
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

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

def calculate_quality_score(df, findings) -> Tuple[int, str, Dict[str, float]]:
    total_rows = len(df)
    missing_rows = set()
    duplicate_rows = set()
    format_rows = set()
    outlier_rows = set()
    
    high_count = 0
    med_count = 0
    
    for f in findings:
        if f.issue_type in ["Null Value", "Incomplete Records"]:
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
            
    p_missing = (len(missing_rows) / total_rows) * 15 if total_rows > 0 else 0
    p_duplicate = (len(duplicate_rows) / total_rows) * 15 if total_rows > 0 else 0
    p_format = (len(format_rows) / total_rows) * 15 if total_rows > 0 else 0
    p_outlier = (len(outlier_rows) / total_rows) * 15 if total_rows > 0 else 0
    
    p_criticality = (high_count * 4.0) + (med_count * 1.5)
    
    p_missing = min(p_missing, 15.0)
    p_duplicate = min(p_duplicate, 15.0)
    p_format = min(p_format, 15.0)
    p_outlier = min(p_outlier, 15.0)
    p_criticality = min(p_criticality, 40.0)
    
    raw_score = 100.0 - (p_missing + p_duplicate + p_format + p_outlier + p_criticality)
    score = max(0, min(100, int(raw_score)))
    
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
