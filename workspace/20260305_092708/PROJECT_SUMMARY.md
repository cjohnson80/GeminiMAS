# HeartbeatAutomation System Architecture

This document outlines the architecture for the HeartbeatAutomation system, designed to process periodic status updates (heartbeats) reliably and intelligently.

## Core Principles
1. **Atomic Updates:** State changes must be transactional; either fully applied or fully rolled back.
2. **Context Awareness:** The system must maintain and utilize the current operational context (state, recent history) for decision-making.
3. **Failure Isolation:** Failures in processing a single heartbeat must not impact the processing of subsequent heartbeats or the overall system state integrity.

## Component Breakdown

### 1. Parser Component (`HeartbeatParser`)

**Responsibility:** Ingest raw heartbeat data (assumed to be JSON or a structured log line) and transform it into a standardized internal `HeartbeatMessage` object.

**Data Flow:** Raw Input -> Parser -> Executor

**Key Features:**
*   Schema Validation: Ensures required fields (e.g., `agent_id`, `timestamp`, `status_code`, `payload`) are present and correctly typed.
*   Data Enrichment: Adds processing timestamps or internal sequence IDs.

### 2. Executor Component (`HeartbeatExecutor`)

**Responsibility:** Contains the core business logic for reacting to the parsed heartbeat. This component manages state transitions and isolation.

**Data Flow:** Parser -> Executor -> (State Store/Context) -> Writer

**Key Features & Isolation Strategy:**
*   **Context Management:** Reads the current system state from the Context Store before processing.
*   **Transactional Buffer:** All proposed changes resulting from the heartbeat are staged in a temporary, in-memory buffer (`TransactionBuffer`).
*   **Decision Engine:** Evaluates the staged changes against current context (e.g., if an agent reports 'CRITICAL', check if it was previously 'OK' to trigger an alert). This ensures context awareness.
*   **Failure Isolation:** If the processing logic fails (e.g., due to bad data causing an unexpected exception), the `TransactionBuffer` is discarded, and the system state remains untouched. The failed message is logged for retry/dead-letter queue processing.

### 3. Writer Component (`StateWriter`)

**Responsibility:** Persists the validated, finalized state changes from the Executor into the persistent store.

**Data Flow:** Executor (on success) -> Writer -> Persistent Store

**Key Features & Atomicity Strategy:**
*   **Atomic Write:** Utilizes database transactions or atomic file operations (e.g., write-ahead logging or temporary file replacement) to ensure that the state update is **Atomic**.
*   **Commit/Rollback:** If the Executor signals success, the Writer commits the transaction. If the Executor fails during the final commit phase, the underlying storage mechanism must handle rollback.

## Data Flow Summary

[Raw Heartbeat] -> [Parser] -> [Executor (Validate & Stage)] -> [Executor (Decision & Buffer)] -> [Writer (Atomic Commit)] -> [Updated System State]

## Dependencies and Implementation Notes
*   **Threading:** The Executor will utilize multi-threading (as per hardware profile) to handle parallel processing of incoming messages, ensuring the Parser can feed the Executor quickly.
*   **Context Store:** Assumed external dependency (e.g., Redis or a dedicated state management module) accessible by the Executor.
