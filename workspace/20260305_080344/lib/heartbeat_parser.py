import os
import re

HEARTBEAT_FILE = "/home/chrisj/gemini_agents/core/HEARTBEAT.md"

def parse_heartbeat():
    """
    Verifies existence and parses /home/chrisj/gemini_agents/core/HEARTBEAT.md
    for unchecked tasks (lines starting with '- [ ]').
    Returns a list of task dictionaries.
    """
    if not os.path.exists(HEARTBEAT_FILE):
        return []

    unchecked_tasks = []
    # Regex to find lines starting with optional whitespace, then '- [ ]'
    task_pattern = re.compile(r"^\s*-\s*\[\s*\]\s*(.*)", re.MULTILINE)

    try:
        with open(HEARTBEAT_FILE, 'r') as f:
            content = f.read()
            
        matches = task_pattern.findall(content)
        
        for task_description in matches:
            cleaned_task = task_description.strip()
            if cleaned_task:
                unchecked_tasks.append({
                    "task_description": cleaned_task,
                    "source_file": HEARTBEAT_FILE
                })
                
    except IOError:
        return []
        
    return unchecked_tasks

if __name__ == '__main__':
    # Dummy execution context for testing purposes
    print(f"Parser module loaded from: {__file__}")
