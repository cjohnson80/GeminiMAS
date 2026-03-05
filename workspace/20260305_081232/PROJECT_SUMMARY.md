# Project Scratchpad

Goal: Execute the pending tasks in /home/chrisj/gemini_agents/core/HEARTBEAT.md

## Acceptance Criteria
### Acceptance Criteria: Execute Pending HEARTBEAT.md Tasks

**1. Context Loading & Parsing**
*   [ ] Verify the existence and readability of `/home/chrisj/gemini_agents/core/HEARTBEAT.md`.
*   [ ] Parse the file content to identify all pending actionable items (specifically looking for unassigned or unchecked tasks, e.g., `- [ ]` or `TODO:`).

**2. Task Execution**
*   [ ] Sequentially or parallelly (where safe) execute each identified task.
*   [ ] **Constraint Check:** If a task requires code modification, ensure a new git branch is created/checked out.
*   [ ] **Conservation Check:** Ensure no existing features are deleted; if a task requests removal, disable via `local_config.json` instead.

**3. State Persistence**
*   [ ] Update `/home/chrisj/gemini_agents/core/HEARTBEAT.md` in real-time or batch:
    *   Mark successfully completed tasks as done (e.g., change `- [ ]` to `- [x]`).
    *   Append a timestamp or execution log link to the completed item if applicable.
*   [ ] If a task fails, annotate the item in `HEARTBEAT.md` with a `[FAILED]` tag and a brief error reason, preserving the rest of the file structure.

**4. Final Verification**
*   [ ] Output a summary report containing:
    *   Number of tasks attempted.
    *   Number of tasks completed.
    *   Any blockers encountered.

## Architecture
(To be defined by Architect)
