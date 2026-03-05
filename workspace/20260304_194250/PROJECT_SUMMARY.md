# Project: test-web

## Architectural Overview
A lightweight, high-performance web interface designed for deployment on low-resource hardware (Intel Celeron). The architecture follows a modular, decoupled approach to ensure maintainability and strict resource management.

## Directory Structure
- `/src/core`: Business logic and core engine (agnostic of transport layer).
- `/src/api`: REST/WebSocket interfaces.
- `/src/ui`: Lightweight frontend components (Vanilla JS/Preact to minimize memory footprint).
- `/config`: Environment-specific configurations, including `local_config.json` for feature toggling.
- `/tests`: Unit and integration test suites.

## Architectural Guidelines
1. **Resource Efficiency**: Maximize use of asynchronous I/O to handle concurrency within the 2-thread limit.
2. **Non-Destructive Evolution**: Never remove code. Use `local_config.json` to disable features that exceed the 512MB cache threshold.
3. **Decoupling**: Business logic must not import UI or Transport modules directly.
4. **Scalability**: Utilize a plugin-based architecture for future feature expansion.

## Dependencies
- **Runtime**: Node.js/Python (Targeted for minimal runtime overhead).
- **Build System**: Standardized npm/pip scripts with `git` integration for versioned self-improvement.
- **Persistence**: SQLite (optimized for single-user low-resource local storage).

## Execution Plan
1. Initialize repository structure with `git init`.
2. Create `local_config.json` with initial feature flags (telemetry_verbose: false, background_indexing: false).
3. Implement core engine interface in `/src/core/engine.py`.
4. Establish Git branching strategy: `main` (stable), `dev` (integration), `feat/` (feature development).