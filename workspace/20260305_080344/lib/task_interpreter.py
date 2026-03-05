import re
import json
from typing import List, Dict, Any

# Assume other modules like heartbeat_parser are available in the workspace path
# For this implementation, we focus on the interpretation logic.

class TaskInterpreter:
    def __init__(self, agent_context: Dict[str, Any]):
        self.context = agent_context
        # Define patterns for command extraction
        self.shell_pattern = re.compile(r"^EXECUTE SHELL: (.*)", re.IGNORECASE)
        self.write_pattern = re.compile(r"^WRITE FILE: (.*) WITH CONTENT: (.*)", re.IGNORECASE)

    def interpret(self, task_item: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Analyzes a task description and returns a list of structured actions.
        :param task_item: Dictionary from heartbeat_parser, e.g., {'task_description': '...', 'source_file': '...'}
        :return: List of actions to be processed by the main agent loop.
        """
        description = task_item.get('task_description', '').strip()
        actions = []

        # 1. Check for SHELL execution command
        shell_match = self.shell_pattern.match(description)
        if shell_match:
            command = shell_match.group(1).strip()
            actions.append({
                'type': 'run_shell',
                'payload': command,
                'source': task_item
            })
            return actions

        # 2. Check for FILE WRITE command
        write_match = self.write_pattern.match(description)
        if write_match:
            # This assumes the content is relatively clean or needs careful handling later
            file_path_raw = write_match.group(1).strip()
            content_raw = write_match.group(2).strip()

            # Basic sanitization: If content contains JSON structure markers, try to parse it.
            try:
                # Attempt to load content as JSON if it looks like it might be structured data
                content = json.loads(content_raw)
                content_str = json.dumps(content) # Re-dump to ensure canonical JSON string
            except json.JSONDecodeError:
                content_str = content_raw # Use raw string if parsing fails
            
            actions.append({
                'type': 'write_file',
                'payload': json.dumps({
                    'path': file_path_raw,
                    'content': content_str
                }),
                'source': task_item
            })
            return actions

        # 3. Default/Fallback: Treat as general instruction or log entry
        actions.append({
            'type': 'log_instruction',
            'payload': description,
            'source': task_item
        })

        return actions


if __name__ == '__main__':
    # Example usage simulation
    interpreter = TaskInterpreter({}) 
    test_tasks = [
        {'task_description': 'EXECUTE SHELL: echo "Initialization complete" >> /tmp/boot.log', 'source_file': 'test.md'},
        {'task_description': 'WRITE FILE: /tmp/config.json WITH CONTENT: {"setting": "high"}', 'source_file': 'test.md'},
        {'task_description': 'Review system performance metrics.', 'source_file': 'test.md'}
    ]
    
    print("--- Interpreting Test Tasks ---")
    for task in test_tasks:
        interpreted_actions = interpreter.interpret(task)
        print(f"\nOriginal Task: {task['task_description']}")
        print(f"Interpreted Actions: {json.dumps(interpreted_actions, indent=2)}")

EOF'
