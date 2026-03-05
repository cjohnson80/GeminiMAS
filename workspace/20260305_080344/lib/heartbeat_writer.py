import threading
import os

class HeartbeatWriter:
    """Handles thread-safe persistence of task status to a central file (e.g., a Markdown checklist)."""

    def __init__(self, persistence_path, lock_timeout=5.0):
        self.persistence_path = persistence_path
        self.lock = threading.Lock()
        self.lock_timeout = lock_timeout
        os.makedirs(os.path.dirname(persistence_path), exist_ok=True)

    def _update_status(self, search_term, new_prefix):
        """Reads the file, finds the line matching search_term, and replaces its status prefix."""
        if not self.lock.acquire(timeout=self.lock_timeout):
            print(f"Warning: Could not acquire lock for {self.persistence_path}")
            return False

        try:
            with open(self.persistence_path, 'r') as f:
                lines = f.readlines()

            new_lines = []
            updated = False
            for line in lines:
                # Look for the initial incomplete status: '- [ ]' or similar
                if search_term in line and line.strip().startswith('- [ ]'):
                    # Replace the status marker. Assuming the format is consistent.
                    new_line = line.replace('- [ ]', new_prefix, 1)
                    new_lines.append(new_line)
                    updated = True
                else:
                    new_lines.append(line)

            if updated:
                with open(self.persistence_path, 'w') as f:
                    f.writelines(new_lines)
                return True
            return False # Item not found or already updated

        except Exception as e:
            print(f"Error writing heartbeat status: {e}")
            return False
        finally:
            self.lock.release()

    def mark_success(self, task_identifier):
        """Marks a specific task as successful ('- [x]')."""
        # task_identifier should be unique enough to find the line, e.g., a unique part of the description.
        success_prefix = '- [x] '
        return self._update_status(task_identifier, success_prefix)

    def mark_failure(self, task_identifier):
        """Marks a specific task as failed ('- [!]')."""
        failure_prefix = '- [!] '
        return self._update_status(task_identifier, failure_prefix)

# Example Usage (for testing/context, not production execution):
# if __name__ == '__main__':
#     # This assumes a setup where a file like PROJECT_SUMMARY.md exists
#     writer = HeartbeatWriter('./test_summary.md')
#     # First, ensure the file exists with a task:
#     with open('./test_summary.md', 'w') as f:
#         f.write("# Project Status

- [ ] Initialize workspace
- [ ] Implement heartbeat_writer
")
#     
#     print(f"Marking initialization as success: {writer.mark_success('Initialize workspace')}")
#     print(f"Marking implementation as failure: {writer.mark_failure('Implement heartbeat_writer')}")
