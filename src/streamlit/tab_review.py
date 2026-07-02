import streamlit as st
import pandas as pd

def render_near_duplicate_inspector():
    if not st.session_state.audit_run:
        st.info("Run Quality Audit first to discover issues requiring review.")
    else:
        findings = st.session_state.discrepancies
        near_dupe_findings = [f for f in findings if f.issue_type == "Near-Duplicate Records"]
        
        if not near_dupe_findings:
            st.success("✅ No near-duplicate records require manual review in this dataset!")
        else:
            st.markdown("### 👯 Near-Duplicate Records Inspector")
            st.info("The following groups of records are extremely similar (e.g. minor typos, spelling variations) and may be duplicates. Review them below:")
            
            for idx, finding in enumerate(near_dupe_findings):
                indices = finding.row_indices
                st.markdown(f"**Near-Duplicate Group #{idx+1} (Similarity Match):**")
                st.dataframe(st.session_state.df.loc[indices].astype(str), width="stretch")
                st.markdown("---")
