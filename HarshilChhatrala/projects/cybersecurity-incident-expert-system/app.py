"""Main Streamlit application entry point."""

import streamlit as st
import pandas as pd
from pathlib import Path

from knowledge.knowledge_base import KnowledgeBase
from engine.inference_engine import InferenceEngine
from database.database import DatabaseManager
from ui.components import render_header, render_diagnosis_card
from utils.helpers import format_observation_labels

# Page Configuration
st.set_page_config(
    page_title="Cybersecurity Incident Expert System",
    page_icon="🛡️",
    layout="wide"
)

# Initialize Core Services (Cached for performance)
@st.cache_resource
def init_services():
    kb = KnowledgeBase()
    engine = InferenceEngine(kb)
    db = DatabaseManager()
    return kb, engine, db

kb, engine, db = init_services()

render_header()

# Navigation Sidebar
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Select System Module:",
    ["🏠 Dashboard", "🔍 Incident Assessment", "📜 Assessment History", "📘 Academic System Manual"]
)

# PAGE 1: DASHBOARD
if page == "🏠 Dashboard":
    st.subheader("System Architecture & Operational Summary")

    st.markdown("""
    This project is an **AI Production-Rule Expert System** designed for deterministic cybersecurity incident classification and diagnostic explanation.
    It evaluates multi-source security observables against a domain knowledge base using a forward-chaining inference engine.
    """)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Supported Incident Types", len(kb.attacks))
    m2.metric("Observable Indicators", len(kb.get_all_indicator_ids()))
    m3.metric("Production Rules", len(kb.rules))
    m4.metric("Inference Engine", "Forward Chaining")

    st.markdown("---")
    st.markdown("### Conceptual Diagnostic Pipeline")
    st.code("""
User Observations ➔ Fact Collection ➔ Knowledge Base Evaluation ➔ Forward-Chaining Inference ➔ Explanation & Playbook
    """, language="text")


# PAGE 2: INCIDENT ASSESSMENT
elif page == "🔍 Incident Assessment":
    st.subheader("Interactive Incident Triage & Diagnosis")
    st.markdown("Select observed security artifacts from the categories below to initiate reasoning:")

    selected_indicators = []
    categories = kb.get_indicator_categories()

    # Dynamic multi-column layout for indicator selection
    cols = st.columns(2)
    cat_names = list(categories.keys())

    for idx, cat in enumerate(cat_names):
        col = cols[idx % 2]
        with col:
            st.markdown(f"#### {cat}")
            for ind in categories[cat]:
                box = st.checkbox(
                    f"{ind['name']}",
                    key=ind['id'],
                    help=f"ID: {ind['id']} | {ind['description']}"
                )
                if box:
                    selected_indicators.append(ind['id'])

    st.markdown("---")
    analyze_btn = st.button("🚀 Execute Expert Diagnosis", type="primary", use_container_width=True)

    if analyze_btn:
        if not selected_indicators:
            st.warning("⚠️ Please select at least one observable symptom before running diagnosis.")
        else:
            with st.spinner("Executing Forward-Chaining Reasoning Engine..."):
                result = engine.run(selected_indicators)
                # Persist result to SQLite
                db.save_assessment(selected_indicators, result)

            st.markdown("## Diagnostic Analysis Results")

            if result["insufficient_evidence"]:
                st.error("⚠️ **INSUFFICIENT EVIDENCE FOR DEFINITIVE DIAGNOSIS**")
                st.info("The observed symptoms do not trigger sufficient rule confidence (<35%) to confirm a known incident category. Continue monitoring or provide additional observations.")
            else:
                top_diag = result["diagnoses"][0]
                render_diagnosis_card(top_diag, is_primary=True)

                if len(result["diagnoses"]) > 1:
                    st.markdown("### Secondary / Competing Hypotheses")
                    for alt_diag in result["diagnoses"][1:]:
                        render_diagnosis_card(alt_diag, is_primary=False)

            st.markdown("---")
            st.markdown("### 🧠 Dynamic Explanation Trace")
            st.markdown("The step-by-step reasoning executed by the inference engine:")

            for step in result["explanation_trace"]:
                with st.expander(f"Step {step['iteration']}: Fired Rule '{step['rule_name']}' [{step['rule_id']}]"):
                    st.write(f"**Justification:** {step['explanation']}")
                    if step["asserted_facts"]:
                        st.write(f"**Asserted Intermediate Facts:** {step['asserted_facts']}")
                    if step["evidence_added"]:
                        st.write("**Updated Hypothesis Confidence:**")
                        st.json(step["evidence_added"])


# PAGE 3: ASSESSMENT HISTORY
elif page == "📜 Assessment History":
    st.subheader("Historical Incident Audit Logs")

    history = db.get_all_assessments()
    if not history:
        st.info("No prior assessments recorded in SQLite database.")
    else:
        df = pd.DataFrame(history)
        st.dataframe(df[["id", "timestamp", "primary_diagnosis", "confidence", "risk_label"]], use_container_width=True)


# PAGE 4: ACADEMIC SYSTEM MANUAL
elif page == "📘 Academic System Manual":
    st.subheader("Academic Documentation & Theory")
    st.markdown("""
    ### System Architecture & Logic
    * **Knowledge Base:** Decoupled JSON data files representing rules and attributes.
    * **Working Memory (Fact Base):** Stores active facts and accumulated hypothesis evidence during reasoning.
    * **Inference Engine:** Evaluates preconditions (`all_of`, `any_of`, `none_of`) and executes forward chaining until no new rules fire.
    * **Uncertainty Model:** Asymptotic confidence aggregation model prevents probability overflow and correctly handles non-conclusive overlapping symptoms.
    """)