# CLI Gateway Architecture (REPL)

## 1. Overview
The `cli_gateway.py` serves as a local, interactive REPL (Read-Eval-Print Loop) alternative to the `tg_gateway.py`. It adheres to the **Gateway** and **Adapter** design patterns, ensuring the core `AtlasSwarm` engine remains completely decoupled from the user interface.

## 2. Core Components

### A. REPL Event Loop (`asyncio` + `prompt_toolkit`)
- **Responsibility:** Manages the non-blocking asynchronous input loop.
- **Features:** Command history, syntax highlighting, and asynchronous progress indicators (spinners) during long-running MAS execution.
- **Signal Handling:** Gracefully intercepts `Ctrl+C` (SIGINT) to cancel the current generation task without killing the REPL, and `Ctrl+D` (EOF) to trigger a safe system teardown.

### B. MAS Adapter (`MASAdapter`)
- **Responsibility:** Acts as the translation layer between the raw CLI strings and the `AtlasSwarmWrapper`.
- **Mechanism:** Injects the `AtlasSwarmWrapper` as a dependency. When a user types a command, the adapter wraps the request in an async task, submits it to the `mas_wrapper.execute_task()`, and awaits the callback/future without blocking the REPL.

### C. Session & State Manager (`LocalSession`)
- **Responsibility:** Maintains the context window, chat history, and current focus (e.g., active project or machine routing).
- **Parity with TG:** Mimics the `chat_id` and user states found in `tg_gateway.py`, storing transient state in `workspace/.cli_session.json`.

## 3. Integration Path
1. **Initialization:** The CLI Gateway boots, loads `.env` for the API key, and initializes `AtlasSwarmWrapper`.
2. **Execution:** User inputs `"/analyze src/"`. The REPL parses the command and passes it to the `MASAdapter`.
3. **Threading:** `MASAdapter` calls `wrapper.execute_task(core_process_func, args)`. The REPL displays an async spinner.
4. **Resolution:** The thread completes, placing the result in an `asyncio.Queue`. The REPL loop consumes the queue and prints the formatted markdown response to `stdout`.
