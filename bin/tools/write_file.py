import os
import json

def execute(payload):
    if isinstance(payload, str):
        try: data = json.loads(payload)
        except: return "Error: payload must be JSON for write_file"
    else: data = payload
    os.makedirs(os.path.dirname(os.path.expanduser(data['path'])), exist_ok=True)
    with open(os.path.expanduser(data['path']), 'w') as f: f.write(data['content'])
    return f"Successfully wrote to {data['path']}"
