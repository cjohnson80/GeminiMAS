# Project Scratchpad

Goal: lets create the test website

## Acceptance Criteria
# Acceptance Criteria: Test Website MVP

**User Story:** As a System Administrator, I want a lightweight local web interface so that I can verify the agent's web server capabilities and hosting infrastructure.

### 1. Server Initialization & Configuration
- [ ] **Launch Script:** A dedicated script (e.g., `start_web_test.py`) exists in `bin/` or `tests/` to launch the server.
- [ ] **Port Binding:** The server successfully binds to `localhost:8080` (or a port defined in `local_config.json`).
- [ ] **Console Output:** Upon startup, the console displays the active URL and process ID.

### 2. Core Page Rendering
- [ ] **Root Access:** A `GET` request to `/` returns a valid HTML5 document with a status code of `200`.
- [ ] **Visual Validation:** The homepage contains an `<h1>` tag with the text "GeminiMAS Test Node".
- [ ] **Metadata:** The HTML `<title>` tag reads "System Status".

### 3. Static Asset Delivery
- [ ] **CSS Loading:** The server serves a stylesheet at `/static/style.css`.
- [ ] **Verification:** The homepage includes the CSS file, and a direct `GET` request to the CSS URL returns status `200` with `Content-Type: text/css`.

### 4. API Connectivity
- [ ] **Health Endpoint:** A `GET` request to `/api/health` returns a JSON response.
- [ ] **JSON Schema:** The response matches the format:
  ```json
  {
    "status": "online",
    "system": "GeminiMAS",
    "version": "<current_version>"
  }
  ```

### 5. Performance Constraints (Low-Resource Profile)
- [ ] **Memory Usage:** The web server process consumes **< 100MB RAM** while idle.
- [ ] **Startup Time:** The server is ready to accept connections within **< 2 seconds** of execution.
- [ ] **Dependencies:** No heavy frontend frameworks (React/Angular) are required for the basic build; use vanilla HTML/CSS/JS or lightweight templates.

## Architecture
(To be defined by Architect)
