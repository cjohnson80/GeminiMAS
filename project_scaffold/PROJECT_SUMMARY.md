# Project Summary and Architectural Overview

**Current Status:** API Quota Blocked (Estimated 23h 54m until reset).
**Impact:** High reliance on external research tools (**RESEARCH SWARM**) is suspended.

## Strategic Pivot
Until the quota resets, execution focus shifts entirely to internal development, structural integrity, and preparing for the next research cycle.

1. **Priority 1: Local Evolution & Commit:** Continue **EVOLUTION PROTOCOL (LOCAL)** and the code modification/commit portion of **EVOLUTION PROTOCOL (GLOBAL)**.
2. **Priority 2: Documentation & Scaffolding:** Focus on Architect duties: generating robust documentation and improving internal tooling structure.
3. **Priority 3: Offline Simulation:** Where external calls are required (e.g., in RESEARCH SWARM), replace them with internal planning, data structure mockups, or simulation runs using existing local data.

## Core Component Data Flow

| Component | Function | Dependencies | Output/Storage |
| :--- | :--- | :--- | :--- |
| `atlas_core.py` | Core Execution Loop | `tg_gateway.py`, `cache_utils.py`, `db_manager.py` | Logs, Workspace, Memory DB |
| `tg_gateway.py` | User I/O Interface | Telegram API | Input queue, Notification output |
| `db_manager.py` | Persistent State Management | `memory.db` | State snapshots, Query results |
| `cache_utils.py` | High-Speed Data Retrieval | In-memory dictionary/Redis (if implemented) | Fast lookups for recurring data |

## Interfaces and Constraints
- **Shell Execution:** Managed via `run_shell`. Used sparingly for Git/system-level tasks.
- **Configuration:** `core/local_config.json` dictates hardware constraints and feature enablement.
- **Git Branching:** All evolution work must use temporary feature branches before potential merging, adhering to the evolutionary mandate.

## Mitigation for Quota Block
- **RESEARCH SWARM:** Goals 1, 2, and 4 are externally dependent and will be marked as PAUSED in the next HEARTBEAT cycle. Goal 3 (saving findings) will be simulated by generating placeholder documentation in `knowledge/` if that directory existed, or planning the structure for it.
- **EVOLUTION PROTOCOL:** The local optimization (Goal 3) and the code modification/commit (Global Goals 1-4) can proceed fully offline. Only the final Telegram notification (Global Goal 5) might be queued or skipped until connectivity is confirmed/needed.