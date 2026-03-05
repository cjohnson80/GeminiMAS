# Project Summary: NotificationManager Architecture

## 1. Overview
The NotificationManager is responsible for decoupling the core AGI logic (`gemini_mas.py`) from specific external communication channels (like `tg_gateway.py`). It will use an asynchronous, event-driven hook system to dispatch critical updates, status changes, and high-priority alerts.

## 2. Core Components
*   **NotificationManager (New Service):** Will reside in a new module, likely `managers/notification_manager.py`. It maintains a registry of subscribed handlers.
*   **Event Hook Signature:** All registered handlers must conform to the following asynchronous signature:
    ```python
    async def handler(event_type: str, payload: dict, timestamp: float) -> None:
        ...
    ```
*   **Dispatch Strategy:** Notifications will be pushed onto an internal `asyncio.Queue`. A dedicated worker thread/task within the Manager will consume this queue and dispatch events concurrently to all registered subscribers, ensuring non-blocking operation for the main AGI loop.

## 3. Configuration Schema (`local_config.json`)
The configuration will control which services are enabled and their specific parameters.

```json
{
  "notification_manager": {
    "enabled": true,
    "max_concurrency": 10, 
    "log_level": "INFO",
    "subscribers": [
      {
        "name": "TelegramGateway",
        "type": "TG_BOT",
        "config": { 
          "api_token_key": "TELEGRAM_TOKEN" 
        }
      }
    ]
  }
} 
```

## 4. Interaction Flow (MAS <-> NotificationManager <-> TG Gateway)
1.  `gemini_mas.py` calls `NotificationManager.dispatch(event_type, payload)`.
2.  The Manager queues the event.
3.  The Manager's worker pulls the event and invokes all subscribed handlers.
4.  The `TelegramGateway` handler (which registers itself upon startup) receives the event and uses its own connection logic to send the message via Telegram.

## 5. Next Steps
Implement the `NotificationManager` class and update both `gemini_mas.py` (to use the manager) and `tg_gateway.py` (to register as a subscriber).