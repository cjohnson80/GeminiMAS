import os
import time
import duckdb
import polars as pl
from api import GeminiClient
from config import DB_FILE, SKILLS_DIR, read_file_safe

class Persistence:
    def __init__(self, api_key):
        self.client = GeminiClient(api_key)
        self.skills_dir = SKILLS_DIR
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        os.makedirs(self.skills_dir, exist_ok=True)
        self._init_db()

    def _init_db(self):
        # Ensure table exists
        for _ in range(10):
            try:
                with duckdb.connect(DB_FILE) as con:
                    con.execute("CREATE TABLE IF NOT EXISTS memory (timestamp TIMESTAMP, goal TEXT, summary TEXT, embedding FLOAT[768], success_score FLOAT, execution_time_seconds FLOAT)")
                return
            except Exception as e:
                if "lock" in str(e).lower():
                    time.sleep(0.5)
                    continue
                raise e

    def save_memory(self, goal, summary, success_score=None, execution_time_seconds=None):
        if vec := self.client.embed(goal + " " + summary):
            for _ in range(20): # Robust retry for writes
                try:
                    with duckdb.connect(DB_FILE) as con:
                        con.execute("INSERT INTO memory VALUES (now(), ?, ?, ?, ?, ?)", [goal, summary, vec, success_score, execution_time_seconds])
                    return
                except Exception as e:
                    if "lock" in str(e).lower():
                        time.sleep(1)
                        continue
                    break

    def semantic_search(self, query, limit=3):
        results = []
        if vec := self.client.embed(query):
            for _ in range(10):
                try:
                    # Open in read_only mode to allow multiple readers
                    with duckdb.connect(DB_FILE, read_only=True) as con:
                        results = con.execute("SELECT goal, summary FROM memory ORDER BY list_cosine_similarity(embedding, ?::FLOAT[768]) DESC LIMIT ?", [vec, limit]).pl().to_dicts()
                    break
                except Exception as e:
                    if "lock" in str(e).lower():
                        time.sleep(0.2)
                        continue
                    break
        # Skill Injection
        skills_found = []
        if os.path.exists(SKILLS_DIR):
            for f in os.listdir(SKILLS_DIR):
                if f.endswith(".md") and any(word in f.lower() for word in query.lower().split()):
                    skills_found.append({"goal": f"Skill: {f}", "summary": read_file_safe(os.path.join(SKILLS_DIR, f))[:2000]})

        return results + skills_found
