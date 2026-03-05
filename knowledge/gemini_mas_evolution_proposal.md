# GeminiMAS Core Evolution Proposal: Performance and Architectural Refinement

**Date:** 2026-03-05
**Source Analysis:** Developer Feedback & Agent Self-Assessment

## 1. Architectural Refactoring Steps

This section outlines the concrete steps required to implement the performance enhancements identified.

### 1.1. Concurrency Enhancement: Decoupling I/O
*   **Target:** Telegram Gateway (`$AGENT_ROOT/bin/tg_gateway.py`) and Core Processor (`$AGENT_ROOT/bin/gemini_mas.py`).
*   **Action:** Refactor the communication layer to use a non-blocking, asynchronous message queue (e.g., `asyncio.Queue` or Redis Pub/Sub if external dependency is acceptable) between the core logic and the I/O handlers. The main processing loop must not wait for network responses.

### 1.2. Caching Optimization
*   **Target:** Knowledge Retrieval and State Management.
*   **Action:** Implement a high-speed, in-memory cache (e.g., `functools.lru_cache` or a custom implementation) with Time-To-Live (TTL) for frequently accessed knowledge chunks and intermediate reasoning steps. Goal: Reduce knowledge lookup latency by 50% under load.

### 1.3. Configuration-Driven Execution Flow
*   **Target:** `$AGENT_ROOT/bin/gemini_mas.py` entry points.
*   **Action:** Harden the initialization sequence to check `local_config.json` *before* attempting to initialize or run modules marked as disabled (e.g., `telemetry_verbose`). This prevents resource waste on disabled paths.

## 2. Conservation Statement

**This proposal strictly adheres to the Conservation Principle.** No existing functionality, code paths, or modules will be deleted from the repository (`$REPO_ROOT`).

*   **Mechanism for Preservation:** Suboptimal or experimental features (e.g., verbose logging, potentially complex legacy state handlers) will be retained in the codebase but explicitly **disabled** via boolean flags within `/local_config.json`.
*   **Benefit:** This ensures full backward compatibility and allows for easy rollback or targeted testing on different hardware profiles. Performance gains are achieved by *skipping* execution paths, not by removing them.

## 3. Next Steps
1.  Implement Async I/O abstraction layer.
2.  Integrate TTL Cache into `KnowledgeRetriever` class.
3.  Update main execution loop to respect configuration flags at the module entry point.

