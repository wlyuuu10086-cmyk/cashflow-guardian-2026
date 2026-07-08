# Antigravity (Gemini) Developer Rules: CashFlow Guardian

This document defines the working process and coding standards for the Antigravity AI coding assistant within the **CashFlow Guardian** repository.

---

## 1. Task Planning and Alignment

* **Substantial Tasks Start with a Plan:** Always begin any major architectural change, new feature, or complex refactoring by writing or updating the `implementation_plan.md` artifact.
* **Obtain Approval First:** Once a plan is created/updated, set `request_feedback = true` in the metadata, summarize the decisions, and **STOP** to wait for explicit user approval before modifying code.
* **Stop at the Requested Phase:** Do not proceed to implement downstream stages (e.g. implementing the Data Engine or the Streamlit app) until the current specification or planning phase is officially completed and approved.

---

## 2. Code Modifications and Safety

* **Use Small, Reviewable Changes:** Prefer modular, incremental updates. Large monolithic modifications are expensive, difficult to lint, and hard for the user to review.
* **Inspect, Don't Assume:** Always inspect the actual folder structure, database dictionary, and existing python files before writing imports, routing paths, or class definitions. Do not rely on assumptions.
* **Prefer Existing Files:** Maintain the existing workspace layout. Avoid creating duplicate directories (e.g., do not create `.agent/` or `src/agent/` when `src/cashflow_guardian/agent/` is the official package location).
* **Show Diffs clearly:** When editing existing files, use precise target replacement blocks so the user can easily see the additions (`+`) and removals (`-`).

---

## 3. Verification & Validation

* **Run Tests After Every Edit:** Execute the relevant test suite (e.g. `pytest tests/`) immediately after code changes to confirm no regressions are introduced.
* **Syntax Validation:** Verify that all config YAML, JSON, and Gherkin files are syntactically valid before completing a task.
* **Cross-File Consistency:** Check that tool names, parameter schemas, and package module paths are aligned across `tool_contracts.yaml`, `architecture.md`, `behaviors.feature`, and the actual Python source code.

---

## 4. Documentation & Walkthroughs

* **Generate a Walkthrough:** After finishing a phase, update or create a `walkthrough.md` artifact detailing what was completed, which tests were run, and the outcomes.
* **Do Not Re-summarize:** The user can read the artifacts directly. Do not duplicate or re-summarize the exact contents of `implementation_plan.md` or `walkthrough.md` in the chat UI response; highlight only high-level decisions or open questions.
