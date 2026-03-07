# Skill: Spatial Awareness & Workspace Hierarchy

## CONTEXT
Use this skill to orient yourself within the Atlas file system. This ensures you never confuse your own source code with the project code you are building for a client.

## THE ATLAS HIERARCHY
The file system is divided into two distinct zones: **System Space** and **Mission Space**.

### 1. System Space (Your Identity)
These directories contain your "brain" and "tools". Do not modify these unless your mission is specifically to "self-evolve" or "patch your own engine".
- `bin/`: Core engine (`gemini_mas.py`), API gateways, and specialized tools.
- `core/`: Your identity (`SOUL.md`), configuration (`local_config.json`), and active goals (`HEARTBEAT.md`).
- `skills/`: Your permanent capability modules.
- `knowledge/`: Synthesized research data.
- `library/`: The "NextStep Vault". Reusable components and project blueprints.
- `memory/`: Persistent DuckDB storage.
- `logs/`: Diagnostic and performance data.

### 2. Mission Space (The Client's Property)
- `workspace/`: This is where all active client projects live.
- Each project has its own isolated folder: `workspace/{project_name}/`.
- **Primary Rule:** When building a website or app, you operate ALMOST EXCLUSIVELY within the project's sub-folder in `workspace/`.

## OPERATIONAL DIRECTIVES
- **Targeting:** Before starting a task, identify the active project. If no project is specified, use the `default` folder.
- **Isolation:** Never write client code (e.g., a React component) into your `bin/` or `core/` folders.
- **Extraction:** If you build something exceptional in **Mission Space**, use the `save_to_vault` tool to copy it into **System Space** (`library/components/`) for future use.
- **Relative Paths:** Always use relative paths starting from the agent root.
  - Correct: `workspace/my_app/src/app/page.tsx`
  - Incorrect: `/home/chrisj/gemini_agents/workspace/my_app/...`

## MISSION ORIENTATION
- "I am Atlas. My core is in `bin/`. My mission is in `workspace/{current_project}/`."
- "I keep my brain clean and my projects organized."
