# Deployment Specification: CashFlow Guardian

This document defines the deployment targets, environment setups, and execution playbooks for the **CashFlow Guardian** system.

---

## 1. Primary Deployment Targets

### 1.1 Local Development Environment (Target 1 - Core MVP)
* **Goal:** A simple, fast, and repeatable setup for local coding, debugging, and testing.
* **Database:** Local DuckDB file accessed in read-only mode.
* **HITL Action Store:** A local JSON file `data/demo_actions.json`.
* **Execution Runner:** Python 3.10+ virtual environment.

### 1.2 Interactive Streamlit Dashboard (Target 2 - Capstone Presentation)
* **Goal:** A user-friendly, responsive interface showing portfolio statistics, business details, scenario outcomes, and HITL actions.
* **Deployment Location:** Run locally on the developer's laptop, exposing port 8501.

### 1.3 Cloud Run (Target 3 - Optional / Post-Capstone)
* **Goal:** Containerized deployment of the Streamlit application and engines to Google Cloud Run.
* **Database:** Mounted read-only DuckDB in the container or connected to Cloud Storage.

---

## 2. Local Environment Setup

### 2.1 Dependencies Configuration (Virtualenv Setup)
To create and initialize the local environment, run the following commands (provided as placeholders for implementation):

```bash
# 1. Navigate to the cashflow_guardian directory
# cd cashflow_guardian (Do not run cd directly, execute python commands from root)

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows:
venv\Scripts\activate
# Unix/macOS:
source venv/bin/activate

# 4. Install required packages (PyYAML, Streamlit, DuckDB, XGBoost, Scikit-Learn)
pip install --upgrade pip
pip install duckdb pandas numpy scikit-learn xgboost streamlit pyyaml python-dotenv
```

---

## 3. Database & Data Store Paths

To prevent local path configuration mismatches, the system resolves files relative to the project root:
* **Database path:** `sme_cashflow_stress_project/data/sme_cashflow_stress.duckdb`
* **Demo Action Store path:** `data/demo_actions.json`
* **Model Artifacts path:** `models/`

---

## 4. Execution Commands (Placeholders)

Once the application files are written, developers will run the system using these commands:

### 4.1 Launching the Streamlit App
To start the presentation dashboard:
```bash
streamlit run app/app.py
```

### 4.2 Running the Verification Suite
To run the automated tests:
```bash
pytest tests/
```

### 4.3 Running Model Evaluation
To evaluate model performance:
```bash
python scripts/evaluate_model.py
```

### 4.4 Running Agent Evals
To execute the agent test cases:
```bash
python evals/agent_eval.py
```
