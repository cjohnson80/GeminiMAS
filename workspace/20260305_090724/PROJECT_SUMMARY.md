# Project Scratchpad

Goal: Execute the pending tasks in /home/chrisj/gemini_agents/core/HEARTBEAT.md

## Acceptance Criteria
# Acceptance Criteria: Process HEARTBEAT.md Pending Tasks

**AC1: Task Parsing & Identification**
- The system must read the file located at `/home/chrisj/gemini_agents/core/HEARTBEAT.md`.
- All items formatted as pending Markdown checkboxes (e.g., `- [ ]`) must be extracted as the execution queue.

**AC2: Execution Workflow**
- The agent must iterate through the execution queue sequentially.
- For each task:
  - Determine the required action (file creation, code modification, shell command, or analysis).
  - Execute the action utilizing the "High-Performance" hardware profile (multi-threading where applicable).
  - Adhere to the **Conservation Principle**: Never delete features; disable via `local_config.json` if necessary.

**AC3: State Synchronization**
- Upon successful completion of a task, the line in `HEARTBEAT.md` must be updated from `[ ]` to `[x]`.
- If a task fails, the line must be annotated with the failure reason (e.g., `[ ] Task Name (FAILED: <reason>)`) to prevent infinite retry loops.

**AC4: Version Control Safety**
- If a task requires significant code refactoring, a new git branch must be created before changes are applied.
- Minor configuration changes or documentation updates can be committed directly to the current branch.

**AC5: Final Reporting**
- The process must conclude with a summary output detailing:
  - Total tasks found.
  - Tasks successfully completed.
  - Tasks failed/skipped.

## Architecture
(To be defined by Architect)
