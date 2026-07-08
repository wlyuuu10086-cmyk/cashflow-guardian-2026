# CashFlow Guardian Submission Screenshot Checklist

Use this checklist to capture visual evidence of system operations while maintaining strict privacy.

---

### 1. 147 Passed Tests
* **Command/File**: Run `uv run pytest` in terminal.
* **Crop Area**: Crop to show the final summary line: `147 passed, 6 warnings in ...`.
* **Do Not Expose**: Local directory structures or usernames.

### 2. Uvicorn Server Startup
* **Command/File**: Run `uv run python -m uvicorn app.adk_app:app --port 8080`.
* **Crop Area**: Crop to show uvicorn startup logs on port 8080.
* **Do Not Expose**: Absolute local file paths.

### 3. GET /health Response
* **Command/File**: `Invoke-RestMethod -Method Get -Uri http://localhost:8080/health`.
* **Crop Area**: Crop to show the JSON response with `status: ok` and `adk_agent`.
* **Do Not Expose**: Windows taskbar or browser tabs.

### 4. Portfolio Snapshot Event
* **Command/File**: Trigger a `portfolio_snapshot` event push.
* **Crop Area**: Crop to show the formatted Markdown table response of highest-risk businesses.
* **Do Not Expose**: Local terminal paths.

### 5. Company Analysis Event
* **Command/File**: Trigger an `analyze_company` event for `B00001`.
* **Crop Area**: Crop to show the Gemini narrative explanation of risk drivers.
* **Do Not Expose**: API keys.

### 6. Prompt Injection Blocked
* **Command/File**: Trigger an event with system-override payload text.
* **Crop Area**: Crop to show the security error response containing injection detection warnings.
* **Do Not Expose**: Private system prompts.

### 7. PII Redaction Summary
* **Command/File**: Trigger a request containing customer email or phone numbers.
* **Crop Area**: Crop to show the response where emails or phone numbers are redacted.
* **Do Not Expose**: Real personal data.

### 8. Privilege Rejection
* **Command/File**: Trigger an event attempting to run `approve_or_reject_watchlist_action`.
* **Crop Area**: Crop to show the policy engine error rejecting the request.
* **Do Not Expose**: Underlying policy file paths.

### 9. Draft Intervention Requiring human review
* **Command/File**: Trigger a `draft_intervention` event.
* **Crop Area**: Crop to show the resulting status field: `"status": "draft_requires_review"`.
* **Do Not Expose**: Database connection details.

### 10. Session Isolation
* **Command/File**: Integration test logs for `test_security_boundaries.py`.
* **Crop Area**: Crop to show session key validation assertions passing.
* **Do Not Expose**: Test framework directories.

### 11. Safe Audit Trace
* **Command/File**: Database log or audit print from `execute_tool_with_policy()`.
* **Crop Area**: Crop to show the audit logging payload with request context and status.
* **Do Not Expose**: Database passwords.

### 12. Agents CLI Real Response
* **Command/File**: Run `agents-cli run "Summarize capabilities"`.
* **Crop Area**: Crop to show the CLI output returning the agent response.
* **Do Not Expose**: Local user profile folders.

### 13. Agents CLI Read-Only Tool Call
* **Command/File**: Run `agents-cli run "Show portfolio 2025-06"`.
* **Crop Area**: Crop to show the tool dispatch logs routing to `get_portfolio_snapshot`.
* **Do Not Expose**: Git branch details.

### 14. Smoke Trace File
* **Command/File**: Open [step9_smoke_traces.json](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/artifacts/step9/smoke_traces/step9_smoke_traces.json).
* **Crop Area**: Crop to show the `eval_case_id` and the recorded tool calls in JSON.
* **Do Not Expose**: Large sections of private instruction text.

### 15. Deterministic Trace-Check Passed
* **Command/File**: Run `uv run python tests/eval/check_step9_traces.py ...`.
* **Crop Area**: Crop to show `passed: true` and `cases_checked: 2`.
* **Do Not Expose**: Python virtual environment paths.

### 16. Architecture Diagram
* **Command/File**: Render the Mermaid diagram from `README.md`.
* **Crop Area**: Crop the flow diagram showing FastAPI, policy gate, and engines.
* **Do Not Expose**: Markdown syntax headers.
