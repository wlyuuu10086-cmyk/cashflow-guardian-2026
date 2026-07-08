# CashFlow Guardian Video Demo Script

**Target Duration**: ~3.5 minutes
**Presenter Roles**: Narrator and Screen Demonstrator

---

### Part 1: Problem and Value (0:00 - 0:20)
* **Visual**: Show the project README.md title or a slides mockup.
* **Narrator (Audio)**:
  > "Welcome to CashFlow Guardian, a secure decision-support system designed to protect Small and Medium Enterprises from sudden liquidity crises. We solve the risk of model hallucination by separating AI reasoning from authoritative deterministic calculations, and gating all operations with a policy engine."

---

### Part 2: Architecture & Setup (0:20 - 0:45)
* **Visual**: Open the Mermaid architecture diagram from the README.md in VS Code.
* **Narrator (Audio)**:
  > "Our architecture enforces strict separation of concerns. Untrusted inputs are screened and redacted by FastAPI. If safe, they are dispatched through `execute_tool_with_policy()`. Our AI orchestrator—built on the Google ADK—only has access to model-safe, read-only, or draft-only tools, keeping database mutations completely secure."
* **Action**: Show `app/adk_app.py` in VS Code.

---

### Part 3: Portfolio Snapshot (0:45 - 1:20)
* **Visual**: Open a terminal and run the local server using:
  `uv run python -m uvicorn app.adk_app:app --port 8080`
  Then, execute a portfolio snapshot event via curl or Invoke-RestMethod:
  `Invoke-RestMethod -Method Post -Uri http://localhost:8080/apps/cashflow_guardian/trigger/pubsub -ContentType "application/json" -Body (Get-Content config/portfolio_event.json)`
* **Narrator (Audio)**:
  > "Let's trigger an ambient event. We push a simulated Pub/Sub event for a portfolio snapshot. The API validates the envelope, binds the `SecurityContext` for an analyst role, and invokes the data engine. The agent retrieves the snapshot and formats the high-risk businesses into a clear table."

---

### Part 4: Scenario Simulation (1:20 - 1:50)
* **Visual**: Trigger a scenario simulation event:
  `Invoke-RestMethod -Method Post -Uri http://localhost:8080/apps/cashflow_guardian/trigger/pubsub -ContentType "application/json" -Body (Get-Content config/simulate_event.json)`
* **Narrator (Audio)**:
  > "Next, we run a stress-test scenario. Here, we simulate a 15% revenue drop for demo business B00001. The engine calculates the cash-flow impact deterministically, and the agent explains the projected liquidity outcomes without making up any math."

---

### Part 5: Security Containment & Prompt Injection (1:50 - 2:20)
* **Visual**: Trigger an event containing a prompt injection:
  `Invoke-RestMethod -Method Post -Uri http://localhost:8080/apps/cashflow_guardian/trigger/pubsub -ContentType "application/json" -Body (Get-Content config/injection_event.json)`
* **Narrator (Audio)**:
  > "Safety is critical. If a user attempts a prompt injection to bypass controls or access sensitive data, our security screening immediately intercepts it, returning a safe warning and refusing execution."

---

### Part 6: Privilege Escalation Containment (2:20 - 2:45)
* **Visual**: Show `tests/integration/test_policy_tool_enforcement.py` and run a command requesting admin tools.
* **Narrator (Audio)**:
  > "Similarly, if the model attempts to invoke a privileged tool like approval or rejection, the policy engine rejects the request. The agent's SecurityContext is hardcoded to a least-privileged analyst role, preventing any privilege escalation."

---

### Part 7: Human-in-the-Loop Boundaries (2:45 - 3:05)
* **Visual**: Trigger an intervention proposal event. Point out the `"status": "draft_requires_review"` in the response.
* **Narrator (Audio)**:
  > "For interventions, the agent is permitted to draft a proposal. However, the action is marked as 'draft_requires_review'. The agent cannot bypass this; actual watchlist additions and executions are kept strictly as human actions in the database."

---

### Part 8: Verification & Smoke Evaluation (3:05 - 3:25)
* **Visual**: Run the regression tests and trace checker in terminal:
  `uv run pytest -q`
  `uv run python tests/eval/check_step9_traces.py artifacts/step9/smoke_traces/smoke_traces.json`
* **Narrator (Audio)**:
  > "Our local test suite is fully verified, with 147 test cases passing successfully. We also executed the Agents CLI smoke evaluation to confirm tool routing and containment, passing all deterministic trace audits."

---

### Part 9: Limitations & Wrap-Up (3:25 - 3:45)
* **Visual**: Show the README.md Limitations section.
* **Narrator (Audio)**:
  > "Due to local environment constraints, live Google Cloud deployment and Vertex AI grading were bypassed. However, CashFlow Guardian successfully delivers a robust, secure, and policy-gated local orchestrator ready for enterprise grading. Thank you!"
