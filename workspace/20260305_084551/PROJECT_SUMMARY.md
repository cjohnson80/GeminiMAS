# Project Summary: Heartbeat Processor Utility

**Date:** 2026-03-05
**Agent Role:** Architect

This document outlines the design for the 'Heartbeat Processor' utility. This utility scans Markdown files for checklist items containing embedded shell commands, executes those commands, and updates the checklist state based on the outcome.

---

## 1. Architecture Definition

### 1.1 Core Components

| Component | Responsibility | Dependencies | Execution Context |
| :--- | :--- | :--- | :--- |
| `HeartbeatAgent` | Orchestrates the entire process: scanning, dispatching, and reporting. | All others | Main thread/Task Manager |
| `MarkdownTaskParser` | Reads the target file, uses Regex to extract tasks (`[ ] Task Name {command: ...}`), and generates a structured Task List.| None (File I/O) | Synchronous |
| `ShellExecutor` | Safely executes the raw shell command string, capturing stdout, stderr, and return code. | None (System Call) | Asynchronous (Threaded) |
| `TaskStateManager` | Updates the source Markdown file atomically: changes `[ ]` to `[x]` (success) or `[!]` (failure) and appends execution logs.| `ShellExecutor` results | Synchronous (File I/O) |

### 1.2 Data Flow and State Management

1.  **Initialization:** `HeartbeatAgent` loads configuration and identifies target files.
2.  **Parsing:** `HeartbeatAgent` passes the file path to `MarkdownTaskParser`, receiving a `Task List` (list of structured task objects).
3.  **Dispatching (Parallel Execution):** For each task in the list, the `HeartbeatAgent` submits the execution request (containing the command and file context) to a thread pool managed by the main agent, utilizing the `ShellExecutor`.
4.  **Execution:** `ShellExecutor` runs the command and returns an `ExecutionResult` object.
5.  **State Update:** The `HeartbeatAgent` aggregates the `ExecutionResult` and passes it along with the original task context to `TaskStateManager`. `TaskStateManager` rewrites the source file, updating the checklist marker and appending notes.
6.  **Reporting:** The agent compiles all results for final operator notification.

### 1.3 High-Performance Strategy (Thread Utilization)

Given the high-performance hardware profile, the execution of I/O-bound operations (file reading/writing) and CPU-bound operations (shell execution) will be parallelized:

*   **Concurrency Limit:** Limited to `MAX_THREADS: 2` (as per hardware profile) for concurrent shell executions to prevent system overload, although the thread pool size can be larger for managing asynchronous callbacks.
*   **Caching:** Intermediate parsing results and recent execution statuses will be stored in a large, thread-safe cache (e.g., Redis or an in-memory dict protected by locks) to prevent redundant file reads or re-execution checks.

---

## 2. Next Steps

1.  Implement the core Python classes based on this architecture.
2.  Define the specific regular expression pattern for command extraction in `MarkdownTaskParser`.
3.  Configure the main execution loop in `$AGENT_ROOT/bin/gemini_mas.py` to initialize the `HeartbeatAgent` upon system startup or request.