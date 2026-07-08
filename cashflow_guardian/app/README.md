# App

Local application entry points.

`adk_app.py` exposes the FastAPI ambient Pub/Sub-style endpoint for the thin
ADK integration. Future Streamlit work should live separately and must not
bypass the policy-gated tool boundary.
