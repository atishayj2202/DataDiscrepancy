import streamlit as st
import pandas as pd

def render_duplicates_inspector():
    if not st.session_state.audit_run:
        st.info("Please click 'Run Quality Audit' in the sidebar to view duplicates.")
    else:
        findings = st.session_state.discrepancies
        exact_dup_findings = [f for f in findings if f.issue_type == "Exact Duplicate Records"]
        near_dupe_findings = [f for f in findings if f.issue_type == "Near-Duplicate Records"]
        
        if not exact_dup_findings and not near_dupe_findings:
            st.success("✅ No exact duplicate or near-duplicate records found in this dataset!")
        else:
            st.markdown("### 👯 Duplicate & Near-Duplicate Records Inspector")
            st.write("Inspect and review duplicate or near-duplicate record groups detected across your dataset.")
            
            # Segmented toggle choice
            dup_option = st.radio(
                "Select Duplicate Category to Inspect:",
                ["👥 Exact Duplicate Records", "👯 Near-Duplicate Record Candidates"],
                horizontal=True,
                key="duplicates_inspector_toggle"
            )
            st.markdown("---")
            
            if dup_option == "👥 Exact Duplicate Records":
                if not exact_dup_findings:
                    st.success("✅ No exact duplicate record groups found in this dataset!")
                else:
                    st.info("The following groups of rows contain exact identical values across all columns:")
                    for idx, finding in enumerate(exact_dup_findings):
                        indices = finding.row_indices
                        st.markdown(f"**Exact Duplicate Group #{idx+1}:**")
                        st.dataframe(st.session_state.df.loc[indices].astype(str), width="stretch")
                        st.markdown("---")
            else:
                if not near_dupe_findings:
                    st.success("✅ No near-duplicate record groups found in this dataset!")
                else:
                    st.info("The following groups of records are extremely similar (e.g. minor typos, spelling variations) and may be duplicates. Review them below:")
                    for idx, finding in enumerate(near_dupe_findings):
                        indices = finding.row_indices
                        st.markdown(f"**Near-Duplicate Group #{idx+1} (Similarity Match):**")
                        st.dataframe(st.session_state.df.loc[indices].astype(str), width="stretch")
                        st.markdown("---")
