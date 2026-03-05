import duckdb
import threading
from queue import Queue

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.write_queue = Queue()
        self._start_worker()

    def _start_worker(self):
        def worker():
            conn = duckdb.connect(self.db_path)
            while True:
                query, event = self.write_queue.get()
                try:
                    conn.execute(query)
                finally:
                    self.write_queue.task_done()
                    if event: event.set()
        threading.Thread(target=worker, daemon=True).start()

    def execute_write(self, query, wait=False):
        event = threading.Event() if wait else None
        self.write_queue.put((query, event))
        if wait: event.wait()

    def execute_read(self, query):
        with duckdb.connect(self.db_path, read_only=True) as conn:
            return conn.execute(query).fetchall()