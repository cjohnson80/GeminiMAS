import time
import duckdb

def _connect(self, db_path, retries=3, backoff=0.5):
    for i in range(retries):
        try:
            return duckdb.connect(db_path)
        except duckdb.IOException:
            if i == retries - 1: raise
            time.sleep(backoff * (2 ** i))
            continue