"""Reusable Streamlit visual UI rendering components."""

import streamlit as st
from typing import Dict, Any, List


def render_header():
    st.markdown("""
        <div style="background-color:#0E1117; padding:18px; border-radius:10px; border:1px solid #30363D; margin-bottom:20px;">
            <h1 style="color:#58A6FF; margin:0;">🛡️ AI-Based Cybersecurity Incident Diagnosis Expert System</h1>
            <p style="color:#8B949E; margin:5px 0 0 0;">Automated Deterministic Rule-Based Triage & Diagnostic Inference Engine</p>
        </div>
    """, unsafe_allow_html=True)


def render_diagnosis_card(diag: Dict[str, Any], is_primary: bool = False):
    title_prefix = "⭐ PRIMARY DIAGNOSIS:" if is_primary else "⚡ ALTERNATIVE DIAGNOSIS:"
    color = "#238636" if diag["risk_label"] == "LOW" else "#D29922" if diag["risk_label"] == "MEDIUM" else "#F85149"

    st.markdown(f"""
        <div style="background-color:#161B22; padding:16px; border-radius:8px; border-left:6px solid {color}; margin-bottom:15px;">
            <h3 style="color:#F0F6FC; margin:0;">{title_prefix} {diag['name']}</h3>
            <p style="color:#8B949E; margin:4px 0 8px 0;">Category: <b>{diag['category']}</b></p>
            <p style="color:#C9D1D9;">{diag['description']}</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Evidence Confidence", f"{diag['confidence'] * 100:.1f}%")
    with col2:
        st.metric("Dynamic Risk Score", f"{diag['risk_score'] * 100:.1f}%")
    with col3:
        st.metric("Severity Rating", diag["risk_label"])

    with st.expander("📌 Recommended Defensive Playbook"):
        for step in diag["recommendations"]:
            st.write(f"- {step}")