import duckdb

def get_connection(db_path, read_only=True):
    return duckdb.connect(db_path, read_only=read_only)
