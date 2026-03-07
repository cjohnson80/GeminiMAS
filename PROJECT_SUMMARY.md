# ATLAS: System Architecture & Workspace Protocol

This document outlines the primary architectural components, data flows, and the organizational hierarchy of the ATLAS Elite Swarm.

## 1. THE IDENTITY BOUNDARY
ATLAS maintains a strict logical separation between its internal reasoning engine and the client projects it builds.

### System Space (Identity)
The following directories define the ATLAS entity. They are persistent, evolving, and separate from any specific mission.
- **Engine (`bin/`):** The logic core (`gemini_mas.py`), API gateways (Next.js & Telegram), and specialized toolsets.
- **Identity (`core/`):** The `SOUL.md` (behavioral protocol), configuration (`local_config.json`), and internal goal tracking (`HEARTBEAT.md`).
- **Capabilities (`skills/`):** Atomic, high-level skill modules that Atlas can "inject" into its reasoning.
- **Knowledge (`knowledge/`):** Summarized research data from the background Research Protocol.
- **The Vault (`library/`):** A persistent repository of verified components and project blueprints.
- **Persistence (`memory/`):** Persistent DuckDB storage for semantic memory and caching.

### Mission Space (Workspace)
- **Projects (`workspace/`):** Every client project is isolated within a sub-directory: `workspace/{project_name}/`.
- All creative artifacts, website code, and databases built for clients MUST live here.
- The workspace is ephemeral; it can be deleted or deployed without affecting the ATLAS identity.

## 2. KEY DATA FLOWS
1. **Command:** Input is received via CLI, Telegram, or the Next.js Web UI.
2. **Triage:** Atlas identifies if the input is a Mission (TASK) or casual CHAT.
3. **Targeting:** Atlas sets its focus to the specific mission directory in `workspace/`.
4. **Execution:** Specialized Swarm agents (Architect, Developer, Reviewer) operate within that directory.
5. **Learning:** High-value code patterns discovered in the workspace are extracted and saved to the **System Vault** (`library/`) for future reuse.
6. **Deployment:** Once verified, the workspace artifacts are pushed to Git and deployed to production (Vercel).

## 3. CORE TECHNOLOGY STACK
*   **Engine:** Python 3.14 (Async/Multithreaded).
*   **Intelligence:** Gemini 1.5 Pro (Multimodal Vision & Audio).
*   **Persistence:** DuckDB + Polars.
*   **Web Skin:** Next.js 15 + FastAPI + Tailwind CSS v4.
*   **DevOps:** Playwright (Visual Audit), Vercel CLI, GitHub CLI.

This structure ensures that ATLAS remains a high-performance, self-improving architect while maintaining perfect organization across any number of client missions.