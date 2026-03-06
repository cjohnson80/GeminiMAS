# GeminiMAS Core System Architecture Overview

This document outlines the primary architectural components, data flows, and dependencies for the GeminiMAS agent system, assuming a high-performance, thread-safe operation model.

## 1. Core Components & Responsibilities

| Component | Path | Responsibility | Dependencies |
| :--- | :--- | :--- | :--- |
| **Core Engine** | `$AGENT_ROOT/bin/gemini_mas.py` | Primary decision-making, task dispatch, evolution logic. | All sub-modules, `cache_utils.py`, External APIs. |
| **Telegram Gateway** | `$AGENT_ROOT/bin/tg_gateway.py` | Handles asynchronous I/O for human interaction. | `process_tg_response.py`, Network I/O. |
| **Resource Monitor** | `$AGENT_ROOT/bin/monitor.py` | Tracks CPU/RAM utilization, feeds into `local_config.json`. | `monitor_resources.sh`, `logs/resource_monitor.log`. |
| **Data Manager** | `$AGENT_ROOT/bin/db_manager.py` | Manages persistence and retrieval from the memory database. | `memory/memory.db`, `logger_setup.py`. |
| **Configuration** | `$AGENT_ROOT/core/local_config.json` | Runtime configuration overrides (e.g., thread limits, feature toggles). | All modules. |

## 2. Data Flow and Persistence

1.  **Input (Telegram/Shell):** Input is routed via `tg_gateway.py` or direct shell execution into the **Core Engine**.
2.  **Processing:** The Core Engine consults **Memory** (`memory.db`) via `db_manager.py` for context and executes logic defined in `skills/`. Caching is managed by `cache_utils.py` to minimize redundant external calls.
3.  **External I/O:** External API calls (e.g., research, generation) are mediated by the Core Engine, which must respect rate limits (429 error handling is critical).
4.  **Logging & State:** All significant actions, configuration changes, and errors are logged to `/logs/` and state updates are persisted to `/data/state/`.
5.  **Evolution:** Architectural changes are proposed by the Core Engine and committed to the repository structure, requiring explicit approval via `approval_manager.py` if security policies are involved.

## 3. Current Architectural Constraint (API Quota Blocked)

Due to an HTTP 429 error, external API access is paused for ~24 hours. The current operational focus shifts entirely to **Local Optimization and Internal Refactoring** as detailed in `workspace/default/24H_LOCAL_STRATEGY.md`. This includes: Refactoring `gemini_mas.py` for better thread utilization and ensuring data integrity checks on local databases.

## 4. Dependencies Summary

*   **Python:** Standard library + specific needs for concurrent execution (`concurrent.futures`).
*   **External:** Primary dependency is the external LLM API; current operations are independent of it.
*   **Shell:** Used for hardware monitoring (`monitor_resources.sh`) and system-level Git operations.

This structure prioritizes resilience and mandates that all core logic be thread-safe, given the high-performance hardware profile.