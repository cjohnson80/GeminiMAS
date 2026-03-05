import duckdb
import os

DB_PATH = '/home/chrisj/gemini_agents/data/mas_core.db'

def validate_db_config():
    # Enforce read_only for IO efficiency on Celeron hardware
    try:
        conn = duckdb.connect(database=DB_PATH, read_only=True)
        conn.execute('SELECT 1')
        conn.close()
        return True, 'DB_VALIDATED'
    except Exception as e:
        return False, str(e)

if __name__ == '__main__':
    status, msg = validate_db_config()
    print(f'{status}:{msg}')
