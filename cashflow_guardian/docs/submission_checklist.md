# Submission Checklist

Verify all of the following steps before submitting the Capstone project.

---

### Phase 1: Repository Safety & Cleanup
- [ ] **Git Setup**: Verify the local Git repository is initialized.
- [ ] **Scrub Secrets**: Check that no `.env` or other configuration files containing API keys are tracked.
- [ ] **Scrub Credentials**: Verify `dummy_credentials.json` is completely deleted.
- [ ] **Review .gitignore**: Ensure `.env`, `.venv`, and `__pycache__/` are present in `.gitignore`.
- [ ] **No Absolute Paths**: Verify code contains no hardcoded absolute paths to local user directories.

### Phase 2: Code & Execution Verification
- [ ] **Clean Check**: Run `uv run python -m compileall -q src tests app agents_cli_agent` to verify compilation.
- [ ] **Dependencies Check**: Run `uv pip check` to confirm clean packages.
- [ ] **Run pytest**: Execute `uv run pytest` to verify all 147 test cases pass.

### Phase 3: Push and GitHub Verification
- [ ] **Push**: Push the clean codebase to your private or public GitHub repository.
- [ ] **Scrub check on GitHub**: Perform a repository-wide search on GitHub for terms:
  - `GOOGLE_API_KEY`
  - `GEMINI_API_KEY`
  - `private_key`
- [ ] **Render Readme**: Verify that the Mermaid diagram and all markdown elements render properly on the GitHub repository homepage.

### Phase 4: Media & Presentation
- [ ] **Demo Video**: Record a 3-4 minute presentation following the [demo_script.md](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/docs/demo_script.md).
- [ ] **Upload Demo**: Upload the demo to a sharing platform (such as YouTube, Vimeo, or Google Drive) with correct sharing permissions.
- [ ] **Cover Image**: Prepare and upload a high-quality cover image for the project submission.

### Phase 5: Submission Submission
- [ ] **Writeup Draft**: Copy the finalized writeup from [kaggle_writeup_draft.md](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/docs/kaggle_writeup_draft.md) and paste it into the Kaggle writeup field.
- [ ] **Include Links**: Paste both the GitHub repository URL and the demo video link in the designated fields.
- [ ] **Review Rules**: Confirm that the writeup correctly distinguishes between implemented vs not completed features.
- [ ] **Submit**: Click submit before the capstone deadline.
