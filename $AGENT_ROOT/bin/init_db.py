import sqlite3
import os

# Define paths relative to the execution environment, assuming $AGENT_ROOT is the base.
DB_PATH = os.path.join(os.environ.get('AGENT_ROOT', '.'), 'data', 'dashboard.db')

# Ensure the data directory exists
DATA_DIR = os.path.dirname(DB_PATH)
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

def initialize_database():
    """Initializes the SQLite database and creates the Metrics table."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        print(f'Successfully connected to database at: {DB_PATH}')

        # Schema Definition for Metrics Table
        create_table_query = """
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY,
            timestamp TEXT NOT NULL,
            metric_type TEXT NOT NULL,
            value REAL NOT NULL
        );"""

        cursor.execute(create_table_query)
        conn.commit()
        print('Metrics table ensured/created successfully.')

    except sqlite3.Error as e:
        print(f'Database error occurred: {e}')
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    initialize_database()
