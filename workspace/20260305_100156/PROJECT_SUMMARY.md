# Project Summary: Heartbeat Processor Architecture

**Target Component:** `bin/heartbeat_processor.py`
**Goal:** Design a robust, high-performance processor for handling incoming agent heartbeats, constrained by the system's limited threading capacity.

## 1. Architecture Overview

The `heartbeat_processor.py` will implement a producer-consumer pattern using three core, decoupled classes to ensure modularity and thread safety.

| Component | Responsibility | Interactions |
| :--- | :--- | :--- |
| `TaskParser` | Validates, deserializes, and normalizes raw heartbeat data. | Input: Raw Data; Output: Structured Task Object. |
| `StateManager` | Manages persistent state (e.g., agent status, last seen time) using thread-safe file operations on the `$AGENT_ROOT/state/` directory. | Thread-safe R/W operations; Synchronization required for state updates. |
| `TaskExecutor` | Executes the actual work defined by the task object (e.g., logging, triggering external actions). | Consumes tasks from the queue; interacts with the system shell or I/O. |

## 2. Concurrency and Threading Model

Given the hardware profile restricts execution to **MAX_THREADS: 2**, the `TaskExecutor` will utilize a `concurrent.futures.ThreadPoolExecutor` initialized with a maximum of **2 worker threads**.

*   **Data Flow:** Heartbeats are received and passed sequentially to `TaskParser`.
*   **Queueing:** Tasks ready for execution are placed onto an internal, thread-safe queue (e.g., `queue.Queue`).
*   **Consumption:** The `TaskExecutor`'s thread pool will pull tasks from this queue, ensuring that no more than two tasks are processed concurrently.

## 3. File System Interaction

*   **State Management:** The `StateManager` is the sole component authorized to perform read/write operations against the agent state directory (`$AGENT_ROOT/state/`). All interactions must use appropriate locking mechanisms (e.g., file locks or process locks if necessary) to prevent race conditions between the two active executor threads.
*   **Configuration:** The processor must dynamically read the hardware constraint (`MAX_THREADS`) from `local_config.json` or rely on the hardcoded limit of 2 for the executor initialization.

## 4. Dependency Mapping

1.  **Heartbeat Ingestion** $ightarrow$ `TaskParser` (Validation)
2.  `TaskParser` $ightarrow$ `StateManager` (Context Check/State Update)
3.  `StateManager` $ightarrow$ **File System** (State Persistence)
4.  `StateManager` $ightarrow$ `TaskExecutor` (Task Submission to 2-thread pool)
5.  `TaskExecutor` $ightarrow$ **Shell/External Systems** (Action Execution)