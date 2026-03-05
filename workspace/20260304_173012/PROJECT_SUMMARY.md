# Project Summary: GeminiMAS Evolution Framework

## 1. Core Architecture
- **Engine (`gemini_mas.py`):** Handles core logic, LLM interaction, and self-modification triggers.
- **Gateway (`tg_gateway.py`):** Asynchronous event loop for Telegram I/O.
- **Constraint Management:** All resource-heavy operations are gated via `local_config.json`.

## 2. Self-Improvement & Approval Workflow
1. **Analysis:** System identifies optimization candidate (e.g., performance bottleneck).
2. **Branching:** System creates `feat/opt-[timestamp]` branch.
3. **Execution:** Modification applied to code; configuration updated to disable legacy features if necessary (per Conservation Principle).
4. **Validation:** Run `verify_project` on the new branch.
5. **Proposal:** System sends diff summary to Telegram for user approval.
6. **Merge:** Upon user confirmation (`/approve`), changes are merged into `main` and deployed.

## 3. Git Branching Strategy (Low-Resource Optimized)
- `main`: Stable production code.
- `feat/*`: Atomic, single-purpose optimization branches.
- `fix/*`: Immediate bug remediation.
- **Strategy:** Local git history is pruned periodically to keep repository size minimal for the Intel Celeron hardware. Remote tracking is kept to a single origin to reduce network overhead.

## 4. Conservation Principle Enforcement
- No `rm` commands allowed on source files.
- All legacy logic must be wrapped in conditional checks linked to `local_config.json` entries.