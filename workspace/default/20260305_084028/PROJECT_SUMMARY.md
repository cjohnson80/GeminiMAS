# Project Summary: Heartbeat Processor Architecture

## 1. Overview
The Heartbeat Processor is designed to asynchronously ingest, process, and persist state updates derived from system heartbeats. The architecture prioritizes low-latency processing for the Executor component while ensuring data integrity via the StateManager.

## 2. System Constraints & Optimization
*   **RAM Limit:** 11.58 GB. We must use memory-efficient data structures (e.g., highly optimized dictionaries/hash maps, avoiding unnecessary object duplication). The StateManager will utilize file-backed persistence or a highly conservative in-memory cache.
*   **Concurrency Limit:** MAX_THREADS = 2. All core processing (Parsing, Execution) must be carefully orchestrated within these two threads, likely using queues (e.g., `queue.Queue` in Python) to manage asynchronous flow without overwhelming the thread pool.

## 3. Component Architecture

### 3.1. Parser Component (HeartbeatParser)
*   **Responsibility:** Ingest raw heartbeat data (e.g., JSON strings, network packets) and validate/transform it into a canonical internal Message Object.
*   **Interface:** `parse(raw_data: bytes) -> InternalMessage`
*   **Error Handling:** Malformed data results in logging and routing the raw data to a dedicated Dead Letter Queue (DLQ) for later inspection, preventing pipeline stalls.

### 3.2. Executor Component (HeartbeatExecutor)
*   **Responsibility:** Apply business logic based on the `InternalMessage`. This component drives state changes.
*   **Interface:** `execute(message: InternalMessage) -> StateUpdateCommand`
*   **Concurrency Model:** Must interface with the StateManager via thread-safe methods. Given the 2-thread limit, this component will likely run predominantly on one dedicated thread, pulling from a 'Ready-to-Execute' queue.

### 3.3. StateManager Component (StateManager)
*   **Responsibility:** Manages the persistent and in-memory state of all monitored entities. Handles ACID operations for state persistence.
*   **Interface (Write):** `apply_update(command: StateUpdateCommand) -> bool`
*   **Interface (Read):** `get_state(entity_id: str) -> CurrentState`
*   **Memory Strategy:** The in-memory cache will be limited, perhaps storing only the last N heartbeats or the current active state for the top K entities. Full state persistence will default to a fast, local database (e.g., SQLite or a highly efficient key-value store) to respect the RAM constraint.

## 4. Data Flow and Error Strategy
1.  **Ingestion:** Raw Heartbeat $ightarrow$ `HeartbeatParser`
2.  **Validation:** Parser $ightarrow$ `InternalMessage` or $ightarrow$ DLQ.
3.  **Dispatch:** `InternalMessage` $ightarrow$ 'Ready-to-Execute' Queue.
4.  **Processing:** Executor reads from Queue $ightarrow$ `StateUpdateCommand`.
5.  **Persistence:** Executor $ightarrow$ `StateManager.apply_update()`

**Error Handling Summary:**
*   **Parsing Errors:** DLQ.
*   **Execution Errors (Business Logic Failure):** Logged, state update rolled back locally, message re-queued (max 3 retries) or moved to a specific 'Execution Failure' queue.
*   **Persistence Errors (I/O or DB Failure):** Immediate critical alert. Executor queues the command back to the front of the 'Ready-to-Execute' queue for immediate retry, ensuring data loss is minimized before escalating.