# Cybersecurity Incident Expert System

A Streamlit-based educational expert system that assesses selected cybersecurity indicators and reasons over a JSON knowledge base to produce incident hypotheses and an explanation trace.

## Architecture
- **Knowledge base:** JSON files describing attacks, indicators, recommendations, and production rules.
- **Inference engine:** Evaluates observed facts using forward-chaining rules.
- **Reasoning layer:** Produces diagnosis and explanation information.
- **Persistence:** Stores assessment history in SQLite.
- **Interface:** Streamlit dashboard, incident assessment, history, and academic manual.

## Tech Stack
Python, Streamlit, pandas, SQLite, JSON, rule-based reasoning.

## Setup
```bash
python -m venv .venv
# Activate the environment, then:
pip install -r requirements.txt
streamlit run app.py
```

## Notes
The original local history database and cached bytecode were excluded. The app may create its SQLite database on first run. This is an educational decision-support prototype, not a replacement for professional incident response or security monitoring.
