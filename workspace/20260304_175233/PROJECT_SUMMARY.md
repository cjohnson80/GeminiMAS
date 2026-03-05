# Self-Evolution & Optimization Architecture

## 1. Low-Resource Strategy (Intel Celeron)
- **Concurrency Control:** Hard-limit thread pool to 2 threads in `gemini_mas.py` to prevent context-switching overhead.
- **Memory Management:** Enforce 512MB cache ceiling. Implement LRU eviction for transient task metadata.
- **Feature Toggling:** Utilize `local_config.json` to disable heavy modules (e.g., `telemetry_verbose`, `background_indexing`, `web_search_cache`).

## 2. Evolution Workflow
- **Branch Strategy:** 
  - `main`: Stable production code.
  - `feat/opt-*`: Experimental performance optimizations.
  - `evolve/*`: Self-modification proposals for core logic.
- **Verification:** Every evolution must pass `verify_project` before merging to `main`.

## 3. Module Configuration (`local_config.json`)
- `disabled_features`: ["telemetry_verbose", "background_indexing", "nlp_heavy_parsing", "realtime_logging"]
- `resource_limits`: { "max_threads": 2, "mem_limit": "512MB" }

## 4. Architectural Interfaces
- **Core Engine:** `gemini_mas.py` acts as the orchestrator.
- **Gateway:** `tg_gateway.py` handles I/O; decoupled from logic via task queues.
