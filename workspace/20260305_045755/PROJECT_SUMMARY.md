# Project Scratchpad

Goal: send tg message when complete

## Acceptance Criteria
# Acceptance Criteria: Telegram Notification on Completion

### 1. Configuration & Credentials
- [ ] **Valid Config Check:** The system must validate the existence of `TG_BOT_TOKEN` and `TG_CHAT_ID` (either in `local_config.json` or environment variables) before attempting to send.
- [ ] **Feature Flag:** The notification feature respects a flag (e.g., `notifications.telegram_enabled`) in `local_config.json`.

### 2. Functional Execution
- [ ] **Trigger Point:** The notification is triggered immediately after the main execution loop reaches a `COMPLETED` or `FAILED` state.
- [ ] **Message Content:** The sent message must include:
    - Task Status (SUCCESS/FAILURE).
    - Execution Duration.
    - A brief summary or the final output result.
- [ ] **Integration:** Utilizes the existing `$AGENT_ROOT/bin/tg_gateway.py` logic or requests library to dispatch the payload.

### 3. Performance & Reliability (Low-Resource Optimization)
- [ ] **Non-Blocking:** The API call is performed asynchronously or in a separate thread to prevent blocking the agent's shutdown process for >2 seconds.
- [ ] **Error Handling:** If the Telegram API returns a 4xx/5xx error or times out:
    - The error is logged to `agent.log` with the tag `[TG_ERROR]`.
    - The agent process exits cleanly (does not crash or hang).
    - No infinite retry loops are initiated to conserve CPU cycles.

### 4. Verification (Manual Test)
- [ ] Run a short dummy task (e.g., `gemini_mas.py --task "Test Notification"`).
- [ ] Verify a message appears in the linked Telegram client within 5 seconds of process exit.

## Architecture
(To be defined by Architect)
