import sqlite3
import os

DB_PATHS = [
    'data/memory.db',
    'data/dashboard_db/dashboard.db', # Assuming the standard name
    'data/dashboard_db' # Checking if it's a file
]

def check_integrity(db_path):
    if not os.path.exists(db_path):
        return f'MISSING: {db_path}'
    
    if os.path.isdir(db_path):
        return f'ERROR: {db_path} is a directory, not a database file'

    try:
        conn = sqlite3.connect(db_path)
        result = conn.execute('PRAGMA integrity_check;').fetchall()
        conn.close()

        if result == [('ok',)]:
            return f'PASSED: {db_path}'
        else:
            return f'FAILED: {db_path} - Issues: {result}'
    except Exception as e:
        return f'ERROR: {db_path} - {str(e)}'

if __name__ == '__main__':
    # Scan data directory for any .db files as well
    found_dbs = set(DB_PATHS)
    for root, dirs, files in os.walk('data'):
        for file in files:
            if file.endswith('.db'):
                found_dbs.add(os.path.join(root, file))
    
    results = []
    for db in sorted(list(found_dbs)):
        results.append(check_integrity(db))
    
    print('\n'.join(results))
