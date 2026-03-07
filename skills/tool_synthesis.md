# Skill: Dynamic Tool Synthesis

## CONTEXT
Use this skill when you encounter a task that is repetitive, slow using standard bash commands, or requires complex programmatic logic that isn't covered by your current toolset.

## THE EVOLUTIONARY HAND PROTOCOL
As Atlas, you have the authority to invent your own tools. If you need a "hammer," you build one.

### 1. Identify the Gap
- Are you writing long, complex `awk`/`sed` bash commands that often fail?
- Are you doing data manipulation (like CSV or JSON merging) that would be trivial in Python?
- Are you trying to interact with an external API?

### 2. Synthesize the Tool
- Create a new Python file in `bin/tools/` (e.g., `bin/tools/process_data.py`).
- Use the `write_file` tool to save it.
- **CRITICAL FORMAT:** The tool MUST expose a function called `execute(payload)`.

```python
import json

def execute(payload):
    \"\"\"
    Atlas Tool: Describe what it does.
    Payload: A description of the expected JSON or string payload.
    \"\"\"
    try:
        if isinstance(payload, str):
            data = json.loads(payload)
        else:
            data = payload
        
        # ... your custom logic here ...
        
        return "Success message or data"
    except Exception as e:
        return f"Error: {str(e)}"
```

### 3. Immediate Usage
- As soon as you write the file to `bin/tools/tool_name.py`, the core engine will automatically discover it on your *next turn*.
- You can immediately call `"tool": "tool_name"` in your next JSON response.

### 4. Best Practices
- **Robustness:** Always include `try/except` blocks. If your tool crashes, it shouldn't crash the swarm.
- **Stateless:** Tools should ideally be stateless and return strings or JSON data that you can read in the `tool_result`.
- **Dependencies:** If your tool requires a pip package, use `run_shell` to `pip install` it into the `venv` *before* using the tool.