# Project Summary: GeminiMAS Core Architecture

**Date Created:** 2026-03-05
**Current Focus:** Defining the state transition architecture for the `/approve` command.

---

## 1. `/approve` Command State Transition Architecture

The `/approve` command is critical for moving a task or execution flow from a review state to an active execution state. This requires a clear, idempotent state machine definition.

### 1.1. State Definition

*   **WAITING_FOR_APPROVAL (Source State):** The system is paused, awaiting explicit confirmation from the operator (e.g., via Telegram or a CLI flag) to proceed with the planned operations.
*   **IN_PROGRESS (Target State):** The system has received approval and begins executing the planned sequence of actions (e.g., running shell commands, generating code, deploying).

### 1.2. State Transition Logic

**Trigger:** Reception of the `/approve` command payload, verified against the current task context.
**Transition:** `WAITING_FOR_APPROVAL` $ightarrow$ `IN_PROGRESS`

**Data Flow:**
1.  The Telegram Gateway (`$AGENT_ROOT/bin/tg_gateway.py`) receives the message containing `/approve`. 
2.  The core engine (`$AGENT_ROOT/bin/gemini_mas.py`) intercepts this command.
3.  It checks the current session context state. If the state is `WAITING_FOR_APPROVAL`, it logs the approval timestamp and updates the internal state tracker for the current execution thread.
4.  The system then proceeds to the next planned step, which is typically the execution phase.

### 1.3. Dependencies and Scalability Notes

*   **Dependency:** Requires a robust, persistent state management layer (currently implicit, but needs definition for future persistence across sessions).
*   **Scalability:** The transition must be atomic to prevent race conditions if multiple approval paths are possible (though unlikely for a simple `/approve`).

---

## 2. Directory Structure & Dependencies (Initial Review)

| Component | Path | Description |
| :--- | :--- | :--- |
| Core Engine | `$AGENT_ROOT/bin/gemini_mas.py` | Main decision-making logic and execution loop. |
| I/O Gateway | `$AGENT_ROOT/bin/tg_gateway.py` | Handles external communication (Telegram). |
| Configuration | `local_config.json` | Runtime settings and feature toggles. |
| Project Context | This File | Architectural documentation. |

---

## 3. Evolution Plan

Next step will be to define the interface between `tg_gateway.py` and `gemini_mas.py` to reliably pass this approval signal and context payload.