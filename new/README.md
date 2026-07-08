# CashFlow Guardian Submission Visual Pack

This folder contains a clean replacement visual package for the project submission.
It is intentionally separate from the main `cashflow_guardian/` source tree.

## Files

- `index.html` - Open this in a browser and screenshot it as the new architecture/mind-map visual.
- `mindmap.txt` - Plain-text ASCII version of the same visual, matching the style of the reference screenshots.
- `code_snippets.md` - Necessary notebook/demo code cells and terminal commands.
- `demo_payloads.py` - Small helper that writes local Pub/Sub-style demo request bodies.
- `curl_payloads/` - Tiny request bodies for the simplified demo endpoints.
- `screenshot_and_video_guide.md` - Exact screenshot targets and a 3-4 minute recording plan.

## Recommended Use

1. Open `new/index.html` in a browser.
2. Screenshot the full title and the first grey ASCII diagram panel.
3. Start the FastAPI app from `cashflow_guardian/`.
4. Use the `curl_payloads/` commands in `code_snippets.md` for terminal evidence.
5. Follow `screenshot_and_video_guide.md` for the required still images and video order.

## Main Message

The architecture should be presented as:

> CashFlow Guardian is not an LLM doing financial math. It is a policy-gated
> deterministic cash-flow intelligence system, with Google ADK used only as a
> safe explanation and orchestration layer.
