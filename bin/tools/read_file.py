import os

def execute(payload):
    with open(os.path.expanduser(payload), 'r') as f: return f.read()
