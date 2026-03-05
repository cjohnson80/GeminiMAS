```json
{
  "final_summary": {
    "status": "IN_PROGRESS",
    "message": "The execution history shows a recursive loop of debugging attempts to reliably parse `HEARTBEAT.md` into `pending_tasks.json`. The core issue identified by the SENIOR_DEBUGGER_ADVICE was using `execute_python` for complex, multi-line logic, leading to JSON escaping and syntax errors. The last successful strategic step was preparing to execute a robust, dedicated Python script (`extract_tasks.py`) via `run_shell` (step 8). However, the execution of this step is missing from the history, and the state of `HEARTBEAT.md` (specifically step 6's attempt to update it) suggests the system is still stuck in the initial task extraction phase.",
    "next_action_recommendation": "The immediate goal is to break the loop and execute the primary task: processing `HEARTBEAT.md`. Since step 8 prepared the robust script `extract_tasks.py`, the next action must be to execute it using the `run_shell` tool, as this bypasses the limitations of `execute_python` for complex payloads.",
    "steps_taken_summary": [
      "Attempted to read HEARTBEAT.md (Steps 1, 3, 5).",
      "Attempted to execute Python logic directly in `execute_python`, which failed due to syntax/escaping issues (Steps 2, 6).",
      "Attempted to write intermediate Python scripts (`parse_heartbeat.py`, `extract_tasks.py`) to disk to enable execution via `run_shell` workaround (Steps 4, 8).",
      "Attempted to update HEARTBEAT.md using a hardcoded string replacement, indicating a potential state stabilization attempt (Step 6).",
      "Attempted to diagnose a separate file error in `heartbeat_processor.py` (Step 7), indicating context switching or previous errors bleeding into the current flow."
    ],
    "critical_path_forward": [
      "Execute the prepared script `extract_tasks.py` using `run_shell` to reliably generate `pending_tasks.json`.",
      "After successful generation, proceed to create the `PROJECT_SUMMARY.md` and create the feature branch as originally intended."
    ],
    "tool_call_for_next_step": {
      "tool": "run_shell",
      "payload": "python3 extract_tasks.py"
    }
  }
}
```