# Project Scratchpad

Goal: run internal evolution

## Acceptance Criteria
# Acceptance Criteria: Internal Evolution Cycle

**Feature:** Self-Optimizing Codebase Update
**Priority:** High
**Assignee:** Senior Software Architect (GeminiMAS)

### 1. Optimization Target Identification
- [ ] The system must analyze `$REPO_ROOT` to identify a specific module or function that requires optimization (e.g., reducing memory footprint, improving execution speed, or refactoring for modularity).
- [ ] The identified target must be explicitly logged with a rationale (e.g., "Detected redundant loop in `tg_gateway.py`").

### 2. Version Control Management
- [ ] A new git branch must be created for this evolution cycle following the naming convention: `evolution/<type>-<short-description>` (e.g., `evolution/perf-reduce-imports`).
- [ ] The `main` branch must remain untouched until the evolution is verified.

### 3. Code Modification & Conservation
- [ ] Code changes must be applied programmatically to the target files.
- [ ] **Conservation Constraint:** Existing features must **not** be deleted. If a feature is deemed too heavy for the current profile (`standard` / Intel Celeron target), it must be disabled via flags in `local_config.json`, not removed from the source.
- [ ] Modifications must align with low-resource optimization principles (e.g., lazy loading imports, minimizing thread usage).

### 4. Stability Verification
- [ ] The system must perform a syntax check (e.g., `python -m py_compile <file>`) on modified files.
- [ ] If available, unit tests relevant to the modified module must pass.
- [ ] The system must confirm that the core engine (`gemini_mas.py`) can still initialize.

### 5. Final Reporting
- [ ] A summary report must be output containing:
    -   The branch name.
    -   Files modified.
    -   Nature of the change.
    -   Instructions for merging (if successful).

## Architecture
(To be defined by Architect)
